#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from django.dispatch import Signal

# Signal's own `providing_args` kwarg was purely documentational
# (Django never validated against it) and got deprecated in 3.0,
# removed in 4.0 - every construction call below fired a
# RemovedInDjango40Warning, turned into a hard failure by this
# project's own filterwarnings=error policy the moment any test
# actually constructed one of these live (module-level constructions,
# as here, only warn once at import time, before pytest's per-test
# warning capture starts - but tests/core/plugin/getters.py and
# providers.py construct their own throwaway Getter/Provider
# instances *inside* test bodies, well within that capture window,
# which is what actually surfaced this). Per Django's own suggested
# migration, the args each signal provides are now just documented in
# a comment alongside each one instead. Phase 2 rung 2 (Django 2.2 ->
# 3.2); see PORTING.md.
# provides: instance, key, value, old_value
changed = Signal(use_caching=True)
# provides: instance, updates
config_updated = Signal(use_caching=True)
# provides: instance, objects
create = Signal(use_caching=True)
# provides: instance, objects
delete = Signal(use_caching=True)
# provides: instance, objects
update = Signal(use_caching=True)
# provides: instance, keep_false_positives
update_checks = Signal(use_caching=True)
# provides: instance
update_data = Signal(use_caching=True)
# provides: instance
update_revisions = Signal(use_caching=True)
# provides: instance, filetype
filetypes_changed = Signal(use_caching=True)
# provides: instance, users
update_scores = Signal(use_caching=True)
# provides: instance, false_positive
toggle = Signal(use_caching=True)
