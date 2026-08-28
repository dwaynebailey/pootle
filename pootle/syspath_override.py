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

import collections
import collections.abc
import gettext
import os
import sys


ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
POOTLE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, ROOT_DIR)  # Top level directory
sys.path.insert(0, POOTLE_DIR)  # Pootle directory

sys.path.insert(0, os.path.join(POOTLE_DIR, 'apps'))  # Applications


# --- Python 3 compatibility shim for Django 1.11 itself ---------------
#
# Django 1.11 (2017) officially supports Python 3.4-3.7 and was never
# updated for what Python removed since. Python 3.10 dropped the
# long-deprecated collections.Iterator/Mapping/... aliases for
# collections.abc's versions; several Django 1.11 internals (e.g.
# django/db/models/sql/query.py) still import them from `collections`
# directly. Restore the aliases rather than patching every such call
# site inside a third-party package. (Django's *other* Python-3.12
# incompatibility - its vendored django/utils/six.py not resolving
# django.utils.six.moves.* correctly - is fixed at image-build time by
# overwriting that file with the real `six` package's source instead;
# see docker/py3/patch-django-six.sh. That one can't be a runtime shim:
# six.py's own internals key off its module's __name__ at import time,
# so it has to genuinely be imported *as* django.utils.six, not aliased
# to it afterwards.)
#
# Phase 2's Django ladder removes the need for this one hop at a time;
# until then it's what makes "Python 3.12 now, Django upgrades later"
# work as two independent axes rather than one blocking the other.
for _name in (
    'Callable', 'Iterable', 'Iterator', 'Mapping', 'MutableMapping',
    'MutableSequence', 'MutableSet', 'Sequence', 'Set',
):
    if not hasattr(collections, _name):
        setattr(collections, _name, getattr(collections.abc, _name))

# django/utils/translation/trans_real.py calls
# self.set_output_charset('utf-8') "for Python 2 gettext()" (its own
# comment, referencing Django ticket #25720) - Python's gettext module
# dropped that method (and the whole output-charset concept, meaningless
# once all strings are unicode) a while ago. Harmless no-op restores it
# rather than patching Django's source for a call that does nothing
# under Python 3 anyway.
if not hasattr(gettext.NullTranslations, 'set_output_charset'):
    gettext.NullTranslations.set_output_charset = lambda self, charset: None

# Same story, same call site's neighbour: django/utils/translation/
# trans_real.py's _new_gnu_trans() calls gettext.translation(...,
# codeset=...) - the codeset kwarg was removed from Python's gettext
# module for the same reason (output charset is meaningless once
# everything is unicode). Wrap the stdlib function to silently drop it
# rather than patching the call site.
_gettext_translation = gettext.translation


def _translation_without_codeset(*args, **kwargs):
    kwargs.pop('codeset', None)
    return _gettext_translation(*args, **kwargs)


gettext.translation = _translation_without_codeset
