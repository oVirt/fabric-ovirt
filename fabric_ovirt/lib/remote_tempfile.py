#!/usr/bin/env python
"""remote_tempfile.py - Manage remote temporary files via Fabric
"""
import os.path
from fabric.state import env
from fabric.operations import run, put
from fabric.context_managers import settings, hide

from fabric_ovirt.lib.shell_cmd import quote_and_join


def mktemp(directory=False):
    """Creates a remote temporary file

    :param boolean directory: True if directory is to be created rather then a
                              file
    :returns: The name of the file created
    :rtype: str
    """
    mktemp_cmd = ['mktemp']
    if directory:
        mktemp_cmd.append('-d')
    with hide('running', 'stdout'):
        tmpfile = run(' '.join(mktemp_cmd), shell=False)
    return tmpfile


class RemoteTempfileError(Exception):
    """Raised when an error occurs with a remote temporary file"""


class RemoteTempfile(object):
    """Creates a temporary file and removes it when the instance dies

    Instances can also be used as context managers.
    """
    def __init__(self, directory=False, source=None):
        """Creates a remote temporary file

        :param boolean directory: True if directory is to be created rather
                                  then a file
        :param str source:        A local file or directory path to be copied
                                  to the remote location

        If 'source' id given then 'directory' is ignored and determined by the
        source file instead
        """
        self._directory = bool(directory)
        self._host_string = env.host_string
        self._name = mktemp(directory)
        if source is not None:
            self._directory = os.path.isdir(os.path.expanduser(source))
            if self._directory:
                source = os.path.join(source, '.')
            with hide('running', 'stdout'):
                put_result = put(local_path=source, remote_path=self.name)
            if put_result.failed:
                raise RemoteTempfileError('Failed to upload files')

    @property
    def directory(self):
        self._check_not_removed()
        return self._directory

    @property
    def name(self):
        self._check_not_removed()
        return self._name

    def rm(self):
        """Delete the remote tempfile"""
        self._check_not_removed()
        with settings(
            hide('running', 'stdout'),
            host_string=self._host_string
        ):
            run(quote_and_join('rm', '-rf', self._name), shell=True)
        self._name = None

    def __del__(self):
        try:
            self.rm()
        except RemoteTempfileError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.rm()

    def _check_not_removed(self):
        if self._name is None:
            raise RemoteTempfileError("RemoteTempfile was already removed")
