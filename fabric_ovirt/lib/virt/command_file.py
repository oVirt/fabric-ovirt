#!/usr/bin/env python
# virt/command_file.py - Module for handling command files for virt-* tools
#
import re
import os
import itertools as _it
from collections import namedtuple
from subprocess import Popen, PIPE


context = namedtuple('context', ('file', 'line'))
nested_context = namedtuple('nested_context', ('file', 'line', 'context'))
line_in_context = namedtuple('line_in_context', ('line', 'context'))


def add_context(file, lines, nest_in=None, start_at=1):
    """Add context to text lines

    :param str file:        The filename to set to the context
    :param Iterable lines:  A collection of text lines
    :param context nest_in: A context to nest added context in
    :param int start_at:    What line number to assign to the 1st line

    :returns: An Iterator of line_in_context objects
    :rtype: Iterator
    """
    line_counter = _it.count(start_at)
    for line in lines:
        if nest_in is None:
            ctx = context(file=file, line=next(line_counter))
        else:
            ctx = nested_context(
                file=file, line=next(line_counter), context=nest_in
            )
        yield line_in_context(line=line, context=ctx)


def lines_to_statements(lines, escape_char='\\'):
    """Generator that uses newline-escaping to join input lines to statements

    :param Iterable lines:  An interable of neweline-terminated lines in
                            context
    :param str escape_char: (optional) The escape character to use to escape
                            newlines

    :rtype: Iterator
    :returns: An iterator of statements made from input lines with line
              terminators removed and lines with escaped terminators joined
    """
    buffer = ''
    buffer_context = None
    terminator_re = re.compile(
        '({0})?(\n|\r|\r\n)?\Z'.format(re.escape(escape_char))
    )
    for line in lines:
        buffer_context = buffer_context or line.context
        match = terminator_re.search(line.line)
        if match.group(1):
            buffer += line.line[:match.start(0)] + match.group(2)
        else:
            buffer += line.line[:match.start(0)]
            yield line_in_context(buffer, buffer_context)
            buffer = ''
            buffer_context = None


comment = namedtuple('comment', ('text', 'context'))
command = namedtuple('command', ('command', 'params', 'context'))


class VirtSyntaxError(Exception):
    def __init__(self, message, context):
        self.message = message
        self.context = context

    def __str__(self):
        return "{message} in {context.file} ({context.line})".format(
            self.__dict__
        )


def statement_to_comment(sttmt):
    """Convert a statement to a comment object if possible

    Raise a VirtSyntaxError if not

    :param statement sttmt: The statement to convert
    :rtype: comment
    """
    if sttmt.line.startswith('#'):
        return comment(sttmt.line[1:], context=sttmt.context)
    elif sttmt.line == '':
        return comment(sttmt.line, context=sttmt.context)
    else:
        raise VirtSyntaxError('Invalid comment', sttmt.context)


def statement_to_command(sttmt):
    """Convert a statement to a command object if possible

    Raise a VirtSyntaxError if not

    :param statement sttmt: The statement to convert
    :rtype: command
    """
    cmd, sep, args = sttmt.line.partition(' ')
    if not sep:
        args = None
    return command(cmd, args, context=sttmt.context)


def statement_to_object(sttmt):
    """Convert a statement to the syntactic object within it

    :param statement sttmt: The statement to convert
    :returns: A connad or a comment object
    :rtype: objects
    """
    try:
        return statement_to_comment(sttmt)
    except VirtSyntaxError:
        return statement_to_command(sttmt)


def lines_to_ast(
    lines, context_file='<stdin>', context_nest_in=None, context_start_at=1
):
    """Converts lines of text to parsed syntax objects

    :param Iterable lines: Lines of text with commands and comments
    :rtype: Iterator
    """
    statements = lines_to_statements(
        add_context(context_file, lines, context_nest_in, context_start_at)
    )
    for sttmt in statements:
        yield statement_to_object(sttmt)


used_file = namedtuple('used_file', ('path', 'context'))


class CommandWithoutFile(Exception):
    def __init__(self, command):
        self.command = command


