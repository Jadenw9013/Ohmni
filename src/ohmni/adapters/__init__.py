"""Interfaces to everything outside this application.

Every external system -- language models, PDF extraction, part data, KiCad,
ngspice, routing -- sits behind a Protocol defined here. Business logic depends
on these Protocols and never on a vendor SDK, so the whole system is testable
with fakes and no vendor is load-bearing.

Two of these tools are known to be absent or partial on the development machine
(KiCad was installed during review; ngspice ships only as a shared library). The
Protocols therefore model *unavailability as a normal result*, not an exception:
:class:`ToolStatus` lets an adapter say UNAVAILABLE and let the report record
`SubsystemStatus.UNSUPPORTED` honestly, rather than a caller inventing a pass.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, Field

from ..domain.circuit import CircuitIR
from ..domain.component import ComponentSpec
from ..domain.document import DatasheetDocument
from ..domain.evidence import Evidence
from ..domain.units import Quantity
from ..domain.verification import VerificationFinding


class ToolStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class ToolAvailability(BaseModel):
    """Whether an external tool can be used, and what was found."""

    name: str
    status: ToolStatus
    version: str | None = None
    executable: str | None = None
    detail: str | None = None

    @property
    def usable(self) -> bool:
        return self.status is ToolStatus.OK


class PartNotFoundError(LookupError):
    """Raised when a circuit references a part the catalog does not know.

    Deliberately an error rather than a silently-empty spec: a verifier that
    silently skips an unknown part reports a pass it did not earn.
    """


@runtime_checkable
class PartCatalog(Protocol):
    """Source of component facts."""

    def get(self, part_id: str) -> ComponentSpec | None: ...

    def require(self, part_id: str) -> ComponentSpec: ...

    def all_parts(self) -> list[ComponentSpec]: ...


@runtime_checkable
class DatasheetExtractor(Protocol):
    """Turns a PDF into page-addressable text.

    Implementations must treat document content strictly as data. Nothing read
    from a document may reach a model in an instruction position, and no text
    found in a document may be executed, fetched or shell-interpolated
    (SECURITY.md).
    """

    def load(self, path: Path) -> DatasheetDocument: ...


TStructured = TypeVar("TStructured", bound=BaseModel)


class StructuredGenerationRequest(BaseModel):
    request_type: str
    instructions: str
    data: dict[str, object] = Field(default_factory=dict)


@runtime_checkable
class LlmProvider(Protocol):
    """A schema-constrained structured-output interface.

    There is deliberately no free-text completion method. Every call names the
    Pydantic model it must return, so unvalidated prose can never reach verified
    project state. Vendor choice stays behind this Protocol.
    """

    def complete_structured(
        self,
        *,
        instructions: str,
        data: str,
        schema: type[BaseModel],
        max_tokens: int = 4096,
    ) -> BaseModel: ...

    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[TStructured]
    ) -> TStructured: ...


class ErcRun(BaseModel):
    """Result of an external electrical-rules check."""

    status: ToolStatus
    run_id: str
    findings: list[VerificationFinding] = Field(default_factory=list)
    raw_output_path: str | None = None
    tool_version: str | None = None
    detail: str | None = None


@runtime_checkable
class KicadTool(Protocol):
    """KiCad project emission and ERC/DRC.

    Corroboration, not the primary source of truth. The deterministic verifier
    must stand on its own if this returns UNAVAILABLE.
    """

    def availability(self) -> ToolAvailability: ...

    def emit_project(self, circuit: CircuitIR, catalog: PartCatalog, out_dir: Path) -> Path: ...

    def run_erc(self, schematic_path: Path) -> ErcRun: ...


class OperatingPoint(BaseModel):
    """A single DC solution: node voltages and branch currents."""

    node_voltages: dict[str, Quantity] = Field(default_factory=dict)
    branch_currents: dict[str, Quantity] = Field(default_factory=dict)


class SimulationRun(BaseModel):
    """Result of a SPICE run.

    ``model_fidelity`` is required and blunt on purpose. A behavioural stand-in
    for a regulator must never be presented as if a vendor model had been used
    (PRE_IMPLEMENTATION_REVIEW.md 6.2).
    """

    status: ToolStatus
    run_id: str
    analysis: str
    model_fidelity: str = Field(
        description="'vendor_model', 'behavioural_approximation', or 'ideal_components'."
    )
    operating_point: OperatingPoint | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    netlist_path: str | None = None
    detail: str | None = None


@runtime_checkable
class SpiceTool(Protocol):
    """SPICE simulation of a subsystem, never of a whole board."""

    def availability(self) -> ToolAvailability: ...

    def operating_point(self, netlist: str, run_id: str) -> SimulationRun: ...


@runtime_checkable
class Router(Protocol):
    """Autorouting. Out of MVP scope; the interface exists so nothing couples to it."""

    def availability(self) -> ToolAvailability: ...

    def route(self, board_path: Path, out_dir: Path) -> ToolAvailability: ...


__all__ = [
    "DatasheetDocument",
    "DatasheetExtractor",
    "ErcRun",
    "KicadTool",
    "LlmProvider",
    "OperatingPoint",
    "PartCatalog",
    "PartNotFoundError",
    "Router",
    "SimulationRun",
    "SpiceTool",
    "StructuredGenerationRequest",
    "ToolAvailability",
    "ToolStatus",
]
