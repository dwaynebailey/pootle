# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

"""Adds pootle directories to the python import path"""

# FIXME: is this useful on an installed codebase or only when running from
# source?

import os
import sys

# Applies the Python 3 / Django 1.11 compatibility shims - kept in a
# standalone top-level module rather than inline here or elsewhere
# under the `pootle` package on purpose; see pootle_py3_compat.py's own
# docstring for why. docker/py3/sitecustomize.py is the earliest actual
# entry point for it (needed before some import orderings, e.g.
# pytest's plugin auto-discovery); this import here is what covers
# every other entry point (manage.py, gunicorn, ...).
import pootle_py3_compat  # noqa


ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
POOTLE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)  # Top level directory
sys.path.insert(0, POOTLE_DIR)  # Pootle directory

sys.path.insert(0, os.path.join(POOTLE_DIR, 'apps'))  # Applications
