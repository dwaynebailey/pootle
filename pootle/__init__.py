# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

# Adds pootle's flat-namespace app directories (pootle_app,
# pootle_store, ...) to sys.path - needed before Django tries to import
# any of them. The Python 3 / Django 1.11 compatibility shims this used
# to also carry live in pootle_py3_compat.py now (imported by
# syspath_override below too, but also - and earlier - by
# docker/py3/sitecustomize.py directly, for import orderings where even
# this __init__.py runs too late; see that module's docstring for why).
from pootle import syspath_override  # noqa

from pootle.core.utils.version import get_version
from pootle.constants import VERSION


__version__ = get_version(VERSION)
