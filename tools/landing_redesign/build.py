"""Author a separately identified landing board; never publish it as the saved demo.

Run from the repository with its src on PYTHONPATH. The default semantic verifier
does not support this buck/translator topology; its results remain in the bundle.
Scoped topology checks and native ERC/DRC are independent records, not substitutes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path

from ohmni.adapters.tools import find_kicad_cli
from ohmni.application.product import _board_geometry
from ohmni.application.systems import build_systems, group_components
from ohmni.eda.kicad.erc import KiCadCliAdapter
from ohmni.eda.kicad.pcb_compiler import KiCadPcbCompiler
from ohmni.physical.footprints import footprint_geometry_fingerprint
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.verifier import verify_routing
from ohmni.verifier.engine import verify

ROOT = Path(__file__).resolve().parents[2]
AUTHORED_ROLES = {
    "R6": "Upper feedback resistor",
    "R7": "Lower feedback resistor",
    "R14": "I2C reference-bias resistor",
    "C8": "I2C reference-bias filter",
    "L1": "Buck output inductor",
    "U2": "Switching regulator",
    "U4": "I2C voltage translator",
    "J3": "5 V I2C expansion header",
}


def write_json(path: Path, value) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def _tool_version(executable: str | None, *args: str) -> dict:
    if not executable:
        return {"status": "UNAVAILABLE"}
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True,
                                timeout=20, check=False)
        return {"status": "OK" if result.returncode == 0 else "FAILED",
                "executable": executable, "return_code": result.returncode,
                "output": (result.stdout + result.stderr).strip()}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "FAILED", "executable": executable, "error": str(exc)}


def generate(output: Path, *, include_i2c_extension: bool, captured_on: str, route_seconds: float = 240,
             native: bool = True) -> dict:
    from .checks import check_design
    from .design import build_design
    from .native_rules import verify_native_rules, write_native_rules
    from .physical import (
        audit_switching_routes,
        build_board_constraints,
        footprint_manifest,
        routing_constraints,
        scoped_footprints,
    )
    from .schematic import build_schematic

    output = output.resolve()
    date.fromisoformat(captured_on)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory; prior evidence must not be overwritten")
    output.mkdir(parents=True, exist_ok=True)
    reference = ROOT / "apps/web/reference-board.json"
    original_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    original_registry = footprint_geometry_fingerprint()
    design = build_design(include_i2c_extension=include_i2c_extension)
    circuit, catalog = design.circuit, design.catalog
    write_json(output / "circuit.json", circuit)
    write_json(output / "requirements.json", design.requirements)
    for part in catalog.all_parts():
        write_json(output / "catalog" / (part.part_id + ".json"), part)
    scoped = check_design(circuit, catalog, include_i2c_extension=include_i2c_extension)
    write_json(output / "topology-checks.json", scoped)
    semantic = verify(circuit, catalog, design.requirements)
    write_json(output / "semantic-checks.json", semantic)
    executable = find_kicad_cli()
    report = {"schema_version": 1, "kind": "landing_circuit_candidate",
              "status": "DRAFT_ENGINEERING_REVIEW_REQUIRED",
              "circuit_hash": circuit.content_hash,
              "i2c_extension": include_i2c_extension,
              "original_reference_sha256": original_hash,
              "production_reference_replaced": False,
              "checks": {"topology": scoped, "semantic": {
                  "export_blocked": semantic.export_blocked,
                  "coverage": semantic.coverage,
                  "blocking_findings": [{"rule_id": f.rule_id, "severity": f.severity.value,
                                         "title": f.title} for f in semantic.blocking_findings],
                  "undecided_rules": [r.rule_id for r in semantic.undecided_rules],
                  "note": "Default voltage derivation lacks this buck/translator topology. Full results also record identity and assembly limitations."},
                  "simulation": "NOT_RUN", "bench": "NOT_RUN"},
              "tools": {"kicad": _tool_version(executable, "version")},
              "limitations": [
                  "A candidate design, not a manufacturing release or hardware-tested board.",
                  "Scoped topology arithmetic does not establish startup, stability, EMI or temperature.",
                  "USB input-current entitlement and complete worst-case load budget require review.",
                  "Exact model-to-footprint physical fits remain separate from board DRC.",
                  "ESP32-WROOM-32 footprint versus the 32E module remains an unresolved manufacturing fit, including the thermal pad and antenna geometry.",
                  "The inherited hand-solderable requirement conflicts with the BME280 LGA package; assembly method needs resolution.",
              ]}
    try:
        if scoped["failed_checks"]:
            report["status"] = "TOPOLOGY_CHECKS_FAILED"
            return report
        with scoped_footprints():
            write_json(output / "footprint-manifest.json", footprint_manifest())
            board = build_board_constraints(circuit)
            write_json(output / "board-constraints.json", board)
            schematic = build_schematic(design, output / "redesign.kicad_sch", scoped)
            write_json(output / "schematic-artifact.json", schematic)
            compiler = KiCadPcbCompiler(catalog)
            placed = compiler.compile(circuit, schematic, board, output / "redesign-placed.kicad_pcb")
            write_json(output / "placed-artifact.json", placed)
            physical = placed.compilation.physical_verification
            report["checks"]["physical"] = physical.model_dump(mode="json")
            report["checks"]["physical"]["passed"] = physical.passed
            if native:
                erc = KiCadCliAdapter(executable).run_erc(schematic, output / "erc.json")
                write_json(output / "erc-report.json", erc)
                report["checks"]["erc"] = {"status": erc.status.value,
                    "tool_status": erc.tool_status.value, "finding_count": len(erc.findings)}
            if not physical.passed:
                report["status"] = "PLACEMENT_CHECKS_FAILED"
                return report
            print(f"Routing {len(circuit.components)} parts / {len(circuit.nets)} nets", flush=True)
            plan = DeterministicRouter().route(circuit, placed, board, routing_constraints(circuit),
                                               time_budget_seconds=route_seconds)
            write_json(output / "routing-plan.json", plan)
            routing = verify_routing(circuit, placed, board, plan)
            write_json(output / "routing-verification.json", routing)
            report["checks"]["routing"] = {"passed": routing.passed,
                                            "failures": len(plan.failures)}
            route_audit = audit_switching_routes(circuit, board, plan)
            write_json(output / "switching-layout-checks.json", route_audit)
            report["checks"]["switching_layout"] = route_audit
            if not routing.passed or plan.failures:
                report["status"] = "ROUTING_INCOMPLETE"
                return report
            if route_audit["status"] != "PASS":
                report["status"] = "SWITCHING_LAYOUT_CHECKS_FAILED"
                return report
            routed = compiler.compile(circuit, schematic, board, output / "redesign.kicad_pcb", plan)
            write_json(output / "routed-artifact.json", routed)
            report["artifact_fingerprint"] = routed.fingerprint.digest
            report["routing_plan_fingerprint"] = plan.content_hash
            if native:
                native_rules = write_native_rules(routed.path, routing_constraints(circuit),
                    circuit_hash=circuit.content_hash, routing_plan_hash=plan.content_hash)
                write_json(output / "native-rules-manifest.json", native_rules)
                report["native_rules"] = native_rules
                verify_native_rules(native_rules)
                drc = KiCadCliAdapter(executable).run_drc(routed, output / "drc.json")
                verify_native_rules(native_rules)
                write_json(output / "drc-report.json", drc)
                report["checks"]["drc"] = {"status": drc.status.value,
                    "tool_status": drc.tool_status.value, "finding_count": len(drc.findings),
                    "unconnected_count": len(drc.unconnected_items)}
            placements = {p.component_ref: (p.x_mm, p.y_mm) for p in board.placements}
            grouping = group_components(circuit, catalog, placements)
            geometry = _board_geometry(board, routed, {g.component_ref: g for g in grouping},
                                       circuit, catalog)
            components = []
            for part in geometry.components:
                if part.ref in AUTHORED_ROLES:
                    part.name = part.name.model_copy(update={"human": AUTHORED_ROLES[part.ref]})
                instance = circuit.component(part.ref)
                spec = catalog.require(instance.part_id)
                components.append({"ref": part.ref, "name": part.name.model_dump(mode="json"),
                    "part_id": part.part_id, "system": part.system.value,
                    "category": spec.category.value, "purpose": instance.notes or spec.description,
                    "value": instance.value.model_dump(mode="json") if instance.value else None})
            scene = {"schema_version": 1, "source": {"kind": "landing_circuit_candidate",
                     "captured_on": captured_on,
                     "artifact_fingerprint": routed.fingerprint.digest,
                     "routing_plan_fingerprint": plan.content_hash,
                     "circuit_hash": circuit.content_hash,
                     "footprint_registry_fingerprint": footprint_geometry_fingerprint(),
                     "status": report["status"]},
                     "board": geometry.model_dump(mode="json"), "components": components,
                     "systems": [s.model_dump(mode="json") for s in build_systems(grouping)],
                     "checks": report["checks"], "limitations": report["limitations"]}
            write_json(output / "candidate-board.json", scene)
            report["scene"] = "candidate-board.json"
            report["counts"] = {"components": len(geometry.components), "nets": len(circuit.nets),
                                "tracks": len(geometry.tracks), "vias": len(geometry.vias)}
            return report
    except Exception as exc:
        report["status"] = "GENERATION_FAILED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        assert hashlib.sha256(reference.read_bytes()).hexdigest() == original_hash
        assert footprint_geometry_fingerprint() == original_registry
        report["original_reference_unchanged"] = True
        report["default_footprint_registry_restored"] = True
        write_json(output / "report.json", report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--captured-on", required=True, help="Explicit ISO capture date")
    parser.add_argument("--i2c-extension", action="store_true")
    parser.add_argument("--route-seconds", type=float, default=240)
    parser.add_argument("--skip-native", action="store_true")
    args = parser.parse_args()
    report = generate(args.output, include_i2c_extension=args.i2c_extension,
                      captured_on=args.captured_on,
                      route_seconds=args.route_seconds, native=not args.skip_native)
    print(json.dumps({"status": report["status"], "counts": report.get("counts"),
                      "checks": report["checks"]}, indent=2))


if __name__ == "__main__":
    main()
