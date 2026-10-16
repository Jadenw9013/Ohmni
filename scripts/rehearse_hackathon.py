"""Run local presentation checks and collect fresh evidence; no live AI or Fetch.

Existing checkers own engineering verdicts. A successful report qualifies only
the local guided demo, not an ASI:One conversation, simulation or physical board.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.rehearse_core_demo import qualified
from scripts.run_browser_acceptance import run, scrubbed_environment


def read_receipt(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def receipt_passes(stage: str, receipt: dict) -> bool:
    if stage == "setup":
        checks = receipt.get("checks", [])
        required = {"python", "ohmni", "pydantic", "anthropic", "pytest", "mcp",
                    "uagents", "uagents-core", "playwright", "chromium", "kicad"}
        passing = {c.get("name") for c in checks if c.get("status") == "PASS"}
        return receipt.get("status") == "LOCAL_SETUP_OK" and required <= passing
    if stage == "board":
        attempts = receipt.get("attempts", [])
        return (receipt.get("status") == "PASS" and receipt.get("attempts_requested") == 1
                and receipt.get("tools", {}).get("kicad_cli") == "10.0.5"
                and len(attempts) == 1 and attempts[0].get("status") == "PASS")
    if stage == "browser":
        return (receipt.get("status") == "PASS"
                and qualified(receipt.get("result", {}), receipt.get("process", {})))
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new report directory; existing paths are refused")
    args = parser.parse_args(argv)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = (args.output or ROOT / "build/hackathon-rehearsal" /
              f"{stamp}-{uuid.uuid4().hex[:8]}").resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError:
        print("BLOCKED: output must be a new writable directory; previous evidence was preserved.")
        return 2
    env, _ = scrubbed_environment(dict(os.environ))
    env["OHMNI_TELEMETRY_ENABLED"] = "0"
    stages = [
        ("setup", ["scripts/hackathon_preflight.py", "--fetch", "--browser", "--board", "--json"],
         output / "setup.log", 60),
        ("board", ["scripts/verify_hackathon_demo.py", "--attempts", "1",
                   "--output-root", str(output / "board"),
                   "--summary", str(output / "board-summary.json")],
         output / "board-summary.json", 180),
        ("browser", ["scripts/rehearse_core_demo.py", "--output", str(output / "browser")],
         output / "browser/summary.json", 960),
    ]
    records = []
    stopped = False
    for name, arguments, receipt_path, timeout in stages:
        if stopped:
            records.append({"stage": name, "status": "NOT_RUN"})
            continue
        print(f"Running {name}; log: {output / (name + '.log')}", flush=True)
        try:
            process = run([sys.executable, *arguments], env, output / f"{name}.log", timeout)
            receipt = read_receipt(receipt_path)
            passed = (process.get("exit_code") == 0 and process.get("timed_out") is False
                      and receipt_passes(name, receipt))
            status = "PASS" if passed else (
                "BLOCKED" if process.get("exit_code") == 2 else "FAIL")
        except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
            process = {"exit_code": None, "timed_out": False}
            status = "FAIL"
        records.append({"stage": name, "status": status, "process": process,
                        "receipt": str(receipt_path.relative_to(output))})
        stopped = status != "PASS"
    status = next((r["status"] for r in records if r["status"] != "PASS"), "PASS")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    except (OSError, subprocess.SubprocessError):
        commit, dirty = "UNKNOWN", True
    summary = {"status": status, "commit": commit, "working_tree_dirty": dirty,
               "stages": records, "live_ai": "NOT_RUN", "live_fetch": "NOT_RUN",
               "simulation": "NOT_RUN", "hardware_bench": "NOT_RUN"}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = [f"Local guided demo: {status}", f"Commit: {commit}; uncommitted changes: {dirty}",
             *[f"{r['stage']}: {r['status']}" for r in records],
             "Live AI / Fetch / simulation / hardware bench: NOT RUN",
             "Next: rehearse your pitch on the actual stage display; keep the saved demo ready.",
             "If blocked: docs/hackathon/TROUBLESHOOTING.md"]
    (output / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{status}: {output / 'report.txt'}")
    return 0 if status == "PASS" else 2 if status == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
