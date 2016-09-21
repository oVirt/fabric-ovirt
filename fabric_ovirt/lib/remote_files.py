#!/usr/bin/env python
"""remote_files.py - Module for listing and getting remote files
"""
import hashlib
from collections import namedtuple
import requests
from urlparse import urljoin


file_digest = namedtuple('file_digest', ('hexdigest', 'algorithem'))


class RemoteFile(object):
    """Represents a file on a remote location

    :param str name:           The name of the remote file
    :param str url:            The URL of the remote file
    :param file_digest digest: (Optional) The digest value for the file and the
                               algorithem used to verify it
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


def from_http_with_digest_file(digest_file_url, digest_algo=hashlib.sha256):
    """List files in a remote HTTP directory that includes a hash digest file

    :param str digest_file_url:  The url of the file that lists the files in
                                 the same directory and their hashes
    :param Callable digest_algo: The algorithem used to generate the hashes in
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
            digest=file_digest(hexdigest=digest, algorithem=digest_algo)
        )
