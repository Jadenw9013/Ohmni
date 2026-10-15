"""Release preflight: distribution evidence cannot become engineering/live proof."""

from __future__ import annotations

import ast
import io
import json
import re
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from scripts import rehearse_hackathon_release as check

SITE = "https://demo.example.test"
BACKEND = "https://backend.example.test"
CANARY = "secret-server-response-must-not-appear"


@pytest.fixture(scope="module")
def candidate():
    return check.load_candidate()


@pytest.fixture(scope="module")
def expanded_candidate():
    return check.load_candidate(include_app=True, include_backend=True)


def _health(**updates):
    return {"status": "ready", "free_text": True, "api_version": 2,
            "ui_version": "a" * 64, "server_instance_id": "b" * 16,
            "fixture_id": "esp32-bme280-environmental-logger", **updates}


def test_expected_health_constants_match_server_and_client_without_importing_runtime():
    tree = ast.parse((check.ROOT / "scripts/demo_server.py").read_text(encoding="utf-8"))
    constants = {target.id: ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) for target in node.targets
                 if isinstance(target, ast.Name) and target.id in {"API_VERSION", "DEMO_FIXTURE_ID"}}
    assert constants == {"API_VERSION": check.EXPECTED_API_VERSION,
                         "DEMO_FIXTURE_ID": check.EXPECTED_FIXTURE_ID}
    client = (check.ROOT / "apps/web/client-contract.js").read_text(encoding="utf-8")
    for name, value in constants.items():
        definition = re.findall(rf"^const {name} = (.+);$", client, re.MULTILINE)
        assert len(definition) == 1 and json.loads(definition[0]) == value
    fields = re.findall(r"export function parseHealth\(payload\) \{\s*const fields = (\[[^\]]+\]);", client)
    assert len(fields) == 1 and set(json.loads(fields[0])) == check.HEALTH_FIELDS


def _fetcher(candidate, *, changes=None, health=None):
    calls = []
    changes = changes or {}

    def fetch(url, *, timeout, max_bytes):
        calls.append((url, timeout, max_bytes))
        origin = next((origin for origin in (SITE, BACKEND) if url.startswith(origin + "/")), None)
        assert origin is not None
        path = url.removeprefix(origin + "/")
        if path == "api/health":
            return check.Response(200, "application/json", json.dumps(health).encode())
        if url in changes or path in changes:
            value = changes.get(url, changes.get(path))
            if isinstance(value, Exception):
                raise value
            return value
        assert path in candidate.assets
        content_type = min(check.MIME_TYPES[Path(path).suffix])
        return check.Response(200, content_type, candidate.assets[path])

    return fetch, calls


def test_exact_candidate_matches_with_no_health_or_provider_requests(candidate):
    fetch, calls = _fetcher(candidate)
    result = check.rehearse(SITE, candidate, fetcher=fetch)
    assert result["status"] == result["static_alignment"] == "PASS"
    assert result["health"] == {"status": "NOT_RUN"}
    assert result["app_entry_alignment"] == result["backend_static_alignment"] == {"status": "NOT_RUN"}
    assert result["candidate_commit"] == candidate.commit
    assert result["capture_commit"] != result["candidate_commit"]
    assert len(result["assets"]) == len(check.ASSET_FILES) == len(calls)
    assert result["maximum_requests"] == 20
    assert [url for url, _, _ in calls] == [SITE + "/" + path for path in check.ASSET_FILES]
    assert all(item["expected_sha256"] == item["observed_sha256"] for item in result["assets"])
    assert "not whole-site or release approval" in result["limitations"][0]
    assert all("/api/" not in url for url, _, _ in calls)


