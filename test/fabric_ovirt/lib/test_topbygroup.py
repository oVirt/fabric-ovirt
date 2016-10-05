#!/usr/bin/env python
"""test_topbygroup.py - Teests for topbygroup.py
"""
import pytest
from random import sample, randrange
from heapq import heappush
from operator import itemgetter

from fabric_ovirt.lib.topbygroup import (
    topbygroup, _topbygroup, _heappush_upto, _popall
)


@pytest.fixture
def some_numbers():
    return sample(xrange(0, 100), randrange(10, 30))


def test__popall(some_numbers):
    heap = []
    for n in some_numbers:
        heappush(heap, n)
    output = [n for n in _popall(heap)]
    assert sorted(some_numbers) == output


def test__heappush_upto(some_numbers):
    heap = []
    heap_size = 5
    for n in some_numbers:
        _heappush_upto(heap, heap_size, n)
    output = [n for n in _popall(heap)]
    assert len(output) == heap_size
    assert sorted(some_numbers)[-heap_size:] == output


@pytest.mark.parametrize(
    ('items', 'amount', 'groupkey', 'expected'),
    [
        (
            (16, 12, 19, 13, 17),
            3, None,
            [16, 12, 19, 13, 17],
        ),
        (
            (31, 36, 24, 12, 19, 17, 25, 13, 34, 37, 16),
            3, lambda x: x / 10,
            [34, 36, 37, 24, 25, 16, 17, 19],
        ),
        (
            ('xaa', 'xba', 'xbb', 'xca'),
            2, itemgetter(0),
            ['xbb', 'xca'],
        ),
    ]
)
def test__topbygroup(items, amount, groupkey, expected):
    output = [i for i in _topbygroup(items, amount, groupkey)]
    assert expected == output


@pytest.mark.parametrize(
    ('items', 'amount', 'groupkey', 'sortkey', 'expected'),
    [
        (
            (16, 12, 19, 13, 17),
            3, None, None,
            [16, 12, 19, 13, 17],
        ),
        (
            (31, 36, 24, 12, 19, 17, 25, 13, 34, 37, 16),
            3, lambda x: x / 10, None,
            [34, 36, 37, 24, 25, 16, 17, 19],
        ),
        (
            (31, 36, 24, 12, 19, 17, 25, 13, 34, 37, 16),
            3, lambda x: x / 10, lambda x: -x % 10,
            [36, 34, 31, 25, 24, 16, 13, 12],
        ),
        (
            ('xaa', 'xba', 'xbb', 'xca'),
            2, itemgetter(0), itemgetter(1),
            ['xba', 'xca'],
        ),
    ]
)
def test_topbygroup(items, amount, groupkey, sortkey, expected):
    output = [i for i in topbygroup(items, amount, groupkey, sortkey)]
    assert expected == output
