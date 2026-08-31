# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.


from pootle_fs.exceptions import (
    FSAddError, FSFetchError, FSStateError, FSSyncError)


# Python 2's BaseException.__repr__() rendered a single-arg exception
# as "ExceptionType('message',)" (literal repr of the args tuple);
# Python 3's omits the trailing comma for the single-arg case:
# "ExceptionType('message')". Not a Pootle behaviour change - none of
# these exception classes define their own __repr__. Phase 1 Python 3
# port; see PORTING.md.


def test_error_fs_add():
    error = FSAddError("it went pear shaped")
    assert repr(error) == "FSAddError('it went pear shaped')"
    assert str(error) == "it went pear shaped"
    assert error.message == "it went pear shaped"


def test_error_fs_fetch():
    error = FSFetchError("it went pear shaped")
    assert repr(error) == "FSFetchError('it went pear shaped')"
    assert str(error) == "it went pear shaped"
    assert error.message == "it went pear shaped"


def test_error_fs_state():
    error = FSStateError("it went pear shaped")
    assert repr(error) == "FSStateError('it went pear shaped')"
    assert str(error) == "it went pear shaped"
    assert error.message == "it went pear shaped"


def test_error_fs_sync():
    error = FSSyncError("it went pear shaped")
    assert repr(error) == "FSSyncError('it went pear shaped')"
    assert str(error) == "it went pear shaped"
    assert error.message == "it went pear shaped"
