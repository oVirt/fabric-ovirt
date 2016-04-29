#!/usr/bin/env python
# encoding: utf-8

import datetime
import sys
import re
import socket
import getpass
import requests
import lxml.html
from fnmatch import translate
from fabric import (
    colors,
    utils,
)
from fabric.api import (
    env,
    task,
    settings,
    hide,
    local,
    run,
    abort,
)
from HTMLParser import HTMLParser
import htmlentitydefs


TTY = sys.stdout.isatty()
TRUE = '(y.*|true|1)'


class CmdResponse():
    """
    class that behaves as a boolean, `True` if there was a match, `False`
    otherwise, and when printed shows the output of the command.
    """
    def __init__(self, cmd_out, boolval):
        self.boolval = boolval
        self.out = cmd_out

    def __nonzero__(self):
        return self.boolval

    def __str__(self):
        return str(self.out)


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def handle_charref(self, number):
        codepoint = (
            int(number[1:], 16) if number[0] in (u'x', u'X')
            else int(number))
        self.result.append(unichr(codepoint))

    def handle_entityref(self, name):
        codepoint = htmlentitydefs.name2codepoint[name]
        self.result.append(unichr(codepoint))

    def get_text(self):
        return u''.join(self.result)


def html_to_text(html):
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()


def absolute_import(modname, fromlist=None):
    fromlist = fromlist or []
    mod = __import__(modname, globals(), locals(), fromlist, 0)
    return mod


def blue(msg, bold=False):
    msg = str(msg)
    return TTY and colors.blue(msg, bold) or msg


def red(msg, bold=False):
    msg = str(msg)
    return TTY and colors.red(msg, bold) or msg


def green(msg, bold=False):
    msg = str(msg)
    return TTY and colors.green(msg, bold) or msg


def yellow(msg, bold=False):
    msg = str(msg)
    return TTY and colors.yellow(msg, bold) or msg


def white(msg, bold=False):
    msg = str(msg)
    return TTY and colors.white(msg, bold) or msg


def magenta(msg, bold=False):
    msg = str(msg)
    return TTY and colors.magenta(msg, bold) or msg


def cyan(msg, bold=False):
    msg = str(msg)
    return TTY and colors.cyan(msg, bold) or msg


def warn(msg, end='\n', with_ts=True):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts('[WARNING] ', yellow, True) + yellow(msg), end=end)
    else:
        utils.fastprint(yellow('[WARNING] ', True) + yellow(msg), end=end)


def error(msg, end='\n', with_ts=True, hard=True):
    msg = str(msg)
    if with_ts:
        msg = ts('[ERROR] ', red, True) + red(msg)
    else:
        msg = red('[ERROR] ', True) + red(msg)
    if hard:
        abort(msg)
    else:
        utils.fastprint(msg, end=end)


def info(msg, end='\n', with_ts=True):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts('[INFO] ', blue, True) + blue(msg), end=end)
    else:
        utils.fastprint(blue('[INFO] ') + blue(msg), end=end)


def puts(msg, end='\n', with_ts=False):
    msg = str(msg)
    if with_ts:
        utils.fastprint(ts(msg), end=end)
    else:
        utils.fastprint(msg, end=end)


def ts(msg, color=None, bold=False, with_origin=True,
       with_target=False, utc=False):
    if color is None:
        def new_color(x, y):
            return x

        color = new_color
    msg = str(msg)
    if utc:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now()
    text = '[' + now.strftime("%d/%m/%Y %H:%M:%S")
    if TTY:
        text = color(text, bold)
    if with_target or env.parallel:
        target = "on %s" % env.host
        if TTY:
            text += color("|", bold) + white(target)
        else:
            text += "|" + target
    if with_origin:
        origin = "by %s@%s" % (getpass.getuser(), socket.gethostname())
        if TTY:
            text += color("|", bold) \
                + blue(origin) \
                + color("] %s" % msg, bold)
        else:
            text += "|" + origin + "] %s" % msg
    return text


def smiley():
    import random
    eyes = ':XB8'
    noses = ['-', '~', '']
    mouths = 'Ddb)9]|'
    face = ''
    for lst in [eyes, noses, mouths]:
        face += random.choice(lst)
    return face


def fancy(msg):
    msg += ' ' + smiley()
    with settings(warn_only=True):
        with hide('warnings'):
            out = local('cowsay "%s"' % msg, capture=True)
    if out.failed:
        return msg
    else:
        return out
    msg += ' ' + smiley()


@task
def run_cmd(command, regexp=''):
    """
    Run the given command, and maybe look if it matches the given regexp

    :param comman: command to run
    :param regexp: regexp to match, empy by default
    """
    if not regexp:
        run(command)

    else:
        res = run_match(command, regexp)
        if res:
            puts(res)
        else:
            sys.exit(1)


