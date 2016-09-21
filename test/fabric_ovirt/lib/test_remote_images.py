#!/usr/bin/env python
"""test_remote_images.py - Tests for fabric_ovirt.lib.remote_images
"""
import pytest
from hashlib import md5
from operator import eq, lt, gt, ne

from fabric_ovirt.lib import remote_images
from fabric_ovirt.lib.remote_images import (
    RemoteImage, file_digest, LooseVersion
)
from fabric_ovirt.lib.remote_files import RemoteFile


class TestRemoteImage(object):
    def test_init(self):
        some_name = 'The Cool Image v13.4-b16 for x86_64'
        some_url = 'http://exapmle.com/dir/coolimg-13.4-b16-x86.64.qcow2'
        some_digest = remote_images.file_digest('abdcdef1234567890', md5)
        some_image_name = 'coolimg'
        some_version = remote_images.LooseVersion('13.4')
        some_revision = remote_images.LooseVersion('b16')
        some_arch = 'x86_64'

        ri = remote_images.RemoteImage(
            name=some_name,
            url=some_url,
            digest=some_digest,
            image_name=some_image_name,
            version=some_version,
            revision=some_revision,
            arch=some_arch
        )
        assert ri.name == some_name
        assert ri.url == some_url
        assert ri.digest == some_digest
        assert ri.image_name == some_image_name
        assert ri.version == some_version
        assert ri.revision == some_revision
        assert ri.arch == some_arch

        ri = remote_images.RemoteImage(
            some_name, some_url,
            some_image_name, some_version, some_arch, some_revision,
            some_digest
        )
        assert ri.name == some_name
        assert ri.url == some_url
        assert ri.digest == some_digest
        assert ri.image_name == some_image_name
        assert ri.version == some_version
        assert ri.revision == some_revision
        assert ri.arch == some_arch

        ri = remote_images.RemoteImage(
            name=some_name,
            url=some_url,
            image_name=some_image_name,
            version=some_version,
            arch=some_arch
        )
        assert ri.name == some_name
        assert ri.url == some_url
        assert ri.digest is None
        assert ri.image_name == some_image_name
        assert ri.version == some_version
        assert ri.revision is None
        assert ri.arch == some_arch

    def test_str(self):
        some_name = 'The Cool Image v13.4-b16 for x86_64'
        rf = remote_images.RemoteImage(
            some_name, 'http://xxx/yyy',
            'the_image', '1.0', 'ppc64'
        )
        assert str(rf) == some_name

    def test_repr(self):
        rf = remote_images.RemoteImage(
            'The cool image', 'http://xxx/yyy',
            'the_image', '1.0', 'ppc64'
        )
        assert repr(rf) == '<RemoteImage url=http://xxx/yyy>'

    @pytest.mark.parametrize(
        (
            'a_image_name', 'a_arch', 'a_version', 'a_revision', 'a_name',
            'a_url', 'a_digest',
            'b_image_name', 'b_arch', 'b_version', 'b_revision', 'b_name',
            'b_url', 'b_digest',
            'expected_relation'
        ),
        [
            (
                'a', 'x86_64', 1, None, 'a', 'http://1a', None,
                'a', 'x86_64', 1, None, 'a', 'http://1a', None,
                eq
            ),
            (
                'a', 'x86_64', 1, None, 'a', 'http://2a', None,
                'a', 'ppc64', 1, None, 'a', 'http://2a', None,
                gt
            ),
            (
                'a', 'x86_64', 1, None, 'a', 'http://3a', None,
                'b', 'x86_64', 1, None, 'a', 'http://3a', None,
                lt
            ),
            (
                'b', 'x86_64', 1, None, 'a', 'http://4a', None,
                'a', 'x86_64', 1, None, 'a', 'http://4a', None,
                gt
            ),
            (
                'a', 'x86_64', 1, None, 'a', 'http://5a', None,
                'a', 'x86_64', 2, None, 'a', 'http://5a', None,
                lt
            ),
            (
                'a', 'x86_64', 1, 2, 'a', 'http://6a', None,
                'a', 'x86_64', 2, 1, 'a', 'http://6a', None,
                lt
            ),
            (
                'a', 'x86_64', 1, 2, 'a', 'http://7a', None,
                'a', 'x86_64', 1, 1, 'a', 'http://7a', None,
                gt
            ),
            (
                'a', 'x86_64', 1, None, 'a', 'http://8a', None,
                'a', 'x86_64', 1, None, 'a', 'http://8b', None,
                eq
            ),
            (
                'a', 'x86_64', 1, None, 'a', 'http://9a', None,
                'a', 'x86_64', 1, None, 'a', 'http://9a', 'foo',
                eq
            ),
        ]
    )
    def test_cmp(
        self,
        a_image_name, a_arch, a_version, a_revision, a_name, a_url, a_digest,
        b_image_name, b_arch, b_version, b_revision, b_name, b_url, b_digest,
        expected_relation
    ):
        img_a = RemoteImage(
            a_name, a_url, a_image_name, a_version, a_arch, a_revision,
            a_digest
        )
        img_b = RemoteImage(
            b_name, b_url, b_image_name, b_version, b_arch, b_revision,
            b_digest
        )
        assert expected_relation(img_a, img_b)

    @pytest.mark.parametrize(
        (
            'a_image_name', 'a_arch', 'a_version', 'a_revision', 'a_name',
            'a_url', 'a_digest',
            'b_image_name', 'b_arch', 'b_version', 'b_revision', 'b_name',
            'b_url', 'b_digest',
            'expected_relation'
        ),
        [
            (
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://1a', None,
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://1a', None,
                eq
            ),
            (
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://2a', None,
                'a', 'ppc64', LooseVersion('1'), None, 'a', 'http://2a', None,
                ne
            ),
            (
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://3a', None,
                'b', 'x86_64', LooseVersion('1'), None, 'a', 'http://3a', None,
                ne
            ),
            (
                'b', 'x86_64', LooseVersion('1'), None, 'a', 'http://4a', None,
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://4a', None,
                ne
            ),
            (
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://5a', None,
                'a', 'x86_64', LooseVersion('2'), None, 'a', 'http://5a', None,
                ne
            ),
            (
                'a', 'x86_64', LooseVersion('1'), LooseVersion('2'), 'a',
                'http://6a', None,
                'a', 'x86_64', LooseVersion('2'), LooseVersion('1'), 'a',
                'http://6a', None,
                ne
            ),
            (
                'a', 'x86_64', LooseVersion('1'), LooseVersion('2'), 'a',
                'http://6a', None,
                'a', 'x86_64', LooseVersion('2'), LooseVersion('1'), 'a',
                'http://6a', None,
                ne
            ),
            (
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://8a', None,
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://8b', None,
                eq
            ),
            (
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://9a', None,
                'a', 'x86_64', LooseVersion('1'), None, 'a', 'http://9a', 'fo',
                eq
            ),
        ]
    )
    def test_hash(
        self,
        a_image_name, a_arch, a_version, a_revision, a_name, a_url, a_digest,
        b_image_name, b_arch, b_version, b_revision, b_name, b_url, b_digest,
        expected_relation
    ):
        img_a = RemoteImage(
            a_name, a_url, a_image_name, a_version, a_arch, a_revision,
            a_digest
        )
        img_b = RemoteImage(
            b_name, b_url, b_image_name, b_version, b_arch, b_revision,
            b_digest
        )
        assert expected_relation(hash(img_a), hash(img_b))


