#!/usr/bin/env python
from fabric.api import (
    task,
    local,
)


@task
def hello():
    local('echo hellllloooooo')
