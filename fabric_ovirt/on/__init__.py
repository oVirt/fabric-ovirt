#!/usr/bin/env python
# encoding: utf-8


from fabric.api import (
    serial,
    task,
    runs_once,
    env,
)

from . import (  # noqa
    foreman,
    range,
)


@task(default=True)
@runs_once
@serial
def hosts(*args):
    env.hosts.extend(args)
