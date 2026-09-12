"""Bounded, noninteractive native-tool execution.

Windows children inherit their parent's process error mode. Keep native tool
crashes in captured diagnostics instead of desktop error dialogs. This changes
only this process temporarily; no machine, registry, or KiCad settings change.
See https://learn.microsoft.com/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode
"""

from __future__ import annotations

import ctypes
import locale
import math
import os
import subprocess
import tempfile
from contextlib import contextmanager
from threading import RLock
from time import monotonic

#: This wrapper's own name for a bounded run that ran out of time. Callers work
#: in terms of run_tool, not of the module it happens to be built on, so they
#: catch this rather than importing subprocess to name one exception type.
ToolTimeoutError = subprocess.TimeoutExpired

_WINDOWS = os.name == "nt"
_ERROR_MODE_LOCK = RLock()
_NONINTERACTIVE_ERRORS = 0x0001 | 0x0002 | 0x8000
_CREATE_NO_WINDOW = 0x08000000
_CLEANUP_SECONDS = 2.0
_TREE_CLEANUP_SECONDS = 0.75


def _windows_kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetErrorMode.argtypes = []
    kernel.GetErrorMode.restype = ctypes.c_uint
    kernel.SetErrorMode.argtypes = [ctypes.c_uint]
    kernel.SetErrorMode.restype = ctypes.c_uint
    return kernel


@contextmanager
def _noninteractive_errors():
    if not _WINDOWS:
        yield
        return
    # SetThreadErrorMode does not set the process mode inherited by children.
    # Serialize process creation so parallel server jobs cannot restore another
    # call's mode while its child is being launched. Child execution happens
    # outside this context: the inherited mode belongs to the child already.
    with _ERROR_MODE_LOCK:
        kernel = _windows_kernel()
        previous = kernel.GetErrorMode()
        kernel.SetErrorMode(previous | _NONINTERACTIVE_ERRORS)
        try:
            yield
        finally:
            kernel.SetErrorMode(previous)


def _kill_and_wait(child, deadline: float) -> None:
    """Best effort termination; never replace the original timeout/failure."""
    try:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=max(0, deadline - monotonic()))
    except (OSError, subprocess.TimeoutExpired):
        pass


def _terminate(child) -> None:
    """Bound cleanup, including a best effort Windows descendant termination.

    This is local-tool reliability, not adversarial process-tree isolation.
    Even if taskkill is unavailable or unsuccessful, direct-child cleanup and
    captured-output reads have finite bounds and do not wait for pipe EOF.
    """
    deadline = monotonic() + _CLEANUP_SECONDS
    if _WINDOWS and child.poll() is None:
        cleaner = None
        try:
            executable = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                      "System32", "taskkill.exe")
            with _noninteractive_errors():
                cleaner = subprocess.Popen(
                    [executable, "/PID", str(child.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, shell=False,
                    creationflags=_CREATE_NO_WINDOW,
                )
            cleaner.wait(timeout=min(_TREE_CLEANUP_SECONDS,
                                     max(0, deadline - monotonic())))
        except (OSError, subprocess.TimeoutExpired):
            pass
        finally:
            if cleaner is not None:
                _kill_and_wait(cleaner, min(deadline, monotonic() + .25))
    _kill_and_wait(child, deadline)


def _captured_text(stream) -> str:
    # A descendant may still own an inherited file handle after best effort
    # cleanup. Snapshot a finite byte count instead of waiting for EOF. These
    # are plain files: there are no communicate reader threads/stream locks.
    size = stream.seek(0, os.SEEK_END)
    stream.seek(0)
    return stream.read(size).decode(locale.getpreferredencoding(False), errors="replace").replace(
        "\r\n", "\n").replace("\r", "\n")


def run_tool(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    """Run fixed argv without a shell, with bounded waiting and cleanup.

    Native failures keep their actual exit code. The caller must reject failed
    checks; suppressing a desktop dialog never turns a crash into a success.
    As with subprocess.run, platform process creation cannot be interrupted.
    A timeout allows at most two additional seconds of cleanup waits. Captures
    use temporary files, so descendants retaining stdout cannot stall cleanup.
    Available diagnostics are decoded as text, replacing invalid byte sequences.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        raise ValueError("Native tool timeout must be finite and nonnegative")
    options = {"creationflags": _CREATE_NO_WINDOW} if _WINDOWS else {}
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        with _noninteractive_errors():
            child = subprocess.Popen(
                command, stdout=output, stderr=errors,
                shell=False, **options,
            )
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            _terminate(child)
            error.stdout, error.stderr = _captured_text(output), _captured_text(errors)
            raise
        except BaseException:
            _terminate(child)
            raise
        return subprocess.CompletedProcess(command, child.returncode,
                                           _captured_text(output), _captured_text(errors))


def describe_exit(return_code: int) -> str:
    """Keep native Windows exception codes recognizable in user diagnostics."""
    unsigned = return_code & 0xFFFFFFFF
    if unsigned >= 0x80000000 and (return_code >= 0 or return_code < -255):
        detail = {
            0xC0000005: "access violation",
            0xC0000135: "missing DLL",
            0xC0000142: "DLL initialization failed",
            0xC0000409: "native fail-fast exception",
        }.get(unsigned, "native process failure")
        return f"exit 0x{unsigned:08X} ({detail})"
    return f"exit {return_code}"
