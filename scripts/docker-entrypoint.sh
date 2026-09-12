#!/bin/sh
# Start the demo server as the image's own unprivileged account.
#
# A Fly volume is mounted root-owned on first boot, so the output directory has
# to be created and handed over before privileges are dropped. Doing that here
# rather than in the Dockerfile is the point: the build-time /data is a bare
# mount point that the volume then covers.
#
# The unprivileged account is `kicad` specifically. The base image prepared
# KiCad's configuration and library tables under that user's home directory for
# exactly this KiCad version, and ERC and DRC read them.
#
# setpriv rather than su: it execs instead of forking, so the server stays PID 1
# and still receives the SIGTERM it installs a handler for. Under su, Fly's
# graceful shutdown would reach the wrapper and never the server.
set -eu

: "${OHMNI_OUTPUT_DIR:=/data/demo-jobs}"
export OHMNI_OUTPUT_DIR

if [ "$(id -u)" = "0" ]; then
    volume="$(dirname "$OHMNI_OUTPUT_DIR")"
    if [ -d "$OHMNI_OUTPUT_DIR" ]; then
        # Already provisioned. Fixing the two directory entries is enough, and
        # avoids walking a volume full of job artifacts on every boot.
        chown kicad:kicad "$volume" "$OHMNI_OUTPUT_DIR"
    else
        mkdir -p "$OHMNI_OUTPUT_DIR"
        chown -R kicad:kicad "$volume"
    fi
    exec setpriv --reuid=kicad --regid=kicad --init-groups \
        python scripts/demo_server.py --host 0.0.0.0 --port "${PORT:-8080}"
fi

mkdir -p "$OHMNI_OUTPUT_DIR"
exec python scripts/demo_server.py --host 0.0.0.0 --port "${PORT:-8080}"