@pytest.mark.parametrize(
    ('filenames', 'regex', 'kwargs', 'expected'),
    [
        (
            (
                'CentOS-6-x86_64-GenericCloud-1608.qcow2',
                'CentOS-6-x86_64-GenericCloud-1608.qcow2.xz'
            ),
            '^CentOS-6-(?P<arch>.+)-GenericCloud-(?P<version>.+)\.qcow2$',
            dict(
                name='CentOS 6 Generic Cloud Image v\g<version> for \g<arch>',
                image_name='CentOS 6 Generic Cloud Image',
            ),
            [
                RemoteImage(
                    name='CentOS 6 Generic Cloud Image v1608 for x86_64',
                    url='u/CentOS-6-x86_64-GenericCloud-1608.qcow2',
                    digest=file_digest('abdcdef1234567890', md5),
                    image_name='CentOS 6 Generic Cloud Image',
                    version=LooseVersion('1608'),
                    revision=None,
                    arch='x86_64'
                ),
            ]
        ),
        (
            (
                'CentOS-Atomic-Host-7.20151101-Vagrant-Libvirt.box',
                'CentOS-Atomic-Host-7.20160129-GenericCloud.qcow2',
                'CentOS-Atomic-Host-7.1606-Vagrant-Libvirt.box',
                'CentOS-Atomic-Host-7.1607-GenericCloud.qcow2',
                'CentOS-Atomic-Host-7.1607-GenericCloud.qcow2.xz',
            ),
            '^CentOS-Atomic-Host-7.(?P<version>\d{4})-GenericCloud.qcow2$',
            dict(
                name='CentOS 7 Atomic Host Image v\g<version> for x86_64',
                image_name='CentOS 7 Atomic Host Image',
                arch='x86_64',
            ),
            [
                RemoteImage(
                    name='CentOS 7 Atomic Host Image v1607 for x86_64',
                    url='u/CentOS-Atomic-Host-7.1607-GenericCloud.qcow2',
                    digest=file_digest('abdcdef1234567890', md5),
                    image_name='CentOS 7 Atomic Host Image',
                    version=LooseVersion('1607'),
                    revision=None,
                    arch='x86_64'
                ),
            ]
        ),
    ]
)
def test_from_files_by_regex(filenames, regex, kwargs, expected):
    some_digest = file_digest('abdcdef1234567890', md5)
    files = (
        RemoteFile(name, 'u/' + name, some_digest)
        for name in filenames
    )
    result = remote_images.from_files_by_regex(files, regex, **kwargs)
    assert expected == [o for o in result]
