# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import os
import sys

from django.core.management.base import (
    BaseCommand, CommandError, OutputWrapper)
from django.core.management.color import no_style
from django.utils.functional import cached_property

from pootle.core.exceptions import MissingPluginError, NotConfiguredError
from pootle_fs.response import FS_RESPONSE
from pootle_fs.utils import FSPlugin
from pootle_project.models import Project


class ActionDisplay(object):

    def __init__(self, action, action_type):
        self.action = action
        self.action_type = action_type

    @property
    def description(self):
        return self.fs_action_type['description']

    @property
    def title(self):
        return (
            "%s (%s)"
            % (self.fs_action_type['title'],
               len(self.action[self.action_type])))

    @property
    def fs_action_type(self):
        return FS_RESPONSE[self.action_type]


class BaseSubCommand(BaseCommand):

    requires_system_checks = False

    def get_fs(self, project_code):
        self.get_project(project_code)
        try:
            self.fs = FSPlugin(self.project)
            return self.fs
        except (NotConfiguredError, MissingPluginError) as e:
            raise CommandError(e)

    def get_project(self, project_code):
        try:
            self.project = Project.objects.get(code=project_code)
        except Project.DoesNotExist as e:
            raise CommandError(e)
        return self.project

    def write_line(self, pootle_path, fs_path,
                   pootle_style=None, fs_style=None):
        self.stdout.write("  %s" % pootle_path, pootle_style)
        self.stdout.write("   <-->  ", ending="")
        self.stdout.write(fs_path, fs_style)


class SubCommand(BaseSubCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '-p', '--fs_path',
            action='store',
            dest='fs_path',
            help='Filter translations by filesystem path')
        parser.add_argument(
            '-P', '--pootle_path',
            action='store',
            dest='pootle_path',
            help='Filter translations by Pootle path')

    @cached_property
    def plugin(self):
        if hasattr(self, "fs"):
            return self.fs.plugin

    def handle_added_from_pootle(self, response):
        if response.fs_state.state_type in ["conflict", "conflict_untracked"]:
            return response.pootle_path, response.fs_path
        else:
            return (
                response.pootle_path,
                "(%s)" % response.fs_path,
                None, self.style.FS_MISSING)

    def handle_fetched_from_fs(self, response):
        if response.fs_state.state_type in ["conflict", "conflict_untracked"]:
            return response.pootle_path, response.fs_path
        else:
            return (
                "(%s)" % response.pootle_path,
                response.fs_path,
                self.style.FS_MISSING)

    def handle_staged_for_removal(self, response):
        file_exists = (
            response.fs_state.state_type
            in ["fs_untracked", "pootle_removed", "conflict_untracked"])
        store_exists = (
            response.fs_state.state_type
            in ["pootle_untracked", "fs_removed", "conflict_untracked"])
        if file_exists:
            fs_path = response.fs_path
        else:
            fs_path = "(%s)" % response.fs_path
        if store_exists:
            pootle_path = response.pootle_path
        else:
            pootle_path = "(%s)" % response.pootle_path
        return pootle_path, fs_path

    def handle_removed(self, response):
        return(
            "(%s)" % response.pootle_path,
            "(%s)" % response.fs_path,
            self.style.POOTLE_MISSING,
            self.style.FS_MISSING)

    def handle_actions(self, action_type):
        failed = self.response.failed(action_type)
        action_display = ActionDisplay(self.response, action_type)
        title = action_display.title
        if any(failed):
            self.stdout.write(title, self.style.ERROR)
        else:
            self.stdout.write(title, self.style.HTTP_INFO)
        self.stdout.write("-" * len(title))
        self.stdout.write(action_display.description)
        self.stdout.write("")
        for action in self.response.completed(action_type):
            handler = getattr(self, "handle_%s" % action_type, None)
            if handler:
                self.write_line(*handler(action))
            else:
                self.write_line(action.pootle_path, action.fs_path)
        if any(failed):
            for action in failed:
                self.write_line(
                    action.pootle_path,
                    action.fs_path,
                    fs_style=self.style.FS_ERROR,
                    pootle_style=self.style.POOTLE_ERROR)
        self.stdout.write("")

    def handle_response(self, response):
        self.response = response
        for action_type in self.response:
            self.handle_actions(action_type)
        if not self.response.made_changes:
            self.stdout.write("No changes made")
        return self.response

    def execute(self, *args, **options):
        """
        Overridden to return response object rather than writing to stdout
        """
        self.stdout = OutputWrapper(options.get('stdout', sys.stdout))
        if options.get('no_color'):
            self.style = no_style()
            self.stderr = OutputWrapper(options.get('stderr', sys.stderr))
            os.environ[str("DJANGO_COLORS")] = str("nocolor")
        else:
            self.stderr = OutputWrapper(
                options.get('stderr', sys.stderr), self.style.ERROR)
        if len(args):
            project = args[0]
        else:
            project = options["project"]
        return self.handle(project, *args, **options)
