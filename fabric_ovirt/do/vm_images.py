#!/usr/bin/env python
#
from fabric.api import task, prompt
from fabric.utils import puts, abort

from fabric_ovirt.lib.utils import yellow, green
from fabric_ovirt.lib import remote_images


@task
def list_sources():
    """List known VM image sources"""
    for src in remote_images.sources.iterkeys():
        puts(src)


@task
def list_images(source):
    """List known VM images

    :param src source: NAme of image source to list images from
    """
    if source not in remote_images.sources:
        abort('No such image source "{}"'.format(source))
    for img in sorted(remote_images.list_from(source)):
        puts(img.name)


@task
def update_glance(auth_url, tenant_name, username, password, sure='no'):
    """Update Glance with new upstream images

    :param str auth_url:    URL for Keystone that is managing auth for Glance
    :param str tenant_name: OpenStack tenant to authenticate as
    :param str username:    OpenStack user to authenticate as
    :param str password:    OpenStack password to authenticate as
    :param str sure:        'yes' to not propmt for confirmation before update
    """
    glance = remote_images.Glance(
        auth_url=auth_url,
        tenant_name=tenant_name,
        username=username,
        password=password,
    )
    missing_images = sorted(
        set(remote_images.from_all_latest_upstream()) -
        set(glance)
    )
    if not missing_images:
        return
    puts(yellow("Going to upload {n} images to glance:\n{images}".format(
        n=len(missing_images),
        images='\n'.join('  - ' + img.name for img in missing_images)
    )))
    if sure != 'yes' and prompt("Continue (yes|no)? ", default='no') != 'yes':
        return
    for img in missing_images:
        puts(green("Uploading: {}".format(img.name)))
        glance.add(img)


@task
def clean_glance(auth_url, tenant_name, username, password, sure='no'):
    """Clean old images from Glance

    :param str auth_url:    URL for Keystone that is managing auth for Glance
    :param str tenant_name: OpenStack tenant to authenticate as
    :param str username:    OpenStack user to authenticate as
    :param str password:    OpenStack password to authenticate as
    :param str sure:        'yes' to not propmt for confirmation before update
    """
    glance = remote_images.Glance(
        auth_url=auth_url,
        tenant_name=tenant_name,
        username=username,
        password=password,
    )
    glance_up_to_date = remote_images.top_latest(glance)
    obsolete = sorted(set(glance) - set(glance_up_to_date))
    if not obsolete:
        return
    puts(yellow("Going to remove {n} images to glance:\n{images}".format(
        n=len(obsolete),
        images='\n'.join('  - ' + img.name for img in obsolete)
    )))
    if sure != 'yes' and prompt("Continue (yes|no)? ", default='no') != 'yes':
        return
    for img in obsolete:
        puts(green("Removing: {}".format(img.name)))
        glance.remove(img)
