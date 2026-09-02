# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest


@pytest.fixture(scope="session")
def submissions(django_db_setup, django_db_blocker):
    """A dictionary of submission.id, submission for all
    submissions created in test env

    as this fixture is session-scoped tests should not change its contents
    """
    from pootle_statistics.models import Submission

    select_related = (
        "unit", "quality_check", "submitter", "suggestion")
    # Session-scoped fixture doing real DB access needs
    # django_db_blocker.unblock() explicitly - see
    # pytest_pootle/fixtures/models/permission.py's comment for why.
    # Phase 1 Python 3 port; see PORTING.md.
    with django_db_blocker.unblock():
        return {
            s.id: s
            for s
            in Submission.objects.select_related(
                *select_related).iterator()}
