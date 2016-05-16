#!/usr/bin/env python
# test_command_file.py - Teasting for virt.command_file module
#
import __builtin__
import os
import itertools as _it
from StringIO import StringIO
from contextlib import contextmanager
from textwrap import dedent
import pytest

from fabric_ovirt.lib.virt.command_file import (
    lines_to_statements, context, nested_context, line_in_context, add_context,
    comment, command, VirtSyntaxError, statement_to_comment,
    statement_to_command, statement_to_object, lines_to_ast, used_file,
    CommandWithoutFile, command_to_used_file, set_command_used_file,
    ast_to_used_files, swap_ast_used_files, ast_to_command_params,
    ast_item_to_string, file_to_ast, shell_cmd_to_ast, find_included_file,
    perform_ast_includes
)


@pytest.fixture
def file_name():
    return 'some_file1'


@pytest.fixture
def file_path():
    return 'some_dir/some_file1'


@pytest.fixture
def context_gen(file_name):
    def gen_func(i):
        return context(file=file_name, line=i)
    return gen_func


@pytest.fixture
def some_context(context_gen):
    return context_gen(84)


def test_context(file_name):
    ctx = context(file=file_name, line=68)
    assert ctx.file == file_name
    assert ctx.line == 68
    ctx = context(file_name, 68)
    assert ctx.file == file_name
    assert ctx.line == 68


def test_nested_context(file_name, some_context):
    ctx = nested_context(file=file_name, line=68, context=some_context)
    assert ctx.file == file_name
    assert ctx.line == 68
    assert ctx.context == some_context
    ctx = nested_context(file_name, 68, some_context)
    assert ctx.file == file_name
    assert ctx.line == 68
    assert ctx.context == some_context


def test_line_in_context(file_name):
    line = line_in_context(
        line='a simple line of text',
        context=context(file=file_name, line=45),
    )
    assert line.context.file == file_name
    assert line.context.line == 45
    assert line.line == 'a simple line of text'
    line = line_in_context('a simple line of text', context(file_name, 45))
    assert line.context.file == file_name
    assert line.context.line == 45
    assert line.line == 'a simple line of text'


def test_add_context(file_name):
    lines = (
        'line1',
        'line2',
        'line3',
    )
    expected = (
        line_in_context(context=context(file=file_name, line=1), line='line1'),
        line_in_context(context=context(file=file_name, line=2), line='line2'),
        line_in_context(context=context(file=file_name, line=3), line='line3'),
    )
    result = tuple(add_context(file=file_name, lines=lines))
    assert expected == result


def test_add_context_nested(file_name, some_context):
    lines = (
        'line1',
        'line2',
        'line3',
    )
    ctx = (
        nested_context(file_name, cnt, some_context) for cnt in _it.count(1)
    )
    expected = (
        line_in_context(context=next(ctx), line='line1'),
        line_in_context(context=next(ctx), line='line2'),
        line_in_context(context=next(ctx), line='line3'),
    )
    result = tuple(
        add_context(file=file_name, lines=lines, nest_in=some_context)
    )
    assert expected == result


def test_lines_to_statements(file_name):
    lines = add_context(file=file_name, lines=(
        'line1\n',
        '  line2  \n',
        'line3 part1\\\n',
        'line3 part2\n',
        'line \\ number 4\n',
        'line5 part1\\\n',
        '  line5\\ part2\\\n',
        'line5 part3\n',
        'line6',
    ))
    expected = (
        line_in_context('line1', context(file_name, 1)),
        line_in_context('  line2  ', context(file_name, 2)),
        line_in_context('line3 part1\nline3 part2', context(file_name, 3)),
        line_in_context('line \\ number 4', context(file_name, 5)),
        line_in_context(
            'line5 part1\n  line5\\ part2\nline5 part3',
            context(file_name, 6)
        ),
        line_in_context('line6', context(file_name, 9)),
    )
    result = tuple(lines_to_statements(lines))
    assert expected == result


def test_comment(some_context):
    txt = 'some comment text'
    cmnt = comment(text=txt, context=some_context)
    assert cmnt.text == txt
    assert cmnt.context == some_context
    cmnt = comment(txt, some_context)
    assert cmnt.text == txt
    assert cmnt.context == some_context


