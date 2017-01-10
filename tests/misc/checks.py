# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from translate.filters.checks import FilterFailure

from pootle_misc.checks import (Category, ENChecker, check_names,
                                get_category_code, get_category_name,
                                get_qualitychecks, get_qualitycheck_list,
                                get_qualitycheck_schema)


checker = ENChecker()


def assert_check(check, source_string, target_string, should_skip, **kwargs):
    """Runs `check` and asserts whether it should be skipped or not for the
    given `source_string` and `target_string`.

    :param check: Checker function.
    :param source_string: Source string.
    :param target_string: Target string.
    :param should_skip: Whether the check should be skipped.
    """
    try:
        assert should_skip == check(source_string, target_string, **kwargs)
    except FilterFailure:
        assert not should_skip


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('$1 aa $2', '$1 dd $2', True),
    ('$1 aa $2', '$1dd$2', True),
])
def test_dollar_sign_check(source_string, target_string, should_skip):
    check = checker.dollar_sign_placeholders
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('foo bar', 'FOO BAR', True),
    ('foo "bar"', '"FOO" <BAR>', True),
    ('foo "bar"', 'FOO <BAR>', True),
    ('foo <a href="bar">foo bar</a>',
     'FOO <a href="BAR">FOO BAR</a>', True),
    ('"foo" <a href="bar">"foo" bar</a>', 'FOO <a href="BAR">FOO BAR</a>', True),
    ('<a href="bar>foo bar</a>', 'FOO BAR', False),
    ('foo bar', '<a href="BAR">FOO BAR</a>', True),
    ('foo bar', '<a href="BAR>FOO BAR</a>', False),
    ('foo <a href="bar">foo bar</a>', 'FOO <a href="BAR>FOO BAR</a>', False),
    ('foo <a href="bar">foo bar</a>', 'FOO <a href=\'BAR\'>FOO BAR</a>', False),
    ('foo <a href="<?php echo("bar");?>">foo bar</a>',
     'FOO <a href="<?php echo("BAR");?>">FOO BAR</a>', True),
    ('foo <a href="<?php echo("bar");?>">foo bar</a>',
     'FOO <a href="<?php echo(\'BAR\');?>">FOO BAR</a>', False),
])
def test_double_quotes_in_tags(source_string, target_string, should_skip):
    check = checker.double_quotes_in_tags
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('A and B', 'A и B', True),
    ('A and B', 'A & B', True),
    ('A and B', 'A &amp; B', True),
    ('A & B', 'A и B', True),
    ('A & B', 'A & B', True),
    ('A &amp; B', 'A и B', True),
    ('A &amp; B', 'A & B', False),
    ('A &amp; B', 'A &amp; B', True),
    ('A &amp; B &amp; C', 'A &amp; B & C', False),
    ('A &amp; B & C', 'A и B и C', True),
    ('A &amp; B & C', 'A & B & C', False),
    ('A &amp; B & C', 'A &amp; B &amp; C', True),
    ('A &amp; B & C', 'A &amp; B & C', False),
    ("A &quot; B &amp; C", "A &quot; B &amp; C", True),
])
def test_unescaped_ampersands(source_string, target_string, should_skip):
    check = checker.unescaped_ampersands
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('A and B', 'A и B', True),
    ('A and B', 'A & B', True),
    ('A and B', 'A &amp; B', True),
    ('A and B and C', 'A &amp; B & C ', False),
    ('A & B', 'A и B', True),
    ('A & B', 'A & B', True),
    ('A & B', 'A &amp; B', False),
    ('A & B & C', 'A &amp; B & C', False),
    ('A &amp; B', 'A и B', True),
    ('A &amp; B', 'A &amp; B', True),
    ('A &amp; B & C', 'A и B и C', True),
    ('A &amp; B & C', 'A &amp; B &amp; C', False),
    ("A &quot; B &amp; C", "A &quot; B &amp; C", True),
])
def test_incorrectly_escaped_ampersands(source_string, target_string, should_skip):
    check = checker.incorrectly_escaped_ampersands
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('NAME_COUNT', 'name_count', False),
    ('NAME_COUNT', 'NaMe_CouNT', False),
    ('NAME_COUNT', 'NAME_COUNT', True),

    ('NAME6_', 'name_', False),
    ('NAME6_', 'name_count', False),
    ('NAME6_', 'NAME7_', False),
    ('NAME6_', 'NAME6_', True),
])
def test_uppercase_placeholders(source_string, target_string, should_skip):
    check = checker.uppercase_placeholders
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('foobar', '{foo}BAR', True),
    ('{foo}bar', '{foo}BAR', True),
    ('{{foo}}bar', '{{foo}}BAR', True),
    ('{{{foo}}}bar', '{{{foo}}}BAR', True),

    ('{{foo}}bar{{foobar}}', '{{foobar}}BAR{{foo}}', True),

    ('{1, foo}bar{{foobar}}', '{1, foo}BAR{{foobar}}', True),
    ('bar {1, foo}bar{{foobar}}', 'BAR {1, FOO}BAR{{foobar}}', False),

    ('{foo}bar', '{Foo}BAR', False),
    ('{{foo}}bar', '{{Foo}}BAR', False),
    ('{{{foo}}}bar', '{{{Foo}}}BAR', False),

    ('{{foo}}bar', '{foo}}BAR', False),
    ('{{{foo}}}bar', '{{foo}}}BAR', False),
    ('{{foo}}bar', '{{foo}BAR', False),
    ('{{{foo}}}bar', '{{{foo}}BAR', False),

    ('{{#a}}a{{/a}}', '{{#a}}A{{a}}', False),
    ('{{a}}a{{/a}}', '{{a}}A{{a}}', False),
    ('{{#a}}a{{/a}}', '{{#a}}A', False),
    ('{{#a}}a{{/a}}', '{{#a}}A{{/s}}', False),

    ('{{a}}a{{/a}}', '{{a}}A', False),
    ('{{a}}a{{/a}}', '{{a}}A{{a}}', False),
    ('{{a}}a{{/a}}', '{{a}}A{{/s}}', False),
    ('{{#a}}a{{/a}}', '{{a}}A{{/a#}}', False),
    ('{{#a}}a{{/a}}', '{{# a}}A{{/ a}}', False),

    # The check should fire when placeholders are translated
    ('{{FOO}}a{{/FOO}}', '{{OOF}}A{{/OOF}}', False),
    ('{{FOO}}a{{BAR}}', '{{FOO}}A{{RAB}}', False),
    ('{{FOO}}a{{BAR}}', '{{OOF}}A{{BAR}}', False),
    ('{{FOO}}a{{BAR}}', '{{OOF}}A{{RAB}}', False),
])
def test_mustache_placeholders(source_string, target_string, should_skip):
    check = checker.mustache_placeholders
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('{foo}% bar', '%{foo} BAR', True),
    ('%{foo} bar', '%{foo} BAR', True),
    ('%{foo} bar', '% {foo} BAR', False),
])
def test_percent_brace_placeholders(source_string, target_string, should_skip):
    check = checker.percent_brace_placeholders
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('{{#a}}a{{/a}}', '{{#a}}A{{/a}}', True),

    ('{{#a}}a', '{{#a}}A', False),
    ('{{#a}}a{{/a}}', '{{#a}}A', False),
    ('{{#a}}a{{/a}}', '{{#a}}A{{#a}}', False),
    ('{{#a}}a{{/a}}', '{{#a}}A{{a}}', False),
    ('{{#a}}a{{/a}}', '{{/a}}A{{#a}}', False),
    ('{{#a}}a{{/a}}', '{{a}}A{{/a}}', False),
    ('{{#a}}a{{/a}}', '{{#a}}A{{/s}}', False),

    ('{{#a}}a{{/a}}', '{{a}}A{{/a#}}', False),
    ('{{#a}}a{{/a}}', '{{#a}}A{{/ a}}', False),
])
def test_mustache_placeholder_pairs(source_string, target_string, should_skip):
    check = checker.mustache_placeholder_pairs
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('a', 'A', True),
    ('{{a}}a', '{{a}}A', True),
    ('{{a}}a{{/a}}', '{{a}}A{{/a}}', True),
    ('a {{#a}}a{{/a}}', 'A {{#a}}A{{/a}}', True),

    ('foo {{a}}a{{/a}}', 'FOO {{/a}}A{{a}}', False),
    ('foo {{a}}a{{/a}}', 'FOO {{a}}A{{/s}}', False),
    ('foo {{a}}a{{/a}}', 'FOO {{a}}A{{/s}}', False),
    ('foo {{a}}a{{/a}}', 'FOO {{a}}A{{/ a}}', False),
])
def test_mustache_like_placeholder_pairs(source_string, target_string, should_skip):
    check = checker.mustache_like_placeholder_pairs
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('', '', True),
    ('{a}', '{a}', True),
    ('{{a}}', '{{a}', False),
])
def test_unbalanced_curly_braces(source_string, target_string, should_skip):
    check = checker.unbalanced_curly_braces
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('a', 'A', True),
    ('<a href="">a</a>', '<a href="">a</a>', True),
    ('<a href="">a</a>', '<a href="">a<a>', False),
    ('<a class="a">a</a>', '<b class="b">a</b>', False),
])
def test_tags_differ(source_string, target_string, should_skip):
    check = checker.tags_differ
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('&Foo', 'Foo', False),
    ('&Foo', '_Foo', False),
    ('&Foo', '^Foo', False),

    ('^Foo', 'Foo', False),
    ('^Foo', '_Foo', False),
    ('^Foo', '&Foo', False),

    ('_Foo', 'Foo', False),
    ('_Foo', '&Foo', False),
    ('_Foo', '^Foo', False),

    ('&Foo', '&foo', True),
    ('&Foo', 'bar&foo', True),

    ('^Foo', '^foo', True),
    ('^Foo', 'bar^foo', True),

    ('_Foo', '_foo', True),
    ('_Foo', 'bar_foo', True),
])
def test_accelerators(source_string, target_string, should_skip):
    check = checker.accelerators
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ('foo bar?<br>&#13;', 'FOO BAR<br>&#13;', True),
    ('foo &#65535;', 'FOO &#65535;', True),
    ('foo &#xff;', 'FOO &#xff;', True),
    ('foo &#65535;', 'FOO &#65536;', False),
    ('foo &nbsp;', 'FOO &nbsp', False),
])
def test_broken_entities(source_string, target_string, should_skip):
    check = checker.broken_entities
    assert_check(check, source_string, target_string, should_skip)


