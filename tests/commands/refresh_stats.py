# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import logging
import os

import pytest

from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.one
@pytest.mark.cmd
@pytest.mark.django_db
def test_refresh_stats_noargs(caplog, afrikaans_tutorial):
    """Simple stats updates.

    Use --no-rq so that we don't need to run rqworkers
    """
    with caplog.atLevel(logging.DEBUG, logger='stats'):
        call_command('refresh_stats', '--no-rq', '--language=af', '--project=tutorial')
    #assert "User purged: evil_member" in caplog.text()
