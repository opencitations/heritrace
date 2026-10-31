# SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

FROM --platform=linux/amd64 debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3 AS frontend

ARG FLUTTER_VERSION=3.47.7
ARG FLUTTER_SHA256=af7455f540df951184c7953fbe3cf884766e7541dacf8571f9f582db03dd6230

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git unzip xz-utils && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/flutter.tar.xz \
    "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz" && \
    echo "${FLUTTER_SHA256}  /tmp/flutter.tar.xz" | sha256sum -c - && \
    mkdir -p /opt && tar -xJf /tmp/flutter.tar.xz -C /opt && rm /tmp/flutter.tar.xz

ENV PATH="/opt/flutter/bin:${PATH}"
RUN git config --global --add safe.directory /opt/flutter && flutter config --no-analytics --enable-web

WORKDIR /src
COPY frontend/pubspec.yaml frontend/pubspec.lock ./
RUN flutter pub get --enforce-lockfile
COPY frontend ./
RUN dart run slang && flutter build web --release

FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb

WORKDIR /app

RUN apt-get update && apt-get install -y lsb-release curl gpg && \
    curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg && \
    chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list && \
    apt-get update && \
    apt-get install -y redis-server redis-tools && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.8@sha256:08f409e1d53e77dfb5b65c788491f8ca70fe1d2d459f41c89afa2fcbef998abe /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
COPY heritrace ./heritrace
COPY default_components ./default_components

COPY config.py ./config.py
COPY example_configurations/opencitations_meta/shacl.ttl ./shacl.ttl
COPY example_configurations/opencitations_meta/display_rules.yaml ./display_rules.yaml

RUN uv sync --locked --no-dev

COPY app.py ./
COPY --from=frontend /src/build/web ./frontend/build/web

RUN mkdir -p /data

RUN printf '%b' '#!/bin/bash\n\
set -e\n\
echo "Starting Redis..."\n\
redis-server --daemonize yes --bind 0.0.0.0 --port 6379 --dir /data --save 900 1 --save 300 10 --save 60 10000 --protected-mode no\n\
echo "Waiting for Redis to be ready..."\n\
until redis-cli ping > /dev/null 2>&1; do\n\
  echo "Waiting for Redis..."\n\
  sleep 1\n\
done\n\
echo "Redis is ready"\n\
echo "Starting Gunicorn..."\n\
\n\
# Trap SIGTERM and SIGINT to save Redis data before shutdown\n\
cleanup() {\n\
  echo "Shutting down gracefully..."\n\
  echo "Saving Redis data..."\n\
  redis-cli BGSAVE\n\
  # Wait for background save to complete\n\
  while [ "$(redis-cli LASTSAVE)" = "$(redis-cli LASTSAVE)" ]; do\n\
    sleep 0.1\n\
  done\n\
  echo "Redis data saved"\n\
  redis-cli SHUTDOWN\n\
  exit 0\n\
}\n\
\n\
trap cleanup SIGTERM SIGINT\n\
\n\
exec "$@" &\n\
wait $!' > /app/start.sh && chmod +x /app/start.sh

ENV FLASK_APP=app.py

EXPOSE 5000

CMD ["/app/start.sh", "sh", "-c", "/app/.venv/bin/gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-$(python -c 'import os; print(os.cpu_count() * 2 + 1)')} --timeout ${GUNICORN_TIMEOUT:-120} app:app"]
