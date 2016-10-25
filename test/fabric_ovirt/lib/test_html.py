#!/usr/bin/env python
"""test_html.py - Testing for html.py
"""
import pytest

from fabric_ovirt.lib.html import (
    _tagFinder, find_tags_in_stream, find_hrefs_in_stream
)


@pytest.fixture
def some_html():
    return """<html>
<head>
<title>Just some HTML</title>
</head>

<body>
    <h1>A heading</h1>
    <p class="the_para">The praragraph</p>
    <p>Some other paragraph</p>
    <p>Paragraph with <a href="foo">link</a></p>
    <ul class="cool-list">
        <li>List item</li>
        <li class="classed-li">With <a href="bar">rel link</a></li>
        <li>With <a href="/baz">abs link<a></li>
        <li>With <a href="dir/">dir link</a></li>
        <li>With <a href="top/sub/">subdir link</a></li>
    </ul>
</body>
"""


@pytest.fixture
def some_html_stream(some_html):
    ck_size = 10
    return (
        some_html[i:i + ck_size] for i in xrange(0, len(some_html), ck_size)
    )


class Test_tagFinder(object):
    @pytest.mark.parametrize(
        ('param', 'attribute'),
        [
            ('a', set(('a',))),
            (('ul', 'li'), set(('ul', 'li'))),
        ]
    )
    def test_init(self, param, attribute):
        tf = _tagFinder(param)
        assert attribute == tf._tags_to_find

    @pytest.mark.parametrize(
        ('tags_to_find', 'found_tags'),
        [
            ('h1', [('h1', [])]),
            ('p', [('p', [('class', 'the_para')]), ('p', []), ('p', [])]),
            (('h1', 'ul'), [('h1', []), ('ul', [('class', 'cool-list')])]),
        ]
    )
    def test_found_tags(self, some_html, tags_to_find, found_tags):
        tf = _tagFinder(tags_to_find)
        tf.feed(some_html)
        assert found_tags == tf.found_tags


def test_find_tags_in_stream(some_html_stream):
    expected = [('body', []), ('h1', []), ('ul', [('class', 'cool-list')])]
    output_i = find_tags_in_stream(('body', 'h1', 'ul'), some_html_stream)
    output = [x for x in output_i]
    assert expected == output


def test_find_hrefs_in_stream(some_html_stream):
    expected = ['foo', 'bar', '/baz', 'dir/', 'top/sub/']
    output_i = find_hrefs_in_stream(some_html_stream)
    output = [x for x in output_i]
    assert expected == output
