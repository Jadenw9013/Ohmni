#!/usr/bin/env python3
"""Real-browser smoke test for the bundled browser telemetry, fully offline.

    python scripts/smoke_browser_telemetry.py [--output build/telemetry-browser-smoke]

Runs headless Chromium (Playwright) against temporary copies of apps/web in
three telemetry modes -- disabled (the committed default), enabled, and enabled
with the SDK bundle missing -- under two hostings:

* ``local``: the real demo server serving its immutable snapshot (same origin);
* ``static``: a plain static file server, like Vercel's no-build publication,
  calling the demo server as a cross-origin API through ``OHMNI_API_BASE``.

Every request leaving 127.0.0.1 is intercepted. Requests to the synthetic
Sentry ingest host are recorded and answered locally; anything else is aborted
and fails the run. Chromium also resolves every other host to NOTFOUND. The
demo server's own telemetry uses the in-memory recording transport, so the
browser-to-server trace link is checked without any network send. Writes a
sanitized summary and the captured envelopes; exits 0 only if every check
passes, 2 if Playwright/Chromium is unavailable (BLOCKED, never PASS).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

INGEST_HOST = "o0.ingest.sentry.io"
FRONTEND_DSN = "https://" + "0123456789abcdef" * 2 + f"@{INGEST_HOST}/42"
SERVER_DSN = "https://" + "fedcba9876543210" * 2 + "@o0.ingest.invalid/43"
CANARY = "ohmni-canary-7f3a9c"
MODES = ("disabled", "enabled", "missing_bundle")
HOSTINGS = ("local", "static")


def config_source(enabled: bool, api_origin: str) -> str:
    return (
        "export const TELEMETRY_CONFIG = Object.freeze("
        + json.dumps({
            "enabled": enabled, "dsn": FRONTEND_DSN if enabled else "", "environment": "local",
            "release": "ohmni@smoke", "apiOrigin": api_origin, "traceSampleRate": 1,
        })
        + ");\n"
    )


def web_copy(base: Path, name: str, *, enabled: bool, api_origin: str, drop_bundle: bool) -> Path:
    target = base / name
    shutil.copytree(WEB, target, ignore=shutil.ignore_patterns("node_modules", "tests"))
    (target / "telemetry-config.js").write_text(config_source(enabled, api_origin), encoding="utf-8")
    if drop_bundle:
        (target / "vendor" / "sentry-telemetry.js").unlink()
    return target


@contextmanager
def thread_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class QuietStatic(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def parse_envelope(body: bytes) -> list[tuple[str, dict]]:
    lines = [line for line in body.split(b"\n") if line.strip()]
    items, index = [], 1
    while index + 1 < len(lines):
        header = json.loads(lines[index])
        items.append((header.get("type"), json.loads(lines[index + 1])))
        index += 2
    return items


def run_scenario(browser, hosting: str, mode: str, work: Path) -> dict:
    from demo_server import DemoHandler, DemoHTTPServer, JobStore

    store = JobStore(work / f"{hosting}-{mode}-jobs")
    enabled = mode != "disabled"
    result: dict = {"hosting": hosting, "mode": mode, "checks": {}}
    if hosting == "local":
        # Same origin: the demo server serves its own snapshot of the copy. Its
        # snapshot requires every asset, so a missing bundle is simulated by
        # answering the bundle request with 404 in the browser.
        root = web_copy(work, f"{hosting}-{mode}", enabled=enabled, api_origin="", drop_bundle=False)
        api = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store, web_root=root)
        with thread_server(api):
            origin = f"http://127.0.0.1:{api.server_port}"
            result.update(drive_page(browser, hosting, mode, origin, origin))
        return result
    api = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store)
    with thread_server(api):
        api_origin = f"http://127.0.0.1:{api.server_port}"
        root = web_copy(work, f"{hosting}-{mode}", enabled=enabled, api_origin=api_origin,
                        drop_bundle=mode == "missing_bundle")
        static = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietStatic, directory=str(root)))
        with thread_server(static):
            result.update(drive_page(browser, hosting, mode, f"http://127.0.0.1:{static.server_port}", api_origin))
    return result


def drive_page(browser, hosting, mode, page_origin, api_origin) -> dict:
    context = browser.new_context()
    context.add_cookies([{"name": "ohmni_canary", "value": CANARY, "url": page_origin}])
    if hosting == "static":
        context.add_init_script(f"window.OHMNI_API_BASE = {json.dumps(api_origin)};")
    page = context.new_page()
    ingest, blocked, api_requests, page_errors, console_errors, bundle_requests = [], [], [], [], [], []
    abort_plan = {"armed": False}

    def route(request_route):
        request = request_route.request
        parts = urlsplit(request.url)
        if parts.hostname == INGEST_HOST:
            ingest.append(request.post_data_buffer or b"")
            return request_route.fulfill(status=200, content_type="application/json", body="{}")
        if parts.hostname != "127.0.0.1":
            blocked.append(parts.scheme + "://" + (parts.hostname or "?"))
            return request_route.abort()
        if parts.path.endswith("/vendor/sentry-telemetry.js"):
            bundle_requests.append(parts.path)
            if mode == "missing_bundle" and hosting == "local":
                return request_route.fulfill(status=404, body="")
        if parts.path.startswith("/api/") and request.method in {"POST", "GET"}:
            entry = {"method": request.method, "path": parts.path,
                     "sentry_trace": request.headers.get("sentry-trace"), "aborted": False}
            api_requests.append(entry)
            if parts.path == "/api/project-plans" and request.method == "POST" and abort_plan["armed"]:
                abort_plan["armed"] = False
                entry["aborted"] = True
                return request_route.abort("connectionrefused")
        return request_route.continue_()

    page.route("**/*", route)
    page.on("pageerror", lambda error: page_errors.append(type(error).__name__))
    page.on("console", lambda message: console_errors.append(message.type) if message.type == "error" else None)
    started = time.monotonic()
    page.goto(f"{page_origin}/?q={CANARY}", wait_until="load")
    state = page.evaluate("import('/telemetry.js').then(async (m) => { await m.startTelemetry(); return m.telemetryState(); })")
    outcome = {"telemetry_state": state}

    # The real fixed-example flow: brief, then confirmed run start.
    with page.expect_response(lambda r: urlsplit(r.url).path == "/api/brief") as brief:
        page.evaluate("document.querySelector('#start-supported').click()")
    outcome["brief_status"] = brief.value.status
    # Interval polling: requestAnimationFrame polling stalls in background headless pages.
    page.wait_for_function("!document.querySelector('#confirm-brief').disabled", polling=100, timeout=15000)
    with page.expect_response(lambda r: urlsplit(r.url).path == "/api/demo") as demo:
        page.evaluate("document.querySelector('#confirm-brief').click()")
    outcome["demo_status"] = demo.value.status

    # A transport failure the backend never sees: the real project request
    # helper, carrying canary text, has its connection refused once.
    abort_plan["armed"] = True
    outcome["plan_request"] = page.evaluate(
        "(message) => import('/project-contract.js').then((m) => m.projectRequest('/api/project-plans',"
        " { method: 'POST', data: { message, parent_id: null } })).then(() => 'resolved', (e) => e.name)",
        f"A small board {CANARY}")
    expected_ingest = 3 if mode == "enabled" else 0
    deadline = time.monotonic() + 8
    while len(ingest) < expected_ingest and time.monotonic() < deadline:
        page.wait_for_timeout(100)
    page.wait_for_timeout(300)
    context.close()
    outcome.update({
        "seconds": round(time.monotonic() - started, 2), "ingest": ingest, "blocked": blocked,
        "api_requests": api_requests, "page_errors": page_errors, "console_error_count": len(console_errors),
        "bundle_requests": len(bundle_requests),
    })
    return outcome


def evaluate(result: dict, server_transactions: list[dict]) -> dict:
    mode, checks = result["mode"], {}
    items = [item for body in result.pop("ingest") for item in parse_envelope(body)]
    raw = json.dumps(items)
    events = [payload for kind, payload in items if kind == "event"]
    transactions = [payload for kind, payload in items if kind == "transaction"]
    traced = [r for r in result["api_requests"] if r["sentry_trace"]]
    checks["no_external_request"] = result["blocked"] == []
    checks["no_uncaught_page_error"] = result["page_errors"] == []
    checks["app_flow_unchanged"] = (result["brief_status"], result["demo_status"], result["plan_request"]) == (
        200, 202, "ProjectRequestError")
    checks["only_event_and_transaction_items"] = {kind for kind, _ in items} <= {"event", "transaction"}
    checks["canary_absent_from_envelopes"] = CANARY not in raw and "ohmni_canary" not in raw
    if mode == "disabled":
        checks["state"] = result["telemetry_state"] == "disabled"
        checks["bundle_not_requested"] = result["bundle_requests"] == 0
        checks["no_envelopes"] = items == []
        checks["no_trace_headers"] = traced == []
    elif mode == "missing_bundle":
        checks["state"] = result["telemetry_state"] == "unavailable"
        checks["no_envelopes"] = items == []
        checks["no_trace_headers"] = traced == []
    else:
        checks["state"] = result["telemetry_state"] == "enabled"
        routes = sorted(t["transaction"] for t in transactions)
        checks["browser_request_transactions"] = routes == ["POST /api/brief", "POST /api/demo", "POST /api/project-plans"]
        checks["one_owned_transport_issue"] = [
            e["exception"]["values"][0]["value"] for e in events] == ["browser.project_request.transport_unreachable"]
        checks["trace_headers_only_on_traced_posts"] = (
            {(r["method"], r["path"]) for r in traced}
            == {("POST", "/api/brief"), ("POST", "/api/demo"), ("POST", "/api/project-plans")})
        browser_spans = {(t["contexts"]["trace"]["trace_id"], t["contexts"]["trace"]["span_id"]) for t in transactions}
        header_spans = {tuple(r["sentry_trace"].split("-")[:2]) for r in traced}
        checks["headers_match_browser_spans"] = header_spans <= browser_spans
        server_http = [t for t in server_transactions if t["contexts"]["trace"].get("op") == "http.server"]
        linked = {(t["contexts"]["trace"]["trace_id"], t["contexts"]["trace"].get("parent_span_id")) for t in server_http}
        delivered = {tuple(r["sentry_trace"].split("-")[:2]) for r in traced if not r["aborted"]}
        checks["server_continues_browser_trace"] = len(delivered) == 2 and delivered <= linked
    result["checks"] = checks
    result["envelope_items"] = [_summarize(kind, payload) for kind, payload in items]
    result["passed"] = all(checks.values())
    result["api_requests"] = [{"method": r["method"], "path": _template(r["path"]), "aborted": r["aborted"],
                               "sentry_trace": bool(r["sentry_trace"])} for r in result["api_requests"]]
    return result


def _template(path: str) -> str:
    return "/api/jobs/{job}" if path.startswith("/api/jobs/") else path


def _summarize(kind: str, payload: dict) -> dict:
    trace = payload.get("contexts", {}).get("trace", {})
    if kind == "event":
        return {"type": "event", "value": payload["exception"]["values"][0]["value"],
                "fingerprint": payload.get("fingerprint"), "tags": payload.get("tags"),
                "has_trace": bool(trace)}
    return {"type": "transaction", "name": payload.get("transaction"), "op": trace.get("op"),
            "status": trace.get("status"), "data": trace.get("data"), "spans": len(payload.get("spans", []))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "telemetry-browser-smoke")
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"status": "BLOCKED", "reason": "playwright is not installed"}))
        return 2
    from ohmni.adapters import telemetry

    transport = telemetry.recording_transport()
    server_config = telemetry.configure_from_environment({
        "OHMNI_TELEMETRY_ENABLED": "1", "SENTRY_DSN": SERVER_DSN, "OHMNI_ENV": "local",
        "SENTRY_RELEASE": "ohmni@smoke", "OHMNI_TRACE_SAMPLE_RATE": "1", "OHMNI_TELEMETRY_METRICS": "0",
    })
    results = []
    with tempfile.TemporaryDirectory(prefix="ohmni-telemetry-smoke-") as temp, sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(args=["--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"])
        except Exception:  # noqa: BLE001 - a missing browser is BLOCKED, never PASS
            print(json.dumps({"status": "BLOCKED", "reason": "chromium could not be launched"}))
            return 2
        browser_version = browser.version
        for hosting in HOSTINGS:
            for mode in MODES:
                transport.envelopes.clear()
                assert telemetry.initialize(server_config, transport=transport)
                try:
                    raw = run_scenario(browser, hosting, mode, Path(temp))
                finally:
                    telemetry.flush(2.0)
                    server_items = [item for body in list(transport.envelopes) for item in parse_envelope(body)]
                    telemetry.shutdown(1.0)
                server_transactions = [payload for kind, payload in server_items if kind == "transaction"]
                results.append(evaluate(raw, server_transactions))
        browser.close()
    passed = all(result["passed"] for result in results)
    summary = {
        "status": "PASS" if passed else "FAIL",
        "browser": f"chromium {browser_version}",
        "sdk": {"browser": json.loads((WEB / "vendor" / "sentry-telemetry.json").read_text())["sdk_version"],
                "python": telemetry.PINNED_SDK_VERSION},
        "transport": "Playwright route interception (browser) and in-memory recording transport (server); no network send",
        "scenarios": results,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for result in results:
        mark = "PASS" if result["passed"] else "FAIL"
        failed = [name for name, ok in result["checks"].items() if not ok]
        print(f"{mark} {result['hosting']:6} {result['mode']:14} state={result['telemetry_state']:11} "
              f"items={len(result['envelope_items'])} {('failed: ' + ', '.join(failed)) if failed else ''}")
    print(f"{summary['status']}: {summary['browser']}; summary at {args.output / 'summary.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
