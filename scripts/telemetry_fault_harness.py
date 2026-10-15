#!/usr/bin/env python3
"""Offline fault harness for backend telemetry: what each failure looks like.

    python scripts/telemetry_fault_harness.py [--output build/telemetry-fault-harness]

Drives the real demo server, JobStore worker, provider adapter and native-tool
boundary through five scenarios with the pinned SDK enabled against the
in-memory recording transport (synthetic ``.invalid`` DSN, outbound sockets
refused). Nothing is sent anywhere. For each scenario it records the public
outcome and a sanitized summary of the captured items (issue codes, span
names/outcomes, metric names/attributes), then checks the expected shape:

1. expected_rejection  -- an engineering reject (incomplete routing) is a
   rejected outcome, never an issue;
2. provider_failure    -- a planner provider outage is one owned issue and the
   unchanged public 400 response;
3. tool_timeout        -- a native tool timeout is a distinct ``timeout`` tool
   span and one ``eda_tool_failed`` issue;
4. publication_failure -- a failed persisted completion is never counted as a
   completion, and is one persistence issue;
5. recovery            -- the same store then completes a job: one completion,
   no new issue.

Scenarios 1, 3, 4 and 5 use small scripted pipelines (and a fake ``kicad-cli``
that sleeps) so the failure is deterministic; they prove telemetry
classification, not a KiCad or routing verdict. Exits 0 only if every check
passes.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

SYNTHETIC_DSN = "https://" + "0123456789abcdef" * 2 + "@o0.ingest.invalid/42"
CANARY = "ohmni-fault-canary-41d2"
TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT = "00f067aa0ba902b7"
OPENER = build_opener(ProxyHandler({}))


@contextmanager
def refuse_outbound():
    """Refuse every non-loopback connection while the harness runs."""
    real_connect, real_getaddrinfo, attempts = socket.socket.connect, socket.getaddrinfo, []

    def connect(sock, address):
        host = address[0] if isinstance(address, tuple) else address
        if sock.family in (socket.AF_INET, socket.AF_INET6) and host not in {"127.0.0.1", "::1", "localhost"}:
            attempts.append("connect")
            raise ConnectionRefusedError("fault harness denies outbound network")
        return real_connect(sock, address)

    def getaddrinfo(host, *args, **kwargs):
        if host not in {"127.0.0.1", "::1", "localhost", None}:
            attempts.append("resolve")
            raise socket.gaierror("fault harness denies name resolution")
        return real_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect, socket.getaddrinfo = connect, getaddrinfo
    try:
        yield attempts
    finally:
        socket.socket.connect, socket.getaddrinfo = real_connect, real_getaddrinfo


def items_of(transport) -> list[tuple[str, dict]]:
    result = []
    for envelope in list(transport.envelopes):
        lines = envelope.split(b"\n")
        index = 1
        while index + 1 < len(lines):
            result.append((json.loads(lines[index])["type"], json.loads(lines[index + 1])))
            index += 2
    return result


def summarize(items) -> dict:
    issues, transactions, metrics = [], [], []
    for kind, payload in items:
        if kind == "event":
            issues.append({"value": payload["exception"]["values"][0]["value"], "level": payload["level"],
                           "fingerprint": payload["fingerprint"]})
        elif kind == "transaction":
            trace = payload["contexts"]["trace"]
            transactions.append({
                "name": payload["transaction"], "op": trace["op"], "status": trace.get("status"),
                "outcome": {k: v for k, v in trace.get("data", {}).items() if k.startswith("ohmni.") and "outcome" in k},
                "spans": [{"op": s["op"], "name": s["description"],
                           **{k: v for k, v in s.get("data", {}).items() if "outcome" in k}} for s in payload["spans"]],
            })
        elif kind == "trace_metric":
            for metric in payload["items"]:
                metrics.append({"name": metric["name"], "value": metric["value"],
                                "attributes": {k: e["value"] for k, e in metric["attributes"].items()
                                               if not k.startswith("sentry.")}})
    return {"issues": issues, "transactions": transactions, "metrics": metrics}


def post(base, path, payload, headers=None):
    request = Request(base + path, data=json.dumps(payload).encode(), method="POST",
                      headers={"content-type": "application/json", **(headers or {})})
    try:
        with OPENER.open(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def wait(store, job_id, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = store.get(job_id)
        if job["status"] in {"complete", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not terminalize")


def settle(telemetry, transport, count, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        telemetry.flush(2.0)
        if sum(kind == "transaction" for kind, _ in items_of(transport)) >= count:
            return
        time.sleep(0.05)


def run(output: Path) -> dict:
    from demo_server import DEMO_REQUEST, DemoHandler, DemoHTTPServer, JobStore

    from ohmni.adapters import process, telemetry
    from ohmni.adapters.anthropic_provider import AnthropicProvider
    from ohmni.application.demo import (
        EdaToolFailedError,
        RoutingIncompleteError,
        current_pcb_policy,
    )

    class Report:
        def model_dump(self, mode=None):
            return {"result": "complete", "pcb": current_pcb_policy()}

    def pipeline(behavior):
        class Scripted:
            def __init__(self, progress):
                self.progress = progress

            def run(self, destination, request):
                return behavior()
        return Scripted

    def reject():
        with telemetry.stage("routing") as stage:
            stage.outcome("ok", "reject")
            raise RoutingIncompleteError(CANARY)

    def slow_tool(executable):
        def behavior():
            with telemetry.stage("erc"):
                try:
                    process.run_tool([str(executable), "sch", "erc", CANARY], timeout=0.3)
                except subprocess.TimeoutExpired:
                    raise EdaToolFailedError(CANARY) from None
        return behavior

    connection_error = type("APIConnectionError", (Exception,), {})

    class VendorClient:
        def __init__(self, error):
            self.messages = SimpleNamespace(create=lambda **_: (_ for _ in ()).throw(error))

    transport = telemetry.recording_transport()
    config = telemetry.configure_from_environment({
        "OHMNI_TELEMETRY_ENABLED": "1", "SENTRY_DSN": SYNTHETIC_DSN, "OHMNI_ENV": "local",
        "SENTRY_RELEASE": "ohmni@fault-harness", "OHMNI_TRACE_SAMPLE_RATE": "1", "OHMNI_TELEMETRY_METRICS": "1",
    })
    scenarios = []

    def scenario(name, transactions, body):
        transport.envelopes.clear()
        telemetry.shutdown(0)
        assert telemetry.initialize(config, transport=transport)
        try:
            public = body()
            settle(telemetry, transport, transactions)
        finally:
            telemetry.flush(2.0)
            items = items_of(transport)
            raw = b"\n".join(transport.envelopes)
            telemetry.shutdown(1.0)
        summary = summarize(items)
        summary.update(name=name, public=public, canary_absent=CANARY.encode() not in raw,
                       item_types=sorted({kind for kind, _ in items}))
        scenarios.append(summary)
        return summary

    with tempfile.TemporaryDirectory(prefix="ohmni-fault-harness-") as temp_name, refuse_outbound() as attempts:
        temp = Path(temp_name)

        def job_with(store, request=DEMO_REQUEST):
            with telemetry.http_operation("POST /api/demo", f"{TRACE}-{PARENT}"):
                job_id = store.start(request)
            job = wait(store, job_id)
            return {"status": job["status"], "error_code": job.get("error_code")}

        def expected_rejection():
            return job_with(JobStore(temp / "reject", pipeline(reject)))

        def provider_failure():
            provider = AnthropicProvider(api_key="test", client=VendorClient(connection_error(CANARY)))
            server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=JobStore(temp / "provider", provider=provider))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, body = post(f"http://127.0.0.1:{server.server_port}", "/api/project-plans",
                                    {**server._identity(), "message": f"A USB board {CANARY}", "parent_id": None},
                                    {"sentry-trace": f"{TRACE}-{PARENT}"})
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            return {"status": status, "error": body.get("error")}

        def tool_timeout():
            bin_dir = temp / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "kicad-cli"
            fake.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            return job_with(JobStore(temp / "timeout", pipeline(slow_tool(fake))))

        recovering = JobStore(temp / "recovery", pipeline(lambda: Report()))
        recovering.enable_persistence()
        real_save = recovering.project_store.save_job

        def publication_failure():
            def save(record):
                if record["status"] == "complete":
                    raise OSError(CANARY)
                return real_save(record)
            recovering.project_store.save_job = save
            try:
                return job_with(recovering)
            finally:
                recovering.project_store.save_job = real_save

        def recovery():
            return job_with(recovering)

        reject_run = scenario("expected_rejection", 2, expected_rejection)
        provider_run = scenario("provider_failure", 1, provider_failure)
        timeout_run = scenario("tool_timeout", 2, tool_timeout)
        publication_run = scenario("publication_failure", 2, publication_failure)
        recovery_run = scenario("recovery", 2, recovery)
        network_attempts = list(attempts)

    def metric(run_summary, name, **attributes):
        return sum(m["value"] for m in run_summary["metrics"] if m["name"] == name
                   and all(m["attributes"].get(k) == v for k, v in attributes.items()))

    def worker(run_summary):
        return next(t for t in run_summary["transactions"] if t["op"] == "ohmni.worker")

    checks = {
        "no_network_attempt": network_attempts == [],
        "canary_absent_everywhere": all(s["canary_absent"] for s in scenarios),
        "only_allowed_item_types": all(set(s["item_types"]) <= {"event", "transaction", "trace_metric"} for s in scenarios),
        "rejection_is_not_an_issue": reject_run["issues"] == []
            and reject_run["public"] == {"status": "failed", "error_code": "routing_incomplete"}
            and worker(reject_run)["outcome"].get("ohmni.engineering_outcome") == "reject"
            and metric(reject_run, "ohmni.jobs.terminal", terminal="failed", reason="routing_incomplete") == 1,
        "provider_outage_one_issue_unchanged_response": provider_run["public"] == {"status": 400, "error": "invalid_plan"}
            and [i["value"] for i in provider_run["issues"]] == ["provider.provider_connection"]
            and metric(provider_run, "ohmni.provider.calls", outcome="provider_connection") == 1,
        "tool_timeout_is_distinct": timeout_run["public"] == {"status": "failed", "error_code": "eda_tool_failed"}
            and [i["value"] for i in timeout_run["issues"]] == ["worker.eda_tool_failed"]
            and any(s["op"] == "ohmni.tool" and s.get("ohmni.execution_outcome") == "timeout"
                    for s in worker(timeout_run)["spans"]),
        "failed_publication_never_completes": publication_run["public"] == {"status": "failed", "error_code": "job_state_invalid"}
            and metric(publication_run, "ohmni.jobs.terminal", terminal="complete") == 0
            and [i["value"] for i in publication_run["issues"]] == ["persistence.job_persist_failed"],
        "recovery_completes_once_without_issue": recovery_run["public"] == {"status": "complete", "error_code": None}
            and recovery_run["issues"] == []
            and metric(recovery_run, "ohmni.jobs.terminal", terminal="complete") == 1
            and worker(recovery_run)["status"] == "ok",
    }
    summary = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "sdk": {"python": telemetry.PINNED_SDK_VERSION},
        "transport": "in-memory recording transport, synthetic .invalid DSN, outbound sockets refused",
        "checks": checks,
        "scenarios": scenarios,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "telemetry-fault-harness")
    args = parser.parse_args(argv)
    for name in [n for n in os.environ if n.startswith(("SENTRY", "OHMNI_TELEMETRY"))]:
        os.environ.pop(name)  # inherited settings are cleared, never read
    summary = run(args.output)
    for name, ok in summary["checks"].items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(f"{summary['status']}: summary at {args.output / 'summary.json'}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
