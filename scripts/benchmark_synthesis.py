"""Frozen structured-brief benchmark; every attempt and failure is retained.

This development harness does not evaluate natural-language interpretation.
Native tools are invoked only by the real ProjectPipeline and guarded adapters.
Use a fresh, normally accessible output directory for Windows KiCad execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
import traceback
from collections import Counter
from contextlib import ExitStack
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

from ohmni.adapters.process import run_tool
from ohmni.adapters.tools import KicadCli
from ohmni.application.demo import PRODUCT_ROUTING_TIME_BUDGET_SECONDS, current_pcb_policy
from ohmni.application.projects import ProjectPipeline, ProjectRefusalError
from ohmni.catalog import default_catalog
from ohmni.domain import CircuitIR
from ohmni.manufacturing.models import prototype_profile
from ohmni.physical.models import PlacementRequest
from ohmni.physical.placement import GeneratedPlacement
from ohmni.routing.models import RoutingPlan
from ohmni.synthesis import SynthesisBrief, synthesize
from ohmni.verifier import verify

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "tests/fixtures/synthesis_benchmark.json"
CORPUS_SHA256 = "59509e67a669d21b989c17f186c2070318e41b8827ec88c2ab478a39b2ca848e"
DEFAULT_SAFETY_CORPUS = ROOT / "tests/fixtures/synthesis_safety_benchmark.json"
SAFETY_CORPUS_SHA256 = "ba7de58e1674cfbce62c1bb5e1cce76cd5010b6aedc746016a325de7ad80a69c"
CANONICAL_KEYS = (
    "circuit", "schematic", "placed_pcb", "pcb", "placement_request", "placement", "routing",
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value) -> str:
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                   allow_nan=False).encode())


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    """Atomic snapshot; attempts and artifacts are never overwritten by retries."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def now() -> str:
    return datetime.now(UTC).isoformat()


def load_corpus(path: Path = DEFAULT_CORPUS) -> dict:
    raw = path.read_bytes()
    if digest_bytes(raw) != CORPUS_SHA256:
        raise ValueError("Corpus differs from the frozen benchmark; author a new version explicitly")
    corpus = json.loads(raw)
    cases = corpus["cases"]
    if len(cases) != 80 or len({case["case_id"] for case in cases}) != 80:
        raise ValueError("Expected 80 unique frozen cases")
    accepted = Counter()
    refusals = 0
    for case in cases:
        if not re.fullmatch(r"(?:A[123]|R)-[0-9]{2}", case["case_id"]):
            raise ValueError("Invalid case ID")
        SynthesisBrief.model_validate(case["brief"])
        if canonical_hash(case["brief"]) != case["input_sha256"]:
            raise ValueError("Input fingerprint mismatch")
        if canonical_hash(case["expected"]) != case["expectation_sha256"]:
            raise ValueError("Expectation fingerprint mismatch")
        if case["expected"]["outcome"] == "accepted":
            accepted[case["brief"]["archetype"]] += 1
        elif case["expected"]["outcome"] == "refused":
            refusals += 1
        else:
            raise ValueError("Unknown expected outcome")
    if sorted(accepted.values()) != [20, 20, 20] or refusals != 20:
        raise ValueError("The 60/20 denominators must remain fixed")
    return corpus


def source_snapshot(root: Path = ROOT) -> dict:
    """Hash source/data bytes, including uncommitted changes, not just Git HEAD."""
    paths = [path for path in (root / "src").rglob("*")
             if path.is_file() and path.suffix in {".py", ".json"}]
    paths += [root / "pyproject.toml", root / "scripts/benchmark_synthesis.py"]
    files = {path.relative_to(root).as_posix(): digest_bytes(path.read_bytes())
             for path in sorted(paths)}
    return {"sha256": canonical_hash(files), "files": files}


