#!/usr/bin/env python
# encoding: utf-8
#
import re
from itertools import count

from ovirtsdk.xml import params as oVirtParams
from ovirtsdk.infrastructure import errors as oVirtErrors
from fabric.api import task, run
from fabric.utils import abort, warn
from fabric.context_managers import hide

from fabric_ovirt.lib.ovirt import ovirt_task, oVirtObjectType
from fabric_ovirt.lib.utils import puts
from fabric_ovirt.lib.units import GiB

from .query import query as _query

# We need this because otherwise we will see imported tasks in fab -l
__all__ = [
    'from_host', 'add_disk', 'attach_disks', 'remove_disk', 'host_add_disk',
    'host_remove_disk', 'host_attach_disks', 'create', 'create_from_disk',
    'delete',
]


def get_host_macs():
    """
    Generator that yeilds the MAC addresses of env.host
    """
    mac_re = re.compile('\s+link/ether\s+([0-9A-Fa-f:]{17})\s+')
    output = run('ip -o link show', shell=False, quiet=True)
    macs = mac_re.findall(output)
    for mac in macs:
        yield mac


@task
@ovirt_task
def from_host(show=None, headers='yes', ovirt=None):
    """
    Get the oVirt VM ID of hosts using their MAC addresses

    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The vm object that was found for the host
    :rtype: ovirtsdk.infrastructure.brokers.VM
    """
    oquery = ' or '.join('Vnic.mac={0}'.format(mac) for mac in get_host_macs())
    vms = _query(ootype='vm', oquery=oquery, show=show, headers=headers)
    if vms:
        return vms[0]
    else:
        return None


@task
@ovirt_task
def add_disk(
    vm_id, size, name=None, format='raw', interface='virtio', bootable='no',
    show=None, headers='yes', ovirt=None
):
    """
    Add a disk to a VM and prints out the disk details when done

    :param str vm_id:      The Id of the VM to add the disk to
    :param str name:       The name of the disk to add, if specified the disk
                           will only be added if a disk of that name does not
                           already exist
    :param int size:       The size of the disk to create in bytes
    :param str format:     The format of the disk to create (Use 'raw', the
                           default unless you know oVirt well enough to know
                           what you are doing)
    :param str interface:  The interface of the disk (Use 'virtio', the default
                           unless you know oVirt well enough to know what you
                           are doing)
    :param str bootable:   If 'yes' the disk will be bootable
    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The disk that was added
    :rtype: ovirtsdk.infrastructure.brokers.Disk
    """
    if name is not None:
        existing_disk = ovirt.disks.get(alias=name)
        if existing_disk:
            abort("Disk with name: '{0}' already exists".format(name))
    vm = ovirt.vms.get(id=vm_id)
    if vm is None:
        abort("VM with specified ID '{0}' not found".format(vm_id))
    disk_params = oVirtParams.Disk(
        size=int(size),
        format=format,
        interface=interface,
        bootable=(bootable == 'yes'),
    )
    if name is not None:
        disk_params.name = name
    disk = vm.disks.add(disk_params)
    disk.activate(oVirtParams.Action(async=False))
    oVirtObjectType.all_types['disk'].print_table(
        (disk,), show=show, headers=headers
    )
    return disk


@task
@ovirt_task
def attach_disks(vm_id, disk_query, show=None, headers='yes', ovirt=None):
    """
    Attach disks to a VM and prints out the disk details when done

    :param str vm_id:      The Id of the VM to add the disk to
    :param str disk_query: A query for disks to attach to the VM
    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The disks that were added
    :rtype: list
    """
    vm = ovirt.vms.get(id=vm_id)
    if vm is None:
        abort("VM with specified ID '{0}' not found".format(vm_id))
    disks = ovirt.disks.list(query=disk_query)
    for disk in disks:
        vm.disks.add(disk)
    oVirtObjectType.all_types['disk'].print_table(
        disks, show=show, headers=headers
    )
    return disks