@pytest.mark.parametrize(("replacement", "code"), [
    (check.Response(200, "application/javascript", b"stale module"), "asset_bytes_mismatch"),
    (check.Response(200, "text/html", b"<html>fallback</html>"), "content_type_mismatch"),
    (check.Response(404, "text/plain", CANARY.encode()), "http_error"),
    (check.PreflightError("redirect_refused", status_code=302), "redirect_refused"),
    (check.PreflightError("response_too_large", status_code=200), "response_too_large"),
    (check.PreflightError("transport_error"), "transport_error"),
])
def test_bad_asset_fails_without_disclosing_bodies(candidate, replacement, code):
    fetch, _ = _fetcher(candidate, changes={"hackathon-demo.js": replacement})
    result = check.rehearse(SITE, candidate, fetcher=fetch)
    assert result["status"] == result["static_alignment"] == "FAIL"
    failed = [item for item in result["assets"] if item["status"] == "FAIL"]
    assert len(failed) == 1 and failed[0]["code"] == code
    assert CANARY not in json.dumps(result)


def test_capture_metadata_tamper_is_not_accepted_even_if_json_parses(candidate):
    changed = json.loads(candidate.assets["hackathon-demo/demo.json"])
    changed["download"]["href"] = "https://other.example/paid"
    fetch, calls = _fetcher(candidate, changes={
        "hackathon-demo/demo.json": check.Response(200, "application/json", json.dumps(changed).encode()),
    })
    result = check.rehearse(SITE, candidate, fetcher=fetch)
    assert result["static_alignment"] == "FAIL"
    assert all(url.startswith(SITE + "/") for url, _, _ in calls)
    assert len(calls) == len(check.ASSET_FILES)


def test_health_capabilities_are_allowlisted_and_do_not_expose_instance(candidate):
    fetch, calls = _fetcher(candidate, health=_health())
    result = check.rehearse(SITE, candidate, fetcher=fetch, health_url=SITE + "/api/health")
    assert result["status"] == "PASS"
    assert result["health"]["kind"] == "configuration_only"
    assert result["health"]["capabilities"] == {"status": "ready", "free_text": True, "api_version": 2}
    serialized = json.dumps(result)
    assert CANARY not in serialized and "b" * 16 not in serialized
    assert len(calls) == len(check.ASSET_FILES) + 1
    assert result["maximum_requests"] == 21


def test_absent_optional_health_capability_matches_frontend_default(candidate):
    health = _health()
    del health["free_text"]
    fetch, _ = _fetcher(candidate, health=health)
    result = check.rehearse(SITE, candidate, fetcher=fetch, health_url=SITE + "/api/health")
    assert result["status"] == "PASS"
    assert result["health"]["capabilities"]["free_text"] is False


@pytest.mark.parametrize("health", [
    _health(status="starting"), _health(free_text="true"), _health(api_version=True),
    _health(api_version=1), _health(ui_version="invalid"), _health(fixture_id="saved_fixture"),
    _health(free_text=None), _health(server_instance_id="invalid"), _health(secret=CANARY), {}, [], None,
])
def test_bad_health_fails_overall_without_relabeling_static_evidence(candidate, health):
    fetch, _ = _fetcher(candidate, health=health)
    result = check.rehearse(SITE, candidate, fetcher=fetch, health_url=SITE + "/api/health")
    assert result["static_alignment"] == "PASS"
    assert result["status"] == result["health"]["status"] == "FAIL"
    assert "capabilities" not in result["health"]
    assert CANARY not in json.dumps(result)


@pytest.mark.parametrize(("include_app", "backend_site", "maximum"), [
    (True, None, 35), (False, BACKEND, 26), (True, BACKEND, 41),
])
def test_opt_in_asset_groups_have_explicit_bounded_origins(expanded_candidate, include_app, backend_site, maximum):
    fetch, calls = _fetcher(expanded_candidate, health=_health())
    result = check.rehearse(SITE, expanded_candidate, include_app=include_app,
                            backend_site=backend_site, health_url=SITE + "/api/health", fetcher=fetch)
    assert result["status"] == result["static_alignment"] == "PASS"
    assert result["maximum_requests"] == len(calls) == maximum + 1
    expected = [SITE + "/" + path for path in check.ASSET_FILES]
    if include_app:
        expected += [SITE + "/" + path for path in check.APP_FILES]
    if backend_site:
        expected += [BACKEND + "/" + path for path in check.BACKEND_FILES]
    assert [url for url, _, _ in calls] == [*expected, SITE + "/api/health"]
    assert BACKEND + "/" + check.TELEMETRY_METADATA not in expected
    for key, enabled in (("app_entry_alignment", include_app), ("backend_static_alignment", backend_site)):
        group = result[key]
        assert group["status"] == ("PASS" if enabled else "NOT_RUN")
        if enabled:
            assert group["kind"] == "selected_static_assets_only"
            assert all(item["expected_sha256"] == item["observed_sha256"] for item in group["assets"])


