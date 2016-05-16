#!/usr/bin/env python
"""shell_cmd.py - Utilities for converting things into safe shell command
strings
"""
import re
import itertools
from pipes import quote


def quote_string(param):
    """Ensure the given string becomes a single shell argument

    :param str param: A parameter to quote and escape
    :rtype: str
    """
    # Fabric adds its own layer of quoting and miss-quotes backslash (\)
    # characters, therfore we cannot use it, and have to use single-quote (')
    # based quoting. pipes.quote seems to do that but we also have tests that
    # would break if it stops doing so.
    return quote(str(param))


def dict_to_opts(param_dict):
    """Convert a Mapping to shell option arguments

    Each dict key is considered to be a long option and the value a value
    appended to it. Short (single char) options and boolean (no value) options
    are not supported.

    :param Mapping param_dict: mapping to convert to options
    :returns: Iterator over generated options and value arguments
    :rtype: Iterator
    """
    for key, value in param_dict.iteritems():
        yield '--{0}'.format(re.sub('[\W_]', '-', key))
        yield value


def quote_and_join(cmd, *args):
    """Build a shell command string from separate parts

    :param str cmd:     This parameter is considered to be the command to run
                        and is taken verbatim
    :param list args:   List of argumetns to the command, are passed through
                        quote_string

    After being processed, all arguments are concatenated together with spaces
    :returns: A single shell command string from all arguments
    :rtype: str
    """
    return ' '.join(itertools.chain(
        (str(cmd),),
        (quote_string(parg) for parg in args),
    ))
