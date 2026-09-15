"""Reproduce a learning preview from one completed local CLI project build.

Saved presentation JSON is not verification authority. Recreate the semantic,
placement and copper artifacts, match their bytes to the saved run, and run the
existing deterministic and KiCad checks before projecting any learning content.
No router, model, simulation or fabrication exporter runs here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import date
from pathlib import Path

from ..adapters import ToolStatus
from ..catalog import default_catalog
from ..domain import CircuitIR
from ..eda.kicad import KiCadCliAdapter, KiCadPcbCompiler, KiCadSchematicCompiler
from ..eda.models import ErcReport, ErcStatus
from ..eda.pcb_models import DrcReport, DrcStatus
from ..manufacturing import prototype_profile, verify_manufacturing
from ..physical.models import PlacementRequest
from ..physical.placement import GeneratedPlacement, generate_placement
from ..routing.models import RoutingPlan, RoutingVerificationReport
from ..routing.verifier import verify_routing
from ..synthesis import SynthesisBrief
from ..verifier import verify
from .demo import BOUNDED_SYNTHESIS_MODE, current_pcb_policy
from .naming import component_term
from .product import _board_geometry, _purpose, build_brief
from .projects import _prepare_project
from .systems import build_flows, build_systems, group_components

MAX_SOURCE_FILE_BYTES = 64 * 1024 * 1024
NATIVE_TIMEOUT_SECONDS = 60
PREVIEW_NOTE = (
    "A saved geometry preview reproduced from a completed local engineering run. "
    "Checks describe these exact source artifacts at export time, not current validation "
    "or physical performance. Colors and component bodies are illustrative; component "
    "height and the board stack-up are not modeled."
)
LIMITATIONS = [
    "Electrical facts retain bundled catalog provenance; they are not bench measurements.",
    "Firmware is not included; wiring does not establish runtime behavior.",
    "Not simulation, thermal, EMC, RF, signal-integrity, assembly or bench verified.",
    "The manufacturing profile is synthetic and requires fabricator review.",
    "Source hashes identify local files; they are not signed attestations.",
]


class ReferencePreviewError(ValueError):
    """The recorded run cannot support this reference preview."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _require(condition, message):
    if not condition:
        raise ReferencePreviewError(message)


class _SourceSnapshot:
    """Read only contained regular files, retaining bytes for end-of-export checks."""

    def __init__(self, directory: Path):
        _require(not directory.is_symlink(), "Source directory must not be a symbolic link")
        self.directory = directory.resolve(strict=True)
        _require(self.directory.is_dir(), "Source must be a completed run directory")
        self.files: dict[str, bytes] = {}

    def read(self, name: str) -> bytes:
        path = self.directory / name
        _require(not Path(name).is_absolute() and ".." not in Path(name).parts,
                 "Source filename leaves the run directory")
        _require(all(not parent.is_symlink() for parent in (path, *path.parents)
                     if parent != self.directory and parent.is_relative_to(self.directory)),
                 "Source files must not be symbolic links")
        resolved = path.resolve(strict=True)
        _require(resolved.is_relative_to(self.directory), "Source file leaves the run directory")
        _require(resolved.is_file() and resolved.stat().st_size <= MAX_SOURCE_FILE_BYTES,
                 "Source file is missing, not regular, or too large")
        value = resolved.read_bytes()
        _require(len(value) <= MAX_SOURCE_FILE_BYTES, "Source file exceeds its size limit")
        self.files[name] = value
        return value

    def json(self, name: str):
        return json.loads(self.read(name))

    def model(self, name: str, model):
        return model.model_validate_json(self.read(name))

    def unchanged(self):
        for name, captured in list(self.files.items()):
            _require(self.read(name) == captured, "Source files changed during preview export")


def _check_erc(report, schematic):
    _require(report.tool_status is ToolStatus.OK
             and report.status in {ErcStatus.PASS, ErcStatus.PASS_WITH_WARNINGS}
             and report.artifact_fingerprint == schematic.fingerprint,
             "A completed passing ERC for the exact schematic is required")


