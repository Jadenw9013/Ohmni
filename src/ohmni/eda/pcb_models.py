"""Typed PCB artifacts, DRC reports, and lineage."""

from __future__ import annotations

import hashlib
import math
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from ..adapters import ToolStatus
from ..domain import EngineeringEvent, Evidence, Lesson
from ..physical.models import FootprintBinding, PadBinding, PhysicalVerificationReport
from ..routing.models import RoutingVerificationReport
from .models import ArtifactFingerprint, ErcReport, SchematicArtifact


class CompiledTrackGeometry(BaseModel):
    """One exact track segment emitted into a fingerprinted KiCad PCB."""

    source_segment_id: str
    emitted_uuid: str
    net_name: str
    net_number: int = Field(gt=0)
    layer: str
    start_x_mm: float
    start_y_mm: float
    end_x_mm: float
    end_y_mm: float
    width_mm: float = Field(gt=0)

    @property
    def length_mm(self) -> float:
        return math.hypot(self.end_x_mm-self.start_x_mm,self.end_y_mm-self.start_y_mm)


class CompiledViaGeometry(BaseModel):
    """One exact drilled via entity emitted into a fingerprinted KiCad PCB."""

    source_via_id: str
    emitted_uuid: str
    net_name: str
    net_number: int = Field(gt=0)
    x_mm: float
    y_mm: float
    diameter_mm: float = Field(gt=0)
    drill_mm: float = Field(gt=0)
    layers: tuple[str, str] = ("F.Cu", "B.Cu")


class PcbCopperStatistics(BaseModel):
    """Counts for exact emitted copper, distinct from routing-plan intent."""

    modeled_track_segment_count: int = Field(ge=0)
    modeled_layer_transition_count: int = Field(ge=0)
    track_segment_count: int = Field(ge=0)
    via_count: int = Field(ge=0)
    coalesced_layer_transition_count: int = Field(ge=0)
    plated_through_hole_transition_count: int = Field(ge=0)
    total_track_length_mm: float = Field(ge=0)


class PcbCompilationReport(BaseModel):
    circuit_content_hash: str
    artifact_fingerprint: ArtifactFingerprint
    schematic_fingerprint: ArtifactFingerprint
    source_schematic_path: Path
    constraints_hash: str
    footprint_bindings: list[FootprintBinding]
    pad_bindings: list[PadBinding]
    net_mapping: dict[str, int]
    physical_verification: PhysicalVerificationReport
    lessons: list[Lesson] = Field(default_factory=list)
    routing_plan_fingerprint: str | None = None
    routing_verification: RoutingVerificationReport | None = None
    emitted_tracks: list[CompiledTrackGeometry] = Field(default_factory=list)
    emitted_vias: list[CompiledViaGeometry] = Field(default_factory=list)
    copper_statistics: PcbCopperStatistics

    @model_validator(mode="after")
    def _compiled_copper_is_self_consistent(self) -> PcbCompilationReport:
        statistics=self.copper_statistics
        if statistics.track_segment_count != len(self.emitted_tracks):
            raise ValueError("compiled track statistics differ from emitted geometry")
        if statistics.via_count != len(self.emitted_vias):
            raise ValueError("compiled via statistics differ from emitted geometry")
        length=round(sum(track.length_mm for track in self.emitted_tracks),6)
        if not math.isclose(statistics.total_track_length_mm,length,abs_tol=1e-9):
            raise ValueError("compiled track length differs from emitted geometry")
        if statistics.modeled_track_segment_count != statistics.track_segment_count:
            raise ValueError("compiled tracks do not account for routing intent")
        accounted=(statistics.via_count+statistics.coalesced_layer_transition_count+statistics.plated_through_hole_transition_count)
        if statistics.modeled_layer_transition_count != accounted:
            raise ValueError("compiled layer transitions do not account for routing intent")
        return self


class PcbArtifact(BaseModel):
    path: Path
    fingerprint: ArtifactFingerprint
    circuit_content_hash: str
    schematic_fingerprint: ArtifactFingerprint
    source_schematic_path: Path
    constraints_hash: str
    compiler_version: str
    compilation: PcbCompilationReport
    events: list[EngineeringEvent] = Field(default_factory=list)
    source_placed_pcb_fingerprint: ArtifactFingerprint | None = None
    source_placed_pcb_path: Path | None = None
    routing_plan_fingerprint: str | None = None

    def current_fingerprint(self) -> ArtifactFingerprint:
        return ArtifactFingerprint(digest=hashlib.sha256(self.path.read_bytes()).hexdigest())

    @property
    def is_current(self) -> bool:
        return self.path.is_file() and self.current_fingerprint() == self.fingerprint

    @property
    def lineage_is_current(self) -> bool:
        base = (
            self.is_current
            and self.source_schematic_path.is_file()
            and hashlib.sha256(self.source_schematic_path.read_bytes()).hexdigest()
            == self.schematic_fingerprint.digest
        )
        if not base:
            return False
        if self.source_placed_pcb_fingerprint is None:
            return True
        return self.source_placed_pcb_path is not None and self.source_placed_pcb_path.is_file() and hashlib.sha256(self.source_placed_pcb_path.read_bytes()).hexdigest() == self.source_placed_pcb_fingerprint.digest


class DrcStatus(StrEnum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    STALE_ARTIFACT = "stale_artifact"


class DrcFindingClass(StrEnum):
    CLEARANCE = "clearance"
    UNROUTED = "unrouted"
    EDGE = "edge"
    COURTYARD = "courtyard"
    FOOTPRINT = "footprint"
    CONNECTIVITY = "connectivity"
    DRILL = "drill"
    TRACK = "track"
    VIA = "via"
    OTHER = "other"


class DrcItem(BaseModel):
    description: str
    uuid: str | None = None
    x: float | None = None
    y: float | None = None


class DrcFinding(BaseModel):
    type: str
    severity: str
    description: str
    classification: DrcFindingClass = DrcFindingClass.OTHER
    excluded: bool = False
    items: list[DrcItem] = Field(default_factory=list)
    raw: dict[str, object] = Field(default_factory=dict)


class DrcReport(BaseModel):
    status: DrcStatus
    tool_status: ToolStatus
    run_id: str
    kicad_version: str | None = None
    pcb_fingerprint: ArtifactFingerprint
    source_schematic_fingerprint: ArtifactFingerprint
    report_path: Path | None = None
    command: list[str] = Field(default_factory=list)
    return_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    findings: list[DrcFinding] = Field(default_factory=list)
    unconnected_items: list[DrcFinding] = Field(default_factory=list)
    ignored_checks: list[dict[str, object]] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    events: list[EngineeringEvent] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "DRC proves only that this exact PCB passed the configured KiCad physical design rules.",
        "DRC does not prove functional correctness, signal integrity, thermal or EMC performance, RF behavior, universal manufacturability, firmware behavior, or hardware operation.",
    ])


class PcbVerificationBundle(BaseModel):
    schematic: SchematicArtifact
    erc: ErcReport
    pcb: PcbArtifact
    drc: DrcReport
