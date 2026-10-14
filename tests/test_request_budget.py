"""Bounded admission for every billed provider path, using fake providers only."""

from __future__ import annotations

import json
import multiprocessing
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest
from test_conversation import Provider as PlanProvider
from test_conversation import output
from test_project_assistant import Provider as AssistantProvider
from test_project_assistant import change

from ohmni.application.projects import preview_project
from ohmni.application.request_budget import (
    BudgetConfig,
    BudgetExceeded,
    BudgetUnavailable,
    RequestBudget,
    reset_day,
    seconds_until_utc_midnight,
)
from ohmni.synthesis import SynthesisBrief
from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore

OPENER = build_opener(ProxyHandler({}))
NOON = datetime(2026, 10, 17, 12, 0, tzinfo=UTC).timestamp()


class Clock:
    def __init__(self, wall=NOON):
        self.wall = wall
        self.mono = 1000.0

    def advance(self, seconds):
        self.wall += seconds
        self.mono += seconds


def budget(tmp_path, clock=None, **limits):
    clock = clock or Clock()
    config = BudgetConfig(**{"daily_limit": 5, "max_in_flight": 10, "burst_limit": 100,
                             "burst_window_seconds": 60, **limits})
    return RequestBudget(tmp_path / "budget.sqlite3", config,
                         clock=lambda: clock.wall, monotonic=lambda: clock.mono)


# -- pure admission -------------------------------------------------------------

def test_daily_limit_counts_failed_calls_and_survives_restart(tmp_path):
    clock = Clock()
    first = budget(tmp_path, clock)
    for _ in range(3):
        with first.admit("planner"):
            pass  # a provider failure still consumed the admission
    restarted = budget(tmp_path, clock)
    assert restarted.admitted_today() == 3
    restarted.admit("assistant").release()
    restarted.admit("brief").release()
    with pytest.raises(BudgetExceeded) as limited:
        restarted.admit("generation")
    assert limited.value.reason == "daily"
    assert limited.value.retry_after_seconds == seconds_until_utc_midnight(clock.wall) == 12 * 3600
    assert restarted.in_flight == 0


def test_day_rollover_admits_again_and_operator_reset_is_local(tmp_path):
    clock = Clock()
    limited = budget(tmp_path, clock, daily_limit=1)
    limited.admit("planner").release()
    with pytest.raises(BudgetExceeded):
        limited.admit("planner")
    clock.advance(12 * 3600 + 1)
    limited.admit("planner").release()
    assert reset_day(tmp_path / "budget.sqlite3", "2026-10-18") == 1
    limited.admit("planner").release()


def test_concurrency_lease_bounds_in_flight_work(tmp_path):
    limited = budget(tmp_path, max_in_flight=2)
    a, b = limited.admit("generation"), limited.admit("planner")
    with pytest.raises(BudgetExceeded) as busy:
        limited.admit("assistant")
    assert busy.value.reason == "concurrency" and busy.value.retry_after_seconds > 0
    a.release()
    a.release()  # idempotent: a double release cannot free someone else's slot
    assert limited.in_flight == 1
    limited.admit("assistant").release()
    b.release()
    assert limited.in_flight == 0


def test_burst_limit_uses_a_sliding_window(tmp_path):
    clock = Clock()
    limited = budget(tmp_path, clock, daily_limit=100, burst_limit=3, burst_window_seconds=60)
    for _ in range(3):
        limited.admit("planner").release()
        clock.advance(10)
    with pytest.raises(BudgetExceeded) as burst:
        limited.admit("planner")
    assert burst.value.reason == "burst" and burst.value.retry_after_seconds == 30
    clock.advance(31)
    limited.admit("planner").release()


def test_concurrent_admissions_across_instances_never_exceed_the_daily_limit(tmp_path):
    clock = Clock()
    instances = [budget(tmp_path, clock, daily_limit=40, max_in_flight=1000, burst_limit=1000)
                 for _ in range(3)]
    start = threading.Barrier(6)

    def worker(instance):
        start.wait(timeout=10)
        admitted, refused = 0, 0
        for _ in range(20):
            try:
                instance.admit("planner").release()
                admitted += 1
            except BudgetExceeded:
                refused += 1
        return admitted, refused

    with ThreadPoolExecutor(max_workers=6) as workers:
        results = list(workers.map(worker, [instances[i % 3] for i in range(6)]))
    assert sum(result[0] for result in results) == 40
    assert sum(result[1] for result in results) == 80
    assert instances[0].admitted_today() == 40


