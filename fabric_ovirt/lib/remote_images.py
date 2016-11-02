#!/usr/bin/env python
"""remote_files.py - Module for listing and getting remote VM images
"""
from distutils.version import LooseVersion
import re
from collections import Mapping
from functools import partial
from itertools import chain
import requests
import hashlib

from fabric_ovirt.lib.html import find_hrefs_in_stream
from fabric_ovirt.lib.remote_files import RemoteFile, file_digest
from fabric_ovirt.lib import remote_files
from fabric_ovirt.lib.topbygroup import topbygroup

# Don't let pyflakes warn about user convenience imports
assert LooseVersion, file_digest


class RemoteImage(RemoteFile):
    """Represents a VM image in a remote location

    :param str name:              The name of the remote image
    :param str url:               The URL of the remote image
    :param file_digest digest:    (Optional) The digest value for the image and
                                  the algorithem used to verify it
    :param str image_name:        The un-versioned basic name of the image
                                  (Typically which OS it contains)
    :param LooseVersion version:  The version of the remote image
    :param LooseVersion revision: (optional) A revision number for the image
    :param str arch:              The system architecture of the image
    """
    def __init__(
        self, name, url, image_name, version, arch,
        revision=None, digest=None
    ):
        super(RemoteImage, self).__init__(name, url, digest)
        self._image_name = image_name
        self._version = version
        self._arch = arch
        self._revision = revision

    @property
    def image_name(self):
        return self._image_name

    @property
    def version(self):
        return self._version

    @property
    def revision(self):
        return self._revision

    @property
    def arch(self):
        return self._arch

    def __cmp__(self, other):
        return cmp(
            (
                self.image_name, self.version,
                self.arch, self.revision, self.name
            ),
            (
                other.image_name, other.version,
                other.arch, other.revision, other.name
            )
        )

    def __hash__(self):
        return hash((
            self.image_name, tuple(self.version.version), self.arch,
            self.revision is not None and tuple(self.revision.version),
            self.name
        ))


def from_files_by_regex(
    files, regex, name=None, image_name=None,
    version=None, revision=None, arch=None
):
    """Convert remote files into remote images by using a regex to extract
    image information from the file name

    :param Iterable files: Set of RemoteFile objects
    :param str regex:      Regex to use for filtering image files and
                           extracting image information from the file name.
    :param str name:       (optional) A replacment expression (as in, the
                           'repl' arguments passed to re.sub) to create the
                           name of the image from a import matching file name
    :param str image_name: (optional) A replacement expression to create the
                           image un-versioned name from the file name
    :param str version:    (optional) A replacement expression to create the
                           image version from the file name
    :param str revision:   (optional) A replacement expression to create the
                           image revision from the file name
    :param str arch:       (optional) A replacement expression to create the
                           image architecture from the file name

    If the default values for the image_name, version, revision and arch are
    used, then 'regex' should contain named matchers (As defined by the
    '(?P<foo>) syntax) with the following names: image_name, version, arch and
    optionally revision.
    If there is no 'revision' named matcher, the image revision would be None
    by default.
    If the 'name' argument is not given, then if 'regex' includes a 'name'
    named matcher, the matched string would be used, otherwise the whole
    original file name would be used.

    :rtype: Iterator
    :returns: Iterator of files listed in the digest file
    """
    if image_name is None:
        image_name = '\g<image_name>'
    if version is None:
        version = '\g<version>'
    if arch is None:
        arch = '\g<arch>'
    regex = re.compile(regex)
    for fil in files:
        mtc = regex.search(fil.name)
        if not mtc:
            continue
        grpd = mtc.groupdict()
        if name is None:
            i_name = grpd.get('name', fil.name)
        else:
            i_name = mtc.expand(name)
        i_image_name = mtc.expand(image_name)
        i_version = LooseVersion(mtc.expand(version))
        if revision is None:
            if 'revision' in grpd:
                revision = '\g<revision>'
            else:
                i_revision = None
        if revision is not None:
            i_revision = LooseVersion(mtc.expand(revision))
        i_arch = mtc.expand(arch)
        yield RemoteImage(
            i_name, fil.url, i_image_name, i_version,
            i_arch, i_revision, fil.digest
        )


class ImageSourceList(Mapping):
    """Class representing a mapping of named image sources"""
    def __init__(self):
        self._image_sources = dict()

    def __getitem__(self, key):
        return self._image_sources[key]()

    def __len__(self):
        return len(self._image_sources)

    def __iter__(self):
        return iter(self._image_sources)

    def __repr__(self):
        return repr(self._image_sources)

    def _add_source(self, name):
        def decorator(func):
            self._image_sources[name] = func
            return func
        return decorator