@pytest.mark.parametrize(("origin", "path", "replacement", "failed_group"), [
    (SITE, "app.js", check.Response(200, "text/javascript", b"old app"), "app_entry_alignment"),
    (BACKEND, "app.js", check.Response(200, "text/javascript", b"old app"), "backend_static_alignment"),
    (BACKEND, "vendor/sentry-telemetry.js", check.PreflightError("http_error", status_code=404), "backend_static_alignment"),
    (SITE, "telemetry-config.js", check.Response(200, "text/javascript", CANARY.encode()), "app_entry_alignment"),
])
def test_selected_asset_skew_fails_its_group_without_relabeling_saved_capture(
        expanded_candidate, origin, path, replacement, failed_group):
    fetch, _ = _fetcher(expanded_candidate, changes={origin + "/" + path: replacement}, health=_health())
    result = check.rehearse(SITE, expanded_candidate, include_app=True, backend_site=BACKEND,
                            health_url=SITE + "/api/health", fetcher=fetch)
    assert result["status"] == result[failed_group]["status"] == "FAIL"
    assert result["static_alignment"] == result["health"]["status"] == "PASS"
    other_group = "backend_static_alignment" if failed_group == "app_entry_alignment" else "app_entry_alignment"
    assert result[other_group]["status"] == "PASS"
    assert CANARY not in json.dumps(result)
    assert any("does not identify backend code" in text for text in result["limitations"])


@pytest.mark.parametrize("metadata", [
    b"not JSON", b"null", b"[]", b"{}",
    json.dumps({"bundle": "sentry-telemetry.js", "sdk": "@sentry/browser", "bytes": 1, "sha256": "0" * 64}).encode(),
])
def test_invalid_local_bundle_metadata_fails_before_any_request(expanded_candidate, metadata):
    assets = {**expanded_candidate.assets, check.TELEMETRY_METADATA: metadata}
    invalid = check.Candidate(expanded_candidate.commit, assets, expanded_candidate.capture_commit)
    fetch, calls = _fetcher(invalid)
    with pytest.raises(check.PreflightError, match="candidate_telemetry_bundle_invalid"):
        check.rehearse(SITE, invalid, include_app=True, fetcher=fetch)
    assert calls == []


@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("bytes", True), ("bundle", "untrusted.js")])
def test_bundle_metadata_fields_are_verified_against_committed_bytes(expanded_candidate, field, value):
    metadata = json.loads(expanded_candidate.assets[check.TELEMETRY_METADATA])
    metadata[field] = value
    assets = {**expanded_candidate.assets, check.TELEMETRY_METADATA: json.dumps(metadata).encode()}
    with pytest.raises(check.PreflightError, match="candidate_telemetry_bundle_invalid"):
        check.validate_telemetry_bundle(assets)


def test_unselected_optional_assets_are_not_required(candidate):
    fetch, calls = _fetcher(candidate)
    with pytest.raises(check.PreflightError, match="candidate_selected_assets_missing"):
        check.rehearse(SITE, candidate, include_app=True, fetcher=fetch)
    assert calls == []


def test_invalid_backend_origin_rejected_before_any_request(expanded_candidate):
    fetch, calls = _fetcher(expanded_candidate)
    with pytest.raises(check.PreflightError, match="invalid_site_url"):
        check.rehearse(SITE, expanded_candidate, backend_site=BACKEND + "/api/health", fetcher=fetch)
    assert calls == []


