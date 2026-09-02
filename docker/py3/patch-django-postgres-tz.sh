#!/bin/bash
# Phase 1: Django 1.11's postgresql backend
# (django/db/backends/postgresql/utils.py) compares the offset psycopg2
# hands its cursor.tzinfo_factory against the bare int 0:
#
#   def utc_tzinfo_factory(offset):
#       if offset != 0:
#           raise AssertionError("database connection isn't set to UTC")
#
# psycopg2 2.7 (the Python 2 baseline's pin, requirements/
# _db_postgresql.txt) passed that offset as an int number of minutes,
# so a UTC connection's offset (0) compared equal. psycopg2 2.8+ (this
# port's requirements/_db_postgresql_py3.txt pins >=2.9, see that
# file's own comment for why 2.7 won't build under Python 3.12 at all)
# passes a datetime.timedelta instead - and timedelta.__eq__ returns
# NotImplemented for a non-timedelta operand, so `timedelta(0) != 0` is
# True even on a genuinely-UTC connection. Every postgres-backed test
# failed with this AssertionError as a result (found running Phase 1's
# postgres validation pass - sqlite and mariadb don't hit this backend
# module at all). Upstream Django fixed this the same way once psycopg2
# 2.8 shipped; this is that fix, backported onto Django 1.11's copy at
# image-build time. See PORTING.md.
set -e

UTILS_PY=$(python3 -c "import django.db.backends.postgresql.utils as m; print(m.__file__)")

python3 - "$UTILS_PY" << 'PYEOF'
import sys

path = sys.argv[1]
with open(path) as f:
    src = f.read()

old = "def utc_tzinfo_factory(offset):\n    if offset != 0:\n"
new = (
    "def utc_tzinfo_factory(offset):\n"
    "    if offset != timedelta(0):\n"
)
assert old in src, "utc_tzinfo_factory body not found - upstream file changed?"
src = src.replace(old, new)

old_import = "from django.utils.timezone import utc\n"
new_import = "from datetime import timedelta\n\nfrom django.utils.timezone import utc\n"
assert old_import in src, "expected import line not found - upstream file changed?"
src = src.replace(old_import, new_import)

with open(path, "w") as f:
    f.write(src)
PYEOF

python3 -c "
from django.db.backends.postgresql.utils import utc_tzinfo_factory
from datetime import timedelta
utc_tzinfo_factory(timedelta(0))
print('utc_tzinfo_factory accepts a timedelta(0) offset correctly')
"
