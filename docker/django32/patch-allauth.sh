#!/bin/bash
# Phase 2 rung 2 (Django 2.2 -> 3.2): rung 1's own django-allauth pin
# (0.42.0) only declares support through Django 3.0. 0.48.0 is the
# first release declaring support through 4.0 (covers this rung and
# headroom into the next). Same setup.py issue as every other allauth
# version patched so far (checked directly - byte-identical
# `from setuptools import convert_path, find_packages, setup` line):
# current setuptools no longer exports convert_path. Same fix, just
# re-pointed at 0.48.0's own sdist - kept as its own script here
# rather than editing docker/django22/patch-allauth.sh or docker/py3/
# patch-allauth.sh in place, since those still need to keep building
# their own pinned versions for their own still-active images. See
# PORTING.md.
set -e

VERSION=0.48.0
WORKDIR=$(mktemp -d)
cd "$WORKDIR"

curl -sSfL "https://files.pythonhosted.org/packages/35/cd/314ff076c83b77b59c650780b0f16cc2ee506ebd0b2bfac151622379f80f/django-allauth-${VERSION}.tar.gz" -o allauth.tar.gz
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
