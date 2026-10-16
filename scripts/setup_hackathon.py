"""Prepare a checkout's .venv; never starts servers, agents or model calls.

Run with Python 3.13. Native tools are checked, not automatically installed.
--check makes no environment changes and never installs packages or browsers.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], timeout: int = 600) -> int:
    print("Running: " + " ".join(command), flush=True)
    try:
        return subprocess.run(command, cwd=ROOT, timeout=timeout, check=False).returncode
    except (OSError, subprocess.SubprocessError):
        print("BLOCKED: command failed to start or timed out; see troubleshooting guide.")
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the existing venv only")
    parser.add_argument("--skip-browser", action="store_true",
                        help="skip Chromium download/check; Python browser package is still installed")
    parser.add_argument("--board", action="store_true", help="also require native KiCad 10.0.5")
    args = parser.parse_args(argv)
    if not (3, 12) <= sys.version_info[:2] <= (3, 13):
        print("BLOCKED: use python3.13 (macOS/Linux) or py -3.13 (Windows).")
        return 2
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        if args.check:
            print("BLOCKED: .venv missing; rerun without --check to create it.")
            return 2
        if environment.exists():
            print("BLOCKED: incomplete .venv; rename it and rerun. No existing files removed.")
            return 2
        try:
            venv.EnvBuilder(with_pip=True).create(environment)
        except (OSError, subprocess.SubprocessError):
            print("BLOCKED: could not create .venv; check disk space and Python's venv support.")
            return 2
    # Check an existing venv before installing into it; it may use another Python.
    probe = [str(python), "-c", "import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] <= (3,13) else 2)"]
    if run(probe) != 0:
        print("BLOCKED: .venv must use Python 3.12 or 3.13; preserve/rename it before recreating.")
        return 2
    if not args.check:
        if run([str(python), "-m", "pip", "install", "-e", ".[dev,mcp,browser,fetch]"]) != 0:
            print("BLOCKED: dependency installation failed; setup did not complete.")
            return 2
        if not args.skip_browser and run(
                [str(python), "-m", "playwright", "install", "chromium"]) != 0:
            print("BLOCKED: Chromium installation failed; use --skip-browser for backend-only work.")
            return 2
    if run([str(python), "-m", "pip", "check"]) != 0:
        return 2
    if run([str(python), "scripts/ai_state.py", "validate"]) != 0:
        return 2
    preflight = [str(python), "scripts/hackathon_preflight.py", "--fetch"]
    if not args.skip_browser:
        preflight.append("--browser")
    if args.board:
        preflight.append("--board")
    if run(preflight) != 0:
        return 2
    print("LOCAL SETUP OK. Native board qualification and live Fetch acceptance are separate.")
    print("Next: docs/LOCAL_ENGINEERING_SETUP.md and docs/hackathon/TROUBLESHOOTING.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