def test_command(some_context):
    cmd = command(
        command='some_command', params='some_params', context=some_context
    )
    assert cmd.command == 'some_command'
    assert cmd.params == 'some_params'
    assert cmd.context == some_context
    cmd = command('some_command', 'some_params', some_context)
    assert cmd.command == 'some_command'
    assert cmd.params == 'some_params'
    assert cmd.context == some_context


def test_statement_to_comment(context_gen):
    comment_statments = (
        line_in_context('# a comment line', context_gen(1)),
        line_in_context('#', context_gen(2)),
        line_in_context('', context_gen(3)),
    )
    expected_objects = (
        comment(' a comment line', context_gen(1)),
        comment('', context_gen(2)),
        comment('', context_gen(3)),
    )
    for sttmt, expected in _it.izip(comment_statments, expected_objects):
        result = statement_to_comment(sttmt)
        assert expected == result

    bad_statements = (
        line_in_context('  # indented comment', context_gen(4)),
        line_in_context('command arg1:arg2', context_gen(5)),
        line_in_context('command', context_gen(6)),
        line_in_context('command args  # not a comment', context_gen(7)),
    )
    exception_contexts = tuple(context_gen(i) for i in range(4, 8))
    for sttmt, exp_ctx in _it.izip(bad_statements, exception_contexts):
        with pytest.raises(VirtSyntaxError) as err:
            statement_to_comment(sttmt)
        assert exp_ctx == err.value.context


def test_statement_to_command(context_gen):
    command_statements = (
        line_in_context(' # indented comment', context_gen(1)),
        line_in_context('command arg1:arg2', context_gen(2)),
        line_in_context('command ', context_gen(3)),
        line_in_context('command', context_gen(4)),
        line_in_context('command   args  # not a comment', context_gen(5)),
    )
    expected_objects = (
        command('', '# indented comment', context_gen(1)),
        command('command', 'arg1:arg2', context_gen(2)),
        command('command', '', context_gen(3)),
        command('command', None, context_gen(4)),
        command('command', '  args  # not a comment', context_gen(5)),
    )
    for sttmt, expected in _it.izip(command_statements, expected_objects):
        result = statement_to_command(sttmt)
        assert expected == result


def test_statement_to_object(file_name):
    statements = add_context(file_name, (
        '# some comment',
        'a_command with:args',
    ))
    expected_objects = (
        comment(' some comment', context(file_name, 1)),
        command('a_command', 'with:args', context(file_name, 2)),
    )
    for sttmt, expected in _it.izip(statements, expected_objects):
        result = statement_to_object(sttmt)
        assert expected == result


def test_lines_to_ast(file_name):
    lines = (
        '# some comment\n',
        'a_command with:multi\\\n',
        'line args\n',
        'a_command with:args\n',
    )
    expected = (
        comment(' some comment', context(file_name, 7)),
        command('a_command', 'with:multi\nline args', context(file_name, 8)),
        command('a_command', 'with:args', context(file_name, 10)),
    )
    result = tuple(
        lines_to_ast(lines, context_file=file_name, context_start_at=7)
    )
    assert expected == result


def test_used_file(file_name, some_context):
    ufile = used_file(path=file_name, context=some_context)
    assert ufile.path == file_name
    assert ufile.context == some_context
    ufile = used_file(file_name, some_context)
    assert ufile.path == file_name
    assert ufile.context == some_context


def test_command_to_used_file(file_name):
    commands = lines_to_ast((
        'upload /copied/file:/dst/path',
        'copy-in /copyed/dir:/dst/dir',
        'firstboot /some/fb.script',
        'password user:file:/user/pwd/file',
        'password user:locked:file:/user/pwd/file',
        'root-password file:/root/pwd/file',
        'root-password locked:file:/root/pwd/file',
        'run /some/script',
    ), context_file=file_name)
    file_names = (
        '/copied/file',
        '/copyed/dir',
        '/some/fb.script',
        '/user/pwd/file',
        '/user/pwd/file',
        '/root/pwd/file',
        '/root/pwd/file',
        '/some/script',
    )
    for cmd, fname in _it.izip(commands, file_names):
        expected = used_file(fname, cmd.context)
        result = command_to_used_file(cmd)
        assert expected == result

    no_file_commands = lines_to_ast((
        'chmod 0755:/some/vm/file',
        'delete /some/vm/file',
        'copy /some/vm/file:/some/othr/vm.file',
        'password user:password:/user/pwd/file',
        'password user:locked:password:/user/pwd/file',
        'root-password password:/root/pwd/file',
        'root-password locked:password:/root/pwd/file',
    ))
    for cmd in no_file_commands:
        with pytest.raises(CommandWithoutFile) as err:
            command_to_used_file(cmd)
        assert cmd == err.value.command


