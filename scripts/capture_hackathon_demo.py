#!/usr/bin/env python3
"""Package one qualified hackathon run as a labeled, offline saved demonstration.

Input is an attempt directory written by scripts/verify_hackathon_demo.py (with
its fault/ diagnostic) and that run's summary.json. Nothing is generated here:
the good board is re-verified through the existing reference-preview exporter
(which re-runs KiCad ERC and DRC on reproduced artifacts), and the damaged copy
is displayed only from its own snapshot bytes. Requires the pinned kicad-cli.

Writes, under --output (default examples/hackathon-demo):
  demo.json                       viewer data, provenance and both check results
  saved-run/...                   the exact receipts, board files and fault snapshot
  ohmni-demo-fabrication.zip      the saved Gerber/drill package for download
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ohmni.application.hackathon_demo import (
    FAULT_DIRECTORY,
    FAULT_EXPLANATION,
    FAULT_PCB,
    FAULT_RAW_DRC,
    FAULT_RESULT,
    REQUIRED_OUTPUTS,
    qualify_run,
    sha256_file,
    snapshot_copper,
)
from ohmni.application.reference_preview import build_reference_preview

SAVED_FILES = (*REQUIRED_OUTPUTS, "confirmed-brief.json", "circuit.json")
ZIP_NAME = "ohmni-demo-fabrication.zip"
MANIFEST = "fabrication/ohmni-fabrication-manifest.json"
ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _key(value: dict) -> str:
    return json.dumps(value, sort_keys=True)


def _copper(board: dict) -> dict:
    return {"tracks": sorted(board["tracks"], key=_key), "vias": sorted(board["vias"], key=_key)}


def _strip(copper: dict) -> dict:
    tracks = [{key: value for key, value in track.items() if key != "uuid"} for track in copper["tracks"]]
    return {"tracks": sorted(tracks, key=_key), "vias": sorted(copper["vias"], key=_key)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "examples" / "hackathon-demo")
    parser.add_argument("--captured-on", type=date.fromisoformat, required=True)
    args = parser.parse_args(argv)
    run = args.run_dir.resolve()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    # The summary must be this run's own: the attempt directory sits next to the
    # summary, and every output hash it recorded matches the bytes captured now.
    attempt = next((item for item in summary["attempts"]
                    if args.summary.resolve().parent / Path(item["directory"]).name == run), None)
    if summary.get("status") != "PASS" or attempt is None or attempt["status"] != "PASS":
        parser.exit(1, "The run is not a passing attempt of a passing harness summary.\n")
    recorded = attempt.get("output_sha256") or {}
    if not recorded or any(not (run / name).is_file() or sha256_file(run / name) != digest
                           for name, digest in recorded.items()):
        parser.exit(1, "The run's files do not match the hashes its summary recorded.\n")
    manifest = json.loads((run / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("package_fingerprint") != attempt["release"]["package_fingerprint"]:
        parser.exit(1, "The fabrication package is not the one the summary released.\n")
    # Only the files the verified manifest lists (and the manifest itself) are
    # saved or offered for download; anything else in the folder is refused.
    listed = {item["relative_path"]: item["sha256"] for item in manifest["files"]}
    present = {path.name for path in (run / "fabrication").iterdir() if path.is_file()}
    if present != set(listed) | {Path(MANIFEST).name} or any(
            sha256_file(run / "fabrication" / name) != digest for name, digest in listed.items()):
        parser.exit(1, "The fabrication folder does not match its manifest.\n")

    qualification = qualify_run(run)
    if not qualification.passed:
        parser.exit(1, "The saved run no longer qualifies from its own receipts.\n")
    fault = json.loads((run / FAULT_DIRECTORY / FAULT_RESULT).read_text(encoding="utf-8"))
    snapshot_path = run / FAULT_DIRECTORY / FAULT_PCB
    if not (fault.get("fault_detected") is True and fault.get("releasable") is False
            and sha256_file(snapshot_path) == fault["snapshot_sha256"]
            and sha256_file(run / FAULT_DIRECTORY / FAULT_RAW_DRC) == fault["raw_drc_sha256"]):
        parser.exit(1, "The fault diagnostic is missing, undetected or no longer matches its receipt.\n")

    good = build_reference_preview(run, captured_on=args.captured_on, label="ESP32 button and LED board")
    good_text = (run / "golden.kicad_pcb").read_text(encoding="utf-8")
    snapshot_text = snapshot_path.read_text(encoding="utf-8")
    if good["board"]["artifact_fingerprint"] != fault["source_pcb_sha256"]:
        parser.exit(1, "The fault was not derived from the re-verified good board.\n")
    # The snapshot must be the good board with exactly one line removed, so every
    # pad and footprint is byte-identical; only the copper is re-derived from it.
    good_lines, fault_lines = good_text.split("\n"), snapshot_text.split("\n")
    index = fault["removed_segment"]["line_number"] - 1
    if good_lines[:index] + good_lines[index + 1:] != fault_lines:
        parser.exit(1, "The snapshot differs from the good board by more than the one removed track.\n")
    if _strip(snapshot_copper(good_text)) != _copper(good["board"]):
        parser.exit(1, "The good board's displayed copper does not match its own PCB bytes.\n")
    fault_board = copy.deepcopy(good["board"])
    fault_copper = _strip(snapshot_copper(snapshot_text))
    fault_board.update(fault_copper, artifact_fingerprint=fault["snapshot_sha256"])
    # The damaged copy has no routing plan or constraint receipt of its own.
    for field in ("routing_plan_fingerprint", "constraints_hash"):
        fault_board.pop(field, None)

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    saved = output / "saved-run"
    for name in (*SAVED_FILES, *(f"fabrication/{path.name}" for path in sorted((run / "fabrication").iterdir()) if path.is_file()),
                 f"{FAULT_DIRECTORY}/{FAULT_PCB}", f"{FAULT_DIRECTORY}/{FAULT_RAW_DRC}",
                 f"{FAULT_DIRECTORY}/{FAULT_RESULT}"):
        target = saved / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run / name, target)
    with zipfile.ZipFile(output / ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(path for path in (run / "fabrication").iterdir() if path.is_file()):
            info = zipfile.ZipInfo(f"fabrication/{path.name}", ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())

    demo = {
        "schema_version": 1,
        "kind": "saved_hackathon_demonstration",
        "label": "Saved successful run",
        "notice": (f"This is a saved run captured on {args.captured_on.isoformat()}. Nothing on "
                   "this page is generated or checked live; every result is a recorded receipt."),
        "capture": {
            "captured_on": args.captured_on.isoformat(),
            "harness_run_id": summary["run_id"],
            "harness_status": summary["status"],
            "attempts_qualified": f"{sum(item['status'] == 'PASS' for item in summary['attempts'])}/"
                                  f"{summary['attempts_requested']}",
            "git_commit": summary["git"]["commit"],
            "kicad_cli": summary["tools"]["kicad_cli"],
            "brief_fingerprint": summary["brief"]["fingerprint"],
            "attempt_seconds": attempt["total_seconds"],
            "checks": attempt["checks"],
            "warnings": attempt["warnings"],
        },
        "download": {"href": ZIP_NAME, "sha256": hashlib.sha256((output / ZIP_NAME).read_bytes()).hexdigest(),
                     "package_fingerprint": attempt["release"]["package_fingerprint"],
                     "board": "original only; the damaged copy is never releasable"},
        "good": good,
        "fault": {
            "fault_id": fault["fault_id"],
            "kind": fault["kind"],
            "releasable": False,
            "source_pcb_sha256": fault["source_pcb_sha256"],
            "snapshot_sha256": fault["snapshot_sha256"],
            "raw_drc_sha256": fault["raw_drc_sha256"],
            "removed_segment": fault["removed_segment"],
            "checker": fault["checker"],
            "drc": fault["drc"],
            "not_checked": fault["not_checked"],
            "board": fault_board,
            "explanation": list(FAULT_EXPLANATION),
        },
    }
    (output / "demo.json").write_text(json.dumps(demo, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Saved demonstration written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
