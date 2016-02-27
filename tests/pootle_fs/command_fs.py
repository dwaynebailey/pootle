# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import io
import os

import pytest

from django.core.management import call_command, CommandError

from pytest_pootle.factories import ProjectDBFactory

from pootle.core.delegate import config
from pootle.core.exceptions import NotConfiguredError, MissingPluginError
from pootle_fs.management.commands import ActionDisplay
from pootle_fs.management.commands.fs_commands.state import (
    StateCommand, StateDisplay)
from pootle_fs.utils import FSPlugin
from pootle_project.models import Project


@pytest.mark.django_db
def test_command_fs(project_fs, capsys):
    call_command("fs")
    out, err = capsys.readouterr()
    expected = []
    for project in Project.objects.order_by("pk"):
        try:
            plugin = FSPlugin(project)
            expected.append(
                "%s\t%s"
                % (project.code, plugin.fs_url))
        except (MissingPluginError, NotConfiguredError):
            pass
    expected = (
        "%s\n"
        % '\n'.join(expected))
    assert out == expected


@pytest.mark.django_db
def test_command_fs_info(project_fs, capsys):
    call_command("fs", project_fs.project.code)
    out, err = capsys.readouterr()
    # TODO


def _test_state(state, out):
    expected = ""

    if not state.has_changed:
        assert out == "Everything up-to-date\n"
        return

    def _state_line(fs_state):
        fs_exists_state = [
            "fs_untracked", "fs_staged", "fs_ahead",
            "pootle_ahead", "pootle_removed",
            "conflict", "conflict_untracked",
            "merge_fs_wins", "merge_pootle_wins"]
        store_exists_state = [
            "pootle_untracked", "pootle_staged", "pootle_ahead",
            "fs_ahead", "fs_removed",
            "conflict", "conflict_untracked",
            "merge_fs_wins", "merge_pootle_wins"]
        fs_exists = (
            fs_state.state_type in fs_exists_state
            or (fs_state.state_type == "remove"
                and fs_state.store_fs.file.file_exists))
        store_exists = (
            fs_state.state_type in store_exists_state
            or (fs_state.state_type == "remove"
                and not fs_state.store_fs.file.file_exists))

        if fs_exists:
            fs_path = fs_state.fs_path
        else:
            fs_path = "(%s)" % fs_state.fs_path
        if store_exists:
            pootle_path = fs_state.pootle_path
        else:
            pootle_path = "(%s)" % fs_state.pootle_path
        return (
            "  %s\n   <-->  %s"
            % (pootle_path, fs_path))

    for k in state:
        state_display = StateDisplay(state, k)
        title = state_display.title
        description = state_display.description
        expected += (
            "%s\n%s\n%s\n\n%s\n\n"
            % (title,
               "-" * len(title),
               description,
               "\n".join([_state_line(fs_state)
                          for fs_state in state[k]])))
    assert out == expected


def _test_response(response, out, err):
    expected = ""

    if response is None:
        raise Exception

    def _response_line(action):

        fs_exists_actions = [
            "pulled_to_pootle", "pushed_to_fs", "fetched_from_fs",
            "staged_for_merge_fs", "staged_for_merge_pootle",
            "merged_from_fs", "merged_from_pootle"]

        store_exists_actions = [
            "pulled_to_pootle", "pushed_to_fs", "added_from_pootle",
            "staged_for_merge_fs", "staged_for_merge_pootle",
            "merged_from_fs", "merged_from_pootle"]

        file_exists = (
            action.action_type in fs_exists_actions
            or (action.fs_state.state_type
                in ["conflict", "conflict_untracked"])
            or (action.action_type == "staged_for_removal"
                and (action.fs_state.state_type
                     in ["fs_untracked", "pootle_removed"])))

        store_exists = (
            action.action_type in store_exists_actions
            or (action.fs_state.state_type
                in ["conflict", "conflict_untracked"])
            or (action.action_type == "staged_for_removal"
                and (action.fs_state.state_type
                     in ["pootle_untracked", "fs_removed"])))

        if file_exists:
            fs_path = action.fs_path
        else:
            fs_path = "(%s)" % action.fs_path
        if store_exists:
            pootle_path = action.pootle_path
        else:
            pootle_path = "(%s)" % action.pootle_path

        return (
            "  %s\n   <-->  %s"
            % (pootle_path, fs_path))

    if not response.made_changes:
        assert out == "No changes made\n"
        return

    for k in response:
        action_display = ActionDisplay(response, k)
        title = action_display.title
        expected += (
            "%s\n%s\n%s\n\n%s\n\n"
            % (title,
               "-" * len(title),
               action_display.description,
               "\n".join([_response_line(action)
                          for action in response[k]])))
    assert out == expected


