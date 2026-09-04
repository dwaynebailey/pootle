#!/bin/bash
# Phase 2 rung 2 (Django 2.2 -> 3.2): Django 3.0 removed
# django/utils/six.py outright (rung 1 only had to fix its *content* -
# Django 2.2 still vendored a byte-identical, broken copy of it; by
# 3.2 the file doesn't exist at all). Several third-party dependencies
# still do `from django.utils import six` at their own module level
# (django_rq's decorators.py before the version bump in requirements/
# django32.txt fixed that one specifically; jsonfield==2.0.2's
# encoder.py does the same and has no newer release available to fix
# it that way - checked, 2.0.2 is jsonfield's last PyPI release) - a
# hard ImportError under Django 3.2, `ImportError: cannot import name
# 'six' from 'django.utils'`, the moment anything imports jsonfield's
# JSONField (our own pootle_config app, hit by literally the first
# django.setup() during any test run).
#
# Recreates the file from scratch (rung 1's patch-django-six.sh
# overwrote an existing broken copy - there's nothing to overwrite
# here) using the real `six` package's own source, same as rung 1,
# plus the same "Additional customizations for Django" block Django's
# own copy used to carry (memoryview/buffer_types, used by
# django/utils/encoding.py's force_bytes()) so nothing any caller
# relies on goes missing. Fixes every third-party (or, in principle,
# in-house) caller doing `from django.utils import six` in one place,
# rather than patching each dependency individually. Found running
# Phase 2 rung 2's first django.setup() probe. See PORTING.md.
set -e

DJANGO_UTILS_DIR=$(python3 -c "import django.utils as m; print(m.__path__[0])")
DJANGO_SIX="$DJANGO_UTILS_DIR/six.py"
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
