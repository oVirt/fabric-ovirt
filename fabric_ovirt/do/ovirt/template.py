#!/usr/bin/env python
# encoding: utf-8
#
from time import sleep
from ovirtsdk.xml import params as oVirtParams
from ovirtsdk.infrastructure import errors as oVirtErrors
from fabric.api import task
from fabric.utils import error
from fabric.context_managers import hide

from fabric_ovirt.lib.ovirt import ovirt_task, oVirtObjectType
from fabric_ovirt.lib.utils import puts
from fabric_ovirt.lib.units import GiB

from .vm import create_from_disk as _create_vm_from_disk

# We need this because otherwise we will see imported tasks in fab -l
__all__ = ['create_from_vm', 'create_from_disk', 'delete']


def _delete_vms(vms, attempts=300, delay=10, ovirt=None):
    """
    Delete oVirt VMs while waiting for disks to be unlocked

    :param list vms:       The list of vms to delete
    :param int attempts:   How many attepmts to make to delete a VM
    :param int delay:      How many seconds to wait between attempts to delete
    :param ovirtsdk.api.API ovirt: An open oVirt API connection
    """
    for attepmt in xrange(0, attempts):
        remaining_vms = []
        for vm in vms:
            if ovirt.vms.get(id=vm.id).status.state != 'down':
                remaining_vms.append(vm)
                continue
            try:
                vm.delete(oVirtParams.Action(async=False))
            except oVirtErrors.RequestError as e:
                if (
                    e.status == 409 and e.reason == 'Conflict' and
                    e.message.find('disks are locked') >= 0
                ):
                    remaining_vms.append(vm)
                elif e.status == 404:
                    pass
                else:
                    raise
        if not remaining_vms:
            return
        sleep(delay)
        vms = remaining_vms
    error("Timed out trying to delete the following VMs: {0}".format(
        ', '.join(vm.name for vm in vms)
    ))


def _create_from_vms(
    vms, delete_vms='no', show=None, headers='yes', ovirt=None
):
    """
    Create an oVirt template from the given VMs
    (See create_from_vm for explanation about parameters)
    """
    templates = []
    for vm in vms:
        templ = ovirt.templates.add(oVirtParams.Template(vm=vm, name=vm.name))
        templates.append(templ)
    if delete_vms == 'yes':
        _delete_vms(vms=vms, ovirt=ovirt)
    oVirtObjectType.all_types['template'].print_table(
        templates, show=show, headers=headers
    )
    return templates


@task
@ovirt_task
def create_from_vm(
    vm_query, delete_vms='no', show=None, headers='yes', ovirt=None
):
    """
    Create an oVirt template from the given VMs

    :param str vm_query:   A query for VMs to make templates of
    :param str delete_vms: "yes" to delete VMs that are converted to templates

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    :returns: The templates tha were created
    :rtype: list
    """
    vms = ovirt.vms.list(query=vm_query)
    templates = _create_from_vms(
        vms=vms,
        delete_vms=delete_vms,
        show=show, headers=headers,
        ovirt=ovirt
    )
    return templates


@task
@ovirt_task
def create_from_disk(
    disk_query, cluster_query=None, memory=2 * GiB, vcpus=2,
    networks=None,
    show=None, headers='yes', ovirt=None
):
    """
    Create an oVirt template from the given disk

    :param str disk_query:    A query to find the disk to use, if multipile
                              disks are found, templates are created for each
                              and every disk
    :param str cluster_query: A query to find the cluster to place the
                              template in, if more then one cluster is found,
                              the first one is used
    :param int memory:        The template memory size (in bytes)
    :param ind vcpus:         The amount of vCPUs to assign to the tempalte
    :param str networks:      A pipe (|) separated list of networks to attach
                              to the template in the order they should be
                              added, a network can appear more then once. Only
                              networks that are attached to the template`s
                              cluster will be added
    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The template tha was created
    :rtype: ovirtsdk.infrastructure.brokers.Template
    """
    with hide('user'):
        vms = _create_vm_from_disk(
            disk_query=disk_query, cluster_query=cluster_query,
            memory=memory, vcpus=vcpus, set_disk_bootable='yes',
            networks=networks,
        )
    templates = _create_from_vms(
        vms=vms,
        delete_vms='yes',
        show=show, headers=headers,
        ovirt=ovirt
    )
    return templates


@task
@ovirt_task
def delete(oquery, ovirt=None):
    """
    Delete templates

    :param str oquery: a query string to select tempaltes to delete
    :param ovirtsdk.api.API ovirt: a connected oVirt API object

    :returns: How many templates were deleted
    :rtype: int
    """
    templates = ovirt.templates.list(query=oquery)
    for template in templates:
        template.delete(async=False)
    puts('{0} templates deleted'.format(len(templates)))
    return len(templates)
