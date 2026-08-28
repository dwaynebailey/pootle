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
#
# Not a pure swap: Django's vendored copy wasn't byte-identical to
# upstream six - it appends a small "Additional customizations for
# Django" block (six.memoryview, six.buffer_types, used by
# django/utils/encoding.py's force_bytes()) that upstream six doesn't
# have. Re-appended after the copy so nothing Django's own code relies
# on goes missing. Found when force_bytes() broke on
# 'module has no attribute memoryview' during the first real test run.
set -e

DJANGO_SIX=$(python3 -c "import django.utils.six as m; print(m.__file__)")
REAL_SIX=$(python3 -c "import six; print(six.__file__)")
cp "$REAL_SIX" "$DJANGO_SIX"

cat >> "$DJANGO_SIX" << 'PYEOF'


### Additional customizations for Django ###

if PY3:
    memoryview = memoryview
    buffer_types = (bytes, bytearray, memoryview)
else:
    # memoryview and buffer are not strictly equivalent, but should be fine for
    # django core usage (mainly BinaryField). However, Jython doesn't support
    # buffer (see http://bugs.jython.org/issue1521), so we have to be careful.
    if sys.platform.startswith('java'):
        memoryview = memoryview
    else:
        memoryview = buffer
    buffer_types = (bytearray, memoryview)
PYEOF

python3 -c "
from django.utils.six.moves.urllib.parse import quote
from django.utils.six.moves.http_client import responses
from django.utils.six import memoryview, buffer_types
print('django.utils.six.moves and Django-specific extras resolve correctly')
"
