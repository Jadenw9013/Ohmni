"""Ohmni's single telemetry adapter: the only production module that imports Sentry.

Telemetry here exists to explain why a run stopped, never to observe what was
designed. Every rule below follows from that and from SECURITY.md:

* **Off is the default and off is inert.** Unless the owner explicitly enables
  it, nothing imports ``sentry_sdk``, no client or transport exists, and every
  public function returns immediately. A missing SDK or an invalid setting
  disables telemetry; it never stops the product from starting.
* **Owned vocabulary only.** Callers pass constant names from the enumerations
  in this module plus bounded numbers. Unknown names collapse to ``other`` or are
  dropped. No caller can hand this module a prompt, a path, a request or an
  exception, because no function accepts one.
* **No inspection.** Nothing here calls ``str``/``repr``/``getattr`` on an
  application object. Failures are reported as constructed
  ``OhmniBoundaryFailure`` events carrying a site and code; no exception object,
  ``exc_info`` or traceback ever reaches the SDK. Context managers never pass the
  application exception to the SDK's own ``__exit__``.
* **Telemetry cannot change the work.** Each context manager runs its body
  exactly once, never suppresses or replaces an exception, and every SDK call is
  independently guarded. A failing SDK costs a span, not a job.
* **Allowlists at the exit.** ``before_send``/``before_send_transaction``/
  ``before_send_metric`` rebuild each payload from an allowlist, and the
  transport drops any envelope item that is not an error event, transaction or
  trace metric. Logs, sessions, profiles, attachments, client reports and
  streamed spans never leave the process.

The SDK still does ingestion, grouping, trace waterfalls and metrics. This file is
deliberately small rather than a second tracing framework.
"""

from __future__ import annotations

import math
import os
import re
import threading
import time
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

#: The exact pinned SDK version this adapter was audited against. A different
#: installed version disables telemetry instead of guessing at its behaviour.
PINNED_SDK_VERSION = "2.72.0"

ENVIRONMENTS = frozenset({"local", "preview", "production", "hackathon"})
FLOWS = frozenset({
    "confirmed_project", "scripted_fixture", "model_proposed",
    "planning", "assistant", "brief", "other",
})
#: Normalized HTTP operations that open a transaction. Health, static and poll
#: traffic is deliberately absent: it would be volume without explanation.
ROUTES = frozenset({
    "POST /api/project-plans",
    "POST /api/project-plans/{plan}/confirm",
    "POST /api/projects/{project}/revisions/{revision}/assistant",
    "POST /api/projects/{project}/revisions/{revision}/assistant/{turn}/apply",
    "POST /api/projects/{project}/revisions/{revision}/run",
    "POST /api/demo",
    "POST /api/brief",
})
STAGES = frozenset({
    "plan_proposal", "assistant_proposal", "brief_interpretation",
    "synthesis", "semantic_verification", "schematic", "erc",
    "design_orchestrate", "placement", "routing", "routing_verification",
    "pcb_compile", "drc", "manufacturing", "packaging",
    "report_validation", "publication",
})
TOOLS = frozenset({"kicad", "ngspice", "freerouting", "pdf_worker", "other"})
EXECUTION_OUTCOMES = frozenset({"ok", "timeout", "spawn_failed", "nonzero_exit", "error"})
ENGINEERING_OUTCOMES = frozenset({"pass", "reject", "unknown", "not_applicable", "not_attempted"})
PROVIDER_OUTCOMES = frozenset({
    "ok", "schema_rejected", "truncated", "refused", "no_tool_call",
    "provider_timeout", "provider_connection", "provider_rate_limited",
    "provider_auth", "provider_status", "provider_error",
})
JOB_TERMINALS = frozenset({"complete", "failed"})
JOB_REASONS = frozenset({
    "none", "worker_start_failed", "pipeline_failed", "progress_publication_failed",
    "job_state_invalid", "server_restarted", "routing_incomplete", "eda_tool_failed",
})
#: Site -> codes. An issue is grouped by exactly (site, code).
FAILURE_CODES: Mapping[str, frozenset[str]] = {
    "provider": frozenset({
        "provider_timeout", "provider_connection", "provider_rate_limited",
        "provider_auth", "provider_status", "provider_error",
        "provider_output_rejected", "provider_refused",
    }),
    "planner": frozenset({"plan_output_rejected", "planner_unavailable"}),
    "assistant": frozenset({"assistant_output_rejected", "assistant_unavailable"}),
    "brief": frozenset({"brief_unavailable"}),
    "worker": frozenset({
        "pipeline_failed", "eda_tool_failed", "progress_publication_failed",
        "worker_start_failed",
    }),
    "persistence": frozenset({"job_persist_failed", "job_start_unavailable"}),
}
LEVELS = frozenset({"error", "warning"})

_OWNED_EVENT_TYPE = "OhmniBoundaryFailure"
_SERVER_NAME = "ohmni-backend"
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX16 = re.compile(r"^[0-9a-f]{16}$")
_JOB_ID = re.compile(r"^[0-9a-f]{12}$")
_MODEL = re.compile(r"^claude-[a-z0-9][a-z0-9.\-]{0,62}$")
_RELEASE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+\-]{0,79}$")
_ISO_TIME = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]{8,20}(?:Z|[+\-][0-9:]{4,5})?$")
_SENTRY_TRACE = re.compile(r"^([0-9a-f]{32})-([0-9a-f]{16})(?:-[01])?$")
_DSN = re.compile(
    r"^https://(?P<key>[0-9a-f]{32})@(?P<host>[a-z0-9][a-z0-9.\-]{0,200})/(?P<project>[0-9]{1,20})$"
)
#: Real ingestion hosts. Any other host is accepted only with an injected
#: (recording) transport, so a synthetic test DSN can never reach the network.
_INGEST_HOST = re.compile(r"^o[0-9]{1,20}\.ingest(?:\.[a-z]{2})?\.sentry\.io$")
_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"", "0", "false", "no", "off"})
#: SDK variables that would print, redirect or re-parent telemetry. Their
#: presence refuses activation rather than being silently overridden.
_UNSAFE_SDK_ENV = ("SENTRY_PRINT_ENVELOPES", "SENTRY_TRACE", "SENTRY_BAGGAGE", "SENTRY_SPOTLIGHT")
_MAX_HEADER = 512
_MAX_EXIT_CODE = 2**32
_ALLOWED_ITEM_TYPES = frozenset({"event", "transaction", "trace_metric"})


