"""Pure tests for the browser acceptance gate: nothing incomplete may pass."""

from __future__ import annotations

import copy
import ctypes
import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from scripts import run_browser_acceptance as gate

OK = {"exit_code": 0, "timed_out": False, "seconds": 1.0}
# The report contract is deliberate, not a fixture derived from the evaluator.
COMMON_SMOKE_CHECKS = {"no_external_request", "no_uncaught_page_error", "app_flow_unchanged",
                       "only_event_and_transaction_items", "canary_absent_from_envelopes", "state"}
EXPECTED_SMOKE_CHECKS = {
    "disabled": COMMON_SMOKE_CHECKS | {"bundle_not_requested", "no_envelopes", "no_trace_headers"},
    "missing_bundle": COMMON_SMOKE_CHECKS | {"no_envelopes", "no_trace_headers"},
    "enabled": COMMON_SMOKE_CHECKS | {"browser_request_transactions", "independent_actions_have_distinct_traces",
                                     "one_owned_transport_issue", "trace_headers_only_on_traced_posts",
                                     "headers_match_browser_spans", "server_continues_browser_trace"},
}


def demo_report(mode: str) -> dict:
    names = list(gate.COMMON_STEPS + gate.MODE_STEPS[mode])
    return {"status": "PASS", "host_mode": mode, "browser_version": "141", "external_requests": [],
            "failed_requests": [], "page_errors": [], "steps": [{"step": name, "status": "PASS"} for name in names]}


def smoke_summary() -> dict:
    scenarios = []
    for hosting, mode in sorted(gate.SMOKE_SCENARIOS):
        checks = {name: True for name in EXPECTED_SMOKE_CHECKS[mode]}
        items = ([{"type": "transaction", "name": name} for name in
                  ("POST /api/brief", "POST /api/demo", "POST /api/project-plans", "POST /api/demo", "POST /api/brief")]
                 + [{"type": "event", "value": "browser.project_request.transport_unreachable"}]) if mode == "enabled" else []
        scenarios.append({"hosting": hosting, "mode": mode, "checks": checks, "passed": True,
                          "telemetry_state": "unavailable" if mode == "missing_bundle" else mode,
                          "envelope_items": items})
    return {"status": "PASS", "browser": "chromium 141", "sdk": {}, "scenarios": scenarios}


def test_complete_reports_pass():
    for mode in gate.DEMO_MODES:
        assert gate.evaluate_demo(mode, demo_report(mode), OK)["status"] == "PASS"
    assert gate.evaluate_smoke(smoke_summary(), OK)["status"] == "PASS"
    assert gate.evaluate_pytest("6 passed in 3.2s", OK)["status"] == "PASS"


def test_saved_demo_failures_cannot_pass():
    cases = {
        "missing report": None,
        "fail status": {**demo_report("site"), "status": "FAIL"},
        "zero steps": {**demo_report("site"), "steps": []},
        "other mode": {**demo_report("offline"), "host_mode": "site"},
        "page error": {**demo_report("site"), "page_errors": ["TypeError"]},
        "external": {**demo_report("site"), "external_requests": ["https://x.invalid/"]},
    }
    failed_step = demo_report("site")
    failed_step["steps"][3]["status"] = "FAIL"
    cases["failed step"] = failed_step
    missing_step = demo_report("site")
    missing_step["steps"] = [s for s in missing_step["steps"] if s["step"] != "cold 320px original: no page overflow"]
    cases["missing overflow step"] = missing_step
    for name, report in cases.items():
        assert gate.evaluate_demo("site", report, OK)["status"] == "FAIL", name
    for process in ({**OK, "exit_code": 1}, {**OK, "timed_out": True, "exit_code": None}):
        assert gate.evaluate_demo("site", demo_report("site"), process)["status"] == "FAIL"


def test_every_width_keeps_its_overflow_assertion():
    for width in gate.WIDTHS:
        assert f"cold {width}px original: no page overflow" in gate.COMMON_STEPS
        assert f"resize to {width}px original: no page overflow" in gate.COMMON_STEPS


