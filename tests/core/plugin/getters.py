# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from pootle.core.plugin import getter
from pootle.core.plugin.delegate import Getter


# Every Getter() below used to pass providing_args=["foo"] - dropped
# throughout this file, same reason as pootle/core/signals.py's own
# comment (the arg name was never meaningful here anyway, just
# exercising the Getter/Provider mechanism itself). Phase 2 rung 2
# (Django 2.2 -> 3.2); see PORTING.md.
def test_getter():

    get_test = Getter()

    @getter(get_test)
    def getter_for_get_test(*args, **kwargs):
        return 2

    assert get_test.get() == 2


def test_no_getter():

    get_test = Getter()

    assert get_test.get() is None


def test_getter_with_arg():

    get_test = Getter()

    @getter(get_test)
    def getter_for_get_test(*args, **kwargs):
        return kwargs["foo"]

    assert get_test.get(foo=3) == 3


def test_getter_with_with_sender():

    get_test = Getter()

    @getter(get_test, sender=str)
    def getter_for_get_test(sender, *args, **kwargs):
        return kwargs["foo"]

    assert get_test.get(str, foo="BOOM") == "BOOM"


def test_getter_with_with_sender_int():

    get_test = Getter()

    @getter(get_test, sender=int)
    def getter_for_get_test(sender, *args, **kwargs):
        return kwargs["foo"] * 7

    assert get_test.get(int, foo=3) == 21


def test_getter_with_with_sender_multi():

    get_test = Getter()

    @getter(get_test)
    def getter_for_get_test(sender, *args, **kwargs):
        if sender is int:
            return kwargs["foo"] * 7
        return int(kwargs["foo"]) * 7

    assert get_test.get(str, foo="3") == 21
    assert get_test.get(int, foo=3) == 21


def test_getter_handle_multi():

    get_test = Getter()
    get_test_2 = Getter()

    @getter([get_test, get_test_2])
    def getter_for_get_test(sender, *args, **kwargs):
        return kwargs["foo"]

    assert get_test.get(str, foo="test 1") == "test 1"
    assert get_test_2.get(str, foo="test 2") == "test 2"


def test_getter_multi_sender():
    get_test = Getter()

    @getter(get_test, sender=(str, int))
    def getter_for_get_test(sender, *args, **kwargs):
        return kwargs["foo"]

    assert get_test.get(str, foo="test") == "test"
    assert get_test.get(int, foo="test") == "test"


def test_getter_handle_order():

    get_test = Getter()

    @getter(get_test)
    def getter_for_get_test(sender, *args, **kwargs):
        pass

    @getter(get_test)
    def getter_for_get_test_2(sender, *args, **kwargs):
        return 2

    assert get_test.get(str, foo="bar") == 2


def test_getter_handle_order_2():

    get_test = Getter()

    @getter(get_test)
    def getter_for_get_test(sender, *args, **kwargs):
        return 1

    @getter(get_test)
    def getter_for_get_test_2(sender, *args, **kwargs):
        return 2

    assert get_test.get(str, foo="bar") == 1


def test_getter_handle_order_3():

    get_test = Getter()

    @getter(get_test)
    def getter_for_get_test(sender, *args, **kwargs):
        pass

    @getter(get_test)
    def getter_for_get_test_2(sender, *args, **kwargs):
        return 2

    @getter(get_test)
    def getter_for_get_test_3(sender, *args, **kwargs):
        return 3

    assert get_test.get(str, foo="bar") == 2
