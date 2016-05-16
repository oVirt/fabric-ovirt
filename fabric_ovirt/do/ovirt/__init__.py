#!/usr/bin/env python
# encoding: utf-8
#
from fabric.api import task
from fabric.utils import warn
try:
    from ovirtsdk.api import API as oVirtApi  # noqa
    have_ovirt_sdk = True
except:
    warn(
        "Not enabling oVirt related tasks, install the oVirt Python SDK "
        "to get full functionality"
    )
    have_ovirt_sdk = False

if have_ovirt_sdk:
    from query import query
    import vm  # noqa
    import template  # noqa
    import vmpool  # noqa

    from imp import new_module
    from functools import partial
    from fabric_ovirt.lib.ovirt import oVirtObjectType

    for ootypename, ootype in oVirtObjectType.all_types.iteritems():
        mod = globals().setdefault(
            ootypename, new_module('.'.join((__name__, ootypename)))
        )
        mod.query = task(partial(query, ootypename))
        mod.query.__doc__ = """
        Query oVirt for {ootypename} objects

        :param str oquery: The oVirt engine query to run. Engine wildards can
                           be used. Make sure the escape equel signs (=) with
                           backslash (\) when passing query from the command
                           line.
        :param str show: A colon (:) separated list of fields to show, the same
                         field could be shown multiple times and the ordering
                         is significant.
                         Supported fields are: {ootype_fields}
                         Default value is: {ootype_default_fields}
        :param str headers: 'yes' to show column headers (The default),
                            anything else to hide them.
        """.format(
            ootypename=ootypename,
            ootype_fields=', '.join(ootype.fields),
            ootype_default_fields=ootype.default_fields,
        )
        if hasattr(mod, '__all__') and mod.__all__:
            mod.__all__.append('query')
