# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest


@pytest.fixture(scope="session")
def root(django_db_setup, django_db_blocker):
    """Require the root directory."""
    from pootle_app.models import Directory

    # Session-scoped fixture doing real DB access needs
    # django_db_blocker.unblock() explicitly - see
    # pytest_pootle/fixtures/models/permission.py's comment for why.
    # Phase 1 Python 3 port; see PORTING.md.
    with django_db_blocker.unblock():
        return Directory.objects.root


@pytest.fixture
def subdir0(tp0):
    return tp0.directory.child_dirs.get(name="subdir0")
