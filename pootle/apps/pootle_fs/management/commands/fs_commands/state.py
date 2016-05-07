# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from pootle_fs.management.commands import SubCommand
from pootle_fs.state import FS_STATE


class StateDisplay(object):

    def __init__(self, state, state_type):
        self.state = state
        self.state_type = state_type

    @property
    def description(self):
        return self.fs_state_type['description']

    @property
    def title(self):
        return (
            "%s (%s)"
            % (self.fs_state_type['title'],
               len(self.state[self.state_type])))

    @property
    def fs_state_type(self):
        return FS_STATE[self.state_type]


class StateCommand(SubCommand):
    help = "State of fs repositories."

    def add_arguments(self, parser):
        parser.add_argument(
            'project',
            type=str,
            help='Pootle project')
        parser.add_argument(
            '-t', '--type',
            action='append',
            dest='state_type',
            help='State type')
        super(StateCommand, self).add_arguments(parser)

    @property
    def state(self):
        return self.plugin.state(
            fs_path=self.fs_path, pootle_path=self.pootle_path)

    def handle_state(self, state_type):
        state_display = StateDisplay(self.state, state_type)
        title = state_display.title
        self.stdout.write(title, self.style.HTTP_INFO)
        self.stdout.write("-" * len(title))
        self.stdout.write(state_display.description)
        self.stdout.write("")
        handler = getattr(self, "handle_%s" % state_type)
        for state in self.state[state_type]:
            self.write_line(*handler(state))
        self.stdout.write("")

    def handle_conflict(self, state):
        return (
            state.pootle_path,
            state.fs_path,
            self.style.FS_CONFLICT,
            self.style.FS_CONFLICT)

    def handle_conflict_untracked(self, state):
        return (
            state.pootle_path,
            state.fs_path,
            self.style.FS_CONFLICT,
            self.style.FS_CONFLICT)

    def handle_fs_untracked(self, state):
        return (
            "(%s)" % state.pootle_path,
            state.fs_path,
            self.style.FS_MISSING,
            self.style.FS_UNTRACKED)

    def handle_fs_staged(self, state):
        return (
            "(%s)" % state.pootle_path,
            state.fs_path,
            self.style.FS_MISSING,
            self.style.FS_STAGED)

    def handle_fs_ahead(self, state):
        return (
            state.pootle_path,
            state.fs_path,
            None,
            self.style.FS_UPDATED)

    def handle_fs_removed(self, state):
        return (
            state.pootle_path,
            "(%s)" % state.fs_path,
            None,
            self.style.FS_REMOVED)

    def handle_pootle_untracked(self, state):
        return (
            state.pootle_path,
            "(%s)" % state.fs_path,
            self.style.FS_UNTRACKED,
            self.style.FS_REMOVED)

    def handle_pootle_staged(self, state):
        return (
            state.pootle_path,
            "(%s)" % state.fs_path,
            self.style.FS_STAGED,
            self.style.FS_REMOVED)

    def handle_pootle_removed(self, state):
        return (
            "(%s)" % state.pootle_path,
            state.fs_path,
            self.style.FS_REMOVED)

    def handle_pootle_ahead(self, state):
        return (
            state.pootle_path,
            state.fs_path,
            self.style.FS_UPDATED)

    def handle_merge_fs_wins(self, state):
        return (
            state.pootle_path,
            state.fs_path,
            self.style.FS_UPDATED,
            self.style.FS_UPDATED)

    def handle_merge_pootle_wins(self, state):
        return (
            state.pootle_path,
            state.fs_path,
            self.style.FS_UPDATED,
            self.style.FS_UPDATED)

    def handle_remove(self, state):
        if state.store_fs.file.file_exists:
            pootle_path = "(%s)" % state.pootle_path
            fs_path = state.fs_path
        else:
            pootle_path = state.pootle_path
            fs_path = "(%s)" % state.fs_path
        return (
            pootle_path,
            fs_path,
            self.style.FS_MISSING,
            self.style.FS_MISSING)

    def handle(self, project_code, *args, **options):
        self.fs = self.get_fs(project_code)
        self.pootle_path = options["pootle_path"]
        self.fs_path = options["fs_path"]

        if not self.state.has_changed:
            self.stdout.write("Everything up-to-date")
            return

        for k in self.state:
            self.handle_state(k)
