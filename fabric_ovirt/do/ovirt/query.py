#!/usr/bin/env python
# encoding: utf-8
#
from fabric.api import task
from fabric.utils import abort

from fabric_ovirt.lib.ovirt import ovirt_task, oVirtObjectType


@task
@ovirt_task
def query(ootype, oquery='', show=None, headers='yes', ovirt=None):
    """
    Query oVirt for objects

    :param str ootype: The oVirt object type to query for
    :param str oquery: The oVirt engine query to run. Engine wildards can be
                    used. Make sure the escape equel signs (=) with backslash
                    (\) when passing query from the command line.
    :param str show: A colon (:) separated list of fields to show, the same
                    field could be shown multiple times and the ordering is
                    significant.
    :param str headers: 'yes' to show column headers (The default), anything
                        else to hide them.
    """
    type_obj = oVirtObjectType.all_types.get(ootype)
    if type_obj is None:
        abort("Invalid oVirt object type specified")

    obj_list = type_obj.query(ovirt, oquery)
    type_obj.print_table(
        obj_list=obj_list,
        show=show,
        headers=headers
    )
    return obj_list
