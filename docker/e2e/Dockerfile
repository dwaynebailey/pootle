# Phase 0, stream D: a running instance for the Playwright smoke suite to
# point at. Same install steps as docker/ci/Dockerfile (see that file for
# why each one is needed - the archive.debian.org mirror fix, the pip/
# virtualenv bootstrap, the ES client, `pip install -e .`) duplicated here
# rather than built FROM it, to keep each Dockerfile buildable standalone
# in CI without a two-step build order. Worth consolidating in Phase 5.

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

RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
         default-libmysqlclient-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip.py \
    && python2 /tmp/get-pip.py -q \
    && python2 -m pip install -q "virtualenv<20" \
    && rm /tmp/get-pip.py

WORKDIR /src

COPY requirements/base.txt requirements/_db_postgresql.txt requirements/_es_5.txt requirements/
RUN python2 -m virtualenv -q /venv \
    && /venv/bin/pip install --no-cache-dir -q \
         -r requirements/base.txt \
         -r requirements/_db_postgresql.txt \
         -r requirements/_es_5.txt

ENV PATH="/venv/bin:${PATH}"

COPY . /src

RUN pip install --no-cache-dir -e .
RUN bash docker/e2e/stub-assets.sh
RUN cp docker/e2e/91-e2e.conf pootle/settings/91-e2e.conf

EXPOSE 8000
ENTRYPOINT ["bash", "docker/e2e/entrypoint.sh"]
