#!/usr/bin/env python
"""test_remote_files.py - Tests for fabric_ovirt.lib.remote_files
"""
from mock import MagicMock, NonCallableMagicMock, patch, call
import pytest
from itertools import izip
from urlparse import urljoin
from operator import eq, lt, gt, ne
from random import randrange
from hashlib import md5, sha256
from textwrap import dedent

from fabric_ovirt.lib import remote_files


@pytest.fixture
def some_hexdigest():
    return 'some_hexdigest'


@pytest.fixture
def mock_digest_algo(some_hexdigest):
    algo = NonCallableMagicMock()
    algo.hexdigest = MagicMock(return_value=some_hexdigest)
    return MagicMock(return_value=algo)


@pytest.fixture
def some_file_name():
    return 'some_file_name.ext'


@pytest.fixture
def some_file_url():
    return 'http://server.com/dir/file.ext'


def test_file_digest(some_hexdigest, mock_digest_algo):
    fd = remote_files.file_digest(
        hexdigest=some_hexdigest,
        algorithm=mock_digest_algo,
    )
    assert fd.hexdigest == some_hexdigest
    assert fd.algorithm == mock_digest_algo
    fd = remote_files.file_digest(some_hexdigest, mock_digest_algo)
    assert fd.hexdigest == some_hexdigest
    assert fd.algorithm == mock_digest_algo


@pytest.fixture
def some_file_digest(some_hexdigest, mock_digest_algo):
    return remote_files.file_digest(
        hexdigest=some_hexdigest,
        algorithm=mock_digest_algo,
    )


@pytest.fixture
def mock_http_with_file(request):
    content = ''.join(
        chr(randrange(0, 256))
        for x in xrange(0, 1024 * randrange(3, 10) + randrange(0, 1024))
    )

    def iter_content(chunk_size=1024):
        for i in xrange(0, len(content), chunk_size):
            yield content[i:i + chunk_size]

    mock_response = NonCallableMagicMock()
    mock_response.iter_content = MagicMock(side_effect=iter_content)
    mock_requests = NonCallableMagicMock()
    mock_requests.get = MagicMock(return_value=mock_response)
    mock_requests._mock_response = mock_response
    mock_requests._content = content

    patcher = patch(
        target='fabric_ovirt.lib.remote_files.requests',
        new=mock_requests,
    )

    def finalizer():
        patcher.stop()

    return patcher.start()