def _admit_in_process(path, start, results):
    """Spawn-safe worker: report failures explicitly instead of losing threads."""
    try:
        instance = RequestBudget(path, BudgetConfig(daily_limit=17, burst_limit=100),
                                 clock=lambda: NOON)
        start.wait(timeout=20)
        admitted, refused = 0, 0
        for _ in range(20):
            try:
                instance.admit("planner").release()
                admitted += 1
            except BudgetExceeded as error:
                assert error.reason == "daily"
                refused += 1
        results.put((admitted, refused, None))
    except Exception as error:  # noqa: BLE001 - return every worker failure to the parent assertion
        results.put((0, 0, repr(error)))


@pytest.mark.parametrize("existing_wal", [False, True])
def test_concurrent_processes_share_the_durable_limit(tmp_path, existing_wal):
    path = tmp_path / "budget.sqlite3"
    if existing_wal:
        budget(tmp_path).admit("planner").release()
    context = multiprocessing.get_context("spawn")
    start, results = context.Barrier(3), context.Queue()
    processes = [context.Process(target=_admit_in_process, args=(path, start, results))
                 for _ in range(3)]
    try:
        for process in processes:
            process.start()
        outcomes = [results.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=5)
        assert [process.exitcode for process in processes] == [0, 0, 0]
        assert [outcome[2] for outcome in outcomes] == [None, None, None]
        assert sum(outcome[0] for outcome in outcomes) == 17 - int(existing_wal)
        assert sum(outcome[1] for outcome in outcomes) == 43 + int(existing_wal)
        assert budget(tmp_path).admitted_today() == 17
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        results.close()
        results.join_thread()


def _setup_fault(monkeypatch, *, code, failures):
    """Inject real sqlite error codes at WAL setup; keep the remaining DB real."""
    original_connect = sqlite3.connect
    failed_connections = []
    attempts = []

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args):
            if sql == "PRAGMA journal_mode=WAL" and len(failed_connections) < failures:
                failed_connections.append(self)
                error = sqlite3.OperationalError("injected setup failure")
                error.sqlite_errorcode = code
                raise error
            return super().execute(sql, *args)

    def connect(*args, **kwargs):
        attempts.append(kwargs["timeout"])
        return original_connect(*args, **kwargs, factory=Connection)

    monkeypatch.setattr(sqlite3, "connect", connect)
    return attempts, failed_connections


def _assert_closed(connections):
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


@pytest.mark.parametrize("code", [sqlite3.SQLITE_BUSY, sqlite3.SQLITE_BUSY_RECOVERY])
def test_busy_setup_retries_without_double_counting(tmp_path, monkeypatch, code):
    attempts, failed = _setup_fault(monkeypatch, code=code, failures=2)
    instance = budget(tmp_path, daily_limit=1)
    instance.admit("planner").release()
    assert len(attempts) == 3
    assert all(0 < timeout <= 5 for timeout in attempts)
    _assert_closed(failed)
    assert instance.admitted_today() == 1 and instance.in_flight == 0
    with pytest.raises(BudgetExceeded):
        instance.admit("planner")


def test_commit_error_is_never_retried_or_admitted(tmp_path, monkeypatch):
    original_connect = sqlite3.connect
    commits = []

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args):
            result = super().execute(sql, *args)
            if sql == "COMMIT":
                commits.append(sql)
                error = sqlite3.OperationalError("unknown commit outcome")
                error.sqlite_errorcode = sqlite3.SQLITE_BUSY
                raise error
            return result

    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs:
                        original_connect(*args, **kwargs, factory=Connection))
    instance = budget(tmp_path)
    with pytest.raises(BudgetUnavailable):
        instance.admit("planner")
    assert commits == ["COMMIT"]
    assert instance.admitted_today() == 1 and instance.in_flight == 0


def test_persistent_busy_setup_is_bounded_and_refuses(tmp_path, monkeypatch):
    from ohmni.application import request_budget

    attempts, failed = _setup_fault(monkeypatch, code=sqlite3.SQLITE_BUSY, failures=1000)
    elapsed = [0.0]

    def sleep(seconds):
        elapsed[0] += seconds

    monkeypatch.setattr(request_budget, "time", SimpleNamespace(
        monotonic=lambda: elapsed[0], sleep=sleep))
    instance = budget(tmp_path)
    with pytest.raises(BudgetUnavailable):
        instance.admit("planner")
    assert elapsed[0] == pytest.approx(5)
    assert 1 < len(attempts) <= 502
    assert instance.in_flight == 0
    _assert_closed(failed)
    # Recovery starts at zero: a failed setup never consumed an admission.
    monkeypatch.undo()
    assert instance.admitted_today() == 0


