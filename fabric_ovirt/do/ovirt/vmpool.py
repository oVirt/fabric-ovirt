#!/usr/bin/env python
# encoding: utf-8
#
from ovirtsdk.api import API as oVirtApi
from ovirtsdk.xml import params as oVirtParams
from ovirtsdk.infrastructure import brokers as oVirtObjects
from fabric.utils import abort, warn, error
from fabric.context_managers import hide

from fabric.api import task

from fabric_ovirt.lib.ovirt import ovirt_task, oVirtObjectType
from .template import (
    create_from_vm as _create_template_from_vm,
    create_from_disk as _create_template_from_disk,
)
from fabric_ovirt.lib.units import GiB

# Silance pyflakes "import but unused" warnings
assert oVirtApi
assert oVirtObjects

# We need this because otherwise we will see imported tasks in fab -l
__all__ = ['create', 'create_from_vm', 'create_from_disk', ]


def _cluster_from_query(cluster_query, ovirt):
    """
    Get a cluster object based on a query, issue a warning if more then one
    object is found and abort if no object is found.

    :param str cluster_query: A query string for clusters
    :param oVirtApi ovirt:    An open oVirt API connection

    :returns: A cluster object that matches the query
    :rtype: oVirtObjects.Cluster
    """
    clusters = ovirt.clusters.list(query=cluster_query)
    if not clusters:
        abort("No cluster found by given query")
    if len(clusters) > 1:
        warn("More then one cluster found, will use the first")
    return clusters[0]


def _vm_args_to_params(**vm_args):  # noqa - ignore mccabe warning
    """
    Convert fabric-style simple arguments into an oVirt VM parameters structure

    All parameters are as defined in the 'create' task for customizing the pool
    VMs

    :returns: an oVirt VM paameters structure or None if not customization was
              requested
    :rtype: oVirtObjects.VM
    """
    vm_args_supported = (
        'custom_serial_number', 'memory', 'memory_guaranteed',
        'memory_balooning', 'vcpus',
    )
    vm_args = dict(
        (key, value) for key, value in vm_args.iteritems()
        if key in vm_args_supported and value is not None
    )
    if not vm_args:
        return None
    vm_params = oVirtParams.VM()
    memory = None
    if 'memory' in vm_args:
        memory = int(vm_args['memory'])
        vm_params.memory = memory
    mem_policy = None
    if 'memory_guaranteed' in vm_args or 'memory_balooning' in vm_args:
        mem_policy = oVirtParams.MemoryPolicy()
        if 'memory_guaranteed' in vm_args:
            mem_policy.guaranteed = int(vm_args['memory_guaranteed'])
        if 'memory_balooning' in vm_args:
            mem_policy.ballooning = bool(vm_args['balooning'])
    # oVirt sets guaranteed to 1G by default so we need to set it for smaller
    # VMs. This is a work-around for oVirt BZ#1333369
    if memory and memory < 1 * GiB:
        if mem_policy is None:
            mem_policy = oVirtParams.MemoryPolicy(guaranteed=memory)
        elif mem_policy.guaranteed is None:
            mem_policy.guaranteed = memory
    vm_params.memory_policy = mem_policy
    if 'vcpus' in vm_args:
        vm_params.cpu = oVirtParams.CPU(
            topology=oVirtParams.CpuTopology(sockets=int(vm_args['vcpus']))
        )
    if 'custom_serial_number' in vm_args:
        vm_params.serial_number = oVirtParams.SerialNumber(
            policy='custom', value=vm_args['custom_serial_number'],
        )
    return vm_params


def _create_one(
    ovirt, template, cluster=None, name=None, size=2, prestarted_vms=0,
    **vm_args
):
    """
    Create a new oVirt VM pool

    :param oVirtObjects.Template template: an ovirt template object to create
                                           the pool from
    :param oVirtObjects.Cluster cluster:   an oVirt cluster to create the pool
                                           in. If 'None' is passed, the cluster
                                           of the template is used.
    :param oVirtApi ovirt:                 An open oVirt API connection

    All other paramters are the same as for the 'create' task

    :returns: The pool that was created
    :rtype: oVirtObjects.VmPool
    """
    if cluster is None:
        tmpl_clstr = template.get_cluster()
        if tmpl_clstr is None:
            abort(
                "Cannot find cluster of template and not cluster query given"
            )
        clusters = ovirt.clusters.list(id=tmpl_clstr.id)
        cluster = clusters[0]
    vmpool = ovirt.vmpools.add(vmpool=oVirtParams.VmPool(
        cluster=cluster,
        template=template,
        name=name or template.name,
        size=int(size),
        prestarted_vms=int(prestarted_vms),
        vm=_vm_args_to_params(**vm_args),
    ))
    return vmpool


def _create(
    templates, cluster_query=None, name=None,
    show=None, headers='yes', ovirt=None, **pool_args
):
    """
    Create new oVirt VM pools

    :param list templates:     A query to find the template to use to create
                               the VM pool, if more then one template is found
                               a pool will be created from each template
    :param oVirtApi ovirt:     An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task
    All other paramters are the same as for the 'create' task

    :returns: The VM pools that were created
    :rtype: list
    """
    if len(templates) > 1 and name:
        error("Cannot assign name when creating multipile VM pools")
    cluster = None
    if templates:
        if cluster_query:
            cluster = _cluster_from_query(cluster_query)
    vmpools = [
        _create_one(
            template=template,
            cluster=cluster,
            name=name,
            ovirt=ovirt,
            **pool_args
        )
        for template in templates
    ]
    oVirtObjectType.all_types['vmpool'].print_table(
        vmpools, show=show, headers=headers
    )
    return vmpools