def test_smoke_blocked_missing_or_skipped_scenarios_cannot_pass():
    assert gate.evaluate_smoke(None, {**OK, "exit_code": 2})["status"] == "FAIL"
    result = gate.evaluate_smoke(smoke_summary(), {**OK, "exit_code": 2})
    assert result["status"] == "FAIL" and any("BLOCKED" in p for p in result["problems"])
    dropped = smoke_summary()
    dropped["scenarios"] = dropped["scenarios"][:5]
    assert gate.evaluate_smoke(dropped, OK)["status"] == "FAIL"
    hollow = smoke_summary()
    hollow["scenarios"][0]["checks"] = {}
    assert gate.evaluate_smoke(hollow, OK)["status"] == "FAIL"
    falsy = smoke_summary()
    first = next(iter(falsy["scenarios"][2]["checks"]))
    falsy["scenarios"][2]["checks"][first] = False
    assert gate.evaluate_smoke(falsy, OK)["status"] == "FAIL"
    duplicate = smoke_summary()
    duplicate["scenarios"][5] = copy.deepcopy(duplicate["scenarios"][0])
    assert gate.evaluate_smoke(duplicate, OK)["status"] == "FAIL"


def test_pytest_skips_errors_or_empty_runs_fail():
    for tail in ("5 passed, 1 skipped in 2s", "1 failed, 5 passed in 2s", "no tests ran in 0.1s",
                 "6 passed, 1 error in 2s", "1 passed, 5 xfailed in 2s", "1 passed, 5 xpassed in 2s",
                 "1 passed, 5 deselected in 2s", ""):
        assert gate.evaluate_pytest(tail, OK)["status"] == "FAIL", tail
    assert gate.evaluate_pytest("6 passed in 2s", {**OK, "exit_code": 1})["status"] == "FAIL"


def test_smoke_requires_named_checks_and_mode_consistent_evidence():
    for index in range(6):
        for name in EXPECTED_SMOKE_CHECKS[smoke_summary()["scenarios"][index]["mode"]]:
            report = smoke_summary()
            checks = report["scenarios"][index]["checks"]
            del checks[name]
            checks["unrelated_passing_check"] = True  # Counts alone must not pass.
            assert gate.evaluate_smoke(report, OK)["status"] == "FAIL", name
        wrong_state = smoke_summary()
        wrong_state["scenarios"][index]["telemetry_state"] = "other"
        assert gate.evaluate_smoke(wrong_state, OK)["status"] == "FAIL"
        missing_evidence = smoke_summary()
        del missing_evidence["scenarios"][index]["envelope_items"]
        assert gate.evaluate_smoke(missing_evidence, OK)["status"] == "FAIL"
        wrong_evidence = smoke_summary()
        scenario = wrong_evidence["scenarios"][index]
        scenario["envelope_items"] = [] if scenario["mode"] == "enabled" else [{"type": "event"}]
        assert gate.evaluate_smoke(wrong_evidence, OK)["status"] == "FAIL"
    wrong_issue = smoke_summary()
    enabled = next(item for item in wrong_issue["scenarios"] if item["mode"] == "enabled")
    enabled["envelope_items"][-1]["value"] = "wrong.owner"
    assert gate.evaluate_smoke(wrong_issue, OK)["status"] == "FAIL"


def test_smoke_named_contract_stays_aligned_with_the_real_checker():
    import ast

    tree = ast.parse((gate.ROOT / "scripts" / "smoke_browser_telemetry.py").read_text(encoding="utf-8"))
    emitted = {node.slice.value for node in ast.walk(tree)
               if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
               and node.value.id == "checks" and isinstance(node.ctx, ast.Store)
               and isinstance(node.slice, ast.Constant)}
    assert gate.SMOKE_CHECKS == EXPECTED_SMOKE_CHECKS
    assert emitted == set.union(*EXPECTED_SMOKE_CHECKS.values())


def _process_alive(pid: int) -> bool:
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_int
        handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
        if not handle:
            if ctypes.get_last_error() == 87:  # No process with this PID.
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            state = kernel.WaitForSingleObject(handle, 0)
            assert state in (0, 258), state  # WAIT_OBJECT_0 or WAIT_TIMEOUT
            return state == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A killed orphan can remain a zombie until Linux's init reaps it.
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return sys.platform != "linux"