COMMANDS_USING_FILES = {
    'upload': re.compile('\A([^:]+):.+\Z'),
    'copy-in': re.compile('\A([^:]+):.+\Z'),
    'firstboot': re.compile('\A(.+)\Z'),
    'password': re.compile('\A[^:]+:(?:locked:)?file:(.*)\Z'),
    'root-password': re.compile('\A(?:locked:)?file:(.*)\Z'),
    'run': re.compile('\A(.+)\Z'),
}


def command_to_used_file(cmd):
    """Converts a command object to the file it uses

    If the connad does not use a file, raises a CommandWithoutFile excpetion
    :param command cmd: The command to Convert
    :rtype: used_file
    """
    file_cmd_spec = COMMANDS_USING_FILES.get(cmd.command)
    if file_cmd_spec is None:
        raise CommandWithoutFile(cmd)
    params_match = file_cmd_spec.match(cmd.params)
    if not params_match:
        raise CommandWithoutFile(cmd)
    return used_file(params_match.group(1), cmd.context)


def set_command_used_file(cmd, path):
    """Set the file path for a file-using command

    If the command does not use a file, raises a CommandWithoutFile excpetion
    :param command cmd: The command to set file to
    :param str path: The file path to set to the command
    :rtype: command
    """
    file_cmd_spec = COMMANDS_USING_FILES.get(cmd.command)
    if file_cmd_spec is None:
        raise CommandWithoutFile(cmd)
    params_match = file_cmd_spec.match(cmd.params)
    if not params_match:
        raise CommandWithoutFile(cmd)
    return command(
        cmd.command,
        cmd.params[:params_match.start(1)]
        + path
        + cmd.params[params_match.end(1):],
        cmd.context,
    )


def ast_to_used_files(ast):
    """Convert a parsed command file AST to a list of used local files

    :param Iterable ast: The ast to convert
    :rtype: Iterator
    """
    for item in ast:
        if not isinstance(item, command):
            continue
        try:
            file_object = command_to_used_file(item)
        except CommandWithoutFile:
            continue
        yield file_object


def swap_ast_used_files(ast, file_map):
    """Swaps used files in AST with results from passing them to given function

    :param Iterable ast: The AST to swap files in
    :param Callable file_map: A function mapping used_file objects to new path
                              strings for them
    :returns: A new AST with the files swapped
    :rtype: Iterator
    """
    for item in ast:
        if not isinstance(item, command):
            yield item
            continue
        try:
            file_object = command_to_used_file(item)
        except CommandWithoutFile:
            yield item
            continue
        yield set_command_used_file(item, file_map(file_object))


def ast_to_command_params(ast):
    """Convert AST to list of parameters to virt-* commands

    :param Iterable ast: The AST to convert to parameters
    :rtype: Iterator
    """
    for item in ast:
        if not isinstance(item, command):
            continue
        yield '--' + item.command
        if item.params is not None:
            yield item.params


def ast_item_to_string(item):
    """Convert an AST item back to the string it was (porbably) made from

    :param object item: The item to convert
    :rtype: str
    """
    if isinstance(item, command):
        if item.params is None:
            return item.command
        else:
            return '{0} {1}'.format(
                item.command,
                item.params.replace('\n', '\\\n')
            )
    elif isinstance(item, comment):
        if item.text:
            return '#{0}'.format(item.text)
        else:
            return ''


def file_to_ast(filename, open_context=None):
    """Reads a file and parses it into an AST

    :param str filename:         The file name to read
    :param context open_context: (Optional a context in which the file is
                                 opened to embed into exceptions
    :rtype: Iterator
    """
    try:
        fd = open(filename)
    except IOError as err:
        if open_context is not None:
            raise VirtSyntaxError(str(err), open_context)
        else:
            raise err
    with fd:
        for item in lines_to_ast(fd, filename):
            yield item