def load_safety_corpus(path: Path = DEFAULT_SAFETY_CORPUS) -> dict:
    if digest_bytes(path.read_bytes()) != SAFETY_CORPUS_SHA256:
        raise ValueError("Supplemental safety corpus differs from its frozen version")
    corpus = read_json(path)
    if len(corpus["cases"]) != 30 or len({case["case_id"] for case in corpus["cases"]}) != 30:
        raise ValueError("Expected 30 unique supplemental safety cases")
    for case in corpus["cases"]:
        SynthesisBrief.model_validate(case["brief"])
        if canonical_hash(case["brief"]) != case["input_sha256"] or canonical_hash(case["expected"]) != case["expectation_sha256"]:
            raise ValueError("Supplemental case fingerprint mismatch")
        if case["expected"]["outcome"] != "refused" or case["expected"]["downstream_eda_calls"] != 0:
            raise ValueError("Supplemental safety cases must stop before EDA")
    return corpus


def environment() -> dict:
    availability = KicadCli().availability()
    tool = availability.model_dump(mode="json")
    executable = Path(availability.executable) if availability.executable else None
    tool["executable_sha256"] = digest_bytes(executable.read_bytes()) if executable else None
    try:
        git = run_tool(["git", "-C", str(ROOT), "rev-parse", "HEAD"], timeout=10)
        head = git.stdout.strip() if git.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        head = None
    return {"python": sys.version, "platform": platform.platform(), "git_head": head,
            "dependencies": {name: version(name) for name in ("pydantic", "PyMuPDF")},
            "kicad": tool, "manufacturing_profile": prototype_profile().model_dump(mode="json"),
            "manufacturing_profile_sha256": prototype_profile().content_hash,
            "routing_budget_seconds": PRODUCT_ROUTING_TIME_BUDGET_SECONDS}


def inventory_findings(circuit: CircuitIR, expected: dict) -> list[str]:
    """Compare outputs with explicit corpus facts; never feed them to synthesis."""
    findings = []
    inventory = dict(Counter(part.part_id for part in circuit.components))
    if inventory != expected["inventory"]:
        findings.append(f"Inventory mismatch: observed {inventory!r}")
    for part in circuit.components:
        if part.package != expected["packages"].get(part.part_id):
            findings.append(f"Unexpected package for {part.ref}: {part.package}")
    actual_sensors = [{"ref": part.ref, "part_id": part.part_id,
                       "address": part.selected_i2c_address}
                      for part in circuit.components if part.selected_i2c_address is not None]
    if actual_sensors != expected["sensor_slots"]:
        findings.append(f"Sensor slot mismatch: observed {actual_sensors!r}")
    parts = {part.ref: part for part in circuit.components}
    for slot in expected["spi_slots"]:
        part = parts.get(slot["ref"])
        net = next((net for net in circuit.nets if net.name == slot["chip_select_net"]), None)
        if part is None or part.part_id != slot["part_id"] or net is None or not any(
            pin.component == slot["ref"] and pin.pin == "1" for pin in net.connections
        ):
            findings.append(f"SPI slot mismatch: {slot!r}")
    return findings


def safe_file(directory: Path, relative: str) -> Path:
    path = directory / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts or path.is_symlink():
        raise ValueError("Artifact path escapes its attempt")
    resolved = path.resolve()
    if not resolved.is_relative_to(directory.resolve()) or not resolved.is_file():
        raise ValueError(f"Missing artifact: {relative}")
    return resolved


def file_fingerprint(directory: Path, relative: str) -> str:
    return digest_bytes(safe_file(directory, relative).read_bytes())


