#!/bin/bash
# Phase 2 rung 1 (Django 1.11 -> 2.2): django-overextends==0.4.3 is
# abandoned upstream (0.4.3, from 2015, is the last release ever
# published - no maintained fork exists either) and its own
# find_template() reimplementation (overextends/templatetags/
# overextends_tags.py) calls `loader.load_template_source(name, dirs)`
# - the pre-1.9 template loader API. Django's built-in loaders kept a
# deprecated-but-working load_template_source() shim through 1.11 (why
# Phase 1 never hit this), and dropped it outright by 2.2 - every
# {% overextends %}-using template (just one in this codebase,
# import_export/templates/browser/index.html, but it's inherited by
# enough pages to affect ~40 test cases) started failing
# "AttributeError: 'Loader' object has no attribute
# 'load_template_source'" instead of rendering.
#
# Ported find_template() to the modern Loader API
# (get_template_sources()/get_contents(), Origin objects) that's been
# available since Django 1.8 - same search-multiple-directories/
# remove-used-directory behavior the original implemented against the
# old API, just expressed against the new one. Patches the installed
# package directly (like patch-django-postgres-tz.sh does for Django
# itself) rather than rebuilding a wheel - unlike patch-allauth.sh/
# patch-sortedm2m.sh, there's nothing wrong with this package's own
# build here, only its runtime code. Found running Phase 2 rung 1's
# first full-suite pass. See PORTING.md.
set -e

TAGS_PY=$(python3 -c "import overextends.templatetags.overextends_tags as m; print(m.__file__)")

python3 - "$TAGS_PY" << 'PYEOF'
import sys

path = sys.argv[1]
with open(path) as f:
    src = f.read()

old = '''        for loader in loaders:
            dirs = context[context_name][name]
            if not dirs:
                break
            try:
                source, path = loader.load_template_source(name, dirs)
            except TemplateDoesNotExist:
                pass
            else:
                # Only remove the absolute path for the initial call in
                # get_parent, and not when we're peeking during the
                # second call.
                if not peeking:
                    remove_path = os.path.abspath(path[:-len(name) - 1])
                    context[context_name][name].remove(remove_path)
                return Template(source)
        raise TemplateDoesNotExist(name)'''

new = '''        for loader in loaders:
            dirs = context[context_name][name]
            if not dirs:
                break
            # Modern Loader API (Django >= 1.8): get_template_sources()
            # yields Origin objects instead of load_template_source()
            # returning a (source, path) tuple directly. Origin.name is
            # the template's absolute path; derive its containing
            # directory the same way the old path string was sliced, so
            # the existing "search directories, then remove the one
            # just used" bookkeeping below still works unchanged.
            for origin in loader.get_template_sources(name):
                origin_name = os.path.abspath(str(origin.name))
                origin_dir = origin_name[:-len(name) - 1]
                if origin_dir not in dirs:
                    continue
                try:
                    source = loader.get_contents(origin)
                except TemplateDoesNotExist:
                    continue
                # Only remove the absolute path for the initial call in
                # get_parent, and not when we're peeking during the
                # second call.
                if not peeking:
                    context[context_name][name].remove(origin_dir)
                return Template(source)
        raise TemplateDoesNotExist(name)'''

assert old in src, "find_template() body not found - upstream file changed?"
src = src.replace(old, new)

with open(path, "w") as f:
    f.write(src)
PYEOF

python3 -c "
import overextends.templatetags.overextends_tags as m
print('overextends find_template() patched to the modern Loader API OK')
"