def shell_cmd_to_ast(
    shell_cmd, run_context=context('<stdin>', 1),
    context_file=None, context_start_at=1,
    env_var_prefix='VIRT_COMMAND_',
    shell='/bin/sh',
):
    """Runs a shell command and parse the output to AST

    Whil raise a VirtSyntaxError if the command fails

    :param str shell_cmd:        The shell command to run
    :param context run_context:  A context object whose content will be
                                 exported to the {prefix}FILE and {prefix}LINE
                                 environment variables when the command runs
    :param str env_var_prefix:   The prefix to set to the environment variables
                                 (be default its "VIRT_COMMAND_")
    :param str context_file:     File name to assign to the context of the
                                 generated AST items (by default its
                                 "script<fff (nn)>" where fff and nn are the
                                 name and line number from run_context)
    :param str context_start_at: The number to start from when enumerating
                                 lines from command output
    :param str shell:            The shell to use to interprate the command
    :rtype: Iterator
    """

    cmd_env = os.environ.copy()
    cmd_env.update({
        env_var_prefix + 'FILE': run_context.file,
        env_var_prefix + 'LINE': str(run_context.line),
    })
    if context_file is None:
        context_file = 'script<{0} ({1})>'.format(*run_context)
    shell_pipe = Popen(
        (shell, '-e', '-c', shell_cmd),
        shell=False, env=cmd_env, stdout=PIPE, close_fds=True
    )
    try:
        for item in lines_to_ast(
            shell_pipe.stdout, context_file, run_context, context_start_at
        ):
            yield item
    finally:
        shell_pipe.wait()
        if shell_pipe.returncode != 0:
            raise VirtSyntaxError("Shell command exited with code {0}".format(
                shell_pipe.returncode
            ), run_context)


def find_included_file(given, inc_ctx):
    """Figure out the path to include a file from

    :param str givem:           The path that was specified for the include
    :param context inc_ctx:     The context in which the file was included
    :rtype: str
    :returns: The path of the file to include
    """
    if os.path.isabs(given):
        return given
    while hasattr(inc_ctx, 'context'):
        inc_ctx = inc_ctx.context
    return os.path.join(os.path.dirname(inc_ctx.file), given)


def perform_ast_includes(
    ast,
    file_include_commands=frozenset(('commands-from-file',)),
    shell_exec_commands=frozenset(('commands-from-shell',)),
    parent_includes=frozenset(),
    set_include_dir=None,
):
    """Implement inclusion commands in AST

    The inclusion commands are expected to include a single argument with is a
    file path for file inclusion commands or a shell command for shell
    execution commands

    :param Iterable ast:                    The ast to parse commands from
    :param frozenset file_include_commands: Recognized file inclusion commands
    :param frozenset shell_exec_commands:   Recognized execution commands
    :param frozenset parent_includes:       If a file inclusion command will
                                            attempt to include a file included
                                            in this set an exceptio will be
                                            raised
    :param str set_include_dir:             A string specifying the path to
                                            include files from for when in
                                            cannot be inferred from the context
                                            (e.g. for shell commands)

    parent_includes is used to preved file inclusion loops, inclusion loops can
    still be caused by scripts

    :returns: A new AST with all inclusions performed recusrively
    :rtype: iterator
    """
    for item in ast:
        if not isinstance(item, command):
            yield item
            continue
        if item.command in file_include_commands:
            inc_file = find_included_file(item.params, item.context)
            done_includes = parent_includes.union((item.context.file,))
            if inc_file in done_includes:
                raise VirtSyntaxError('File inclusion loop', item.context)
            for sub_item in perform_ast_includes(
                file_to_ast(inc_file, item.context),
                file_include_commands,
                shell_exec_commands,
                done_includes,
            ):
                yield sub_item
            continue
        if item.command in shell_exec_commands:
            if set_include_dir is not None:
                child_include_dir = set_include_dir
            else:
                child_include_dir = os.path.dirname(item.context.file)
            for sub_item in perform_ast_includes(
                shell_cmd_to_ast(item.params, item.context),
                file_include_commands,
                shell_exec_commands,
                parent_includes.union((item.context.file,)),
                child_include_dir,
            ):
                yield sub_item
            continue
        yield item