def canonical_artifacts(directory: Path) -> dict:
    """Only explicit path/event exclusions. No coordinates or net facts removed.

    The emitted schematic/PCBs are already deterministic bytes. RoutingPlan's
    own hash includes its absolute source path; the portable comparison replaces
    that one field with the fixed placed-artifact name, retaining geometry,
    statistics, profile, constraints, and failures. Events carry wall timestamps.
    """
    fingerprints = {}
    for name, filename in (("schematic", "golden.kicad_sch"),
                           ("placed_pcb", "golden.placed.kicad_pcb"),
                           ("pcb", "golden.kicad_pcb")):
        if (directory / filename).is_file():
            fingerprints[name] = file_fingerprint(directory, filename)
    if (directory / "circuit.json").is_file():
        fingerprints["circuit"] = CircuitIR.model_validate(read_json(directory / "circuit.json")).content_hash
    if (directory / "placement.json").is_file():
        placement = GeneratedPlacement.model_validate(read_json(directory / "placement.json"))
        request = PlacementRequest.model_validate(read_json(safe_file(directory, "placement-request.json")))
        if request.content_hash != placement.request_fingerprint or request.circuit_content_hash != placement.circuit_content_hash or fingerprints.get("circuit") != placement.circuit_content_hash:
            raise ValueError("Placement request, solved placement and circuit binding disagree")
        fingerprints["placement"] = canonical_hash(placement.model_dump(mode="json"))
        fingerprints["placement_constraints"] = placement.board.content_hash
        fingerprints["placement_algorithm"] = placement.algorithm
        fingerprints["placement_request"] = request.content_hash
    if (directory / "routing-plan.json").is_file():
        plan = RoutingPlan.model_validate(read_json(directory / "routing-plan.json"))
        if plan.circuit_content_hash != fingerprints.get("circuit") or plan.source_constraints_hash != fingerprints.get("placement_constraints") or plan.source_pcb_fingerprint != fingerprints.get("placed_pcb") or plan.source_pcb_path.resolve() != safe_file(directory, "golden.placed.kicad_pcb"):
            raise ValueError("Routing does not bind this circuit, solved placement and placed PCB")
        values = plan.model_dump(mode="json", exclude={"events", "source_pcb_path"})
        values["source_pcb_path"] = "golden.placed.kicad_pcb"
        fingerprints["routing"] = canonical_hash(values)
    return fingerprints


