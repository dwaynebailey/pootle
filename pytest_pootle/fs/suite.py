# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import io
import os
from fnmatch import fnmatch

from translate.storage.factory import getclass


def check_files_match(src, response):
    from pootle_fs.models import StoreFS

    assert all(
        os.path.exists(
            os.path.join(
                src,
                p.fs_path.strip("/")))
        for p
        in response["pushed_to_fs"])
    assert not any(
        os.path.exists(
            os.path.join(
                src,
                p.fs_path.strip("/")))
        for p
        in response["removed"])
    # Any Store/files that have been synced should now match
    synced = (
        response["pulled_to_pootle"]
        + response["pushed_to_fs"]
        + response["merged_from_fs"]
        + response["merged_from_pootle"]
        + response["merged_from_fs"])
    for action in synced:
        store_fs = StoreFS.objects.get(
            pootle_path=action.pootle_path)
        file_path = os.path.join(
            src,
            store_fs.path.strip("/"))
        store_f = io.BytesIO(store_fs.store.serialize())
        with open(file_path) as src_file:
            file_store = getclass(src_file)(src_file.read())
            serialized = getclass(store_f)(store_f.read())
            assert (
                [(x.source, x.target)
                 for x in file_store.units if x.source]
                == [(x.source, x.target)
                    for x in serialized.units if x.source])

    for action in response["removed"]:
        store = action.fs_state.store_fs.store
        if store:
            assert store.obsolete is True
        assert action.fs_state.store_fs.file.file_exists is False
        assert action.fs_state.store_fs.pk is None
        assert not os.path.exists(
            os.path.join(src, action.fs_path.strip("/")))


def _check_fs(plugin, response):
    check_files_match(plugin.fs_url, response)


def _test_sync(plugin, **kwargs):
    from pootle_store.models import FILE_WINS, POOTLE_WINS

    pootle_path = kwargs.get("pootle_path", None)
    fs_path = kwargs.get("fs_path", None)
    state = plugin.state(fs_path=fs_path, pootle_path=pootle_path)

    check_fs = kwargs.get("check_fs", _check_fs)
    if "check_fs" in kwargs:
        del kwargs["check_fs"]

    expected = {}
    expected["pulled_to_pootle"] = []
    expected["pushed_to_fs"] = []
    expected["removed"] = []
    expected["merged_from_fs"] = []
    expected["merged_from_pootle"] = []

    response_mapping = {
        "merged_from_fs": ("merge_fs_wins", ),
        "merged_from_pootle": ("merge_pootle_wins", ),
        "pushed_to_fs": ("pootle_staged", "pootle_ahead"),
        "pulled_to_pootle": ("fs_staged", "fs_ahead"),
        "removed": ("remove", )}

    for expect, prev_state in response_mapping.items():
        _prev_state = []
        for k in prev_state:
            _prev_state += state[k]
        for fs_state in _prev_state:
            if pootle_path and not fnmatch(fs_state.pootle_path, pootle_path):
                continue
            if fs_path and not fnmatch(fs_state.fs_path, fs_path):
                continue
            expected[expect].append(fs_state)

    response = plugin.sync_translations(
        state=state, pootle_path=pootle_path, fs_path=fs_path)

    assert len(response) == len([k for k, v in expected.items() if v])

    for k, v in expected.items():
        assert len(response[k]) == len(expected[k])
        for i, item in enumerate(response[k]):
            expected_state = expected[k][i]
            fs_state = item.fs_state

            assert fs_state.pootle_path == expected_state.pootle_path
            assert fs_state.fs_path == expected_state.fs_path

            if item.store and k != "removed":
                assert not item.store.obsolete
            elif item.store and k == "removed":
                assert item.store.obsolete

            synced_responses = [
                "pulled_to_pootle", "pushed_to_fs",
                "merged_from_fs", "merged_from_pootle"]

            if k in synced_responses:
                assert item.store.pootle_path == expected_state.pootle_path
                assert item.store.fs.get().path == expected_state.fs_path
                store_fs = item.store.fs.get()
                assert (
                    store_fs.store.get_max_unit_revision()
                    == store_fs.last_sync_revision)
                assert (
                    store_fs.file.latest_hash
                    == store_fs.last_sync_hash)

    check_fs(plugin, response)

    # ensure there are no stale "staged_for_removal"
    # or "resolve_conflict" flags
    resources = plugin.resources
    for store_fs in resources.tracked.filter(staged_for_removal=True):
        if pootle_path is not None:
            assert not fnmatch(store_fs.pootle_path, pootle_path)
        if fs_path is not None:
            assert not fnmatch(store_fs.path, fs_path)
        if pootle_path is None and fs_path is None:
            assert not store_fs
    resolved = resources.tracked.filter(
        resolve_conflict__in=[FILE_WINS, POOTLE_WINS])
    for store_fs in resolved:
        if pootle_path is not None:
            assert not fnmatch(store_fs.pootle_path, pootle_path)
        if fs_path is not None:
            assert not fnmatch(store_fs.path, fs_path)
        if pootle_path is None and fs_path is None:
            assert not store_fs
    for store_fs in resources.tracked.filter(staged_for_merge=True):
        if pootle_path is not None:
            assert not fnmatch(store_fs.pootle_path, pootle_path)
        if fs_path is not None:
            assert not fnmatch(store_fs.path, fs_path)
        if pootle_path is None and fs_path is None:
            assert not store_fs


