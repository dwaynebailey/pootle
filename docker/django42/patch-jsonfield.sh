#!/bin/bash
# Phase 2 rung 3 (Django 3.2 -> 4.2): jsonfield==2.0.2 (no newer PyPI
# release exists - same situation as rung 2's own django.utils.six
# problem for this exact package) imports `ugettext_lazy` from
# django.utils.translation at its own module level
# (jsonfield/fields.py) - `ugettext_lazy` was unified with
# `gettext_lazy` back in Django 2.0 (Python 3's strings made the u-
# prefixed names redundant, same reasoning as pootle/i18n/gettext.py's
# own rung-1 fix) and finally removed outright in Django 4.0. A hard
# ImportError the moment anything imports jsonfield's JSONField (our
# own pootle_config app, hit by the very first django.setup() during
# any test run). Patches the installed package directly, same style as
# the postgres-tz/mysql-encoders/overextends patches - there's nothing
# wrong with jsonfield's own *build*, only now-removed imports. See
# PORTING.md.
#
# A second, independent removed-API import in the same package,
# jsonfield/encoder.py's own `force_text` (deprecated in 3.0, removed
# in 4.0 - see PORTING.md's rung 2 section for the full force_text
# story, this is the same API, just a different caller), is patched
# below too - found immediately after fixing the first one, same
# module-import-time shape.
set -e

# Can't use `import jsonfield.fields` (or even importlib.util.
# find_spec('jsonfield.fields') - that still has to import the
# `jsonfield` package itself first to resolve the submodule) to locate
# the file: jsonfield/__init__.py's own `from .fields import ...`
# already hits the exact ImportError being patched. Resolve the path
# directly off site-packages instead.
JSONFIELD_DIR="$(python3 -c 'import site; print(site.getsitepackages()[0])')/jsonfield"
JSONFIELD_FIELDS="$JSONFIELD_DIR/fields.py"
JSONFIELD_ENCODER="$JSONFIELD_DIR/encoder.py"
if [ ! -f "$JSONFIELD_FIELDS" ] || [ ! -f "$JSONFIELD_ENCODER" ]; then
    echo "patch target not found under $JSONFIELD_DIR - has jsonfield's layout changed?" >&2
    exit 1
fi

sed -i.bak 's/from django.utils.translation import ugettext_lazy as _/from django.utils.translation import gettext_lazy as _/' "$JSONFIELD_FIELDS"
rm -f "$JSONFIELD_FIELDS.bak"

sed -i.bak \
    -e 's/from django.utils.encoding import force_text/from django.utils.encoding import force_str/' \
    -e 's/force_text(/force_str(/g' \
    "$JSONFIELD_ENCODER"
rm -f "$JSONFIELD_ENCODER.bak"

python3 -c "
from jsonfield.fields import JSONField, JSONCharField
from jsonfield.encoder import JSONEncoder
print('jsonfield.fields and jsonfield.encoder import correctly')
"
