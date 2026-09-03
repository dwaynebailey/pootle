#!/bin/bash
# Phase 2 rung 1 (Django 1.11 -> 2.2): base.txt pins django-
# allauth==0.35.0 (Phase 1's own pin, patched by docker/py3/
# patch-allauth.sh for the same setup.py issue this script fixes) -
# its adapter.py calls `django.utils.http.is_safe_url(url)` with a
# single argument, but Django 2.1 made the second parameter
# (`allowed_hosts`) required, so every login/logout view (the
# redirect-safety check runs on every request through allauth's
# adapter) started raising "TypeError: is_safe_url() missing 1
# required positional argument: 'allowed_hosts'" - a 500 instead of a
# redirect. 0.42.0 is the first release both requiring Django>=2.0 and
# declaring support through Django 3.0 (0.39.0 is the first to declare
# 2.2 support at all, but still supports back to 1.11; there's no
# reason to pick the narrowest option when a wider one - covering this
# rung and headroom into the next - exists), and fixes this call site
# itself upstream rather than needing our own patch for it.
#
# Same setup.py issue as 0.35.0 though (checked directly - byte-
# identical `from setuptools import convert_path, find_packages,
# setup` line): current setuptools no longer exports convert_path.
# Same fix, just re-pointed at 0.42.0's own sdist - kept as its own
# script here rather than editing docker/py3/patch-allauth.sh in
# place, since that one still needs to keep building 0.35.0 for
# Phase 1's still-active image. Found running Phase 2 rung 1's first
# full-suite pass. See PORTING.md.
set -e

VERSION=0.42.0
WORKDIR=$(mktemp -d)
cd "$WORKDIR"

curl -sSfL "https://files.pythonhosted.org/packages/5c/fc/ada953944ad773b5953677adfbc3c7bc6c7a853502fde12843e780e29535/django-allauth-${VERSION}.tar.gz" -o allauth.tar.gz
tar xzf allauth.tar.gz
cd "django-allauth-${VERSION}"

python3 - <<'PYEOF'
content = open('setup.py').read()
patched = content.replace(
    'from setuptools import convert_path, find_packages, setup',
    'from setuptools import find_packages, setup\n'
    'try:\n'
    '    from setuptools import convert_path\n'
    'except ImportError:\n'
    '    from os import sep\n'
    '    def convert_path(pathname):\n'
    '        return pathname.replace("/", sep)\n'
)
assert patched != content, 'patch target not found - has upstream setup.py changed?'
open('setup.py', 'w').write(patched)
PYEOF

pip install --no-cache-dir -q setuptools wheel
python setup.py -q bdist_wheel -d /wheels
