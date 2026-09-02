"""Live Windows process and browser coverage for the local demo contract."""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from scripts.demo_server import (
    DEMO_FIXTURE_ID,
    STARTUP_FAILURE_MESSAGE,
    DemoHandler,
    DemoHTTPServer,
    JobStore,
)

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "scripts" / "demo_server.py"
BROWSER_SMOKE = ROOT / "scripts" / "demo_browser_smoke.mjs"
API_VERSION = 2
JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")
INSTANCE_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")
UI_VERSION_PATTERN = re.compile(r"^[0-9a-f]{64}$")
NO_PROXY_OPENER = build_opener(ProxyHandler({}))


class _PipeLines:
    """Drain a subprocess pipe while allowing a bounded wait for one line."""

    def __init__(self, pipe):
        self.lines: list[str] = []
        self.pending: queue.Queue[str] = queue.Queue()
        self.thread = threading.Thread(target=self._read, args=(pipe,), daemon=True)
        self.thread.start()

    def _read(self, pipe):
        for line in iter(pipe.readline, ""):
            self.lines.append(line)
            self.pending.put(line)

    def next(self, timeout: float) -> str:
        return self.pending.get(timeout=timeout)

    @property
    def text(self) -> str:
        return "".join(self.lines)


def _available_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return candidate.getsockname()[1]