@pytest.mark.parametrize('source_string, target_string, should_skip', [
    ("EEE, MMM d h:mm a", "EEE, MMM d HH:mm", True),
    ("EEE, MMM", "EEEMMM", False),
    ("yyyy.MM.dd G 'at' HH:mm:ss z",
     "yyyy.MM.dd G 'в' HH:mm:ss z", True),
    ("EEE, MMM d, ''yy", "dd-MM-yy", True),
    ("h:mm a", "dd-MM-yy", True),
    ("hh 'o''clock' a, zzzz", "dd-MM-yy", True),
    ("K:mm a, z", "dd-MM-yy", True),
    ("yyyyy.MMMMM.dd GGG hh:mm aaa", "dd-MM-yy", True),
    ("EEE, d MMM yyyy HH:mm:ss Z", "dd-MM-yy", True),
    ("yyyy-MM-dd'T'HH:mm:ss.SSSZ", "dd-MM-yy", True),
    ("yyyy-MM-dd'T'HH:mm:ss.SSSXXX", "dd-MM-yy", True),
    ("YYYY-'W'ww-u", "dd-MM-yy", True),

    # if a string isn't a date_format string the check should be skipped
    ("yyMMddHHmmssZ", "what ever 345", True),
    ("F", "what ever 345", True),
    ("M", "what ever 345", True),
    ("S", "what ever 345", True),
    ("W", "what ever 345", True),
])
def test_date_format(source_string, target_string, should_skip):
    check = checker.date_format
    assert_check(check, source_string, target_string, should_skip)


def test_get_qualitycheck_schema():
    d = {}
    checks = get_qualitychecks()
    for check, cat in list(checks.items()):
        if cat not in d:
            d[cat] = {
                'code': cat,
                'name': get_category_code(cat),
                'title': get_category_name(cat),
                'checks': []
            }
        d[cat]['checks'].append({
            'code': check,
            'title': "%s" % check_names.get(check, check),
            'url': ''
        })

    result = sorted([item for item in list(d.values())],
                    key=lambda x: x['code'],
                    reverse=True)

    assert result == get_qualitycheck_schema()


@pytest.mark.django_db
def test_get_qualitycheck_list(tp0):
    result = []
    checks = get_qualitychecks()
    for check, cat in list(checks.items()):
        result.append({
            'code': check,
            'is_critical': cat == Category.CRITICAL,
            'title': "%s" % check_names.get(check, check),
            'url': tp0.get_translate_url(check=check)
        })

    def alphabetical_critical_first(item):
        sort_prefix = 0 if item['is_critical'] else 1
        return "%d%s" % (sort_prefix, item['title'].lower())

    result = sorted(result, key=alphabetical_critical_first)

    assert result == get_qualitycheck_list(tp0)
