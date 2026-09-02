#!/bin/bash
# Phase 1: Django 1.11's mysql backend (django/db/backends/mysql/
# base.py) unconditionally copies encoders out of the driver's own
# registry when opening a connection:
#
#   def get_new_connection(self, conn_params):
#       conn = Database.connect(**conn_params)
#       conn.encoders[SafeText] = conn.encoders[six.text_type]
#       conn.encoders[SafeBytes] = conn.encoders[bytes]
#       return conn
#
# mysqlclient 1.3.x (the Python 2 baseline's pin, requirements/
# _db_mysql.txt) registered `str`/`bytes` as explicit keys in
# conn.encoders, so copying from them to also cover Django's
# safe-string subclasses (SafeText/SafeBytes) worked. mysqlclient
# 2.2+ (this port's pin, requirements/_db_mysql_py3.txt - see that
# file's own comment for why 1.3.x can't be used under Python 3.12 at
# all) dropped `str`/`bytes` as registered keys and handles them (and
# any subclass, SafeText/SafeBytes included - verified directly) via
# a built-in fallback in the C extension instead, so `conn.encoders`
# has no entry to copy and the very first line raises
# "KeyError: <class 'str'>" on every single database connection.
# Every mariadb-backed test failed with this as a result (found
# running Phase 1's mariadb validation pass - sqlite and postgres
# don't hit this backend module at all). Fix: only copy an encoder
# across when the driver actually registered one, so this degrades
# to a safe no-op on drivers (like this one) that already handle
# SafeText/SafeBytes without it, while staying correct for any driver
# that still needs the explicit copy. See PORTING.md.
set -e

BASE_PY=$(python3 -c "import django.db.backends.mysql.base as m; print(m.__file__)")

python3 - "$BASE_PY" << 'PYEOF'
import sys

path = sys.argv[1]
with open(path) as f:
    src = f.read()

old = (
    "    def get_new_connection(self, conn_params):\n"
    "        conn = Database.connect(**conn_params)\n"
    "        conn.encoders[SafeText] = conn.encoders[six.text_type]\n"
    "        conn.encoders[SafeBytes] = conn.encoders[bytes]\n"
    "        return conn\n"
)
new = (
    "    def get_new_connection(self, conn_params):\n"
    "        conn = Database.connect(**conn_params)\n"
    "        if six.text_type in conn.encoders:\n"
    "            conn.encoders[SafeText] = conn.encoders[six.text_type]\n"
    "        if bytes in conn.encoders:\n"
    "            conn.encoders[SafeBytes] = conn.encoders[bytes]\n"
    "        return conn\n"
)
assert old in src, "get_new_connection body not found - upstream file changed?"
src = src.replace(old, new)

with open(path, "w") as f:
    f.write(src)
PYEOF

python3 -c "
import django.db.backends.mysql.base as base
print('django.db.backends.mysql.base.DatabaseWrapper.get_new_connection patched OK')
"