def release_findings(report: dict, directory: Path, brief: SynthesisBrief, circuit_hash: str) -> list[str]:
    """Require real checks and recheck exact on-disk release lineage."""
    failures = []
    schematic, pcb, release = report["schematic"], report["pcb"], report["release"]
    if any(pcb.get(key) != value for key, value in current_pcb_policy().items()):
        failures.append("PCB compiler or local footprint geometry policy is stale")
    actual = canonical_artifacts(directory)
    if actual.get("circuit") != circuit_hash:
        failures.append("Final circuit differs from pre-run synthesis")
    if report["project"].get("placement_request_fingerprint") != actual.get("placement_request") or pcb.get("placement", {}).get("request_fingerprint") != actual.get("placement_request") or pcb.get("placement", {}).get("constraints_hash") != actual.get("placement_constraints") or pcb.get("placement", {}).get("algorithm") != actual.get("placement_algorithm"):
        failures.append("Reported placement metadata does not match retained request and solution")
    if report.get("mode") != "bounded_synthesis" or report["project"].get("brief_fingerprint") != brief.fingerprint or report["project"].get("circuit_hash") != circuit_hash:
        failures.append("Report does not bind the confirmed brief and circuit")
    if schematic.get("current") is not True or schematic.get("erc_status") not in {"PASS", "PASS_WITH_WARNINGS"}:
        failures.append("Schematic/ERC is not current and completed")
    if pcb.get("current") is not True or pcb.get("drc_status") != "PASS" or pcb.get("violations") != 0 or pcb.get("unrouted") != 0:
        failures.append("PCB did not reach current DRC 0/0")
    manufacturing = report["manufacturing"]["findings"]
    if not manufacturing or any(item.get("status") != "pass" for item in manufacturing):
        failures.append("Manufacturing profile is not an explicit PASS")
    if release.get("current") is not True or release.get("status") != "READY_FOR_MANUFACTURING_REVIEW":
        failures.append("Release is not current and ready for review")
    for filename, expected in (("golden.kicad_sch", schematic.get("fingerprint")),
                               ("golden.kicad_pcb", pcb.get("fingerprint")),
                               ("golden.placed.kicad_pcb", pcb.get("source_placed_pcb_fingerprint"))):
        if file_fingerprint(directory, filename) != expected:
            failures.append(f"Artifact hash mismatch: {filename}")
    erc = read_json(safe_file(directory, "erc-report.json"))
    drc = read_json(safe_file(directory, "drc-report.json"))
    if erc.get("tool_status") != "ok" or erc.get("return_code") not in (0, 5) or erc.get("status") not in {"pass", "pass_with_warnings"} or erc.get("artifact_fingerprint", {}).get("digest") != schematic.get("fingerprint"):
        failures.append("Raw ERC evidence is incomplete or stale")
    if drc.get("tool_status") != "ok" or drc.get("return_code") != 0 or drc.get("status") != "pass" or drc.get("findings") != [] or drc.get("unconnected_items") != [] or drc.get("pcb_fingerprint", {}).get("digest") != pcb.get("fingerprint"):
        failures.append("Raw DRC evidence is not complete 0/0 for this PCB")
    fab = directory / "fabrication"
    manifest_entry = release["manifest"]
    manifest_path = safe_file(fab, manifest_entry["relative_path"])
    if digest_bytes(manifest_path.read_bytes()) != manifest_entry["sha256"]:
        failures.append("Manifest file hash mismatch")
    manifest = read_json(manifest_path)
    plan = RoutingPlan.model_validate(read_json(safe_file(directory, "routing-plan.json")))
    bindings = {"circuit_fingerprint": circuit_hash, "schematic_fingerprint": schematic["fingerprint"],
                "pcb_fingerprint": pcb["fingerprint"], "routing_plan_fingerprint": plan.content_hash,
                "manufacturing_profile_fingerprint": prototype_profile().content_hash,
                "package_fingerprint": release["package_fingerprint"]}
    if any(manifest.get(key) != value for key, value in bindings.items()):
        failures.append("Fabrication manifest lineage mismatch")
    portable = {key: value for key, value in manifest.items() if key != "package_fingerprint"}
    if canonical_hash(portable) != release["package_fingerprint"] or release.get("pcb_fingerprint") != pcb["fingerprint"]:
        failures.append("Release/package content fingerprint mismatch")
    if manifest.get("files") != release["files"] or not release["files"]:
        failures.append("Fabrication file inventory mismatch")
    for entry in release["files"]:
        data = safe_file(fab, entry["relative_path"]).read_bytes()
        if not data or digest_bytes(data) != entry["sha256"] or len(data) != entry["size_bytes"]:
            failures.append(f"Fabrication bytes mismatch: {entry['relative_path']}")
    return failures


def raw_artifacts(directory: Path) -> dict:
    """Timestamped/path-bearing reports and fab bytes retained, never called reproducible."""
    return {path.relative_to(directory).as_posix(): digest_bytes(path.read_bytes())
            for path in sorted(directory.rglob("*")) if path.is_file() and not path.is_symlink()}


def application_refusal(brief, directory, progress, pipeline_factory) -> dict:
    """Exercise the application refusal, blocking and recording any EDA attempt."""
    calls = []

    def forbidden(*_args, **_kwargs):
        calls.append("downstream_eda")
        raise RuntimeError("A refused input attempted downstream EDA work")

    with ExitStack() as stack:
        for target in ("ohmni.application.projects.KiCadSchematicCompiler.compile",
                       "ohmni.eda.kicad.erc.run_tool",
                       "ohmni.manufacturing.exporter.run_tool", "ohmni.adapters.tools.run_tool"):
            stack.enter_context(patch(target, forbidden))
        try:
            pipeline_factory(progress=progress).run(directory / "refusal-application", brief)
        except ProjectRefusalError as exc:
            return {"refusal": exc.refusal.model_dump(mode="json"), "downstream_eda_calls": len(calls)}
    return {"refusal": None, "downstream_eda_calls": len(calls)}


