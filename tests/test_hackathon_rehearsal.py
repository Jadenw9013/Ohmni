"""Fresh evidence and child-process success are both required for readiness."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def runner():
    path = Path(__file__).resolve().parents[1] / "scripts/rehearse_hackathon.py"
    spec = importlib.util.spec_from_file_location("rehearse_hackathon", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_evidence_is_preserved(runner, tmp_path, monkeypatch):
    marker = tmp_path / "summary.json"
    marker.write_text("previous evidence")
    monkeypatch.setattr(runner, "run", lambda *args: pytest.fail("must not run checks"))
    assert runner.main(["--output", str(tmp_path)]) == 2
    assert marker.read_text() == "previous evidence"


@pytest.mark.parametrize("exit_code,expected", [(2, "BLOCKED"), (0, "FAIL")])
def test_blocked_or_empty_preflight_cannot_launch_build(runner, tmp_path, monkeypatch,
                                                     exit_code, expected):
    calls = []

    def child(command, env, log, timeout):
        calls.append(command)
        log.write_text('{}')
        return {"exit_code": exit_code, "timed_out": False}

    monkeypatch.setattr(runner, "run", child)
    output = tmp_path / "new-run"
    assert runner.main(["--output", str(output)]) != 0
    report = json.loads((output / "summary.json").read_text())
    assert report["status"] == expected
    assert [s["status"] for s in report["stages"]] == [expected, "NOT_RUN", "NOT_RUN"]
    assert len(calls) == 1
    assert report["live_fetch"] == "NOT_RUN"


def test_browser_bad_result_cannot_become_ready(runner):
    from scripts.rehearse_core_demo import FAMILIES, STEPS

    result = {"status": "PASS", "provider_calls": 0, "external_requests": 1,
              "page_errors": 0, "planner_recovery": True, "restart_recovery": True,
              "families": {family: dict.fromkeys(STEPS, True) for family in FAMILIES}}
    receipt = {"status": "PASS", "process": {"exit_code": 0, "timed_out": False},
               "result": result}
    assert not runner.receipt_passes("browser", receipt)
    result["external_requests"] = 0
    assert runner.receipt_passes("browser", receipt)
