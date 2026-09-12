# syntax=docker/dockerfile:1
# Ohmni demo backend.
#
# KiCad is present, and it is pinned. Both are deliberate:
#
# * Present, because Ohmni refuses to publish a board no external checker saw.
#   `require_eda_check` turns an UNAVAILABLE ERC into a failed job rather than a
#   pass, so an image without kicad-cli completes exactly zero designs.
# * Pinned to 10.0.5, because ERC and DRC verdicts are read out of KiCad's own
#   JSON. The checker version is part of the result, and this is the version
#   every verdict in this repository was verified against.
FROM kicad/kicad:10.0.5

USER root

# The KiCad image is Debian trixie, whose system interpreter is externally
# managed (PEP 668), so the application gets its own virtual environment
# instead of fighting the distribution's packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python3 -m venv "$VIRTUAL_ENV"

WORKDIR /app

# Dependencies come from pyproject.toml alone, so the declared set is the
# installed set -- anthropic included. The provider imports it lazily and
# nothing calls a model until ANTHROPIC_API_KEY is set.
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY apps/ ./apps/
COPY scripts/ ./scripts/
# A checkout will not carry the mode bit on every platform.
RUN chmod +x scripts/docker-entrypoint.sh && chown -R kicad:kicad /app

# Jobs, artifacts and the local project database live on the Fly volume mounted
# at /data; demo_server.py reads OHMNI_OUTPUT_DIR to find it. HOME points at the
# account the entrypoint drops to, whose KiCad configuration and library tables
# the base image prepared for this KiCad version.
ENV OHMNI_OUTPUT_DIR=/data/demo-jobs \
    OHMNI_DB_PATH=/data/ohmni.sqlite3 \
    HOME=/home/kicad

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=4)"

# Root only long enough to take ownership of the mounted volume; the server
# itself runs as `kicad`. See scripts/docker-entrypoint.sh.
ENTRYPOINT ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]
