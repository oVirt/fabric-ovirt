#!/usr/bin/env python
"""html.py - HTML manipulation functions
"""
from HTMLParser import HTMLParser
from collections import Iterable
from types import StringTypes


class _tagFinder(HTMLParser, object):
    def __init__(self, tags_to_find):
        super(_tagFinder, self).__init__()
        if isinstance(tags_to_find, StringTypes):
            self._tags_to_find = set((tags_to_find,))
        elif isinstance(tags_to_find, Iterable):
            self._tags_to_find = set(tags_to_find)
        else:
            self._tags_to_find = set((tags_to_find,))
        self.found_tags = []

    def handle_starttag(self, tag, attrs):
        if tag in self._tags_to_find:
            self.found_tags.append((tag, attrs))


def find_tags_in_stream(tags_to_find, stream):
    """Find the given HTML tags in the given HTML data stream"""
    tf = _tagFinder(tags_to_find)
    for chunk in stream:
        tf.feed(chunk)
        for tag in tf.found_tags:
            yield tag
        tf.found_tags = []


def find_hrefs_in_stream(stream):
    """Find the urls pointed to by HTML links in the given HTML stream"""
    for tag, attrs in find_tags_in_stream('a', stream):
        href = next((val for attr, val in attrs if attr == 'href'), None)
        if href is not None:
            yield href
