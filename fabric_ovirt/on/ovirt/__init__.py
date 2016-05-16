#!/usr/bin/env python
# encoding: utf-8
#
from fabric.utils import warn
try:
    from ovirtsdk.api import API as oVirtApi
    assert oVirtApi
    have_ovirt_sdk = True
except:
    warn(
        "Not enabling oVirt related tasks, install the oVirt Python SDK "
        "to get full functionality"
    )
    have_ovirt_sdk = False

if have_ovirt_sdk:
    import host
    assert host