class TestRemoteFile(object):
    def test_init(self, some_file_name, some_file_url, some_file_digest):
        rf = remote_files.RemoteFile(
            name=some_file_name,
            url=some_file_url,
            digest=some_file_digest
        )
        assert rf.name == some_file_name
        assert rf.url == some_file_url
        assert rf.digest == some_file_digest
        rf = remote_files.RemoteFile(some_file_name, some_file_url)
        assert rf.name == some_file_name
        assert rf.url == some_file_url
        assert rf.digest is None

    def test_str(self, some_file_name, some_file_url):
        rf = remote_files.RemoteFile(some_file_name, some_file_url)
        assert str(rf) == some_file_name

    def test_repr(self):
        rf = remote_files.RemoteFile('nnn', 'http://xxx/yyy')
        assert repr(rf) == '<RemoteFile url=http://xxx/yyy>'

    @pytest.mark.parametrize(
        (
            'a_name', 'a_url', 'a_digest', 'b_name', 'b_url', 'b_digest',
            'expected_relation'
        ),
        [
            ('aaaa', 'http://aaaa', None, 'aaaa', 'http://aaaa', None, eq),
            ('aaaa', 'http://aaaa', None, 'aaab', 'http://aaaa', None, lt),
            ('aaab', 'http://aaaa', None, 'aaaa', 'http://aaaa', None, gt),
            ('aaaa', 'http://aaaa', None, 'aaaa', 'http://aaab', None, lt),
            ('aaaa', 'http://aaaa', '11', 'aaaa', 'http://aaaa', '11', eq),
            ('aaaa', 'http://aaaa', '11', 'aaaa', 'http://aaaa', '12', lt),
            ('aaaa', 'http://aaaa', '12', 'aaaa', 'http://aaaa', '11', gt),
        ]
    )
    def test_cmp(
        self, a_name, a_url, a_digest, b_name, b_url, b_digest,
        expected_relation
    ):
        img_a = remote_files.RemoteFile(a_name, a_url, a_digest)
        img_b = remote_files.RemoteFile(b_name, b_url, b_digest)
        assert expected_relation(img_a, img_b)

    @pytest.mark.parametrize(
        (
            'a_name', 'a_url', 'a_digest', 'b_name', 'b_url', 'b_digest',
            'expected_relation'
        ),
        [
            ('aaaa', 'http://aaaa', None, 'aaaa', 'http://aaaa', None, eq),
            ('aaaa', 'http://aaaa', None, 'aaab', 'http://aaaa', None, ne),
            ('aaab', 'http://aaaa', None, 'aaaa', 'http://aaaa', None, ne),
            ('aaaa', 'http://aaaa', None, 'aaaa', 'http://aaab', None, ne),
            ('aaaa', 'http://aaaa', '11', 'aaaa', 'http://aaaa', '11', eq),
            ('aaaa', 'http://aaaa', '11', 'aaaa', 'http://aaaa', '12', ne),
            ('aaaa', 'http://aaaa', '12', 'aaaa', 'http://aaaa', '11', ne),
        ]
    )
    def test_hash(
        self, a_name, a_url, a_digest, b_name, b_url, b_digest,
        expected_relation
    ):
        img_a = remote_files.RemoteFile(a_name, a_url, a_digest)
        img_b = remote_files.RemoteFile(b_name, b_url, b_digest)
        assert expected_relation(hash(img_a), hash(img_b))

    def test_download(self, mock_http_with_file):
        rf = remote_files.RemoteFile('nnn', 'http://xxx/yyy')
        with rf.download() as result_tf:
            assert 1 == mock_http_with_file.get.call_count
            assert (
                call('http://xxx/yyy', stream=True) ==
                mock_http_with_file.get.call_args
            )
            resp = mock_http_with_file._mock_response
            assert resp.raise_for_status.called
            assert resp.iter_content.called
            assert mock_http_with_file._content == result_tf.read()
        rf = remote_files.RemoteFile(
            'nnn', 'http://xxx/yyy', remote_files.file_digest(
                md5(mock_http_with_file._content).hexdigest(), md5
            )
        )
        with rf.download() as result_tf:
            assert mock_http_with_file._content == result_tf.read()
        rf = remote_files.RemoteFile(
            'nnn', 'http://xxx/yyy', remote_files.file_digest(
                'bad_digest_value', md5
            )
        )
        with pytest.raises(remote_files.BadFileDigest):
            rf.download()
        with rf.download(verify_digest=False) as result_tf:
            assert mock_http_with_file._content == result_tf.read()


@pytest.fixture
def mock_digests_and_files(mock_digest_algo):
    return (
        (mock_digest_algo().hexdigest(), 'file1.foo'),
        (mock_digest_algo().hexdigest(), 'file2.bar'),
    )


@pytest.fixture
def mock_http_with_digest_file(request, mock_digests_and_files):
    digest_file_lines = ('  '.join(pair) for pair in mock_digests_and_files)
    mock_response = NonCallableMagicMock()
    mock_response.iter_lines = MagicMock(return_value=digest_file_lines)
    mock_requests = NonCallableMagicMock()
    mock_requests.get = MagicMock(return_value=mock_response)
    mock_requests._mock_response = mock_response

    patcher = patch(
        target='fabric_ovirt.lib.remote_files.requests',
        new=mock_requests,
    )

    def finalizer():
        patcher.stop()

    return patcher.start()


