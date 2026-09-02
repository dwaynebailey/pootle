# Phase 2, rung 1: Django 1.11 -> 2.2 target environment. Built on top
# of Phase 1's already-solved Python 3.12 problem (same base image, same
# apt packages, same allauth/sortedm2m build patches - none of that is
# Django-version-specific) with Django itself overridden to the 2.2
# line via requirements/django22.txt. See PORTING.md's "Phase 2: Django
# upgrade ladder" section for what's been found and fixed on this rung
# so far.

FROM python:3.12-slim

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      build-essential curl git pkg-config \
      libxml2-dev libxslt-dev libjpeg62-turbo-dev libfreetype6-dev \
      liblcms2-dev libtiff5-dev libwebp-dev \
      default-libmysqlclient-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -q --upgrade pip 'setuptools<81' wheel

WORKDIR /src

# Same two build-time patches Phase 1 needed - both fix Python-3-era
# packaging issues in these packages' setup.py, unrelated to which
# Django version is installed. See docker/py3/patch-*.sh's own
# comments for what each fixes.
COPY docker/py3/patch-allauth.sh docker/py3/patch-sortedm2m.sh docker/py3/
RUN mkdir -p /wheels \
    && bash docker/py3/patch-allauth.sh \
    && bash docker/py3/patch-sortedm2m.sh

# Builds requirements/django22.txt's own pinned django-allauth wheel
# (0.42.0, not base.txt's 0.35.0 - see that file's own note) into the
# same /wheels dir the step above uses, so the django22.txt install
# further down can --find-links its way to it too. Same underlying
# setup.py issue as docker/py3/patch-allauth.sh, just a different
# version; see this script's own comment.
COPY docker/django22/patch-allauth.sh docker/django22/
RUN bash docker/django22/patch-allauth.sh

COPY requirements/base.txt requirements/django22.txt requirements/_es_5.txt requirements/_db_mysql_py3.txt requirements/_db_postgresql_py3.txt requirements/
RUN pip install --no-cache-dir -q \
         -r requirements/base.txt \
         -r requirements/_es_5.txt \
         -r requirements/_db_mysql_py3.txt \
         -r requirements/_db_postgresql_py3.txt \
         --find-links /wheels

COPY . /src
RUN pip install --no-cache-dir -q -e .

COPY requirements/tests_py3.txt requirements/
RUN pip install --no-cache-dir -q -r requirements/tests_py3.txt

# django22.txt installed dead last, as its own separate pip invocation
# - not alongside base.txt/setup.py's install_requires in the same
# command: passed together, pip's resolver sees Django~=1.11.12 (both
# base.txt and, transitively, `pip install -e .` which re-parses
# base.txt for its own install_requires - see setup.py) and
# Django~=2.2.28 (django22.txt) as a real, unsatisfiable conflict in
# one solve and refuses outright (ResolutionImpossible: hit this
# directly when django22.txt was listed alongside base.txt above).
# Installing everything else on the 1.11 pin first and then letting
# this last, independent `pip install` override it in place works
# fine - pip only *warns* about the now-stale "requires
# Django~=1.11.12" metadata rather than blocking, which is exactly
# what's wanted; the warning just reflects that our own setup.py
# hasn't been bumped yet (expected mid-ladder - it moves once this
# rung is actually done, not before). Has to be the true last step,
# after -e . too, or -e .'s own re-resolve would drag Django back
# down to 1.11.
RUN pip install --no-cache-dir -q -r requirements/django22.txt --find-links /wheels

RUN SITE_PACKAGES="$(python3 -c 'import site; print(site.getsitepackages()[0])')" \
    && cp docker/py3/sitecustomize.py "$SITE_PACKAGES/" \
    && cp pootle_py3_compat.py "$SITE_PACKAGES/"

# Django 2.2 vendors the exact same broken django/utils/six.py as 1.11
# did (byte-identical - checked directly), so it needs Phase 1's same
# fix, for the same reason (see patch-django-six.sh's own comment).
# Has to run after the django22.txt install above, not with the other
# patch-*.sh steps near the top of this file - django22.txt reinstalls
# Django 2.2 itself, which would silently overwrite this file back to
# the broken vendored copy if patched any earlier. Phase 2 rung 1; see
# PORTING.md.
COPY docker/py3/patch-django-six.sh docker/py3/
RUN bash docker/py3/patch-django-six.sh

# django-overextends==0.4.3 (abandoned upstream, no maintained fork -
# see requirements/django22.txt's own note on it) calls the pre-1.9
# template loader API, removed outright by Django 2.2. Doesn't depend
# on the django22.txt override above (nothing about this package
# itself changes), just needs to run after overextends is actually
# installed (the main requirements/base.txt step). See the script's
# own comment for the full story. Phase 2 rung 1; see PORTING.md.
COPY docker/django22/patch-overextends.sh docker/django22/
RUN bash docker/django22/patch-overextends.sh

# dj.subcommand==0.0.3's SubcommandsParser relied on a Django
# CommandParser constructor signature removed in Django 2.1. See the
# script's own comment. Phase 2 rung 1; see PORTING.md.
COPY docker/django22/patch-dj-subcommand.sh docker/django22/
RUN bash docker/django22/patch-dj-subcommand.sh
