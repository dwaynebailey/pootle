# Phase 0, stream B: reproducible Python 2.7 / Django 1.11 test image.
#
# Not a production artifact. This exists purely so the "control channel"
# CI (see .github/workflows/old-stack-ci.yml) has something fixed to run
# the existing test suite against while later phases port the app
# forward. See PORTING.md for the repo/branch strategy this supports.
#
# Builds on the fixes from stream A: debian:stretch is past its own EOL
# and needs its apt sources repointed at the archive (docker/root
# uses the current, patched pipe already), and the apt-packaged
# 'virtualenv' can't bootstrap on this image (stream A2) so pip/virtualenv
# are bootstrapped here via get-pip.py instead.

ARG BUILD_FROM=debian:stretch-slim
FROM $BUILD_FROM

ENV DEBIAN_FRONTEND=noninteractive \
    APP_USER_ID=1000 \
    APP_GROUP_ID=1000 \
    APP_USERNAME=pootle \
    APP_DIR=/app

COPY docker/root /tmp/build-root
RUN /tmp/build-root/install-root

COPY docker/builder/install-build-env /tmp/install-build-env
RUN /tmp/install-build-env

# Headers for the optional DB backends' Python drivers (mysqlclient,
# psycopg2), not part of the shared builder chain since the production
# Dockerfile installs psycopg2-binary as a prebuilt wheel instead.
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
         default-libmysqlclient-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip.py \
    && python2 /tmp/get-pip.py -q \
    && python2 -m pip install -q "virtualenv<20" \
    && rm /tmp/get-pip.py

WORKDIR /src

# Install requirements first so this layer caches across source changes.
# _es_5.txt is needed even for DB-only test runs: saving a unit fires a
# signal (pootle_store/receivers.py) that unconditionally constructs the
# ES-backed TM broker; without the client library installed, that
# constructor is literally None and every such save errors out. Found
# running Phase 0 stream B.
COPY requirements/base.txt requirements/tests.txt requirements/_db_mysql.txt requirements/_db_postgresql.txt requirements/_es_5.txt requirements/
RUN python2 -m virtualenv -q /venv \
    && /venv/bin/pip install --no-cache-dir -q \
         -r requirements/base.txt \
         -r requirements/tests.txt \
         -r requirements/_db_mysql.txt \
         -r requirements/_db_postgresql.txt \
         -r requirements/_es_5.txt

ENV PATH="/venv/bin:${PATH}"

COPY . /src

# pytest_pootle registers itself as a pytest plugin via the pytest11
# entry point in setup.py (see tests/conftest.py's marker errors
# otherwise) - only takes effect once the package itself is installed.
RUN pip install --no-cache-dir -e .

CMD ["pytest", "tests"]
