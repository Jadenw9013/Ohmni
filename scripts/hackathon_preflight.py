"""Read-only local readiness checks. Never calls models or registers an agent.

Use --board to require the native pinned KiCad CLI as well as Python setup.
Docker installation is reported separately; this script does not start Docker,
pull images, or establish that a container can build a board.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inspect(require_board: bool, require_fetch: bool = False,
            require_browser: bool = False) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    supported = (3, 12) <= sys.version_info[:2] <= (3, 13)
    add("python", "PASS" if supported else "BLOCKED",
        f"{sys.version.split()[0]}; use Python 3.13 for the Fetch integration")
    for package in ("ohmni", "pydantic", "anthropic", "pytest"):
        try:
            version = metadata.version(package)
        except metadata.PackageNotFoundError:
            add(package, "BLOCKED", "missing; install the repo with its dev extra")
        else:
            add(package, "PASS", version)
    optional = {"mcp": ("2.2.0", require_fetch),
                "uagents": ("0.26.1", require_fetch),
                "uagents-core": ("0.4.12", require_fetch),
                "playwright": ("1.56.0", require_browser)}
    for package, (expected, required) in optional.items():
        try:
            version = metadata.version(package)
        except metadata.PackageNotFoundError:
            add(package, "BLOCKED" if required else "WARN",
                "not installed; run scripts/setup_hackathon.py")
        else:
            matched = version == expected
            add(package, ("PASS" if matched else "BLOCKED") if required else "INFO",
                f"{version}; expected {expected}; presence does not prove integration")

    if require_browser and not any(c["name"] == "playwright" and
                                   c["status"] == "BLOCKED" for c in checks):
        try:
            from playwright.sync_api import Error as BrowserError
            from playwright.sync_api import sync_playwright
        except ImportError:
            add("chromium", "BLOCKED", "browser discovery failed; rerun setup and check Playwright")
        else:
            try:
                with sync_playwright() as playwright:
                    exists = Path(playwright.chromium.executable_path).is_file()
                add("chromium", "PASS" if exists else "BLOCKED",
                    "matching executable present; browser launch NOT CHECKED" if exists else
                    "missing; run python -m playwright install chromium")
            except (BrowserError, OSError, RuntimeError):
                add("chromium", "BLOCKED", "browser discovery failed; rerun setup and check Playwright")

    license_exists = any((ROOT / name).is_file() for name in
                         ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"))
    add("project_license", "INFO" if license_exists else "WARN",
        "file present; review its terms" if license_exists else
        "no root license found; owner must resolve existing-project reuse eligibility")
    for name in ("AGENTS.md", "docs/hackathon/FETCH_AI_IMPLEMENTATION_PLAN.md",
                 "examples/hackathon-demo/demo.json"):
        add(name, "PASS" if (ROOT / name).is_file() else "BLOCKED",
            "present" if (ROOT / name).is_file() else "missing checkout input")

    if any(check["status"] == "BLOCKED" for check in checks):
        add("native_tools", "INFO", "install the required Python environment before probing tools")
        return checks
    # Reuse production fallback discovery without importing a provider or EDA runner.
    sys.path.insert(0, str(ROOT / "src"))
    from ohmni.adapters.tools import find_kicad_cli

    executable = find_kicad_cli()
    kicad_status = "BLOCKED" if require_board else "WARN"
    if executable:
        try:
            result = subprocess.run([executable, "version"], capture_output=True,
                                    text=True, timeout=8, check=False)
            version = result.stdout.strip()
            pinned = result.returncode == 0 and version == "10.0.5"
            add("kicad", "PASS" if pinned else kicad_status,
                "10.0.5 detected; run the qualification harness next" if pinned else
                "version unavailable or different from the qualified 10.0.5")
        except (OSError, subprocess.SubprocessError):
            add("kicad", kicad_status, "CLI probe failed or timed out")
    else:
        add("kicad", kicad_status, "not detected; fresh native PCB builds are blocked")
    add("docker", "INFO", "CLI installed; daemon and image NOT CHECKED" if
        shutil.which("docker") else "CLI not detected; native KiCad remains an option")
    add("live_fetch", "INFO", "NOT CHECKED: registration, connectivity, discovery and quotas")
    add("credentials", "INFO", "NOT READ: supply secrets only to an authorized runtime")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", action="store_true", help="require native KiCad 10.0.5")
    parser.add_argument("--fetch", action="store_true", help="require pinned Fetch and MCP SDKs")
    parser.add_argument("--browser", action="store_true", help="require Playwright and Chromium")
    parser.add_argument("--json", action="store_true", help="print structured output")
    args = parser.parse_args()
    checks = inspect(args.board, args.fetch, args.browser)
    blocked = any(check["status"] == "BLOCKED" for check in checks)
    status = "BLOCKED" if blocked else "LOCAL_SETUP_OK"
    if args.json:
        print(json.dumps({"status": status, "checks": checks}, indent=2))
    else:
        for check in checks:
            print(f'{check["status"]:7} {check["name"]}: {check["detail"]}')
        print(f"{status}: local checks only; no engineering or live agent qualification")
    return 2 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