def _check_drc(report, routed):
    _require(report.tool_status is ToolStatus.OK
             and report.status in {DrcStatus.PASS, DrcStatus.PASS_WITH_WARNINGS}
             and not report.findings and not report.unconnected_items
             and report.pcb_fingerprint == routed.fingerprint
             and report.source_schematic_fingerprint == routed.schematic_fingerprint,
             "A completed clean DRC for the exact routed PCB is required")


def _check_release(source, report, circuit, schematic, routed, profile):
    release = report["release"]
    _require(release.get("status") == "READY_FOR_MANUFACTURING_REVIEW"
             and release.get("current") is True
             and release.get("pcb_fingerprint") == routed.fingerprint.digest,
             "The saved run has no completed current release")
    manifest_item = release["manifest"]
    _require(manifest_item["relative_path"] == "ohmni-fabrication-manifest.json",
             "Unexpected fabrication manifest name")
    raw = source.read("fabrication/ohmni-fabrication-manifest.json")
    _require(_digest(raw) == manifest_item["sha256"] and len(raw) == manifest_item["size_bytes"],
             "Saved fabrication manifest has changed")
    manifest = json.loads(raw)
    package_hash = manifest.pop("package_fingerprint")
    _require(_digest(_json_bytes(manifest)) == package_hash == release["package_fingerprint"],
             "Fabrication package fingerprint does not match its manifest")
    expected = {
        "circuit_fingerprint": circuit.content_hash,
        "schematic_fingerprint": schematic.fingerprint.digest,
        "pcb_fingerprint": routed.fingerprint.digest,
        "routing_plan_fingerprint": routed.routing_plan_fingerprint,
        "manufacturing_profile_fingerprint": profile.content_hash,
        "release_status": "ready_for_manufacturing_review",
        "files": release["files"],
    }
    _require(all(manifest.get(key) == value for key, value in expected.items()),
             "Fabrication manifest lineage does not match the reproduced run")
    _require(bool(release["files"]), "The completed release has no fabrication files")
    names = set()
    kinds = set()
    for item in release["files"]:
        name = item["relative_path"]
        _require(isinstance(name, str) and Path(name).name == name and name not in names,
                 "Fabrication files must have unique contained names")
        names.add(name)
        data = source.read("fabrication/" + name)
        _require(bool(data) and _digest(data) == item["sha256"] and len(data) == item["size_bytes"],
                 "Saved fabrication file has changed")
        kinds.add(item["kind"])
    _require({"F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts", "Drill"}
             <= kinds, "The completed release is missing required fabrication outputs")
    return package_hash