@dataclass(frozen=True)
class TelemetryConfig:
    """Validated settings. ``state`` explains a disabled result with a constant."""

    enabled: bool = False
    state: str = "disabled"
    dsn: str | None = None
    environment: str = "local"
    release: str = "ohmni@unknown"
    trace_sample_rate: float = 0.0
    metrics: bool = False
    logs: bool = False

    def __repr__(self) -> str:  # never print a DSN
        return f"TelemetryConfig(enabled={self.enabled}, state={self.state!r})"


def _flag(raw: str | None) -> bool | None:
    value = (raw or "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    return None


def configure_from_environment(environ: Mapping[str, str] | None = None) -> TelemetryConfig:
    """Parse owned settings without raising and without echoing any value."""
    try:
        env = os.environ if environ is None else environ
        enabled = _flag(env.get("OHMNI_TELEMETRY_ENABLED"))
        if not enabled:
            return TelemetryConfig(state="disabled" if enabled is False else "invalid")
        for name in _UNSAFE_SDK_ENV:
            if (env.get(name) or "").strip():
                return TelemetryConfig(state="unsafe_environment")
        dsn = (env.get("SENTRY_DSN") or "").strip()
        if not _DSN.fullmatch(dsn):
            return TelemetryConfig(state="invalid")
        environment = (env.get("OHMNI_ENV") or "local").strip()
        if environment not in ENVIRONMENTS:
            return TelemetryConfig(state="invalid")
        release = (env.get("SENTRY_RELEASE") or "ohmni@unknown").strip()
        if not _RELEASE.fullmatch(release):
            return TelemetryConfig(state="invalid")
        raw_rate = (env.get("OHMNI_TRACE_SAMPLE_RATE") or "0").strip()
        try:
            rate = float(raw_rate)
        except ValueError:
            return TelemetryConfig(state="invalid")
        if not math.isfinite(rate) or not 0.0 <= rate <= 1.0:
            return TelemetryConfig(state="invalid")
        metrics = _flag(env.get("OHMNI_TELEMETRY_METRICS"))
        logs = _flag(env.get("OHMNI_TELEMETRY_LOGS"))
        if metrics is None or logs is None:
            return TelemetryConfig(state="invalid")
        return TelemetryConfig(
            enabled=True, state="configured", dsn=dsn, environment=environment,
            release=release, trace_sample_rate=rate, metrics=metrics, logs=logs,
        )
    except BaseException:  # noqa: BLE001 - configuration never prevents startup
        return TelemetryConfig(state="invalid")


# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------

class _Runtime:
    """Process-wide adapter state; replaced wholesale, never mutated piecemeal."""

    def __init__(self, sdk: Any = None, config: TelemetryConfig | None = None) -> None:
        self.sdk = sdk
        self.config = config or TelemetryConfig()

    @property
    def active(self) -> bool:
        return self.sdk is not None and self.config.enabled


_RUNTIME = _Runtime()
_LOCK = threading.Lock()


@dataclass
class _Operation:
    """Per request/worker state, private to this module and one context."""

    flow: str
    transaction: Any
    failure_reported: bool = False
    provider_calls: int = 0
    engineering_rejected: bool = False


_OPERATION: ContextVar[_Operation | None] = ContextVar("ohmni_telemetry_operation", default=None)


def enabled() -> bool:
    return _RUNTIME.active


def state() -> str:
    """A constant describing why telemetry is (not) active, for local diagnostics."""
    return "enabled" if _RUNTIME.active else _RUNTIME.config.state


# ---------------------------------------------------------------------------
# Outgoing allowlists
# ---------------------------------------------------------------------------

def _owned_str(value: Any, allowed: frozenset[str]) -> str | None:
    return value if type(value) is str and value in allowed else None


def _bounded_int(value: Any, low: int = 0, high: int = 2**53) -> int | None:
    return value if type(value) is int and low <= value <= high else None


def _finite(value: Any) -> float | None:
    if type(value) in (int, float) and type(value) is not bool and math.isfinite(value):
        return float(value)
    return None


def _timestamp(value: Any) -> str | float | None:
    if type(value) is str and _ISO_TIME.fullmatch(value):
        return value
    return _finite(value)


def _model(value: Any) -> str | None:
    return value if type(value) is str and _MODEL.fullmatch(value) else None


_FAILURE_VALUES = frozenset(f"{site}.{code}" for site, codes in FAILURE_CODES.items() for code in codes)
_SPAN_OPS = frozenset({"http.server", "ohmni.worker", "ohmni.stage", "ohmni.tool", "gen_ai.chat"})

_DATA_RULES: Mapping[str, Any] = {
    "ohmni.flow": lambda v: _owned_str(v, FLOWS),
    "ohmni.route": lambda v: _owned_str(v, ROUTES),
    "ohmni.stage": lambda v: _owned_str(v, STAGES),
    "ohmni.tool": lambda v: _owned_str(v, TOOLS),
    "ohmni.execution_outcome": lambda v: _owned_str(v, EXECUTION_OUTCOMES),
    "ohmni.engineering_outcome": lambda v: _owned_str(v, ENGINEERING_OUTCOMES),
    "ohmni.provider.outcome": lambda v: _owned_str(v, PROVIDER_OUTCOMES),
    "ohmni.exit_code": lambda v: _bounded_int(v, -_MAX_EXIT_CODE, _MAX_EXIT_CODE),
    "ohmni.job_id": lambda v: v if type(v) is str and _JOB_ID.fullmatch(v) else None,
    "ohmni.job.reused": lambda v: v if type(v) is bool else None,
    "ohmni.http.status_code": lambda v: _bounded_int(v, 100, 599),
    "ohmni.usage_reported": lambda v: v if type(v) is bool else None,
    "ohmni.synthetic": lambda v: v if type(v) is bool else None,
    "ohmni.provider.attempt": lambda v: _bounded_int(v, 1, 64),
    "gen_ai.operation.name": lambda v: v if v == "chat" else None,
    "gen_ai.provider.name": lambda v: v if v == "anthropic" else None,
    "gen_ai.request.model": _model,
    "gen_ai.response.model": _model,
    "gen_ai.usage.input_tokens": _bounded_int,
    "gen_ai.usage.input_tokens.cached": _bounded_int,
    "gen_ai.usage.input_tokens.cache_write": _bounded_int,
    "gen_ai.usage.output_tokens": _bounded_int,
    "gen_ai.usage.total_tokens": _bounded_int,
    "error.type": lambda v: _owned_str(v, PROVIDER_OUTCOMES),
    "sentry.op": lambda v: _owned_str(v, _SPAN_OPS),
    "sentry.origin": lambda v: v if v == "manual" else None,
    "sentry.source": lambda v: v if v in ("route", "task", "custom") else None,
    "sentry.sample_rate": lambda v: _finite(v) if _finite(v) is not None and 0 <= v <= 1 else None,
}
_TAG_RULES: Mapping[str, Any] = {
    "ohmni.flow": lambda v: _owned_str(v, FLOWS),
    "ohmni.site": lambda v: _owned_str(v, frozenset(FAILURE_CODES)),
    "ohmni.code": lambda v: _owned_str(v, frozenset(c for cs in FAILURE_CODES.values() for c in cs)),
    "ohmni.owned": lambda v: v if v == "1" else None,
}


def _clean_data(data: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if type(data) is not dict:
        return result
    for key, rule in _DATA_RULES.items():
        if key in data:
            value = rule(data[key])
            if value is not None:
                result[key] = value
    return result


def _clean_tags(tags: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if type(tags) is not dict:
        return result
    for key, rule in _TAG_RULES.items():
        if key in tags:
            value = rule(tags[key])
            if value is not None:
                result[key] = value
    return result


def _span_description(op: Any, description: Any) -> str | None:
    if type(description) is not str:
        return None
    if op == "http.server":
        return _owned_str(description, ROUTES)
    if op == "ohmni.worker":
        flow = description.removeprefix("worker ")
        return description if description.startswith("worker ") and flow in FLOWS else None
    if op == "ohmni.stage":
        return _owned_str(description, STAGES)
    if op == "ohmni.tool":
        return _owned_str(description, TOOLS)
    if op == "gen_ai.chat":
        model = description.removeprefix("chat ")
        return description if description.startswith("chat ") and _model(model) else None
    return None


def _trace_context(trace: Any) -> dict[str, Any] | None:
    if type(trace) is not dict:
        return None
    trace_id = trace.get("trace_id")
    span_id = trace.get("span_id")
    if type(trace_id) is not str or not _HEX32.fullmatch(trace_id):
        return None
    if type(span_id) is not str or not _HEX16.fullmatch(span_id):
        return None
    result: dict[str, Any] = {"trace_id": trace_id, "span_id": span_id}
    parent = trace.get("parent_span_id")
    if type(parent) is str and _HEX16.fullmatch(parent):
        result["parent_span_id"] = parent
    op = _owned_str(trace.get("op"), _SPAN_OPS)
    if op is not None:
        result["op"] = op
    status = trace.get("status")
    if type(status) is str and re.fullmatch(r"[a-z_]{1,32}", status):
        result["status"] = status
    if trace.get("origin") == "manual":
        result["origin"] = "manual"
    data = _clean_data(trace.get("data"))
    if data:
        result["data"] = data
    return result


def _common(event: dict[str, Any]) -> dict[str, Any] | None:
    config = _RUNTIME.config
    event_id = event.get("event_id")
    if type(event_id) is not str or not _HEX32.fullmatch(event_id):
        return None
    result: dict[str, Any] = {
        "event_id": event_id,
        "platform": "python",
        "server_name": _SERVER_NAME,
        "environment": config.environment,
        "release": config.release,
    }
    for key in ("timestamp", "start_timestamp"):
        value = _timestamp(event.get(key))
        if value is not None:
            result[key] = value
    sdk = event.get("sdk")
    if type(sdk) is dict and sdk.get("name") == "sentry.python" and sdk.get("version") == PINNED_SDK_VERSION:
        result["sdk"] = {"name": "sentry.python", "version": PINNED_SDK_VERSION}
    tags = _clean_tags(event.get("tags"))
    if tags:
        result["tags"] = tags
    return result


def _filter_error_event(event: Any, _hint: Any = None) -> dict[str, Any] | None:
    """Keep only an Ohmni-constructed boundary failure; drop anything else."""
    try:
        if type(event) is not dict or event.get("type") not in (None, "error"):
            return None
        exception = event.get("exception")
        values = exception.get("values") if type(exception) is dict else None
        if type(values) is not list or len(values) != 1 or type(values[0]) is not dict:
            return None
        failure = values[0]
        if failure.get("type") != _OWNED_EVENT_TYPE or failure.get("value") not in _FAILURE_VALUES:
            return None
        if "stacktrace" in failure:
            return None
        result = _common(event)
        if result is None:
            return None
        level = event.get("level")
        result["level"] = level if level in LEVELS else "error"
        site, code = failure["value"].split(".", 1)
        result["exception"] = {"values": [{
            "type": _OWNED_EVENT_TYPE, "value": failure["value"],
            "mechanism": {"type": "ohmni.boundary", "handled": True},
        }]}
        result["fingerprint"] = [_OWNED_EVENT_TYPE, site, code]
        contexts = event.get("contexts")
        trace = _trace_context(contexts.get("trace")) if type(contexts) is dict else None
        if trace is not None:
            trace.pop("data", None)
            result["contexts"] = {"trace": trace}
        return result
    except BaseException:  # noqa: BLE001 - a filter failure drops the event
        return None


def _filter_transaction(event: Any, _hint: Any = None) -> dict[str, Any] | None:
    """Rebuild a transaction from owned names, ids, timings and data keys."""
    try:
        if type(event) is not dict or event.get("type") != "transaction":
            return None
        contexts = event.get("contexts")
        trace = _trace_context(contexts.get("trace")) if type(contexts) is dict else None
        if trace is None:
            return None
        name = _span_description(trace.get("op"), event.get("transaction"))
        if name is None:
            return None
        result = _common(event)
        if result is None or "start_timestamp" not in result or "timestamp" not in result:
            return None
        result.update(type="transaction", transaction=name, contexts={"trace": trace})
        info = event.get("transaction_info")
        source = info.get("source") if type(info) is dict else None
        result["transaction_info"] = {"source": source if source in ("route", "task", "custom") else "custom"}
        spans = []
        for span in event.get("spans") or []:
            if type(span) is not dict:
                continue
            op = _owned_str(span.get("op"), _SPAN_OPS)
            description = _span_description(op, span.get("description"))
            ids = [span.get(key) for key in ("trace_id", "span_id", "parent_span_id")]
            if op is None or description is None or ids[0] != trace["trace_id"]:
                continue
            if type(ids[1]) is not str or not _HEX16.fullmatch(ids[1]):
                continue
            if type(ids[2]) is not str or not _HEX16.fullmatch(ids[2]):
                continue
            start = _timestamp(span.get("start_timestamp"))
            end = _timestamp(span.get("timestamp"))
            if start is None or end is None:
                continue
            cleaned = {
                "trace_id": ids[0], "span_id": ids[1], "parent_span_id": ids[2],
                "op": op, "description": description, "origin": "manual",
                "start_timestamp": start, "timestamp": end,
            }
            status = span.get("status")
            if type(status) is str and re.fullmatch(r"[a-z_]{1,32}", status):
                cleaned["status"] = status
            data = _clean_data(span.get("data"))
            if data:
                cleaned["data"] = data
            spans.append(cleaned)
        result["spans"] = spans
        return result
    except BaseException:  # noqa: BLE001 - a filter failure drops the transaction
        return None


_METRIC_NAMES = frozenset({
    "ohmni.jobs.accepted", "ohmni.jobs.terminal", "ohmni.stage.duration",
    "ohmni.verifier.attempts", "ohmni.repair.attempts", "ohmni.provider.calls",
})
_METRIC_ATTRIBUTE_RULES: Mapping[str, Any] = {
    "flow": lambda v: _owned_str(v, FLOWS),
    "stage": lambda v: _owned_str(v, STAGES),
    "tool": lambda v: _owned_str(v, TOOLS),
    "outcome": lambda v: _owned_str(v, EXECUTION_OUTCOMES | ENGINEERING_OUTCOMES | PROVIDER_OUTCOMES),
    "terminal": lambda v: _owned_str(v, JOB_TERMINALS),
    "reason": lambda v: _owned_str(v, JOB_REASONS),
}


def _filter_metric(metric: Any, _hint: Any = None) -> dict[str, Any] | None:
    """Metrics are dropped unless the metric channel was explicitly enabled."""
    try:
        if not _RUNTIME.config.metrics or type(metric) is not dict:
            return None
        name = _owned_str(metric.get("name"), _METRIC_NAMES)
        kind = metric.get("type")
        value = _finite(metric.get("value"))
        if name is None or kind not in ("counter", "distribution") or value is None:
            return None
        attributes: dict[str, Any] = {}
        raw = metric.get("attributes")
        if type(raw) is dict:
            for key, rule in _METRIC_ATTRIBUTE_RULES.items():
                owned = rule(raw.get(key))
                if owned is not None:
                    attributes[key] = owned
        config = _RUNTIME.config
        attributes["sentry.environment"] = config.environment
        attributes["sentry.release"] = config.release
        result: dict[str, Any] = {
            "name": name, "type": kind, "value": value, "attributes": attributes,
            "timestamp": _finite(metric.get("timestamp")) or time.time(),
        }
        unit = metric.get("unit")
        if unit in ("millisecond", None):
            result["unit"] = unit
        trace_id = metric.get("trace_id")
        if type(trace_id) is str and _HEX32.fullmatch(trace_id):
            result["trace_id"] = trace_id
        span_id = metric.get("span_id")
        if type(span_id) is str and _HEX16.fullmatch(span_id):
            result["span_id"] = span_id
        return result
    except BaseException:  # noqa: BLE001 - a filter failure drops the metric
        return None


def _drop(*_args: Any) -> None:
    """Logs and breadcrumbs are outside the core: always dropped."""
    return


def gate_envelope_items(items: list[Any]) -> tuple[list[Any], list[str]]:
    """Split envelope items into allowed items and rejected type names."""
    kept: list[Any] = []
    rejected: list[str] = []
    for item in items:
        try:
            kind = item.type if type(getattr(item, "type", None)) is str else "unknown"
        except BaseException:  # noqa: BLE001
            kind = "unknown"
        if kind in _ALLOWED_ITEM_TYPES:
            kept.append(item)
        else:
            rejected.append(kind if kind and len(kind) <= 32 else "unknown")
    return kept, rejected


def _make_transports(sdk: Any) -> tuple[type, type]:
    from sentry_sdk.envelope import Envelope
    from sentry_sdk.transport import HttpTransport, Transport

    def gated(envelope: Any) -> Any:
        kept, _rejected = gate_envelope_items(list(envelope.items))
        if not kept:
            return None
        return Envelope(headers=dict(envelope.headers), items=kept)

    class GatedHttpTransport(HttpTransport):
        """The production transport: the same HTTP transport, behind the item gate."""

        def capture_envelope(self, envelope: Any) -> None:
            outgoing = gated(envelope)
            if outgoing is not None:
                super().capture_envelope(outgoing)

    class RecordingTransport(Transport):
        """Offline evidence: keeps serialized envelopes in memory, sends nothing."""

        def __init__(self, options: Any = None) -> None:
            super().__init__(options)
            self.envelopes: list[bytes] = []
            self.rejected_item_types: list[str] = []
            self._lock = threading.Lock()

        def capture_envelope(self, envelope: Any) -> None:
            kept, rejected = gate_envelope_items(list(envelope.items))
            with self._lock:
                self.rejected_item_types.extend(rejected)
                if kept:
                    self.envelopes.append(Envelope(headers=dict(envelope.headers), items=kept).serialize())

    return GatedHttpTransport, RecordingTransport


def recording_transport() -> Any:
    """A fresh in-memory transport for tests and the local fault harness."""
    import sentry_sdk

    return _make_transports(sentry_sdk)[1]()


def _sampler(context: Any) -> float:
    """Local sampling; a caller-supplied decision is never honoured.

    Only the worker continuation of this process's own HTTP transaction, which
    carries an explicit internal marker, inherits its parent's decision.
    """
    try:
        rate = _RUNTIME.config.trace_sample_rate
        if type(context) is dict and context.get("ohmni_trusted_parent") is True:
            parent = context.get("parent_sampled")
            if type(parent) is bool:
                return 1.0 if parent else 0.0
        return rate
    except BaseException:  # noqa: BLE001
        return 0.0


def _sdk_options(config: TelemetryConfig, transport: Any) -> dict[str, Any]:
    return {
        "dsn": config.dsn,
        "transport": transport,
        "release": config.release,
        "environment": config.environment,
        "server_name": _SERVER_NAME,
        "debug": False,
        "spotlight": False,
        "default_integrations": False,
        "auto_enabling_integrations": False,
        "integrations": [],
        "include_local_variables": False,
        "include_source_context": False,
        "attach_stacktrace": False,
        "max_breadcrumbs": 0,
        "max_request_body_size": "never",
        "sample_rate": 1.0,
        "traces_sampler": _sampler,
        "trace_lifecycle": "static",
        "stream_gen_ai_spans": False,
        "trace_propagation_targets": [],
        "propagate_traces": False,
        "auto_session_tracking": False,
        "send_client_reports": False,
        "profiles_sample_rate": None,
        "enable_logs": False,
        "enable_metrics": config.metrics,
        "transport_queue_size": 100,
        "shutdown_timeout": 2,
        "before_send": _filter_error_event,
        "before_send_transaction": _filter_transaction,
        "before_send_metric": _filter_metric,
        "before_send_log": _drop,
        "before_breadcrumb": _drop,
        "data_collection": {
            "user_info": False,
            "cookies": {"mode": "off"},
            "http_headers": {"request": {"mode": "off"}},
            "http_bodies": [],
            "url_query_params": {"mode": "off"},
            "graphql": {"document": False, "variables": False},
            "gen_ai": {"inputs": False, "outputs": False},
            "database_query_data": False,
            "queues": False,
            "stack_frame_variables": False,
            "frame_context_lines": 0,
        },
    }


def initialize(config: TelemetryConfig, *, transport: Any = None) -> bool:
    """Start the SDK when ``config`` is enabled; return whether it is active.

    ``transport`` is for tests and the local fault harness only. Without it, the
    DSN must name a real Sentry ingestion host and the gated HTTP transport is
    used. Any failure leaves telemetry disabled and the caller unaffected.
    """
    global _RUNTIME
    with _LOCK:
        try:
            if _RUNTIME.active:
                return True
            if type(config) is not TelemetryConfig or not config.enabled or config.dsn is None:
                _RUNTIME = _Runtime(config=config if type(config) is TelemetryConfig else TelemetryConfig())
                return False
            match = _DSN.fullmatch(config.dsn)
            if match is None or (transport is None and not _INGEST_HOST.fullmatch(match["host"])):
                _RUNTIME = _Runtime(config=TelemetryConfig(state="invalid"))
                return False
            import sentry_sdk  # the one production import of the SDK

            if getattr(sentry_sdk, "VERSION", None) != PINNED_SDK_VERSION:
                _RUNTIME = _Runtime(config=TelemetryConfig(state="sdk_version_mismatch"))
                return False
            if transport is None:
                transport = _make_transports(sentry_sdk)[0]
            # Set before init so hooks see the configuration; marked active only
            # after init succeeds and nothing unexpected was installed.
            _RUNTIME = _Runtime(config=config)
            sentry_sdk.init(**_sdk_options(config, transport))
            client = sentry_sdk.get_client()
            if not client.is_active() or getattr(client, "integrations", {}):
                _close_quietly(sentry_sdk)
                _RUNTIME = _Runtime(config=TelemetryConfig(state="init_failed"))
                return False
            _RUNTIME = _Runtime(sdk=sentry_sdk, config=config)
            return True
        except BaseException:  # noqa: BLE001 - a broken SDK never prevents startup
            try:
                import sys

                module = sys.modules.get("sentry_sdk")
                if module is not None:
                    _close_quietly(module)
            except BaseException:  # noqa: BLE001, S110
                pass
            _RUNTIME = _Runtime(config=TelemetryConfig(state="init_failed"))
            return False


def _close_quietly(sdk: Any, timeout: float = 0) -> None:
    """Close the client and detach it, so a closed client is never reused."""
    try:
        client = sdk.get_client()
        if client.is_active():
            client.close(timeout=timeout)
    except BaseException:  # noqa: BLE001, S110
        pass
    try:
        sdk.get_global_scope().set_client(None)
    except BaseException:  # noqa: BLE001, S110
        pass


def shutdown(timeout_seconds: float = 2.0) -> None:
    """Flush with a short bound and disable. Upload completion is best effort."""
    global _RUNTIME
    with _LOCK:
        runtime = _RUNTIME
        _RUNTIME = _Runtime(config=TelemetryConfig(state="shutdown"))
    if runtime.sdk is None:
        return
    bound = timeout_seconds if _finite(timeout_seconds) is not None and 0 <= timeout_seconds <= 10 else 2.0
    _close_quietly(runtime.sdk, bound)


def flush(timeout_seconds: float = 2.0) -> None:
    """Bounded flush, used by tests and the local harness; never per request."""
    sdk = _RUNTIME.sdk
    if sdk is None:
        return
    try:
        sdk.flush(timeout=timeout_seconds)
    except BaseException:  # noqa: BLE001, S110
        pass


# ---------------------------------------------------------------------------
# Trace input and handoff
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TraceHandoff:
    """The only thing passed from a request thread to its worker thread."""

    trace_id: str
    parent_span_id: str
    sampled: bool | None


def validated_parent(sentry_trace: Any, baggage: Any = None) -> str | None:
    """Accept a bounded ``sentry-trace`` header and keep only its identifiers.

    The caller's sampling flag is removed so it cannot override the local rate,
    and baggage is ignored entirely: it can carry arbitrary key/values and a
    sampling decision, neither of which this server needs. Same-organization
    checks would not be authentication, so none is attempted.
    """
    del baggage
    if type(sentry_trace) is not str or len(sentry_trace) > _MAX_HEADER:
        return None
    match = _SENTRY_TRACE.fullmatch(sentry_trace.strip())
    if match is None or set(match[1]) == {"0"} or set(match[2]) == {"0"}:
        return None
    return f"{match[1]}-{match[2]}"


def capture_handoff() -> TraceHandoff | None:
    """Snapshot the current span's identifiers for an explicit thread handoff."""
    if not _RUNTIME.active:
        return None
    try:
        span = _RUNTIME.sdk.get_current_span()
        if span is None:
            return None
        trace_id, span_id, sampled = span.trace_id, span.span_id, span.sampled
        if type(trace_id) is not str or not _HEX32.fullmatch(trace_id):
            return None
        if type(span_id) is not str or not _HEX16.fullmatch(span_id):
            return None
        return TraceHandoff(trace_id, span_id, sampled if type(sampled) is bool else None)
    except BaseException:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------

class _NoopHandle:
    """Returned whenever telemetry is inactive; every method does nothing."""

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def outcome(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def usage(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def result(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def set_job(self, *_args: Any, **_kwargs: Any) -> None:
        return None


_NOOP = _NoopHandle()
#: A handle whose methods do nothing, for callers invoked outside an operation.
INERT_HANDLE = _NOOP


class _Guarded:
    """Shared enter/exit discipline: run the body once, never touch its exception."""

    _span: Any = None

    def _set(self, key: str, value: Any) -> None:
        span = self._span
        if span is None:
            return
        try:
            span.set_data(key, value)
        except BaseException:  # noqa: BLE001, S110
            pass

    def _status(self, value: str) -> None:
        span = self._span
        if span is None:
            return
        try:
            span.set_status(value)
        except BaseException:  # noqa: BLE001, S110
            pass

    def _close_span(self, failed: bool) -> None:
        span = self._span
        self._span = None
        if span is None:
            return
        try:
            if failed and getattr(self, "_explicit_status", None) is None:
                span.set_status("internal_error")
        except BaseException:  # noqa: BLE001, S110
            pass
        try:
            # The application exception is deliberately not forwarded.
            span.__exit__(None, None, None)
        except BaseException:  # noqa: BLE001, S110
            pass


class _OperationScope(_Guarded):
    """One transaction in a fresh isolation scope (HTTP request or worker)."""

    def __init__(self, *, op: str, name: str, source: str, flow: str,
                 parent: str | None, trusted_sampled: bool | None, data: dict[str, Any]) -> None:
        self._args = (op, name, source, flow, parent, trusted_sampled, data)
        self._scopes: list[Any] = []
        self._token: Any = None
        self._explicit_status: str | None = None
        self._started = 0.0

    def __enter__(self) -> Any:
        if not _RUNTIME.active:
            return _NOOP
        sdk = _RUNTIME.sdk
        op, name, source, flow, parent, trusted_sampled, data = self._args
        try:
            for factory in (sdk.isolation_scope, sdk.new_scope):
                manager = factory()
                manager.__enter__()
                self._scopes.append(manager)
            headers: dict[str, str] = {}
            if parent is not None:
                flag = "" if trusted_sampled is None else ("-1" if trusted_sampled else "-0")
                headers["sentry-trace"] = parent + flag
            transaction = sdk.continue_trace(headers, op=op, name=name, source=source)
            transaction = sdk.start_transaction(transaction, custom_sampling_context={
                "ohmni_trusted_parent": trusted_sampled is not None,
            })
            transaction.__enter__()
            self._span = transaction
            for key, value in data.items():
                self._set(key, value)
            self._set("ohmni.flow", flow)
            self._token = _OPERATION.set(_Operation(flow=flow, transaction=transaction))
            self._started = time.monotonic()
        except BaseException:  # noqa: BLE001 - telemetry setup never blocks the request
            self._unwind(failed=False)
            return _NOOP
        return self

    def set_status(self, status_code: int) -> None:
        code = _bounded_int(status_code, 100, 599)
        if code is None:
            return
        self._set("ohmni.http.status_code", code)
        self._explicit_status = "ok" if code < 400 else ("internal_error" if code >= 500 else "failed_precondition")
        self._status(self._explicit_status)

    def outcome(self, execution: str, engineering: str | None = None) -> None:
        execution = execution if execution in EXECUTION_OUTCOMES else "error"
        self._set("ohmni.execution_outcome", execution)
        if engineering in ENGINEERING_OUTCOMES:
            self._set("ohmni.engineering_outcome", engineering)
        if engineering == "not_attempted":
            self._explicit_status = "cancelled"
        else:
            self._explicit_status = "ok" if execution == "ok" else "internal_error"
        self._status(self._explicit_status)

    def set_job(self, job_id: str, *, reused: bool | None = None) -> None:
        if type(job_id) is str and _JOB_ID.fullmatch(job_id):
            self._set("ohmni.job_id", job_id)
        if type(reused) is bool:
            self._set("ohmni.job.reused", reused)

    def _unwind(self, failed: bool) -> None:
        if self._span is not None and not failed and self._explicit_status is None:
            self._status("ok")
        self._close_span(failed)
        if self._token is not None:
            try:
                _OPERATION.reset(self._token)
            except BaseException:  # noqa: BLE001
                _OPERATION.set(None)
            self._token = None
        while self._scopes:
            manager = self._scopes.pop()
            try:
                manager.__exit__(None, None, None)
            except BaseException:  # noqa: BLE001, S110
                pass

    def __exit__(self, exc_type: object, _exc: object, _tb: object) -> bool:
        try:
            self._unwind(failed=exc_type is not None)
        except BaseException:  # noqa: BLE001, S110
            pass
        return False


def http_operation(route: str, sentry_trace: Any = None, baggage: Any = None) -> Any:
    """A server transaction for one normalized, allowlisted POST route."""
    if not _RUNTIME.active or route not in ROUTES:
        return _Disabled()
    flow = {
        "POST /api/project-plans": "planning",
        "POST /api/project-plans/{plan}/confirm": "planning",
        "POST /api/brief": "brief",
        "POST /api/projects/{project}/revisions/{revision}/run": "confirmed_project",
    }.get(route, "assistant" if "/assistant" in route else "other")
    return _OperationScope(
        op="http.server", name=route, source="route", flow=flow,
        parent=validated_parent(sentry_trace, baggage), trusted_sampled=None,
        data={"ohmni.route": route},
    )


def worker_operation(handoff: TraceHandoff | None, flow: str, job_id: str | None = None) -> Any:
    """The whole worker lifetime, parented by the explicit request-thread handoff."""
    if not _RUNTIME.active:
        return _Disabled()
    flow = flow if flow in FLOWS else "other"
    parent = None
    sampled = None
    if type(handoff) is TraceHandoff:
        parent = f"{handoff.trace_id}-{handoff.parent_span_id}"
        sampled = handoff.sampled
    data: dict[str, Any] = {}
    if type(job_id) is str and _JOB_ID.fullmatch(job_id):
        data["ohmni.job_id"] = job_id
    return _OperationScope(
        op="ohmni.worker", name=f"worker {flow}", source="task", flow=flow,
        parent=parent, trusted_sampled=sampled if parent is not None else None, data=data,
    )


class _Disabled:
    def __enter__(self) -> Any:
        return _NOOP

    def __exit__(self, *_args: object) -> bool:
        return False


class _Child(_Guarded):
    """A span inside the active operation; absent outside one."""

    def __init__(self, op: str, description: str, data: dict[str, Any]) -> None:
        self._op = op
        self._description = description
        self._data = data
        self._explicit_status: str | None = None
        self._started = 0.0
        self._execution: str | None = None
        self._restore: tuple[Any, Any, Any] | None = None

    def __enter__(self) -> Any:
        operation = _OPERATION.get()
        if not _RUNTIME.active or operation is None:
            return _NOOP
        try:
            # The owned record of what was current, so a sibling never inherits
            # this span as its parent, whatever the SDK's own cleanup does.
            scope = _RUNTIME.sdk.get_current_scope()
            previous = scope.span
        except BaseException:  # noqa: BLE001
            return _NOOP
        span = None
        try:
            span = _RUNTIME.sdk.start_span(op=self._op, name=self._description)
            self._restore = (scope, previous, span)
            span.__enter__()
            self._span = span
            for key, value in self._data.items():
                self._set(key, value)
            self._started = time.monotonic()
        except BaseException:  # noqa: BLE001
            self._span = None
            self._restore_previous()
            return _NOOP
        return self

    def __exit__(self, exc_type: object, _exc: object, _tb: object) -> bool:
        try:
            if self._span is not None:
                if self._execution is None:
                    self._set("ohmni.execution_outcome", "error" if exc_type is not None else "ok")
                    self._execution = "error" if exc_type is not None else "ok"
                if self._explicit_status is None and exc_type is None:
                    self._status("ok")
                self._on_close(exc_type is not None)
            self._close_span(exc_type is not None)
        except BaseException:  # noqa: BLE001, S110
            pass
        finally:
            self._restore_previous()
        return False

    def _restore_previous(self) -> None:
        """Make the span current before this one current again, if it is not."""
        restore, self._restore = self._restore, None
        if restore is None:
            return
        scope, previous, span = restore
        try:
            if scope.span is span:
                scope.span = previous
        except BaseException:  # noqa: BLE001, S110
            pass

    def _on_close(self, failed: bool) -> None:
        return None


class _Stage(_Child):
    def __init__(self, stage: str) -> None:
        super().__init__("ohmni.stage", stage, {"ohmni.stage": stage})
        self._stage = stage

    def outcome(self, execution: str = "ok", engineering: str | None = None) -> None:
        self._execution = execution if execution in EXECUTION_OUTCOMES else "error"
        self._set("ohmni.execution_outcome", self._execution)
        if engineering in ENGINEERING_OUTCOMES:
            self._set("ohmni.engineering_outcome", engineering)
        self._explicit_status = "ok" if self._execution == "ok" else "internal_error"
        self._status(self._explicit_status)

    def _on_close(self, failed: bool) -> None:
        operation = _OPERATION.get()
        elapsed = (time.monotonic() - self._started) * 1000.0
        _metric("distribution", "ohmni.stage.duration", elapsed, unit="millisecond", attributes={
            "stage": self._stage, "flow": operation.flow if operation else "other",
            "outcome": self._execution or ("error" if failed else "ok"),
        })


def stage(name: str) -> Any:
    """A span for one actual application stage. Unknown names are not traced."""
    if not _RUNTIME.active or name not in STAGES:
        return _Disabled()
    return _Stage(name)


class _Tool(_Child):
    def __init__(self, tool: str) -> None:
        super().__init__("ohmni.tool", tool, {"ohmni.tool": tool})

    def result(self, outcome: str, return_code: int | None = None) -> None:
        self._execution = outcome if outcome in EXECUTION_OUTCOMES else "error"
        self._set("ohmni.execution_outcome", self._execution)
        if type(return_code) is int and -_MAX_EXIT_CODE <= return_code <= _MAX_EXIT_CODE:
            self._set("ohmni.exit_code", return_code)
        self._explicit_status = "ok" if self._execution == "ok" else (
            "deadline_exceeded" if self._execution == "timeout" else "internal_error")
        self._status(self._explicit_status)


_TOOL_NAMES = {
    "kicad-cli": "kicad", "kicad-cli.exe": "kicad", "ngspice": "ngspice", "ngspice.exe": "ngspice",
    "ngspice_con.exe": "ngspice", "java": "freerouting", "java.exe": "freerouting",
}


def classify_tool(command: Any) -> str:
    """Map an argv to the small tool whitelist without exporting any of it."""
    try:
        if type(command) is not list or not command:
            return "other"
        executable = command[0]
        if not isinstance(executable, (str, os.PathLike)):
            return "other"
        base = os.path.basename(os.fspath(executable)).lower()
        if base in _TOOL_NAMES:
            return _TOOL_NAMES[base]
        # The only Python child in src/ohmni is the isolated PDF observation
        # worker, started as `<python> -c <bootstrap> ...`.
        if base.startswith("python") and len(command) > 1 and command[1] == "-c":
            return "pdf_worker"
        return "other"
    except BaseException:  # noqa: BLE001
        return "other"


def tool_call(tool: str) -> Any:
    """A span for one bounded native-tool execution; no argv, cwd, env or output."""
    if not _RUNTIME.active:
        return _Disabled()
    return _Tool(tool if tool in TOOLS else "other")


class _ProviderAttempt(_Child):
    def __init__(self, model: str | None, attempt: int, synthetic: bool) -> None:
        model = _model(model) or "claude-unknown"
        data: dict[str, Any] = {
            "gen_ai.operation.name": "chat", "gen_ai.provider.name": "anthropic",
            "gen_ai.request.model": model, "ohmni.synthetic": bool(synthetic),
        }
        if _bounded_int(attempt, 1, 64) is not None:
            data["ohmni.provider.attempt"] = attempt
        super().__init__("gen_ai.chat", f"chat {model}", data)

    def usage(self, *, input_tokens: Any = None, output_tokens: Any = None,
              cache_read: Any = None, cache_write: Any = None, response_model: Any = None) -> None:
        """Record only counts the vendor actually reported; absent stays absent."""
        observed = [_bounded_int(v) for v in (input_tokens, output_tokens, cache_read, cache_write)]
        base_in, out, read, write = observed
        reported = base_in is not None and out is not None
        self._set("ohmni.usage_reported", reported)
        if reported:
            total_in = base_in + (read or 0) + (write or 0)
            self._set("gen_ai.usage.input_tokens", total_in)
            self._set("gen_ai.usage.output_tokens", out)
            self._set("gen_ai.usage.total_tokens", total_in + out)
            if read is not None:
                self._set("gen_ai.usage.input_tokens.cached", read)
            if write is not None:
                self._set("gen_ai.usage.input_tokens.cache_write", write)
        model = _model(response_model)
        if model is not None:
            self._set("gen_ai.response.model", model)

    def result(self, outcome: str, return_code: int | None = None) -> None:
        del return_code
        outcome = outcome if outcome in PROVIDER_OUTCOMES else "provider_error"
        self._set("ohmni.provider.outcome", outcome)
        self._execution = "ok" if outcome == "ok" else "error"
        self._set("ohmni.execution_outcome", self._execution)
        if outcome != "ok":
            self._set("error.type", outcome)
        self._explicit_status = "ok" if outcome == "ok" else "internal_error"
        self._status(self._explicit_status)
        self._outcome = outcome

    def _on_close(self, failed: bool) -> None:
        operation = _OPERATION.get()
        if operation is not None:
            operation.provider_calls += 1
        _metric("counter", "ohmni.provider.calls", 1, attributes={
            "flow": operation.flow if operation else "other",
            "outcome": getattr(self, "_outcome", "provider_error" if failed else "ok"),
        })


_PROVIDER_FAILURE_CLASSES = (
    ("APITimeoutError", "provider_timeout"),
    ("APIConnectionError", "provider_connection"),
    ("RateLimitError", "provider_rate_limited"),
    ("AuthenticationError", "provider_auth"),
    ("PermissionDeniedError", "provider_auth"),
    ("APIStatusError", "provider_status"),
)
_TYPE_NAME = vars(type)["__name__"]
_TYPE_MRO = vars(type)["__mro__"]


def classify_provider_failure(exception_type: Any) -> str:
    """Owned code for a vendor failure from its class hierarchy names only.

    Names are read through ``type``'s own descriptors, so a hostile metaclass
    property cannot run; the exception instance is never touched.
    """
    try:
        if not isinstance(exception_type, type):
            return "provider_error"
        names = {_TYPE_NAME.__get__(cls, type) for cls in _TYPE_MRO.__get__(exception_type, type)}
        for name, code in _PROVIDER_FAILURE_CLASSES:
            if name in names:
                return code
    except BaseException:  # noqa: BLE001, S110
        pass
    return "provider_error"


def provider_attempt(model: str | None, attempt: int = 1, *, synthetic: bool = False) -> Any:
    """A manual ``gen_ai.chat`` span for one actual vendor SDK call."""
    if not _RUNTIME.active:
        return _Disabled()
    return _ProviderAttempt(model, attempt, synthetic)


# ---------------------------------------------------------------------------
# Owned failures and metrics
# ---------------------------------------------------------------------------

def provider_calls_in_operation() -> int:
    """How many provider calls the current operation made (0 when inactive)."""
    operation = _OPERATION.get()
    return operation.provider_calls if operation is not None and _RUNTIME.active else 0


def record_boundary_failure(site: str, code: str, *, level: str = "error") -> None:
    """Emit one owned issue, at most once per operation.

    The first boundary to report a failure owns it; an outer handler that sees
    the same failure later in the same operation is silent. A genuinely separate
    later failure (for example persistence after a pipeline error) uses
    :func:`record_separate_failure` instead.
    """
    _capture_failure(site, code, level, separate=False)


def record_separate_failure(site: str, code: str, *, level: str = "error") -> None:
    """Report a failure that is distinct from any earlier one in this operation."""
    _capture_failure(site, code, level, separate=True)


def _capture_failure(site: str, code: str, level: str, *, separate: bool) -> None:
    if not _RUNTIME.active:
        return
    try:
        codes = FAILURE_CODES.get(site) if type(site) is str else None
        if codes is None or code not in codes:
            return
        operation = _OPERATION.get()
        if operation is not None:
            if operation.failure_reported and not separate:
                return
            operation.failure_reported = True
        _RUNTIME.sdk.capture_event({
            "level": level if level in LEVELS else "error",
            "exception": {"values": [{"type": _OWNED_EVENT_TYPE, "value": f"{site}.{code}"}]},
            "fingerprint": [_OWNED_EVENT_TYPE, site, code],
            "tags": {"ohmni.site": site, "ohmni.code": code, "ohmni.owned": "1",
                     "ohmni.flow": operation.flow if operation is not None else "other"},
        })
    except BaseException:  # noqa: BLE001, S110 - reporting never affects the request
        pass


def engineering_rejection() -> None:
    """Mark the exception about to be raised as a deterministic engineering verdict.

    Called immediately before a check's own ``raise``, never from a stage
    outcome: a later infrastructure failure in the same operation must still
    be reported as a failure rather than hidden behind an earlier rejection.
    """
    try:
        operation = _OPERATION.get()
        if operation is not None:
            operation.engineering_rejected = True
    except BaseException:  # noqa: BLE001, S110 - bookkeeping never affects the pipeline
        pass


def engineering_rejected() -> bool:
    """Whether the current operation's failure was marked as an engineering rejection."""
    operation = _OPERATION.get()
    return bool(operation is not None and _RUNTIME.active and operation.engineering_rejected)


def failure_already_reported() -> bool:
    operation = _OPERATION.get()
    return bool(operation is not None and operation.failure_reported)


def _metric(kind: str, name: str, value: float, *, unit: str | None = None,
            attributes: dict[str, str] | None = None) -> None:
    runtime = _RUNTIME
    if not runtime.active or not runtime.config.metrics or name not in _METRIC_NAMES:
        return
    try:
        number = _finite(value)
        if number is None:
            return
        clean = {key: v for key, v in (attributes or {}).items()
                 if key in _METRIC_ATTRIBUTE_RULES and _METRIC_ATTRIBUTE_RULES[key](v) is not None}
        from sentry_sdk import metrics

        if kind == "counter":
            metrics.count(name, number, unit=unit, attributes=clean)
        else:
            metrics.distribution(name, number, unit=unit, attributes=clean)
    except BaseException:  # noqa: BLE001, S110
        pass


def record_job_accepted(flow: str) -> None:
    """Once per newly accepted job; never for a reused, polled or reopened one."""
    _metric("counter", "ohmni.jobs.accepted", 1, attributes={"flow": flow if flow in FLOWS else "other"})


def record_job_terminal(flow: str, terminal: str, reason: str = "none") -> None:
    """Once per persisted terminal transition."""
    if terminal not in JOB_TERMINALS:
        return
    _metric("counter", "ohmni.jobs.terminal", 1, attributes={
        "flow": flow if flow in FLOWS else "other", "terminal": terminal,
        "reason": reason if reason in JOB_REASONS else "none",
    })


def record_verifier_attempt(flow: str, outcome: str) -> None:
    """One per actual semantic verification attempt (pass/reject/unknown)."""
    _metric("counter", "ohmni.verifier.attempts", 1, attributes={
        "flow": flow if flow in FLOWS else "other",
        "outcome": outcome if outcome in ENGINEERING_OUTCOMES else "unknown",
    })


def current_flow() -> str | None:
    operation = _OPERATION.get()
    return operation.flow if operation is not None and _RUNTIME.active else None


__all__ = [
    "ENGINEERING_OUTCOMES",
    "EXECUTION_OUTCOMES",
    "FAILURE_CODES",
    "FLOWS",
    "INERT_HANDLE",
    "PINNED_SDK_VERSION",
    "PROVIDER_OUTCOMES",
    "ROUTES",
    "STAGES",
    "TOOLS",
    "TelemetryConfig",
    "TraceHandoff",
    "capture_handoff",
    "classify_provider_failure",
    "classify_tool",
    "configure_from_environment",
    "current_flow",
    "enabled",
    "engineering_rejected",
    "engineering_rejection",
    "failure_already_reported",
    "flush",
    "gate_envelope_items",
    "http_operation",
    "initialize",
    "provider_attempt",
    "provider_calls_in_operation",
    "record_boundary_failure",
    "record_job_accepted",
    "record_job_terminal",
    "record_separate_failure",
    "record_verifier_attempt",
    "recording_transport",
    "shutdown",
    "stage",
    "state",
    "tool_call",
    "validated_parent",
    "worker_operation",
]
