#!/usr/bin/env python
"""remote_files.py - Module for listing and getting remote files
"""
import hashlib
from collections import namedtuple, MutableSet
import requests
from urlparse import urljoin
from tempfile import NamedTemporaryFile
import re
try:
    import glanceclient
    import keystoneclient
except ImportError:
    # Just make Glance functionality broken if client libraries are not
    # instsalled
    pass


file_digest = namedtuple('file_digest', ('hexdigest', 'algorithm'))


class BadFileDigest(Exception):
    """Raised when file data does not match digest information"""
    pass


class RemoteFile(object):
    """Represents a file on a remote location

    :param str name:           The name of the remote file
    :param str url:            The URL of the remote file
    :param file_digest digest: (Optional) The digest value for the file and the
                               algorithm used to verify it
    """
    def __init__(self, name, url, digest=None):
        self._name = name
        self._url = url
        self._digest = digest

    @property
    def name(self):
        return self._name

    @property
    def url(self):
        return self._url

    @property
    def digest(self):
        return self._digest

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{} url={}>".format(type(self).__name__, self.url)

    def __cmp__(self, other):
        return cmp(
            (self.name, self.url, self.digest),
            (other.name, other.url, other.digest)
        )

    def __hash__(self):
        return hash((self.name, self.url, self.digest))

    def download(self, verify_digest=True):
        """Download file into a temporary location

        :param bool verify_digest: (Optional) whether to verify the file digest
                                   while downloading. True by default. Digest
                                   will only be verified if the file has such
                                   information.
        :rtype: NamedTemporaryFile
        :returns: An open temporary file with the downloaded information
        """
        if verify_digest and self.digest:
            digest_algo = self.digest.algorithm()
        else:
            digest_algo = None
        resp = requests.get(self.url, stream=True)
        resp.raise_for_status()
        tmp = NamedTemporaryFile()
        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                tmp.write(chunk)
                if digest_algo is not None:
                    digest_algo.update(chunk)
        if digest_algo is not None:
            if digest_algo.hexdigest() != self.digest.hexdigest:
                raise BadFileDigest("Bad file digest for: {}".format(self))
        tmp.flush()
        tmp.seek(0)
        return tmp


def _strip_gpg_wrappers(lines):
    """Strip GPG signiture headers and blocks from input lines

    :param Iterable lines: Lines of text
    :rtype: Iterator
    :returns: Iterator over non-signiture or header lines
    """
    MBEGIN = '-----BEGIN PGP SIGNED MESSAGE-----'
    SBEGIN = '-----BEGIN PGP SIGNATURE-----'
    SEND = '-----END PGP SIGNATURE-----'

    line_i = iter(lines)
    try:
        while True:
            line = next(line_i)
            while line.rstrip() != MBEGIN:
                yield line
                line = next(line_i)
            next(line_i)
            next(line_i)
            line = next(line_i)
            while line.rstrip() != SBEGIN:
                yield line
                line = next(line_i)
            while line.rstrip() != SEND:
                line = next(line_i)
    except StopIteration:
        pass


def _from_digest_file_lines(digest_file_url, lines, digest_algo):
    for line in lines:
        digest, file_name = line.split()
        yield RemoteFile(
            name=file_name,
            url=urljoin(digest_file_url, file_name),
            digest=file_digest(hexdigest=digest, algorithm=digest_algo)
        )


def from_http_with_digest_file(digest_file_url, digest_algo=hashlib.sha256):
    """List files in a remote HTTP directory that includes a hash digest file

    :param str digest_file_url:  The url of the file that lists the files in
                                 the same directory and their hashes
    :param Callable digest_algo: The algorithm used to generate the hashes in
                                 the digest file, as represented by the hashlib
                                 module
    :rtype: Iterator
    :returns: Iterator of files listed in the digest file
    """
    resp = requests.get(digest_file_url, stream=True)
    resp.raise_for_status()
    for remote_file in _from_digest_file_lines(
        digest_file_url, _strip_gpg_wrappers(resp.iter_lines()), digest_algo
    ):
        yield remote_file


def _from_fedora_file_lines(digest_file_url, lines):
    """Given lines of a Fedora digest file, return listed remote files
    """
    FEDRE = re.compile('^(?P<algo>[A-Z0-9]+) \((?P<name>.+)\) = (?P<hash>.+)$')
    for line in lines:
        mtc = FEDRE.match(line)
        if not mtc:
            continue
        algo_name = mtc.group('algo').lower()
        if algo_name in hashlib.algorithms:
            algo = getattr(hashlib, algo_name)
        else:
            continue
        yield RemoteFile(
            name=mtc.group('name'),
            url=urljoin(digest_file_url, mtc.group('name')),
            digest=file_digest(mtc.group('hash'), algo)
        )


