# Phase 1: Python 3 port target environment. Not a production image yet
# (no app server, no asset pipeline) - this exists to validate the port
# itself: that requirements install and the app imports/runs cleanly
# under Python 3.12. See PORTING.md for what's been found and fixed so
# far, and docker/py3/patch-*.sh for why each patch step exists.

FROM python:3.12-slim

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      build-essential curl git \
      libxml2-dev libxslt-dev libjpeg62-turbo-dev libfreetype6-dev \
      liblcms2-dev libtiff5-dev libwebp-dev \
      default-libmysqlclient-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -q --upgrade pip setuptools wheel

WORKDIR /src

COPY docker/py3/patch-allauth.sh docker/py3/patch-sortedm2m.sh docker/py3/
RUN mkdir -p /wheels \
    && bash docker/py3/patch-allauth.sh \
    && bash docker/py3/patch-sortedm2m.sh

COPY requirements/base.txt requirements/
RUN pip install --no-cache-dir -q -r requirements/base.txt --find-links /wheels

COPY docker/py3/patch-django-six.sh docker/py3/
RUN bash docker/py3/patch-django-six.sh

COPY . /src
RUN pip install --no-cache-dir -q -e .

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