@pytest.mark.parametrize("mode", ["normal", "nonzero", "timeout"])
def test_run_removes_real_descendants_on_every_exit(tmp_path, mode):
    ready = tmp_path / "descendant.json"
    descendant = (
        "import json, os, pathlib, sys, time\n"
        "pathlib.Path(sys.argv[1]).write_text(json.dumps({'pid': os.getpid()}))\n"
        "while True: time.sleep(1)\n"
    )
    command = (
        "import pathlib, subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {descendant!r}, sys.argv[1]])\n"
        "deadline = time.monotonic() + 5\n"
        "while not pathlib.Path(sys.argv[1]).exists():\n"
        "    if time.monotonic() > deadline: sys.exit(3)\n"
        "    time.sleep(0.01)\n"
        "print('descendant ready', flush=True)\n"
        "if sys.argv[2] == 'timeout': time.sleep(60)\n"
        "sys.exit(7 if sys.argv[2] == 'nonzero' else 0)\n"
    )
    env, _ = gate.scrubbed_environment(dict(os.environ))
    started = time.monotonic()
    try:
        result = gate.run([sys.executable, "-c", command, str(ready), mode], env, tmp_path / "run.log", timeout=3)
        assert time.monotonic() - started < 12
        assert ready.exists(), "The test must start a real descendant before checking cleanup."
        state = json.loads(ready.read_text())
        deadline = time.monotonic() + 3
        while _process_alive(state["pid"]) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not _process_alive(state["pid"]), "Checker left its descendant running."
        assert result["timed_out"] is (mode == "timeout")
        assert result["exit_code"] == {"normal": 0, "nonzero": 7, "timeout": None}[mode]
        assert "descendant ready" in (tmp_path / "run.log").read_text()
    finally:
        # A broken cleanup implementation must not leak the test's own process.
        if ready.exists():
            state = json.loads(ready.read_text())
            if _process_alive(state["pid"]):
                os.kill(state["pid"], signal.SIGTERM)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object assignment contract")
def test_windows_failed_job_assignment_never_starts_the_checker(tmp_path, monkeypatch):
    ran = tmp_path / "must-not-exist"
    launches = []
    popen = gate.subprocess.Popen

    def record_launch(command, **kwargs):
        launches.append(command)
        return popen(command, **kwargs)

    def cannot_assign(self, process):
        raise OSError("synthetic job assignment failure")

    monkeypatch.setattr(gate._WindowsJob, "assign", cannot_assign)
    monkeypatch.setattr(gate.subprocess, "Popen", record_launch)
    with pytest.raises(OSError, match="synthetic job assignment failure"):
        gate.run([sys.executable, "-c", "import pathlib, sys; pathlib.Path(sys.argv[1]).touch()", str(ran)],
                 gate.scrubbed_environment(dict(os.environ))[0], tmp_path / "assignment.log", timeout=3)
    assert not ran.exists()
    assert launches[0][0] == sys._base_executable


def test_inherited_telemetry_and_provider_settings_are_removed_without_values():
    env, removed = gate.scrubbed_environment({
        "PATH": "/bin", "SENTRY_DSN": "https://secret@o1.ingest.sentry.io/1", "SENTRY_RELEASE": "x",
        "OHMNI_TELEMETRY_ENABLED": "1", "OHMNI_TRACE_SAMPLE_RATE": "1", "ANTHROPIC_API_KEY": "sk-secret",
        "OHMNI_ENV": "production", "HOME": "/home/u",
    })
    assert env["PATH"] == "/bin" and env["HOME"] == "/home/u"
    assert not any(name.startswith(("SENTRY_", "OHMNI_TELEMETRY_")) for name in env)
    assert "ANTHROPIC_API_KEY" not in env and "OHMNI_ENV" not in env
    assert removed == sorted(["ANTHROPIC_API_KEY", "OHMNI_ENV", "OHMNI_TELEMETRY_ENABLED",
                              "OHMNI_TRACE_SAMPLE_RATE", "SENTRY_DSN", "SENTRY_RELEASE"])
    assert all("secret" not in name for name in removed)


def test_ci_runs_the_browser_gate_with_a_pinned_playwright():
    import tomllib
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["browser-acceptance"]
    assert "continue-on-error" not in job
    runs = [step.get("run", "") for step in job["steps"]]
    assert any('pip install -e ".[dev,browser]"' in run for run in runs)
    assert any("playwright install --with-deps chromium" in run for run in runs)
    assert any(run.strip() == "python scripts/run_browser_acceptance.py --output build/browser-acceptance" for run in runs)
    assert all("continue-on-error" not in step for step in job["steps"])
    extras = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]
    assert extras["browser"] == ["playwright==1.56.0"]
    # The existing gates stay in place beside it.
    assert {"fast", "corpus", "frontend", "kicad-gate"} <= set(workflow["jobs"])
