#!/bin/bash
#
# Phase 0, stream D: stub webpack output so pages using {% assets 'js_*' %}
# render at all. The real JS bundles (pootle/apps/pootle_app/assets.py)
# reference literal pre-built webpack output files with no source list for
# webassets to assemble - they're not "built" by ASSETS_DEBUG the way the
# CSS bundles are (stream B), they're expected to already exist.
#
# These stubs are NOT real assets: every page they touch renders with zero
# working JS, so anything relying on the JS-mounted editor (translate,
# suggest, accept) is explicitly out of scope for the Playwright smoke
# suite these unblock - see PORTING.md. They exist purely so
# server-rendered pages (login, browse, admin, permissions, uploads,
# checks, terminology) don't 500 on load. Real bundles come from the
# Phase 4 frontend rebuild, at which point this script goes away.
#
# Never committed: *.bundle.js is already gitignored, and these are
# generated fresh in the e2e image, not checked into source.

set -e

cd "$(dirname "$0")/../../pootle/static/js"

for f in \
    vendor.bundle.js \
    common/app.bundle.js \
    admin/general/app.bundle.js \
    admin/app.bundle.js \
    user/app.bundle.js \
    editor/app.bundle.js
do
    mkdir -p "$(dirname "$f")"
    echo "// stub for Phase 0 stream D - not a real webpack build, see docker/e2e/stub-assets.sh" > "$f"
done
