#!/usr/bin/env python3
"""Run and gate every real-browser acceptance check, offline.

    python scripts/run_browser_acceptance.py [--output build/browser-acceptance]

Runs, one at a time, each in its own process group with a deadline:

* scripts/browser_check_offline_demo.py for the offline, site and static hosts;
* scripts/smoke_browser_telemetry.py (disabled, enabled and missing bundle under
  local and static hosting: six scenarios);
* tests/test_browser_acceptance.py with OHMNI_REQUIRE_BROWSER=1, so a missing
  browser fails instead of skipping.

Children get a scrubbed environment: inherited Sentry, telemetry and AI provider
variables are removed (only their names are reported, never values). The
checkers themselves deny every non-local browser request and use synthetic
telemetry configuration with recording transports.

The gate passes only when every expected mode and scenario reported PASS with
its required checks present and nonzero counts. A missing report, missing
Playwright or Chromium (BLOCKED), a skipped scenario or test, a timeout, or a
FAIL is a failure. Writes a sanitized summary.json (names, counts, statuses and
versions; no envelopes, URLs or bodies). Exit 0 only on a full pass.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_MODES = ("offline", "site", "static")
SMOKE_SCENARIOS = frozenset((hosting, mode) for hosting in ("local", "static")
                            for mode in ("disabled", "enabled", "missing_bundle"))
WIDTHS = (390, 375, 320)
STEP_TIMEOUT_S = 600

# Variables a developer or CI runner could inherit that would point a child at
# a real account or provider. They are removed, never printed.
SCRUB_PREFIXES = ("SENTRY_", "OHMNI_TELEMETRY_")
SCRUB_NAMES = frozenset({"OHMNI_ENV", "OHMNI_TRACE_SAMPLE_RATE", "ANTHROPIC_API_KEY", "OHMNI_ANTHROPIC_MODEL",
                         "OHMNI_API_BASE", "ALLOWED_ORIGINS"})

COMMON_STEPS = (
    "original board loads from local saved files",
    "saved-run label is visible",
    "desktop cold load: no page overflow",
    "local package downloads with recorded hash",
    "fault shows its own DRC failure (round 1)",
    "restore returns the original (round 1)",
    "fault shows its own DRC failure (round 2)",
    "restore returns the original (round 2)",
    "board controls are disabled while the file is pending",
    "late fault response cannot replace the original",
    "missing demo metadata leaves controls disabled and offers recovery",
    "reload recovers once saved metadata is available",
    "desktop keyboard: Tab reaches Show fault and Space shows the fault",
    "desktop keyboard: Tab reaches Restore original and Enter restores with focus kept",
    *(f"resize to {width}px original: board layers match the board size" for width in WIDTHS),
    *(f"resize to {width}px original: no page overflow" for width in WIDTHS),
    f"{WIDTHS[-1]}px fault: no page overflow",
    f"{WIDTHS[-1]}px restored: no page overflow",
    "resize back to desktop with fault shown: no page overflow",
    f"resize to {WIDTHS[0]}px with fault shown: no page overflow",
    *(f"cold {width}px original: board layers match the board size" for width in WIDTHS),
    *(f"cold {width}px original: no page overflow" for width in WIDTHS),
    *(f"cold {width}px keyboard: Tab reaches Show fault and Space shows the fault" for width in WIDTHS),
    *(f"cold {width}px keyboard: Tab reaches Restore original and Enter restores with focus kept" for width in WIDTHS),
    *(f"cold {width}px: package downloads with recorded hash" for width in WIDTHS),
    f"cold {WIDTHS[-1]}px: recovery control is visible and within the screen",
    f"cold {WIDTHS[-1]}px: unavailable state has no page overflow",
    f"cold {WIDTHS[-1]}px: recovery reload shows the original again",
    "no external request was attempted",
    "no unexpected local request failed",
    "no page errors",
)
MODE_STEPS = {
    "offline": ("offline host hides unavailable site navigation",),
    "site": ("landing demo opens separately and preserves the seeded unsaved draft",
             "workspace demo link also preserves the seeded unsaved draft", "hosted demo has site navigation"),
    "static": ("landing demo opens separately and preserves the seeded unsaved draft",
               "workspace demo link also preserves the seeded unsaved draft", "hosted demo has site navigation"),
}
_SMOKE_COMMON = frozenset({"no_external_request", "no_uncaught_page_error", "app_flow_unchanged",
                           "only_event_and_transaction_items", "canary_absent_from_envelopes", "state"})
SMOKE_CHECKS = {
    "disabled": _SMOKE_COMMON | {"bundle_not_requested", "no_envelopes", "no_trace_headers"},
    "missing_bundle": _SMOKE_COMMON | {"no_envelopes", "no_trace_headers"},
    "enabled": _SMOKE_COMMON | {"browser_request_transactions", "independent_actions_have_distinct_traces",
                                "one_owned_transport_issue", "trace_headers_only_on_traced_posts",
                                "headers_match_browser_spans", "server_continues_browser_trace"},
}
_SMOKE_TRANSACTIONS = ["POST /api/brief", "POST /api/brief", "POST /api/demo", "POST /api/demo",
                       "POST /api/project-plans"]

# On Windows the launcher cannot spawn the checker until it belongs to our job.
# Assigning an already-running checker would leave a race for unowned descendants.
_WINDOWS_LAUNCHER = (
    "import subprocess, sys\n"
    "if sys.stdin.buffer.read(1) != b'!':\n"
    "    sys.exit(125)\n"
    "sys.exit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL))\n"
)


class _WindowsJob:
    """Own an entire subprocess tree, including children left after normal exit."""

    def __init__(self) -> None:
        class BasicLimits(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", ctypes.c_uint32), ("min_working_set", ctypes.c_size_t),
                        ("max_working_set", ctypes.c_size_t), ("active_processes", ctypes.c_uint32),
                        ("affinity", ctypes.c_size_t), ("priority", ctypes.c_uint32),
                        ("scheduling", ctypes.c_uint32)]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("basic", BasicLimits), ("io", IoCounters),
                        ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                        ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]

        kernel = self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        kernel.CreateJobObjectW.restype = ctypes.c_void_p
        kernel.SetInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        kernel.SetInformationJobObject.restype = ctypes.c_int
        kernel.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel.AssignProcessToJobObject.restype = ctypes.c_int
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_int
        self.handle = kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process: subprocess.Popen) -> None:
        if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self.handle:
            if not self.kernel.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.handle = None


def scrubbed_environment(environ: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    removed = sorted(name for name in environ if name.startswith(SCRUB_PREFIXES) or name in SCRUB_NAMES)
    env = {name: value for name, value in environ.items() if name not in removed}
    env["PYTHONUNBUFFERED"] = "1"
    return env, removed


def run(command: list[str], env: dict[str, str], log: Path, timeout: float = STEP_TIMEOUT_S) -> dict:
    """Run one checker with a deadline and clean up its tree on every exit path."""
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as handle:
        process = None
        job = _WindowsJob() if os.name == "nt" else None
        try:
            if job:
                # A Windows venv executable can spawn a redirector child before
                # Python runs. The base interpreter has no such pre-job child;
                # the actual checker still uses the requested venv command.
                process = subprocess.Popen([sys._base_executable, "-c", _WINDOWS_LAUNCHER, *command], cwd=ROOT,
                                           env=env, stdin=subprocess.PIPE, stdout=handle, stderr=subprocess.STDOUT)
                job.assign(process)
                process.stdin.write(b"!")
                process.stdin.flush()
                process.stdin.close()
            else:
                process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                           start_new_session=True)
            code = process.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            code = None
        finally:
            if job:
                job.close()
            if process is not None:
                if os.name == "nt":
                    # Also covers a launcher whose job assignment failed before release.
                    if process.poll() is None:
                        process.kill()
                    if process.stdin and not process.stdin.closed:
                        process.stdin.close()
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                # Cleanup failure is a gate failure, never an unbounded wait or PASS.
                process.wait(timeout=5)
    return {"exit_code": code, "timed_out": timed_out, "seconds": round(time.monotonic() - started, 1)}


def evaluate_demo(mode: str, report: dict | None, process: dict) -> dict:
    problems = []
    if process["timed_out"]:
        problems.append("timed out")
    if report is None:
        problems.append("no report")
        return {"mode": mode, "status": "FAIL", "steps": 0, "passed_steps": 0, "problems": problems}
    steps = report.get("steps") or []
    names = [step.get("step") for step in steps]
    passed = [step for step in steps if step.get("status") == "PASS"]
    failed = [step.get("step") for step in steps if step.get("status") != "PASS"]
    missing = [name for name in COMMON_STEPS + MODE_STEPS[mode] if name not in names]
    if report.get("host_mode") != mode:
        problems.append("report is for another host mode")
    if report.get("status") != "PASS":
        problems.append(f"status {report.get('status')}")
    if not steps:
        problems.append("zero steps")
    if failed:
        problems.append(f"failed steps: {failed[:5]}")
    if missing:
        problems.append(f"missing steps: {missing[:5]}")
    if len(names) != len(set(names)):
        problems.append("duplicate step names")
    if process["exit_code"] != 0:
        problems.append(f"exit code {process['exit_code']}")
    if report.get("external_requests") or report.get("failed_requests") or report.get("page_errors"):
        problems.append("external requests, failed requests or page errors recorded")
    return {"mode": mode, "status": "FAIL" if problems else "PASS", "browser_version": report.get("browser_version"),
            "steps": len(steps), "passed_steps": len(passed), "required_steps": len(COMMON_STEPS + MODE_STEPS[mode]),
            "problems": problems, "step_results": [[step.get("step"), step.get("status")] for step in steps]}


def evaluate_smoke(summary: dict | None, process: dict) -> dict:
    problems = []
    if process["timed_out"]:
        problems.append("timed out")
    if process["exit_code"] == 2:
        problems.append("BLOCKED: Playwright or Chromium unavailable")
    if summary is None:
        problems.append("no summary")
        return {"status": "FAIL", "scenarios": [], "problems": problems}
    scenarios = summary.get("scenarios") or []
    seen = [(item.get("hosting"), item.get("mode")) for item in scenarios]
    if sorted(seen) != sorted(SMOKE_SCENARIOS):
        problems.append(f"scenarios {sorted(seen)} != expected six")
    out = []
    for item in scenarios:
        checks = item.get("checks") or {}
        bad = [name for name, ok in checks.items() if ok is not True]
        mode = item.get("mode")
        missing = sorted(SMOKE_CHECKS.get(mode, set()) - checks.keys())
        if missing:
            problems.append(f"{item.get('hosting')}/{mode}: missing checks {missing}")
        if bad or item.get("passed") is not True:
            problems.append(f"{item.get('hosting')}/{item.get('mode')}: failed {bad}")
        expected_state = "unavailable" if mode == "missing_bundle" else mode
        if item.get("telemetry_state") != expected_state:
            problems.append(f"{item.get('hosting')}/{mode}: incorrect telemetry state")
        items = item.get("envelope_items")
        if not isinstance(items, list):
            problems.append(f"{item.get('hosting')}/{mode}: missing envelope evidence")
        elif mode == "enabled":
            transactions = sorted(entry.get("name", "") for entry in items if entry.get("type") == "transaction")
            events = [entry.get("value") for entry in items if entry.get("type") == "event"]
            if (len(items) != 6 or transactions != _SMOKE_TRANSACTIONS
                    or events != ["browser.project_request.transport_unreachable"]):
                problems.append(f"{item.get('hosting')}/{mode}: incorrect recorded envelope evidence")
        elif items:
            problems.append(f"{item.get('hosting')}/{mode}: unexpected envelopes")
        out.append({"hosting": item.get("hosting"), "mode": item.get("mode"), "checks": len(checks),
                    "passed_checks": len(checks) - len(bad), "telemetry_state": item.get("telemetry_state"),
                    "envelope_items": len(item.get("envelope_items") or [])})
    if summary.get("status") != "PASS":
        problems.append(f"status {summary.get('status')}")
    if process["exit_code"] != 0:
        problems.append(f"exit code {process['exit_code']}")
    return {"status": "FAIL" if problems else "PASS", "browser": summary.get("browser"), "sdk": summary.get("sdk"),
            "scenarios": out, "problems": problems}


_PYTEST_SUMMARY = re.compile(r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed|deselected)")


def evaluate_pytest(log_text: str, process: dict) -> dict:
    tail = log_text.strip().splitlines()[-1] if log_text.strip() else ""
    counts = {kind: int(number) for number, kind in _PYTEST_SUMMARY.findall(tail)}
    problems = []
    if process["timed_out"]:
        problems.append("timed out")
    if process["exit_code"] != 0:
        problems.append(f"exit code {process['exit_code']}")
    if counts.get("passed", 0) == 0:
        problems.append("zero passed tests")
    for kind in ("failed", "skipped", "error", "errors", "xfailed", "xpassed", "deselected"):
        if counts.get(kind):
            problems.append(f"{counts[kind]} {kind}")
    return {"status": "FAIL" if problems else "PASS", "counts": counts, "problems": problems}


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "browser-acceptance")
    parser.add_argument("--chromium", help="Chromium executable for the saved-demo checker")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env, removed = scrubbed_environment(dict(os.environ))
    python = sys.executable
    results: dict = {"scrubbed_variables": removed}

    demo = []
    for mode in DEMO_MODES:
        evidence = output / f"saved-demo-{mode}"
        evidence.mkdir(parents=True, exist_ok=True)
        stale = evidence / "browser-check.json"
        stale.unlink(missing_ok=True)
        command = [python, "scripts/browser_check_offline_demo.py", "--host-mode", mode, "--evidence", str(evidence)]
        if args.chromium:
            command += ["--chromium", args.chromium]
        process = run(command, env, output / f"saved-demo-{mode}.log")
        demo.append({**evaluate_demo(mode, _load(stale), process), "process": process})
    results["saved_demo"] = demo

    smoke_dir = output / "telemetry-smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    (smoke_dir / "summary.json").unlink(missing_ok=True)
    process = run([python, "scripts/smoke_browser_telemetry.py", "--output", str(smoke_dir)], env,
                  output / "telemetry-smoke.log")
    results["telemetry_smoke"] = {**evaluate_smoke(_load(smoke_dir / "summary.json"), process), "process": process}

    pytest_env = {**env, "OHMNI_REQUIRE_BROWSER": "1"}
    pytest_log = output / "browser-regressions.log"
    process = run([python, "-m", "pytest", "tests/test_browser_acceptance.py", "-o", "addopts=-q --strict-markers",
                   "-p", "no:cacheprovider", "--basetemp", str(output / "pytest-tmp")], pytest_env, pytest_log)
    results["browser_regressions"] = {**evaluate_pytest(pytest_log.read_text(encoding="utf-8"), process),
                                      "process": process}

    parts = [*demo, results["telemetry_smoke"], results["browser_regressions"]]
    results["status"] = "PASS" if all(part["status"] == "PASS" for part in parts) else "FAIL"
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for item in demo:
        print(f"{item['status']} saved demo {item['mode']:7} {item['passed_steps']}/{item['steps']} steps "
              f"{'; '.join(item['problems'])}")
    smoke = results["telemetry_smoke"]
    print(f"{smoke['status']} telemetry smoke {len(smoke['scenarios'])}/6 scenarios "
          f"{sum(s['passed_checks'] for s in smoke['scenarios'])}/{sum(s['checks'] for s in smoke['scenarios'])} checks "
          f"{'; '.join(smoke['problems'])}")
    regressions = results["browser_regressions"]
    print(f"{regressions['status']} browser regressions {regressions['counts']} {'; '.join(regressions['problems'])}")
    if removed:
        print(f"scrubbed inherited variables: {', '.join(removed)}")
    print(f"{results['status']}: summary at {output / 'summary.json'}")
    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
