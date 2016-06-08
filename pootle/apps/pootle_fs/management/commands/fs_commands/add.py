# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from pootle_fs.management.commands import SubCommand


class AddCommand(SubCommand):
    help = "Add translations into Pootle from FS."

    def add_arguments(self, parser):
        parser.add_argument(
            'project',
            type=str,
            help='Pootle project')
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help=('Add translations that are conflicting with Pootle '
                  'stores'))
        super(AddCommand, self).add_arguments(parser)

    def handle(self, project_code, *args, **kwargs):
        return self.handle_response(
            self.get_fs(project_code).add(
                force=kwargs["force"],
                fs_path=kwargs['fs_path'],
                pootle_path=kwargs['pootle_path']))
