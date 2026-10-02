"""The parent half of bounded PDF observation: run the parse somewhere else.

:class:`IsolatedObservationExtractor` has the same ``observe`` signature as
:class:`~ohmni.datasheet.pdf.BoundedObservationExtractor` and raises the same
exceptions, so it is a drop-in for the in-process path. The difference is where
the parse happens: in a child with a wall-clock bound owned here and an
address-space bound the child applies to itself before reading anything.

Three refusals are deliberate and each corresponds to a way the first
remediation pass could have gone wrong:

* A child that exits zero without writing a bundle is a failure, not an empty
  observation. This is CS-AUDIT-004's shape -- "the tool exited zero" is not
  "the tool produced what was asked for" -- applied to this boundary.
* A bundle whose ``document_digest`` is not the digest *this* process computed
  from *these* bytes is rejected, and every returned image is checked against
  the digest the validated bundle records. The parent does not take the child's
  word for which path was read. Note what this is not: the digest is computed
  inside the child, so a *compromised* worker could report the expected value
  for a bundle describing anything. This defends against the wrong file, not
  against a subverted parser.
* A timeout, a crash, or an unparseable result is an exception. There is no code
  path here that degrades a bounded-run failure into a successful empty result.

The child is started through :func:`ohmni.adapters.process.run_tool`, the same
bounded runner the KiCad and ngspice paths use, so this module does not invent
its own process call.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..adapters.process import ToolProcessError, ToolTimeoutError, run_tool
from .observation_worker import (
    EXIT_OK,
    EXIT_REJECTED,
    EXIT_UNBOUNDED,
)
from .observations import DocumentObservationBundle, ObservationLimitError
from .pdf import DEFAULT_RENDER_DPI, PdfIngestError, PdfIngestStatus

WORKER_MODULE = "ohmni.datasheet.observation_worker"


def _bootstrap() -> str:
    """The child's entry program: adopt the parent's import path, then run.

    ``python -m`` would resolve the worker through the *child's* ``sys.path``,
    which does not inherit a parent that inserted a source directory at runtime.
    That works only when ``ohmni`` happens to be installed, so a script run from
    an uninstalled checkout would spawn a child that cannot import its own
    package. Handing the parent's ``sys.path`` over explicitly removes the
    dependency on how this process was started. The argument vector stays fixed
    and no shell is involved.
    """
    return (
        "import sys, json;"
        f"sys.path[:0] = json.loads({json.dumps(json.dumps(sys.path))});"
        f"from {WORKER_MODULE} import main;"
        "sys.exit(main())"
    )


class ObservationWorkerError(RuntimeError):
    """The bounded worker did not produce a usable observation. Never a pass."""


class ObservationTimeoutError(ObservationWorkerError):
    """The worker exceeded its wall-clock bound and was terminated."""


@dataclass(frozen=True)
class WorkerBounds:
    """What one isolated parse is allowed to consume.

    The defaults are generous for a datasheet and small for a machine: a real
    500-page manufacturer PDF observes well inside both, while a document built
    to exhaust memory meets a wall the parent survives.
    """

    timeout_seconds: float = 120.0
    address_space_bytes: int = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class WorkerRun:
    """What the last run actually did, including the bound it applied.

    ``memory_mechanism`` comes from the child. A run that could not name one
    never reaches here, because the worker refuses to parse unbounded.
    """

    memory_mechanism: str
    address_space_bytes: int
    timeout_seconds: float
    exit_code: int


class IsolatedObservationExtractor:
    """Observes a PDF in a bounded child process."""

    def __init__(
        self,
        *,
        bounds: WorkerBounds | None = None,
        max_bytes: int = 64 * 1024 * 1024,
        render_dpi: int = DEFAULT_RENDER_DPI,
        python_executable: str | None = None,
    ) -> None:
        self.bounds = bounds or WorkerBounds()
        self.max_bytes = max_bytes
        self.render_dpi = render_dpi
        self.python_executable = python_executable or sys.executable
        self.last_run: WorkerRun | None = None

    def observe(
        self, path: Path, pages: list[int], *, render: bool = False
    ) -> tuple[DocumentObservationBundle, dict[int, bytes]]:
        """Observe the named 1-based pages of one PDF in a bounded child.

        Mirrors :meth:`BoundedObservationExtractor.observe`, including its
        exceptions, so callers do not branch on which one they hold.
        """
        path = Path(path)
        expected_digest = self._digest(path)
        request = {
            "path": str(path),
            "pages": sorted(set(pages)),
            "render": bool(render),
            "render_dpi": self.render_dpi,
            "max_bytes": self.max_bytes,
            "address_space_bytes": self.bounds.address_space_bytes,
        }
        workspace = Path(tempfile.mkdtemp(prefix="ohmni-observe-"))
        try:
            completed = self._run_worker(request, workspace)
            return self._read_result(
                completed, workspace, expected_digest, set(request["pages"]),
                render=bool(render),
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _digest(self, path: Path) -> str:
        """Hash the file without materialising it in the parent.

        The parent has to know which document it asked about, but the document
        is the hostile input: reading it whole here would put the unbounded
        allocation back in the process the isolation exists to protect. So the
        size is checked from the directory entry before anything is read, and
        the digest is streamed.
        """
        try:
            size = path.stat().st_size
            if size > self.max_bytes:
                raise PdfIngestError(
                    PdfIngestStatus.TOO_LARGE,
                    f"the file is {size} bytes; the bound is {self.max_bytes}",
                )
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise PdfIngestError(PdfIngestStatus.PARSER_ERROR, str(exc)) from exc
        return digest.hexdigest()

    def _run_worker(self, request: dict, workspace: Path):
        request_path = workspace / "request.json"
        output = workspace / "out"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        command = [
            self.python_executable, "-c", _bootstrap(), str(request_path), str(output),
        ]
        try:
            return run_tool(command, timeout=self.bounds.timeout_seconds)
        except ToolTimeoutError as exc:
            raise ObservationTimeoutError(
                f"the observation worker exceeded its {self.bounds.timeout_seconds:g}s "
                "wall-clock bound and was terminated; no observation was produced"
            ) from exc
        except ToolProcessError as exc:
            raise ObservationWorkerError(
                f"the observation worker could not be started or failed: {exc}"
            ) from exc

    def _read_result(
        self, completed, workspace: Path, expected_digest: str,
        requested_pages: set[int], *, render: bool = False,
    ) -> tuple[DocumentObservationBundle, dict[int, bytes]]:
        output = workspace / "out"
        code = completed.returncode
        if code in (EXIT_REJECTED, EXIT_UNBOUNDED):
            self._raise_worker_refusal(output, code, completed)
        if code != EXIT_OK:
            raise ObservationWorkerError(
                f"the observation worker exited {code}; no observation was produced. "
                f"{_diagnostics(completed)}"
            )
        payload_path = output / "bundle.json"
        if not payload_path.is_file():
            # CS-AUDIT-004's shape: a zero exit is not an artifact.
            raise ObservationWorkerError(
                "the observation worker exited successfully without writing a bundle; "
                f"a zero exit is not an observation. {_diagnostics(completed)}"
            )
        try:
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            bundle = DocumentObservationBundle.model_validate(payload["bundle"])
            applied = int(payload["address_space_bytes"])
            mechanism = str(payload["memory_mechanism"])
        except (OSError, TypeError, ValueError, KeyError) as exc:
            raise ObservationWorkerError(
                f"the observation worker wrote an unusable bundle: {exc}"
            ) from exc
        if bundle.document_digest != expected_digest:
            raise ObservationWorkerError(
                "the observation worker returned a bundle for document "
                f"{bundle.document_digest[:16]}..., but the requested document hashes "
                f"{expected_digest[:16]}.... The parent hashes the bytes itself, so it "
                "does not take the child's word for which path was read."
            )
        observed = {page.number for page in bundle.pages}
        if not observed >= requested_pages:
            raise ObservationWorkerError(
                f"the worker returned pages {sorted(observed)} but {sorted(requested_pages)} "
                "were requested; a partial bundle is not an observation"
            )
        if applied > self.bounds.address_space_bytes:
            raise ObservationWorkerError(
                f"the worker ran under a {applied} byte cap, looser than the "
                f"{self.bounds.address_space_bytes} bytes requested; it was not bounded "
                "as asked"
            )
        images = self._read_images(payload, output, bundle, render=render)
        self.last_run = WorkerRun(
            memory_mechanism=mechanism,
            address_space_bytes=applied,
            timeout_seconds=self.bounds.timeout_seconds,
            exit_code=code,
        )
        return bundle, images

    def _read_images(
        self, payload: dict, output: Path, bundle, *, render: bool
    ) -> dict[int, bytes]:
        """Return the rendered pages, each checked against the validated bundle.

        The bundle records every render's SHA-256, and the bundle has already
        been bound to the requested document. Verifying the bytes against it
        here means the pixels are checked at the isolation boundary rather than
        only by whichever downstream caller happens to look.
        """
        images: dict[int, bytes] = {}
        declared = {page.number for page in bundle.pages if page.render is not None}
        reported = {int(number) for number in payload.get("rendered_pages", [])}
        # `declared` and `reported` both come from the child, so agreeing with each
        # other witnesses nothing about what the caller asked for. Renders that were
        # requested and did not arrive are a failure, not an empty result.
        if render and not reported:
            raise ObservationWorkerError(
                "renders were requested but the worker returned none; an empty render "
                "set is not a successful observation"
            )
        if declared != reported:
            raise ObservationWorkerError(
                f"the bundle declares renders for pages {sorted(declared)} but the worker "
                f"reported images for {sorted(reported)}"
            )
        for number in sorted(reported):
            image_path = output / f"page{number}.png"
            if not image_path.is_file():
                raise ObservationWorkerError(
                    f"the worker reported a render for page {number} but wrote no image"
                )
            png = image_path.read_bytes()
            expected = bundle.page(number).render.image_digest
            actual = hashlib.sha256(png).hexdigest()
            if actual != expected:
                raise ObservationWorkerError(
                    f"the image for page {number} hashes {actual[:16]}..., but the bundle "
                    f"records {expected[:16]}..."
                )
            images[number] = png
        return images

    def _raise_worker_refusal(self, output: Path, code: int, completed) -> None:
        """Re-raise the child's refusal as the exception the caller expects."""
        detail, kind = _read_error(output)
        if code == EXIT_UNBOUNDED:
            raise ObservationWorkerError(
                f"the observation worker refused to parse unbounded: {detail}"
            )
        if kind == "ingest":
            status = _ingest_status(output)
            raise PdfIngestError(status, detail)
        if kind == "limit":
            raise ObservationLimitError(detail)
        raise ObservationWorkerError(
            f"the observation worker rejected the document: {detail} "
            f"{_diagnostics(completed)}"
        )


def _read_error(output: Path) -> tuple[str, str]:
    try:
        payload = json.loads((output / "error.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "the worker reported a refusal without a readable reason", "unknown"
    return str(payload.get("detail", "no detail")), str(payload.get("kind", "unknown"))


def _ingest_status(output: Path) -> PdfIngestStatus:
    try:
        payload = json.loads((output / "error.json").read_text(encoding="utf-8"))
        raw = str(payload.get("status", "")).rsplit(".", 1)[-1]
        for status in PdfIngestStatus:
            if status.value == raw or status.name == raw:
                return status
    except (OSError, ValueError):
        pass
    return PdfIngestStatus.PARSER_ERROR


def _diagnostics(completed) -> str:
    tail = (getattr(completed, "stderr", "") or "").strip().splitlines()
    return f"stderr: {tail[-1]}" if tail else "no diagnostics were captured."


__all__ = [
    "IsolatedObservationExtractor",
    "ObservationTimeoutError",
    "ObservationWorkerError",
    "WorkerBounds",
    "WorkerRun",
]
