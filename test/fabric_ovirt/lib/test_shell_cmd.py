#!/usr/bin/env python
"""test_shell_cmd.py - Tests for shell_cmd.py
"""
import pytest
from collections import OrderedDict

from fabric_ovirt.lib.shell_cmd import (
    quote_string, dict_to_opts, quote_and_join
)


@pytest.mark.parametrize(
    ('param', 'expected'),
    [
        ('abcd', 'abcd'),
        ('abc def', '\'abc def\''),
        ('ab "cd" ef', '\'ab "cd" ef\''),
        ('ab $cd $ef', '\'ab $cd $ef\''),
        ('ab `cd ef`', '\'ab `cd ef`\''),
        (42, '42'),
        ('xyz \\$foo', '\'xyz \\$foo\''),
        ('abc\'def', '\'abc\'"\'"\'def\''),
    ]
)
def test_quote_string(param, expected):
    output = quote_string(param)
    assert expected == output


@pytest.mark.parametrize(
    ('param_dict', 'expected'),
    [
        (
            dict(op1='xyz', op2='uvw', longer_opt=786),
            ('--op1', 'xyz', '--op2', 'uvw', '--longer-opt', 786),
        ),
    ]
)
def test_dict_to_opts(param_dict, expected):
    result = dict_to_opts(param_dict)
    assert sorted(expected) == sorted(result)


@pytest.mark.parametrize(
    ('param_dict', 'expected'),
    [
        (
            OrderedDict(
                (('op1', 'xyz'), ('op2', 'uvw'), ('longer_opt', 786))
            ),
            ('--op1', 'xyz', '--op2', 'uvw', '--longer-opt', 786),
        ),
    ]
)
def test_dict_to_opts_keeps_order(param_dict, expected):
    result = tuple(dict_to_opts(param_dict))
    assert expected == result


@pytest.mark.parametrize(
    ('cmd', 'args', 'expected'),
    [
        ('foo', ('bar', 234, 'my thing'), "foo bar 234 'my thing'"),
        ('lone_foo', (), 'lone_foo'),
    ]
)
def test_quote_and_join(cmd, args, expected):
    result = quote_and_join(cmd, *args)
    assert expected == result
