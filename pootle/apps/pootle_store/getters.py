# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from django.conf import settings
from django.core.exceptions import ValidationError

from pootle.core.delegate import (
    deserializers, frozen, lifecycle, review, search_backend, serializers,
    uniqueid, wordcount)
from pootle.core.plugin import getter
from pootle_config.delegate import (
    config_should_not_be_set, config_should_not_be_appended)
from pootle_misc.util import import_func

from .models import Suggestion, Unit
from .unit.search import DBSearchBackend
from .utils import (
    FrozenUnit, SuggestionsReview, UnitLifecycle, UnitUniqueId, UnitWordcount)


wordcounter = None


@getter(wordcount, sender=Unit)
def get_unit_wordcount(**kwargs_):
    global wordcounter

    if not wordcounter:
        wordcounter = UnitWordcount(
            import_func(settings.POOTLE_WORDCOUNT_FUNC))
    return wordcounter


@getter(frozen, sender=Unit)
def get_frozen_unit(**kwargs_):
    return FrozenUnit


@getter(search_backend, sender=Unit)
def get_search_backend(**kwargs_):
    return DBSearchBackend


@getter(review, sender=Suggestion)
def get_suggestions_review(**kwargs_):
    return SuggestionsReview


@getter(uniqueid, sender=Unit)
def get_unit_uniqueid(**kwargs_):
    return UnitUniqueId


@getter(lifecycle, sender=Unit)
def get_unit_lifecylcle(**kwargs_):
    return UnitLifecycle


@getter([config_should_not_be_set, config_should_not_be_appended])
def serializer_should_not_be_saved(**kwargs):

    if kwargs["key"] == "pootle.core.serializers":
        if not isinstance(kwargs["value"], list):
            return ValidationError(
                "pootle.core.serializers must be a list")
        available_serializers = list(serializers.gather(kwargs["sender"]).keys())
        for k in kwargs["value"]:
            if k not in available_serializers:
                return ValidationError(
                    "Unrecognised pootle.core.serializers: '%s'" % k)
    elif kwargs["key"] == "pootle.core.deserializers":
        if not isinstance(kwargs["value"], list):
            return ValidationError(
                "pootle.core.deserializers must be a list")
        available_deserializers = list(
            deserializers.gather(kwargs["sender"]).keys())
        for k in kwargs["value"]:
            if k not in available_deserializers:
                return ValidationError(
                    "Unrecognised pootle.core.deserializers: '%s'" % k)
