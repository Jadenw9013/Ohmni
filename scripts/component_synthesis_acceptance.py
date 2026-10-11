#!/usr/bin/env python3
"""Build the bounded CS-T11 acceptance report from exact local evidence."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ohmni.catalog.lm317 import lm317_asset_record, lm317_record
from ohmni.eda.kicad.reusable_asset_library import (
    ImmutableAssetResolver,
    compile_asset,
    export_portable_library,
)

CASE_MANIFEST = ROOT / "tests/corpus/component_synthesis_acceptance.json"
CORPUS_MANIFEST = ROOT / "tests/corpus/manifest.json"
PRIOR_STAGES = tuple(f"CS-T{number:02d}" for number in range(1, 11))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selector_exists(selector: str) -> bool:
    parts = selector.split("::")
    if len(parts) not in {2, 3}:
        return False
    path = ROOT / parts[0]
    if not path.is_file():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if len(parts) == 2:
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == parts[1]
            for node in tree.body
        )
    owner = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == parts[1]),
        None,
    )
    return owner is not None and any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == parts[2]
        for node in owner.body
    )


def _prior_verification() -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    errors: list[str] = []
    for task in PRIOR_STAGES:
        path = ROOT / f".ai/verification/{task}.yaml"
        if not path.is_file():
            errors.append(f"missing verification record {path.relative_to(ROOT)}")
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        status = value.get("status")
        if not isinstance(status, str) or not status.startswith("PASSED"):
            errors.append(f"{task} verification is {status!r}, not a recorded pass boundary")
        records.append({
            "task": task,
            "status": status,
            "record_sha256": _sha256(path),
            "commit": value.get("commit"),
        })
    return records, errors


def _source_evidence() -> tuple[dict, list[str]]:
    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    documents: list[dict] = []
    for entry in manifest["documents"]:
        path = ROOT / manifest["workspace"] / f"{entry['id']}.pdf"
        actual = _sha256(path) if path.is_file() else None
        if actual != entry["sha256"]:
            errors.append(f"{entry['id']} source bytes are absent or do not match the pinned digest")
        documents.append({
            "id": entry["id"],
            "origin": entry["acquisition_url"],
            "expected_sha256": entry["sha256"],
            "actual_sha256": actual,
            "bytes": path.stat().st_size if path.is_file() else None,
            "license_note": entry["license_note"],
        })
    ti = lm317_record()
    documents.append({
        "id": "TI-LM317-SLVS044Z",
        "origin": ti["source"]["url"],
        "expected_sha256": ti["source"]["sha256"],
        "actual_sha256": None,
        "bytes": None,
        "license_note": (
            "Digest-bound CS-T10 source record; datasheet bytes are not redistributed and "
            "this CS-T11 run does not relabel the recorded digest as a fresh byte check."
        ),
    })
    return {"documents": documents}, errors


def _cad_evidence(path: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    if not path.is_file():
        return {"path": str(path)}, ["real CAD evidence file is absent"]
    value = json.loads(path.read_text(encoding="utf-8"))
    if not value.get("asset_checks", {}).get("passed"):
        errors.append("CAD asset checks did not pass")
    native = value.get("native_tool_runs", [])
    connected = value.get("connected_design_runs", [])
    if not native or any(item.get("status") != "ok" for item in native):
        errors.append("one or more KiCad render runs did not complete")
    if not connected or any(not item.get("corroborated") for item in connected):
        errors.append("one or more connected KiCad harness runs were not corroborated")
    outputs: list[dict] = []
    for item in native:
        for relative, expected in zip(item.get("outputs", []), item.get("output_sha256", []), strict=True):
            artifact = ROOT / relative
            actual = _sha256(artifact) if artifact.is_file() else None
            if actual != expected:
                errors.append(f"render output {relative} is absent or hash-mismatched")
            outputs.append({"path": relative, "expected_sha256": expected, "actual_sha256": actual})
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": _sha256(path),
        "document_sha256": value.get("document", {}).get("sha256"),
        "constraint_hash": value.get("verified_constraint_hash"),
        "native_tool_runs": native,
        "connected_design_runs": connected,
        "user_visible_outputs": outputs,
    }, errors


def _portable_evidence(destination: Path) -> tuple[dict, list[str]]:
    compiled = compile_asset(lm317_asset_record())
    resolver = ImmutableAssetResolver((compiled,))
    manifest_path = export_portable_library(
        resolver, ((compiled.asset_id, compiled.record_hash),), destination
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Recreate the resolver as a restart boundary; no in-memory resolved object is reused.
    restarted = ImmutableAssetResolver((compile_asset(lm317_asset_record()),)).resolve(
        compiled.asset_id, record_hash=compiled.record_hash
    )
    errors: list[str] = []
    footprint_path = destination / "OhmniGenerated.pretty" / f"{compiled.asset_id}.kicad_mod"
    symbol_path = destination / "symbols" / f"{compiled.asset_id}.kicad_sym"
    checks = {
        "footprint": (_sha256(footprint_path), compiled.footprint_sha256),
        "symbol": (_sha256(symbol_path), compiled.symbol_sha256),
        "restart_footprint": (
            hashlib.sha256(restarted.footprint_bytes).hexdigest(), compiled.footprint_sha256
        ),
        "restart_symbol": (
            hashlib.sha256(restarted.symbol_bytes).hexdigest(), compiled.symbol_sha256
        ),
    }
    for name, (actual, expected) in checks.items():
        if actual != expected:
            errors.append(f"portable {name} hash differs from the compiled immutable asset")
    return {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": _sha256(manifest_path),
        "assets": manifest["assets"],
        "hash_checks": {
            name: {"actual": actual, "expected": expected, "passed": actual == expected}
            for name, (actual, expected) in checks.items()
        },
        "restart_reconstructed": not errors,
    }, errors


def run(cad_evidence_path: Path, out_dir: Path) -> int:
    cases = json.loads(CASE_MANIFEST.read_text(encoding="utf-8"))
    selectors = [
        selector
        for group in cases["positive_evidence"]
        for selector in group["selectors"]
    ] + cases["negative_corpus"]
    selector_results = {selector: _selector_exists(selector) for selector in selectors}
    errors = [selector for selector, present in selector_results.items() if not present]
    errors = [f"acceptance selector is absent: {selector}" for selector in errors]

    prior, prior_errors = _prior_verification()
    source, source_errors = _source_evidence()
    cad, cad_errors = _cad_evidence(cad_evidence_path)
    portable, portable_errors = _portable_evidence(out_dir / "portable")
    errors.extend((*prior_errors, *source_errors, *cad_errors, *portable_errors))
    report = {
        "schema_version": 1,
        "task": "CS-T11",
        "scope": cases["scope"],
        "status": "PASS" if not errors else "FAIL",
        "case_manifest_sha256": _sha256(CASE_MANIFEST),
        "defined_negative_cases": len(cases["negative_corpus"]),
        "selector_presence": selector_results,
        "prior_stage_verification": prior,
        "source_evidence": source,
        "cad_and_ui_evidence": cad,
        "portable_and_restart_evidence": portable,
        "limitations": cases["limitations"],
        "errors": errors,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "acceptance-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{report['status']}: {report_path.relative_to(ROOT)}")
    for error in errors:
        print(f"ERROR: {error}")
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cad-evidence", required=True)
    parser.add_argument("--out", default="build/component-synthesis/acceptance")
    args = parser.parse_args(argv)
    return run((ROOT / args.cad_evidence).resolve(), (ROOT / args.out).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
