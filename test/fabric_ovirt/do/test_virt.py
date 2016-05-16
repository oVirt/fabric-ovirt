#!/usr/bin/env python
"""Unit tests for do.virt.* tasks"""
import mock
import pytest
from textwrap import dedent
from fabric.state import env

from fabric_ovirt.lib.mockups import (
    FabricMock, open_mockup
)

from fabric_ovirt.do.virt import customize, check_command_file


def mk_fake_remote_tempfile_object(directory=False, source=None):
    obj = mock.Mock(spec=('directory', 'name'))
    obj.directory = directory
    obj.name = 'remote:'
    return obj


@mock.patch(
    'fabric_ovirt.do.virt.RemoteTempfile',
    autospec=True,
    side_effect=mk_fake_remote_tempfile_object,
)
@open_mockup({
    'commands.file': dedent(
        """
        write /tgt/file:data
        commands-from-file dir/included.file
        commands-from-shell \\
            echo root-password random
        run /some/script.sh
        """
    ).lstrip(),
    'dir/included.file': dedent(
        """
        upload /some/data.dat:/var/lib/data.dat
        upload relative/more_data.dat:/var/lib/more_data.dat
        """
    ).lstrip(),
})
@mock.patch('fabric_ovirt.do.virt.put', new_callable=FabricMock)
@mock.patch('fabric_ovirt.do.virt.run', new_callable=FabricMock)
def test_customize(fake_run, fake_put, fake_open, fake_remote_templfile):
    env.host_string = 'user@host.example.com'
    customize(add='some-disk.img', commands_from_file='commands.file')
    print(fake_remote_templfile.call_args_list)
    print(fake_put.call_args_list)
    print(fake_run.call_args_list)
    command = fake_run.call_args[0][0]
    sent_files = set(
        args[1]['local_path'] for args in fake_put.call_args_list
    )
    expected_command = ' '.join((
        "virt-customize --add some-disk.img",
        "--write /tgt/file:data",
        "--upload remote:/data.dat:/var/lib/data.dat",
        "--upload remote:/more_data.dat:/var/lib/more_data.dat",
        "--root-password random",
        "--run remote:/script.sh",
    ))
    expected_files = set((
        '/some/data.dat', 'dir/relative/more_data.dat', '/some/script.sh'
    ))
    assert expected_command == command
    assert expected_files == sent_files


@mock.patch('fabric_ovirt.do.virt.abort', side_effect=RuntimeError)
def test_customize_errors(abort_mockup):
    with pytest.raises(RuntimeError):
        customize()
    assert abort_mockup.called


@open_mockup({
    'commands.file': dedent(
        """
        # some command file

        write /tgt/file:data\\
        more data\\
        even more data
        commands-from-file dir/included.file
        commands-from-shell \\
            echo root-password password:$ROOT_PWD
        run /some/script.sh
        selinux-relabel
        """
    ).lstrip(),
    'dir/included.file': dedent(
        """
        upload /some/data.dat:/var/lib/data.dat
        """
    ).lstrip(),
})
@mock.patch('fabric_ovirt.do.virt.puts')
@mock.patch('fabric_ovirt.do.virt.exists', return_value=True)
def test_check_command_file(fake_exists, fake_puts, fake_open, monkeypatch):
    monkeypatch.setenv('ROOT_PWD', 'some-password')
    check_command_file(cmd_file='commands.file')
    result = tuple(args[0][0] for args in fake_puts.call_args_list)
    expected = (
        '# some command file',
        '',
        'write /tgt/file:data\\\nmore data\\\neven more data',
        'upload /some/data.dat:/var/lib/data.dat',
        'root-password password:some-password',
        'run /some/script.sh',
        'selinux-relabel',
    )
    assert result == expected
    assert fake_exists.call_count == 2
    assert fake_exists.call_args_list == [
        mock.call('/some/data.dat'), mock.call('/some/script.sh')
    ]


@open_mockup({
    'commands.file': dedent(
        """
        upload /some/data.dat:/var/lib/data.dat
        """
    ).lstrip(),
})
@mock.patch('fabric_ovirt.do.virt.abort')
@mock.patch('fabric_ovirt.do.virt.exists', return_value=False)
def test_check_command_file_errors(fake_exists, fake_abort, fake_open):
    check_command_file(cmd_file='commands.file')
    assert fake_abort.call_count == 1
