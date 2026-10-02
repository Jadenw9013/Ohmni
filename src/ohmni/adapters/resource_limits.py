"""A self-applied address-space cap, for a process about to parse hostile bytes.

A wall-clock timeout bounds how long an untrusted parse runs; it does not bound
how much memory the parse commits in that time. A decompression bomb inside an
otherwise small content stream is exactly the case a timeout does not catch: it
allocates quickly, and the machine is under pressure before the clock expires.

This module supplies the other half. It is deliberately *self*-applied by the
child rather than imposed by the parent: the child is the process that performs
the allocation, and capping itself before it opens the document means there is
no window in which unbounded parsing is possible. The parent still owns the
clock, through :func:`ohmni.adapters.process.run_tool`.

The contract is fail-closed. :func:`apply_address_space_limit` either applies a
real cap and names the mechanism, or raises. It never returns "I could not do
this" as a success, because a caller that believed it was bounded and was not is
worse off than one that refused to parse.
"""

from __future__ import annotations

import ctypes
import math
import os

_WINDOWS = os.name == "nt"

#: Retained so the cap can be read back out of the kernel later, not because it
#: would otherwise lapse: a job keeps constraining its members for as long as
#: any process is still assigned to it, whether or not a handle stays open.
_JOB_HANDLE: int | None = None

_JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


class ResourceLimitUnavailable(RuntimeError):
    """No address-space cap could be applied. The caller must not proceed."""


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _apply_windows_limit(limit_bytes: int) -> str:
    """Put this process in an unnamed job object with a committed-memory cap.

    Nested jobs are supported from Windows 8, so this works even when the
    process is already inside a job -- a CI agent or a container, typically.
    When it is not supported, assignment fails and we raise rather than run on.
    """
    global _JOB_HANDLE
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel.CreateJobObjectW.restype = ctypes.c_void_p
    kernel.SetInformationJobObject.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32
    ]
    kernel.SetInformationJobObject.restype = ctypes.c_int
    kernel.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.AssignProcessToJobObject.restype = ctypes.c_int
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int

    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ResourceLimitUnavailable(
            f"CreateJobObject failed with error {ctypes.get_last_error()}"
        )
    try:
        info = _ExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_PROCESS_MEMORY
        info.ProcessMemoryLimit = ctypes.c_size_t(limit_bytes).value
        if not kernel.SetInformationJobObject(
            job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            raise ResourceLimitUnavailable(
                f"SetInformationJobObject failed with error {ctypes.get_last_error()}"
            )
        if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            raise ResourceLimitUnavailable(
                f"AssignProcessToJobObject failed with error {ctypes.get_last_error()}"
            )
    except BaseException:
        kernel.CloseHandle(job)
        raise
    _JOB_HANDLE = job
    return "windows-job-object:process-memory"


def _apply_posix_limit(limit_bytes: int) -> str:
    import resource

    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        limit_bytes = min(limit_bytes, hard)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, hard))
    except (ValueError, OSError) as exc:
        raise ResourceLimitUnavailable(f"setrlimit(RLIMIT_AS) failed: {exc}") from exc
    return "posix-rlimit:address-space"


def _apply_platform_limit(limit_bytes: int) -> str:
    """Seam for the fail-closed test: the only place a platform is chosen."""
    if _WINDOWS:
        return _apply_windows_limit(limit_bytes)
    return _apply_posix_limit(limit_bytes)


def _read_windows_limit() -> int:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.QueryInformationJobObject.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    kernel.QueryInformationJobObject.restype = ctypes.c_int
    info = _ExtendedLimitInformation()
    returned = ctypes.c_uint32(0)
    if not kernel.QueryInformationJobObject(
        _JOB_HANDLE, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned),
    ):
        raise ResourceLimitUnavailable(
            f"QueryInformationJobObject failed with error {ctypes.get_last_error()}"
        )
    if not info.BasicLimitInformation.LimitFlags & _JOB_OBJECT_LIMIT_PROCESS_MEMORY:
        raise ResourceLimitUnavailable("the job object carries no process-memory limit")
    return int(info.ProcessMemoryLimit)


def _read_posix_limit() -> int:
    import resource

    soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY:
        raise ResourceLimitUnavailable("RLIMIT_AS is unlimited")
    return int(soft)


def read_applied_limit() -> int:
    """The cap currently in force on this process, read back from the kernel.

    The point is that this is *not* the number the caller asked for. A reported
    bound that is only the request echoed back cannot detect a mechanism that
    silently applied something else, or nothing -- so the worker reports this
    value and the parent checks it against what it requested.
    """
    if _WINDOWS:
        if _JOB_HANDLE is None:
            raise ResourceLimitUnavailable("no job object has been created in this process")
        return _read_windows_limit()
    return _read_posix_limit()


def apply_address_space_limit(limit_bytes: int) -> str:
    """Cap this process's memory at ``limit_bytes``; return the mechanism used.

    Raises :class:`ResourceLimitUnavailable` when no cap could be applied,
    :class:`TypeError` for something that is not a byte count, and
    :class:`ValueError` for a limit that is not positive and finite.
    """
    if isinstance(limit_bytes, bool) or not isinstance(limit_bytes, (int, float)):
        raise TypeError("an address-space limit must be a number of bytes")
    if not math.isfinite(limit_bytes) or limit_bytes <= 0:
        raise ValueError("an address-space limit must be finite and positive")
    return _apply_platform_limit(int(limit_bytes))


__all__ = ["ResourceLimitUnavailable", "apply_address_space_limit", "read_applied_limit"]