def execute_attempt(case: dict, directory: Path, progress, pipeline_factory=ProjectPipeline) -> dict:
    brief = SynthesisBrief.model_validate(case["brief"])
    expected = case["expected"]
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "input.json", case["brief"])
    write_json(directory / "expected.json", expected)
    result = synthesize(brief)
    write_json(directory / "synthesis-result.json", result.model_dump(mode="json"))
    record = {"status": "FAIL", "issues": [], "canonical": {}, "brief_fingerprint": brief.fingerprint}
    if not result.accepted:
        record["refusal"] = result.refusal.model_dump(mode="json")
        record["canonical"]["refusal"] = canonical_hash(record["refusal"])
        application = application_refusal(brief, directory, progress, pipeline_factory)
        record["application_refusal"] = application
        write_json(directory / "application-refusal.json", application)
        if expected["outcome"] == "refused" and result.refusal.code.value == expected["refusal_code"] and application["refusal"] is not None and application["refusal"]["code"] == expected["refusal_code"] and application["downstream_eda_calls"] == 0:
            record["status"] = "PASS"
        else:
            record["issues"].append("Compiler/application refusal mismatch or downstream EDA attempted")
        return record
    circuit = result.circuit
    record["canonical"]["circuit"] = circuit.content_hash
    write_json(directory / "circuit.json", circuit.model_dump(mode="json"))
    if expected["outcome"] == "refused":
        record["issues"].append("Out-of-envelope request was accepted")
        return record
    record["issues"].extend(inventory_findings(circuit, expected))
    semantic = verify(circuit, default_catalog(), result.requirements)
    write_json(directory / "semantic-report.json", semantic.model_dump(mode="json"))
    record["semantic"] = {"coverage": semantic.coverage, "export_blocked": semantic.export_blocked}
    if semantic.export_blocked or semantic.coverage != 1:
        record["issues"].append("Semantic verification is blocked or incomplete")
    # Only the exact structured brief enters the product pipeline. No oracle data.
    report = pipeline_factory(progress=progress).run(directory, brief)
    report = report.model_dump(mode="json") if hasattr(report, "model_dump") else report
    write_json(directory / "report.json", report)
    record["issues"].extend(release_findings(report, directory, brief, circuit.content_hash))
    record["canonical"].update(canonical_artifacts(directory))
    if not set(CANONICAL_KEYS).issubset(record["canonical"]):
        record["issues"].append("A canonical artifact fingerprint is missing")
    record["quality_metrics"] = report["pcb"].get("quality_metrics")
    record["provenance"] = {"evidence_statuses": dict(Counter(str(item.get("status", "UNKNOWN")) for item in report["evidence"])),
                            "requirement_statuses": dict(Counter(item["status"] for item in report["requirements"])),
                            "manufacturing": report["manufacturing"], "limitations": report["limitations"]}
    record["status"] = "FAIL" if record["issues"] else "PASS"
    return record


