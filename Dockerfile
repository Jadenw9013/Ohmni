# syntax=docker/dockerfile:1
# Authored behavior benches require ngspice 42, not the base image's distro
# version. Build the official release with a checked archive and keep compiler
# dependencies out of the runtime image.
FROM kicad/kicad:10.0.5 AS ngspice42
USER root
RUN apt-get update && apt-get install -y --no-install-recommends build-essential bison flex curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/ngspice-build
RUN curl --fail --location --retry 3 https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/old-releases/42/ngspice-42.tar.gz -o source.tar.gz \
    && echo "737fe3846ab2333a250dfadf1ed6ebe1860af1d8a5ff5e7803c772cc4256e50a  source.tar.gz" | sha256sum -c - \
    && tar -xzf source.tar.gz \
    && cd ngspice-42 \
    && ./configure --prefix=/opt/ngspice42 --without-x --with-readline=no --enable-xspice --enable-cider --disable-debug \
    && make -j2 && make install \
    && /opt/ngspice42/bin/ngspice -v

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
ENV PATH="$VIRTUAL_ENV/bin:/opt/ngspice42/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python3 -m venv "$VIRTUAL_ENV"
COPY --from=ngspice42 /opt/ngspice42 /opt/ngspice42

WORKDIR /app

# Dependencies come from pyproject.toml alone, so the declared set is the
# installed set -- anthropic included. The provider imports it lazily and
# nothing calls a model until ANTHROPIC_API_KEY is set.
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY apps/ ./apps/
COPY scripts/ ./scripts/
# The behavior API validates source anchors and historical receipt references at
# runtime. Keep those inputs in the image; they are not public static assets.
COPY COMPONENT_BEHAVIOR_SPEC.md ./
COPY docs/behavior/ ./docs/behavior/
COPY out/component-behavior/run/bench-results/ ./out/component-behavior/run/bench-results/
RUN python -c "from pathlib import Path; from ohmni.application.component_behavior import ComponentBehaviorService; s = ComponentBehaviorService(Path('/app'), Path('/tmp/behavior-package-check')); assert len(s.summary()) == s.registry.manifest.entry_count; r = s.run('OHM-001'); print(r['version_output']); assert r['status'] == 'ran', r"
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