@pytest.mark.parametrize(
    ('lines_str', 'expected_str'),
    [
        ('', ''),
        ('foo bar', 'foo bar'),
        (
            """
            -----BEGIN PGP SIGNED MESSAGE-----
            Hash: SHA1

            foo bar
            baz
            -----BEGIN PGP SIGNATURE-----
            Version: GnuPG v2.0.22 (GNU/Linux)

            iQEcBAEBAgAGBQJYFerUAAoJEL/8m8Zq8UyXmykH/3Py0H98v2VTeiBA1Lp20AvA
            MvKlVNuGnHMZ6v3zAi+872vi01Izd7tKHrvvshFP5K9wDdi7712kzNSVQJ5ZYTOY
            su5cig2hlY2HBbO0mWSvb+2mFkFHlBLKrAtyJIiNmcLlG/r4KDRlaQ0QTbzbHAHf
            Mzw/sUv6ffMhn/TSMWBt2R9atcO3eZnwK+xQ4Fe9zuVFx37N77fKF5TmHav2WlvD
            k33OAOpe6sRN+MwKbGbsGNCUPo5E9SOSWjrH9uzDG6e5mg2Nvgj9GTDeNjtElle+
            BVmahXARMF26rW4wO4WnUfUBViwg+5p4otEOnAz7D3Og86rlf8wE5Ge7vsoXPhc=
            =GFNY
            -----END PGP SIGNATURE-----
            """,
            """
            foo bar
            baz
            """
        ),
        (
            """
            unsigned text
            -----BEGIN PGP SIGNED MESSAGE-----
            Hash: SHA1

            signed text
            -----BEGIN PGP SIGNATURE-----
            does not really matter
            -----END PGP SIGNATURE-----
            more unsigned text
            -----BEGIN PGP SIGNED MESSAGE-----
            Hash: SHA1

            more signed text
            -----BEGIN PGP SIGNATURE-----
            does not really matter
            -----END PGP SIGNATURE-----
            even more unsigned text
            """,
            """
            unsigned text
            signed text
            more unsigned text
            more signed text
            even more unsigned text
            """
        ),
    ]
)
def test__strip_gpg_wrappers(lines_str, expected_str):
    lines = dedent(lines_str).lstrip().splitlines(True)
    expected = dedent(expected_str).lstrip().splitlines(True)
    output_i = remote_files._strip_gpg_wrappers(lines)
    output = list(output_i)
    assert expected == output


def test_from_http_with_digest_file(
    mock_digests_and_files, mock_digest_algo, mock_http_with_digest_file
):
    digest_file_url = 'http://server.com/dir/dfile.txt'
    rfl_iter = remote_files.from_http_with_digest_file(
        digest_file_url=digest_file_url,
        digest_algo=mock_digest_algo,
    )
    assert 0 == mock_http_with_digest_file.get.call_count
    rfl = [f for f in rfl_iter]
    assert 1 == mock_http_with_digest_file.get.call_count
    assert mock_http_with_digest_file.get.call_args[0][0] == digest_file_url
    assert len(rfl) == len(mock_digests_and_files)
    for rf, expected in izip(rfl, mock_digests_and_files):
        exp_digest, exp_file = expected
        assert rf.name == exp_file
        assert rf.digest.hexdigest == exp_digest
        assert rf.digest.algorithm == mock_digest_algo
        assert rf.url == urljoin(digest_file_url, exp_file)


@pytest.mark.parametrize(
    ('lines_str', 'expected_rf_data'),
    [
        (
            """
            SHA256 (foo.qcow2) = foo_hash
            SHA256 (bar.qcow2) = bar_hash
            """,
            (
                ('foo.qcow2', 'u/foo.qcow2', 'foo_hash', sha256),
                ('bar.qcow2', 'u/bar.qcow2', 'bar_hash', sha256),
            )
        ),
    ]
)
def test__from_fedora_file_lines(lines_str, expected_rf_data):
    lines = dedent(lines_str).lstrip().splitlines(True)
    expected = tuple(
        remote_files.RemoteFile(
            name,
            url,
            remote_files.file_digest(digest, algo)
        )
        for name, url, digest, algo in expected_rf_data
    )
    output_i = remote_files._from_fedora_file_lines('u/u', lines)
    output = tuple(output_i)
    assert expected == output
