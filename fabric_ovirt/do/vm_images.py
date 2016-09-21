#!/usr/bin/env python
#
from fabric.api import task
from fabric.utils import puts, abort

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
    for img in remote_images.list_from(source):
        puts(img.name)
