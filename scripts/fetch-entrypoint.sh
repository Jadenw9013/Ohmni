#!/bin/sh
set -eu
: "${OHMNI_FETCH_OUTPUT_DIR:=/data/fetch-jobs}"
export OHMNI_FETCH_OUTPUT_DIR
if [ "$(id -u)" = "0" ]; then
    mkdir -p "$OHMNI_FETCH_OUTPUT_DIR"
    chown kicad:kicad /data "$OHMNI_FETCH_OUTPUT_DIR"
    exec setpriv --reuid=kicad --regid=kicad --init-groups \
        python -m ohmni.integrations.fetch_ai.agent
fi
exec python -m ohmni.integrations.fetch_ai.agent
