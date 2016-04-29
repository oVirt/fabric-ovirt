#!/usr/bin/env python
# encoding: utf-8
"""
foreman.py

various methods used by fabric tasks that interact with foreman
"""

from functools import wraps
from fabric.api import env
from getpass import getpass
from fabric_ovirt.lib.utils import check_param


def foreman_defaults(func):
    """
    Decorator to pass the defaults to the function

    All the default params will be passed as keyword arguments. positional
    arguments will be respected
    """

    @wraps(func)
    def newfunc(*args, **kwargs):
        """
        Wrapper to add the foerman parameters to the task
        """
        check_param('FOREMAN_URL', 'foreman', kwargs)
        check_param('FOREMAN_USER', 'user', kwargs)
        check_param('FOREMAN_PASSWORD', 'passwd', kwargs, input_func=getpass)
        kwargs['foreman'] = kwargs.get('foreman', env.FOREMAN_URL)
        kwargs['user'] = kwargs.get('user', env.FOREMAN_USER)
        kwargs['passwd'] = kwargs.get('passwd', env.FOREMAN_PASSWORD)
        return func(*args, **kwargs)
    return newfunc


def add_hosts_to_query(query='', hosts=None):
    """
    Add the env.hosts or the given hosts to the given foreman query.

    :param query: Original query
    :param hosts: list of hosts if not using env.hosts
    """
    hosts = hosts or env.hosts
    if hosts:
        query += (query and ' AND' or '') \
            + ' ( name=%s )' % ' OR name='.join(hosts)
    return query


def get_hg_by_name(frm_client, hg_name):
    """
    get_hg_by_name
    get hostgroup metadata dictonary

    :param frm_client: frm open connection
    :param hg_name: hostgroup name to look up
    :return: hostgroup metadata dictonary
    :rtype: dict
    """
    hostgroup = frm_client.index_hostgroups(search='name = %s' % hg_name)
    res = hostgroup.get('results', [])
    if len(res) != 1:
        raise LookupError(('hostgroup {0} does not exists or more than one'
                           ' hostgroup was found').format(hg_name))
    return res[0]


def get_host_by_name(frm_client, host_name):
    """
    get_host_by_name
    get a host metadata dictonary

    :param frm_client: foreman connection
    :param host_name: hostname to lookup
    :return: hostname metadata dictonary
    :rtype: dict
    """
    host = frm_client.index_hosts(search='name = {0}'.format(host_name))
    res = host.get('results', [])
    if len(res) != 1:
        raise LookupError(('host {0} does not exist or more than one'
                           ' host was found').format(host_name))
    return res[0]
