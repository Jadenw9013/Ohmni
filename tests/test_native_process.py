"""A native crash must be observable without putting dialogs on the desktop."""

import ctypes
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from ohmni.adapters import process
from ohmni.adapters.tools import _run_version


@pytest.mark.parametrize("failure", [None, OSError("launch refused"), subprocess.TimeoutExpired("tool", 1)])
def test_windows_mode_preserved_and_restored_even_on_failure(monkeypatch, failure):
    state = {"mode": 0x10}
    changes = []
    operations = []
    captures = []

    def set_mode(mode):
        changes.append(mode)
        state["mode"] = mode

    monkeypatch.setattr(process, "_WINDOWS", True)
    monkeypatch.setattr(process, "_windows_kernel", lambda: SimpleNamespace(
        GetErrorMode=lambda: state["mode"], SetErrorMode=set_mode,
    ))

    class Child:
        returncode = 0xC0000005

        def wait(self, timeout):
            assert state["mode"] == 0x10  # Restored before any wait.
            operations.append("wait")
            assert timeout == 1
            if failure:
                raise failure
            return self.returncode

    def launch(command, **options):
        assert state["mode"] == 0x8013
        assert options["creationflags"] == 0x08000000
        assert options["shell"] is False
        captures.extend([options["stdout"], options["stderr"]])
        options["stdout"].write(b"captured stdout")
        options["stderr"].write(b"captured stderr")
        assert "timeout" not in options
        if isinstance(failure, OSError):
            raise failure
        return Child()

    monkeypatch.setattr(process.subprocess, "Popen", launch)
    monkeypatch.setattr(process, "_terminate", lambda child: operations.append("terminate"))
    if failure:
        with pytest.raises(type(failure)) as caught:
            process.run_tool(["tool", "a path with spaces"], timeout=1)
        if isinstance(failure, subprocess.TimeoutExpired):
            assert caught.value.stdout == "captured stdout"
            assert caught.value.stderr == "captured stderr"
            assert operations == ["wait", "terminate"]
    else:
        assert process.run_tool(["tool", "a path with spaces"], timeout=1).returncode == 0xC0000005
        assert operations == ["wait"]
    assert changes == [0x8013, 0x10]
    assert state["mode"] == 0x10
    assert all(capture.closed for capture in captures)


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
    captures = []
    original = process.subprocess.Popen

    def launch(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        if kwargs["stdout"] != subprocess.DEVNULL:
            captures.extend([kwargs["stdout"], kwargs["stderr"]])
        return child

    monkeypatch.setattr(process.subprocess, "Popen", launch)
    with pytest.raises(subprocess.TimeoutExpired):
        process.run_tool([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.2)
    assert children and all(child.poll() is not None for child in children)
    assert all(capture.closed for capture in captures)


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


def test_wait_exception_terminates_child_and_closes_captures(monkeypatch):
    operations = []
    captures = []

    class Child:
        def wait(self, **_):
            raise RuntimeError("wait failed")

    def launch(*args, **kwargs):
        captures.extend([kwargs["stdout"], kwargs["stderr"]])
        return Child()
    monkeypatch.setattr(process.subprocess, "Popen", launch)
    monkeypatch.setattr(process, "_terminate", lambda child: operations.append("terminate"))
    with pytest.raises(RuntimeError, match="wait failed"):
        process.run_tool(["tool"], timeout=1)
    assert operations == ["terminate"]
    assert all(capture.closed for capture in captures)


def test_cleanup_waits_are_bounded_when_tree_killer_and_child_wont_exit(monkeypatch):
    clock = {"now": 0.0}
    waits = []
    launches = []
    monkeypatch.setattr(process, "_WINDOWS", True)
    monkeypatch.setattr(process, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(process, "_noninteractive_errors", nullcontext)

    class Stuck:
        pid = 123
        def poll(self): return None
        def kill(self): pass
        def wait(self, timeout):
            waits.append(timeout)
            clock["now"] += timeout
            raise subprocess.TimeoutExpired("stuck", timeout)

    def launch(command, **options):
        launches.append((command, options))
        return Stuck()
    monkeypatch.setattr(process.subprocess, "Popen", launch)
    process._terminate(Stuck())
    assert sum(waits) == pytest.approx(process._CLEANUP_SECONDS)
    assert all(value >= 0 for value in waits)
    command, options = launches[0]
    assert command[1:] == ["/PID", "123", "/T", "/F"]
    assert options["creationflags"] == 0x08000000 and options["shell"] is False
    assert options["stdout"] == options["stderr"] == subprocess.DEVNULL


def test_missing_tree_killer_still_kills_and_reaps_direct_child(monkeypatch):
    operations = []
    monkeypatch.setattr(process, "_WINDOWS", True)
    monkeypatch.setattr(process, "_noninteractive_errors", nullcontext)
    monkeypatch.setattr(process.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("unavailable")))
    child = SimpleNamespace(pid=123, poll=lambda: None,
                            kill=lambda: operations.append("kill"),
                            wait=lambda timeout: operations.append(("wait", timeout)))
    process._terminate(child)
    assert operations[0] == "kill"
    assert 0 <= operations[1][1] <= process._CLEANUP_SECONDS


@pytest.mark.skipif(os.name != "nt", reason="Windows inherited capture handles")
@pytest.mark.parametrize("tree_cleanup", [True, False])
def test_inherited_descendant_capture_cannot_hold_timeout_open(tmp_path, monkeypatch, tree_cleanup):
    descendant_id = tmp_path / "descendant.pid"
    original = process.subprocess.Popen
    captures = []

    def launch(command, **options):
        if str(command[0]).lower().endswith("taskkill.exe") and not tree_cleanup:
            raise OSError("Tree cleanup deliberately unavailable")
        if options["stdout"] != subprocess.DEVNULL:
            captures.extend([options["stdout"], options["stderr"]])
        return original(command, **options)
    monkeypatch.setattr(process.subprocess, "Popen", launch)
    code = (
        "import pathlib,subprocess,sys,time; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'], "
        "stdout=sys.stdout,stderr=sys.stderr,creationflags=0x08000000); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid)); "
        "print('descendant launched',flush=True); "
        "print('saved stderr',file=sys.stderr,flush=True); time.sleep(20)"
    )
    started = time.monotonic()
    try:
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            process.run_tool([sys.executable, "-c", code, str(descendant_id)], timeout=4.0)
        # The descendant lives for 20 seconds unless the tree-kill succeeds.
        # Neither that lifetime nor inherited file handles may delay return.
        assert time.monotonic() - started < 12
        assert descendant_id.exists(), "The reproducer must actually launch its descendant"
        assert "descendant launched" in caught.value.stdout
        assert "saved stderr" in caught.value.stderr
        assert all(capture.closed for capture in captures)
    finally:
        if descendant_id.exists():
            pid = int(descendant_id.read_text())
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x0001, False, pid)
            if handle:
                kernel.TerminateProcess(handle, 1)
                kernel.CloseHandle(handle)


def test_capture_preserves_diagnostics_and_replaces_invalid_text(monkeypatch):
    monkeypatch.setattr(process.locale, "getpreferredencoding", lambda _do_setlocale: "utf-8")
    result = process.run_tool([sys.executable, "-c",
        "import os; os.write(1,b'out\\r\\n'); os.write(2,b'bad: \\xff\\n')"], timeout=5)
    assert result.stdout == "out\n"
    assert result.stderr == "bad: \ufffd\n"


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
