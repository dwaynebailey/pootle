# Phase 2, rung 3: Django 3.2 -> 4.2 target environment. Built on top
# of Phase 1's already-solved Python 3.12 problem (same base image, same
# apt packages, same Python-3-packaging build patches - none of that is
# Django-version-specific) with Django itself overridden to the 4.2
# line via requirements/django42.txt. See PORTING.md's "Phase 2: Django
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

COPY requirements/base.txt requirements/django42.txt requirements/_es_5.txt requirements/_db_mysql_py3.txt requirements/_db_postgresql_py3.txt requirements/
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

# django42.txt installed dead last, as its own separate pip invocation
# - same reasoning as rungs 1 and 2's own overrides: passed alongside
# base.txt/setup.py's install_requires in one command, pip's resolver
# sees Django~=1.11.12 and Django~=4.2.30 as a real, unsatisfiable
# conflict and refuses outright. Has to be the true last step, after
# -e . too, or -e .'s own re-resolve would drag Django back down to
# 1.11. Unlike rung 2, this rung's own django-allauth pin (0.61.0)
# needs no build-time patch (see requirements/django42.txt's own
# comment) so there's no per-rung wheel to --find-links here beyond
# the two Phase-1 ones already built above.
RUN pip install --no-cache-dir -q -r requirements/django42.txt --find-links /wheels

RUN SITE_PACKAGES="$(python3 -c 'import site; print(site.getsitepackages()[0])')" \
    && cp docker/py3/sitecustomize.py "$SITE_PACKAGES/" \
    && cp pootle_py3_compat.py "$SITE_PACKAGES/"

# django.utils.six stays removed under 4.2 too (gone outright since
# 3.0 - see rung 2's own patch-django-six.sh comment for the full
# story). Reused unchanged, not duplicated: nothing about recreating
# this file is Django-4.2-specific. Has to run after the django42.txt
# override above, same reason as every rung so far - that override
# reinstalls Django itself, which doesn't ship this file at all.
COPY docker/django32/patch-django-six.sh docker/django32/
RUN bash docker/django32/patch-django-six.sh

# jsonfield==2.0.2 (no newer release exists, same as rung 2's own
# six.py finding for this package) still imports the removed
# `ugettext_lazy` at its own module level. See this script's own
# comment. Phase 2 rung 3; see PORTING.md.
COPY docker/django42/patch-jsonfield.sh docker/django42/
RUN bash docker/django42/patch-jsonfield.sh

# Both carried over unchanged from rung 1 (reused directly, not
# duplicated - checked directly that the exact code each one targets
# is byte-identical between Django 2.2, 3.2, and 4.2, so there's
# nothing rung-specific to change):
# - dj.subcommand==0.0.3's SubcommandsParser/SubcommandsSubParser
#   still rely on the same Django 2.1-era CommandParser signature
#   rung 1 already patched around.
# - django-overextends==0.4.3 still calls the same pre-1.9
#   `load_template_source()` loader API rung 1 already ported to the
#   modern one.
# Phase 2 rung 3; see PORTING.md.
COPY docker/django22/patch-dj-subcommand.sh docker/django22/patch-overextends.sh docker/django22/
RUN bash docker/django22/patch-dj-subcommand.sh \
    && bash docker/django22/patch-overextends.sh
