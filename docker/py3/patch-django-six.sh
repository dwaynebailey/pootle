#!/bin/bash
# Phase 1: Django 1.11's vendored django/utils/six.py (frozen circa
# 2017) fails to resolve django.utils.six.moves.* under Python 3.12's
# import system, even though the real `six` package (also installed,
# per requirements/base.txt) works fine. six.py's own machinery
# (_SixMetaPathImporter, the `moves` lazy module) keys off its module's
# __name__ at import time, so aliasing sys.modules after the fact
# doesn't work - it has to genuinely be *imported as* django.utils.six.
# Overwriting the installed file with the real six package's source
# does exactly that, at image-build time, in the one place it's needed.
set -e

DJANGO_SIX=$(python3 -c "import django.utils.six as m; print(m.__file__)")
REAL_SIX=$(python3 -c "import six; print(six.__file__)")
cp "$REAL_SIX" "$DJANGO_SIX"
python3 -c "
from django.utils.six.moves.urllib.parse import quote
from django.utils.six.moves.http_client import responses
print('django.utils.six.moves resolves correctly')
"
