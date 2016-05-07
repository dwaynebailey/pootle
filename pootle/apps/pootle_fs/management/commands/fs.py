# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import logging
import os
import sys


from django.utils.termcolors import PALETTES, NOCOLOR_PALETTE

PALETTES[NOCOLOR_PALETTE]["FS_MISSING"] = {}
PALETTES["light"]["FS_MISSING"] = {'fg': 'magenta'}
PALETTES["dark"]["FS_MISSING"] = {'fg': 'magenta'}
PALETTES[NOCOLOR_PALETTE]["POOTLE_MISSING"] = {}
PALETTES["light"]["POOTLE_MISSING"] = {'fg': 'magenta'}
PALETTES["dark"]["POOTLE_MISSING"] = {'fg': 'magenta'}
PALETTES[NOCOLOR_PALETTE]["FS_UNTRACKED"] = {}
PALETTES["light"]["FS_UNTRACKED"] = {'fg': 'red'}
PALETTES["dark"]["FS_UNTRACKED"] = {'fg': 'red'}
PALETTES[NOCOLOR_PALETTE]["FS_STAGED"] = {}
PALETTES["light"]["FS_STAGED"] = {'fg': 'green'}
PALETTES["dark"]["FS_STAGED"] = {'fg': 'green'}
PALETTES[NOCOLOR_PALETTE]["FS_UPDATED"] = {}
PALETTES["light"]["FS_UPDATED"] = {'fg': 'green'}
PALETTES["dark"]["FS_UPDATED"] = {'fg': 'green'}
PALETTES[NOCOLOR_PALETTE]["FS_CONFLICT"] = {}
PALETTES["light"]["FS_CONFLICT"] = {'fg': 'red', 'opts': ('bold',)}
PALETTES["dark"]["FS_CONFLICT"] = {'fg': 'red', 'opts': ('bold',)}
PALETTES[NOCOLOR_PALETTE]["FS_REMOVED"] = {}
PALETTES["light"]["FS_REMOVED"] = {'fg': 'red'}
PALETTES["dark"]["FS_REMOVED"] = {'fg': 'red'}
PALETTES[NOCOLOR_PALETTE]["FS_ERROR"] = {}
PALETTES["light"]["FS_ERROR"] = {'fg': 'red', 'opts': ('bold',)}
PALETTES["dark"]["FS_ERROR"] = {'fg': 'red', 'opts': ('bold',)}


# This must be run before importing Django.
os.environ["DJANGO_COLORS"] = "light"
os.environ['DJANGO_SETTINGS_MODULE'] = 'pootle.settings'


from django.core.management import (
    BaseCommand, CommandError, handle_default_options)
from django.core.management.base import OutputWrapper

from pootle.core.exceptions import MissingPluginError, NotConfiguredError
from pootle_fs.utils import FSPlugin
from pootle_project.models import Project

from .fs_commands.add import AddCommand
from .fs_commands.info import ProjectInfoCommand
from .fs_commands.fetch import FetchCommand
from .fs_commands.merge import MergeCommand
from .fs_commands.rm import RmCommand
from .fs_commands.set_fs import SetFSCommand
from .fs_commands.state import StateCommand
from .fs_commands.sync import SyncCommand


logger = logging.getLogger('pootle.fs')


class Command(BaseCommand):
    help = "Pootle FS."
    subcommands = {
        "add": AddCommand,
        "info": ProjectInfoCommand,
        "fetch": FetchCommand,
        "merge": MergeCommand,
        "rm": RmCommand,
        "set_fs": SetFSCommand,
        "state": StateCommand,
        "sync": SyncCommand}

    def add_arguments(self, parser):
        parser.add_argument(
            'extra',
            type=str,
            nargs="*",
            help='Additional positional arguments')

    def execute(self, *args, **kwargs):
        pos_args = kwargs["extra"]
        if not pos_args:
            return super(Command, self).execute(*args, **kwargs)
        project_code = pos_args[0]
        pos_args = pos_args[1:]
        if project_code and not pos_args:
            pos_args = ["info"]
        try:
            Project.objects.get(code=project_code)
        except Project.DoesNotExist:
            raise CommandError("Unrecognised project: %s" % project_code)
        if not pos_args:
            return super(Command, self).execute(*args, **kwargs)
        subcommand = pos_args[0]
        try:
            subcommand = self.subcommands[subcommand]()
        except KeyError:
            raise CommandError(
                "Unrecognised command: %s" % subcommand)

        subparser = subcommand.create_parser("pootle", pos_args[0])
        subargs = subparser.parse_args([project_code] + pos_args[1:]).__dict__
        subargs.update(kwargs)
        result = subcommand.execute(project_code, *subargs["project"], **subargs)
        return result

    def handle(self, *args, **kwargs):
        any_configured = False
        for project in Project.objects.order_by("pk"):
            try:
                plugin = FSPlugin(project)
                self.stdout.write(
                    "%s\t%s"
                    % (project.code, plugin.fs_url))
                any_configured = True
            except (MissingPluginError, NotConfiguredError):
                pass
        if not any_configured:
            self.stdout.write("No projects configured")

    def _do_run(self, argv):
        if argv[2:] and not argv[2].startswith("-"):
            project_code = argv[2]
            try:
                Project.objects.get(code=project_code)
            except Project.DoesNotExist:
                raise CommandError(
                    "Unrecognised project: %s" % project_code)
            if argv[3:]:
                subcommand = argv[3]
            else:
                subcommand = "info"
            try:
                to_run = self.subcommands[subcommand]()
            except KeyError:
                raise CommandError(
                    "Unrecognised command: %s" % subcommand)
            return to_run.run_from_argv(
                argv[:1] + [subcommand, project_code] + argv[4:])

        parser = self.create_parser(argv[0], argv[1])
        options = parser.parse_args(argv[2:])
        cmd_options = vars(options)
        # Move positional args out of options to mimic legacy optparse
        args = cmd_options.pop('args', ())
        handle_default_options(options)
        return self.execute(*args, **options.__dict__)

    def run_from_argv(self, argv):
        """
        Set up any environment changes requested (e.g., Python path
        and Django settings), then run this command. If the
        command raises a ``CommandError``, intercept it and print it sensibly
        to stderr. If the ``--traceback`` option is present or the raised
        ``Exception`` is not ``CommandError``, raise it.
        """
        options = None
        try:
            self._do_run(argv)
        except Exception as e:
            do_raise = (
                "--traceback" in argv
                or (options
                    and options.traceback
                    or not isinstance(e, CommandError)))
            if do_raise:
                raise

            # self.stderr is not guaranteed to be set here
            stderr = getattr(
                self, 'stderr', OutputWrapper(sys.stderr, self.style.ERROR))
            stderr.write('%s: %s' % (e.__class__.__name__, e))
            sys.exit(1)