@pytest.mark.parametrize("code", [sqlite3.SQLITE_IOERR, sqlite3.SQLITE_CORRUPT,
                                 sqlite3.SQLITE_READONLY])
def test_non_busy_setup_error_refuses_without_retry(tmp_path, monkeypatch, code):
    attempts, failed = _setup_fault(monkeypatch, code=code, failures=1000)
    instance = budget(tmp_path)
    with pytest.raises(BudgetUnavailable):
        instance.admit("planner")
    assert len(attempts) == 1 and instance.in_flight == 0
    _assert_closed(failed)


def test_untrusted_storage_or_configuration_refuses(tmp_path):
    directory = tmp_path / "is-a-directory"
    directory.mkdir()
    broken = RequestBudget(directory, BudgetConfig())
    with pytest.raises(BudgetUnavailable):
        broken.admit("planner")
    corrupt_path = tmp_path / "corrupt.sqlite3"
    with sqlite3.connect(corrupt_path) as connection:
        connection.execute("CREATE TABLE ai_daily_requests (day TEXT PRIMARY KEY, admitted)")
        connection.execute("INSERT INTO ai_daily_requests VALUES (?, ?)",
                           (datetime.fromtimestamp(NOON, UTC).strftime("%Y-%m-%d"), "lots"))
    corrupt = RequestBudget(corrupt_path, BudgetConfig(), clock=lambda: NOON)
    with pytest.raises(BudgetUnavailable):
        corrupt.admit("planner")
    for environ in ({"OHMNI_AI_DAILY_LIMIT": "0"}, {"OHMNI_AI_DAILY_LIMIT": "-5"},
                    {"OHMNI_AI_MAX_IN_FLIGHT": "inf"}, {"OHMNI_AI_BURST_LIMIT": "1e9"}):
        refused = RequestBudget.from_environment(tmp_path / "env.sqlite3", environ)
        with pytest.raises(BudgetUnavailable):
            refused.admit("planner")
    with pytest.raises(ValueError):
        budget(tmp_path).admit("not-a-billed-route")


def test_documented_defaults_come_from_the_environment(tmp_path):
    configured = RequestBudget.from_environment(tmp_path / "b.sqlite3", {"OHMNI_AI_DAILY_LIMIT": "50"})
    assert configured.config == BudgetConfig(daily_limit=50, max_in_flight=2, burst_limit=6,
                                             burst_window_seconds=60)
    assert RequestBudget.from_environment(tmp_path / "b.sqlite3", {}).config == BudgetConfig()


# -- HTTP routes -----------------------------------------------------------------

def _post(base, path, payload, headers=None):
    request = Request(base + path, data=json.dumps(payload).encode(),
                      headers={"content-type": "application/json", **(headers or {})}, method="POST")
    try:
        with OPENER.open(request, timeout=10) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, json.loads(response.read())
    except HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, json.loads(error.read())


@contextmanager
def serving(tmp_path, *, provider, pipeline=None, ai_budget):
    store = JobStore(tmp_path, pipeline, provider=provider) if pipeline else JobStore(tmp_path, provider=provider)
    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store, ai_budget=ai_budget)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _wait_terminal(store, job_id):
    import time
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if store.get(job_id)["status"] in {"complete", "failed"}:
            return store.get(job_id)
        time.sleep(0.01)
    raise AssertionError("job did not terminalize")


def test_exhausted_planner_returns_429_without_calling_the_provider(tmp_path):
    provider = PlanProvider(*(output() for _ in range(3)))
    limited = budget(tmp_path, daily_limit=2)
    with serving(tmp_path / "server", provider=provider, ai_budget=limited) as (server, base):
        data = {**server._identity(), "message": "A USB temperature and humidity board", "parent_id": None}
        assert _post(base, "/api/project-plans", data)[0] == 200
        assert _post(base, "/api/project-plans", data)[0] == 200
        for spoof in ({}, {"x-forwarded-for": "203.0.113.9"}, {"x-real-ip": "198.51.100.1"}):
            status, headers, body = _post(base, "/api/project-plans", data, spoof)
            assert status == 429 and body["error"] == "ai_request_limited"
            assert int(headers["retry-after"]) > 0 and "Your text is still here" in body["refusal"]["message"]
        assert len(provider.requests) == 2
        # Ordinary reads are not behind the billed quota.
        with OPENER.open(base + "/api/health", timeout=10) as response:
            assert response.status == 200
        assert limited.in_flight == 0


