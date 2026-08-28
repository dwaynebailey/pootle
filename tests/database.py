import pytest
# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.


@pytest.mark.django_db
def test_backend_db():
    """Ensure that we are always testing sqlite on fast in memory DB"""
    from django.db import connection, connections

    if connection.vendor == "sqlite":
        # Newer pytest-django (test tooling, bumped in the Phase 1
        # Python 3 port; see PORTING.md) opens sqlite's in-memory DB
        # via a shared-cache URI (file:memorydb_default?mode=memory&
        # cache=shared) rather than the bare ":memory:" name - same
        # in-memory DB, different spelling. Accept either.
        db_name = connections.databases["default"]["NAME"]
        assert db_name == ":memory:" or "mode=memory" in db_name
