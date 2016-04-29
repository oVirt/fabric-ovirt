#!/usr/bin/env python
"""
Some examples:

* See the list of available tasks.
    ~# fab --list
* Execute the given task with the given parameter:
    ~# fab mytask:myparam=myvalue
* or (using positional parameters)
    ~# fab mytask:myvalue
* Execute the given task on a host range:
    ~# fab hostrange:myhost10:20range mytask
* or using letter ranges
    ~# fab hostrange:myhostA:Zrange mytask
* Execute an arbitrary command (ls -la):
    ~# fab hostrange:myhost10:20range -- ls -la
"""
import fabric
from fabric_ovirt import (  # noqa
    on,
    do,
)
from fabric_ovirt.lib.parallel import monkey_patch


monkey_patch(fabric)
