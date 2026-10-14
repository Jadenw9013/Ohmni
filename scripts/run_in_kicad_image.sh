#!/bin/sh
# Run a command from this checkout inside the pinned production KiCad image.
#
#   scripts/run_in_kicad_image.sh python3 scripts/verify_hackathon_demo.py
#
# The checkout is mounted at /repo. By default the declared dev dependencies are
# installed into a throwaway venv inside the container (needs package-index
# access). Set OHMNI_HOST_SITE_PACKAGES to an existing Python 3.13
# site-packages directory to mount it instead, for offline sandboxes.
# HOME stays /home/kicad so KiCad finds the library tables the image prepared.
set -eu
IMAGE="${OHMNI_KICAD_IMAGE:-kicad/kicad:10.0.5}"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
# The mounted checkout belongs to another uid; let git inside read its HEAD.
GIT_SAFE="-e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0=/repo"
if [ "$#" -eq 0 ]; then
    echo "usage: $0 <command> [args...]" >&2
    exit 64
fi
if [ -n "${OHMNI_HOST_SITE_PACKAGES:-}" ]; then
    exec docker run --rm -u root -e HOME=/home/kicad \
        -v "$ROOT":/repo -v "$OHMNI_HOST_SITE_PACKAGES":/sitepkgs:ro -w /repo \
        -e PYTHONPATH=/repo/src:/sitepkgs -e PYTHONDONTWRITEBYTECODE=1 $GIT_SAFE \
        "$IMAGE" "$@"
fi
exec docker run --rm -u root -e HOME=/home/kicad -v "$ROOT":/repo -w /repo \
    -e PYTHONDONTWRITEBYTECODE=1 $GIT_SAFE "$IMAGE" sh -c '
        set -e
        apt-get update -qq >/dev/null
        apt-get install -y -qq --no-install-recommends python3-venv >/dev/null
        python3 -m venv /tmp/venv
        /tmp/venv/bin/pip install -q -e ".[dev]"
        PATH=/tmp/venv/bin:$PATH exec "$@"' sh "$@"
