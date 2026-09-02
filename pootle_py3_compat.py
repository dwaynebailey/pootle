# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

"""Python 3 compatibility shims for Django 1.11 itself (Phase 1 of the
Python 3 port - see PORTING.md).

Django 1.11 (2017) officially supports Python 3.4-3.7 and was never
updated for what Python removed since. These patch the *runtime
environment* Django's own code sees, not Django's source.

Deliberately NOT part of the `pootle` package: it needs to be
importable, and applied, before anything - including pytest's own
plugin auto-discovery, which can load a plugin (django-assets
registers its own pytest11 entry point, independent of anything pootle
imports) before pootle is ever imported at all. Importing anything
under `pootle.*` first would run pootle/__init__.py and mark the
`pootle` package as already-imported in sys.modules before pytest's
assertion-rewrite import hook installs, which pytest then reports as
a (filterwarnings=error-fatal) warning. See docker/py3/sitecustomize.py,
which is what actually invokes this early enough, and
pootle/syspath_override.py, which also imports this for non-pytest
entry points (manage.py, gunicorn, ...).

Phase 2's Django ladder removes the need for each of these one hop at
a time; until then this is what makes "Python 3.12 now, Django
upgrades later" work as two independent axes rather than one blocking
the other.
"""

import collections
import collections.abc
import gettext


def apply():
    # Python 3.10 dropped the long-deprecated collections.Iterator/
    # Mapping/... aliases for collections.abc's versions; several
    # Django 1.11 internals (e.g. django/db/models/sql/query.py) and
    # third-party deps (e.g. pytz.lazy) still import them from
    # `collections` directly. Restore the aliases rather than patching
    # every such call site inside third-party packages.
    for name in (
        'Callable', 'Iterable', 'Iterator', 'Mapping', 'MutableMapping',
        'MutableSequence', 'MutableSet', 'Sequence', 'Set',
    ):
        if not hasattr(collections, name):
            setattr(collections, name, getattr(collections.abc, name))

    # django/utils/translation/trans_real.py calls
    # self.set_output_charset('utf-8') "for Python 2 gettext()" (its
    # own comment, referencing Django ticket #25720) - Python's
    # gettext module dropped that method (and the whole output-charset
    # concept, meaningless once all strings are unicode) a while ago.
    # Harmless no-op restores it rather than patching Django's source
    # for a call that does nothing under Python 3 anyway.
    if not hasattr(gettext.NullTranslations, 'set_output_charset'):
        gettext.NullTranslations.set_output_charset = (
            lambda self, charset: None)

    # Same story, same call site's neighbour: _new_gnu_trans() calls
    # gettext.translation(..., codeset=...) - the codeset kwarg was
    # removed from Python's gettext module for the same reason. Wrap
    # the stdlib function to silently drop it rather than patching the
    # call site.
    if not getattr(gettext.translation, '_pootle_codeset_shim', False):
        _original_translation = gettext.translation

        def _translation_without_codeset(*args, **kwargs):
            kwargs.pop('codeset', None)
            return _original_translation(*args, **kwargs)

        _translation_without_codeset._pootle_codeset_shim = True
        gettext.translation = _translation_without_codeset


apply()