def test_optional_asset_selection_does_not_weaken_viewer_dependency_guard(expanded_candidate):
    assets = dict(expanded_candidate.assets)
    assets["hackathon-demo.js"] += b'\nimport "./app.js";'
    with pytest.raises(check.PreflightError, match="candidate_dependency_not_allowlisted"):
        check.validate_dependencies(assets)


def test_malformed_health_body_is_not_reported(candidate):
    fetch, _ = _fetcher(candidate)

    def malformed(url, **kwargs):
        return check.Response(200, "application/json", CANARY.encode()) if url.endswith("/api/health") else fetch(url, **kwargs)

    result = check.rehearse(SITE, candidate, fetcher=malformed, health_url=SITE + "/api/health")
    assert result["health"]["code"] == "health_json_invalid"
    assert CANARY not in json.dumps(result)


@pytest.mark.parametrize("response", [
    check.Response(503, "application/json", b"{}"),
    check.Response(200, "text/html", b"<html>login</html>"),
    check.Response(200, "application/json", b"[" * 1200 + b"]" * 1200),
    check.Response(200, "application/json", b" " * (check.HEALTH_MAX_BYTES + 1)),
])
def test_health_transport_and_parse_failures_leave_static_result_intact(candidate, response):
    fetch, _ = _fetcher(candidate)

    def altered(url, **kwargs):
        return response if url.endswith("/api/health") else fetch(url, **kwargs)

    result = check.rehearse(SITE, candidate, fetcher=altered, health_url=SITE + "/api/health")
    assert result["static_alignment"] == "PASS"
    assert result["status"] == result["health"]["status"] == "FAIL"


@pytest.mark.parametrize("url", [
    "http://example.com", "file:///etc/passwd", "https://user:password@example.com",
    "https://example.com?token=secret", "https://example.com#fragment", "https://example.com/path",
    "https://example.com:99999", "https://example.com\\other", "https://example.com\n",
    "http://localhost.example.com", "https://example.com?", "https://example.com#",
])
def test_invalid_site_is_rejected_before_any_fetch(candidate, url):
    fetch, calls = _fetcher(candidate)
    with pytest.raises(check.PreflightError, match="invalid_site_url"):
        check.rehearse(url, candidate, fetcher=fetch)
    assert calls == []


@pytest.mark.parametrize("url", ["http://127.0.0.1:8765", "http://[::1]:8765", "http://localhost:8765", SITE])
def test_loopback_http_and_https_origins_are_accepted(url):
    assert check.validate_url(url + "/") == url


def test_health_only_accepts_known_read_only_endpoint(candidate):
    fetch, calls = _fetcher(candidate)
    with pytest.raises(check.PreflightError, match="invalid_health_url"):
        check.rehearse(SITE, candidate, health_url=SITE + "/api/planner/propose", fetcher=fetch)
    assert calls == []


@pytest.mark.parametrize("addition", [
    b'\nimport "./new-dependency.js";',
    b'\nimport value from "./new-dependency.js";',
    b'\nexport { value } from "./new-dependency.js";',
    b'\nimport("./new-dependency.js");',
])
def test_new_module_dependency_requires_allowlist_update(candidate, addition):
    assets = dict(candidate.assets)
    assets["hackathon-demo.js"] += addition
    with pytest.raises(check.PreflightError, match="candidate_dependency_not_allowlisted"):
        check.validate_dependencies(assets)


def test_new_computed_or_external_dependency_fails(candidate):
    for addition, code in [
        (b"\nimport(getUrl());", "candidate_computed_dependency"),
        (b'\nimport "https://cdn.example/library.js";', "candidate_external_dependency"),
    ]:
        assets = dict(candidate.assets)
        assets["hackathon-demo.js"] += addition
        with pytest.raises(check.PreflightError, match=code):
            check.validate_dependencies(assets)


def test_missing_transitive_three_core_is_detected(candidate):
    assets = dict(candidate.assets)
    del assets["vendor/three.core.min.js"]
    with pytest.raises(check.PreflightError, match="candidate_dependency_not_allowlisted"):
        check.validate_dependencies(assets)


