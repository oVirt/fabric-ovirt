#!/usr/bin/env python
from fabric.api import (
    task,
    run,
)


@task
def show_bridges():
    run('brctl show')