def summarize(state: dict) -> dict:
    records = state["cases"]
    supported = [case for case in records if case["expected_outcome"] == "accepted"]
    refused = [case for case in records if case["expected_outcome"] == "refused" and case["group"] == "core"]
    safety = [case for case in records if case["group"] == "supplemental_safety"]
    first = lambda case: bool(case["attempts"]) and case["attempts"][0]["status"] == "PASS"
    all_pass = lambda case: len(case["attempts"]) == state["repetitions"] and all(item["status"] == "PASS" for item in case["attempts"])
    complete = len(records) == 110 and all(len(case["attempts"]) == state["repetitions"] and all(item["status"] in {"PASS", "FAIL"} for item in case["attempts"]) for case in records)
    gate = lambda passed: "NOT_EVALUATED" if not complete else "PASS" if passed else "FAIL"
    return {"fixed_in_envelope_denominator": 60, "fixed_refusal_denominator": 20,
            "fixed_supplemental_safety_denominator": 30,
            "selected_in_envelope": len(supported), "selected_refusals": len(refused),
            "fixed_unique_resolved_feature_topologies": 56,
            "selected_unique_resolved_feature_topologies": len({case["expected_topology_sha256"] for case in supported}),
            "first_attempt_successes": sum(map(first, supported)),
            "first_attempt_success_rate_of_60": sum(map(first, supported)) / 60,
            "all_attempt_successes": sum(map(all_pass, supported)),
            "specific_refusals_passing_all_attempts": sum(map(all_pass, refused)),
            "selected_supplemental_safety": len(safety),
            "supplemental_safety_passing_all_attempts": sum(map(all_pass, safety)),
            "reproducible_in_envelope": sum(case.get("reproducibility") == "PASS" for case in supported),
            "failed_attempts": sum(item["status"] in {"FAIL", "INTERRUPTED"} for case in records for item in case["attempts"]),
            "full_corpus_executed": complete,
            "end_to_end_90_percent_gate": gate(sum(map(first, supported)) >= 54),
            "core_specific_refusal_gate": gate(sum(map(all_pass, refused)) == 20),
            "supplemental_safety_gate": gate(sum(map(all_pass, safety)) == 30),
            "artifact_reproducibility_gate": "NOT_EVALUATED" if state["repetitions"] < 2 else gate(sum(case.get("reproducibility") == "PASS" for case in supported) == 60)}


