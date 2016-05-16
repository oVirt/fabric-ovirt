#!/usr/bin/env python
# encoding: utf-8
#
from itertools import chain
from fabric.api import task
from fabric.utils import abort, puts
from fabric.operations import run, put
from os.path import exists, expanduser, join, basename

from fabric_ovirt.lib.virt.command_file import (
    file_to_ast, perform_ast_includes, ast_to_used_files, swap_ast_used_files,
    ast_to_command_params, find_included_file, ast_item_to_string,
)
from fabric_ovirt.lib.shell_cmd import quote_and_join, dict_to_opts
from fabric_ovirt.lib.remote_tempfile import RemoteTempfile


@task
def customize(**kwargs):
    """Run virt-customize on the remote host

    All keyword arguments to this command are converted to command line
    arguments for virt-customize by converting underscores (_) to hyphens (-)
    and prepending double hyphens (--). This means that single-character flags
    will most probably not work.
    Two of the arguments maintain their original meaning but get special
    treatment:

    :param str add:                Specifying this argument is mandatory as the
                                   command is pretty useless without it
    :param str commands_from_file: This argument is meant to refer to a local
                                   file. The file is parsed, and its content is
                                   converted into arguments for the remote
                                   virt-customize command.

    Any files referred to by the local command file are either uploaded to the
    remote host (With the command arguments adjusted to point to the right
    remote file locations) or parsed locally and converted to arguments in case
    they are referred to by a 'commands-from-file' command. The
    'commands-from-shell' command can also be used in the command files to
    embed some locally-executed shell logic to generate more complex commands.
    See the fabric_ci.lib.virt.command_file.perform_ast_includes for full
    details of inclusion logic.
    """
    remote_files = []

    def file_map(local_file):
        """Upload local file to remote location and calculate remote name"""
        tmpfile = RemoteTempfile(directory=True)
        local_path = find_included_file(local_file.path, local_file.context)
        put(local_path=local_path, remote_path=tmpfile.name)
        remote_files.append(tmpfile)
        return join(tmpfile.name, basename(local_path))

    if 'add' not in kwargs:
        abort("The 'add' parameter must be specified")
    if 'commands_from_file' in kwargs:
        commands_from_file = expanduser(kwargs.pop('commands_from_file'))
        args_from_file = ast_to_command_params(swap_ast_used_files(
            perform_ast_includes(file_to_ast(commands_from_file)),
            file_map
        ))
    else:
        args_from_file = ()
    run(quote_and_join('virt-customize', *tuple(chain(
        dict_to_opts(kwargs), args_from_file
    ))))


@task
def check_command_file(cmd_file):
    """Helper tool to writing complex virt-* command files

    Read the given command file, attempt to perform all file inclusions and
    emdebbed script execution and yeild the resulting composit command file

    :param str cmd_file: The command file to check
    """
    ast = tuple(perform_ast_includes(file_to_ast(expanduser(cmd_file))))
    for used_file in ast_to_used_files(ast):
        used_file_path = find_included_file(used_file.path, used_file.context)
        if not exists(used_file_path):
            abort('File "{0}" included from "{1}" line {2} not found!'.format(
                used_file.path, used_file.context.file, used_file.context.line
            ))
    for item in ast:
        puts(ast_item_to_string(item))
