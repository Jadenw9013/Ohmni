#!/usr/bin/env python3
"""Run the CS-T04 component CAD proof end to end and write its evidence.

Pipeline, in the order the trust boundary requires:

  pinned PDF -> bounded observations -> recorded multimodal proposal
             -> independent deterministic source verification
             -> deterministic land pattern and symbol
             -> emitted .kicad_mod / .kicad_sym bytes
             -> independent byte-level measurement
             -> CS-* asset checks
             -> KiCad CLI corroboration

No catalog admission happens here: CS-T07 owns that gate.

Usage::

    python scripts/acquire_corpus.py
    python scripts/component_cad_proof.py [--out build/component_synthesis]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ohmni.adapters import ToolStatus
from ohmni.adapters.vision import RecordedVisionProvider
from ohmni.datasheet.constraint_verifier import verify_extraction
from ohmni.datasheet.isolated_observations import IsolatedObservationExtractor
from ohmni.datasheet.multimodal import MultimodalCandidateExtractor
from ohmni.eda.kicad.component_asset_parser import (
    measure_footprint,
    measure_symbol_library,
)
from ohmni.eda.kicad.component_assets import (
    FOOTPRINT_FORMAT_VERSION,
    GENERATOR_VERSION,
    SYMBOL_LIB_FORMAT_VERSION,
    render_footprint,
    render_symbol_library,
    write_asset,
)
from ohmni.eda.kicad.component_harness import (
    build_harness_pcb,
    build_harness_schematic,
    export_footprint_svg,
    export_symbol_svg,
    run_harness_drc,
    run_harness_erc,
)
from ohmni.physical.component_asset_verifier import verify_assets
from ohmni.physical.land_patterns import (
    POLICY_VERSION,
    REQUIRED_LAND_DIMENSIONS,
    build_land_pattern,
    build_symbol,
    cad_capabilities,
)

DOCUMENT_ID = "MCP73831-DS20001984H"
PAGES = [11, 24, 26]
PACKAGE_COLUMN = "SOT-23-5"


def _replayed_reason(provider) -> str | None:
    for payload in provider.recordings.values():
        if payload.get("fidelity") == provider.replayed_fidelity:
            return payload.get("fidelity_reason")
    return None


def _extraction_fidelity_caveat(provider) -> str:
    """Say plainly what the replayed proposal is, in the durable record."""
    if provider.replayed_fidelity == "recorded":
        return (
            "Extraction fidelity beyond this one witnessed response: one document is "
            "not a measured error rate"
        )
    return (
        f"Extraction fidelity: the replayed proposal is '{provider.replayed_fidelity}', "
        "not a witnessed provider response, so how well extraction performs against a "
        "live provider is UNEVALUATED"
    )


def run(out_dir: Path) -> int:
    manifest = json.loads((ROOT / "tests/corpus/manifest.json").read_text(encoding="utf-8"))
    pdf = ROOT / manifest["workspace"] / f"{DOCUMENT_ID}.pdf"
    if not pdf.is_file():
        print(f"ABSENT: {pdf.relative_to(ROOT)} -- run scripts/acquire_corpus.py first")
        return 2

    # The manufacturer PDF is untrusted input, so the evidence run reads it the
    # way production should: in a bounded child that caps its own address space
    # before the parser exists in it. The bundle is byte-identical to the
    # in-process one -- the observation digest below is what proves that.
    extractor = IsolatedObservationExtractor()
    bundle, images = extractor.observe(pdf, PAGES, render=True)
    run = extractor.last_run
    print(f"observation worker: {run.memory_mechanism} cap="
          f"{run.address_space_bytes // (1024 * 1024)}MiB timeout={run.timeout_seconds:g}s")
    provider = RecordedVisionProvider(directory=ROOT / "tests/corpus/recordings")
    proposal = MultimodalCandidateExtractor(provider).extract(
        bundle, images, requested_package=PACKAGE_COLUMN
    )
    report = verify_extraction(
        bundle, proposal,
        required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
    )
    print(f"source receipts: {len(report.receipts)}, "
          f"unsupported: {len(report.unsupported())}, missing: {list(report.missing)}")
    if report.verified is None:
        print("QUARANTINED: source verification did not admit a constraint set")
        return 1
    verified = report.verified

    land_pattern = build_land_pattern(verified)
    symbol_definition = build_symbol(verified)
    pretty = out_dir / "Ohmni_ComponentSynthesis.pretty"
    footprint_path = pretty / f"{land_pattern.name}.kicad_mod"
    symbol_path = out_dir / f"{symbol_definition.name}.kicad_sym"
    footprint_digest = write_asset(render_footprint(land_pattern), footprint_path)
    symbol_digest = write_asset(render_symbol_library(symbol_definition), symbol_path)

    measured_footprint = measure_footprint(footprint_path.read_text(encoding="utf-8"))
    measured_symbol = measure_symbol_library(symbol_path.read_text(encoding="utf-8"))
    assets = verify_assets(
        verified, measured_footprint, measured_symbol,
        land_pattern=land_pattern, symbol_definition=symbol_definition,
        footprint_digest=footprint_digest, symbol_digest=symbol_digest,
        recorded_footprint_digest=footprint_digest, recorded_symbol_digest=symbol_digest,
    )
    for finding in assets.findings:
        mark = "OK  " if finding.ok else "FAIL"
        print(f"{mark} {finding.check_id:<20} {finding.description}")
        if not finding.ok:
            print(f"       measured={finding.measured} expected={finding.expected}")

    # Each proof run renders into a destination it owns and has just emptied.
    # The harness refuses a directory that already holds an SVG, because an
    # older render cannot corroborate this run.
    renders = out_dir / "renders"
    if renders.exists():
        shutil.rmtree(renders)
    footprint_run = export_footprint_svg(pretty, land_pattern.name, renders / "footprint")
    symbol_run = export_symbol_svg(symbol_path, symbol_definition.name, renders / "symbol")
    for run_result in (footprint_run, symbol_run):
        print(f"{run_result.name}: {run_result.status.value} "
              f"({run_result.tool_version or 'version unknown'}) {run_result.detail or ''}")

    # The plan's CS-KICAD criterion asks for the assets in a design, not only in
    # a library: a symbol that plots can still fail ERC, and a footprint that
    # plots can still be malformed to DRC.
    harness_dir = out_dir / "harness"
    if harness_dir.exists():
        shutil.rmtree(harness_dir)
    harness_dir.mkdir(parents=True)
    build_harness_schematic(
        render_symbol_library(symbol_definition), symbol_definition.name,
        [(pin.number, pin.x_nm, pin.y_nm) for pin in symbol_definition.pins],
        harness_dir / "harness.kicad_sch",
    )
    build_harness_pcb(
        render_footprint(land_pattern), land_pattern.name, harness_dir / "harness.kicad_pcb"
    )
    erc_run = run_harness_erc(harness_dir / "harness.kicad_sch", symbol_digest)
    drc_run = run_harness_drc(harness_dir / "harness.kicad_pcb", footprint_digest)
    for design_run in (erc_run, drc_run):
        print(f"{design_run.name}: {design_run.status.value} "
              f"corroborated={design_run.corroborated} "
              f"violations={dict(design_run.violation_counts) or 'none'} "
              f"asset_defects={list(design_run.asset_defects) or 'none'}")

    capabilities = cad_capabilities(
        verified, land_pattern_built=True, symbol_built=True,
    )
    evidence = {
        "schema_version": 1,
        "task": "CS-T04",
        "document": {
            "document_id": DOCUMENT_ID,
            "sha256": bundle.document_digest,
            "observed_pages": PAGES,
            "observation_digest": bundle.observation_digest,
            "parser": f"{bundle.parser} {bundle.parser_version}",
            "renderer": f"{bundle.renderer} {bundle.renderer_version}",
        },
        # The proposal's provenance travels with the evidence. Without it a
        # reader cannot tell whether the extraction that produced these
        # constraints was a witnessed provider response or an offline fixture.
        "proposal_provenance": {
            "fidelity": provider.replayed_fidelity,
            "fidelity_reason": _replayed_reason(provider),
        },
        "identity": verified.identity.model_dump(mode="json"),
        "verified_constraint_hash": verified.content_hash,
        "source_receipts": [receipt.model_dump(mode="json") for receipt in report.receipts],
        "land_pattern": {
            "name": land_pattern.name,
            "method": land_pattern.method.value,
            "policy_version": POLICY_VERSION,
            "content_hash": land_pattern.content_hash,
            "pads_nm": [
                {"number": pad.number, "x": pad.centre_x_nm, "y": pad.centre_y_nm,
                 "w": pad.width_nm, "h": pad.height_nm}
                for pad in land_pattern.pads
            ],
            "limitations": list(land_pattern.limitations),
        },
        "symbol": {
            "name": symbol_definition.name,
            "content_hash": symbol_definition.content_hash,
            "limitations": list(symbol_definition.limitations),
        },
        "artifacts": {
            "footprint": {"path": str(footprint_path.relative_to(ROOT)),
                          "sha256": footprint_digest,
                          "format_version": FOOTPRINT_FORMAT_VERSION},
            "symbol": {"path": str(symbol_path.relative_to(ROOT)),
                       "sha256": symbol_digest,
                       "format_version": SYMBOL_LIB_FORMAT_VERSION},
            "generator_version": GENERATOR_VERSION,
        },
        "asset_checks": {
            "checker_version": assets.checker_version,
            "passed": assets.passed,
            "findings": [
                {"check_id": item.check_id, "status": item.status.value,
                 "description": item.description, "measured": item.measured,
                 "expected": item.expected}
                for item in assets.findings
            ],
            "limitations": list(assets.limitations),
        },
        "native_tool_runs": [
            {"name": item.name, "status": item.status.value,
             "artifact_sha256": item.artifact_sha256, "tool_version": item.tool_version,
             "outputs": [str(Path(path).relative_to(ROOT)) for path in item.outputs],
             "output_sha256": list(item.output_sha256), "detail": item.detail}
            for item in (footprint_run, symbol_run)
        ],
        "connected_design_runs": [
            {"name": item.name, "status": item.status.value,
             "design_sha256": item.design_sha256, "asset_sha256": item.asset_sha256,
             "tool_version": item.tool_version,
             "report_sha256": item.report_sha256,
             "violations": dict(item.violation_counts),
             "asset_defects": list(item.asset_defects),
             "corroborated": item.corroborated, "detail": item.detail}
            for item in (erc_run, drc_run)
        ],
        "connected_design_note": (
            "One component, labelled pins, a rectangular outline. This establishes that "
            "KiCad loaded the generated assets in a design and reported no asset-defect "
            "violation. It does not establish that any design works. Remaining violations "
            "are recorded above, including the isolated-pin labels a one-component harness "
            "necessarily produces."
        ),
        "capabilities": capabilities.model_dump(mode="json"),
        "not_established": [
            "IPC-7351 or IPC-7352 compliance",
            "Solder joint reliability, paste volume, stencil design, thermal performance",
            "Any electrical behaviour, operating limit or absolute maximum rating",
            "Any SPICE model or simulated behaviour",
            "Catalog admission or design eligibility: CS-T07 owns that gate and has not run",
            _extraction_fidelity_caveat(provider),
        ],
    }
    evidence_path = out_dir / "CS-T04_evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"evidence: {evidence_path.relative_to(ROOT)}")

    corroborated = (
        all(item.status is ToolStatus.OK for item in (footprint_run, symbol_run))
        and erc_run.corroborated and drc_run.corroborated
    )
    if not assets.passed:
        print("RESULT: asset checks FAILED")
        return 1
    if not corroborated:
        print("RESULT: asset checks passed; KiCad corroboration did NOT run or failed")
        return 1
    print("RESULT: asset checks passed; KiCad rendered both artifacts and reported no "
          "asset-defect violation with them in a design")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="build/component_synthesis")
    args = parser.parse_args(argv)
    return run((ROOT / args.out).resolve())


if __name__ == "__main__":
    sys.exit(main())
