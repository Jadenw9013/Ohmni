"""Fixed hackathon demonstration board and its fail-closed qualification checks.

The demonstration uses one existing supported configuration through the
production :class:`~ohmni.application.projects.ProjectPipeline`. This module
adds no engineering judgement of its own: it re-reads the receipts the pipeline
wrote and refuses unless every required external check actually ran, completed
and is bound to the exact bytes on disk. A missing checker, a malformed or stale
report, an unresolved route or an empty fabrication file is a failure here.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic

from ..routing.models import RoutingPlan
from ..synthesis import ArchetypeId, SynthesisBrief

#: The A2 minimum configuration already accepted by
#: ``test_generated_family_copper_closes_real_drc_and_manufacturing``: default
#: 100 x 70 mm outline, one indicator LED, one momentary GPIO input button, no
#: sensors and no programming header. The button is a GPIO-to-ground input, not
#: a power switch, and no firmware is part of this board.
DEMO_BRIEF = SynthesisBrief(
    project_name="ESP32 button and LED board",
    description=(
        "USB-C powered ESP32 with one momentary input button and one indicator LED, "
        "no sensors, default board size."
    ),
    archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
    sensors=(),
    status_led_count=1,
    button_count=1,
    include_programming_header=False,
)

#: Candidate wording for a later, separately authorised live prompt rehearsal.
#: The deterministic harness never sends it to a model.
CONVERSATIONAL_WORDING = (
    "A USB-C powered ESP32 board with one momentary input button and one indicator "
    "LED, no sensors, using the default board size."
)

REQUIRED_FABRICATION_KINDS = frozenset({"F.Cu", "B.Cu", "Edge.Cuts", "F.Mask", "B.Mask"})
REQUIRED_OUTPUTS = (
    "golden.kicad_sch", "golden.kicad_pcb", "erc-report.json", "drc-report.json",
    "golden.erc.json", "golden.drc.json", "routing-plan.json", "routing-verification.json",
    "fabrication/ohmni-fabrication-manifest.json",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Check:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "status": "PASS" if self.passed else "FAIL", "detail": self.detail}


@dataclass
class Qualification:
    checks: list[Check] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.checks.append(Check(name, bool(passed), detail))


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path.name} is not a JSON object")
    return value


def _digest(value: object) -> str | None:
    return value.get("digest") if isinstance(value, dict) else None


def qualify_run(directory: Path) -> Qualification:
    """Re-verify one pipeline output directory from its on-disk receipts.

    Every check is recorded, including the failing ones, so a report always
    shows which receipt was missing rather than stopping at the first problem.
    """
    directory = Path(directory)
    result = Qualification()
    missing = [name for name in REQUIRED_OUTPUTS if not (directory / name).is_file()]
    empty = [name for name in REQUIRED_OUTPUTS
             if (directory / name).is_file() and (directory / name).stat().st_size == 0]
    result.add("required_outputs_present", not missing and not empty,
               "all required outputs present and non-empty" if not missing and not empty
               else f"missing={missing} empty={empty}")
    if missing:
        return result

    try:
        erc = _load(directory / "erc-report.json")
        drc = _load(directory / "drc-report.json")
        raw_erc = _load(directory / "golden.erc.json")
        raw_drc = _load(directory / "golden.drc.json")
        plan = _load(directory / "routing-plan.json")
        routing = _load(directory / "routing-verification.json")
        manifest = _load(directory / "fabrication/ohmni-fabrication-manifest.json")
    except (OSError, ValueError, TypeError) as exc:  # JSONDecodeError is a ValueError
        result.add("reports_parse", False, f"malformed report: {type(exc).__name__}")
        return result
    result.add("reports_parse", True, "all receipts are JSON objects")

    schematic_sha = sha256_file(directory / "golden.kicad_sch")
    pcb_sha = sha256_file(directory / "golden.kicad_pcb")

    # ERC: a completed KiCad run bound to these schematic bytes. Warnings are
    # preserved and reported; they are not upgraded to a clean pass.
    erc_status = erc.get("status")
    result.add("erc_completed", erc.get("tool_status") == "ok" and erc_status in {"pass", "pass_with_warnings"},
               f"status={erc_status} tool_status={erc.get('tool_status')}")
    result.add("erc_bound_to_schematic", _digest(erc.get("artifact_fingerprint")) == schematic_sha,
               f"report={_digest(erc.get('artifact_fingerprint'))} file={schematic_sha}")
    erc_errors = [item for item in erc.get("findings", []) if item.get("severity") == "error"]
    result.add("erc_no_errors", not erc_errors, f"{len(erc_errors)} error-severity ERC findings")
    result.add("erc_raw_kicad_receipt", bool(raw_erc.get("kicad_version")) and isinstance(raw_erc.get("sheets"), list),
               f"kicad_version={raw_erc.get('kicad_version')}")
    erc_types = Counter(str(item.get("type")) for item in erc.get("findings", []))
    if erc_types:
        result.warnings.append("KiCad ERC warnings retained: " + ", ".join(
            f"{name} x{count}" for name, count in sorted(erc_types.items())))

    # DRC: a completed KiCad run bound to these PCB bytes with zero violations
    # and zero unconnected items, in both the typed report and KiCad's own JSON.
    result.add("drc_completed", drc.get("tool_status") == "ok" and drc.get("status") == "pass",
               f"status={drc.get('status')} tool_status={drc.get('tool_status')}")
    result.add("drc_bound_to_pcb", _digest(drc.get("pcb_fingerprint")) == pcb_sha,
               f"report={_digest(drc.get('pcb_fingerprint'))} file={pcb_sha}")
    result.add("drc_zero_findings",
               not drc.get("findings") and not drc.get("unconnected_items")
               and raw_drc.get("violations") == [] and raw_drc.get("unconnected_items") == [],
               f"typed={len(drc.get('findings', []))}/{len(drc.get('unconnected_items', []))} "
               f"raw={len(raw_drc.get('violations') or [])}/{len(raw_drc.get('unconnected_items') or [])}")
    result.add("drc_raw_kicad_receipt", bool(raw_drc.get("kicad_version")),
               f"kicad_version={raw_drc.get('kicad_version')}")

    statistics = plan.get("statistics", {})
    result.add("routing_complete",
               plan.get("failures") == [] and statistics.get("unresolved_net_count") == 0,
               f"failures={len(plan.get('failures') or [])} unresolved={statistics.get('unresolved_net_count')}")
    try:
        plan_hash = RoutingPlan.model_validate(plan).content_hash
    except ValueError:
        plan_hash = None
    routing_findings = routing.get("findings") or []
    failing = [item.get("rule_id") for item in routing_findings if item.get("status") != "pass"]
    result.add("routing_independently_verified",
               bool(routing_findings) and not failing
               and plan_hash is not None and routing.get("plan_fingerprint") == plan_hash,
               f"{len(routing_findings)} findings; non-pass={failing}; "
               f"plan_bound={plan_hash is not None and routing.get('plan_fingerprint') == plan_hash}")

    files = manifest.get("files") or []
    problems = []
    kinds = set()
    for item in files:
        relative = str(item.get("relative_path", ""))
        path = (directory / "fabrication" / relative).resolve()
        if path.parent != (directory / "fabrication").resolve() or not path.is_file():
            problems.append(f"{relative}: missing")
            continue
        if path.stat().st_size == 0 or path.stat().st_size != item.get("size_bytes"):
            problems.append(f"{relative}: size mismatch")
        if sha256_file(path) != item.get("sha256"):
            problems.append(f"{relative}: hash mismatch")
        kinds.add(item.get("kind"))
    has_drill = any(str(item.get("relative_path", "")).endswith(".drl") for item in files)
    missing_kinds = sorted(REQUIRED_FABRICATION_KINDS - kinds)
    result.add("fabrication_package_intact", bool(files) and not problems and not missing_kinds and has_drill,
               f"{len(files)} files; problems={problems} missing_kinds={missing_kinds} drill={has_drill}")
    result.add("fabrication_bound_to_pcb", _digest(manifest.get("pcb_fingerprint")) == pcb_sha
               or manifest.get("pcb_fingerprint") == pcb_sha,
               f"manifest={manifest.get('pcb_fingerprint')!s:.80} file={pcb_sha}")
    return result


@dataclass
class Attempt:
    directory: Path
    qualification: Qualification
    stage_seconds: dict[str, float]
    total_seconds: float
    error: str | None = None
    fault: dict[str, object] | None = None


def run_attempt(directory: Path, pipeline_factory: Callable, brief: SynthesisBrief = DEMO_BRIEF,
                *, include_fault: bool = True) -> Attempt:
    """Run one fresh pipeline attempt into an empty directory and qualify it."""
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError("attempt directories must be fresh; refusing to reuse old receipts")
    directory.mkdir(parents=True, exist_ok=True)
    marks: list[tuple[str, float]] = []
    started = monotonic()

    def progress(event) -> None:
        marks.append((event.stage, monotonic() - started))

    error = None
    report = None
    try:
        report = pipeline_factory(progress).run(directory, brief)
    except Exception as exc:  # noqa: BLE001 -- recorded as a typed failure, never a pass
        error = f"{type(exc).__name__}: {exc}"
    total = monotonic() - started
    stage_seconds: dict[str, float] = {}
    previous = 0.0
    for stage, at in marks:
        stage_seconds[stage] = round(stage_seconds.get(stage, 0.0) + at - previous, 3)
        previous = at
    if report is not None:
        (directory / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    qualification = qualify_run(directory)
    if error is not None:
        qualification.add("pipeline_completed", False, error[:500])
    else:
        release = report.release
        qualification.add("pipeline_completed", True, "ProjectPipeline.run returned a report")
        qualification.add("release_current", release.get("current") is True
                          and release.get("status") == "READY_FOR_MANUFACTURING_REVIEW",
                          f"release={release.get('status')} current={release.get('current')}")
    fault = None
    if include_fault and qualification.passed:
        fault = check_fault(directory, qualification)
    return Attempt(directory, qualification, stage_seconds, round(total, 3), error, fault)


def _protected_hashes(directory: Path) -> dict[str, str]:
    names = set(REQUIRED_OUTPUTS) | {f"fabrication/{path.name}"
                                     for path in (directory / "fabrication").iterdir() if path.is_file()}
    return {name: sha256_file(directory / name) for name in sorted(names)}


def check_fault(directory: Path, qualification: Qualification) -> dict[str, object] | None:
    """Prove the damaged copy fails real DRC while the original stays byte-identical."""
    protected = _protected_hashes(directory)
    started = monotonic()
    try:
        fault = run_fault_diagnostic(directory)
    except (FaultDiagnosticError, OSError, ValueError) as exc:
        qualification.add("fault_detected_by_real_drc", False, f"{type(exc).__name__}: {exc}"[:500])
        return None
    fault["seconds"] = round(monotonic() - started, 3)
    unconnected = [item for item in fault["drc"]["unconnected_items"]]
    qualification.add(
        "fault_detected_by_real_drc",
        fault["fault_detected"] is True and fault["drc"]["status"] == "fail" and bool(unconnected)
        and fault["snapshot_sha256"] != fault["source_pcb_sha256"] and fault["releasable"] is False,
        f"{fault['fault_id']}: status={fault['drc']['status']} "
        f"unconnected={fault['drc']['unconnected_count']} findings={fault['drc']['finding_count']}")
    unchanged = _protected_hashes(directory) == protected
    qualification.add("original_unchanged_after_fault", unchanged,
                      "original board, receipts and package are byte-identical after the fault check"
                      if unchanged else "an original artifact changed during the fault check")
    return fault


# ---------------------------------------------------------------------------
# One isolated fault: a separate diagnostic snapshot with one copper track cut.
# ---------------------------------------------------------------------------

#: Fixed, server-owned identity of the only supported fault. No caller supplies
#: a path, a net or a segment: those are all derived from this constant.
FAULT_ID = "cut-led1-anode-track"
FAULT_NET = "LED1_A"
FAULT_DIRECTORY = "fault"
FAULT_PCB = "diagnostic-fault.kicad_pcb"
FAULT_RAW_DRC = "diagnostic-fault.drc.json"
FAULT_RESULT = "diagnostic-result.json"
FAULT_TIMEOUT_SECONDS = 120
#: Checks deliberately not run on the damaged snapshot. They are reported as
#: NOT_CHECKED, never inherited from the original board.
#: Deterministic explanation bound to this one known finding. It describes the
#: recorded receipt; it is not generated and it does not grade the board.
FAULT_EXPLANATION = (
    "One copper track on net LED1_A was removed from a separate copy of the board.",
    ("KiCad DRC, run on that exact copy, reports that pad 2 of the LED D1, on net LED1_A, is no "
     "longer connected to the rest of its net, and that the remaining track has a dangling end."),
    ("On a real board the indicator LED could not light: its current path through the "
     "resistor would be open."),
    ("Only DRC ran on this copy. Every other check is NOT_CHECKED, and this copy is never "
     "offered for download or manufacturing."),
)
FAULT_NOT_CHECKED = ("schematic_erc", "independent_routing_verification", "physical_placement_rules",
                     "manufacturing_profile", "fabrication_export", "simulation", "bench")

_NET_DECLARATION = re.compile(r'^  \(net (\d+) "([^"]*)"\)$')
_SEGMENT = re.compile(
    r'^  \(segment \(start (-?[\d.]+) (-?[\d.]+)\) \(end (-?[\d.]+) (-?[\d.]+)\) '
    r'\(width ([\d.]+)\) \(layer "([^"]+)"\) \(net (\d+)\) \(uuid "([0-9a-f-]{36})"\)\)$')
_VIA = re.compile(
    r'^  \(via \(at (-?[\d.]+) (-?[\d.]+)\) \(size ([\d.]+)\) \(drill ([\d.]+)\) '
    r'\(layers "[^"]+" "[^"]+"\) \(net (\d+)\) \(uuid "[0-9a-f-]{36}"\)\)$')


class FaultDiagnosticError(RuntimeError):
    """The diagnostic fault could not be produced or checked; nothing is inferred."""


def _net_names(lines: list[str]) -> dict[str, str]:
    return {match[1]: match[2] for line in lines if (match := _NET_DECLARATION.match(line))}


def snapshot_copper(pcb_text: str) -> dict[str, list[dict[str, object]]]:
    """Read track and via geometry from the exact bytes of one compiled PCB.

    This reads only the one-line ``segment``/``via`` records Ohmni's own PCB
    compiler emits; it is not a general KiCad parser. Display geometry for a
    diagnostic snapshot comes from here, never from the original compilation.
    """
    lines = pcb_text.splitlines()
    nets = _net_names(lines)
    tracks, vias = [], []
    for line in lines:
        if line.startswith("  (segment "):
            match = _SEGMENT.match(line)
            if match is None:
                raise FaultDiagnosticError("unrecognised segment record in snapshot")
            sx, sy, ex, ey, width, layer, net, uuid = match.groups()
            tracks.append({"start_x_mm": float(sx), "start_y_mm": float(sy), "end_x_mm": float(ex),
                           "end_y_mm": float(ey), "width_mm": float(width), "layer": layer,
                           "net_name": nets[net], "uuid": uuid})
        elif line.startswith("  (via "):
            match = _VIA.match(line)
            if match is None:
                raise FaultDiagnosticError("unrecognised via record in snapshot")
            x, y, size, drill, net = match.groups()
            vias.append({"x_mm": float(x), "y_mm": float(y), "diameter_mm": float(size),
                         "drill_mm": float(drill), "net_name": nets[net]})
    return {"tracks": tracks, "vias": vias}


def build_fault_snapshot(good_pcb: Path, destination: Path) -> dict[str, object]:
    """Write a separate snapshot of ``good_pcb`` with one LED anode track removed.

    The original file is only read. The snapshot differs from it by exactly one
    deleted line, the first ``LED1_A`` segment in file order.
    """
    good_bytes = Path(good_pcb).read_bytes()
    good_sha = hashlib.sha256(good_bytes).hexdigest()
    lines = good_bytes.decode("utf-8").split("\n")
    nets = _net_names(lines)
    net_number = next((number for number, name in nets.items() if name == FAULT_NET), None)
    if net_number is None:
        raise FaultDiagnosticError(f"board has no {FAULT_NET} net")
    index = next((i for i, line in enumerate(lines)
                  if (match := _SEGMENT.match(line)) and match[7] == net_number), None)
    if index is None:
        raise FaultDiagnosticError(f"board has no {FAULT_NET} copper track to cut")
    removed = lines[index]
    match = _SEGMENT.match(removed)
    damaged = "\n".join(lines[:index] + lines[index + 1:]).encode("utf-8")
    destination = Path(destination)
    if destination.exists():
        raise FaultDiagnosticError("diagnostic snapshots are never overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(damaged)
    return {
        "fault_id": FAULT_ID,
        "source_pcb_sha256": good_sha,
        "snapshot_sha256": hashlib.sha256(damaged).hexdigest(),
        "removed_segment": {"net_name": FAULT_NET, "uuid": match[8], "layer": match[6],
                            "start_mm": [float(match[1]), float(match[2])],
                            "end_mm": [float(match[3]), float(match[4])],
                            "line_number": index + 1},
    }


def run_fault_diagnostic(good_run: Path, *, executable: str | None = None) -> dict[str, object]:
    """Create the damaged snapshot of one qualified run and check it with real KiCad DRC.

    Produces a diagnostic-only result: it is never releasable, carries its own
    snapshot hash and raw DRC receipt, and lists every check it did not run.
    """
    from ..adapters.process import run_tool
    from ..adapters.tools import find_kicad_cli
    from ..eda.kicad.pcb_parser import DrcReportParseError, parse_drc_json
    from ..eda.models import ArtifactFingerprint

    good_run = Path(good_run)
    good_pcb = good_run / "golden.kicad_pcb"
    drc_receipt = _load(good_run / "drc-report.json")
    executable = executable or find_kicad_cli()
    if executable is None:
        raise FaultDiagnosticError("kicad-cli is unavailable; the fault was not checked")
    directory = good_run / FAULT_DIRECTORY
    snapshot_path = directory / FAULT_PCB
    snapshot = build_fault_snapshot(good_pcb, snapshot_path)
    if snapshot["source_pcb_sha256"] != _digest(drc_receipt.get("pcb_fingerprint")):
        raise FaultDiagnosticError("source board is not the board the original DRC checked")
    report_path = directory / FAULT_RAW_DRC
    command = [executable, "pcb", "drc", "--format", "json", "--severity-all",
               "--exit-code-violations", "--output", str(report_path), str(snapshot_path)]
    before = sha256_file(snapshot_path)
    completed = run_tool(command, timeout=FAULT_TIMEOUT_SECONDS)
    after = sha256_file(snapshot_path)
    if not before == after == snapshot["snapshot_sha256"]:
        raise FaultDiagnosticError("diagnostic snapshot changed during DRC")
    run_id = hashlib.sha256(f"{after}:hackathon-fault-drc".encode()).hexdigest()[:16]
    try:
        report = parse_drc_json(
            report_path, pcb_fingerprint=ArtifactFingerprint(digest=after),
            schematic_fingerprint=ArtifactFingerprint(
                digest=_digest(drc_receipt.get("source_schematic_fingerprint"))),
            run_id=run_id, command=command, return_code=completed.returncode,
            stdout=completed.stdout, stderr=completed.stderr)
    except DrcReportParseError as exc:
        raise FaultDiagnosticError(f"KiCad DRC on the snapshot did not complete: {exc}") from exc
    active = [item for item in report.findings + report.unconnected_items if not item.excluded]
    copper = snapshot_copper(snapshot_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": 1,
        "kind": "diagnostic_fault_only",
        "releasable": False,
        **snapshot,
        "checker": {"name": "KiCad PCB DRC", "kicad_version": report.kicad_version,
                    "command_template": ["kicad-cli", "pcb", "drc", "--format", "json", "--severity-all",
                                         "--exit-code-violations", "--output", "<report>", "<snapshot>"],
                    "return_code": completed.returncode, "run_id": run_id},
        "raw_drc_sha256": sha256_file(report_path),
        "drc": {"status": report.status.value, "tool_status": report.tool_status.value,
                "finding_count": len(report.findings), "unconnected_count": len(report.unconnected_items),
                "findings": [_finding_summary(item) for item in report.findings],
                "unconnected_items": [_finding_summary(item) for item in report.unconnected_items]},
        "fault_detected": report.tool_status.value == "ok" and bool(active),
        "not_checked": list(FAULT_NOT_CHECKED),
        "copper": {"track_count": len(copper["tracks"]), "via_count": len(copper["vias"])},
    }
    (directory / FAULT_RESULT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _finding_summary(finding) -> dict[str, object]:
    return {"type": finding.type, "severity": finding.severity,
            "classification": finding.classification.value,
            "description": finding.description[:300],
            "items": [{"description": item.description[:200], "x_mm": item.x, "y_mm": item.y}
                      for item in finding.items[:4]]}