sources = ImageSourceList()
list_from = sources.__getitem__
_image_source = sources._add_source


@_image_source("CentOS 6")
def from_centos6():
    return from_files_by_regex(
        files=remote_files.from_http_with_digest_file(
            'http://cloud.centos.org/centos/6/images/sha256sum.txt',
        ),
        regex='^CentOS-6-(?P<arch>.+)-GenericCloud-(?P<version>\d{4})\.qcow2$',
        name='CentOS 6 Generic Cloud Image v\g<version> for \g<arch>',
        image_name='CentOS 6 Generic Cloud Image',
    )


@_image_source("CentOS 7")
def from_centos7():
    return from_files_by_regex(
        files=remote_files.from_http_with_digest_file(
            'http://cloud.centos.org/centos/7/images/sha256sum.txt',
        ),
        regex='^CentOS-7-(?P<arch>.+)-GenericCloud-(?P<version>\d{4})\.qcow2$',
        name='CentOS 7 Generic Cloud Image v\g<version> for \g<arch>',
        image_name='CentOS 7 Generic Cloud Image',
    )


@_image_source("CentOS Atomic 7")
def from_centos_atomic7():
    return from_files_by_regex(
        files=remote_files.from_http_with_digest_file(
            'http://cloud.centos.org/centos/7/atomic/images/sha256sum.txt'
        ),
        regex='^CentOS-Atomic-Host-7.(?P<version>\d{4})-GenericCloud.qcow2$',
        name='CentOS 7 Atomic Host Image v\g<version> for x86_64',
        image_name='CentOS 7 Atomic Host Image',
        arch='x86_64',
    )


class Glance(remote_files.Glance):
    def refresh(self):
        super(Glance, self).refresh()
        self._convert_files_to_images()

    def add(self, img):
        self._add(img)

    def _add(self, img, **extra_args):
        extra_args.setdefault('disk_format', 'qcow2')
        extra_args.setdefault('container_format', 'bare')
        extra_args.setdefault('visibility', 'public')
        super(Glance, self)._add(img, **extra_args)
        self._convert_files_to_images()

    def _convert_files_to_images(self):
        """Convert RemoteFile object to RemoteImage"""
        files = [obj for obj in self if obj is not RemoteImage]
        id_map = {}
        for fil in files:
            id_map[fil.url] = self._data.pop(fil)
        for img in self._files_to_images(files):
            self._data[img] = id_map[img.url]

    @staticmethod
    def _files_to_images(files):
        regex = '^(?P<image_name>.+) v?(?P<version>[\d\.]+) for (?P<arch>.+)$'
        return from_files_by_regex(files=files, regex=regex)


from_glance = Glance
from_ovirt_glance = _image_source("oVirt Glance")(
    partial(Glance, image_url='http://glance.ovirt.org:9292')
)


@_image_source("Cirros")
def from_cirros():
    dl_cirrus = 'http://download.cirros-cloud.net/'
    resp = requests.get(dl_cirrus, stream=True)
    resp.raise_for_status()
    rel_dir = re.compile('^\d+\.\d+\.\d+/')
    return chain.from_iterable(
        from_files_by_regex(
            files=remote_files.from_http_with_digest_file(
                dl_cirrus + href + 'MD5SUMS', hashlib.md5
            ),
            regex='^cirros-(?P<version>.+)-x86_64-disk\.img$',
            name='CirrOS \g<version> for x86_64',
            image_name='CirrOS',
            arch='x86_64',
        )
        for href in find_hrefs_in_stream(resp)
        if rel_dir.match(href)
    )


FEDORA_BASE = 'http://download.fedoraproject.org/pub'


def _from_fedora_pre24(fedora_ver):
    ck_url = (
        FEDORA_BASE +
        '/fedora/linux/releases/{ver}' +
        '/Cloud/x86_64/Images/Fedora-Cloud_Images-x86_64-{ver}-CHECKSUM'
    ).format(ver=fedora_ver)
    regex = '^Fedora-Cloud-(?P<imgtyp>.+)-{ver}-(?P<version>.+).x86_64.qcow2$'\
        .format(ver=fedora_ver)
    return from_files_by_regex(
        files=remote_files.from_http_with_fedora_file(ck_url),
        regex=regex,
        name='Fedora {ver} Cloud \g<imgtyp> Image v\g<version> for x86_64'
        .format(ver=fedora_ver),
        image_name='Fedora {ver} Cloud \g<imgtyp> Image'
        .format(ver=fedora_ver),
        arch='x86_64',
    )