@pytest.mark.parametrize(("file", "addition"), [
    ("hackathon-demo.html", b'<script type="module" src="/new-module.js"></script>'),
    ("hackathon-demo.css", b'\n@import "./new-style.css";'),
    ("hackathon-demo.css", b'\n.demo { background: url("./new-image.png"); }'),
])
def test_html_and_css_dependency_drift_is_detected(candidate, file, addition):
    assets = dict(candidate.assets)
    assets[file] += addition
    with pytest.raises(check.PreflightError, match="candidate_dependency_not_allowlisted"):
        check.validate_dependencies(assets)


@pytest.mark.parametrize("edit", [
    lambda demo: demo["download"].update(sha256="0" * 64),
    lambda demo: demo["fault"].update(releasable=True),
    lambda demo: demo["fault"].update(source_pcb_sha256="0" * 64),
])
def test_capture_lineage_is_validated_not_just_mirror_equality(candidate, edit):
    canonical = {name: candidate.assets["hackathon-demo/" + name] for name in check.CAPTURE_FILES}
    demo = json.loads(canonical["demo.json"])
    edit(demo)
    canonical["demo.json"] = json.dumps(demo).encode()
    assets = dict(candidate.assets)
    assets["hackathon-demo/demo.json"] = canonical["demo.json"]
    with pytest.raises(check.PreflightError, match="candidate_capture_invalid"):
        check.validate_capture(assets, canonical)


def test_candidate_uses_git_bytes_but_checks_local_capture_mirror(expanded_candidate, tmp_path, monkeypatch):
    candidate = expanded_candidate
    requested = []

    def git(root, *arguments):
        requested.append(arguments)
        if arguments[0] == "rev-parse":
            return candidate.commit.encode() + b"\n"
        path = arguments[1].split(":", 1)[1]
        if path.startswith("examples/hackathon-demo/"):
            path = "apps/web/hackathon-demo/" + path.removeprefix("examples/hackathon-demo/")
        return candidate.assets[path.removeprefix("apps/web/")]

    monkeypatch.setattr(check, "_git", git)
    for directory in ("examples/hackathon-demo", "apps/web/hackathon-demo"):
        for name in check.CAPTURE_FILES:
            target = tmp_path / directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(candidate.assets["hackathon-demo/" + name])
    module = tmp_path / "apps/web/hackathon-demo.js"
    module.write_bytes(candidate.assets["hackathon-demo.js"].replace(b"\n", b"\r\n"))
    (tmp_path / "apps/web/telemetry-config.js").write_bytes(CANARY.encode())
    loaded = check.load_candidate(tmp_path, include_app=True, include_backend=True)
    assert loaded.assets["hackathon-demo.js"] == candidate.assets["hackathon-demo.js"]
    assert loaded.assets["telemetry-config.js"] == candidate.assets["telemetry-config.js"]
    assert all(args[1].startswith(candidate.commit + ":") for args in requested if args[0] == "show")
    assert len([args for args in requested if args == ("show", candidate.commit + ":apps/web/telemetry.js")]) == 1
    (tmp_path / "apps/web/hackathon-demo/demo.json").write_bytes(b"{}")
    with pytest.raises(check.PreflightError, match="local_capture_mismatch"):
        check.load_candidate(tmp_path)


class _Stream(io.BytesIO):
    status = 200

    def __init__(self, body, content_length=None):
        super().__init__(body)
        self.headers = {"Content-Type": "application/javascript; charset=utf-8"}
        if content_length is not None:
            self.headers["Content-Length"] = content_length


