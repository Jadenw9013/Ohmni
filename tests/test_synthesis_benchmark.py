"""Pure benchmark oracle, accounting and failure-boundary checks; no native EDA."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from ohmni.application.projects import ProjectPipeline
from ohmni.catalog import default_catalog
from ohmni.domain import SafetyDomain
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.placement import generate_placement
from ohmni.routing.models import RoutingPlan, RoutingProfile, RoutingStatistics
from ohmni.synthesis import SynthesisBrief, synthesize

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark_synthesis", ROOT / "scripts/benchmark_synthesis.py")
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)
CORPUS = benchmark.load_corpus()
SAFETY = benchmark.load_safety_corpus()
ACCEPTED = [case for case in CORPUS["cases"] if case["expected"]["outcome"] == "accepted"]
REFUSED = [case for case in CORPUS["cases"] if case["expected"]["outcome"] == "refused"] + SAFETY["cases"]


def test_the_freeze_is_about_content_not_about_line_endings():
    """A CRLF checkout is the same corpus, and must be seen as the same corpus.

    Hashing the raw bytes made this repository's own CI fail on every commit it
    ever ran while passing on the machine that authored the constant: git stores
    these fixtures with LF, a Windows checkout materializes CRLF, and only one of
    those two byte strings could match.
    """
    lf = benchmark.DEFAULT_CORPUS.read_bytes().replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    assert benchmark.corpus_digest(lf) == benchmark.corpus_digest(crlf) == benchmark.CORPUS_SHA256
    assert json.loads(lf.decode("utf-8")) == json.loads(crlf.decode("utf-8"))
    # Generated artifacts keep their byte-exact digests: only the authored
    # corpora normalize, because there the content is the claim.
    assert benchmark.digest_bytes(b"a\r\nb") != benchmark.digest_bytes(b"a\nb")


def test_corpus_remains_frozen_and_contains_reported_failure():
    assert benchmark.corpus_digest(benchmark.DEFAULT_CORPUS.read_bytes()) == benchmark.CORPUS_SHA256
    assert (benchmark.corpus_digest(benchmark.DEFAULT_SAFETY_CORPUS.read_bytes())
            == benchmark.SAFETY_CORPUS_SHA256)
    assert len(ACCEPTED) == 60
    assert len(REFUSED) == 50
    case = next(case for case in ACCEPTED if case["case_id"] == "A1-20")
    assert [slot["part_id"] for slot in case["brief"]["sensors"]] == ["BME280", "BME280", "TMP102AIDRLR"]
    assert all(slot["address"] is None for slot in case["brief"]["sensors"])
    assert case["brief"]["status_led_count"] == 1
    assert case["brief"]["include_programming_header"] is True
    for family in {case["brief"]["archetype"] for case in ACCEPTED}:
        domain_cases = [case for case in SAFETY["cases"] if case["brief"]["archetype"] == family]
        assert {domain for case in domain_cases for domain in case["brief"]["safety_domains"]} == {item.value for item in SafetyDomain}
        assert any(case["brief"]["input_voltage_v"] > 12 for case in domain_cases)


@pytest.mark.parametrize("case", ACCEPTED, ids=lambda case: case["case_id"])
def test_frozen_composition_oracle_matches_typed_synthesis(case):
    result = synthesize(SynthesisBrief.model_validate(case["brief"]))
    assert result.accepted, result.refusal
    assert benchmark.inventory_findings(result.circuit, case["expected"]) == []


@pytest.mark.parametrize("case", REFUSED, ids=lambda case: case["case_id"])
def test_frozen_refusals_stop_compiler_and_application_before_eda(case, tmp_path):
    result = benchmark.execute_attempt(case, tmp_path / case["case_id"], lambda _event: None)
    if case["case_id"] == "R-18":
        # PCB-EXPLORER-1 deliberately adds the formerly refused optional A2
        # sensor. Preserve the frozen oracle and denominator: its runner must
        # report contract drift, never silently turn the old benchmark green.
        assert case["expected"] == {"outcome": "refused", "refusal_code": "peripheral_slots_unsupported"}
        assert result["status"] == "FAIL"
        assert result["issues"] == ["Out-of-envelope request was accepted"]
        assert "application_refusal" not in result
        assert not list(tmp_path.rglob("*.kicad_sch"))
        return
    assert result["status"] == "PASS", result
    assert result["application_refusal"]["refusal"]["code"] == case["expected"]["refusal_code"]
    assert result["application_refusal"]["downstream_eda_calls"] == 0
    assert not list(tmp_path.rglob("*.kicad_sch"))


def run_options(**changes):
    return {"case_ids": ["A1-01"], "environment_factory": lambda: {"test_only": True},
            "source_factory": lambda: {"sha256": "frozen-test-source", "files": {}}, **changes}


def test_incremental_results_retain_pipeline_failures_and_all_attempts(tmp_path):
    snapshots = []
    output = tmp_path / "run"

    class FailedPipeline:
        def __init__(self, progress):
            self.progress = progress

        def run(self, destination, brief):
            snapshot = benchmark.read_json(output / "results.json")
            snapshots.append(snapshot["cases"][0]["attempts"][-1]["status"])
            assert brief == SynthesisBrief.model_validate(ACCEPTED[0]["brief"])
            assert destination.is_relative_to(output)
            raise RuntimeError("Deliberate routing failure")

    state = benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, output,
                                    **run_options(pipeline_factory=FailedPipeline))
    assert snapshots == ["RUNNING", "RUNNING"]
    assert [item["status"] for item in state["cases"][0]["attempts"]] == ["FAIL", "FAIL"]
    assert state["summary"]["failed_attempts"] == 2
    assert state["summary"]["first_attempt_success_rate_of_60"] == 0
    assert state["cases"][0]["reproducibility"] == "INCOMPLETE"
    assert (output / "A1-01/attempt-1/exception.txt").is_file()
    assert (output / "A1-01/attempt-2/exception.txt").is_file()
    assert benchmark.read_json(output / "results.json")["status"] == "COMPLETE"


def test_later_success_does_not_erase_first_failure(tmp_path, monkeypatch):
    calls = 0

    def attempt(_case, directory, _progress, _factory):
        nonlocal calls
        calls += 1
        directory.mkdir(parents=True)
        if calls == 1:
            raise RuntimeError("First run failed")
        return {"status": "PASS", "canonical": {key: "a" * 64 for key in benchmark.CANONICAL_KEYS}}

    monkeypatch.setattr(benchmark, "execute_attempt", attempt)
    state = benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, tmp_path / "run", **run_options())
    assert state["summary"]["first_attempt_successes"] == 0
    assert state["summary"]["all_attempt_successes"] == 0
    assert state["summary"]["failed_attempts"] == 1
    assert state["cases"][0]["reproducibility"] == "INCOMPLETE"


def test_repeated_success_with_different_geometry_fails_reproducibility(tmp_path, monkeypatch):
    calls = 0

    def attempt(_case, directory, _progress, _factory):
        nonlocal calls
        calls += 1
        directory.mkdir(parents=True)
        canonical = {key: "a" * 64 for key in benchmark.CANONICAL_KEYS}
        canonical["pcb"] = str(calls) * 64
        return {"status": "PASS", "canonical": canonical}

    monkeypatch.setattr(benchmark, "execute_attempt", attempt)
    state = benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, tmp_path / "run", **run_options())
    assert state["summary"]["first_attempt_successes"] == 1
    assert state["summary"]["first_attempt_success_rate_of_60"] == 1 / 60
    assert state["summary"]["full_corpus_executed"] is False
    assert state["cases"][0]["reproducibility"] == "FAIL"


def test_source_changes_abort_with_retained_results(tmp_path):
    calls = 0

    def source():
        nonlocal calls
        calls += 1
        return {"sha256": str(calls), "files": {}}

    output = tmp_path / "run"
    with pytest.raises(RuntimeError, match="Source or corpus changed"):
        benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, output, **run_options(source_factory=source))
    state = benchmark.read_json(output / "results.json")
    assert state["status"] == "ABORTED"
    assert state["cases"][0]["attempts"] == []
    assert state["summary"]["fixed_in_envelope_denominator"] == 60


def test_no_overwrite_resume_or_unknown_case_filter(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "keep.json"
    sentinel.write_text("original")
    with pytest.raises(FileExistsError):
        benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, output, **run_options())
    assert sentinel.read_text() == "original"
    with pytest.raises(ValueError, match="Unknown case"):
        benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, tmp_path / "new", **run_options(case_ids=["made-up"]))
    assert not (tmp_path / "new").exists()


def test_edited_expectations_are_rejected_before_execution(tmp_path):
    corpus = json.loads(benchmark.DEFAULT_CORPUS.read_text())
    corpus["cases"][0]["expected"]["inventory"]["BME280"] = 9
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(corpus))
    with pytest.raises(ValueError, match="frozen benchmark"):
        benchmark.load_corpus(path)


def test_supplemental_accounting_never_changes_core_denominators(tmp_path):
    state = benchmark.run_benchmark(benchmark.DEFAULT_CORPUS, tmp_path / "run",
                                    **run_options(case_ids=["R-01", "S-A1-01"]))
    assert state["summary"]["specific_refusals_passing_all_attempts"] == 1
    assert state["summary"]["supplemental_safety_passing_all_attempts"] == 1
    assert state["summary"]["fixed_refusal_denominator"] == 20
    assert state["summary"]["fixed_supplemental_safety_denominator"] == 30


def test_application_refusal_canary_catches_ignored_refusal(tmp_path):
    class BrokenPipeline(ProjectPipeline):
        def run(self, destination, brief):
            from ohmni.eda.kicad import KiCadSchematicCompiler
            KiCadSchematicCompiler(default_catalog()).compile(None, destination / "bad.kicad_sch")

    with pytest.raises(RuntimeError, match="attempted downstream EDA"):
        benchmark.execute_attempt(REFUSED[0], tmp_path / "case", lambda _event: None, BrokenPipeline)
    assert not list(tmp_path.rglob("*.kicad_sch"))


@pytest.fixture
def canonical_directory(tmp_path):
    """Real pure compilers, no routed success or native verification is claimed."""
    directory = tmp_path / "canonical"
    directory.mkdir()
    result = synthesize(SynthesisBrief.model_validate(ACCEPTED[0]["brief"]))
    catalog = default_catalog()
    placement = generate_placement(result.circuit, result.placement_request, catalog)
    schematic = KiCadSchematicCompiler(catalog).compile(result.circuit, directory / "golden.kicad_sch")
    placed = KiCadPcbCompiler(catalog).compile(result.circuit, schematic, placement.board,
                                             directory / "golden.placed.kicad_pcb")
    plan = RoutingPlan(source_pcb_fingerprint=placed.fingerprint.digest, source_pcb_path=placed.path,
                       source_constraints_hash=placement.board.content_hash,
                       circuit_content_hash=result.circuit.content_hash, profile=RoutingProfile(),
                       routed_nets=[], events=list(schematic.events),
                       statistics=RoutingStatistics(required_connections=0, routed_net_count=0,
                           unresolved_net_count=0, track_segment_count=0, via_count=0,
                           total_track_length_mm=0, expanded_nodes=0, routing_attempts=0, route_order=[]))
    for name, model in (("circuit.json", result.circuit), ("placement-request.json", result.placement_request),
                        ("placement.json", placement), ("routing-plan.json", plan)):
        benchmark.write_json(directory / name, model.model_dump(mode="json"))
    return directory


def test_canonical_routing_normalizes_only_source_path_and_events(canonical_directory, tmp_path):
    first = benchmark.canonical_artifacts(canonical_directory)
    second = tmp_path / "other-attempt"
    shutil.copytree(canonical_directory, second)
    data = benchmark.read_json(second / "routing-plan.json")
    data["source_pcb_path"] = str(second / "golden.placed.kicad_pcb")
    data["events"] = []
    benchmark.write_json(second / "routing-plan.json", data)
    assert first == benchmark.canonical_artifacts(second)
    original_plan = RoutingPlan.model_validate(benchmark.read_json(canonical_directory / "routing-plan.json"))
    portable_plan = RoutingPlan.model_validate(data)
    assert original_plan.content_hash != portable_plan.content_hash
    data["statistics"]["total_track_length_mm"] = 1
    benchmark.write_json(second / "routing-plan.json", data)
    assert first["routing"] != benchmark.canonical_artifacts(second)["routing"]


@pytest.mark.parametrize("filename,field,value", [
    ("placement-request.json", "minimum_edge_clearance_mm", 1.5),
    ("placement.json", "request_fingerprint", "0" * 64),
    ("circuit.json", "constraints", []),
    ("routing-plan.json", "source_constraints_hash", "0" * 64),
])
def test_canonical_artifacts_reject_stale_request_and_lineage(canonical_directory, filename, field, value):
    benchmark.canonical_artifacts(canonical_directory)
    path = canonical_directory / filename
    data = benchmark.read_json(path)
    data[field] = value
    benchmark.write_json(path, data)
    with pytest.raises(ValueError, match="binding disagree|does not bind"):
        benchmark.canonical_artifacts(canonical_directory)


def test_canonical_placement_includes_algorithm(canonical_directory):
    original = benchmark.canonical_artifacts(canonical_directory)
    data = benchmark.read_json(canonical_directory / "placement.json")
    data["algorithm"] = "different-policy"
    benchmark.write_json(canonical_directory / "placement.json", data)
    changed = benchmark.canonical_artifacts(canonical_directory)
    assert original["placement"] != changed["placement"]
    assert changed["placement_algorithm"] == "different-policy"
