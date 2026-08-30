#!/usr/bin/env python3
"""Canonical development verification entrypoint for Ohmni's pytest tiers."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tier", choices=("workflow", "fast", "integration", "slow", "full"))
    args = parser.parse_args(argv)
    commands = {
        "workflow": [sys.executable, "-m", "pytest", "tests/test_ai_workflow.py", "-o", "addopts=-q --strict-markers"],
        "fast": [sys.executable, "-m", "pytest"],
        "integration": [sys.executable, "-m", "pytest", "-m", "integration"],
        "slow": [sys.executable, "-m", "pytest", "-m", "slow_integration"],
        "full": [sys.executable, "-m", "pytest", "-o", "addopts=-q --strict-markers"],
    }
    result = subprocess.run(commands[args.tier], cwd=ROOT, check=False, shell=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

