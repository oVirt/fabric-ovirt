#!/usr/bin/env python
"""test_remote_tempfile.py - Tests for fabric_ovirt.lib.remote_tempfile
"""
import mock
import pytest
import os.path
from fabric.state import env
from fabric.context_managers import settings

from fabric_ovirt.lib.mockups import FabricMock
from fabric_ovirt.lib.remote_tempfile import (
    mktemp, RemoteTempfileError, RemoteTempfile,
)


@pytest.fixture
def tmp_file_name():
    return 'tmpfile.tmp'


@pytest.fixture
def host_name():
    return 'host.example.com'


@pytest.fixture
def upload_file_name():
    return 'upload.file'


@pytest.fixture
def failed_upload_file_name():
    return 'failed_upload.file'


@pytest.fixture
def upload_dir_name(monkeypatch):
    dir_name = 'upload.directory'

    def fake_isdir(some_dir):
        return (some_dir == dir_name)

    monkeypatch.setattr(os.path, 'isdir', fake_isdir)
    return dir_name


@pytest.fixture
def fabric_mockup(request, tmp_file_name, failed_upload_file_name):
    """Patch multipile fabric operations with the settings we need"""
    def put_mockup(*args, **kwargs):
        if kwargs['local_path'] == failed_upload_file_name:
            return mock.MagicMock(
                succeeded=False, failed=[failed_upload_file_name]
            )
        else:
            return mock.MagicMock(succeeded=True, failed=[])

    patchers = (
        mock.patch(
            'fabric_ovirt.lib.remote_tempfile.run',
            return_value=tmp_file_name,
            new_callable=FabricMock,
        ),
        mock.patch(
            'fabric_ovirt.lib.remote_tempfile.put',
            side_effect=put_mockup,
            new_callable=FabricMock,
        ),
    )

    def finalizer():
        for patcher in reversed(patchers):
            patcher.stop()

    request.addfinalizer(finalizer)

    mockup = mock.NonCallableMock(spec=('run', 'put'))
    mockup.attach_mock(patchers[0].start(), 'run')
    mockup.attach_mock(patchers[1].start(), 'put')
    return mockup


def test_mktemp(fabric_mockup, tmp_file_name):
    result = mktemp()
    assert tmp_file_name == result
    assert 1 == fabric_mockup.run.call_count
    assert fabric_mockup.run.call_args == mock.call(
        'mktemp', shell=False
    )
    fabric_mockup.reset_mock()
    result == mktemp(True)
    assert tmp_file_name == result
    assert 1 == fabric_mockup.run.call_count
    assert fabric_mockup.run.call_args == mock.call(
        'mktemp -d', shell=False
    )


class TestRemoteTempfile(object):
    def test_init(self, fabric_mockup, tmp_file_name, host_name):
        env.host_string = host_name
        rtf = RemoteTempfile()
        assert rtf.directory is False
        assert tmp_file_name == rtf.name
        assert 1 == fabric_mockup.run.call_count
        assert fabric_mockup.run.call_args == mock.call(
            'mktemp', shell=False
        )
        env.host_string = '--dummy--'
        assert host_name != env.host_string
        assert host_name == fabric_mockup.run.call_env.host_string

    def test_init_directory(self, fabric_mockup, tmp_file_name, host_name):
        env.host_string = host_name
        rtf = RemoteTempfile(directory=True)
        assert rtf.directory is True
        assert tmp_file_name == rtf.name
        assert 1 == fabric_mockup.run.call_count
        assert fabric_mockup.run.call_args == mock.call(
            'mktemp -d', shell=False
        )
        env.host_string = '--dummy--'
        assert host_name != env.host_string
        assert host_name == fabric_mockup.run.call_env.host_string

    def test_rm(self, fabric_mockup, tmp_file_name, host_name):
        env.host_string = '--dummy--'
        assert host_name != env.host_string
        with settings(host_string=host_name):
            rtf = RemoteTempfile()
            assert 1 == fabric_mockup.run.call_count
            assert host_name == fabric_mockup.run.call_env.host_string
        assert host_name != env.host_string
        fabric_mockup.reset_mock()
        rtf.rm()
        assert 1 == fabric_mockup.run.call_count
        assert fabric_mockup.run.call_args == mock.call(
            "rm -rf {0}".format(tmp_file_name), shell=True
        )
        assert host_name == fabric_mockup.run.call_env.host_string
        with pytest.raises(RemoteTempfileError):
            rtf.rm()
        with pytest.raises(RemoteTempfileError):
            rtf.directory
        with pytest.raises(RemoteTempfileError):
            rtf.name

    def test_raii(self, fabric_mockup, tmp_file_name):
        env.host_string = host_name
        rtf = RemoteTempfile()
        assert 1 == fabric_mockup.run.call_count
        del(rtf)
        assert 2 == fabric_mockup.run.call_count
        assert fabric_mockup.run.call_args == mock.call(
            "rm -rf {0}".format(tmp_file_name), shell=True
        )

    def test_context(self, fabric_mockup, tmp_file_name):
        with RemoteTempfile() as rtf:
            assert tmp_file_name == rtf.name
            assert 1 == fabric_mockup.run.call_count
        assert 2 == fabric_mockup.run.call_count
        assert fabric_mockup.run.call_args == mock.call(
            "rm -rf {0}".format(tmp_file_name), shell=True
        )

    def test_file_upload(self, fabric_mockup, upload_file_name, tmp_file_name):
        with RemoteTempfile(source=upload_file_name):
            assert 1 == fabric_mockup.put.call_count
            assert fabric_mockup.put.call_args == mock.call(
                local_path=upload_file_name,
                remote_path=tmp_file_name
            )

    def test_failed_file_upload(
        self, fabric_mockup, failed_upload_file_name, tmp_file_name
    ):
        with pytest.raises(RemoteTempfileError):
            RemoteTempfile(source=failed_upload_file_name)

    def test_dir_upload(self, fabric_mockup, upload_dir_name, tmp_file_name):
        with RemoteTempfile(source=upload_dir_name, directory=True) as rtf:
            assert rtf.directory is True
            assert 1 == fabric_mockup.put.call_count
            assert fabric_mockup.put.call_args == mock.call(
                local_path=upload_dir_name + '/.',
                remote_path=tmp_file_name
            )
        fabric_mockup.reset_mock()
        with RemoteTempfile(source=upload_dir_name, directory=False) as rtf:
            assert rtf.directory is True
            assert 1 == fabric_mockup.put.call_count
            print(fabric_mockup.put.call_args)
            assert fabric_mockup.put.call_args == mock.call(
                local_path=upload_dir_name + '/.',
                remote_path=tmp_file_name
            )