def _from_fedora_post24(fedora_ver):
    base_url = FEDORA_BASE + '/alt/atomic/stable'
    resp = requests.get(base_url, stream=True)
    resp.raise_for_status()
    rel_dir = re.compile('^Fedora-Atomic-{}-(.+)/$'.format(fedora_ver))
    regex = \
        '^Fedora-(Cloud-)?(?P<imgtyp>.+)-{ver}-(?P<version>.+).x86_64.qcow2$'\
        .format(ver=fedora_ver)
    for href in find_hrefs_in_stream(resp):
        mtc = rel_dir.match(href)
        if not mtc:
            continue
        rel_ver = mtc.group(1)
        files = remote_files.from_http_with_fedora_file(
            base_url + '/' + href + 'CloudImages/x86_64/images/' +
            'Fedora-CloudImages-{fedora_ver}-{rel_ver}-x86_64-CHECKSUM'
            .format(fedora_ver=fedora_ver, rel_ver=rel_ver)
        )
        for img in from_files_by_regex(
            files=files,
            regex=regex,
            name='Fedora {ver} Cloud \g<imgtyp> Image v\g<version> for x86_64'
            .format(ver=fedora_ver),
            image_name='Fedora {ver} Cloud \g<imgtyp> Image'
            .format(ver=fedora_ver),
            arch='x86_64',
        ):
            yield img


@_image_source("Fedora 22")
def from_fedora22():
    return _from_fedora_pre24(22)


@_image_source("Fedora 23")
def from_fedora23():
    return _from_fedora_pre24(23)


@_image_source("Fedora 24")
def from_fedora24():
    return _from_fedora_post24(24)


def _from_ubuntu(code_name, full_verion_name):
    base_url = 'https://cloud-images.ubuntu.com/' + code_name
    resp = requests.get(base_url, stream=True)
    resp.raise_for_status()
    rel_dir = re.compile('^[\d\.]+/')
    return chain.from_iterable(
        from_files_by_regex(
            files=remote_files.from_http_with_digest_file(
                base_url + '/' + href + 'SHA256SUMS', hashlib.sha256, ' *'
            ),
            regex='^{code_name}-server-cloudimg-amd64(-disk1)?.img$'.format(
                code_name=code_name
            ),
            name='Ubuntu Server {fvn} Cloud Image v{build} for x86_64'.format(
                fvn=full_verion_name, build=href[0:-1]
            ),
            image_name='Ubuntu Server {fvn} Cloud Image'.format(
                fvn=full_verion_name
            ),
            version=href[0:-1],
            arch='x86_64',
        )
        for href in find_hrefs_in_stream(resp)
        if rel_dir.match(href)
    )


@_image_source("Ubuntu 14.04 LTS")
def from_ubuntu_14_04():
    return _from_ubuntu('trusty', '14.04 LTS (Trusty Tahr)')


@_image_source("Ubuntu 16.04 LTS")
def from_ubuntu_16_04():
    return _from_ubuntu('xenial', '16.04 LTS (Xenial Xerus)')


@_image_source("Ubuntu 16.10")
def from_ubuntu_16_10():
    return _from_ubuntu('yakkety', '16.10 (Yakkety Yak)')


@_image_source("All Upstream")
def from_all_upstream():
    return chain(
        from_centos6(),
        from_centos_atomic7(),
        from_centos7(),
        from_cirros(),
        from_fedora22(),
        from_fedora23(),
        from_fedora24(),
        from_ubuntu_14_04(),
        from_ubuntu_16_04(),
        from_ubuntu_16_10(),
    )


def top_latest(images, amount=3):
    """Return the most recnt images from given list

    :param Iterable images: A set of remote images
    :param int amount:      How many images to return for each image_name

    :returns: Images are grouped by image_name and the top 'amount' images by
              version and revision are returned
    :rtype: Iterator
    """
    return topbygroup(
        images,
        amount,
        lambda img: img.image_name,
        lambda img: img.version,
    )


@_image_source("Latest Upstream")
def from_all_latest_upstream():
    return top_latest(from_all_upstream())


@_image_source("Missing from oVirt Glance")
def missing_from_ovirt_glance():
    return set(from_all_latest_upstream()) - set(from_ovirt_glance())


@_image_source("Obsolete on oVirt Glance")
def obsolete_on_ovirt_glance():
    glance_all = from_ovirt_glance()
    glance_up_to_date = top_latest(glance_all)
    return set(glance_all) - set(glance_up_to_date)