def test_set_command_used_file(file_name):
    commands = lines_to_ast((
        'upload /copied/file:/dst/path',
        'copy-in /copyed/dir:/dst/dir',
        'firstboot /some/fb.script',
        'password user:file:/user/pwd/file',
        'password user:locked:file:/user/pwd/file',
        'root-password file:/root/pwd/file',
        'root-password locked:file:/root/pwd/file',
        'run /some/script',
    ), context_file=file_name)
    new_commands = lines_to_ast((
        'upload /replaced/path:/dst/path',
        'copy-in /replaced/path:/dst/dir',
        'firstboot /replaced/path',
        'password user:file:/replaced/path',
        'password user:locked:file:/replaced/path',
        'root-password file:/replaced/path',
        'root-password locked:file:/replaced/path',
        'run /replaced/path',
    ), context_file=file_name)
    for cmd, expected in _it.izip(commands, new_commands):
        result = set_command_used_file(cmd, '/replaced/path')
        assert expected == result

    no_file_commands = lines_to_ast((
        'chmod 0755:/some/vm/file',
        'delete /some/vm/file',
        'password user:password:/user/pwd/file',
        'password user:locked:password:/user/pwd/file',
        'root-password password:/root/pwd/file',
        'root-password locked:password:/root/pwd/file',
    ))
    for cmd in no_file_commands:
        with pytest.raises(CommandWithoutFile) as err:
            set_command_used_file(cmd, '/replaced/path')
        assert cmd == err.value.command


def test_ast_to_used_files(file_name):
    ast = lines_to_ast((
        '# some comment',
        'run /some/script',
        'copy-in /copyed/dir:/dst/dir',
        'install sopme-pkg',
        '',
        'root-password file:/root/pwd/file',
    ), context_file=file_name)
    expected = (
        used_file('/some/script', context(file_name, 2)),
        used_file('/copyed/dir', context(file_name, 3)),
        used_file('/root/pwd/file', context(file_name, 6)),
    )
    result = tuple(ast_to_used_files(ast))
    assert expected == result


def test_swap_ast_used_files(file_name):
    ast = lines_to_ast((
        '# some comment',
        'run /some/script',
        'copy-in /copyed/dir:/dst/dir',
        'install sopme-pkg',
        '',
        'root-password file:/root/pwd/file',
    ), context_file=file_name)
    expected = tuple(lines_to_ast((
        '# some comment',
        'run /remote/prefix/some/script',
        'copy-in /remote/prefix/copyed/dir:/dst/dir',
        'install sopme-pkg',
        '',
        'root-password file:/remote/prefix/root/pwd/file',
    ), context_file=file_name))

    def file_map_func(file_object):
        return '/remote/prefix' + file_object.path

    result = tuple(swap_ast_used_files(ast, file_map_func))
    assert expected == result


def test_ast_to_command_params():
    ast = lines_to_ast((
        '# some comment',
        'run /some/script',
        'copy-in /copyed/dir:/dst/dir',
        'install sopme-pkg',
        'selinux-relabel',
    ))
    expected = (
        '--run', '/some/script',
        '--copy-in', '/copyed/dir:/dst/dir',
        '--install', 'sopme-pkg',
        '--selinux-relabel',
    )
    result = tuple(ast_to_command_params(ast))
    assert expected == result


def test_ast_item_to_string():
    strings = (
        '# some command file',
        '',
        'write /tgt/file:data\\\nmore data\\\neven more data',
        'copy /some/data.dat:/var/lib/data.dat',
        'root-password password:some-password',
        'run /some/script.sh',
    )
    for string in strings:
        items = tuple(lines_to_ast(StringIO(string + '\n')))
        assert len(items) == 1
        item = items[0]
        assert ast_item_to_string(item) == string


