"""Pure tests for the browser acceptance gate: nothing incomplete may pass."""

from __future__ import annotations

import copy

from scripts import run_browser_acceptance as gate

OK = {"exit_code": 0, "timed_out": False, "seconds": 1.0}


def demo_report(mode: str) -> dict:
    names = list(gate.COMMON_STEPS + gate.MODE_STEPS[mode])
    return {"status": "PASS", "host_mode": mode, "browser_version": "141", "external_requests": [],
            "failed_requests": [], "page_errors": [], "steps": [{"step": name, "status": "PASS"} for name in names]}


def smoke_summary() -> dict:
    scenarios = []
    for hosting, mode in sorted(gate.SMOKE_SCENARIOS):
        checks = {f"check_{index}": True for index in range(gate.MIN_SMOKE_CHECKS[mode])}
        scenarios.append({"hosting": hosting, "mode": mode, "checks": checks, "passed": True,
                          "telemetry_state": "enabled", "envelope_items": []})
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
                 "6 passed, 1 error in 2s", ""):
        assert gate.evaluate_pytest(tail, OK)["status"] == "FAIL", tail
    assert gate.evaluate_pytest("6 passed in 2s", {**OK, "exit_code": 1})["status"] == "FAIL"


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
