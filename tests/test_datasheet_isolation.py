"""Regressions for CS-AUDIT-006: bounded, isolated PDF observation extraction.

The audit's required correction had three parts. Preflight budgets and explicit
token rejection were closed in the first remediation pass; this module covers
the part that was left open as CS-AUDIT-006-RESIDUAL -- running the parse in an
isolated worker with a wall-clock and address-space bound.

The point of the worker is not that it makes parsing safe. It is that a parse
which exceeds its bounds becomes a *rejection the parent observes*, rather than
an allocation the parent is already inside of. So every test here asserts a
refusal, and the two that matter most assert that a worker which fails, dies, or
returns nothing is never read as an empty-but-successful observation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import tracemalloc
from pathlib import Path
from unittest.mock import patch

import pytest

from ohmni.adapters.resource_limits import (
    ResourceLimitUnavailable,
    apply_address_space_limit,
)
from ohmni.datasheet.isolated_observations import (
    IsolatedObservationExtractor,
    ObservationTimeoutError,
    ObservationWorkerError,
    WorkerBounds,
)
from ohmni.datasheet.observations import ObservationLimitError
from ohmni.datasheet.pdf import (
    BoundedObservationExtractor,
    PdfIngestError,
    PdfIngestStatus,
)


def _simple_pdf(path: Path, *, width: float = 612, height: float = 792) -> Path:
    import pymupdf

    document = pymupdf.open()
    page = document.new_page(width=width, height=height)
    page.insert_text((72, 144), "Contact Pad Width 0.60", fontsize=11)
    page.draw_line((72, 160), (400, 160))
    document.save(path)
    document.close()
    return path


def _huge_page_pdf(path: Path) -> Path:
    import pymupdf

    document = pymupdf.open()
    document.new_page(width=14000, height=14000).insert_text((20, 20), "x")
    document.save(path)
    document.close()
    return path


class TestAddressSpaceLimit:
    """The cap is only a cap if an over-limit allocation actually fails."""

    def test_the_cap_bounds_an_allocation_in_a_real_child(self, tmp_path: Path):
        program = textwrap.dedent(
            """
            import sys
            sys.path.insert(0, %r)
            from ohmni.adapters.resource_limits import apply_address_space_limit
            apply_address_space_limit(256 * 1024 * 1024)
            try:
                blob = bytearray(2 * 1024 * 1024 * 1024)
            except (MemoryError, OSError):
                sys.exit(42)
            sys.exit(0)
            """
        ) % str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True, text=True, timeout=120, check=False,
        )
        # 42 is the child's signal that the allocation was *refused*. Asserting
        # only "nonzero" would also pass when no cap was applied at all and the
        # child died reporting ResourceLimitUnavailable -- the opposite result.
        assert result.returncode == 42, (
            "expected the 2 GiB allocation to be refused under a 256 MiB cap (exit 42); "
            f"got exit {result.returncode}.\n"
            f"stdout={result.stdout!r} stderr={result.stderr[-2000:]!r}"
        )

    def test_the_applied_limit_is_read_from_the_kernel_not_remembered(self):
        """Change the cap behind the library's back; the read-back must follow.

        Asserting that ``read_applied_limit()`` equals the value just requested
        proves nothing -- an implementation that simply returned its argument
        would satisfy it. So the child sets a cap, then rewrites the kernel's
        limit directly, and requires the reported value to track the kernel
        rather than the request.
        """
        if os.name != "nt":
            pytest.skip("the direct job-object mutation below is Windows-specific")
        program = textwrap.dedent(
            """
            import ctypes, sys
            sys.path.insert(0, %r)
            from ohmni.adapters import resource_limits as rl

            rl.apply_address_space_limit(512 * 1024 * 1024)
            if rl.read_applied_limit() != 512 * 1024 * 1024:
                sys.exit(10)

            info = rl._ExtendedLimitInformation()
            info.BasicLimitInformation.LimitFlags = rl._JOB_OBJECT_LIMIT_PROCESS_MEMORY
            info.ProcessMemoryLimit = ctypes.c_size_t(123 * 1024 * 1024).value
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.SetInformationJobObject.argtypes = [
                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32
            ]
            if not kernel.SetInformationJobObject(
                rl._JOB_HANDLE, rl._JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(info), ctypes.sizeof(info),
            ):
                sys.exit(11)

            sys.exit(42 if rl.read_applied_limit() == 123 * 1024 * 1024 else 12)
            """
        ) % str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True, text=True, timeout=120, check=False,
        )
        assert result.returncode == 42, (
            "read_applied_limit did not track the kernel after the job limit changed "
            f"(exit {result.returncode}); a reported bound that only echoes the request "
            f"cannot witness anything. stderr={result.stderr[-2000:]!r}"
        )

    def test_an_unavailable_mechanism_is_an_error_not_a_silent_pass(self):
        """Fail closed. A cap that could not be applied must not read as applied."""
        with patch(
            "ohmni.adapters.resource_limits._apply_platform_limit",
            side_effect=ResourceLimitUnavailable("no mechanism on this platform"),
        ), pytest.raises(ResourceLimitUnavailable):
            apply_address_space_limit(256 * 1024 * 1024)

    def test_a_nonsense_limit_is_refused(self):
        for bad in (0, -1, float("inf")):
            with pytest.raises(ValueError):
                apply_address_space_limit(bad)


class TestIsolatedWorkerEquivalence:
    def test_the_worker_observes_what_the_in_process_extractor_observes(self, tmp_path: Path):
        path = _simple_pdf(tmp_path / "simple.pdf")
        direct_bundle, direct_images = BoundedObservationExtractor().observe(
            path, [1], render=True
        )
        worker_bundle, worker_images = IsolatedObservationExtractor().observe(
            path, [1], render=True
        )
        assert worker_bundle.observation_digest == direct_bundle.observation_digest
        assert worker_images.keys() == direct_images.keys()
        assert worker_images[1] == direct_images[1]

    def test_the_worker_reports_the_bound_the_kernel_actually_holds(self, tmp_path: Path):
        """The worker names a mechanism and a cap, and the parent checks it.

        This pins the plumbing only. It does NOT by itself prove the value came
        from the kernel: on Windows the read-back equals the request, so an
        implementation that echoed the request would satisfy it too. That
        property is pinned separately by
        ``test_the_applied_limit_is_read_from_the_kernel_not_remembered``.
        """
        path = _simple_pdf(tmp_path / "simple.pdf")
        bounds = WorkerBounds(address_space_bytes=512 * 1024 * 1024)
        extractor = IsolatedObservationExtractor(bounds=bounds)
        extractor.observe(path, [1])
        assert extractor.last_run is not None
        assert extractor.last_run.memory_mechanism in {
            "windows-job-object:process-memory", "posix-rlimit:address-space",
        }
        assert extractor.last_run.address_space_bytes == bounds.address_space_bytes

    def test_a_cap_looser_than_requested_is_refused(self, tmp_path: Path):
        """If the mechanism quietly applied more than we asked for, that is a failure."""
        path = _simple_pdf(tmp_path / "simple.pdf")
        extractor = IsolatedObservationExtractor()
        real = IsolatedObservationExtractor._read_result

        def loosened(self, completed, workspace, expected_digest, requested_pages, **kw):
            payload_path = workspace / "out" / "bundle.json"
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            payload["address_space_bytes"] = self.bounds.address_space_bytes * 1000
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            return real(self, completed, workspace, expected_digest, requested_pages, **kw)

        with (
            patch.object(IsolatedObservationExtractor, "_read_result", loosened),
            pytest.raises(ObservationWorkerError, match="looser"),
        ):
            extractor.observe(path, [1])


class TestIsolatedWorkerRefusals:
    """A worker that fails, dies, or returns nothing is never a pass."""

    def test_a_wall_clock_overrun_is_a_timeout_not_a_result(self, tmp_path: Path):
        path = _simple_pdf(tmp_path / "simple.pdf")
        extractor = IsolatedObservationExtractor(
            bounds=WorkerBounds(timeout_seconds=0.001)
        )
        with pytest.raises(ObservationTimeoutError):
            extractor.observe(path, [1])

    def test_a_worker_that_dies_is_rejected(self, tmp_path: Path):
        path = _simple_pdf(tmp_path / "simple.pdf")
        crashed = subprocess.CompletedProcess([], 0xC0000005 - (1 << 32), "", "")
        with patch(
            "ohmni.datasheet.isolated_observations.run_tool", return_value=crashed
        ), pytest.raises(ObservationWorkerError):
            IsolatedObservationExtractor().observe(path, [1])

    def test_a_worker_that_exits_zero_without_a_bundle_is_rejected(self, tmp_path: Path):
        """The audit's CS-AUDIT-004 shape, applied to this worker."""
        path = _simple_pdf(tmp_path / "simple.pdf")
        silent = subprocess.CompletedProcess([], 0, "", "")
        with patch(
            "ohmni.datasheet.isolated_observations.run_tool", return_value=silent
        ), pytest.raises(ObservationWorkerError):
            IsolatedObservationExtractor().observe(path, [1])

    def test_a_bundle_for_a_different_document_is_rejected(self, tmp_path: Path):
        """The parent hashes the bytes itself; the child cannot substitute a source."""
        path = _simple_pdf(tmp_path / "simple.pdf")
        other = _simple_pdf(tmp_path / "other.pdf", width=400, height=500)
        real_run = IsolatedObservationExtractor()._run_worker

        def swapped(request, workspace):
            request = {**request, "path": str(other)}
            return real_run(request, workspace)

        extractor = IsolatedObservationExtractor()
        with patch.object(
            IsolatedObservationExtractor, "_run_worker", side_effect=swapped, autospec=False
        ), pytest.raises(ObservationWorkerError, match="document"):
            extractor.observe(path, [1])

    def test_an_oversized_page_is_refused_by_the_worker(self, tmp_path: Path):
        path = _huge_page_pdf(tmp_path / "huge.pdf")
        with pytest.raises(ObservationLimitError):
            IsolatedObservationExtractor().observe(path, [1], render=True)

    def test_an_invalid_pdf_keeps_its_ingest_status_across_the_boundary(self, tmp_path: Path):
        path = tmp_path / "broken.pdf"
        path.write_bytes(b"this is not a pdf")
        with pytest.raises(PdfIngestError) as raised:
            IsolatedObservationExtractor().observe(path, [1])
        # _ingest_status falls back to PARSER_ERROR whenever it cannot read the
        # child's reason, so every status could collapse to that and a bare
        # `raises(PdfIngestError)` would not notice.
        assert raised.value.status is PdfIngestStatus.INVALID_PDF

    def test_a_worker_that_cannot_bound_itself_refuses_to_parse(self, tmp_path: Path):
        """Fail closed at the far end too, not only in the parent.

        The match matters: on POSIX a tiny RLIMIT_AS is *accepted* and the child
        then dies of starvation during import, which reaches the parent through
        the generic nonzero-exit branch instead. The worker's explicit floor
        makes this one path on every platform.
        """
        path = _simple_pdf(tmp_path / "simple.pdf")
        extractor = IsolatedObservationExtractor(
            bounds=WorkerBounds(address_space_bytes=1024)
        )
        # Match the floor's own reason, not the generic EXIT_UNBOUNDED wrapper:
        # on Windows SetInformationJobObject rejects 1024 bytes outright and
        # produces the same wrapper, so the loose match passed even with the
        # floor deleted.
        with pytest.raises(ObservationWorkerError, match=r"below the \d+ byte floor"):
            extractor.observe(path, [1])