def _json_request(
    base: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 3,
) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode()
    request_headers = dict(headers or {})
    if body is not None:
        request_headers["content-type"] = "application/json"
    request = Request(base + path, data=body, headers=request_headers, method=method)
    try:
        with NO_PROXY_OPENER.open(request, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def _identity_headers(identity: dict[str, object]) -> dict[str, str]:
    return {
        "X-Ohmni-API-Version": str(identity["api_version"]),
        "X-Ohmni-Server-Instance": str(identity["server_instance_id"]),
        "X-Ohmni-UI-Version": str(identity["ui_version"]),
    }


def _assert_identity(payload: dict[str, object]) -> None:
    assert payload["api_version"] == API_VERSION
    assert INSTANCE_ID_PATTERN.fullmatch(str(payload["server_instance_id"]))
    assert UI_VERSION_PATTERN.fullmatch(str(payload["ui_version"]))


def _listener_snapshot(port: int) -> list[int]:
    command = (
        f"$items=@(Get-NetTCPConnection -State Listen -LocalPort {port} "
        "-ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -eq '127.0.0.1'});"
        "$items | ForEach-Object {[string]$_.OwningProcess}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return [int(line) for line in result.stdout.splitlines() if line.strip()]


def _await_listener_count(port: int, count: int, timeout: float = 8) -> list[int]:
    deadline = time.monotonic() + timeout
    owners: list[int] = []
    while time.monotonic() < deadline:
        owners = _listener_snapshot(port)
        if len(owners) == count:
            return owners
        time.sleep(0.05)
    raise AssertionError(f"port {port} had listener PIDs {owners}, expected {count}")


def _start_server(port: int) -> tuple[subprocess.Popen[str], _PipeLines, _PipeLines]:
    process = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT), "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    assert process.stdout is not None and process.stderr is not None
    stdout = _PipeLines(process.stdout)
    stderr = _PipeLines(process.stderr)
    expected = f"Ohmni demo: http://127.0.0.1:{port}\n"
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(
                f"demo server exited {process.returncode}; stdout={stdout.text!r}; stderr={stderr.text!r}"
            )
        try:
            line = stdout.next(min(0.1, deadline - time.monotonic()))
        except queue.Empty:
            continue
        if line == expected:
            return process, stdout, stderr
        raise AssertionError(f"unexpected demo startup output: {line!r}")
    raise AssertionError(
        f"demo startup line was not flushed; stdout={stdout.text!r}; stderr={stderr.text!r}"
    )


def _kill_tree(process_id: int) -> None:
    subprocess.run(
        ["taskkill.exe", "/PID", str(process_id), "/T", "/F"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _stop_server(process: subprocess.Popen[str], port: int) -> None:
    if process.poll() is None:
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            process.wait(timeout=8)
        except (OSError, subprocess.TimeoutExpired):
            _kill_tree(process.pid)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    try:
        owners = _await_listener_count(port, 0, timeout=3)
    except AssertionError:
        owners = _listener_snapshot(port)
        for owner in owners:
            _kill_tree(owner)
        _await_listener_count(port, 0, timeout=5)


def _wait_for_health(base: str, process: subprocess.Popen[str]) -> dict[str, object]:
    deadline = time.monotonic() + 8
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"demo server exited with {process.returncode}")
        try:
            status, health = _json_request(base, "/api/health", timeout=1)
            if status == 200:
                return health
        except (OSError, URLError) as error:
            last_error = error
        time.sleep(0.05)
    raise AssertionError(f"demo health endpoint did not become ready: {last_error}")


@pytest.mark.integration
@pytest.mark.skipif(os.name != "nt", reason="Windows endpoint ownership regression")
def test_windows_demo_subprocess_has_one_owner_and_restart_identity():
    port = _available_port()
    base = f"http://127.0.0.1:{port}"
    first = second = restarted = None
    old_job_id = None
    try:
        first, _, first_stderr = _start_server(port)
        first_health = _wait_for_health(base, first)
        assert first_health["status"] == "ready"
        assert first_health["fixture_id"] == DEMO_FIXTURE_ID
        _assert_identity(first_health)

        owners = _await_listener_count(port, 1)
        assert owners[0] > 0  # The listener may be the venv launcher's child process.

        second = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT), "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        duplicate_stdout, duplicate_stderr = second.communicate(timeout=8)
        assert second.returncode == 1
        assert duplicate_stdout == ""
        duplicate_lines = duplicate_stderr.splitlines()
        assert json.loads(duplicate_lines[0]) == {
            "api_version": API_VERSION,
            "component": "ohmni_demo",
            "event": "server_bind_failed",
        }
        assert duplicate_lines[1:] == [STARTUP_FAILURE_MESSAGE]
        assert "Traceback" not in duplicate_stderr
        assert _await_listener_count(port, 1) == owners
        assert _wait_for_health(base, first) == first_health

        start_payload = {
            "fixture_id": DEMO_FIXTURE_ID,
            "api_version": API_VERSION,
            "server_instance_id": first_health["server_instance_id"],
            "ui_version": first_health["ui_version"],
        }
        status, accepted = _json_request(base, "/api/demo", method="POST", payload=start_payload)
        assert status == 202 and accepted["status"] == "queued"
        assert JOB_ID_PATTERN.fullmatch(str(accepted["job_id"]))
        _assert_identity(accepted)
        assert accepted["server_instance_id"] == first_health["server_instance_id"]
        old_job_id = str(accepted["job_id"])

        _stop_server(first, port)
        first = None
        restarted, _, restart_stderr = _start_server(port)
        restarted_health = _wait_for_health(base, restarted)
        _assert_identity(restarted_health)
        assert restarted_health["server_instance_id"] != first_health["server_instance_id"]
        assert restarted_health["ui_version"] == first_health["ui_version"]
        assert len(_await_listener_count(port, 1)) == 1

        stale_status, stale_body = _json_request(
            base,
            f"/api/jobs/{old_job_id}",
            headers=_identity_headers(first_health),
        )
        assert stale_status == 409
        assert stale_body == {"error": "server_instance_mismatch"}

        missing_status, missing_body = _json_request(
            base,
            f"/api/jobs/{old_job_id}",
            headers=_identity_headers(restarted_health),
        )
        assert missing_status == 404
        assert missing_body == {"error": "job_not_found"}
        assert "Traceback" not in first_stderr.text + restart_stderr.text
    finally:
        if second is not None and second.poll() is None:
            _kill_tree(second.pid)
        if first is not None:
            _stop_server(first, port)
        if restarted is not None:
            _stop_server(restarted, port)
        if old_job_id is not None and JOB_ID_PATTERN.fullmatch(old_job_id):
            job_directory = ROOT / "out" / "demo-jobs" / old_job_id
            shutil.rmtree(job_directory, ignore_errors=True)


def _find_chromium() -> Path | None:
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _wait_for_cdp(debug_port: int, page_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"browser exited with {process.returncode}")
        try:
            with NO_PROXY_OPENER.open(
                f"http://127.0.0.1:{debug_port}/json/list", timeout=1
            ) as response:
                targets = json.loads(response.read())
            if any(item.get("type") == "page" and item.get("url") == page_url for item in targets):
                return
        except (OSError, URLError, json.JSONDecodeError):
            pass
        time.sleep(0.1)
    raise AssertionError("browser CDP target did not become ready")


@pytest.mark.integration
@pytest.mark.skipif(os.name != "nt", reason="Windows browser operability regression")
def test_real_browser_click_posts_and_advances_beyond_zero(tmp_path):
    chrome = _find_chromium()
    node = shutil.which("node")
    if chrome is None or node is None:
        pytest.skip("Chromium and Node are required for the optional browser integration")

    progressed = threading.Event()
    release = threading.Event()

    class Report:
        def model_dump(self, mode=None):
            return {"result": "browser integration complete"}

    class Pipeline:
        def __init__(self, progress):
            self.progress = progress

        def run(self, destination, request):
            self.progress(
                SimpleNamespace(
                    model_dump=lambda mode=None: {
                        "stage": "requirements",
                        "label": "Browser form reached the worker",
                        "status": "RUNNING",
                        "percent": 5,
                        "detail": "",
                    }
                )
            )
            progressed.set()
            release.wait(20)
            return Report()

    store = JobStore(tmp_path / "jobs", Pipeline)
    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    page_url = f"http://127.0.0.1:{server.server_port}/"
    debug_port = _available_port()
    profile = tmp_path / "chrome-profile"
    browser = subprocess.Popen(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={profile}",
            page_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    try:
        _wait_for_cdp(debug_port, page_url, browser)
        result = subprocess.run(
            [
                node,
                str(BROWSER_SMOKE),
                "--debug-port",
                str(debug_port),
                "--page-url",
                page_url,
                "--timeout-ms",
                "20000",
                "--stop-after-progress",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        smoke = json.loads(result.stdout)
        assert smoke["mode"] == "progress"
        assert smoke["progress"] > 0
        assert JOB_ID_PATTERN.fullmatch(smoke["job_id"])
        assert INSTANCE_ID_PATTERN.fullmatch(smoke["server_instance_id"])
        assert UI_VERSION_PATTERN.fullmatch(smoke["ui_version"])
        assert {item["status"] for item in smoke["api"] if item["path"] == "/api/demo"} == {202}
        assert any(
            item["method"] == "GET"
            and item["path"].startswith(f"/api/jobs/{smoke['job_id']}")
            and item["status"] == 200
            for item in smoke["api"]
        )
        assert progressed.wait(2)
    finally:
        release.set()
        if browser.poll() is None:
            _kill_tree(browser.pid)
            try:
                browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait(timeout=5)
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)