def from_http_with_fedora_file(digest_file_url):
    """List files in a remote HTTP directory that includes a Fedora style
    digest file

    :param str digest_file_url:  The url of the file that lists the files in
                                 the same directory and their hashes
    :rtype: Iterator
    :returns: Iterator of files listed in the digest file
    """
    resp = requests.get(digest_file_url, stream=True)
    resp.raise_for_status()
    for remote_file in _from_fedora_file_lines(
        digest_file_url, _strip_gpg_wrappers(resp.iter_lines())
    ):
        yield remote_file


class Glance(MutableSet):
    """Representing Glance as a mutable set of files

    :param str image_url:   (Optional) URL of the Glance image service API
    :param str auth_token:  (Optional) OpenStack authentication token
    :param str auth_url:    (Optional) URL of Keystone service
    :param str tenant_name: (Optional) OpenStack tenant for authentication
    :param str username:    (Optional) Username for authentication
    :param str password:    (Optional) Password for authentication

    Service usage credintials must be specified by either passing auth_token or
    auth_url, tenant_name, username and password. If none are given, an attempt
    to use Glance anonymously would be made.
    If image_url is not given, auth_url must be passed so that Keystone can be
    queried for the image service endpoint.

    Examples:
        - Connect anonymously to a Glance server that allows it:

            Glance(image_url='http://glance.ovirt.org:9292')

        - Connect while authenticating via Keystone:

            Glance(
                auth_url='http://glance.ovirt.org:35357/v2.0',
                tenant_name='service',
                username='glance',
                password='...',
            )
    """
    def __init__(
        self, image_url=None, auth_token=None, auth_url=None, tenant_name=None,
        username=None, password=None
    ):
        ks_session = None
        if auth_token is None:
            if (
                auth_url is None or tenant_name is None or
                username is None or password is None
            ):
                auth_token = '-anonymous-'
            else:
                ks_auth = keystoneclient.auth.identity.v2.Password(
                    auth_url=auth_url,
                    username=username,
                    password=password,
                    tenant_name=tenant_name,
                )
                ks_session = keystoneclient.session.Session(auth=ks_auth)
                auth_token = ks_session.get_token()
        if image_url is None:
            if ks_session is None:
                if auth_url:
                    ks_auth = keystoneclient.auth.identity.v2.Token(
                        auth_url=auth_url,
                        token=auth_token
                    )
                else:
                    raise TypeError('Must pass either image_url or auth_url')
                ks_session = keystoneclient.session.Session(auth=ks_auth)
            image_url = ks_session.get_endpoint(
                service_type='image', interface='public'
            )
        self.gcl = glanceclient.Client(
            '2', endpoint=image_url, token=auth_token
        )
        self._data = {}
        self.refresh()

    def refresh(self):
        """Refresh files from Glance"""
        self._data.clear()
        for glance_img in self.gcl.images.list():
            self._add_glance_image(glance_img)

    def add(self, fil):
        """Add file to glance"""
        self._add(fil)

    def _add(self, fil, **extra_args):
        """Private add implementation that allows for finer grained control on
        Glance data
        """
        if fil in self:
            return
        # Set default assumed values for mandatory arguments
        extra_args.setdefault('disk_format', 'raw')
        extra_args.setdefault('container_format', 'bare')
        gli = self.gcl.images.create(name=fil.name, **extra_args)
        self.gcl.images.upload(gli.id, fil.download())
        self._add_glance_image(gli)

    def _add_glance_image(self, gli):
        fil = self._glance_image_to_member(gli)
        if fil is not None:
            self._data[fil] = gli.id

    def _glance_image_to_member(self, gli):
        if 'name' not in gli or 'file' not in gli:
            # Skip broken image objects
            return
        if 'checksum' in gli:
            digest = file_digest(gli.checksum, hashlib.md5)
        else:
            digest = None
        return RemoteFile(
            gli.name,
            urljoin(self.gcl.http_client.endpoint, gli.file),
            digest
        )

    def discard(self, fil):
        """Remove file from Glance"""
        gli_id = self._data.get(fil)
        if gli_id is not None:
            self.gcl.images.delete(gli_id)
            self._data.pop(fil, None)

    def __contains__(self, fil):
        return fil in self._data

    def __iter__(self):
        return self._data.iterkeys()

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return repr(set(self._data.iterkeys()))

    # Enable binary non-mutating opertators to return plain sets
    @classmethod
    def _from_iterable(cls, it):
        return set(it)


from_glance = Glance
