#!/usr/bin/env python3
"""Canonical development verification entrypoint for Ohmni's pytest tiers."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

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


def _writable_cache() -> Path:
    """Return build/pytest-cache if writable; fall back to a temp dir."""
    preferred = ROOT / "build" / "pytest-cache"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write_probe"
        probe.write_text("ok")
        probe.unlink()
        return preferred
    except OSError:
        return Path(tempfile.mkdtemp(prefix="ohmni-pytest-cache-"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tier", choices=("workflow", "fast", "integration", "corpus", "slow", "full")
    )
    args = parser.parse_args(argv)
    basetemp = _writable_basetemp()
    cache_dir = _writable_cache()
    (ROOT / "build").mkdir(parents=True, exist_ok=True)
    pytest = [
        sys.executable,
        "-m",
        "pytest",
        "--basetemp",
        str(basetemp),
        "-o",
        f"cache_dir={cache_dir}",
    ]
    commands = {
        "workflow": pytest
        + ["tests/test_ai_workflow.py", "-o", "addopts=-q --strict-markers"],
        "fast": pytest,
        "integration": pytest + ["-m", "integration"],
        # The corpus tier is a separate evidence gate on purpose. `fast` runs
        # offline and skips every source-dependent test when the pinned
        # manufacturer PDFs are absent, so a green `fast` run must never be able
        # to stand in for "the checks were exercised against the real document".
        # This tier fails when they are absent instead of skipping.
        "corpus": pytest + ["-m", "corpus", "-o", "addopts=-q --strict-markers -p no:randomly"],
        "slow": pytest + ["-m", "slow_integration"],
        "full": pytest + ["-o", "addopts=-q --strict-markers"],
    }
    if args.tier == "corpus":
        # A skip is honest but it is not evidence. This gate requires the pinned
        # sources to be present, so "the corpus tests passed" can never mean
        # "the corpus tests did not run".
        presence = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "acquire_corpus.py"), "--check"],
            cwd=ROOT, check=False, shell=False,
        )
        if presence.returncode != 0:
            print(
                "corpus gate: the pinned manufacturer sources are absent.\n"
                "  Run: python scripts/acquire_corpus.py\n"
                "This gate fails rather than skipping, because a skipped source check is "
                "not evidence that the source was checked."
            )
            return presence.returncode
    result = subprocess.run(commands[args.tier], cwd=ROOT, check=False, shell=False)
    if args.tier == "corpus" and result.returncode == 0:
        print("corpus gate: the pinned sources were present and every corpus test ran.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