def run_benchmark(corpus_path: Path, output: Path, *, case_ids=None, repetitions=2,
                  pipeline_factory=ProjectPipeline, environment_factory=environment,
                  source_factory=source_snapshot, safety_corpus_path=DEFAULT_SAFETY_CORPUS) -> dict:
    corpus = load_corpus(corpus_path)
    safety_corpus = load_safety_corpus(safety_corpus_path)
    combined = [{**case, "group": "core"} for case in corpus["cases"]] + [
        {**case, "group": "supplemental_safety"} for case in safety_corpus["cases"]]
    if isinstance(repetitions, bool) or repetitions not in (1, 2, 3):
        raise ValueError("Use one to three repetitions; one cannot establish reproducibility")
    selected = set(case_ids) if case_ids else {case["case_id"] for case in combined}
    if not selected.issubset({case["case_id"] for case in combined}):
        raise ValueError("Unknown case filter")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = source_factory()
    state = {"schema_version": 1, "started_at": now(), "status": "INITIALIZING",
             "corpus_sha256": digest_bytes(corpus_path.read_bytes()), "source": source,
             "supplemental_safety_sha256": digest_bytes(safety_corpus_path.read_bytes()),
             "repetitions": repetitions, "cases": [
                 {"case_id": case["case_id"], "family": case["brief"]["archetype"], "group": case["group"],
                  "input_sha256": case["input_sha256"], "expectation_sha256": case["expectation_sha256"],
                  "expected_topology_sha256": canonical_hash(case["expected"]),
                  "expected_outcome": case["expected"]["outcome"], "attempts": [], "reproducibility": "NOT_RUN"}
                 for case in combined if case["case_id"] in selected]}
    write_json(output / "corpus.json", corpus)
    write_json(output / "supplemental-safety-corpus.json", safety_corpus)

    def persist():
        state["summary"] = summarize(state)
        write_json(output / "results.json", state)

    persist()
    try:
        state["environment"] = environment_factory()
        state["status"] = "RUNNING"
        persist()
        cases = {case["case_id"]: case for case in combined}
        for record in state["cases"]:
            for repetition in range(1, repetitions + 1):
                if source_factory() != source or digest_bytes(corpus_path.read_bytes()) != state["corpus_sha256"] or digest_bytes(safety_corpus_path.read_bytes()) != state["supplemental_safety_sha256"]:
                    raise RuntimeError("Source or corpus changed during the run; start a fresh output directory")
                directory = output / record["case_id"] / f"attempt-{repetition}"
                attempt = {"number": repetition, "directory": directory.relative_to(output).as_posix(),
                           "status": "RUNNING", "started_at": now(), "progress": []}
                record["attempts"].append(attempt)
                persist()
                started = time.perf_counter()

                def progress(event, attempt=attempt):
                    attempt["progress"].append(event.model_dump(mode="json"))
                    persist()

                try:
                    attempt.update(execute_attempt(cases[record["case_id"]], directory, progress, pipeline_factory))
                except Exception as exc:  # noqa: BLE001 - retain unexpected failures as benchmark evidence
                    attempt.update(status="FAIL", error_type=type(exc).__name__, error=str(exc),
                                   error_code=str(getattr(exc, "code", "pipeline_failed")))
                    if directory.exists():
                        (directory / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")
                except BaseException:
                    attempt["status"] = "INTERRUPTED"
                    raise
                finally:
                    attempt["runtime_seconds"] = time.perf_counter() - started
                    attempt["finished_at"] = now()
                    if directory.exists():
                        try:
                            attempt.setdefault("canonical", {}).update(canonical_artifacts(directory))
                        except Exception as exc:  # noqa: BLE001 - malformed artifacts are retained failures
                            attempt["canonical_collection_error"] = f"{type(exc).__name__}: {exc}"
                            if attempt["status"] == "PASS":
                                attempt["status"] = "FAIL"
                        attempt["raw_artifact_sha256"] = raw_artifacts(directory)
                    persist()
                print(f"{record['case_id']} attempt {repetition}: {attempt['status']} ({attempt['runtime_seconds']:.2f}s)", flush=True)
            attempts = record["attempts"]
            if repetitions < 2:
                record["reproducibility"] = "NOT_MEASURED"
            elif any(attempt["status"] != "PASS" for attempt in attempts):
                record["reproducibility"] = "INCOMPLETE"
            else:
                record["reproducibility"] = "PASS" if all(item["canonical"] == attempts[0]["canonical"] for item in attempts[1:]) else "FAIL"
            persist()
        if source_factory() != source or digest_bytes(corpus_path.read_bytes()) != state["corpus_sha256"] or digest_bytes(safety_corpus_path.read_bytes()) != state["supplemental_safety_sha256"]:
            raise RuntimeError("Source or corpus changed during the run; start a fresh output directory")
        state["status"] = "COMPLETE"
    except BaseException as exc:
        state["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ABORTED"
        state["run_error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        state["finished_at"] = now()
        persist()
    return state


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, help="New directory; no overwrite or resume")
    parser.add_argument("--case", action="append", dest="case_ids", help="Exact case ID; repeat to select several")
    parser.add_argument("--repetitions", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--validate-corpus", action="store_true", help="Validate frozen inputs only; no EDA")
    args = parser.parse_args(argv)
    if args.validate_corpus:
        corpus = load_corpus(args.corpus)
        safety = load_safety_corpus()
        print(json.dumps({"corpus_sha256": CORPUS_SHA256, "cases": len(corpus["cases"]),
                          "denominators": corpus["denominators"], "supplemental_safety_cases": len(safety["cases"]),
                          "supplemental_safety_sha256": SAFETY_CORPUS_SHA256}, indent=2))
        return 0
    if args.output is None:
        parser.error("--output is required for execution")
    try:
        state = run_benchmark(args.corpus, args.output, case_ids=args.case_ids,
                              repetitions=args.repetitions)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI must preserve a nonzero failure exit
        print(f"Benchmark stopped: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(state["summary"], indent=2))
    return 0 if all(attempt["status"] == "PASS" for case in state["cases"] for attempt in case["attempts"]) and all(case["reproducibility"] != "FAIL" for case in state["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
