#!/bin/bash
# Phase 1: django-allauth==0.35.0 never shipped a wheel (its first wheel
# release, 65.13.0, requires a much newer Django than 1.11 - see
# PORTING.md), and its setup.py imports setuptools.convert_path, which
# current setuptools no longer exports. convert_path('.') is a no-op on
# POSIX; patch a one-line fallback and build a wheel at image-build
# time. Not vendored - rebuilt fresh from the real PyPI sdist every
# time, this script is the only thing committed.
set -e

VERSION=0.35.0
WORKDIR=$(mktemp -d)
cd "$WORKDIR"

curl -sSfL "https://files.pythonhosted.org/packages/source/d/django-allauth/django-allauth-${VERSION}.tar.gz" -o allauth.tar.gz
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
