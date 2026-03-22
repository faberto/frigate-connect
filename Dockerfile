ARG BUILD_FROM
FROM ${BUILD_FROM:-python:3.12-alpine}

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apk add --no-cache ffmpeg

COPY pyproject.toml uv.lock /app/
WORKDIR /app
RUN uv sync --no-dev --frozen

COPY app/ /app/

# Bake in default options for local testing (HA overrides via /data/options.json)
COPY options.json /data/options.json

# s6-overlay service files (used when running as HA addon)
COPY rootfs /
RUN chmod a+x /etc/services.d/frigateconnect/run /etc/services.d/frigateconnect/finish