def _build(source, *, captured_on: date, label: str | None):
    _require(not (source.directory / "failure.json").exists(), "Failed runs cannot become references")
    report = source.json("report.json")
    _require(report.get("mode") == BOUNDED_SYNTHESIS_MODE
             and report["project"].get("status") == "READY_FOR_MANUFACTURING_REVIEW",
             "A completed generated project report is required")
    _require(all(report["pcb"].get(key) == value for key, value in current_pcb_policy().items()),
             "Saved PCB compiler or footprint policy is no longer current")
    brief = source.model("confirmed-brief.json", SynthesisBrief)
    result, requirements = _prepare_project(brief)
    circuit = result.circuit
    saved_circuit = source.model("circuit.json", CircuitIR)
    _require(saved_circuit.content_hash == circuit.content_hash
             and report["project"].get("circuit_hash") == circuit.content_hash
             and report["project"].get("brief_fingerprint") == brief.fingerprint,
             "Saved circuit and report do not match the confirmed brief")
    request = source.model("placement-request.json", PlacementRequest)
    _require(result.placement_request is not None
             and request.content_hash == result.placement_request.content_hash,
             "Saved placement request does not match the confirmed brief")
    placement = generate_placement(circuit, request, default_catalog())
    saved_placement = source.model("placement.json", GeneratedPlacement)
    _require(saved_placement == placement, "Saved placement differs from the current generated geometry")
    board = placement.board
    _require(report["project"].get("placement_request_fingerprint") == request.content_hash
             and report["pcb"]["placement"].get("request_fingerprint") == request.content_hash
             and report["pcb"]["placement"].get("constraints_hash") == board.content_hash
             and report["pcb"]["placement"].get("algorithm") == placement.algorithm,
             "Report placement lineage does not match the saved placement")
    plan = source.model("routing-plan.json", RoutingPlan)
    _require(not plan.failures, "Incomplete routing cannot become a reference")
    catalog = default_catalog()
    semantic = verify(circuit, catalog, requirements.requirements)
    _require(not semantic.export_blocked and semantic.coverage == 1
             and requirements.requirements.is_supported_scope,
             "The confirmed circuit did not pass complete supported semantic verification")
    with tempfile.TemporaryDirectory(prefix="ohmni-reference-") as temporary:
        work = Path(temporary)
        schematic = KiCadSchematicCompiler(catalog).compile(circuit, work / "golden.kicad_sch")
        compiler = KiCadPcbCompiler(catalog)
        placed = compiler.compile(circuit, schematic, board, work / "golden.placed.kicad_pcb")
        route_report = verify_routing(circuit, placed, board, plan)
        saved_routing = source.model("routing-verification.json", RoutingVerificationReport)
        _require(route_report.passed and saved_routing == route_report,
                 "Saved routing does not pass independent verification")
        routed = compiler.compile(circuit, schematic, board, work / "golden.kicad_pcb", plan)
        # The plan's original path participates in its hash. Preserve that identity,
        # but make all native checks read only the reproduced temporary artifacts.
        routed.source_placed_pcb_path = placed.path
        for artifact in (schematic, placed, routed):
            _require(_digest(source.read(artifact.path.name)) == artifact.fingerprint.digest,
                     "Saved artifact bytes differ from the reproduced circuit and routing")
        _require(report["schematic"].get("fingerprint") == schematic.fingerprint.digest
                 and report["pcb"].get("fingerprint") == routed.fingerprint.digest
                 and report["pcb"].get("source_schematic_fingerprint") == schematic.fingerprint.digest
                 and report["pcb"].get("source_placed_pcb_fingerprint") == placed.fingerprint.digest,
                 "Report artifact lineage does not match the saved files")
        physical = routed.compilation.physical_verification
        _require(bool(physical.findings) and physical.passed,
                 "The reproduced board did not pass physical checks")
        recorded_erc = source.model("erc-report.json", ErcReport)
        recorded_drc = source.model("drc-report.json", DrcReport)
        _check_erc(recorded_erc, schematic)
        _check_drc(recorded_drc, routed)
        profile = prototype_profile()
        manufacturing = verify_manufacturing(routed, board, plan, profile)
        _require(bool(manufacturing.findings) and manufacturing.passed,
                 "The reproduced board did not pass the manufacturing profile")
        package_hash = _check_release(source, report, circuit, schematic, routed, profile)
        # Exactly two bounded native checks; no simulation or fabrication processes.
        adapter = KiCadCliAdapter(timeout_seconds=NATIVE_TIMEOUT_SECONDS)
        erc = adapter.run_erc(schematic)
        _check_erc(erc, schematic)
        drc = adapter.run_drc(routed)
        _check_drc(drc, routed)
        positions = {p.component_ref: (p.x_mm, p.y_mm) for p in board.placements}
        groupings = group_components(circuit, catalog, positions, request)
        by_ref = {group.component_ref: group for group in groupings}
        geometry = _board_geometry(board, routed, by_ref, circuit, catalog)
        preview = {
            "schema_version": 1,
            "source": {
                "kind": "previously_generated_reference_preview",
                "label": label or brief.project_name,
                "job_id": source.directory.name,
                "captured_on": captured_on.isoformat(),
                "artifact_fingerprint": routed.fingerprint.digest,
                "schematic_fingerprint": schematic.fingerprint.digest,
                "routing_plan_fingerprint": plan.content_hash,
                "circuit_fingerprint": circuit.content_hash,
                "brief_fingerprint": brief.fingerprint,
                "constraints_hash": board.content_hash,
                "package_fingerprint": package_hash,
                **current_pcb_policy(),
                "note": PREVIEW_NOTE,
            },
            "confirmed_brief": brief.model_dump(mode="json"),
            "brief": build_brief(requirements).model_dump(mode="json"),
            "board": geometry.model_dump(mode="json"),
            "components": [{
                "ref": part.ref, "part_id": part.part_id,
                "name": component_term(circuit, catalog, part.ref).model_dump(mode="json"),
                "system": by_ref[part.ref].system.value,
                "purpose": _purpose(circuit, catalog, part.ref, by_ref[part.ref]),
            } for part in sorted(circuit.components, key=lambda part: part.ref)],
            "systems": [system.model_dump(mode="json") for system in build_systems(groupings)],
            "flows": [flow.model_dump(mode="json") for flow in build_flows(circuit, catalog, groupings)],
            "checks": {
                "basis": "Recomputed from the exact source artifacts at preview export time",
                "semantic": {"report_id": semantic.report_id, "coverage": semantic.coverage,
                             "export_blocked": semantic.export_blocked,
                             "subsystem_status": {key: value.value for key, value in semantic.subsystem_status.items()},
                             "rule_count": len(semantic.results), "limitations": semantic.limitations},
                "erc": {"status": erc.status.value, "tool_status": erc.tool_status.value,
                        "kicad_version": erc.kicad_version, "finding_count": len(erc.findings),
                        "limitations": erc.limitations},
                "physical": {"passed": physical.passed, "finding_count": len(physical.findings)},
                "routing": {"passed": route_report.passed, "finding_count": len(route_report.findings),
                            "plan_fingerprint": plan.content_hash},
                "drc": {"status": drc.status.value, "tool_status": drc.tool_status.value,
                        "kicad_version": drc.kicad_version, "finding_count": len(drc.findings),
                        "unconnected_count": len(drc.unconnected_items), "limitations": drc.limitations},
                "manufacturing": {"passed": manufacturing.passed, "profile": profile.display_name,
                                  "provenance": profile.provenance.value},
                "simulation": "NOT_RUN", "bench": "NOT_VERIFIED",
            },
            "limitations": LIMITATIONS,
        }
    source.unchanged()
    _require(not (source.directory / "failure.json").exists(), "Source run failed during preview export")
    preview["source"]["files"] = {name: _digest(data) for name, data in sorted(source.files.items())}
    return preview


