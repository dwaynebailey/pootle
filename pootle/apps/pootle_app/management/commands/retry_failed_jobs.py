# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import os

# This must be run before importing Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'pootle.settings'

from django.core.management.base import BaseCommand

from django_rq.queues import get_queue


class Command(BaseCommand):
    help = "Retry failed RQ jobs."

    def handle(self, **options):
        # rq 1.0 (bumped from 0.10.0; see requirements/base.txt)
        # dropped the dedicated failed-jobs Queue and
        # get_failed_queue() in favour of a per-queue
        # FailedJobRegistry. Phase 1 Python 3 port; see PORTING.md.
        failed_queue = get_queue().failed_job_registry
        for job_id in failed_queue.get_job_ids():
            failed_queue.requeue(job_id)
