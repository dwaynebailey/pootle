# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from django.dispatch import Signal


# `providing_args` dropped - see pootle/core/signals.py's own comment
# for why. Phase 2 rung 2 (Django 2.2 -> 3.2); see PORTING.md.
# provides: comment
comment_was_saved = Signal(use_caching=True)
