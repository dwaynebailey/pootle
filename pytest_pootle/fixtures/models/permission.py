# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest


# These are session-scoped fixtures doing real DB access, so (like
# pytest_pootle/fixtures/site.py's post_db_setup) they need
# django_db_blocker.unblock() explicitly: pytest-django's db-access
# block is normally lifted per-test based on the django_db marker/db
# fixtures, which a session-scoped fixture doesn't participate in.
# A newer pytest-django (bumped from 3.1.2 to 4.8.0; see
# requirements/tests.txt) enforces this more strictly than the
# version these fixtures were originally written against. Phase 1
# Python 3 port; see PORTING.md.
@pytest.fixture(scope="session")
def pootle_content_type(django_db_setup, django_db_blocker):
    """Require the pootle ContentType."""
    from django.contrib.contenttypes.models import ContentType

    args = {
        'app_label': 'pootle_app',
        'model': 'directory',
    }
    with django_db_blocker.unblock():
        return ContentType.objects.get(**args)


def _require_permission(code, name, content_type):
    """Helper to get/create a new permission."""
    from django.contrib.auth.models import Permission

    criteria = {
        'codename': code,
        'name': name,
        'content_type': content_type,
    }
    permission = Permission.objects.get_or_create(**criteria)[0]

    return permission


@pytest.fixture(scope="session")
def view(pootle_content_type, django_db_blocker):
    """Require the `view` permission."""
    with django_db_blocker.unblock():
        return _require_permission('view', 'Can access a project',
                                   pootle_content_type)


@pytest.fixture(scope="session")
def hide(pootle_content_type, django_db_blocker):
    """Require the `hide` permission."""
    with django_db_blocker.unblock():
        return _require_permission('hide', 'Cannot access a project',
                                   pootle_content_type)


@pytest.fixture(scope="session")
def administrate(pootle_content_type, django_db_blocker):
    """Require the `suggest` permission."""
    with django_db_blocker.unblock():
        return _require_permission('administrate', 'Can administrate a TP',
                                   pootle_content_type)


@pytest.fixture
def translate():
    """Require the `translate` permission."""
    from django.contrib.auth.models import Permission

    return Permission.objects.get(codename="translate")