@pytest.fixture
def fake_open(monkeypatch):
    class CTXStringIO(StringIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    @contextmanager
    def open_faker(file_dict):
        file_dict = file_dict.copy()

        def _open(name, mode=None, buffering=None):
            content = file_dict.get(
                name,
                IOError(2, "No such file or directory: '{0}'".format(name))
            )
            if isinstance(content, BaseException):
                raise content
            return CTXStringIO(content)
        monkeypatch.setattr(__builtin__, 'open', _open)
        try:
            yield
        finally:
            monkeypatch.undo()

    return open_faker


def test_fake_open(fake_open):
    files = {
        'file1.txt': 'file 1 content',
        'file2.txt': 'file 2 content',
    }
    with fake_open(files):
        for name, content in files.iteritems():
            with open(name) as fd1:
                assert content == fd1.read()
            try:
                fd2 = open(name)
                assert content == fd2.read()
            finally:
                fd2.close()
        with pytest.raises(IOError) as err:
            open('file3')
        assert err.value.errno == 2


def test_file_to_ast(fake_open, file_name):
    lines = (
        '# comment\n',
        'command arg1:arg2\n',
    )
    expected = tuple(lines_to_ast(lines, file_name))
    with fake_open({file_name: ''.join(lines)}):
        result = tuple(file_to_ast(file_name))
    assert expected == result


def test_shell_cmd_to_ast(some_context):
    script = """
        # shell comment
        echo '# ast comment'
        echo ast_command arg1:arg2:arg3
        echo given_file_is "$VIRT_COMMAND_FILE"
        echo given_line_is "$VIRT_COMMAND_LINE"
    """
    expected = tuple(lines_to_ast(
        (
            '# ast comment',
            'ast_command arg1:arg2:arg3',
            'given_file_is {0}'.format(some_context.file),
            'given_line_is {0}'.format(some_context.line),
        ),
        context_file='script<{0} ({1})>'.format(*some_context),
        context_nest_in=some_context,
    ))
    os.environ['VIRT_COMMAND_FILE'] = 'was_not_changed'
    os.environ['VIRT_COMMAND_LINE'] = 'not_changed_either'
    result = tuple(shell_cmd_to_ast(script, run_context=some_context))
    assert expected == result
    assert os.environ['VIRT_COMMAND_FILE'] == 'was_not_changed'
    assert os.environ['VIRT_COMMAND_LINE'] == 'not_changed_either'


def test_shell_cmd_to_ast_errors(some_context):
    with pytest.raises(VirtSyntaxError) as err:
        tuple(shell_cmd_to_ast('false\n', some_context))
    assert some_context == err.value.context
    with pytest.raises(VirtSyntaxError) as err:
        tuple(shell_cmd_to_ast('false\ntrue\n', some_context))
    assert some_context == err.value.context


@pytest.mark.parametrize(
    ('given', 'inc_ctx', 'expected'),
    [
        ('/abs/inc', None, '/abs/inc'),
        ('/abs/inc', context('foo', 1), '/abs/inc'),
        ('/abs/inc', nested_context('bar', 1, context('foo', 1)), '/abs/inc'),
        ('inc', context('parent', 1), 'inc'),
        ('inc', context('dir/parent', 1), 'dir/inc'),
        ('inc', nested_context('bar', 1, context('f', 1)), 'inc'),
        ('inc', nested_context('bar', 1, context('hdir/f', 1)), 'hdir/inc'),
    ]
)
def test_find_included_file(given, inc_ctx, expected):
    result = find_included_file(given, inc_ctx)
    assert expected == result


def test_perform_ast_includes(file_name, fake_open):
    files = {
        'file1.inc': dedent(
            """
            run /file1/arg1
            write /file1/arg2:long\\
            input
            """
        ).lstrip(),
        'incdir/file2.inc': dedent(
            """
            # file2 comment
            run /file2/script
            commands-from-file file3.inc
            commands-from-shell \\
                echo "# shell ctx: $VIRT_COMMAND_FILE ($VIRT_COMMAND_LINE)" \\
                echo "root-password password:foo"
            write /last/file2:command
            """
        ).lstrip(),
        'incdir/file3.inc': dedent(
            """
            # file3 comment
            run file3_command
            """
        ).lstrip(),
        'file4': dedent(
            """
            # will be included from script
            """
        ).lstrip(),
    }
    ast = lines_to_ast(StringIO(dedent(
        """
        # The main AST
        commands-from-file file1.inc
        commands-from-file incdir/file2.inc
        commands-from-shell \\
            echo "# shell comment" \\
            echo commands-from-file file4
        selinux-relabel
        """
    ).lstrip()), context_file=file_name)
    expected = (
        comment(' The main AST', context(file_name, 1)),
        # commands-from-file file1.inc
        command('run', '/file1/arg1', context('file1.inc', 1)),
        command('write', '/file1/arg2:long\ninput', context('file1.inc', 2)),
        # commands-from-file file2.inc
        comment(' file2 comment', context('incdir/file2.inc', 1)),
        command('run', '/file2/script', context('incdir/file2.inc', 2)),
        # commands-from-file file3.inc (in file2)
        comment(' file3 comment', context('incdir/file3.inc', 1)),
        command('run', 'file3_command', context('incdir/file3.inc', 2)),
        # commands-from-shell (in file2)
        comment(
            " shell ctx: incdir/file2.inc (4)",
            nested_context(
                'script<incdir/file2.inc (4)>', 1,
                context('incdir/file2.inc', 4)
            )
        ),
        command(
            'root-password', 'password:foo',
            nested_context(
                'script<incdir/file2.inc (4)>', 2,
                context('incdir/file2.inc', 4)
            )
        ),
        # back to file2
        command(
            'write', '/last/file2:command',
            context('incdir/file2.inc', 7)
        ),
        # commands-from-shell (in main ast)
        comment(
            " shell comment",
            nested_context(
                'script<{0} (4)>'.format(file_name), 1,
                context(file_name, 4)
            ),
        ),
        # commands-from-file file4
        comment(' will be included from script', context('file4', 1)),
        # back to main
        command('selinux-relabel', None, context(file_name, 7)),
    )
    with fake_open(files):
        result = tuple(perform_ast_includes(ast))
    assert expected == result


def test_perform_ast_include_errors(file_name, fake_open):
    files = {
        'missing.inc': dedent(
            """
            run just_a_command
            commands-from-file really_missing.inc
            """
        ).lstrip(),
        'simple_loop': dedent(
            """
            # a simple include loop
            commands-from-file simple_loop
            """
        ).lstrip(),
        'nested_loop1': dedent(
            """
            # a nested include loop file 1
            commands-from-file nested_loop2
            """
        ).lstrip(),
        'nested_loop2': dedent(
            """
            # a nested include loop file 2
            commands-from-file nested_loop1
            """
        ).lstrip(),
        'script_nested_loop1': dedent(
            """
            # a nested loop via script file 1
            commands-from-shell \
              echo commands-from-file script_nested_loop2
            """
        ).lstrip(),
        'script_nested_loop2': dedent(
            """
            # a nested lopp via script file 2
            commands-from-file script_nested_loop1
            """
        ).lstrip(),
    }
    asts_contexts = (
        (
            lines_to_ast(
                StringIO('commands-from-file simple_missing.inc'),
                file_name
            ),
            context(file_name, 1),
        ),
        (
            lines_to_ast(StringIO('commands-from-file missing.inc')),
            context('missing.inc', 2),
        ),
        (
            lines_to_ast(StringIO('commands-from-file simple_loop')),
            context('simple_loop', 2),
        ),
        (
            lines_to_ast(StringIO('commands-from-file nested_loop1')),
            context('nested_loop2', 2),
        ),
        (
            lines_to_ast(StringIO('commands-from-file script_nested_loop1')),
            context('script_nested_loop2', 2),
        ),
    )
    for ast, ctx in asts_contexts:
        with pytest.raises(VirtSyntaxError) as err:
            with fake_open(files):
                t = tuple(perform_ast_includes(ast))
                print(t)
        assert ctx == err.value.context
