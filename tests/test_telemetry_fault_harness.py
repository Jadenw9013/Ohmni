"""The offline rehearsal must exercise a real timeout on Windows and POSIX."""

from __future__ import annotations

import errno
import json
import socket
import subprocess
import sys

import pytest
from telemetry_support import NetworkGuard, isolate_environment

from ohmni.adapters import process, telemetry
from scripts import telemetry_fault_harness as harness


@pytest.fixture(autouse=True)
def isolated_telemetry(monkeypatch):
    isolate_environment(monkeypatch)
    guard = NetworkGuard()
    guard.install(monkeypatch)
    telemetry.shutdown(0)
    try:
        yield
    finally:
        telemetry.shutdown(0)
        assert guard.attempts == []


def test_timeout_fixture_starts_and_is_terminated_without_a_shell(tmp_path, monkeypatch):
    real_popen = subprocess.Popen
    children = []

    def observed_popen(command, **kwargs):
        child = real_popen(command, **kwargs)
        if command[0] == sys.executable:
            children.append((child, kwargs))
        return child

    monkeypatch.setattr(subprocess, "Popen", observed_popen)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        process.run_tool(harness.timeout_child_command(tmp_path), timeout=1.0)
    assert harness.TIMEOUT_CHILD_READY in caught.value.stdout
    assert len(children) == 1
    child, options = children[0]
    assert options["shell"] is False
    assert child.poll() is not None


def test_offline_fault_harness_proves_timeout_and_recovery(tmp_path):
    summary = harness.run(tmp_path / "evidence")
    assert summary["status"] == "PASS"
    assert len(summary["checks"]) == 8 and all(summary["checks"].values())
    assert json.loads((tmp_path / "evidence" / "summary.json").read_text()) == summary
    timeout = next(item for item in summary["scenarios"] if item["name"] == "tool_timeout")
    assert timeout["public"] == {"status": "failed", "error_code": "eda_tool_failed"}
    assert [issue["value"] for issue in timeout["issues"]] == ["worker.eda_tool_failed"]
    tool_spans = [span for transaction in timeout["transactions"]
                  for span in transaction["spans"] if span["op"] == "ohmni.tool"]
    assert len(tool_spans) == 1
    assert tool_spans[0]["name"] == "other"
    assert tool_spans[0]["ohmni.execution_outcome"] == "timeout"


def test_harness_guard_blocks_connect_ex_before_delegating(monkeypatch):
    # Replace the underlying method with a sentinel: neither the test fixture's
    # network guard nor a real socket may make this test pass on the harness's behalf.
    delegated = []

    def forbidden_connect_ex(sock, address):
        delegated.append(address)
        raise AssertionError("harness delegated a forbidden connection")

    monkeypatch.setattr(socket.socket, "connect_ex", forbidden_connect_ex)
    with harness.refuse_outbound() as attempts, socket.socket() as connection:
        assert connection.connect_ex(("203.0.113.1", 443)) == errno.ECONNREFUSED
        assert attempts == ["connect_ex"]
    assert delegated == []
    assert socket.socket.connect_ex is forbidden_connect_ex