@task
@ovirt_task
def remove_disk(vm_id, disk_id=None, disk_name=None, erase='no', ovirt=None):
    """
    Remove the specified disk from the specified VM

    :param str vm_id:      The ID of the VM to add the disk to
    :param str disk_id:    The Id of the disk to remove
    :param str disk_name`: The name of the disk to remove
    :param str erase:      'yes' to erase the removed disks from the system,
                           anything else to leave them detached. default is
                           'no'
    :param oVirtApi ovirt: An open oVirt API connection

    One of disk_id or disk_name must be specified, if both are specified,
    disk_id will be used
    """
    vm = ovirt.vms.get(id=vm_id)
    if vm is None:
        abort("VM with specified ID '{0}' not found".format(vm_id))
    if disk_id is not None:
        disk = vm.disks.get(id=disk_id)
    elif disk_name is not None:
        disk = vm.disks.get(name=disk_name)
    else:
        abort('Niether disk_id nor disk_name specified')
    if not disk:
        abort("Disk with specified ID or name not found")
    if disk.active:
        puts("Deactivating disk: {0}".format(disk.name))
        disk.deactivate(oVirtParams.Action(async=False))
    if erase == 'yes':
        puts("Erasing disk: {0}".format(disk.name))
        disk.delete(oVirtParams.Action(detach=False, async=False))
    else:
        puts("Detaching disk: {0}".format(disk.name))
        disk.delete(oVirtParams.Action(detach=True, async=False))


@task
@ovirt_task
def host_add_disk(
    size, name=None, format='raw', interface='virtio', bootable='no',
    show=None, headers='yes', ovirt=None
):
    """
    Add a disk to the VM of a fabric-managed host

    All parameters except vm_id which cannot be specified are same as for the
    'add_disk' task

    :returns: The disk that was added
    :rtype: ovirtsdk.infrastructure.brokers.Disk
    """
    with hide('user'):
        vm = from_host(ovirt=ovirt)
    if vm is None:
        abort("VM not found for host")
    disk = add_disk(
        vm_id=vm.id, size=size, name=name, format=format, interface=interface,
        bootable=bootable, show=show, headers=headers, ovirt=ovirt
    )
    return disk


@task
@ovirt_task
def host_attach_disks(disk_query, show=None, headers='yes', ovirt=None):
    """
    Attach a disk to the VM of a fabric-managed host

    All parameters except vm_id which cannot be specified are same as for the
    'attach_disk' task

    :returns: The disk that was added
    :rtype: ovirtsdk.infrastructure.brokers.Disk
    """
    with hide('user'):
        vm = from_host(ovirt=ovirt)
    if vm is None:
        abort("VM not found for host")
    disks = attach_disks(
        vm_id=vm.id, disk_query=disk_query, show=show, headers=headers,
        ovirt=ovirt
    )
    return disks


@task
@ovirt_task
def host_remove_disk(disk_id=None, disk_name=None, erase='no', ovirt=None):
    """
    Remove the specified disk from the VM of a fabric-managed host

    All parameters except vm_id which cannot be specified are same as for the
    'remove_disk' task
    """
    with hide('user'):
        vm = from_host(ovirt=ovirt)
    if vm is None:
        abort("VM not found for host")
    return remove_disk(
        vm_id=vm.id, disk_id=disk_id, disk_name=disk_name, erase=erase,
        ovirt=ovirt
    )