@pytest.mark.django_db
def test_command_state_fetch(project_fs, capsys):
    plugin = project_fs
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.fetch()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.fetch(force=True)
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.sync()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()

    _test_state(plugin.state(), out)


@pytest.mark.django_db
def test_command_state_add(project_fs, capsys):
    plugin = project_fs
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.add()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.add(force=True)
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.sync()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)


@pytest.mark.django_db
def test_command_state_merge_fs(project_fs, capsys):
    plugin = project_fs
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.merge()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.sync()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()

    _test_state(plugin.state(), out)


@pytest.mark.django_db
def test_command_state_synced(project_fs, capsys):
    plugin = project_fs
    plugin.add()
    plugin.fetch()
    plugin.merge()
    plugin.rm()
    plugin.sync()
    out, err = capsys.readouterr()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    assert out == "Everything up-to-date\n"


@pytest.mark.django_db
def test_command_state_merge_pootle(project_fs, capsys):
    plugin = project_fs
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.merge(pootle_wins=True)
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.sync()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()

    _test_state(plugin.state(), out)


@pytest.mark.django_db
def test_command_state_rm(project_fs, capsys):
    plugin = project_fs
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.rm()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()
    _test_state(plugin.state(), out)

    plugin.sync()
    call_command("fs", plugin.project.code, "state")
    out, err = capsys.readouterr()

    _test_state(plugin.state(), out)


@pytest.mark.django_db
def __test_command_config(project_fs, capsys):
    plugin = project_fs
    call_command("fs", plugin.project.code, "config")
    out, err = capsys.readouterr()
    with open(os.path.join(plugin.fs.url, ".pootle.ini")) as f:
        assert out.strip() == f.read().strip()
    saved_conf = io.BytesIO()
    config = plugin.read_config()
    config.set("default", "some", "setting")
    config.write(saved_conf)
    saved_conf.seek(0)
    saved_conf = saved_conf.read().strip()
    config.write(
        open(
            os.path.join(plugin.fs.url, ".pootle.ini"), "w"))
    call_command("fs", plugin.project.code, "config", update=True)
    new_out, err = capsys.readouterr()
    assert new_out == "Config updated\n"
    call_command("fs", plugin.project.code, "config")
    out, err = capsys.readouterr()
    assert out.strip() == saved_conf


@pytest.mark.django_db
def test_command_set_fs(project_fs, capsys, english):

    project_fs.pull()
    assert project_fs.is_cloned

    with pytest.raises(CommandError):
        call_command("fs", "project0", "set_fs")

    with pytest.raises(CommandError):
        call_command("fs", "project0", "set_fs", "foo")

    with pytest.raises(CommandError):
        call_command("fs", "project0", "set_fs", "foo", "bar")

    # "localfs" plugin is registered so this works...
    call_command("fs", "project0", "set_fs", "localfs", "bar")

    # at this point the project_fs.fs is stale because config is cached
    assert project_fs.fs_url != "bar"

    project_fs.reload()

    # but now the url should be set
    assert project_fs.fs_url == "bar"

    # changing the fs_type/url results in the local_fs being deleted
    assert project_fs.is_cloned is False

    project = ProjectDBFactory(source_language=english)

    call_command("fs", project.code, "set_fs", "localfs", "baz")
    assert FSPlugin(project).fs_url == "baz"
    assert FSPlugin(project).is_cloned is False


