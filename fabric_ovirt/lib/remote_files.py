#!/usr/bin/env python
"""remote_files.py - Module for listing and getting remote files
"""
import hashlib
from collections import namedtuple
import requests
from urlparse import urljoin
from tempfile import NamedTemporaryFile


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
    for line in resp.iter_lines():
        digest, file_name = line.split()
        yield RemoteFile(
            name=file_name,
            url=urljoin(digest_file_url, file_name),
            digest=file_digest(hexdigest=digest, algorithm=digest_algo)
        )
