"""Telemetry through the real demo server, workers, pipelines and native-tool boundary.

The pinned SDK runs with a recording transport and the network guard from
telemetry_support.py. Responses are compared with telemetry disabled so the
public contract (status, body, job codes, artifact bytes) is shown unchanged.
KiCad is replaced by tiny local fake executables where a native outcome is
needed; that proves the telemetry classification, not a KiCad verdict.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest
from telemetry_support import isolate_environment, offline_telemetry
from test_conversation import output

from ohmni.adapters import telemetry
from ohmni.adapters.anthropic_provider import AnthropicProvider
from ohmni.application.demo import DemoProgress, current_pcb_policy
from ohmni.application.request_budget import BudgetConfig, RequestBudget
from ohmni.synthesis import SynthesisBrief
from scripts.demo_server import DEMO_REQUEST, DemoHandler, DemoHTTPServer, JobStore

OPENER = build_opener(ProxyHandler({}))
TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT = "00f067aa0ba902b7"
CANARY = "CANARY-request-9c1d"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    isolate_environment(monkeypatch)
    telemetry.shutdown(0)
    yield
    telemetry.shutdown(0)


@contextmanager
def served(tmp_path, *, provider=None, budget=None, pipeline=None):
    kwargs = {"provider": provider}
    if pipeline is not None:
        kwargs["pipeline_factory"] = pipeline
    store = JobStore(tmp_path, **kwargs)
    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store, ai_budget=budget)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def post(base, path, payload, headers=None):
    request = Request(base + path, data=json.dumps(payload).encode(), method="POST",
                      headers={"content-type": "application/json", **(headers or {})})
    try:
        with OPENER.open(request, timeout=30) as response:
            return response.status, json.loads(response.read()), dict(response.headers)
    except HTTPError as error:
        return error.code, json.loads(error.read()), dict(error.headers)


def wait(store, job_id, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = store.get(job_id)
        if job["status"] in {"complete", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not terminalize")


def wait_for_transactions(recorder, count, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = recorder.transactions()
        if len(found) >= count:
            return found
        time.sleep(0.05)
    raise AssertionError(f"expected {count} transactions, saw {len(recorder.transactions())}")


class VendorClient:
    """A test double for the vendor SDK: scripted responses or exceptions."""

    def __init__(self, *responses):
        self.messages = SimpleNamespace(create=self._create)
        self.responses = list(responses)

    def _create(self, **_kwargs):
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


APIConnectionError = type("APIConnectionError", (Exception,), {})


def tool_message(payload):
    return SimpleNamespace(stop_reason="tool_use", model="claude-sonnet-5",
                           usage=SimpleNamespace(input_tokens=11, output_tokens=7),
                           content=[SimpleNamespace(type="tool_use", name="emit_board_plan", input=payload)])


def plan_request(server):
    return {**server._identity(), "message": f"A USB temperature board {CANARY}", "parent_id": None}


def test_planner_provider_outage_is_one_issue_with_the_unchanged_public_response(tmp_path, monkeypatch):
    def outage():
        return AnthropicProvider(api_key="test", client=VendorClient(APIConnectionError(CANARY)))
    with served(tmp_path / "off", provider=outage()) as (server, base):
        disabled = post(base, "/api/project-plans", plan_request(server))
    with offline_telemetry(monkeypatch) as recorder:
        with served(tmp_path / "on", provider=outage()) as (server, base):
            enabled = post(base, "/api/project-plans", plan_request(server),
                           {"sentry-trace": f"{TRACE}-{PARENT}-1", "baggage": f"other={CANARY}"})
        [transaction] = wait_for_transactions(recorder, 1)
        raw = recorder.raw()
        values = recorder.failure_values()
    assert disabled[:2] == enabled[:2]
    assert enabled[0] == 400 and enabled[1]["error"] == "invalid_plan"
    assert values == ["provider.provider_connection"]
    trace = transaction["contexts"]["trace"]
    assert (trace["trace_id"], trace["parent_span_id"]) == (TRACE, PARENT)
    assert transaction["transaction"] == "POST /api/project-plans"
    assert trace["data"]["ohmni.http.status_code"] == 400
    assert [s["op"] for s in transaction["spans"]] == ["ohmni.stage", "gen_ai.chat"]
    assert CANARY.encode() not in raw and b"test" not in raw.replace(b"latest", b"")


def test_rejected_model_output_after_a_successful_call_is_a_planner_warning(tmp_path, monkeypatch):
    bad = output(stated=[{"field": "status_led_count", "quote": "not in the message"}])
    with offline_telemetry(monkeypatch) as recorder:
        provider = AnthropicProvider(api_key="test", client=VendorClient(tool_message(bad)))
        with served(tmp_path, provider=provider) as (server, base):
            status, body, _ = post(base, "/api/project-plans", plan_request(server))
            empty = post(base, "/api/project-plans", {**plan_request(server), "message": ""})
        assert status == 400 and body["error"] == "invalid_plan"
        assert empty[0] == 400
        wait_for_transactions(recorder, 2)
        # The empty message never reached the model, so it is the caller's input.
        assert recorder.failure_values() == ["planner.plan_output_rejected"]
        assert recorder.events()[0]["level"] == "warning"


def fake_kicad(directory, body):
    directory.mkdir(parents=True, exist_ok=True)
    executable = directory / "kicad-cli"
    executable.write_text(f"#!{sys.executable}\nimport sys, time\n{body}\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IEXEC)
    return directory


def saved_revision(server, base):
    brief = SynthesisBrief(project_name="Telemetry board").model_dump(mode="json")
    status, body, _ = post(base, "/api/projects", {**server._identity(), "brief": brief})
    assert status == 201
    project = body["project"]
    return project["project_id"], project["revisions"][0]["revision_id"]


@pytest.mark.parametrize("kicad", ["missing", "nonzero"])
def test_confirmed_project_worker_trace_connects_to_the_request(tmp_path, monkeypatch, kicad):
    if kicad == "missing":
        monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    else:
        bin_dir = fake_kicad(tmp_path / "bin", "sys.exit(9)")
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    with offline_telemetry(monkeypatch) as recorder:
        with served(tmp_path / "work") as (server, base):
            project_id, revision_id = saved_revision(server, base)
            path = f"/api/projects/{project_id}/revisions/{revision_id}/run"
            status, body, _ = post(base, path, server._identity(), {"sentry-trace": f"{TRACE}-{PARENT}"})
            assert status == 202
            job = wait(server.store, body["job_id"])
            for _ in range(3):  # polling never recounts a job
                server.store.get(body["job_id"])
            assert job["status"] == "failed" and job["error_code"] == "eda_tool_failed"
            transactions = wait_for_transactions(recorder, 2)
        http = next(t for t in transactions if t["contexts"]["trace"]["op"] == "http.server")
        worker = next(t for t in transactions if t["contexts"]["trace"]["op"] == "ohmni.worker")
        values = recorder.failure_values()
        accepted = recorder.metric_count("ohmni.jobs.accepted", flow="confirmed_project")
        terminal = recorder.metric_count("ohmni.jobs.terminal", terminal="failed", reason="eda_tool_failed")
        complete = recorder.metric_count("ohmni.jobs.terminal", terminal="complete")
    assert http["contexts"]["trace"]["trace_id"] == worker["contexts"]["trace"]["trace_id"] == TRACE
    assert worker["contexts"]["trace"]["parent_span_id"] == http["contexts"]["trace"]["span_id"]
    assert worker["transaction"] == "worker confirmed_project"
    assert worker["contexts"]["trace"]["data"]["ohmni.job_id"] == body["job_id"]
    stages = [s["description"] for s in worker["spans"] if s["op"] == "ohmni.stage"]
    assert stages == ["synthesis", "semantic_verification", "schematic", "erc"]
    assert not any(s["op"] == "gen_ai.chat" or s["description"] in {"design_orchestrate", "ngspice"}
                   for s in worker["spans"])
    erc = next(s for s in worker["spans"] if s["description"] == "erc")
    assert erc["data"]["ohmni.engineering_outcome"] == "unknown"
    tools = [(s["description"], s["data"]["ohmni.execution_outcome"]) for s in worker["spans"] if s["op"] == "ohmni.tool"]
    assert tools == ([] if kicad == "missing" else [("kicad", "nonzero_exit")])
    assert values == ["worker.eda_tool_failed"]
    assert (accepted, terminal, complete) == (1, 1, 0)


def test_concurrent_jobs_keep_their_own_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    traces = ["a" * 31 + "1", "b" * 31 + "2"]
    with offline_telemetry(monkeypatch) as recorder, served(tmp_path / "work") as (server, base):
        revisions = [saved_revision(server, base) for _ in traces]
        results = [None, None]
        def start(index):
            project_id, revision_id = revisions[index]
            results[index] = post(base, f"/api/projects/{project_id}/revisions/{revision_id}/run",
                                  server._identity(), {"sentry-trace": f"{traces[index]}-{PARENT}"})
        threads = [threading.Thread(target=start, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        jobs = [r[1]["job_id"] for r in results]
        for job_id in jobs:
            wait(server.store, job_id)
        transactions = wait_for_transactions(recorder, 4)
    workers = {t["contexts"]["trace"]["trace_id"]: t for t in transactions if t["contexts"]["trace"]["op"] == "ohmni.worker"}
    https = {t["contexts"]["trace"]["trace_id"]: t for t in transactions if t["contexts"]["trace"]["op"] == "http.server"}
    for index, trace in enumerate(traces):
        assert workers[trace]["contexts"]["trace"]["data"]["ohmni.job_id"] == jobs[index]
        assert workers[trace]["contexts"]["trace"]["parent_span_id"] == https[trace]["contexts"]["trace"]["span_id"]
        assert {s["trace_id"] for s in workers[trace]["spans"]} == {trace}


class Report:
    def model_dump(self, mode=None):
        return {"result": "complete", "pcb": current_pcb_policy()}


class Pipeline:
    def __init__(self, progress):
        self.progress = progress

    def run(self, destination, request):
        return Report()


def test_failed_publication_never_reports_completion(tmp_path, monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        store = JobStore(tmp_path, Pipeline)
        store.enable_persistence()
        real = store.project_store.save_job
        def save(record):
            if record["status"] == "complete":
                raise OSError(CANARY)
            return real(record)
        monkeypatch.setattr(store.project_store, "save_job", save)
        with telemetry.http_operation("POST /api/demo"):
            job_id = store.start(DEMO_REQUEST)
        job = wait(store, job_id)
        transactions = wait_for_transactions(recorder, 2)
        assert job["status"] == "failed" and job["error_code"] == "job_state_invalid"
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="complete") == 0
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="failed", reason="job_state_invalid") == 1
        assert recorder.failure_values() == ["persistence.job_persist_failed"]
        worker = next(t for t in transactions if t["contexts"]["trace"]["op"] == "ohmni.worker")
        publication = next(s for s in worker["spans"] if s["description"] == "publication")
        assert publication["data"]["ohmni.execution_outcome"] == "error"
        assert worker["contexts"]["trace"]["status"] == "internal_error"
        assert CANARY.encode() not in recorder.raw()


def test_successful_publication_counts_once_and_reuse_never_recounts(tmp_path, monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        store = JobStore(tmp_path, Pipeline)
        store.enable_persistence()
        with telemetry.http_operation("POST /api/demo"):
            job_id = store.start(DEMO_REQUEST)
        assert wait(store, job_id)["status"] == "complete"
        for _ in range(3):
            store.get(job_id)
        wait_for_transactions(recorder, 2)
        assert recorder.metric_count("ohmni.jobs.accepted", flow="scripted_fixture") == 1
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="complete") == 1
        assert recorder.failure_values() == []


def test_progress_persistence_failure_is_reported_once_after_the_lock(tmp_path, monkeypatch):
    class Progressing(Pipeline):
        def run(self, destination, request):
            self.progress(DemoProgress(stage="requirements", label="x", status="RUNNING", percent=5))
            return Report()
    with offline_telemetry(monkeypatch) as recorder:
        store = JobStore(tmp_path, Progressing)
        store.enable_persistence()
        real = store.project_store.save_job
        def save(record):
            if record["status"] == "running":
                raise OSError(CANARY)
            return real(record)
        monkeypatch.setattr(store.project_store, "save_job", save)
        with telemetry.http_operation("POST /api/demo"):
            job_id = store.start(DEMO_REQUEST)
        job = wait(store, job_id)
        wait_for_transactions(recorder, 2)
        assert (job["status"], job["error_code"]) == ("failed", "job_state_invalid")
        assert recorder.failure_values() == ["persistence.job_persist_failed"]
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="failed", reason="job_state_invalid") == 1
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="complete") == 0
        assert CANARY.encode() not in recorder.raw()


@pytest.mark.parametrize("marked", [True, False])
def test_only_a_marked_check_failure_is_an_engineering_rejection(tmp_path, monkeypatch, marked):
    class Rejecting(Pipeline):
        def run(self, destination, request):
            with telemetry.stage("routing") as span:
                span.outcome("ok", "reject")
            if marked:
                telemetry.engineering_rejection()
                raise RuntimeError(CANARY)
            raise OSError(CANARY)  # infrastructure failure after an earlier reject outcome
    with offline_telemetry(monkeypatch) as recorder:
        store = JobStore(tmp_path, Rejecting)
        with telemetry.http_operation("POST /api/demo"):
            job_id = store.start(DEMO_REQUEST)
        assert wait(store, job_id)["error_code"] == "pipeline_failed"
        transactions = wait_for_transactions(recorder, 2)
        worker = next(t for t in transactions if t["contexts"]["trace"]["op"] == "ohmni.worker")
        data = worker["contexts"]["trace"]["data"]
        if marked:
            assert recorder.failure_values() == []
            assert data["ohmni.engineering_outcome"] == "reject"
        else:
            assert recorder.failure_values() == ["worker.pipeline_failed"]
            assert data.get("ohmni.engineering_outcome") != "reject"


def test_interrupted_job_is_not_a_successful_trace(tmp_path, monkeypatch):
    release = threading.Event()
    entered = threading.Event()
    class Slow(Pipeline):
        def run(self, destination, request):
            entered.set()
            release.wait(10)
            return Report()
    with offline_telemetry(monkeypatch) as recorder:
        store = JobStore(tmp_path, Slow)
        store.enable_persistence()
        job_id = store.start(DEMO_REQUEST)
        assert entered.wait(10)
        store.stop()  # server shutdown terminalizes the active attempt first
        release.set()
        assert wait(store, job_id)["error_code"] == "server_restarted"
        [worker] = wait_for_transactions(recorder, 1)
        assert worker["contexts"]["trace"]["status"] == "internal_error"
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="complete") == 0
        assert recorder.metric_count("ohmni.jobs.terminal", terminal="failed", reason="server_restarted") == 1


def test_budget_refusals_and_leases_are_unchanged_with_telemetry(tmp_path, monkeypatch):
    def budget(path):
        return RequestBudget(path / "budget.sqlite3", BudgetConfig(daily_limit=1, max_in_flight=1, burst_limit=5,
                                                                   burst_window_seconds=60))
    results = {}
    for mode in ("off", "on"):
        root = tmp_path / mode
        root.mkdir()
        provider = AnthropicProvider(api_key="test", client=VendorClient(tool_message(output()), tool_message(output())))
        manager = offline_telemetry(monkeypatch) if mode == "on" else _null()
        with manager, served(root, provider=provider, budget=budget(root)) as (server, base):
            first = post(base, "/api/project-plans", plan_request(server))
            second = post(base, "/api/project-plans", plan_request(server))
            results[mode] = (first[0], second[0], second[1], second[2].get("Retry-After") is not None,
                             server.ai_budget.in_flight)
    assert results["off"] == results["on"]
    assert results["on"][:2] == (200, 429)


@contextmanager
def _null():
    yield


def test_cors_allows_trace_headers_only_for_already_allowed_origins(tmp_path, monkeypatch):
    monkeypatch.setattr(DemoHandler, "_ALLOWED_ORIGINS", frozenset({"https://ohmni.example"}))
    with served(tmp_path) as (_server, base):
        def preflight(origin):
            request = Request(base + "/api/project-plans", method="OPTIONS", headers={"origin": origin})
            with OPENER.open(request, timeout=10) as response:
                return dict(response.headers)
        allowed = preflight("https://ohmni.example")
        foreign = preflight("https://elsewhere.example")
    assert "sentry-trace" in allowed["access-control-allow-headers"]
    assert "baggage" in allowed["access-control-allow-headers"]
    assert "access-control-allow-origin" not in {k.lower() for k in foreign}


def test_schematic_bytes_and_job_codes_match_with_telemetry_on_and_off(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    outcomes = {}
    for mode in ("off", "on"):
        manager = offline_telemetry(monkeypatch) if mode == "on" else _null()
        with manager, served(tmp_path / mode) as (server, base):
            project_id, revision_id = saved_revision(server, base)
            status, body, _ = post(base, f"/api/projects/{project_id}/revisions/{revision_id}/run", server._identity())
            job = wait(server.store, body["job_id"])
            schematic = (tmp_path / mode / body["job_id"] / "golden.kicad_sch").read_bytes()
            outcomes[mode] = (status, job["status"], job["error_code"], hashlib.sha256(schematic).hexdigest())
    assert outcomes["off"] == outcomes["on"]


@pytest.mark.parametrize(("status", "rejected"), [("fail", True), ("stale_artifact", False)])
def test_only_a_completed_failing_eda_check_marks_a_rejection(monkeypatch, status, rejected):
    from ohmni.application.demo import require_eda_check
    report = SimpleNamespace(status=SimpleNamespace(value=status), tool_status=None)
    with offline_telemetry(monkeypatch), telemetry.http_operation("POST /api/demo"):
        with pytest.raises(RuntimeError):
            require_eda_check(report, "ERC")
        assert telemetry.engineering_rejected() is rejected
