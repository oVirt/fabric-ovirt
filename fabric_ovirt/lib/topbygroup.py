#!/usr/bin/env python
"""Function for finding the top N items for each group if items in a collection
"""
from collections import OrderedDict
from itertools import count, izip, imap, chain, tee
from heapq import heappush, heappop, heappushpop
from operator import itemgetter


def topbygroup(items, amount, groupkey=None, sortkey=None):
    """Divide items to groups and return top 'amount' items per-group

    :param Iterable items:    Iterable of items to group
    :param int amount:        How many items to leave per-group
    :param Callable groupkey: Function to extract item ket to group by
    :param Callable sortkey:  Function to extract key to sort items by to
                              decide which ar the top ones

    When multipile items are equivalent as far as sorting goes, items coming
    first will be considered 'bigger' then following items

    :rtype: Iterator
    """
    if sortkey is None:
        wrapped_items = izip(items, count(0, -1))
        unwrapper = itemgetter(0)
    else:
        items, items_2 = tee(items)
        item_keys = imap(sortkey, items_2)
        wrapped_items = izip(item_keys, count(0, -1), items)
        unwrapper = itemgetter(2)
    if groupkey:
        groupkey_unwrapper = (lambda it: groupkey(unwrapper(it)))
    else:
        groupkey_unwrapper = unwrapper
    return imap(
        unwrapper,
        _topbygroup(wrapped_items, amount, groupkey_unwrapper)
    )


def _topbygroup(items, amount, groupkey=None):
    """Implement topbygroup without support for sort keys or duplicate items
    """
    heapdict = OrderedDict()
    if groupkey is None:
        groupkey = _identity
    for item in items:
        heap = heapdict.setdefault(groupkey(item), [])
        _heappush_upto(heap, amount, item)
    return chain.from_iterable(imap(_popall, heapdict.itervalues()))


def _heappush_upto(heap, amount, item):
    """Push itmes into a heap keeping the heap at 'amount' length
    """
    if len(heap) >= amount:
        heappushpop(heap, item)
    else:
        heappush(heap, item)


def _identity(x):
    return x


def _popall(heap):
    while heap:
        yield heappop(heap)