def run_match(command, regexp, hide_out=True):
    """
    Helper function to check if the output of a command matches a regexp

    :param comman: Command to run
    :param regexp: Regexp to matches
    :param hide_out: Hide the commands output, True by default
    :rtype: :class:`.CmdResponse`

    """
    if hide_out:
        to_hide = ['warnings', 'stdout']
    else:
        to_hide = []
    with hide(*to_hide):
        out = run(command)
    res = re.search(regexp, out)
    if res:
        return CmdResponse(out, True)
    else:
        return CmdResponse(out, False)


def matches_glob(what, pattern):
    return re.match(translate(pattern), what)


def ifilter_glob(what_list, patterns):
    for what in what_list:
        for pattern in patterns:
            if matches_glob(what, pattern):
                yield what
                break


def filter_glob(what_list, patterns):
    return list(ifilter_glob(what_list, patterns))


def assign_param(env_name, param_name=None, params=None, input_func=raw_input):
    """
    assign_param
    Assigns the given paramter to env['env_name'] from the params dictonary
    by the following precedence:
        1) if found in params dict assings its value to env['env_name']
        2) if not and found in env[env_name] keeps it unchanged
        3) if both are not found asks the user to input the parameter

    :param env_name: name of the parameter in env dict, if not set uses
        env_name
    :param param_name: name of the parameter in the params dict, if not set
        uses param_name
    :param params: dict with params to look up
    :param input_func: input function, default is raw_input
    :return: the new assigned variable in env dict
    :rtype: string
    """
    param_name = param_name or env_name
    params = params or {}
    if params.get(param_name, None) is not None:
        env[env_name] = params.get(param_name)
    elif env.get(env_name, None) is None:
        if not TTY or env['parallel']:
            raise Exception(
                'Missing parameter %s and %s not found in configuration file'
                % (param_name, env_name))
        env[env_name] = input_func('Provide %s: ' % param_name)
    return env[env_name]


def check_param(env_name, param_name=None, params=None, input_func=raw_input):
    """
    Checks if the given parameter is present in the params dict or available in
    the env, and asks for it to the user if not or set to 'ask'.

    :param env_name: name of the parameter in the env dict
    :param param_name: nome of the parameter in the params dict, will use
        env_name if not passed.
    :param params: dict with the params to look into before looking into the
        env, will use an empty dict if not passed.
    :param input_func: input function to ask the user, by default is raw_input
        but you can pass getpass.getpass or a custom one
    """
    param_name = param_name or env_name
    params = params or {}

    if (
        params.get(param_name, None) in (None, 'ask') and
        env.get(env_name, None) in (None, 'ask')
    ):
        if not TTY or env['parallel']:
            raise Exception(
                'Missing parameter %s and %s not found in configuration file'
                % (param_name, env_name)
            )
        env[env_name] = input_func('Provide %s: ' % param_name)
    return env[env_name]


def split_host(host_str):
    """
    Given a host spec in the form [user[:pass]@]host return the user, pass
    and host tuple

    :param host_str: Host spec in the form [user[:pass]@]host
    """
    user = passwd = ''
    host = host_str
    if '@' in host_str:
        user, host = host.split('@', 1)
    if ':' in user:
        user, passwd = user.split(':', 1)
    return user, passwd, host


def is_true(my_str):
    """
    Matches a string response (user restponse) with a boolean

    :param my_str: String to evaluate
    """
    return re.match(TRUE, my_str.lower())


def is_false(my_str):
    """
    Matches a string response (user restponse) with a boolean

    :param my_str: String to evaluate
    """
    return not is_true(my_str)


def filter_links(http_url, regex):
    """
    filter_links
    filters links from url by a regex

    :param http_url: url to extract links from
    :param regex: regex to match each link name
    :return: filtered links' names
    :rtype: list
    """
    result = requests.get(http_url)
    result.raise_for_status()
    html_page = lxml.html.fromstring(result.text)
    links = (link[2][:-1] for link in html_page.iterlinks())
    r = re.compile(regex)
    return [link for link in links if r.match(link)]


def filter_dirs(dir_path, regex):
    """
    filter_dirs
    run ls and filter results by regex

    :param dir_path: path to ls in
    :param regex: regex to filter ls results
    :return: filtered dirs
    :rtype: list
    """
    with settings(warn_only=True):
        dirs = run('ls {0}'.format(dir_path))
    r = re.compile(regex)
    return [directory for directory in dirs.split() if r.match(directory)]


def extract_date(string, date_format='%Y%m%d'):
    """
    extract_date
    looks for the first 8 digit sequence in a string and attempts to create a
    datetime object from it

    :param string: string to look for the sequence
    :param date_format: date format, default is YYYYMMDD
    :returns: datetime exracted from the string
    :rtype: datetime.datetime
    """
    match = re.search(r'(?P<date>\d{4}\d{2}\d{2})', string)
    if match is not None and len(match.groups()) == 1:
        date_str = match.group('date')
        date_obj = datetime.datetime.strptime(date_str, date_format)
        return date_obj
    else:
        raise ValueError('unable to extract date from: %s' % string)
