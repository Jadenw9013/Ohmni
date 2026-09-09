"""Bounded, noninteractive native-tool execution.

Windows children inherit their parent's process error mode. Keep native tool
crashes in captured diagnostics instead of desktop error dialogs. This changes
only this process temporarily; no machine, registry, or KiCad settings change.
See https://learn.microsoft.com/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode
"""

from __future__ import annotations

import ctypes
import math
import os
import subprocess
from contextlib import contextmanager
from threading import RLock

_WINDOWS = os.name == "nt"
_ERROR_MODE_LOCK = RLock()
_NONINTERACTIVE_ERRORS = 0x0001 | 0x0002 | 0x8000
_CREATE_NO_WINDOW = 0x08000000


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


def run_tool(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    """Run fixed argv without a shell, with a finite child-communication timeout.

    Native failures keep their actual exit code. The caller must reject failed
    checks; suppressing a desktop dialog never turns a crash into a success.
    As with subprocess.run, platform process creation cannot be interrupted.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        raise ValueError("Native tool timeout must be finite and nonnegative")
    options = {"creationflags": _CREATE_NO_WINDOW} if _WINDOWS else {}
    with _noninteractive_errors():
        child = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, shell=False, **options,
        )
    with child:
        try:
            stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            child.kill()
            if _WINDOWS:
                # Windows communicate uses reader threads; after termination,
                # collect their output just as subprocess.run does.
                error.stdout, error.stderr = child.communicate()
            else:
                # POSIX already includes captured output in TimeoutExpired.
                child.wait()
            raise
        except BaseException:
            # Cancellation and decoding/communication failures must not leave
            # a native child running. The context closes all captured pipes.
            child.kill()
            child.wait()
            raise
        return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)


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