def test_transport_get_only_bounded_read_and_redirect_handler(monkeypatch):
    observed = []

    class Opener:
        def open(self, request, *, timeout):
            observed.append((request.get_method(), request.data, timeout))
            return _Stream(b"12345")

    def build(*handlers):
        assert any(isinstance(handler, check._NoRedirect) for handler in handlers)
        tls = next(handler for handler in handlers if isinstance(handler, check.HTTPSHandler))
        assert tls._context.verify_mode == ssl.CERT_REQUIRED
        assert tls._context.check_hostname is True
        return Opener()

    monkeypatch.setattr(check, "build_opener", build)
    with pytest.raises(check.PreflightError, match="response_too_large"):
        check.fetch_url(SITE + "/hackathon-demo.js", timeout=2, max_bytes=4)
    assert observed == [("GET", None, 2)]
    assert check._NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test") is None


@pytest.mark.parametrize("length", ["999999999999999999999999999999", "not-a-length", "50"])
def test_response_length_is_bounded_before_reading(monkeypatch, length):
    class Opener:
        def open(self, *args, **kwargs):
            return _Stream(b"123", content_length=length)

    monkeypatch.setattr(check, "build_opener", lambda *args: Opener())
    with pytest.raises(check.PreflightError, match="response_too_large"):
        check.fetch_url(SITE, timeout=1, max_bytes=10)


@pytest.mark.parametrize("error", [
    HTTPError(SITE, 302, CANARY, {}, io.BytesIO(CANARY.encode())),
    HTTPError(SITE, 404, CANARY, {}, io.BytesIO(CANARY.encode())),
    URLError(CANARY), TimeoutError(CANARY),
])
def test_transport_errors_emit_owned_codes_only(monkeypatch, error):
    class Opener:
        def open(self, *args, **kwargs):
            raise error

    monkeypatch.setattr(check, "build_opener", lambda *args: Opener())
    with pytest.raises(check.PreflightError) as raised:
        check.fetch_url(SITE, timeout=1, max_bytes=10)
    assert CANARY not in str(raised.value)


def test_slow_drip_response_cannot_extend_caller_deadline():
    # Each byte arrives well inside urllib's inactivity timeout. Only an actual
    # elapsed-time deadline can return before this local response is complete.
    started, finished = threading.Event(), threading.Event()

    class SlowDrip(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", "20")
            self.end_headers()
            started.set()
            try:
                for _ in range(20):
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                finished.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowDrip)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        began = time.monotonic()
        with pytest.raises(check.PreflightError, match="request_deadline_exceeded"):
            check.fetch_url(f"http://127.0.0.1:{server.server_port}/slow.js",
                            timeout=0.25, max_bytes=100)
        elapsed = time.monotonic() - began
        assert started.is_set(), "The request must reach the slow-drip server"
        assert elapsed < 0.75
        assert not finished.is_set(), "The caller must return while bytes are still arriving"
        assert finished.wait(3), "The read-only in-flight request may finish after the deadline"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


def test_cli_needs_explicit_site_and_reports_local_failure_without_network(monkeypatch, capsys):
    with pytest.raises(SystemExit) as raised:
        check.main([])
    assert raised.value.code == 2

    def unavailable(**kwargs):
        raise check.PreflightError("candidate_capture_invalid")

    monkeypatch.setattr(check, "load_candidate", unavailable)
    assert check.main(["--site", SITE]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "candidate_capture_invalid"


def test_cli_options_select_git_inputs_and_matching_report_groups(expanded_candidate, monkeypatch, capsys):
    observed = []

    def load(**kwargs):
        observed.append(kwargs)
        return expanded_candidate

    def rehearse(site, candidate, **kwargs):
        observed.append((site, candidate.commit, kwargs))
        return {"status": "PASS"}

    monkeypatch.setattr(check, "load_candidate", load)
    monkeypatch.setattr(check, "rehearse", rehearse)
    assert check.main(["--site", SITE, "--include-app", "--backend-site", BACKEND,
                       "--health-url", BACKEND + "/api/health"]) == 0
    assert observed == [
        {"include_app": True, "include_backend": True},
        (SITE, expanded_candidate.commit, {"include_app": True, "backend_site": BACKEND,
                                          "health_url": BACKEND + "/api/health", "timeout": 10}),
    ]
    assert json.loads(capsys.readouterr().out) == {"status": "PASS"}
