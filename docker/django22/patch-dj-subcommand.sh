#!/bin/bash
# Phase 2 rung 1 (Django 1.11 -> 2.2): dj.subcommand==0.0.3 (only ever
# one release, no maintained fork) defines two CommandParser
# subclasses - SubcommandsParser and SubcommandsSubParser - neither
# with its own `__init__`. Both relied entirely on Django 1.11's
# `CommandParser.__init__(self, cmd, **kwargs)` storing the command
# instance as `self.cmd` (SubcommandsParser.parse_args() reads
# self.cmd.subcommands; SubcommandsSubParser.format_help() calls
# self.cmd.create_parser()). Django 2.1 changed CommandParser to a
# keyword-only signature with no `cmd` argument at all
# (`__init__(self, *, missing_args_message=None,
# called_from_command_line=None, **kwargs)`) - every subcommand-based
# management command (just `pootle fs`, via
# pootle/apps/pootle_fs/management/commands/fs.py, but exercised by
# ~70 test cases between it and its own subcommands) started raising a
# TypeError from one class or the other, first from SubcommandsParser
# itself ("takes 1 positional argument but 2 were given"), then - once
# that one's fixed - from argparse's own add_subparsers() machinery
# instantiating SubcommandsSubParser with `cmd` in kwargs
# ("ArgumentParser.__init__() got an unexpected keyword argument
# 'cmd'").
#
# Gives both classes back their own __init__: accepts `cmd`
# positionally (SubcommandsParser) or as a keyword (SubcommandsSubParser
# - that's how argparse's add_parser() instantiates it, via **kwargs),
# stores it as self.cmd itself, and forwards everything else to
# Django's now-keyword-only CommandParser.__init__. Patches the
# installed package directly (like patch-django-postgres-tz.sh does
# for Django itself) - nothing wrong with this package's own build,
# only a real API it was relying on changing out from under it. Found
# running Phase 2 rung 1's first full-suite pass. See PORTING.md.
set -e

SUBCOMMANDS_PY=$(python3 -c "import dj.subcommand.subcommands as m; print(m.__file__)")

python3 - "$SUBCOMMANDS_PY" << 'PYEOF'
import sys

path = sys.argv[1]
with open(path) as f:
    src = f.read()

old_parser = "class SubcommandsParser(CommandParser):\n\n    def parse_args(self, args):"
new_parser = (
    "class SubcommandsParser(CommandParser):\n\n"
    "    def __init__(self, cmd, **kwargs):\n"
    "        # See patch-dj-subcommand.sh's own comment for why this\n"
    "        # override exists at all.\n"
    "        self.cmd = cmd\n"
    "        super(SubcommandsParser, self).__init__(**kwargs)\n\n"
    "    def parse_args(self, args):"
)
assert old_parser in src, "SubcommandsParser class header not found - upstream file changed?"
src = src.replace(old_parser, new_parser)

old_subparser = "class SubcommandsSubParser(CommandParser):\n\n    def format_help(self):"
new_subparser = (
    "class SubcommandsSubParser(CommandParser):\n\n"
    "    def __init__(self, **kwargs):\n"
    "        # See patch-dj-subcommand.sh's own comment for why this\n"
    "        # override exists at all. argparse's add_subparsers()\n"
    "        # machinery instantiates this class with `cmd` folded\n"
    "        # into **kwargs (parser_class(**kwargs) in argparse's own\n"
    "        # add_parser()), not positionally.\n"
    "        self.cmd = kwargs.pop('cmd')\n"
    "        super(SubcommandsSubParser, self).__init__(**kwargs)\n\n"
    "    def format_help(self):"
)
assert old_subparser in src, "SubcommandsSubParser class header not found - upstream file changed?"
src = src.replace(old_subparser, new_subparser)

# add_default_arguments() is this package's own hand-rolled copy of
# Django's default command arguments (--version, --verbosity,
# --settings, --pythonpath, --traceback, --no-color), frozen at
# whatever Django version it was written against. Django 2.2 added a
# --force-color argument alongside --no-color, and
# BaseCommand.execute() unconditionally reads options['force_color']
# - never added by this package's own parser, so every subcommand
# invocation KeyErrors there. Add the same argument Django's own
# create_parser() does.
old_no_color = """        parser.add_argument(
            '--no-color',
            action='store_true',
            dest='no_color',
            default=False,
            help="Don't colorize the command output.")"""
new_no_color = old_no_color + """
        parser.add_argument(
            '--force-color',
            action='store_true',
            dest='force_color',
            default=False,
            help='Force colorization of the command output.')"""
assert old_no_color in src, "--no-color argument block not found - upstream file changed?"
src = src.replace(old_no_color, new_no_color)

with open(path, "w") as f:
    f.write(src)
PYEOF

python3 -c "
from dj.subcommand.subcommands import SubcommandsParser, SubcommandsSubParser
p = SubcommandsParser('fake-cmd', prog='x')
assert p.cmd == 'fake-cmd'
sp = SubcommandsSubParser(cmd='fake-cmd', prog='x')
assert sp.cmd == 'fake-cmd'
print('SubcommandsParser and SubcommandsSubParser accept cmd again OK')
"
