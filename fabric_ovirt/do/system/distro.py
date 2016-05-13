#!/usr/bin/env python
# encoding: utf-8
"""
Tasks to retrieve distro information from the hosts
"""

from fabric.api import task, run


@task(default=True)
def get():
    """
    Get the remote distro, really dummy right now
    """
    return run("cat /etc/redhat-release || echo unknown")
