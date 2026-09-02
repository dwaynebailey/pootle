# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import logging
import os

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

# django.core.management.color.no_style() is cached forever
# (@lru_cache), and color_style() falls back to it whenever
# supports_color() is False (true for any non-tty stdout, e.g. under
# pytest) - so whichever command gets instantiated *first* in the
# whole process, from anywhere, permanently bakes in whatever
# PALETTES looked like at that moment. This module being imported
# "before importing the rest of the Django libs" (see below) doesn't
# guarantee it also runs before every other management command in
# the process has ever been touched (test collection order,
# pytest-django's own setup, etc. can all get there first). Clearing
# the cache makes the next no_style() call rebuild the Style object
# from the now-fully-patched PALETTES, regardless of what happened
# before this module was imported. Phase 1 Python 3 port; see
# PORTING.md.
from django.core.management.color import no_style
no_style.cache_clear()

# This must be run before importing the rest of the Django libs.
os.environ["DJANGO_COLORS"] = "light"
os.environ['DJANGO_SETTINGS_MODULE'] = 'pootle.settings'


from pootle.core.exceptions import MissingPluginError, NotConfiguredError
from pootle.core.management.subcommands import CommandWithSubcommands
from pootle_fs.utils import FSPlugin
from pootle_project.models import Project

from .fs_commands.add import AddCommand
from .fs_commands.fetch import FetchCommand
from .fs_commands.info import ProjectInfoCommand
from .fs_commands.resolve import ResolveCommand
from .fs_commands.rm import RmCommand
from .fs_commands.state import StateCommand
from .fs_commands.sync import SyncCommand
from .fs_commands.unstage import UnstageCommand


logger = logging.getLogger('pootle.fs')


class Command(CommandWithSubcommands):
    help = "Pootle FS."
    subcommands = {
        "add": AddCommand,
        "fetch": FetchCommand,
        "info": ProjectInfoCommand,
        "rm": RmCommand,
        "resolve": ResolveCommand,
        "state": StateCommand,
        "sync": SyncCommand,
        "unstage": UnstageCommand}

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