class TestParentSideChecks:
    """The parent verifies what comes back; it does not take the child's word."""

    def test_the_parent_never_reads_an_oversize_file_into_itself(self, tmp_path: Path):
        """The hostile input must not be materialised in the protected process.

        Isolation that begins after the parent has already allocated the whole
        document is the exact thing this worker exists to avoid.
        """
        big = tmp_path / "big.pdf"
        with big.open("wb") as handle:
            handle.write(b"%PDF-1.4\n")
            for _ in range(80):
                handle.write(b"\0" * (1024 * 1024))
        extractor = IsolatedObservationExtractor(max_bytes=8 * 1024 * 1024)
        tracemalloc.start()
        try:
            with pytest.raises(PdfIngestError) as raised:
                extractor.observe(big, [1])
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        assert raised.value.status is PdfIngestStatus.TOO_LARGE
        assert peak < 8 * 1024 * 1024, (
            f"the parent allocated {peak // (1024 * 1024)} MiB refusing an 80 MiB file; "
            "it must decide from the directory entry, before reading"
        )

    def test_a_tampered_page_image_is_rejected(self, tmp_path: Path):
        """The bundle records each render's digest, so the pixels are checkable."""
        path = _simple_pdf(tmp_path / "simple.pdf")
        extractor = IsolatedObservationExtractor()
        real = IsolatedObservationExtractor._read_result

        def tampered(self, completed, workspace, expected_digest, requested_pages, **kw):
            image = workspace / "out" / "page1.png"
            image.write_bytes(image.read_bytes() + b"tampered")
            return real(self, completed, workspace, expected_digest, requested_pages, **kw)

        with patch.object(IsolatedObservationExtractor, "_read_result", tampered), \
                pytest.raises(ObservationWorkerError, match="hashes"):
            extractor.observe(path, [1], render=True)

    def test_a_bundle_missing_a_requested_page_is_rejected(self, tmp_path: Path):
        path = _simple_pdf(tmp_path / "simple.pdf")
        extractor = IsolatedObservationExtractor()
        real = IsolatedObservationExtractor._read_result

        def narrowed(self, completed, workspace, expected_digest, requested_pages, **kw):
            return real(self, completed, workspace, expected_digest, {1, 7}, **kw)

        with patch.object(IsolatedObservationExtractor, "_read_result", narrowed), \
                pytest.raises(ObservationWorkerError, match="requested"):
            extractor.observe(path, [1])

    def test_the_child_can_import_the_package_the_parent_imported(self):
        """`-m` would resolve through the child's own sys.path, not the parent's.

        A script that inserts `src/` at runtime must still be able to spawn a
        worker that can import its own package, so the bootstrap carries the
        parent's path over rather than relying on an installed distribution.
        Run with -S, an emptied PYTHONPATH and an unrelated cwd. Emptying
        PYTHONPATH alone is not enough: an editable install answers the import
        through a .pth in site-packages, which would mask a gutted bootstrap.
        -S is what removes that, so this test can actually fail.
        """
        from ohmni.datasheet.isolated_observations import _bootstrap

        environment = {**os.environ, "PYTHONPATH": ""}
        result = subprocess.run(
            # -S skips the site module, so the editable-install .pth is NOT
            # processed and `import ohmni` can only succeed via the path this
            # bootstrap hands over. Without it an installed copy answers the
            # import and the test passes even when the bootstrap is gutted.
            [sys.executable, "-S", "-c", _bootstrap()],
            capture_output=True, text=True, timeout=120, check=False,
            cwd=tempfile.gettempdir(), env=environment,
        )
        # No arguments, so the worker prints its usage and exits EXIT_FAILED.
        # Reaching that proves the import succeeded, which is what is at stake.
        assert "usage: observation_worker" in result.stderr, (
            f"the child could not import the worker: {result.stderr[-2000:]!r}"
        )

    def test_requested_renders_that_do_not_arrive_are_rejected(self):
        """An empty render set is not a successful observation.

        The bundle's declared renders and the payload's reported renders both
        come from the child, so their agreeing with each other witnesses nothing
        about what the caller asked for. Only the caller's own `render` flag can.
        """
        import tempfile as _tempfile

        directory = Path(_tempfile.mkdtemp())
        path = _simple_pdf(directory / "simple.pdf")
        extractor = IsolatedObservationExtractor()
        real = IsolatedObservationExtractor._run_worker

        def unrendered(self, request, workspace):
            return real(self, {**request, "render": False}, workspace)

        with (
            patch.object(IsolatedObservationExtractor, "_run_worker", unrendered),
            pytest.raises(ObservationWorkerError, match="renders were requested"),
        ):
            extractor.observe(path, [1], render=True)

    def test_a_bundle_missing_the_worker_metadata_is_an_observation_error(self):
        """Not a bare KeyError: callers must not have to catch two families."""
        import tempfile as _tempfile

        directory = Path(_tempfile.mkdtemp())
        path = _simple_pdf(directory / "simple.pdf")
        extractor = IsolatedObservationExtractor()
        real = IsolatedObservationExtractor._read_result

        def stripped(self, completed, workspace, expected_digest, requested_pages, **kw):
            payload_path = workspace / "out" / "bundle.json"
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            del payload["memory_mechanism"]
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            return real(self, completed, workspace, expected_digest, requested_pages, **kw)

        with (
            patch.object(IsolatedObservationExtractor, "_read_result", stripped),
            pytest.raises(ObservationWorkerError, match="unusable bundle"),
        ):
            extractor.observe(path, [1])