def _test_response(expected, response):

    assert (
        sorted(x for x in response)
        == sorted(k for k, v in expected.items() if v))

    for k, v in expected.items():
        assert len(response[k]) == len(expected[k])
        for i, item in enumerate(response[k]):
            # old_state = [x.pootle_path
            #               for x in new_state[expected[k][0].state]]
            expected_state = expected[k][i]
            fs_state = response[k][i].fs_state
            assert fs_state.pootle_path == expected_state.pootle_path
            assert fs_state.fs_path == expected_state.fs_path
            if fs_state.store_fs:
                assert fs_state.store_fs == expected_state.store_fs
            if fs_state.store:
                assert fs_state.store == expected_state.store


def _run_fetch_test(plugin, **kwargs):
    state = plugin.state(
        fs_path=kwargs.get("fs_path"),
        pootle_path=kwargs.get("pootle_path"))
    force = kwargs.get("force", None)
    pootle_path = kwargs.get("pootle_path", None)
    fs_path = kwargs.get("fs_path", None)
    expected = {}
    expected["fetched_from_fs"] = []
    to_fetch = list(state['fs_untracked'])
    if force:
        to_fetch += (
            state["conflict_untracked"]
            + state["pootle_removed"]
            + state["conflict"])
    for fs_state in to_fetch:
        if pootle_path and not fnmatch(fs_state.pootle_path, pootle_path):
            continue
        if fs_path and not fnmatch(fs_state.fs_path, fs_path):
            continue
        expected["fetched_from_fs"].append(fs_state)
    response = plugin.fetch(
        state=state, pootle_path=pootle_path, fs_path=fs_path, force=force)
    _test_response(expected, response)
    _test_sync(plugin, **kwargs)


def _run_add_test(plugin, **kwargs):
    state = plugin.state(
        fs_path=kwargs.get("fs_path"),
        pootle_path=kwargs.get("pootle_path"))
    force = kwargs.get("force", None)
    pootle_path = kwargs.get("pootle_path", None)
    fs_path = kwargs.get("fs_path", None)
    expected = {}
    expected["added_from_pootle"] = []
    to_add = list(state['pootle_untracked'])
    if force:
        to_add += (
            state["conflict_untracked"]
            + state["fs_removed"]
            + state["conflict"])
    for fs_state in to_add:
        if pootle_path and not fnmatch(fs_state.pootle_path, pootle_path):
            continue
        if fs_path and not fnmatch(fs_state.fs_path, fs_path):
            continue
        expected["added_from_pootle"].append(fs_state)
    response = plugin.add(
        state=state, pootle_path=pootle_path, fs_path=fs_path, force=force)
    _test_response(expected, response)
    _test_sync(plugin, **kwargs)


def _run_rm_test(plugin, **kwargs):
    state = plugin.state(
        fs_path=kwargs.get("fs_path"),
        pootle_path=kwargs.get("pootle_path"))
    pootle_path = kwargs.get("pootle_path", None)
    fs_path = kwargs.get("fs_path", None)
    expected = {}
    expected["staged_for_removal"] = []
    remove = (
        state["fs_untracked"] + state["pootle_untracked"]
        + state["pootle_removed"] + state["fs_removed"])
    for fs_state in remove:
        if pootle_path and not fnmatch(fs_state.pootle_path, pootle_path):
            continue
        if fs_path and not fnmatch(fs_state.fs_path, fs_path):
            continue
        expected["staged_for_removal"].append(fs_state)
    response = plugin.rm(
        state=state, pootle_path=pootle_path, fs_path=fs_path)
    _test_response(expected, response)
    _test_sync(plugin, **kwargs)


def _run_merge_test(plugin, **kwargs):
    state = plugin.state(
        fs_path=kwargs.get("fs_path"),
        pootle_path=kwargs.get("pootle_path"))
    pootle_path = kwargs.get("pootle_path", None)
    fs_path = kwargs.get("fs_path", None)
    pootle_wins = kwargs.get("pootle_wins", False)
    action_type = "staged_for_merge_fs"
    if pootle_wins:
        action_type = "staged_for_merge_pootle"
    expected = {}
    expected[action_type] = []
    remove = (
        state["conflict_untracked"] + state["conflict"])
    for fs_state in remove:
        if pootle_path and not fnmatch(fs_state.pootle_path, pootle_path):
            continue
        if fs_path and not fnmatch(fs_state.fs_path, fs_path):
            continue
        expected[action_type].append(fs_state)
    response = plugin.merge(
        state=state,
        pootle_path=pootle_path,
        fs_path=fs_path,
        pootle_wins=pootle_wins)
    _test_response(expected, response)
    _test_sync(plugin, **kwargs)


def run_fetch_test(plugin, **kwargs):
    _run_fetch_test(plugin, force=False, **kwargs)
    _run_fetch_test(plugin, force=True, **kwargs)


def run_add_test(plugin, **kwargs):
    _run_add_test(plugin, force=False, **kwargs)
    _run_add_test(plugin, force=True, **kwargs)


def run_rm_test(plugin, **kwargs):
    _run_rm_test(plugin, **kwargs)


def run_merge_test(plugin, **kwargs):
    _run_merge_test(plugin, **kwargs)