@task  # noqa
@ovirt_task
def create(
    name, cluster_query=None, template_query='name=Blank',
    memory=2 * GiB, vcpus=2, disk_query=None, ostype='rhel_7x64',
    networks=None,
    show=None, headers='yes', ovirt=None
):
    """
    Create a new oVirt VM

    :param str name:           The name of the VM to create
    :param str cluster_query:  A query to find the cluster to place the VM in,
                               if more then one cluster is found, the first one
                               is used
    :param str template_query: A query to find the template to use to create
                               the VM, if more then one template is found the
                               first one is used
    :param int memory:         The VM memory size (in bytes)
    :param ind vcpus:          The amount of vCPUs to assign to the VM
    :param str disk_query:     A query for disks to attach to the VM
    :param str ostype:         The OS type of the VM
    :param str networks:       A pipe (|) separated list of networks to attach
                               to the VM in the order they should be added, a
                               network can appear more then once. Only networks
                               that are attached to the VM`s cluster will be
                               added
    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    The 'show' and 'headers' parameters are the same as for the 'query' task

    :returns: The VM that was created
    :rtype: ovirtsdk.infrastructure.brokers.VM
    """
    if cluster_query is None:
        # get the 2 top clusters so we'll issue a warning if there is more then
        # one and the user didn't specify an explicit selection query
        clusters = ovirt.clusters.list(max=2)
    else:
        clusters = ovirt.clusters.list(query=cluster_query)
    if not clusters:
        abort("No cluster found by given query")
    if len(clusters) > 1:
        warn("More then one cluster found, will use the first")
    cluster = clusters[0]
    templates = ovirt.templates.list(query=template_query)
    if not templates:
        abort("No template found by given query")
    if len(templates) > 1:
        warn("More then one tempalte found, will use the first")
    template = templates[0]
    vm = ovirt.vms.add(oVirtParams.VM(
        name=name,
        template=template,
        cluster=cluster,
        memory=int(memory),
        cpu=oVirtParams.CPU(topology=oVirtParams.CpuTopology(
            sockets=int(vcpus)
        )),
        os=oVirtParams.OperatingSystem(type_=ostype),
    ))
    if disk_query is not None:
        disks = ovirt.disks.list(query=disk_query)
        for disk in disks:
            vm.disks.add(disk)
    if networks is not None:
        nic_name = ('nic{0}'.format(i) for i in count())
        for network_name in networks.split('|'):
            network = cluster.networks.get(name=network_name)
            if network is None:
                continue
            vm.nics.add(nic=oVirtParams.NIC(
                name=next(nic_name),
                network=network,
                linked=True,
            ))
    oVirtObjectType.all_types['vm'].print_table(
        (vm,), show=show, headers=headers
    )
    return vm


@task
@ovirt_task
def create_from_disk(
    disk_query, cluster_query=None, template_query='name=Blank',
    memory=2 * GiB, vcpus=2, set_disk_bootable='yes',
    networks=None,
    show=None, headers='yes', ovirt=None
):
    """
    Create oVirt VMs from the given disks. The names of the VMs will be the
    same a the names of the disks. If VMs with disk names already exist, VM
    creation will be skipped with a warning

    :param str disk_query: A query to find the disk to use, if multipile disks
                           are found, a vm will be created for each and every
                           disk
    :param str set_disk_bootable: If true mark the disk as bootable

    The cluster_query, template_query, memory, vcpus and networks parameters
    are like the ones for the 'create' task.
    The 'show' and 'headers' parameters are the same as for the 'query' task

    :param ovirtsdk.api.API ovirt: An open oVirt API connection

    :returns: The vms that were created
    :rtype: list
    """
    disks = ovirt.disks.list(query=disk_query)
    vms = []
    for disk in disks:
        if cluster_query is None:
            # If cluster is not specified, ensure we choose a cluster that is
            # attached to the storage domain that hosts the disk
            disk_sd = disk.get_storage_domains().get_storage_domain()[0]
            disk_sd = ovirt.storagedomains.get(id=disk_sd.id)
            cluster_query = "Storage={0}".format(disk_sd.name)
        with hide('user'):
            try:
                vm = create(
                    name=disk.name,
                    cluster_query=cluster_query,
                    template_query=template_query,
                    memory=memory,
                    vcpus=vcpus,
                    networks=networks,
                    ovirt=ovirt
                )
            except oVirtErrors.RequestError as e:
                if e.detail.find('VM name is already in use') < 0:
                    raise
                warn("VM '{0}' already exists".format(disk.name))
                continue
            if set_disk_bootable == 'yes':
                disk.set_bootable(True)
            disk.set_active(True)
            vm.disks.add(disk)
            vms.append(vm)
    oVirtObjectType.all_types['vm'].print_table(
        vms, show=show, headers=headers
    )
    return vms


@task
@ovirt_task
def delete(oquery, ovirt=None):
    """
    Delete VMs

    :param str oquery: a query string to select VMs to delete
    :param ovirtsdk.api.API ovirt: a connected oVirt API object

    :returns: How many VMs were deleted
    :rtype: int
    """
    vms = ovirt.vms.list(query=oquery)
    for vm in vms:
        vm.delete(action=oVirtParams.Action(async=False))
    puts('{0} VMs deleted'.format(len(vms)))
    return len(vms)