def test_assistant_route_is_admitted_and_releases_its_lease(tmp_path):
    provider = AssistantProvider(change(), change())
    limited = budget(tmp_path, daily_limit=1)
    with serving(tmp_path / "server", provider=provider, ai_budget=limited) as (server, base):
        brief = SynthesisBrief()
        project = server.projects.save_revision(brief.model_dump(mode="json"), brief.fingerprint,
                                                preview_project(brief).model_dump(mode="json"))
        path = f"/api/projects/{project['project_id']}/revisions/{project['revisions'][0]['revision_id']}/assistant"
        data = {**server._identity(), "message": "Make it 80 mm wide", "parent_id": None}
        assert _post(base, path, data)[0] == 200
        status, headers, body = _post(base, path, data)
        assert status == 429 and body["error"] == "ai_request_limited" and "retry-after" in headers
        assert len(provider.requests) == 1 and limited.in_flight == 0


def test_failed_brief_call_is_counted_and_untrusted_budget_refuses(tmp_path):
    class Failing:
        def __init__(self):
            self.calls = 0

        def generate_structured(self, request, schema):
            self.calls += 1
            raise RuntimeError("provider outage")

    provider = Failing()
    limited = budget(tmp_path, daily_limit=1)
    text = "Build a USB-powered CO2 logger with a status light."
    with serving(tmp_path / "server", provider=provider, ai_budget=limited) as (server, base):
        data = {"request": text, **server._identity()}
        assert _post(base, "/api/brief", data)[0] == 503
        status, headers, body = _post(base, "/api/brief", data)
        assert status == 429 and body == {"error": "ai_request_limited"} and int(headers["retry-after"]) > 0
        assert provider.calls == 1 and limited.admitted_today() == 1 and limited.in_flight == 0
    directory = tmp_path / "budget-dir"
    directory.mkdir()
    with serving(tmp_path / "server2", provider=provider,
                 ai_budget=RequestBudget(directory, BudgetConfig())) as (server, base):
        status, _headers, body = _post(base, "/api/brief", {"request": text, **server._identity()})
        assert status == 503 and body == {"error": "ai_budget_unavailable"}
        assert provider.calls == 1


def test_background_generation_holds_its_lease_until_the_worker_finishes(tmp_path):
    release = threading.Event()
    entered = threading.Event()

    class Report:
        def model_dump(self, mode=None):
            from ohmni.application.demo import current_pcb_policy
            return {"result": "accepted", "pcb": current_pcb_policy()}

    class Pipeline:
        def __init__(self, progress, provider=None):
            self.provider = provider

        def run(self, destination, request):
            entered.set()
            assert release.wait(5)
            if request.endswith("fail."):
                raise RuntimeError("provider failed mid-generation")
            return Report()

    limited = budget(tmp_path, daily_limit=3, max_in_flight=1)
    provider = SimpleNamespace(name="fake billed provider")
    plans = PlanProvider(output())
    with serving(tmp_path / "server", provider=provider, pipeline=Pipeline, ai_budget=limited) as (server, base):
        server.planner.provider = plans
        identity = server._identity()
        text = "Build a USB-powered CO2 logger with a status light."
        status, _headers, body = _post(base, "/api/demo", {"request": text, **identity})
        assert status == 202
        assert entered.wait(5)
        # The HTTP handler has returned, but the worker still holds the lease.
        assert limited.in_flight == 1
        status, headers, body = _post(base, "/api/demo", {"request": text, **identity})
        assert status == 429 and body == {"error": "ai_request_limited"} and "retry-after" in headers
        status, _headers, _body = _post(base, "/api/project-plans",
                                        {**identity, "message": "A USB temperature board", "parent_id": None})
        assert status == 429 and plans.requests == []
        # The scripted fixture is not billed and is not behind the quota.
        assert _post(base, "/api/demo", {"fixture_id": "esp32-bme280-environmental-logger", **identity})[0] != 429
        release.set()
        assert _wait_terminal(server.store, body.get("job_id") or next(iter(server.store.jobs)))
        for job_id in list(server.store.jobs):
            _wait_terminal(server.store, job_id)
        assert limited.in_flight == 0
        release.clear()
        entered.clear()
        status, _headers, failing = _post(base, "/api/demo", {"request": "Build a board that will fail.", **identity})
        assert status == 202 and entered.wait(5) and limited.in_flight == 1
        release.set()
        assert _wait_terminal(server.store, failing["job_id"])["status"] == "failed"
        assert limited.in_flight == 0
        assert limited.admitted_today() == 2  # both generations, including the failed one
