#!/usr/bin/env python3
"""Canonical development verification entrypoint for Ohmni's pytest tiers."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import tempfile

ROOT = Path(__file__).resolve().parents[1]
_PYTEST_BASE_PREFERRED = ROOT / "build" / "pytest"
PYTEST_CACHE = ROOT / "build" / "pytest-cache"


def _writable_basetemp() -> Path:
    """Return build/pytest if writable; fall back to a system temp dir."""
    try:
        _PYTEST_BASE_PREFERRED.mkdir(parents=True, exist_ok=True)
        probe = _PYTEST_BASE_PREFERRED / ".write_probe"
        probe.write_text("ok")
        probe.unlink()
        return _PYTEST_BASE_PREFERRED
    except OSError:
        return Path(tempfile.mkdtemp(prefix="ohmni-pytest-"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tier", choices=("workflow", "fast", "integration", "slow", "full"))
    args = parser.parse_args(argv)
    basetemp = _writable_basetemp()
    (ROOT / "build").mkdir(parents=True, exist_ok=True)
    pytest = [
        sys.executable,
        "-m",
        "pytest",
        "--basetemp",
        str(basetemp),
        "-o",
        f"cache_dir={PYTEST_CACHE}",
    ]
    commands = {
        "workflow": pytest
        + ["tests/test_ai_workflow.py", "-o", "addopts=-q --strict-markers"],
        "fast": pytest,
        "integration": pytest + ["-m", "integration"],
        "slow": pytest + ["-m", "slow_integration"],
        "full": pytest + ["-o", "addopts=-q --strict-markers"],
    }
    result = subprocess.run(commands[args.tier], cwd=ROOT, check=False, shell=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