def build_reference_preview(run_directory: Path, *, captured_on: date,
                            label: str | None = None) -> dict:
    """Return reproducible preview data, rejecting incomplete or stale local builds."""
    try:
        return _build(_SourceSnapshot(Path(run_directory)), captured_on=captured_on, label=label)
    except ReferencePreviewError:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        raise ReferencePreviewError("The saved run could not be reproduced and verified") from exc


def export_reference_preview(run_directory: Path, destination: Path, *, captured_on: date,
                             label: str | None = None) -> dict:
    """Atomically write a verified preview, keeping all original source files intact."""
    destination = Path(destination)
    _require(not destination.is_symlink(), "Preview destination must not be a symbolic link")
    destination = destination.resolve()
    _require(not destination.is_relative_to(Path(run_directory).resolve()),
             "Preview destination must be outside the source run")
    preview = build_reference_preview(run_directory, captured_on=captured_on, label=label)
    data = _json_bytes(preview) + b"\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".reference-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return preview


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="Completed ohmni generate output")
    parser.add_argument("--output", type=Path, required=True, help="Preview JSON outside the source run")
    parser.add_argument("--captured-on", type=date.fromisoformat, required=True,
                        help="Recorded export date, YYYY-MM-DD; explicit for reproducibility")
    parser.add_argument("--label", help="Optional presentation title; does not change electrical data")
    args = parser.parse_args(argv)
    try:
        preview = export_reference_preview(args.run_dir, args.output,
                                           captured_on=args.captured_on, label=args.label)
    except (ReferencePreviewError, OSError):
        parser.exit(1, "Reference export failed: source run is incomplete, stale, or could not be checked.\n")
    print(f"Saved {len(preview['board']['components'])} components to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
