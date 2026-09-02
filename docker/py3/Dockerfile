# Phase 1: Python 3 port target environment. Not a production image yet
# (no app server, no asset pipeline) - this exists to validate the port
# itself: that requirements install and the app imports/runs cleanly
# under Python 3.12. See PORTING.md for what's been found and fixed so
# far, and docker/py3/patch-*.sh for why each patch step exists.

FROM python:3.12-slim

# pkg-config: needed to build mysqlclient>=2.2 (requirements/
# _db_mysql_py3.txt) - without it, setup.py can't locate mysql_config/
# mariadb_config at all. Phase 1 Python 3 port; see PORTING.md.
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      build-essential curl git pkg-config \
      libxml2-dev libxslt-dev libjpeg62-turbo-dev libfreetype6-dev \
      liblcms2-dev libtiff5-dev libwebp-dev \
      default-libmysqlclient-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# setuptools<81: bleach==2.1.3 (requirements/base.txt) still does
# `from pkg_resources import parse_version` - pkg_resources was split
# out of setuptools's default install starting around 81 and is
# slated for removal outright. bleach is already flagged in stream
# G's dependency audit (10 known advisories against this exact pin)
# as due for a real upgrade later; pinning setuptools here is the
# narrow, in-scope fix to keep it importable under Python 3.12 for
# now. Phase 1 Python 3 port; see PORTING.md.
RUN pip install --no-cache-dir -q --upgrade pip 'setuptools<81' wheel

WORKDIR /src

COPY docker/py3/patch-allauth.sh docker/py3/patch-sortedm2m.sh docker/py3/
RUN mkdir -p /wheels \
    && bash docker/py3/patch-allauth.sh \
    && bash docker/py3/patch-sortedm2m.sh

# _es_5.txt is needed even for DB-only test runs: saving a unit fires a
# post_save receiver that instantiates SearchBroker(), which imports
# every configured search backend module - including elasticsearch.py,
# whose top-level `Elasticsearch = None` ImportError fallback turns
# into a plain TypeError the moment a test actually saves a unit.
# Mirrors docker/ci/Dockerfile's Python 2 baseline (see its own
# comment); verified elasticsearch~=5.0 installs and imports cleanly
# under Python 3.12. Phase 1 Python 3 port; see PORTING.md.
# _db_mysql_py3.txt / _db_postgresql_py3.txt: current-compatible pins
# for the DB drivers, so this one image can run against sqlite,
# postgres, or mariadb by just setting APP_DB_ENV (see
# tests/settings.py) - see those files' own comments for why the
# Python 2 baseline's requirements/_db_*.txt pins don't work under
# Python 3.12. Phase 1 Python 3 port; see PORTING.md.
COPY requirements/base.txt requirements/_es_5.txt requirements/_db_mysql_py3.txt requirements/_db_postgresql_py3.txt requirements/
RUN pip install --no-cache-dir -q \
         -r requirements/base.txt \
         -r requirements/_es_5.txt \
         -r requirements/_db_mysql_py3.txt \
         -r requirements/_db_postgresql_py3.txt \
         --find-links /wheels

COPY docker/py3/patch-django-six.sh docker/py3/
RUN bash docker/py3/patch-django-six.sh

COPY . /src
RUN pip install --no-cache-dir -q -e .

# requirements/tests.txt pins pytest==3.3.0 and friends for the
# Python 2 control channel (docker/ci/Dockerfile) - none of that runs
# under Python 3 (pytest 3.3.0 imports the removed stdlib `imp`
# module, among other things). tests_py3.txt is the separate,
# current-compatible pin for this image. Baked into the image itself,
# not left as a runtime `pip install` tacked onto CMD/command: a
# container command override (`docker run pootle-py3 pytest ...`,
# `docker-compose run test pytest ...`) replaces the whole command,
# so anything installed only at runtime would silently vanish. Phase
# 1 Python 3 port; see PORTING.md.
COPY requirements/tests_py3.txt requirements/
RUN pip install --no-cache-dir -q -r requirements/tests_py3.txt

# See sitecustomize.py's own comment for why this has to be a
# site-wide startup hook rather than living solely in pootle/__init__.py
# or a conftest.py. pootle_py3_compat.py is copied alongside it (not
# just relied on via the editable install's own sys.path setup): the
# `site` module imports sitecustomize.py before it's finished
# processing the editable-install .pth file that would otherwise make
# the repo root (and pootle_py3_compat.py within it) importable.
RUN SITE_PACKAGES="$(python3 -c 'import site; print(site.getsitepackages()[0])')" \
    && cp docker/py3/sitecustomize.py "$SITE_PACKAGES/" \
    && cp pootle_py3_compat.py "$SITE_PACKAGES/"

# Runs after the sitecustomize.py install above (not alongside the
# other patch-*.sh steps earlier in this file): its self-check imports
# django.db.backends.postgresql.utils, which imports django.utils.
# timezone, which imports pytz - and pytz still does `from collections
# import Mapping`, only satisfiable once the compat shim just installed
# is in place. See the script's own comment for what it fixes.
COPY docker/py3/patch-django-postgres-tz.sh docker/py3/patch-django-mysql-encoders.sh docker/py3/
RUN bash docker/py3/patch-django-postgres-tz.sh \
    && bash docker/py3/patch-django-mysql-encoders.sh
