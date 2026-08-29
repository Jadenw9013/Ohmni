"""Typed contracts for compiled schematics and KiCad ERC."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ..adapters import ToolStatus
from ..domain import CircuitIR, EngineeringEvent, Evidence, VerificationReport


class ArtifactFingerprint(BaseModel):
    algorithm: str = "sha256"
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PinBinding(BaseModel):
    component_ref: str
    circuit_pin: str
    kicad_pin: str
    pin_uuid: str


class SymbolBinding(BaseModel):
    component_ref: str
    part_id: str
    library_id: str
    symbol_uuid: str
    pins: list[PinBinding]


class CompilationWarning(BaseModel):
    code: str
    message: str
    component_ref: str | None = None


class CompilationReport(BaseModel):
    circuit_content_hash: str
    compiler_version: str
    target: str
    symbol_bindings: list[SymbolBinding]
    net_mapping: dict[str, str]
    warnings: list[CompilationWarning] = Field(default_factory=list)


class SchematicArtifact(BaseModel):
    path: Path
    fingerprint: ArtifactFingerprint
    circuit_content_hash: str
    compiler_version: str
    target_eda: str
    compilation: CompilationReport
    events: list[EngineeringEvent] = Field(default_factory=list)

    def current_fingerprint(self) -> ArtifactFingerprint:
        import hashlib
        return ArtifactFingerprint(digest=hashlib.sha256(self.path.read_bytes()).hexdigest())

    @property
    def is_current(self) -> bool:
        return self.path.is_file() and self.current_fingerprint().digest == self.fingerprint.digest


@runtime_checkable
class SchematicCompiler(Protocol):
    def compile(self, circuit: CircuitIR, destination: Path) -> SchematicArtifact: ...


class ErcStatus(StrEnum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    STALE_ARTIFACT = "stale_artifact"


class ErcItem(BaseModel):
    description: str
    uuid: str | None = None
    x: float | None = None
    y: float | None = None


class ErcFinding(BaseModel):
    type: str
    severity: str
    description: str
    excluded: bool = False
    sheet_path: str = "/"
    items: list[ErcItem] = Field(default_factory=list)
    raw: dict[str, object] = Field(default_factory=dict)


class ErcReport(BaseModel):
    status: ErcStatus
    tool_status: ToolStatus
    run_id: str
    kicad_version: str | None = None
    artifact_fingerprint: ArtifactFingerprint
    report_path: Path | None = None
    command: list[str] = Field(default_factory=list)
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    findings: list[ErcFinding] = Field(default_factory=list)
    ignored_checks: list[dict[str, object]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "A zero-violation ERC result establishes only that this exact generated schematic passed the configured KiCad electrical checks.",
        "ERC does not establish functional or datasheet correctness, simulation behavior, PCB layout, manufacturability, firmware behavior, or hardware performance.",
    ])
    evidence: list[Evidence] = Field(default_factory=list)
    events: list[EngineeringEvent] = Field(default_factory=list)


class EdaVerificationBundle(BaseModel):
    semantic: VerificationReport
    aggregated: VerificationReport
    artifact: SchematicArtifact
    erc: ErcReport
