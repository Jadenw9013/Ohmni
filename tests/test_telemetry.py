"""The telemetry adapter's privacy and failure-isolation contract, against the real SDK.

Every enabled test here runs the pinned ``sentry_sdk`` with a recording
transport (see telemetry_support.py); none uses a stub in place of the SDK's
own serialization. Failure-isolation probes break the SDK at each lifecycle
point and assert the application body still ran exactly once with its own
result or exception.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
import sentry_sdk
from telemetry_support import SYNTHETIC_DSN, config, isolate_environment, offline_telemetry

from ohmni.adapters import telemetry
from ohmni.adapters.anthropic_provider import AnthropicProvider, StructuredGenerationError
from ohmni.adapters.process import run_tool

ROOT = Path(__file__).resolve().parents[1]
TRACE = "771a43a4192642f0b136d5159a501700"
PARENT = "b7ad6b7169203331"
CANARIES = [f"CANARY-{name}-7f3a" for name in (
    "prompt", "model-output", "exception-arg", "local", "netlist", "argv", "env", "stdout",
    "path", "url", "header",
)]


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    isolate_environment(monkeypatch)
    telemetry.shutdown(0)
    yield
    telemetry.shutdown(0)


class Sentinel(Exception):
    pass


# ---------------------------------------------------------------------------
# Configuration and disabled mode
# ---------------------------------------------------------------------------

def test_disabled_and_invalid_configuration_import_nothing_and_create_no_transport():
    code = (
        "import sys\n"
        "from ohmni.adapters import telemetry\n"
        "import scripts.demo_server\n"
        "assert telemetry.initialize(telemetry.configure_from_environment({})) is False\n"
        "bad = {'OHMNI_TELEMETRY_ENABLED': '1', 'SENTRY_DSN': '" + SYNTHETIC_DSN + "'}\n"
        "assert telemetry.initialize(telemetry.configure_from_environment(bad)) is False\n"
        "with telemetry.http_operation('POST /api/demo') as op, telemetry.stage('erc') as s:\n"
        "    op.set_status(500); s.outcome('error')\n"
        "telemetry.record_boundary_failure('worker', 'pipeline_failed')\n"
        "assert 'sentry_sdk' not in sys.modules, 'disabled mode imported the SDK'\n"
        "print('ok')\n"
    )
    env = {key: value for key, value in __import__("os").environ.items()
           if not key.startswith(("SENTRY", "OHMNI_TELEMETRY"))}
    env["PYTHONPATH"] = f"{ROOT / 'src'}:{ROOT}"
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True,
                            text=True, timeout=60, check=False)
    assert result.returncode == 0 and result.stdout.strip() == "ok", result.stderr[-400:]


@pytest.mark.parametrize("overrides, state", [
    ({"OHMNI_TELEMETRY_ENABLED": None}, "disabled"),
    ({"OHMNI_TELEMETRY_ENABLED": "0"}, "disabled"),
    ({"OHMNI_TELEMETRY_ENABLED": "maybe"}, "invalid"),
    ({"SENTRY_DSN": None}, "invalid"),
    ({"SENTRY_DSN": "https://public@sentry.example.com/1"}, "invalid"),
    ({"SENTRY_DSN": "http://" + "a" * 32 + "@o1.ingest.sentry.io/1"}, "invalid"),
    ({"OHMNI_ENV": "staging"}, "invalid"),
    ({"OHMNI_TRACE_SAMPLE_RATE": "nan"}, "invalid"),
    ({"OHMNI_TRACE_SAMPLE_RATE": "1.5"}, "invalid"),
    ({"SENTRY_RELEASE": "ohmni release with spaces"}, "invalid"),
    ({"OHMNI_TELEMETRY_METRICS": "sometimes"}, "invalid"),
    ({"SENTRY_PRINT_ENVELOPES": "1"}, "unsafe_environment"),
    ({"SENTRY_TRACE": TRACE + "-" + PARENT + "-1"}, "unsafe_environment"),
    ({"SENTRY_SPOTLIGHT": "1"}, "unsafe_environment"),
])
def test_configuration_fails_closed_with_a_constant_state(overrides, state):
    parsed = config(**overrides)
    assert parsed.enabled is False and parsed.state == state
    assert SYNTHETIC_DSN not in repr(parsed)
    assert telemetry.initialize(parsed) is False and telemetry.enabled() is False


def test_a_synthetic_dsn_needs_an_explicit_recording_transport():
    assert telemetry.initialize(config()) is False
    assert telemetry.state() == "invalid" and not sentry_sdk.get_client().is_active()


def test_a_different_sdk_version_is_refused(monkeypatch):
    monkeypatch.setattr(sentry_sdk, "VERSION", "9.9.9")
    assert telemetry.initialize(config(), transport=telemetry.recording_transport()) is False
    assert telemetry.state() == "sdk_version_mismatch"


def test_init_failure_leaves_the_product_usable(monkeypatch):
    def broken(**_kwargs):
        raise Sentinel(CANARIES[2])
    monkeypatch.setattr(sentry_sdk, "init", broken)
    assert telemetry.initialize(config(), transport=telemetry.recording_transport()) is False
    assert telemetry.state() == "init_failed"
    with telemetry.http_operation("POST /api/demo") as operation:
        operation.set_status(202)
    assert telemetry.enabled() is False


def test_enabled_client_has_no_integrations_and_no_implicit_channels(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        client = sentry_sdk.get_client()
        assert client.integrations == {}
        collection = client.options["data_collection"]
        assert collection["user_info"] is False and collection["stack_frame_variables"] is False
        assert collection["gen_ai"] == {"inputs": False, "outputs": False}
        assert client.options["auto_session_tracking"] is False
        assert client.options["send_client_reports"] is False
        assert client.options["trace_propagation_targets"] == []
        assert client.options["trace_lifecycle"] == "static"
        assert client.options["stream_gen_ai_spans"] is False
        assert client.options["include_local_variables"] is False
        # Channels the core never uses produce nothing, even if called directly.
        sentry_sdk.add_breadcrumb(message=CANARIES[3])
        import sentry_sdk.logger as sdk_logger
        sdk_logger.info(CANARIES[3])
        sentry_sdk.capture_message(CANARIES[3])
        try:
            raise Sentinel(CANARIES[2])
        except Sentinel:
            sentry_sdk.capture_exception()
        assert recorder.items() == []


# ---------------------------------------------------------------------------
# Failure isolation at every lifecycle point
# ---------------------------------------------------------------------------

def _run_application(fail: bool):
    calls = []
    def body():
        calls.append(1)
        with telemetry.http_operation("POST /api/demo", TRACE + "-" + PARENT) as operation:  # noqa: SIM117
            with telemetry.stage("synthesis") as stage:
                with telemetry.tool_call("kicad") as tool:
                    with telemetry.provider_attempt("claude-sonnet-5") as attempt:
                        attempt.usage(input_tokens=1, output_tokens=1)
                        attempt.result("ok")
                    tool.result("ok", 0)
                stage.outcome("ok", "pass")
                telemetry.record_boundary_failure("worker", "pipeline_failed")
                telemetry.record_job_accepted("scripted_fixture")
                operation.set_status(500)
                if fail:
                    raise Sentinel("application")
                return "application-result"
    return body, calls


def _break(monkeypatch, point):
    def boom(*_args, **_kwargs):
        raise Sentinel("sdk")
    from sentry_sdk import tracing
    targets = {
        "isolation_scope": (sentry_sdk, "isolation_scope"),
        "continue_trace": (sentry_sdk, "continue_trace"),
        "start_transaction": (sentry_sdk, "start_transaction"),
        "transaction_enter": (tracing.Transaction, "__enter__"),
        "transaction_exit": (tracing.Transaction, "__exit__"),
        "start_span": (sentry_sdk, "start_span"),
        "span_enter": (tracing.Span, "__enter__"),
        "span_exit": (tracing.Span, "__exit__"),
        "set_status": (tracing.Span, "set_status"),
        "set_data": (tracing.Span, "set_data"),
        "capture_event": (sentry_sdk, "capture_event"),
        "metrics": (sentry_sdk.metrics, "count"),
        "flush": (sentry_sdk, "flush"),
    }
    owner, name = targets[point]
    monkeypatch.setattr(owner, name, boom)


POINTS = ["isolation_scope", "continue_trace", "start_transaction", "transaction_enter",
          "transaction_exit", "start_span", "span_enter", "span_exit", "set_status",
          "set_data", "capture_event", "metrics", "flush"]


@pytest.mark.parametrize("point", POINTS)
@pytest.mark.parametrize("fail", [False, True])
def test_sdk_failure_never_skips_repeats_replaces_or_suppresses_work(monkeypatch, point, fail):
    with offline_telemetry(monkeypatch):
        _break(monkeypatch, point)
        body, calls = _run_application(fail)
        if fail:
            with pytest.raises(Sentinel, match="^application$"):
                body()
        else:
            assert body() == "application-result"
        assert calls == [1]
        telemetry.flush(0.1)
        monkeypatch.undo()


def test_transport_failure_never_reaches_the_application(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        def broken(_envelope):
            raise Sentinel("transport")
        monkeypatch.setattr(recorder.transport, "capture_envelope", broken)
        body, calls = _run_application(False)
        assert body() == "application-result" and calls == [1]
        telemetry.flush(0.5)
        telemetry.shutdown(0.5)


def test_context_managers_restore_scope_on_success_and_failure(monkeypatch):
    with offline_telemetry(monkeypatch):
        outer_scope = sentry_sdk.get_current_scope()
        for fail in (False, True):
            try:
                with telemetry.http_operation("POST /api/demo"), telemetry.stage("erc"):
                    assert telemetry.current_flow() == "scripted_fixture" or telemetry.current_flow() == "other"
                    if fail:
                        raise Sentinel("x")
            except Sentinel:
                pass
            assert telemetry.current_flow() is None
            assert sentry_sdk.get_current_span() is None
            assert sentry_sdk.get_current_scope() is outer_scope


# ---------------------------------------------------------------------------
# No inspection and canaries
# ---------------------------------------------------------------------------

class HostileMeta(type):
    touched: ClassVar[list[str]] = []

    @property
    def __name__(cls):  # pragma: no cover - must never run
        HostileMeta.touched.append("metaclass-name")
        return "APITimeoutError"


class HostileError(Exception, metaclass=HostileMeta):
    touched: ClassVar[list[str]] = []

    def __str__(self):
        HostileError.touched.append("str")
        return CANARIES[2]

    def __repr__(self):
        HostileError.touched.append("repr")
        return CANARIES[2]

    def __getattribute__(self, name):
        if name not in {"__class__", "__traceback__", "__cause__", "__context__",
                        "__suppress_context__", "with_traceback", "args", "__dict__"}:
            HostileError.touched.append(f"getattr:{name}")
        return object.__getattribute__(self, name)


def test_hostile_exceptions_and_objects_are_never_inspected(monkeypatch):
    HostileError.touched.clear()
    HostileMeta.touched.clear()
    with offline_telemetry(monkeypatch) as recorder:
        secret_local = CANARIES[3]  # noqa: F841 - must not be captured as a local
        with pytest.raises(HostileError), telemetry.http_operation("POST /api/demo"):  # noqa: SIM117
            with telemetry.stage("routing"):
                try:
                    raise HostileError(CANARIES[2])
                except HostileError:
                    telemetry.record_boundary_failure("worker", "pipeline_failed")
                    assert telemetry.classify_provider_failure(HostileError) == "provider_error"
                    raise
        raw = recorder.raw()
    assert HostileError.touched == [] and HostileMeta.touched == []
    assert all(canary.encode() not in raw for canary in CANARIES)
    assert recorder.failure_values() == ["worker.pipeline_failed"]


def test_unowned_names_values_and_types_are_dropped(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        with telemetry.http_operation("POST /api/" + CANARIES[9]) as ignored:
            ignored.set_status(200)
        with telemetry.http_operation("POST /api/demo") as operation:
            operation.set_job(CANARIES[0])
            with telemetry.stage(CANARIES[0]):
                pass
            with telemetry.tool_call(CANARIES[5]) as tool:
                tool.result(CANARIES[6], CANARIES[7])
            with telemetry.provider_attempt(CANARIES[1]) as attempt:
                attempt.usage(input_tokens=CANARIES[1], output_tokens=-5, response_model=CANARIES[1])
                attempt.result(CANARIES[1])
            telemetry.record_boundary_failure("worker", CANARIES[2])
            telemetry.record_boundary_failure(CANARIES[2], "pipeline_failed")
            telemetry.record_job_terminal(CANARIES[4], "failed", CANARIES[4])
            sentry_sdk.set_tag("free", CANARIES[10])
            sentry_sdk.get_current_span().set_data("free", CANARIES[10])
        raw = recorder.raw()
        transactions = recorder.transactions()
    assert all(canary.encode() not in raw for canary in CANARIES)
    assert [t["transaction"] for t in transactions] == ["POST /api/demo"]
    spans = transactions[0]["spans"]
    assert [(span["op"], span["description"]) for span in spans] == [
        ("ohmni.tool", "other"), ("gen_ai.chat", "chat claude-unknown"),
    ]
    attempt = spans[1]["data"]
    assert attempt["ohmni.usage_reported"] is False
    assert "gen_ai.usage.input_tokens" not in attempt and "gen_ai.response.model" not in attempt


def test_filters_drop_payloads_that_are_not_owned(monkeypatch):
    with offline_telemetry(monkeypatch):
        assert telemetry._filter_error_event({"event_id": "a" * 32, "message": CANARIES[0]}) is None
        forged = {"event_id": "a" * 32, "exception": {"values": [{
            "type": "OhmniBoundaryFailure", "value": "worker.pipeline_failed",
            "stacktrace": {"frames": [{"vars": {"x": CANARIES[3]}}]}}]}}
        assert telemetry._filter_error_event(forged) is None
        assert telemetry._filter_transaction({"type": "transaction", "transaction": CANARIES[9]}) is None
        assert telemetry._filter_metric({"name": CANARIES[0], "type": "counter", "value": 1}) is None


def test_envelope_gate_rejects_unexpected_item_types(monkeypatch):
    from sentry_sdk.envelope import Envelope, Item, PayloadRef
    with offline_telemetry(monkeypatch) as recorder:
        envelope = Envelope(items=[
            Item(payload=PayloadRef(json={"sid": "x"}), type="session"),
            Item(payload=PayloadRef(json={"x": 1}), type="client_report"),
            Item(payload=PayloadRef(bytes=b"profile"), type="profile"),
            Item(payload=PayloadRef(bytes=b"attachment"), type="attachment"),
            Item(payload=PayloadRef(json={"items": []}), type="log"),
            Item(payload=PayloadRef(json={"items": []}), type="span"),
        ])
        recorder.transport.capture_envelope(envelope)
        assert recorder.transport.envelopes == []
        assert sorted(recorder.transport.rejected_item_types) == sorted(
            ["session", "client_report", "profile", "attachment", "log", "span"])
        recorder.transport.rejected_item_types.clear()


# ---------------------------------------------------------------------------
# Channels, sampling and trace input
# ---------------------------------------------------------------------------

def test_metric_channel_off_really_suppresses_metrics(monkeypatch):
    with offline_telemetry(monkeypatch, OHMNI_TELEMETRY_METRICS="0") as recorder:
        with telemetry.http_operation("POST /api/demo"), telemetry.stage("erc"):
            telemetry.record_job_accepted("scripted_fixture")
        sentry_sdk.metrics.count("ohmni.jobs.accepted", 1)
        kinds = [kind for kind, _ in recorder.items()]
    assert "trace_metric" not in kinds and kinds == ["transaction"]


def test_metrics_carry_only_bounded_dimensions(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        telemetry.record_job_accepted("confirmed_project")
        telemetry.record_job_terminal("confirmed_project", "failed", "eda_tool_failed")
        telemetry.record_verifier_attempt("confirmed_project", "reject")
        metrics = recorder.metrics()
    assert {m["name"] for m in metrics} == {"ohmni.jobs.accepted", "ohmni.jobs.terminal", "ohmni.verifier.attempts"}
    for metric in metrics:
        assert set(metric["attributes"]) <= {"flow", "terminal", "reason", "outcome", "stage", "tool",
                                             "sentry.environment", "sentry.release"}


@pytest.mark.parametrize("header, expected", [
    (None, None),
    ("", None),
    (TRACE + "-" + PARENT, TRACE + "-" + PARENT),
    (TRACE + "-" + PARENT + "-1", TRACE + "-" + PARENT),
    (TRACE + "-" + PARENT + "-0", TRACE + "-" + PARENT),
    (TRACE.upper() + "-" + PARENT, None),
    ("0" * 32 + "-" + PARENT, None),
    (TRACE + "-" + PARENT + "-1-extra", None),
    (TRACE + "-" + PARENT + " " * 600, None),
    (12345, None),
])
def test_incoming_trace_headers_are_bounded_and_lose_their_sampling_flag(header, expected):
    assert telemetry.validated_parent(header, "sentry-sample_rate=1,other=" + CANARIES[10]) == expected


def test_caller_sampling_cannot_override_the_local_rate(monkeypatch):
    with offline_telemetry(monkeypatch, OHMNI_TRACE_SAMPLE_RATE="0") as recorder:
        with telemetry.http_operation("POST /api/demo", TRACE + "-" + PARENT + "-1", "sentry-sampled=true"):
            telemetry.record_boundary_failure("worker", "pipeline_failed")
        assert recorder.transactions() == []
        # Errors are independent of trace sampling and keep their trace id.
        [event] = recorder.events()
        assert event["contexts"]["trace"]["trace_id"] == TRACE
    with offline_telemetry(monkeypatch, OHMNI_TRACE_SAMPLE_RATE="1") as recorder:
        with telemetry.http_operation("POST /api/demo", TRACE + "-" + PARENT + "-0"):
            pass
        [transaction] = recorder.transactions()
        assert transaction["contexts"]["trace"]["parent_span_id"] == PARENT


def test_worker_handoff_connects_threads_and_inherits_the_local_decision(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        handoffs = []
        with telemetry.http_operation("POST /api/projects/{project}/revisions/{revision}/run", TRACE + "-" + PARENT):
            handoffs.append(telemetry.capture_handoff())
        def worker():
            with telemetry.worker_operation(handoffs[0], "confirmed_project", "abcdef012345"), \
                    telemetry.stage("synthesis"):
                    pass
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        http, work = recorder.transactions()
    assert http["contexts"]["trace"]["trace_id"] == work["contexts"]["trace"]["trace_id"] == TRACE
    assert work["contexts"]["trace"]["parent_span_id"] == http["contexts"]["trace"]["span_id"]
    assert work["contexts"]["trace"]["data"]["ohmni.job_id"] == "abcdef012345"
    assert [span["description"] for span in work["spans"]] == ["synthesis"]


def test_concurrent_operations_do_not_mix_parents_tags_or_failures(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        barrier = threading.Barrier(2)
        traces = {"a": "1" * 31 + "a", "b": "2" * 31 + "b"}
        def request(name):
            with telemetry.http_operation("POST /api/demo", traces[name] + "-" + PARENT):
                barrier.wait()
                with telemetry.stage("synthesis" if name == "a" else "routing"):
                    barrier.wait()
                    if name == "a":
                        telemetry.record_boundary_failure("worker", "pipeline_failed")
                barrier.wait()
        threads = [threading.Thread(target=request, args=(name,)) for name in traces]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        transactions = {t["contexts"]["trace"]["trace_id"]: t for t in recorder.transactions()}
        events = recorder.events()
    assert [s["description"] for s in transactions[traces["a"]]["spans"]] == ["synthesis"]
    assert [s["description"] for s in transactions[traces["b"]]["spans"]] == ["routing"]
    assert len(events) == 1 and events[0]["contexts"]["trace"]["trace_id"] == traces["a"]


def test_one_issue_per_operation_unless_separately_reported(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        with telemetry.http_operation("POST /api/project-plans"):
            telemetry.record_boundary_failure("provider", "provider_timeout")
            telemetry.record_boundary_failure("planner", "planner_unavailable")
            telemetry.record_separate_failure("persistence", "job_persist_failed")
        assert recorder.failure_values() == ["provider.provider_timeout", "persistence.job_persist_failed"]


# ---------------------------------------------------------------------------
# Provider and native tool boundaries
# ---------------------------------------------------------------------------

def _message(payload, usage=(100, 20), cache=None, stop_reason="tool_use"):
    values = None if usage is None else {"input_tokens": usage[0], "output_tokens": usage[1]}
    if cache and values is not None:
        values.update(cache_read_input_tokens=cache[0], cache_creation_input_tokens=cache[1])
    return SimpleNamespace(
        stop_reason=stop_reason, model="claude-sonnet-5-20261001",
        usage=None if values is None else SimpleNamespace(**values),
        content=[SimpleNamespace(type="tool_use", name="emit_board", input=payload)],
    )


class Board(__import__("pydantic").BaseModel):
    name: str


class Messages:
    def __init__(self, responses):
        self.responses = list(responses)

    def create(self, **_kwargs):
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def _provider(*responses):
    return AnthropicProvider(api_key="test-key", client=SimpleNamespace(messages=Messages(responses)))


def test_provider_outage_is_one_owned_issue_without_vendor_text(monkeypatch):
    APITimeoutError = type("APITimeoutError", (Exception,), {})
    with offline_telemetry(monkeypatch) as recorder:
        with telemetry.http_operation("POST /api/project-plans"):
            with pytest.raises(StructuredGenerationError):
                _provider(APITimeoutError(CANARIES[1])).complete_structured(
                    instructions=CANARIES[0], data=CANARIES[0], schema=Board)
            telemetry.record_boundary_failure("planner", "plan_output_rejected")
        raw = recorder.raw()
        [transaction] = recorder.transactions()
    assert recorder.failure_values() == ["provider.provider_timeout"]
    [span] = transaction["spans"]
    assert span["op"] == "gen_ai.chat" and span["status"] == "internal_error"
    assert span["data"]["ohmni.provider.outcome"] == "provider_timeout"
    assert span["data"]["ohmni.synthetic"] is True
    assert all(canary.encode() not in raw for canary in CANARIES)


def test_provider_usage_reports_only_observed_counts(monkeypatch):
    with offline_telemetry(monkeypatch) as recorder:
        with telemetry.http_operation("POST /api/project-plans"):
            provider = _provider(_message({"name": CANARIES[1]}, usage=None),
                                 _message({"name": "x"}, cache=(30, 7)),
                                 _message({"bad": CANARIES[1]}), _message({"bad": 1}), _message({"bad": 2}))
            provider.complete_structured(instructions="i", data="d", schema=Board)
            provider.complete_structured(instructions="i", data="d", schema=Board)
            with pytest.raises(StructuredGenerationError):
                provider.complete_structured(instructions="i", data="d", schema=Board)
        [transaction] = recorder.transactions()
        raw = recorder.raw()
    absent, cached, *retries = [span["data"] for span in transaction["spans"]]
    assert absent["ohmni.usage_reported"] is False
    assert not any(key.startswith("gen_ai.usage") for key in absent)
    assert cached["gen_ai.usage.input_tokens"] == 137 and cached["gen_ai.usage.output_tokens"] == 20
    assert cached["gen_ai.usage.input_tokens.cached"] == 30
    assert cached["gen_ai.usage.input_tokens.cache_write"] == 7
    assert cached["gen_ai.usage.total_tokens"] == 157
    assert cached["gen_ai.response.model"] == "claude-sonnet-5-20261001"
    assert [r["ohmni.provider.outcome"] for r in retries] == ["schema_rejected"] * 3
    assert [r["ohmni.provider.attempt"] for r in retries] == [1, 2, 3]
    assert recorder.failure_values() == ["provider.provider_output_rejected"]
    assert recorder.events()[0]["level"] == "warning"
    assert CANARIES[1].encode() not in raw
    assert recorder.metric_count("ohmni.provider.calls") == 5


def test_native_tool_outcomes_are_distinct_and_carry_no_command_details(monkeypatch, tmp_path):
    script = tmp_path / CANARIES[8]
    script.mkdir()
    with offline_telemetry(monkeypatch) as recorder:
        with telemetry.http_operation("POST /api/demo"):
            ok = run_tool([sys.executable, "-c", f"print('{CANARIES[7]}')", CANARIES[5]], timeout=30,
                          environment={"X": CANARIES[6], "PATH": ""})
            assert ok.returncode == 0
            assert run_tool([sys.executable, "-c", "import sys; sys.exit(3)"], timeout=30).returncode == 3
            with pytest.raises(subprocess.TimeoutExpired):
                run_tool([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.2)
            with pytest.raises(OSError):
                run_tool([str(script / "kicad-cli")], timeout=5)
        [transaction] = recorder.transactions()
        raw = recorder.raw()
    outcomes = [(s["description"], s["data"]["ohmni.execution_outcome"], s["data"].get("ohmni.exit_code"))
                for s in transaction["spans"]]
    assert outcomes == [("pdf_worker", "ok", 0), ("pdf_worker", "nonzero_exit", 3),
                        ("pdf_worker", "timeout", None), ("kicad", "spawn_failed", None)]
    assert all(canary.encode() not in raw for canary in CANARIES)


def test_tool_classification_is_a_whitelist():
    assert telemetry.classify_tool(["/opt/kicad/bin/kicad-cli", "sch", "erc"]) == "kicad"
    assert telemetry.classify_tool([r"C:\KiCad\bin\kicad-cli.exe"]) in {"kicad", "other"}
    assert telemetry.classify_tool(["ngspice", "-b"]) == "ngspice"
    assert telemetry.classify_tool(["java", "-jar", "freerouting.jar"]) == "freerouting"
    assert telemetry.classify_tool([CANARIES[5]]) == "other"
    assert telemetry.classify_tool("kicad-cli") == "other"
