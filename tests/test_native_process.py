"""A native crash must be observable without putting dialogs on the desktop."""

import ctypes
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from ohmni.adapters import process
from ohmni.adapters.tools import _run_version


@pytest.mark.parametrize("failure", [None, OSError("launch refused"), subprocess.TimeoutExpired("tool", 1)])
def test_windows_mode_preserved_and_restored_even_on_failure(monkeypatch, failure):
    state = {"mode": 0x10}
    changes = []
    operations = []

    def set_mode(mode):
        changes.append(mode)
        state["mode"] = mode

    monkeypatch.setattr(process, "_WINDOWS", True)
    monkeypatch.setattr(process, "_windows_kernel", lambda: SimpleNamespace(
        GetErrorMode=lambda: state["mode"], SetErrorMode=set_mode,
    ))

    class Child:
        returncode = 0xC0000005

        def __enter__(self):
            return self

        def __exit__(self, *_):
            operations.append("closed")

        def communicate(self, timeout=None):
            assert state["mode"] == 0x10  # Restored before any wait.
            operations.append("communicate")
            if timeout is not None:
                assert timeout == 1
                if failure:
                    raise failure
            return "captured stdout", "captured stderr"

        def kill(self):
            operations.append("kill")

        def wait(self):
            operations.append("wait")
            return self.returncode

    def launch(command, **options):
        assert state["mode"] == 0x8013
        assert options["creationflags"] == 0x08000000
        assert options["shell"] is False
        assert options["stdout"] == options["stderr"] == subprocess.PIPE
        assert "timeout" not in options
        if isinstance(failure, OSError):
            raise failure
        return Child()

    monkeypatch.setattr(process.subprocess, "Popen", launch)
    if failure:
        with pytest.raises(type(failure)) as caught:
            process.run_tool(["tool", "a path with spaces"], timeout=1)
        if isinstance(failure, subprocess.TimeoutExpired):
            assert caught.value.stdout == "captured stdout"
            assert caught.value.stderr == "captured stderr"
            assert operations == ["communicate", "kill", "communicate", "closed"]
    else:
        assert process.run_tool(["tool", "a path with spaces"], timeout=1).returncode == 0xC0000005
        assert operations == ["communicate", "closed"]
    assert changes == [0x8013, 0x10]
    assert state["mode"] == 0x10


@pytest.mark.skipif(os.name != "nt", reason="Windows child process inheritance")
def test_real_child_inherits_noninteractive_mode_and_parent_is_restored():
    kernel = ctypes.WinDLL("kernel32")
    previous = kernel.GetErrorMode()
    result = process.run_tool([
        sys.executable, "-c",
        "import ctypes,json; print(json.dumps(ctypes.WinDLL('kernel32').GetErrorMode()))",
    ], timeout=10)
    assert result.returncode == 0
    assert json.loads(result.stdout) & 0x8003 == 0x8003
    assert kernel.GetErrorMode() == previous


def test_native_timeout_is_bounded_and_reaps_child(monkeypatch):
    children = []
    original = process.subprocess.Popen

    def launch(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(process.subprocess, "Popen", launch)
    with pytest.raises(subprocess.TimeoutExpired):
        process.run_tool([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.2)
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdout.closed and children[0].stderr.closed


def test_concurrent_children_can_make_progress_before_either_exits(tmp_path):
    # Each child waits for evidence that its peer was launched. Serializing
    # their entire lifetimes makes the first child time out, even though two
    # independent processes should be able to finish immediately together.
    code = (
        "import pathlib,sys,time; "
        "mine,peer=map(pathlib.Path,sys.argv[1:]); mine.write_text('started'); "
        "\nwhile not peer.exists(): time.sleep(.01)"
        "\nprint('peer running',flush=True)"
    )
    first, second = tmp_path / "first", tmp_path / "second"
    previous = ctypes.WinDLL("kernel32").GetErrorMode() if os.name == "nt" else None
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(process.run_tool, [sys.executable, "-c", code, str(mine), str(peer)], timeout=3)
                 for mine, peer in ((first, second), (second, first))]
        results = [call.result(timeout=5) for call in calls]
    assert all(result.returncode == 0 and "peer running" in result.stdout for result in results)
    if previous is not None:
        assert ctypes.WinDLL("kernel32").GetErrorMode() == previous


def test_communication_exception_kills_and_reaps_child(monkeypatch):
    operations = []

    class Child:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            operations.append("closed")

        def communicate(self, **_):
            raise RuntimeError("communication failed")

        def kill(self):
            operations.append("kill")

        def wait(self):
            operations.append("wait")

    monkeypatch.setattr(process.subprocess, "Popen", lambda *a, **k: Child())
    with pytest.raises(RuntimeError, match="communication failed"):
        process.run_tool(["tool"], timeout=1)
    assert operations == ["kill", "wait", "closed"]


@pytest.mark.parametrize("timeout", [None, float("inf"), float("nan"), -1, True])
def test_invalid_timeout_is_refused_before_launch(monkeypatch, timeout):
    monkeypatch.setattr(process.subprocess, "Popen", lambda *a, **k: pytest.fail("Invalid timeout reached process creation"))
    with pytest.raises(ValueError, match="finite and nonnegative"):
        process.run_tool(["tool"], timeout=timeout)


@pytest.mark.parametrize("code", [0xC0000005, -1073741819])
def test_native_exception_code_is_not_lost(code):
    assert process.describe_exit(code) == "exit 0xC0000005 (access violation)"
    assert process.describe_exit(5) == "exit 5"
    assert process.describe_exit(-9) == "exit -9"


def test_failed_probe_includes_native_code(monkeypatch):
    monkeypatch.setattr("ohmni.adapters.tools.run_tool", lambda *a, **k:
        subprocess.CompletedProcess(a[0], 0xC0000005, "", ""))
    ok, detail = _run_version("kicad-cli")
    assert not ok
    assert "0xC0000005" in detail


def test_empty_version_is_failed_probe(monkeypatch):
    monkeypatch.setattr("ohmni.adapters.tools.run_tool", lambda *a, **k:
        subprocess.CompletedProcess(a[0], 0, "", ""))
    assert _run_version("kicad-cli") == (False, "Tool returned no version information.")