@pytest.mark.django_db
def test_command_merge_fs(project_fs, capsys):
    resp = call_command(
        "fs", project_fs.project.code,
        "merge")
    _test_response(
        resp,
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_merge_pootle(project_fs, capsys):
    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "merge", pootle_wins=True),
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_rm(project_fs, capsys):
    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "rm"),
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_add(project_fs, capsys):
    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "add"),
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_add_force(project_fs, capsys):
    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "add", force=True),
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_fetch(project_fs, capsys):
    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "fetch"),
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_fetch_force(project_fs, capsys):
    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "fetch", force=True),
        *capsys.readouterr())

    _test_response(
        call_command(
            "fs", project_fs.project.code,
            "sync"),
        *capsys.readouterr())


@pytest.mark.django_db
def test_command_fs_no_projects(capsys):
    for project in Project.objects.all():
        conf = config.get(Project, instance=project)
        conf.clear_config("pootle_fs.fs_type")
        conf.clear_config("pootle_fs.fs_url")
    call_command("fs")
    out, err = capsys.readouterr()
    assert out == "No projects configured\n"


@pytest.mark.django_db
def test_command_fs_bad_project(project_fs, capsys):
    with pytest.raises(CommandError):
        call_command(
            "fs", "BAD_PROJECT_CODE")

    with pytest.raises(CommandError):
        call_command(
            "fs", "project0", "BAD_SUBCOMMAND")


@pytest.mark.django_db
def test_command_fs_argv_subcommands(project_fs, capsys):
    from pootle_fs.management.commands.fs import Command
    command = Command().run_from_argv

    with pytest.raises(SystemExit):
        command(
            ["pootle", "fs", "BAD_PROJECT_CODE"])

    with pytest.raises(SystemExit):
        command(
            ["pootle", "fs", "project0", "BAD_SUBCOMMAND"])

    out, err = capsys.readouterr()
    command(["pootle", "fs"])
    out, err = capsys.readouterr()

    expected = []
    for project in Project.objects.order_by("pk"):
        try:
            plugin = FSPlugin(project)
            expected.append(
                "%s\t%s"
                % (project.code, plugin.fs_url))
        except (MissingPluginError, NotConfiguredError):
            pass
    expected = (
        "%s\n"
        % '\n'.join(expected))
    assert out == expected


@pytest.mark.django_db
def test_command_fs_argv_subcommand_error(project_fs):
    from pootle_fs.management.commands.fs import Command
    command = Command().run_from_argv

    with pytest.raises(SystemExit):
        command(
            ["pootle", "fs", "BAD_PROJECT_CODE"])

    with pytest.raises(CommandError):
        command(
            ["pootle", "fs", "BAD_PROJECT_CODE", "--traceback"])

    with pytest.raises(CommandError):
        command(
            ["pootle", "fs", "BAD_PROJECT_CODE", "--traceback", "--foo"])


@pytest.mark.django_db
def test_command_translations_subcommands(project_fs, capsys, english):
    command = StateCommand()

    # this works fine
    command.execute("project0", pootle_path=None, fs_path=None)
    out, err = capsys.readouterr()
    assert not err

    project = ProjectDBFactory(source_language=english)

    # a project with no fs setup raises command error
    with pytest.raises(CommandError):
        command.execute(project.code, pootle_path=None, fs_path=None)

    # as does a non-existent project
    with pytest.raises(CommandError):
        command.execute("DOESNT_EXIST", pootle_path=None, fs_path=None)


@pytest.mark.django_db
def test_command_no_color(project_fs):
    call_command("fs", "project0", "state")
    assert os.environ["DJANGO_COLORS"] == "light"
    call_command("fs", "project0", "state", no_color=True)
    assert os.environ["DJANGO_COLORS"] == "nocolor"
