# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.


from pootle.core.plugin.delegate import Getter, Provider


# `providing_args` dropped throughout this file - see
# pootle/core/signals.py's own comment for why. Phase 2 rung 2
# (Django 2.2 -> 3.2); see PORTING.md.
config = Getter()  # provides: instance
search_backend = Getter()  # provides: instance
lang_mapper = Getter()  # provides: instance
state = Getter()
response = Getter()
check_updater = Getter()
comparable_event = Getter()
contributors = Getter()
crud = Getter()
display = Getter()
event_score = Provider()
event_formatters = Provider()
formats = Getter()
format_registration = Provider()
format_classes = Provider()
format_diffs = Provider()
format_updaters = Provider()
format_syncers = Provider()
frozen = Getter()
filetype_tool = Getter()
grouped_events = Getter()
lifecycle = Getter()
log = Getter()
stemmer = Getter()
site_languages = Getter()
terminology = Getter()
terminology_matcher = Getter()
tp_tool = Getter()
data_tool = Getter()
data_updater = Getter()
language_code = Getter()
language_team = Getter()
membership = Getter()
paths = Getter()
profile = Getter()
review = Getter()
revision = Getter()
revision_updater = Getter()
scores = Getter()
score_updater = Getter()
site = Getter()
states = Getter()
stopwords = Getter()
text_comparison = Getter()
panels = Provider()

serializers = Provider()  # provides: instance
deserializers = Provider()  # provides: instance
subcommands = Provider()
uniqueid = Getter()
unitid = Provider()
url_patterns = Provider()
wordcount = Getter()

# view.context_data
context_data = Provider()  # provides: view, context

upstream = Provider()
versioned = Getter()
