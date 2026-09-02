# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from fnmatch import translate

from django.utils.functional import cached_property

from pootle.core.exceptions import MissingPluginError, NotConfiguredError

from .delegate import fs_plugins


class PathFilter(object):

    def path_regex(self, path):
        # fnmatch.translate()'s output format changed: Python 2 ended
        # every pattern with the literal suffix "\Z(?ms)" (an anchor
        # plus trailing inline flags); Python 3.6+ instead wraps the
        # whole body in a scoped "(?s:...)" group and ends with just
        # "\Z". Callers of path_regex() strip trailing anchors
        # themselves (see _tp_path_regex() below) so they can append
        # their own suffix - stripping the old Python 2 string here
        # was always a no-op replace under Python 3, silently leaving
        # a stray mid-pattern "\Z" that made every match impossible.
        # Phase 1 Python 3 port; see PORTING.md.
        pattern = translate(path).replace(r"\Z", "$")
        # These patterns get sent straight through to the database as
        # a regex lookup (pootle_path__regex / path__regex), not run
        # through Python's re module - and "(?s:...)" is Python re's
        # own syntax for a scoped inline-flags group, not portable:
        # MySQL/MariaDB's PCRE-based REGEXP accepts it, but
        # PostgreSQL's regex engine doesn't support the
        # "(?flags:pattern)" form at all and raises "invalid regular
        # expression: quantifier operand invalid" on every query that
        # uses one. None of these glob-derived patterns need DOTALL
        # (paths don't contain newlines), so it's safe to just unwrap
        # the group rather than translate it to each backend's own
        # inline-flag syntax. Found running Phase 1's postgres
        # validation pass. Phase 1 Python 3 port; see PORTING.md.
        if pattern.startswith("(?s:") and pattern.endswith(")$"):
            pattern = pattern[len("(?s:"):-len(")$")] + "$"
        # Python 3.11+'s fnmatch.translate() also wraps runs of "*"
        # in an atomic group, "(?>...)", to avoid catastrophic
        # backtracking on adversarial input - another Perl/PCRE
        # extension PostgreSQL's regex engine doesn't support (same
        # "quantifier operand invalid" error as the (?s:...) case
        # above, just from a group that can appear anywhere in the
        # pattern rather than only wrapping the whole thing, so it
        # can't be unwrapped the same way). Downgrading to a plain
        # non-capturing group is semantically identical for matching
        # purposes - only the backtracking-safety optimization is
        # lost, which doesn't matter for these short, bounded,
        # glob-derived patterns. Phase 1 Python 3 port; see PORTING.md.
        pattern = pattern.replace("(?>", "(?:")
        return pattern


class StorePathFilter(PathFilter):
    """Filters Stores (only pootle_path)
    pootle_path should be file a glob
    the glob is converted to a regex and used to filter a qs
    """

    def __init__(self, pootle_path=None):
        self.pootle_path = pootle_path

    @cached_property
    def pootle_regex(self):
        if not self.pootle_path:
            return
        return self.path_regex(self.pootle_path)

    def filtered(self, qs):
        if not self.pootle_regex:
            return qs
        return qs.filter(pootle_path__regex=self.pootle_regex)


class StoreFSPathFilter(StorePathFilter):
    """Filters StoreFS
    pootle_path and fs_path should be file globs
    these are converted to regexes and used to filter a qs
    """

    def __init__(self, pootle_path=None, fs_path=None):
        super(StoreFSPathFilter, self).__init__(pootle_path=pootle_path)
        self.fs_path = fs_path

    @cached_property
    def fs_regex(self):
        if not self.fs_path:
            return
        return self.path_regex(self.fs_path)

    def filtered(self, qs):
        qs = super(StoreFSPathFilter, self).filtered(qs)
        if not self.fs_regex:
            return qs
        return qs.filter(path__regex=self.fs_regex)


class FSPlugin(object):
    """Wraps a Project to access the configured FS plugin"""

    def __init__(self, project):
        self.project = project
        plugins = fs_plugins.gather(self.project.__class__)
        fs_type = project.config.get("pootle_fs.fs_type")
        fs_url = project.config.get("pootle_fs.fs_url")
        if not fs_type or not fs_url:
            missing_key = "pootle_fs.fs_url" if fs_type else "pootle_fs.fs_type"
            raise NotConfiguredError('Missing "%s" in project configuration.' %
                                     missing_key)
        try:
            self.plugin = plugins[fs_type](self.project)
        except KeyError:
            raise MissingPluginError(
                "No such plugin: %s" % fs_type)

    @property
    def __class__(self):
        return self.plugin.__class__

    def __getattr__(self, k):
        return getattr(self.plugin, k)

    def __eq__(self, other):
        return self.plugin.__eq__(other)

    # Python 2 kept the default identity-based __hash__ even when a
    # class defined __eq__; Python 3 sets __hash__ to None as soon as
    # __eq__ is defined without it - and __getattr__ isn't consulted
    # for implicit dunder lookups like hash(), so it has to be
    # explicit here too, delegating like __eq__ does. Phase 1 Python
    # 3 port; see PORTING.md.
    def __hash__(self):
        return self.plugin.__hash__()

    def __str__(self):
        return str(self.plugin)


def parse_fs_url(fs_url):
    fs_type = 'localfs'
    chunks = fs_url.split('+', 1)
    if len(chunks) > 1:
        if chunks[0] in fs_plugins.gather().keys():
            fs_type = chunks[0]
            fs_url = chunks[1]
    return fs_type, fs_url
