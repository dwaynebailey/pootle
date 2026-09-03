# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from contextlib import contextmanager

import pytest

from pootle.core.contextmanagers import keep_data
from pootle.core.signals import update_data
from pootle.core.utils.timezone import localdate


class UpdateUnitTest(object):

    def __init__(self, runner):
        self.runner = runner
        self.unit = runner.unit

    def __enter__(self):
        self.original = self._get_unit_data(self.unit)

    def __exit__(self, *args):
        # Refreshing only the one concrete field this test actually
        # reads back (revision), not the whole instance: Django 2.0+
        # made a bare refresh_from_db() also clear an instance's
        # cached forward-FK relations as a side effect (ticket #27343
        # - 1.11 left them stale on purpose, which this whole flow
        # implicitly relied on). self.unit.store is cached back onto
        # this unit by the related manager that originally fetched it
        # (store0.units...), so it's literally the store0/tp0 fixture
        # objects the rest of the test keeps reading and mutating in
        # place via their own .data caches - a bare refresh_from_db()
        # here would silently swap self.unit.store for a disconnected,
        # freshly-queried Store instance instead, and the two explicit
        # refresh_from_db() calls below would then update *that*
        # object's .data rather than store0's/tp0's, leaving the ones
        # everything else reads stale for the rest of the test. Passing
        # fields=["revision"] limits refresh_from_db() to reloading
        # that one column, which - per Django's own implementation -
        # skips the cached-relation-clearing step entirely (it only
        # runs for fields actually being refreshed), keeping
        # self.unit.store's identity intact on any Django version.
        # Found running Phase 2 rung 1 - test_contextmanager_update_tp_
        # after_suggestion started failing under Django 2.2 with this
        # exact symptom. See PORTING.md.
        self.unit.refresh_from_db(fields=["revision"])
        self.unit.store.data.refresh_from_db()
        self.unit.store.translation_project.data.refresh_from_db()
        self._test(
            self.original,
            self._get_unit_data(self.unit))

    def _get_unit_data(self, unit):
        store = unit.store
        tp = store.translation_project
        data = {}
        data["unit_revision"] = unit.revision
        data["checks"] = list(unit.qualitycheck_set.filter(name="xmltags"))
        data["store_data"] = {
            k: getattr(store.data, k)
            for k
            in ["translated_words",
                "critical_checks",
                "max_unit_revision",
                "total_words",
                "pending_suggestions"]}
        store_score = unit.store.user_scores.get(
            user__username="member",
            date=localdate())
        data["store_score"] = {
            k: getattr(store_score, k)
            for k
            in ["translated",
                "suggested",
                "reviewed",
                "score"]}
        tp_score = tp.user_scores.get(
            user__username="member",
            date=localdate())
        data["tp_score"] = {
            k: getattr(tp_score, k)
            for k
            in ["translated",
                "suggested",
                "reviewed",
                "score"]}
        data["store_checks_data"] = {
            cd.name: cd.count
            for cd in store.check_data.all()}
        data["tp_checks_data"] = {
            cd.name: cd.count
            for cd in tp.check_data.all()}
        data["tp_data"] = {
            k: getattr(tp.data, k)
            for k
            in ["translated_words",
                "critical_checks",
                "max_unit_revision",
                "total_words",
                "pending_suggestions"]}
        data["dir_revision"] = list(
            store.parent.revisions.filter(
                key__in=["stats", "checks"]))
        data["tp_dir_revision"] = list(
            tp.directory.revisions.filter(
                key__in=["stats", "checks"]))
        return data

    def _test(self, original, updated):
        for test_type in ["revisions", "data", "check_data", "scores"]:
            getattr(self.runner, "_test_%s" % test_type)(original, updated)


@pytest.fixture
def update_unit_test():
    return UpdateUnitTest


@contextmanager
def _no_update_data():
    with keep_data(signals=(update_data, )):
        yield


@pytest.fixture
def no_update_data():
    return _no_update_data
