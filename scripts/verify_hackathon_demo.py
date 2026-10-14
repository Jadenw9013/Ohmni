#!/usr/bin/env python3
"""Fresh, fail-closed engineering reproduction of the hackathon demonstration board.

Runs the production ProjectPipeline for the fixed A2 minimum brief through real
KiCad ERC, routing, DRC, manufacturing checks and Gerber/drill export, once per
attempt, each into a new directory. Every attempt is re-qualified from its own
on-disk receipts. The machine-readable summary records the Git commit, brief,
tool versions, input/output hashes, check results and measured timings.

Exit codes: 0 every attempt qualified; 1 an attempt failed; 2 blocked (the
required KiCad CLI is missing or is not the pinned version). A blocked run is
never reported as a pass.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ohmni.adapters.tools import find_kicad_cli
from ohmni.application.hackathon_demo import (
    CONVERSATIONAL_WORDING,
    DEMO_BRIEF,
    REQUIRED_CHECKS,
    run_attempt,
    sha256_file,
)

PINNED_KICAD_VERSION = "10.0.5"
HASHED_OUTPUTS = (
    "confirmed-brief.json", "circuit.json", "golden.kicad_sch", "golden.kicad_pcb",
    "erc-report.json", "drc-report.json", "routing-plan.json",
    "fabrication/ohmni-fabrication-manifest.json",
)


def _git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "UNKNOWN"


def kicad_version(executable: str) -> str | None:
    try:
        completed = subprocess.run([executable, "version"], capture_output=True, text=True,
                                   timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = completed.stdout.strip()
    return output if completed.returncode == 0 and output else None


def _catalog_snapshot() -> str | None:
    from ohmni.catalog import default_catalog
    return getattr(default_catalog(), "snapshot_hash", None)


def _pipeline_factory(progress):
    from ohmni.application.projects import ProjectPipeline
    return ProjectPipeline(progress)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--attempts", type=int, default=3, help="fresh sequential attempts (default 3)")
    parser.add_argument("--output-root", type=Path, default=ROOT / "build" / "hackathon-demo")
    parser.add_argument("--summary", type=Path, default=None,
                        help="summary path (default <run directory>/summary.json)")
    parser.add_argument("--kicad-version", default=PINNED_KICAD_VERSION,
                        help="required kicad-cli version, or 'any' (default %(default)s)")
    args = parser.parse_args(argv)
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")

    started_at = datetime.now(UTC)
    run_id = started_at.strftime("%Y%m%dT%H%M%SZ")
    run_directory = (args.output_root / run_id).resolve()
    if run_directory.exists():
        parser.error(f"run directory already exists: {run_directory}")
    run_directory.mkdir(parents=True)
    summary_path = (args.summary or run_directory / "summary.json").resolve()

    executable = find_kicad_cli()
    version = kicad_version(executable) if executable else None
    summary: dict[str, object] = {
        "schema_version": 1,
        "harness": "scripts/verify_hackathon_demo.py",
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "git": {"commit": _git("rev-parse", "HEAD"),
                "dirty": bool(_git("status", "--porcelain"))},
        "brief": {"fingerprint": DEMO_BRIEF.fingerprint,
                  "normalized": DEMO_BRIEF.model_dump(mode="json"),
                  "conversational_wording_for_rehearsal": CONVERSATIONAL_WORDING,
                  "live_prompt_rehearsal": "PENDING (no model call is made by this harness)"},
        "tools": {"kicad_cli": version, "kicad_cli_required": args.kicad_version,
                  "python": platform.python_version(), "platform": platform.platform()},
        "inputs": {"catalog_snapshot_sha256": _catalog_snapshot()},
        "attempts_requested": args.attempts,
        "attempts": [],
    }

    blocked = None
    if executable is None or version is None:
        blocked = "kicad-cli is not installed or did not report a version"
    elif args.kicad_version != "any" and version != args.kicad_version:
        blocked = f"kicad-cli {version} is not the pinned {args.kicad_version}"
    if blocked:
        summary.update(status="BLOCKED", reason=blocked)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"BLOCKED: {blocked}. No board was qualified. Summary: {summary_path}")
        return 2

    attempts = []
    for index in range(1, args.attempts + 1):
        attempt = run_attempt(run_directory / f"attempt-{index}", _pipeline_factory)
        outputs = {name: sha256_file(attempt.directory / name)
                   for name in HASHED_OUTPUTS if (attempt.directory / name).is_file()}
        record = {
            "attempt": index,
            "directory": str(attempt.directory.relative_to(ROOT) if attempt.directory.is_relative_to(ROOT)
                             else attempt.directory),
            "status": "PASS" if attempt.passed else "FAIL",
            "missing_required_checks": sorted(REQUIRED_CHECKS - {c.name for c in attempt.qualification.checks}),
            "total_seconds": attempt.total_seconds,
            "stage_seconds": attempt.stage_seconds,
            "checks": [check.as_dict() for check in attempt.qualification.checks],
            "warnings": attempt.qualification.warnings,
            "output_sha256": outputs,
            "fault": attempt.fault,
        }
        report_path = attempt.directory / "report.json"
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            record["release"] = {key: report["release"].get(key)
                                 for key in ("status", "package_fingerprint", "pcb_fingerprint", "current")}
            record["part_count"] = len(json.loads((attempt.directory / "circuit.json")
                                                  .read_text(encoding="utf-8"))["components"])
            record["board_mm"] = [DEMO_BRIEF.board_width_mm, DEMO_BRIEF.board_height_mm]
            record["routing"] = report["pcb"].get("statistics")
            record["limitations"] = report.get("limitations")
        attempts.append(record)
        print(f"attempt {index}: {record['status']} in {attempt.total_seconds:.1f}s "
              f"({sum(c.passed for c in attempt.qualification.checks)}/"
              f"{len(attempt.qualification.checks)} checks)")
        for check in attempt.qualification.checks:
            if not check.passed:
                print(f"  FAIL {check.name}: {check.detail}")

    summary["attempts"] = attempts
    passed = len(attempts) == args.attempts and all(item["status"] == "PASS" for item in attempts)
    pcb_hashes = {item["output_sha256"].get("golden.kicad_pcb") for item in attempts}
    summary["cross_attempt"] = {
        "identical_routed_pcb_bytes": len(pcb_hashes) == 1 and None not in pcb_hashes,
        "note": "Recorded, not required: KiCad logs and timestamps are not promised byte-identical.",
    }
    summary["status"] = "PASS" if passed else "FAIL"
    summary["finished_at"] = datetime.now(UTC).isoformat()
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['status']}: {sum(item['status'] == 'PASS' for item in attempts)}/{args.attempts} "
          f"attempts qualified with kicad-cli {version}. Summary: {summary_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