@task
@ovirt_task
def create(
    template_query, cluster_query=None,
    name=None, size=2, prestarted_vms=0,
    custom_serial_number=None, memory=None, memory_guaranteed=None,
    memory_balooning=None, vcpus=None,
    show=None, headers='yes', ovirt=None
):
    """
    Create new oVirt VM pools

    :param str template_query:       A query to find the template to use to
                                     create the VM pool, if more then one
                                     template is found a pool will be created
                                     from each template
    :param str name:                 The name of the VM  pool to create, if
                                     unspecified the name of the template will
                                     be used
    :param str cluster_query:        A query to find the cluster to place the
                                     VM pool in, if more then one cluster is
                                     found, the first one is used, if
                                     unspecified, the cluster of the template
                                     will be used.
    :param int size:                 The size of the VM pool (default 2)
    :param int prestarted_vms:       The amount of pre-started VMs in the pool
                                     (default 0)
    :param str custom_serial_number: A custom serial number to set for VMs in
                                     the pool
    :param int memory:               The pool VM memory size (in bytes). If
                                     unspecified, value is taken from template
    :param int memory_guaranteed:    How much memory to guarantee for the VMs
                                     in the pool
    :param bool memory_balooning:    Wither to enable balooning for VMs in pool
    :param int vcpus:                The amount of vCPUs to assign to VMs in
                                     them pool. If unspecified, value is taken
                                     from template
    :param oVirtApi ovirt:           An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The VM pools that were created
    :rtype: list
    """
    templates = ovirt.templates.list(query=template_query)
    vmpools = _create(
        templates=templates,
        cluster_query=cluster_query,
        name=name,
        size=size,
        prestarted_vms=prestarted_vms,
        custom_serial_number=custom_serial_number,
        memory=memory,
        memory_guaranteed=memory_guaranteed,
        memory_balooning=memory_balooning,
        vcpus=vcpus,
        show=show,
        headers=headers,
        ovirt=ovirt
    )
    return vmpools


@task
@ovirt_task
def create_from_vm(
    vm_query, delete_vms='no',
    name=None, size=2, prestarted_vms=0, custom_serial_number=None,
    show=None, headers='yes', ovirt=None
):
    """
    Create an oVirt vmpools from the given VMs

    :param str vm_query:             A query for VMs to make vmpools of
    :param str delete_vms:           "yes" to delete VMs that are converted to
                                     templates
    :param str name:                 The name of the VM  pool to create, if
                                     unspecified the name of the template will
                                     be used
    :param int size:                 The size of the VM pool (default 2)
    :param int prestarted_vms:       The amount of pre-started VMs in the pool
                                     (default 0)
    :param str custom_serial_number: A custom serial number to set for VMs in
                                     the pool
    :param oVirtApi ovirt:           An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The VM pools that were created
    :rtype: list
    """
    with hide('user'):
        templates = _create_template_from_vm(
            vm_query=vm_query,
            delete_vms=delete_vms,
            ovirt=ovirt,
        )
    vmpools = _create(
        templates=templates,
        name=name,
        size=size,
        prestarted_vms=prestarted_vms,
        show=show,
        custom_serial_number=custom_serial_number,
        headers=headers,
        ovirt=ovirt
    )
    return vmpools


@task
@ovirt_task
def create_from_disk(
    disk_query, cluster_query=None, memory=2 * GiB, vcpus=2,
    networks=None,
    name=None, size=2, prestarted_vms=0, custom_serial_number=None,
    show=None, headers='yes', ovirt=None
):
    """
    Create an oVirt vmpools from the given disks

    :param str disk_query:           A query to find the disk to use, if
                                     multipile disks are found, templates are
                                     created for each and every disk
    :param str cluster_query:        A query to find the cluster to place the
                                     VM pool in, if more then one cluster is
                                     found, the first one is used, if
                                     unspecified, the cluster of the template
                                     will be used.
    :param int memory:               The pool VM memory size (in bytes)
    :param ind vcpus:                The amount of vCPUs to assign to VMs in
                                     them pool
    :param str networks:             A pipe (|) separated list of networks to
                                     attach to the VMs in the pool in the order
                                     they should be added, a network can appear
                                     more then once. Only networks that are
                                     attached to the pool`s cluster will be
                                     added
    :param str name:                 The name of the VM  pool to create, if
                                     unspecified the name of the template will
                                     be used
    :param int size:                 The size of the VM pool (default 2)
    :param int prestarted_vms:       The amount of pre-started VMs in the pool
                                     (default 0)
    :param str custom_serial_number: A custom serial number to set for VMs in
                                     the pool
    :param oVirtApi ovirt:           An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The VM pools that were created
    :rtype: list
    """
    with hide('user'):
        templates = _create_template_from_disk(
            disk_query=disk_query,
            cluster_query=cluster_query,
            memory=memory,
            vcpus=vcpus,
            networks=networks,
            ovirt=ovirt,
        )
    vmpools = _create(
        templates=templates,
        size=size,
        prestarted_vms=prestarted_vms,
        show=show,
        custom_serial_number=custom_serial_number,
        headers=headers,
        ovirt=ovirt
    )
    return vmpools
