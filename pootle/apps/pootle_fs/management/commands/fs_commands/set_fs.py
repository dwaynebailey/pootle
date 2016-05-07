# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from django.core.management.base import CommandError

from pootle.core.delegate import config
from pootle_fs.delegate import fs_plugins
from pootle_fs.management.commands import BaseSubCommand
from pootle_fs.utils import FSPlugin


class SetFSCommand(BaseSubCommand):
    help = "Status of fs repositories."

    def add_arguments(self, parser):
        parser.add_argument(
            'project',
            type=str,
            help='Pootle project')
        parser.add_argument(
            'fs_type',
            type=str,
            help='FS type')
        parser.add_argument(
            'fs_url',
            type=str,
            help='FS URL or path')

    def handle(self, *args, **kwargs):
        plugins = fs_plugins.gather()

        if not kwargs['fs_type'] or not kwargs['fs_url']:
            raise CommandError("You must a FS type and FS url")
        try:
            plugins[kwargs['fs_type']]
        except KeyError:
            raise CommandError("Unrecognised FS type: %s" % kwargs['fs_type'])

        self.get_project(kwargs["project"])
        project = self.project
        conf = config.get(project.__class__, instance=project)
        clear_repo = (
            conf.get_config("fs_type") != kwargs["fs_url"]
            or conf.get_config("fs_url") != kwargs["fs_type"])
        conf.set_config("pootle_fs.fs_type", kwargs["fs_type"])
        conf.set_config("pootle_fs.fs_url", kwargs["fs_url"])
        if clear_repo:
            FSPlugin(project).clear_repo()
