#!/usr/bin/env python
# encoding: utf-8
#
from fabric.api import task, env, prompt, abort, puts

from fabric_ci.lib.utils import yellow
from fabric_ci.lib.ovirt import ovirt_task, oVirtObjectType


@task
@ovirt_task
def query(oquery='', sure='no', ovirt=None):
    """
    Query oVirt for hosts and place them in env.hosts

    :param str oquery: The oVirt engine query to run. Engine wildards can be
                       used. Make sure the escape equel signs (=) with
                       backslash (\) when passing query from the command line.
    :param str sure:   If set to `yes`, it will not ask for confirmation before
                       running.
    """
    hosts = oVirtObjectType.all_types['host'].query(ovirt, oquery)
    env.hosts = [host.address for host in hosts]
    puts(yellow(
        "Got %d hosts: \n\t" % len(env.hosts)
        + '\n\t'.join(env.hosts)
    ))
    if sure != 'yes' and not env.parallel:
        if prompt('Is what you expected? y|n', default='y').lower() == 'n':
            abort('Ended by user request.')
    return hosts
