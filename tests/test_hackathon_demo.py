"""Boundaries of the hackathon demonstration harness, fault and saved capture.

These pure tests use the committed saved run (real KiCad 10.0.5 receipts) and
mutated copies of it. They prove that a missing, stale, malformed or failing
receipt cannot qualify, that a missing checker blocks instead of passing, and
that the damaged copy never inherits the original board's evidence.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from ohmni.application import hackathon_demo as demo
from scripts import verify_hackathon_demo as harness

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "examples" / "hackathon-demo"
SAVED = CAPTURE / "saved-run"


@pytest.fixture
def run(tmp_path):
    copy = tmp_path / "run"
    shutil.copytree(SAVED, copy)
    shutil.rmtree(copy / demo.FAULT_DIRECTORY)
    return copy


def _edit(path: Path, change) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    path.write_text(json.dumps(value), encoding="utf-8")


def _failed(run_directory: Path) -> set[str]:
    return {check.name for check in demo.qualify_run(run_directory).checks if not check.passed}


def test_saved_capture_qualifies_from_its_own_receipts():
    result = demo.qualify_run(SAVED)
    assert result.passed, [check.as_dict() for check in result.checks if not check.passed]
    assert len(result.checks) == 14
    assert any("lib_symbol_issues" in warning for warning in result.warnings)


def test_empty_directory_never_qualifies(tmp_path):
    result = demo.qualify_run(tmp_path)
    assert not result.passed
    assert not demo.Qualification().passed


@pytest.mark.parametrize("mutation,failed", [
    (lambda run: (run / "drc-report.json").unlink(), "required_outputs_present"),
    (lambda run: (run / "golden.drc.json").write_text("", encoding="utf-8"), "required_outputs_present"),
    (lambda run: (run / "erc-report.json").write_text("{not json", encoding="utf-8"), "reports_parse"),
    (lambda run: _edit(run / "drc-report.json",
                       lambda v: v.update(status="unavailable", tool_status="unavailable")), "drc_completed"),
    (lambda run: _edit(run / "erc-report.json", lambda v: v.update(tool_status="failed")), "erc_completed"),
    (lambda run: _edit(run / "erc-report.json",
                       lambda v: v["findings"].append({"type": "pin_not_connected", "severity": "error"})),
     "erc_no_errors"),
    (lambda run: _edit(run / "golden.drc.json",
                       lambda v: v["unconnected_items"].append({"type": "unconnected_items"})),
     "drc_zero_findings"),
    (lambda run: (run / "golden.kicad_pcb").write_text(
        (run / "golden.kicad_pcb").read_text(encoding="utf-8") + "\n", encoding="utf-8"), "drc_bound_to_pcb"),
    (lambda run: (run / "golden.kicad_sch").write_text(
        (run / "golden.kicad_sch").read_text(encoding="utf-8") + "\n", encoding="utf-8"),
     "erc_bound_to_schematic"),
    (lambda run: _edit(run / "routing-plan.json",
                       lambda v: v["failures"].append({"net_name": "LED1_A"})), "routing_complete"),
    (lambda run: _edit(run / "routing-verification.json",
                       lambda v: v["findings"][0].update(status="fail")), "routing_independently_verified"),
    (lambda run: next((run / "fabrication").glob("*.gtl")).write_bytes(b"G04 tampered*"),
     "fabrication_package_intact"),
    (lambda run: next((run / "fabrication").glob("*.drl")).unlink(), "fabrication_package_intact"),
])
def test_missing_stale_or_failing_receipts_cannot_qualify(run, mutation, failed):
    mutation(run)
    assert failed in _failed(run)
    assert not demo.qualify_run(run).passed


def test_harness_blocks_without_kicad(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "find_kicad_cli", lambda: None)
    called = []
    monkeypatch.setattr(harness, "run_attempt", lambda *args, **kwargs: called.append(args))
    assert harness.main(["--attempts", "1", "--output-root", str(tmp_path)]) == 2
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text(encoding="utf-8"))
    assert summary["status"] == "BLOCKED" and summary["attempts"] == [] and not called


def test_harness_blocks_on_unpinned_kicad(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "find_kicad_cli", lambda: "/usr/bin/kicad-cli")
    monkeypatch.setattr(harness, "kicad_version", lambda executable: "9.0.4")
    monkeypatch.setattr(harness, "run_attempt", lambda *args, **kwargs: pytest.fail("must not run"))
    assert harness.main(["--attempts", "1", "--output-root", str(tmp_path)]) == 2


def test_attempt_without_every_required_check_is_not_a_pass(run):
    qualification = demo.qualify_run(run)
    assert qualification.passed
    attempt = demo.Attempt(run, qualification, {}, 0.0)
    assert not attempt.passed
    qualification.add("pipeline_completed", True, "")
    qualification.add("release_current", True, "")
    assert not attempt.passed
    for name in ("fault_detected_by_real_drc", "original_unchanged_after_fault"):
        qualification.add(name, True, "")
    assert attempt.passed


def test_pipeline_error_is_a_failed_attempt_not_a_pass(tmp_path):
    class Broken:
        def __init__(self, progress):
            self.progress = progress

        def run(self, destination, brief):
            raise RuntimeError("KiCad DRC checks did not pass")

    attempt = demo.run_attempt(tmp_path / "attempt", Broken)
    assert not attempt.qualification.passed and attempt.fault is None
    assert "pipeline_completed" in {c.name for c in attempt.qualification.checks if not c.passed}


def test_attempts_refuse_to_reuse_old_receipts(tmp_path):
    (tmp_path / "attempt").mkdir()
    (tmp_path / "attempt" / "drc-report.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        demo.run_attempt(tmp_path / "attempt", lambda progress: pytest.fail("must not run"))


def test_fault_snapshot_removes_exactly_one_identified_track(run, tmp_path):
    good = run / "golden.kicad_pcb"
    before = good.read_bytes()
    result = demo.build_fault_snapshot(good, tmp_path / "fault.kicad_pcb")
    assert good.read_bytes() == before
    damaged = (tmp_path / "fault.kicad_pcb").read_text(encoding="utf-8")
    good_lines, fault_lines = before.decode().split("\n"), damaged.split("\n")
    index = result["removed_segment"]["line_number"] - 1
    assert good_lines[:index] + good_lines[index + 1:] == fault_lines
    assert result["snapshot_sha256"] == hashlib.sha256(damaged.encode()).hexdigest() != result["source_pcb_sha256"]
    good_tracks = demo.snapshot_copper(before.decode())["tracks"]
    fault_tracks = demo.snapshot_copper(damaged)["tracks"]
    removed = [track for track in good_tracks if track not in fault_tracks]
    assert len(removed) == 1 and removed[0]["net_name"] == demo.FAULT_NET
    assert removed[0]["uuid"] == result["removed_segment"]["uuid"]
    with pytest.raises(demo.FaultDiagnosticError):
        demo.build_fault_snapshot(good, tmp_path / "fault.kicad_pcb")


def test_fault_refuses_a_board_without_the_named_net(tmp_path):
    board = tmp_path / "board.kicad_pcb"
    board.write_text('(kicad_pcb\n  (net 1 "GND")\n)\n', encoding="utf-8")
    with pytest.raises(demo.FaultDiagnosticError):
        demo.build_fault_snapshot(board, tmp_path / "fault.kicad_pcb")


def test_missing_checker_fails_the_fault_gate(run, monkeypatch):
    monkeypatch.setattr("ohmni.adapters.tools.find_kicad_cli", lambda: None)
    qualification = demo.qualify_run(run)
    assert qualification.passed
    assert demo.check_fault(run, qualification) is None
    assert not qualification.passed
    assert "fault_detected_by_real_drc" in {c.name for c in qualification.checks if not c.passed}


def _saved_fault_with(change):
    fault = json.loads((SAVED / "fault" / demo.FAULT_RESULT).read_text(encoding="utf-8"))
    change(fault)
    return fault


def test_fault_gate_requires_the_cut_net_in_the_drc_receipt(run, monkeypatch):
    def elsewhere(fault):
        for finding in fault["drc"]["unconnected_items"]:
            for item in finding["items"]:
                item["description"] = item["description"].replace("[LED1_A]", "[GND]")
    monkeypatch.setattr(demo, "run_fault_diagnostic", lambda _run: _saved_fault_with(elsewhere))
    qualification = demo.qualify_run(run)
    demo.check_fault(run, qualification)
    assert "fault_detected_by_real_drc" in {c.name for c in qualification.checks if not c.passed}


def test_fault_gate_ignores_excluded_or_warning_items(run, monkeypatch):
    def excluded(fault):
        for finding in fault["drc"]["unconnected_items"]:
            finding["excluded"] = True
    monkeypatch.setattr(demo, "run_fault_diagnostic", lambda _run: _saved_fault_with(excluded))
    qualification = demo.qualify_run(run)
    demo.check_fault(run, qualification)
    assert "fault_detected_by_real_drc" in {c.name for c in qualification.checks if not c.passed}


def test_fault_checker_timeout_fails_without_crashing(run, monkeypatch):
    import subprocess

    def hang(_run):
        raise subprocess.TimeoutExpired(["kicad-cli"], 1)
    monkeypatch.setattr(demo, "run_fault_diagnostic", hang)
    qualification = demo.qualify_run(run)
    assert demo.check_fault(run, qualification) is None
    assert "fault_detected_by_real_drc" in {c.name for c in qualification.checks if not c.passed}


def test_saved_fault_passes_the_net_bound_gate(run, monkeypatch):
    monkeypatch.setattr(demo, "run_fault_diagnostic", lambda _run: _saved_fault_with(lambda _f: None))
    qualification = demo.qualify_run(run)
    demo.check_fault(run, qualification)
    assert qualification.passed


def test_saved_fault_receipt_is_a_real_unconnected_finding():
    fault = json.loads((SAVED / "fault" / demo.FAULT_RESULT).read_text(encoding="utf-8"))
    raw = SAVED / "fault" / demo.FAULT_RAW_DRC
    snapshot = SAVED / "fault" / demo.FAULT_PCB
    assert fault["kind"] == "diagnostic_fault_only" and fault["releasable"] is False
    assert fault["fault_detected"] is True and fault["drc"]["status"] == "fail"
    assert demo.sha256_file(raw) == fault["raw_drc_sha256"]
    assert demo.sha256_file(snapshot) == fault["snapshot_sha256"]
    assert fault["source_pcb_sha256"] == demo.sha256_file(SAVED / "golden.kicad_pcb")
    receipt = json.loads(raw.read_text(encoding="utf-8"))
    assert receipt["kicad_version"] == fault["checker"]["kicad_version"] == "10.0.5"
    assert [item["type"] for item in receipt["unconnected_items"]] == ["unconnected_items"]
    assert any("D1" in item["description"] and "LED1_A" in item["description"]
               for item in receipt["unconnected_items"][0]["items"])
    assert set(fault["not_checked"]) >= {"schematic_erc", "manufacturing_profile", "fabrication_export"}


def test_saved_demo_keeps_good_and_damaged_evidence_separate():
    data = json.loads((CAPTURE / "demo.json").read_text(encoding="utf-8"))
    good, fault = data["good"], data["fault"]
    assert data["label"] == "Saved successful run" and "Nothing on this page is generated" in data["notice"]
    assert good["board"]["artifact_fingerprint"] == demo.sha256_file(SAVED / "golden.kicad_pcb")
    assert fault["board"]["artifact_fingerprint"] == fault["snapshot_sha256"] != good["board"]["artifact_fingerprint"]
    assert good["checks"]["drc"]["status"] == "pass" and good["checks"]["drc"]["unconnected_count"] == 0
    assert fault["drc"]["unconnected_count"] >= 1 and "checks" not in fault and fault["releasable"] is False
    snapshot = demo.snapshot_copper((SAVED / "fault" / demo.FAULT_PCB).read_text(encoding="utf-8"))
    displayed = sorted(json.dumps(track, sort_keys=True) for track in fault["board"]["tracks"])
    derived = sorted(json.dumps({k: v for k, v in track.items() if k != "uuid"}, sort_keys=True)
                     for track in snapshot["tracks"])
    assert displayed == derived and len(fault["board"]["tracks"]) == len(good["board"]["tracks"]) - 1
    assert hashlib.sha256((CAPTURE / data["download"]["href"]).read_bytes()).hexdigest() == data["download"]["sha256"]
    summary = json.loads((CAPTURE / "harness-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "PASS" and summary["attempts_requested"] == 3
    assert all(item["status"] == "PASS" for item in summary["attempts"])
    assert data["capture"]["git_commit"] == summary["git"]["commit"] and summary["git"]["dirty"] is False


@pytest.mark.kicad
@pytest.mark.slow_integration
def test_fresh_attempt_qualifies_and_its_fault_fails_real_drc(tmp_path):
    from ohmni.adapters.tools import find_kicad_cli
    if find_kicad_cli() is None:
        pytest.skip("KiCad CLI unavailable")
    from ohmni.application.projects import ProjectPipeline
    attempt = demo.run_attempt(tmp_path / "attempt", ProjectPipeline)
    failed = [check.as_dict() for check in attempt.qualification.checks if not check.passed]
    assert attempt.qualification.passed, failed
    assert attempt.passed and demo.REQUIRED_CHECKS <= {c.name for c in attempt.qualification.checks}
    names = {check.name for check in attempt.qualification.checks}
    assert {"fault_detected_by_real_drc", "original_unchanged_after_fault", "release_current"} <= names
    assert attempt.fault["drc"]["unconnected_count"] >= 1 and attempt.fault["releasable"] is False


def test_offline_server_serves_only_contained_allowlisted_files():
    from scripts.serve_offline_demo import CAPTURE as served
    from scripts.serve_offline_demo import WEB, resolve
    assert resolve("/") == WEB / "hackathon-demo.html"
    assert resolve("/board-view.js") == WEB / "board-view.js"
    assert resolve("/hackathon-demo/demo.json") == served / "demo.json"
    assert resolve("/hackathon-demo/saved-run/fault/diagnostic-fault.kicad_pcb") is not None
    for path in ("/../pyproject.toml", "/hackathon-demo/../../pyproject.toml", "/%2e%2e/pyproject.toml",
                 "/tests/hackathon-demo.test.mjs", "/.git/config", "/hackathon-demo/missing.json",
                 "/package-lock.json/x", "/hackathon-demo/..%2f..%2fpyproject.toml", "/a\\b"):
        assert resolve(path) is None, path


def test_offline_server_answers_without_any_api(tmp_path):
    import threading
    from urllib.error import HTTPError
    from urllib.request import ProxyHandler, build_opener

    from scripts.serve_offline_demo import make_server
    server = make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    opener = build_opener(ProxyHandler({}))
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with opener.open(base + "/hackathon-demo/demo.json", timeout=10) as response:
            assert response.headers["Cache-Control"] == "no-store"
            assert json.loads(response.read())["kind"] == "saved_hackathon_demonstration"
        for path in ("/api/projects", "/health", "/api/assistant"):
            with pytest.raises(HTTPError) as error:
                opener.open(base + path, timeout=10)
            assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
