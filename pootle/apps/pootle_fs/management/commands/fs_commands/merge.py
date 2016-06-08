# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from pootle_fs.management.commands import SubCommand


class MergeCommand(SubCommand):
    help = "Merge translations between Pootle and FS."

    def add_arguments(self, parser):
        parser.add_argument(
            'project',
            type=str,
            help='Pootle project')
        parser.add_argument(
            '--pootle-wins',
            action='store_true',
            dest='pootle_wins',
            help='Status type')
        super(MergeCommand, self).add_arguments(parser)

    def handle(self, project_code, *args, **options):
        return self.handle_response(
            self.get_fs(project_code).plugin.merge(
                fs_path=options['fs_path'],
                pootle_path=options['pootle_path'],
                pootle_wins=options["pootle_wins"]))
