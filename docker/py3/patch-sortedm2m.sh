#!/bin/bash
# Phase 1: django-sortedm2m==1.5.0's setup.py wraps long_description in
# a Python-2-era 'UltraMagicString' class (a unicode-metadata workaround
# from ~2010, see the setup.py comment crediting a Stack Overflow
# answer) that current setuptools' metadata writer chokes on - it calls
# .endswith() on it, which UltraMagicString doesn't implement. Python 3
# str doesn't need the workaround this class existed for; patch
# long_description to a plain string and build a wheel at image-build
# time. Not vendored, same as patch-allauth.sh.
set -e

VERSION=1.5.0
WORKDIR=$(mktemp -d)
cd "$WORKDIR"

curl -sSfL "https://files.pythonhosted.org/packages/70/54/3eaf25cdefdd4ea82a68537428f41536a086dc2200662ae55253d4a96c1f/django-sortedm2m-${VERSION}.tar.gz" -o sortedm2m.tar.gz
tar xzf sortedm2m.tar.gz
cd "django-sortedm2m-${VERSION}"

python3 - <<'PYEOF'
lines = open('setup.py').readlines()
found = False
for i, line in enumerate(lines):
    if 'long_description = UltraMagicString' in line:
        lines[i] = line.replace('UltraMagicString(', '(')
        found = True
assert found, 'patch target not found - has upstream setup.py changed?'
open('setup.py', 'w').writelines(lines)
PYEOF

pip install --no-cache-dir -q setuptools wheel
python setup.py -q bdist_wheel -d /wheels
