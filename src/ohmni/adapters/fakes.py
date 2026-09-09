"""Fakes for every external system.

These exist so the application can be exercised end to end with nothing
installed. Two rules they all follow:

* A fake never invents a result. :class:`UnavailableKicad` and
  :class:`UnavailableSpice` report ``UNAVAILABLE``, which the report renders as
  ``UNSUPPORTED``. They do not return an empty finding list, because an empty
  finding list is indistinguishable from a clean ERC run and would be a
  fabricated pass.
* :class:`RecordingLlmProvider` returns only what a test queued for it, and
  validates that against the requested schema. There is no free-text path.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ..domain.circuit import CircuitIR
from ..domain.component import ComponentSpec
from ..domain.document import (
    DatasheetDocument,
    DatasheetIdentity,
    DocumentFingerprint,
    DocumentMetadata,
    DocumentPage,
    DocumentSpan,
)
from ..domain.evidence import DocumentRef
from . import (
    ErcRun,
    PartCatalog,
    PartNotFoundError,
    SimulationRun,
    StructuredGenerationRequest,
    ToolAvailability,
    ToolStatus,
)


class InMemoryPartCatalog:
    """A catalog built from ComponentSpec objects, for tests and fixtures."""

    def __init__(self, parts: list[ComponentSpec] | None = None) -> None:
        self._parts: dict[str, ComponentSpec] = {p.part_id: p for p in (parts or [])}

    def add(self, spec: ComponentSpec) -> None:
        self._parts[spec.part_id] = spec

    def get(self, part_id: str) -> ComponentSpec | None:
        return self._parts.get(part_id)

    def require(self, part_id: str) -> ComponentSpec:
        spec = self._parts.get(part_id)
        if spec is None:
            raise PartNotFoundError(f"part {part_id!r} is not in the catalog")
        return spec

    def all_parts(self) -> list[ComponentSpec]:
        return [self._parts[k] for k in sorted(self._parts)]


class StaticDatasheetExtractor:
    """Serves pre-loaded page text, keyed by file name.

    Used to exercise the citation-verification path without a PDF parser: a
    snippet either occurs in the page text this fake holds, or it does not.
    """

    def __init__(self, documents: dict[str, DatasheetDocument] | None = None) -> None:
        self._documents = documents or {}

    def add(self, name: str, ref: DocumentRef, pages: dict[int, str]) -> DatasheetDocument:
        import hashlib
        digest = hashlib.sha256("\n".join(pages.values()).encode()).hexdigest()
        doc = DatasheetDocument(
            metadata=DocumentMetadata(
                document_id=ref.document_id,
                fingerprint=DocumentFingerprint(digest=digest),
                title=ref.title,
                page_count=len(pages),
                identity=DatasheetIdentity(
                    manufacturer=ref.manufacturer,
                    detected_parts=[ref.part_number] if ref.part_number else [],
                    revision=ref.revision,
                ),
            ),
            pages=[DocumentPage(
                number=n, text=t,
                spans=[DocumentSpan(start=0, end=len(t), text=t)] if t else [],
            ) for n, t in sorted(pages.items())],
        )
        self._documents[name] = doc
        return doc

    def load(self, path: Path) -> DatasheetDocument:
        doc = self._documents.get(path.name)
        if doc is None:
            raise FileNotFoundError(f"no fake document registered for {path.name}")
        return doc


class QueuedResponse(BaseModel):
    """One queued structured response for the fake model provider."""

    payload: dict[str, object]


class RecordingLlmProvider:
    """Returns queued structured responses and records every call.

    Deliberately has no free-text method: the real Protocol does not either, so
    a test cannot exercise a path the production interface forbids.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self._queue: list[dict[str, object]] = []

    def queue(self, payload: dict[str, object]) -> None:
        self._queue.append(payload)

    def complete_structured(
        self,
        *,
        instructions: str,
        data: str,
        schema: type[BaseModel],
        max_tokens: int = 4096,
    ) -> BaseModel:
        self.calls.append(
            {
                "instructions": instructions,
                "data": data,
                "schema": schema.__name__,
                "max_tokens": max_tokens,
            }
        )
        if not self._queue:
            raise AssertionError(
                f"RecordingLlmProvider had no queued response for {schema.__name__}"
            )
        # Validating here is the point: a model's output reaches project state
        # only if it satisfies the schema, in the fake exactly as in production.
        return schema.model_validate(self._queue.pop(0))

    def generate_structured(self, request: StructuredGenerationRequest, response_model):
        self.calls.append({
            "request_type": request.request_type,
            "instructions": request.instructions,
            "data": request.data,
            "schema": response_model.__name__,
        })
        if not self._queue:
            raise AssertionError(f"RecordingLlmProvider had no queued response for {response_model.__name__}")
        return response_model.model_validate(self._queue.pop(0))


class UnavailableKicad:
    """Stands in for KiCad when it is not installed.

    Returns UNAVAILABLE rather than an empty pass. The difference matters: an
    ERC run with no violations and an ERC run that never happened must never
    look the same to a caller.
    """

    name = "kicad-cli"

    def availability(self) -> ToolAvailability:
        return ToolAvailability(
            name=self.name,
            status=ToolStatus.UNAVAILABLE,
            detail="KiCad CLI not configured for this environment.",
        )

    def emit_project(self, circuit: CircuitIR, catalog: PartCatalog, out_dir: Path) -> Path:
        raise RuntimeError("KiCad is unavailable; no project was emitted")

    def run_erc(self, schematic_path: Path) -> ErcRun:
        return ErcRun(
            status=ToolStatus.UNAVAILABLE,
            run_id="erc-unavailable",
            findings=[],
            detail=(
                "KiCad is unavailable, so ERC did not run. This is not a pass: the EDA "
                "subsystem stays UNSUPPORTED."
            ),
        )


class UnavailableSpice:
    """Stands in for ngspice when it is not installed."""

    name = "ngspice"

    def availability(self) -> ToolAvailability:
        return ToolAvailability(
            name=self.name,
            status=ToolStatus.UNAVAILABLE,
            detail=(
                "ngspice is not installed. KiCad ships it as a shared library rather than a "
                "CLI on this platform; see spike S2."
            ),
        )

    def operating_point(self, netlist: str, run_id: str) -> SimulationRun:
        return SimulationRun(
            status=ToolStatus.UNAVAILABLE,
            run_id=run_id,
            analysis="op",
            model_fidelity="ideal_components",
            detail=(
                "ngspice is unavailable, so no operating point was computed. No simulated "
                "evidence is produced, and the simulation subsystem stays UNSUPPORTED."
            ),
        )


class UnavailableRouter:
    """Routing is out of MVP scope; the interface exists so nothing couples to it."""

    name = "freerouting"

    def availability(self) -> ToolAvailability:
        return ToolAvailability(
            name=self.name,
            status=ToolStatus.UNAVAILABLE,
            detail="Autorouting is out of MVP scope.",
        )

    def route(self, board_path: Path, out_dir: Path) -> ToolAvailability:
        return self.availability()


__all__ = [
    "InMemoryPartCatalog",
    "QueuedResponse",
    "RecordingLlmProvider",
    "StaticDatasheetExtractor",
    "UnavailableKicad",
    "UnavailableRouter",
    "UnavailableSpice",
]
