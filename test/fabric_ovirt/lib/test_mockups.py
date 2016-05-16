#!/usr/bin/env python
"""test_mockups.py - Testing for testing mockups (confused yet? :P)
"""
import pytest
import mock
import fabric.operations
import fabric.state
import fabric.context_managers

from fabric_ovirt.lib.mockups import (
    FabricMock, open_mockup, mockup_to_fixture
)


@pytest.fixture
def some_cmd():
    return 'some_command --option arg1 arg2'


@pytest.fixture
def some_host():
    return 'some_host.exapmle.com'


@pytest.fixture
def some_other_host():
    return 'some_other_host.exapmle.com'


def test_fabric_mock(some_cmd, some_host, some_other_host):
    with mock.patch(
        'fabric.operations.run',
        new_callable=FabricMock
    ) as mockup:
        fabric.state.env.host_string = some_host
        fabric.operations.run(some_cmd)
        assert mockup.call_count == 1
        assert mockup.call_args == mock.call(some_cmd)
        assert mockup.call_env.host_string == some_host
        with fabric.context_managers.settings(host_string=some_other_host):
            fabric.operations.run(some_cmd, shell=False)
        assert mockup.call_count == 2
        assert mockup.call_args == mock.call(some_cmd, shell=False)
        assert mockup.call_env.host_string == some_other_host
        assert len(mockup.call_env_list) == 2
        assert mockup.call_env_list[0].host_string == some_host
        assert mockup.call_env_list[1].host_string == some_other_host


def test_fabric_mock_reset_mock(some_cmd):
    with mock.patch(
        'fabric.operations.run',
        new_callable=FabricMock
    ) as mockup:
        fabric.operations.run(some_cmd)
        assert mockup.call_count == 1
        assert len(mockup.call_env_list) == 1
        fabric.operations.run(some_cmd)
        assert mockup.call_count == 2
        assert len(mockup.call_env_list) == 2
        mockup.reset_mock()
        assert mockup.call_count == 0
        assert len(mockup.call_env_list) == 0
        fabric.operations.run(some_cmd)
        assert mockup.call_count == 1
        assert len(mockup.call_env_list) == 1


@mock.patch('fabric.operations.put', new_callable=FabricMock)
@mock.patch('fabric.operations.sudo', new_callable=FabricMock)
def test_fabric_mock_from_decorator(sudo_mockup, put_mockup):
    assert isinstance(sudo_mockup, FabricMock)
    assert isinstance(put_mockup, FabricMock)
    assert fabric.operations.sudo is sudo_mockup
    assert fabric.operations.put is put_mockup


def test_fake_open():
    files = {
        'file1.txt': 'file 1 content',
        'file2.txt': 'file 2 content',
    }
    with open_mockup(files):
        for name, content in files.iteritems():
            with open(name) as fd1:
                assert content == fd1.read()
            assert open.call_args == mock.call(name)
            try:
                fd2 = open(name)
                assert content == fd2.read()
            finally:
                fd2.close()
            assert open.call_args == mock.call(name)
        with pytest.raises(IOError) as err:
            open('file3')
        assert err.value.errno == 2
        assert open.call_args == mock.call('file3')
        assert open.call_count == len(files) * 2 + 1


def some_mockup(a1, a2):
    """Dummy function that will be mocked up"""


fixture_to_test = mockup_to_fixture(
    mock.patch(__name__ + '.some_mockup', return_value='some_value')
)


def test_mockup_to_fixture(fixture_to_test):
    result = some_mockup('arg1', 'arg2')
    assert result == 'some_value'
    assert fixture_to_test.call_count == 1
    assert fixture_to_test.call_args == mock.call('arg1', 'arg2')


def test_mockup_to_fixture_not_there():
    result = some_mockup('arg1', 'arg2')
    assert result is None
