"""Author a separately identified landing board; never publish it as the saved demo.

Run from the repository with its src on PYTHONPATH. Generic semantic verification and scoped controller checks remain separate
records; their coverage limits remain in the bundle.
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
from ohmni.physical.footprints import footprint_geometry_fingerprint
from ohmni.routing.models import RoutingPlan
from ohmni.routing.verifier import verify_routing
from ohmni.verifier.engine import verify

ROOT = Path(__file__).resolve().parents[2]



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


def generate(output: Path, *, captured_on: str, route_seconds: float = 240,
             native: bool = True, routing_plan_path: Path | None = None) -> dict:
    from tools.landing_redesign.native_rules import verify_native_rules, write_native_rules

    from .checks import check_design
    from .design import build_design
    from .physical import (
        MOUNTING_HOLES,
        ControllerPcbCompiler,
        build_board_constraints,
        footprint_manifest,
        routing_constraints,
        scoped_footprints,
    )
    from .routing import structured_route
    from .schematic import ControllerSchematicCompiler

    output = output.resolve()
    date.fromisoformat(captured_on)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use an empty output directory; prior evidence must not be overwritten")
    output.mkdir(parents=True, exist_ok=True)
    reference = ROOT / "apps/web/reference-board.json"
    original_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    original_registry = footprint_geometry_fingerprint()
    design = build_design()
    circuit, catalog = design.circuit, design.catalog
    write_json(output / "circuit.json", circuit)
    write_json(output / "requirements.json", design.requirements)
    for part in catalog.all_parts():
        write_json(output / "catalog" / (part.part_id + ".json"), part)
    scoped = check_design(circuit, catalog)
    write_json(output / "topology-checks.json", scoped)
    semantic = verify(circuit, catalog, design.requirements)
    write_json(output / "semantic-checks.json", semantic)
    executable = find_kicad_cli()
    report = {"schema_version": 1, "kind": "landing_circuit_candidate",
              "status": "DRAFT_ENGINEERING_REVIEW_REQUIRED",
              "circuit_hash": circuit.content_hash,
              "original_reference_sha256": original_hash,
              "production_reference_replaced": False,
              "checks": {"topology": scoped, "semantic": {
                  "export_blocked": semantic.export_blocked,
                  "coverage": semantic.coverage,
                  "coverage_scope": "Generic rule coverage only; not a measure of whole-system electrical verification.",
                  "blocking_findings": [{"rule_id": f.rule_id, "severity": f.severity.value,
                                         "title": f.title} for f in semantic.blocking_findings],
                  "undecided_rules": [r.rule_id for r in semantic.undecided_rules],
                  "note": "Scoped topology is distinct from complete electrical and physical verification. See the retained semantic findings."},
                  "simulation": "NOT_RUN", "bench": "NOT_RUN"},
              "tools": {"kicad": _tool_version(executable, "version")},
              "limitations": [
                  "Source-backed authored controller concept; not a manufacturing release or hardware-tested board.",
                  "No firmware, SPICE, hardware, EMC or thermal validation has been performed.",
                  "USB-C is a power-only input; cable/source current entitlement and complete worst-case budget need review.",
                  "GPIO expansion is 3.3 V logic; external loads, protection and connector wiring need engineering review.",
                  "Exact manufacturer evidence is catalog-reported, not machine-relocated verified evidence.",
                  "The retained generic LED rule uses typical 2.2 V forward voltage as a fallback, not a guaranteed minimum. Its current estimate is not a worst-case bound. The separate scoped calculation is conditional on a rail at or below 3.6 V and 1% 1 kohm resistors; output drive and brightness remain unknown.",
                  "Rendering uses real package geometry with explicit source bindings and recorded cosmetic approximations.",
              ]}
    try:
        if scoped["failed_checks"]:
            report["status"] = "TOPOLOGY_CHECKS_FAILED"
            return report
        with scoped_footprints():
            write_json(output / "footprint-manifest.json", footprint_manifest())
            board = build_board_constraints(circuit)
            write_json(output / "board-constraints.json", board)
            schematic = ControllerSchematicCompiler(catalog).compile(circuit, output / "controller.kicad_sch")
            write_json(output / "schematic-artifact.json", schematic)
            compiler = ControllerPcbCompiler(catalog)
            placed = compiler.compile(circuit, schematic, board, output / "controller-placed.kicad_pcb")
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
            route_rules = routing_constraints(circuit)
            if routing_plan_path:
                plan_bytes = routing_plan_path.read_bytes()
                plan = RoutingPlan.model_validate_json(plan_bytes)
                if (plan.source_pcb_fingerprint != placed.fingerprint.digest
                        or plan.source_constraints_hash != board.content_hash
                        or plan.circuit_content_hash != circuit.content_hash
                        or plan.profile != route_rules.profile
                        or plan.net_constraints != route_rules.nets):
                    raise ValueError("Supplied route has different circuit, placement, source PCB or routing rules")
                report["reused_route"] = {"path": str(routing_plan_path),
                    "sha256": hashlib.sha256(plan_bytes).hexdigest(),
                    "note": "Exact lineage checked; full geometry/connectivity verification rerun below."}
            else:
                print(f"Routing {len(circuit.components)} parts / {len(circuit.nets)} nets", flush=True)
                plan, routing_manifest = structured_route(circuit, placed, board, route_rules,
                                                          time_budget_seconds=route_seconds)
                write_json(output / "routing-authoring-manifest.json", routing_manifest)
            write_json(output / "routing-plan.json", plan)
            routing = verify_routing(circuit, placed, board, plan)
            write_json(output / "routing-verification.json", routing)
            report["checks"]["routing"] = {"passed": routing.passed,
                                            "failures": len(plan.failures)}
            if not routing.passed or plan.failures:
                report["status"] = "ROUTING_INCOMPLETE"
                return report
            routed = compiler.compile(circuit, schematic, board, output / "controller.kicad_pcb", plan)
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
            scene["board"]["mounting_holes"] = MOUNTING_HOLES
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
    parser.add_argument("--route-seconds", type=float, default=240)
    parser.add_argument("--skip-native", action="store_true")
    parser.add_argument("--routing-plan", type=Path, help="Reuse only with identical source and rules; independently rechecked")
    args = parser.parse_args()
    report = generate(args.output, captured_on=args.captured_on,
                      route_seconds=args.route_seconds, native=not args.skip_native,
                      routing_plan_path=args.routing_plan)
    print(json.dumps({"status": report["status"], "counts": report.get("counts"),
                      "checks": report["checks"]}, indent=2))


if __name__ == "__main__":
    main()
