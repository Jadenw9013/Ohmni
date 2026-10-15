#!/usr/bin/env python3
"""Read-only alignment check for the saved demo and optional application assets.

Uses only the standard library and GET requests. Expected bytes come from the
current Git commit, not platform-dependent checkout line endings. This checks
distribution of an existing capture; it runs no AI, KiCad, SPICE or browser.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import posixpath
import re
import ssl
import subprocess
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from queue import Empty, Queue
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
HEALTH_MAX_BYTES = 16 * 1024
EXPECTED_API_VERSION = 2  # Guarded against scripts/demo_server.py by a source-only test.
EXPECTED_FIXTURE_ID = "esp32-bme280-environmental-logger"
HEALTH_FIELDS = {"status", "fixture_id", "api_version", "server_instance_id", "ui_version"}
CAPTURE_FILES = (
    "demo.json",
    "saved-run/golden.kicad_pcb",
    "saved-run/fault/diagnostic-fault.kicad_pcb",
    "ohmni-demo-fabrication.zip",
)
# Deliberately bounded, not a crawler. Changes to the demo's import graph must
# still fit this reviewed list or fail local validation before any HTTP request.
VIEWER_FILES = (
    "hackathon-demo.html", "hackathon-demo.css", "hackathon-demo.js",
    "hackathon-demo-model.js", "favicon.svg", "view-model.js", "board-view.js",
    "board-model.js", "board-renderer-geometry.js", "visual-renderer.js",
    "visual-assets.js", "visual-layers.js", "visual-board-scene.js",
    "visual-version.js", "vendor/three.module.js", "vendor/three.core.min.js",
)
ASSET_FILES = VIEWER_FILES + tuple("hackathon-demo/" + name for name in CAPTURE_FILES)
# Selected entry points, not the complete application dependency graph. Their
# alignment cannot establish a usable application; the browser rehearsal does.
APP_FILES = (
    "index.html", "app.js", "client-contract.js", "project-contract.js",
    "conversation.js", "project-assistant.js", "project-workbench.js", "plan-summary.js",
    "telemetry.js", "telemetry-config.js", "vendor/sentry-telemetry.js",
    "vendor/sentry-telemetry.json", "styles.css", "workbench-theme.css", "guided-flow.css",
)
# The backend does not serve bundle metadata. Check only its allowlisted files.
BACKEND_FILES = (
    "app.js", "client-contract.js", "project-contract.js", "telemetry.js",
    "telemetry-config.js", "vendor/sentry-telemetry.js",
)
TELEMETRY_METADATA = "vendor/sentry-telemetry.json"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
MIME_TYPES = {
    ".html": {"text/html"},
    ".css": {"text/css"},
    ".js": {"text/javascript", "application/javascript"},
    ".svg": {"image/svg+xml"},
    ".json": {"application/json"},
    ".zip": {"application/zip", "application/x-zip-compressed"},
    ".kicad_pcb": {"text/plain", "application/octet-stream"},
}
LIMITATIONS = [
    "PASS means the checked static assets match this candidate commit; it is not whole-site or release approval.",
    "The capture contains historical engineering receipts; no engineering check was rerun.",
    "No browser rendering, accessibility, live AI request, SPICE run or Sentry ingestion was tested.",
    "Health reports configuration only; it does not establish provider success, quota availability or budget persistence.",
    "Application checks cover selected entry assets, not their complete dependency graph.",
    "Backend asset alignment does not identify backend code or establish that telemetry is enabled; a mismatch may be deployment skew or intentional configuration drift.",
    "Each GET has a caller deadline. A timed-out daemon worker may finish its read-only request later; requests and workers are bounded by maximum_requests and never retried.",
]


class PreflightError(Exception):
    """An owned diagnostic code; never contains a response body or raw error."""

    def __init__(self, code: str, *, status_code: int | None = None, content_type: str | None = None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.content_type = content_type


@dataclass(frozen=True)
class Candidate:
    commit: str
    assets: dict[str, bytes]
    capture_commit: str


@dataclass(frozen=True)
class Response:
    status_code: int
    content_type: str
    body: bytes


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments], check=True, capture_output=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        raise PreflightError("candidate_git_unavailable") from None
    if len(result.stdout) > MAX_RESPONSE_BYTES:
        raise PreflightError("candidate_file_too_large")
    return result.stdout


class _PageAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("src"):
            self.references.append(values["src"])
        if (tag == "link" and values.get("href")
                and set((values.get("rel") or "").split()) & {"stylesheet", "icon", "modulepreload"}):
            self.references.append(values["href"])


IMPORT_FROM = re.compile(
    r"\b(?:import|export)\s*(?:\{[^}]*\}|\*\s*(?:as\s+[\w$]+)?|[\w$]+"
    r"(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+[\w$]+))?)\s*from\s*(['\"])([^'\"]+)\1",
    re.DOTALL,
)
IMPORT_SIDE_EFFECT = re.compile(r"\bimport\s*(['\"])([^'\"]+)\1")
DYNAMIC_IMPORT = re.compile(r"\bimport\s*\(\s*(['\"])([^'\"]+)\1\s*\)")


def validate_dependencies(assets: dict[str, bytes]) -> None:
    """Check literal module/stylesheet edges in this known, native-ESM viewer.

    This intentionally is not a JavaScript parser. Computed dynamic imports
    fail rather than silently becoming an unexamined network dependency.
    """
    for name in VIEWER_FILES:
        try:
            source = assets[name].decode("utf-8")
        except (KeyError, UnicodeError):
            raise PreflightError("candidate_viewer_invalid") from None
        references: list[str] = []
        if name.endswith(".html"):
            page = _PageAssets()
            page.feed(source)
            references = page.references
        elif name.endswith(".js"):
            references = [match[1] for match in IMPORT_FROM.findall(source)]
            references += [match[1] for match in IMPORT_SIDE_EFFECT.findall(source)]
            dynamic = DYNAMIC_IMPORT.findall(source)
            if len(re.findall(r"\bimport\s*\(", source)) != len(dynamic):
                raise PreflightError("candidate_computed_dependency")
            references += [match[1] for match in dynamic]
        elif name.endswith(".css"):
            references = [match.strip(" \t\r\n\"'") for match in re.findall(r"url\(([^)]+)\)", source)]
            references += re.findall(r"@import\s+['\"]([^'\"]+)['\"]", source)
        for reference in references:
            if name.endswith(".css") and reference.startswith("data:"):
                continue
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or "\\" in reference:
                raise PreflightError("candidate_external_dependency")
            resolved = posixpath.normpath(posixpath.join("/" + posixpath.dirname(name), parsed.path)).lstrip("/")
            if resolved not in ASSET_FILES or resolved not in assets:
                raise PreflightError("candidate_dependency_not_allowlisted")


def validate_capture(assets: dict[str, bytes], canonical: dict[str, bytes]) -> str:
    try:
        if any(assets["hackathon-demo/" + name] != canonical[name] for name in CAPTURE_FILES):
            raise PreflightError("candidate_capture_mirror_mismatch")
        demo = json.loads(canonical["demo.json"])
        good, fault, download = demo["good"], demo["fault"], demo["download"]
        original_hash = good["board"]["artifact_fingerprint"]
        fault_hash = fault["snapshot_sha256"]
        expected = {
            "saved-run/golden.kicad_pcb": original_hash,
            "saved-run/fault/diagnostic-fault.kicad_pcb": fault_hash,
            "ohmni-demo-fabrication.zip": download["sha256"],
        }
        valid = (
            type(demo["schema_version"]) is int and demo["schema_version"] == 1
            and demo["kind"] == "saved_hackathon_demonstration"
            and download["href"] == "ohmni-demo-fabrication.zip"
            and fault["kind"] == "diagnostic_fault_only" and fault["releasable"] is False
            and "checks" not in fault and original_hash != fault_hash
            and fault["source_pcb_sha256"] == original_hash
            and fault["board"]["artifact_fingerprint"] == fault_hash
            and "routing_plan_fingerprint" not in fault["board"]
            and "constraints_hash" not in fault["board"]
        )
        if not valid or any(not isinstance(digest, str) or not DIGEST.fullmatch(digest)
                            or sha256(canonical[name]) != digest for name, digest in expected.items()):
            raise PreflightError("candidate_capture_invalid")
        capture_commit = demo["capture"]["git_commit"]
        if not isinstance(capture_commit, str) or not COMMIT.fullmatch(capture_commit):
            raise PreflightError("candidate_capture_invalid")
        return capture_commit
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise PreflightError("candidate_capture_invalid") from None


def validate_telemetry_bundle(assets: dict[str, bytes]) -> None:
    """Verify committed bundle metadata locally; never inspect runtime config."""
    try:
        metadata = json.loads(assets[TELEMETRY_METADATA])
        bundle = assets["vendor/sentry-telemetry.js"]
        valid = (metadata["bundle"] == "sentry-telemetry.js"
                 and metadata["sdk"] == "@sentry/browser"
                 and type(metadata["bytes"]) is int and metadata["bytes"] == len(bundle)
                 and metadata["sha256"] == sha256(bundle))
        if not valid:
            raise PreflightError("candidate_telemetry_bundle_invalid")
    except (KeyError, TypeError, ValueError, RecursionError):
        raise PreflightError("candidate_telemetry_bundle_invalid") from None


def load_candidate(root: Path = ROOT, *, include_app: bool = False,
                   include_backend: bool = False) -> Candidate:
    try:
        commit = _git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    except UnicodeError:
        raise PreflightError("candidate_git_unavailable") from None
    if not COMMIT.fullmatch(commit):
        raise PreflightError("candidate_git_unavailable")
    selected = [*ASSET_FILES, *(APP_FILES if include_app else ()),
                *(BACKEND_FILES if include_backend else ())]
    if include_app or include_backend:
        selected.append(TELEMETRY_METADATA)
    assets = {name: _git(root, "show", f"{commit}:apps/web/{name}") for name in dict.fromkeys(selected)}
    canonical = {name: _git(root, "show", f"{commit}:examples/hackathon-demo/{name}") for name in CAPTURE_FILES}
    capture_commit = validate_capture(assets, canonical)
    # Capture files are -text in .gitattributes; the local fallback must also
    # retain their exact committed bytes. Ordinary JS CRLF is not a mismatch.
    try:
        for name in CAPTURE_FILES:
            for directory in (root / "examples/hackathon-demo", root / "apps/web/hackathon-demo"):
                if (directory / name).read_bytes() != canonical[name]:
                    raise PreflightError("local_capture_mismatch")
    except OSError:
        raise PreflightError("local_capture_unavailable") from None
    validate_dependencies(assets)
    if include_app or include_backend:
        validate_telemetry_bundle(assets)
    return Candidate(commit, assets, capture_commit)


def validate_url(value: str, *, health: bool = False) -> str:
    try:
        if any(character.isspace() or ord(character) < 32 for character in value):
            raise ValueError
        parsed = urlsplit(value)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError
        if parsed.query or parsed.fragment or "?" in value or "#" in value or "\\" in value:
            raise ValueError
        _ = parsed.port  # Validate malformed/out-of-range ports.
        loopback = parsed.hostname.lower() == "localhost"
        try:
            loopback = loopback or ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            pass
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError
        if parsed.path not in ({"/health", "/api/health"} if health else {"", "/"}):
            raise ValueError
    except ValueError:
        raise PreflightError("invalid_health_url" if health else "invalid_site_url") from None
    return value.rstrip("/") if not health else value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _media_type(value: str) -> str:
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type if len(media_type) <= 80 and re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", media_type) else "invalid"


def _read_url(url: str, *, timeout: float, max_bytes: int) -> Response:
    request = Request(url, headers={
        "Accept-Encoding": "identity", "Cache-Control": "no-cache",
        "User-Agent": "Ohmni-Release-Rehearsal/1.0",
    }, method="GET")
    opener = build_opener(_NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=timeout) as response:
            content_type = _media_type(response.headers.get("Content-Type", ""))
            length = response.headers.get("Content-Length")
            if length and (len(length) > 20 or not length.isdigit() or int(length) > max_bytes):
                raise PreflightError("response_too_large", status_code=response.status, content_type=content_type)
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise PreflightError("response_too_large", status_code=response.status, content_type=content_type)
            return Response(response.status, content_type, body)
    except HTTPError as error:
        # Do not read or report bodies, Location, reason phrases or exception text.
        error.close()
        raise PreflightError("redirect_refused" if 300 <= error.code < 400 else "http_error",
                             status_code=error.code) from None
    except (TimeoutError, OSError, URLError, HTTPException):
        raise PreflightError("transport_error") from None


def fetch_url(url: str, *, timeout: float, max_bytes: int) -> Response:
    """Bound the caller's wait, including DNS and a continuously trickling body.

    urllib's socket timeout measures inactivity, not total elapsed time. A
    daemon worker may continue its bounded GET after this caller gives up. The
    CLI's explicitly selected fixed lists bound the worker count. It does not
    retry, and lingering workers cannot hold process exit open.
    """
    completed: Queue[Response | PreflightError] = Queue(maxsize=1)

    def worker() -> None:
        try:
            result = _read_url(url, timeout=timeout, max_bytes=max_bytes)
        except PreflightError as error:
            result = error
        except Exception:  # noqa: BLE001 -- an unexpected transport failure stays opaque
            result = PreflightError("transport_error")
        completed.put(result)

    threading.Thread(target=worker, daemon=True).start()
    try:
        result = completed.get(timeout=timeout)
    except Empty:
        raise PreflightError("request_deadline_exceeded") from None
    if isinstance(result, PreflightError):
        raise result
    return result


def _health(url: str, fetcher, timeout: float) -> dict:
    result = {"status": "FAIL", "url": url, "kind": "configuration_only"}
    try:
        response = fetcher(url, timeout=timeout, max_bytes=HEALTH_MAX_BYTES)
        result.update(response_code=response.status_code, content_type=response.content_type)
        if response.status_code != 200 or response.content_type != "application/json":
            raise PreflightError("health_response_invalid")
        if len(response.body) > HEALTH_MAX_BYTES:
            raise PreflightError("response_too_large")
        value = json.loads(response.body)
        valid = (
            isinstance(value, dict) and value.get("status") == "ready"
            and set(value) in (HEALTH_FIELDS, HEALTH_FIELDS | {"free_text"})
            and type(value.get("free_text", False)) is bool
            and type(value.get("api_version")) is int and value["api_version"] == EXPECTED_API_VERSION
            and isinstance(value.get("ui_version"), str) and DIGEST.fullmatch(value["ui_version"])
            and isinstance(value.get("server_instance_id"), str)
            and re.fullmatch(r"[0-9a-f]{16}", value["server_instance_id"])
            and value.get("fixture_id") == EXPECTED_FIXTURE_ID
        )
        if not valid:
            raise PreflightError("health_contract_invalid")
        # Do not publish instance IDs, unknown fields or raw response content.
        result.update(status="PASS", code="ready_contract_observed", capabilities={
            "status": "ready", "free_text": value.get("free_text", False), "api_version": value["api_version"],
        })
    except (ValueError, UnicodeError, RecursionError):
        result["code"] = "health_json_invalid"
    except PreflightError as error:
        result["code"] = error.code
        if error.status_code is not None:
            result["response_code"] = error.status_code
    return result


def _check_assets(site: str, candidate: Candidate, files: tuple[str, ...], fetcher,
                  timeout: float) -> list[dict]:
    assets = []
    for name in files:
        expected = candidate.assets[name]
        item = {
            "path": "/" + name, "status": "FAIL", "expected_sha256": sha256(expected),
            "expected_bytes": len(expected), "observed_sha256": None,
            "response_code": None, "content_type": None,
        }
        try:
            response = fetcher(site + "/" + name, timeout=timeout,
                               max_bytes=min(MAX_RESPONSE_BYTES, len(expected) + 1))
            item.update(response_code=response.status_code, content_type=response.content_type,
                        observed_sha256=sha256(response.body), observed_bytes=len(response.body))
            if response.status_code != 200:
                raise PreflightError("http_error")
            if len(response.body) > min(MAX_RESPONSE_BYTES, len(expected) + 1):
                raise PreflightError("response_too_large")
            if response.content_type not in MIME_TYPES[Path(name).suffix]:
                raise PreflightError("content_type_mismatch")
            if response.body != expected:
                raise PreflightError("asset_bytes_mismatch")
            item.update(status="PASS", code="matches_candidate")
        except PreflightError as error:
            item["code"] = error.code
            if error.status_code is not None:
                item["response_code"] = error.status_code
            if error.content_type is not None:
                item["content_type"] = error.content_type
        assets.append(item)
    return assets


def _asset_group(site: str | None, candidate: Candidate, files: tuple[str, ...],
                 fetcher, timeout: float) -> dict:
    if site is None:
        return {"status": "NOT_RUN"}
    assets = _check_assets(site, candidate, files, fetcher, timeout)
    return {"status": "PASS" if all(item["status"] == "PASS" for item in assets) else "FAIL",
            "kind": "selected_static_assets_only", "site": site, "assets": assets}


def rehearse(site: str, candidate: Candidate, *, health_url: str | None = None,
             include_app: bool = False, backend_site: str | None = None,
             timeout: float = 10, fetcher=fetch_url) -> dict:
    site = validate_url(site)
    if health_url is not None:
        health_url = validate_url(health_url, health=True)
    if backend_site is not None:
        backend_site = validate_url(backend_site)
    if not 0 < timeout <= 30:
        raise PreflightError("invalid_timeout")
    selected = (*ASSET_FILES, *(APP_FILES if include_app else ()),
                *(BACKEND_FILES if backend_site else ()))
    if any(name not in candidate.assets for name in selected):
        raise PreflightError("candidate_selected_assets_missing")
    if include_app or backend_site:
        validate_telemetry_bundle(candidate.assets)
    assets = _check_assets(site, candidate, ASSET_FILES, fetcher, timeout)
    static_status = "PASS" if all(item["status"] == "PASS" for item in assets) else "FAIL"
    app = _asset_group(site if include_app else None, candidate, APP_FILES, fetcher, timeout)
    backend = _asset_group(backend_site, candidate, BACKEND_FILES, fetcher, timeout)
    health = _health(health_url, fetcher, timeout) if health_url else {"status": "NOT_RUN"}
    return {
        "schema_version": 1, "kind": "saved_demo_static_alignment",
        "checked_at": datetime.now(UTC).isoformat(), "candidate_commit": candidate.commit,
        "capture_commit": candidate.capture_commit, "site": site,
        "status": "FAIL" if "FAIL" in (static_status, app["status"], backend["status"], health["status"]) else "PASS",
        "static_alignment": static_status, "assets": assets, "health": health,
        "app_entry_alignment": app, "backend_static_alignment": backend,
        "maximum_requests": len(selected) + int(health_url is not None),
        "limitations": LIMITATIONS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, help="Explicit HTTPS origin (HTTP allowed only on loopback)")
    parser.add_argument("--health-url", help="Optional explicit /api/health or /health URL; no provider call")
    parser.add_argument("--include-app", action="store_true", help="Also compare selected application and telemetry entry assets")
    parser.add_argument("--backend-site", help="Optional explicit backend origin; compare its selected static assets, not its code identity")
    parser.add_argument("--timeout", type=float, default=10, help="Per-request timeout in seconds, up to 30")
    parser.add_argument("--output", type=Path, help="Also save the JSON report at this path")
    args = parser.parse_args(argv)
    try:
        validate_url(args.site)
        if args.health_url:
            validate_url(args.health_url, health=True)
        if args.backend_site:
            validate_url(args.backend_site)
        candidate = load_candidate(include_app=args.include_app, include_backend=args.backend_site is not None)
        result = rehearse(args.site, candidate, health_url=args.health_url, timeout=args.timeout,
                          include_app=args.include_app, backend_site=args.backend_site)
    except PreflightError as error:
        result = {"schema_version": 1, "kind": "saved_demo_static_alignment", "status": "FAIL",
                  "code": error.code, "limitations": LIMITATIONS}
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        except OSError:
            print(json.dumps({"status": "FAIL", "code": "report_write_failed"}))
            return 1
    print(rendered, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
