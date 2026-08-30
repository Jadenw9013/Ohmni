"""Pure physical-design intent, independent of any EDA file format."""

from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain import Evidence


class BoardOutline(BaseModel):
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)


class PlacementRegion(BaseModel):
    x_min_mm: float
    y_min_mm: float
    x_max_mm: float
    y_max_mm: float


class PlacementConstraintKind(StrEnum):
    FIXED = "fixed"
    BOARD_EDGE = "board_edge"
    NEAR_COMPONENT = "near_component"
    AWAY_FROM_COMPONENT = "away_from_component"


class PlacementConstraint(BaseModel):
    constraint_id: str
    kind: PlacementConstraintKind
    component_ref: str
    target_ref: str | None = None
    maximum_distance_mm: float | None = None
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)


class ComponentPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)
    component_ref: str
    x_mm: float
    y_mm: float
    rotation_deg: float = 0
    side: str = "F.Cu"
    reason: str


class BoardConstraints(BaseModel):
    outline: BoardOutline
    layer_count: int = Field(default=2, ge=1)
    minimum_edge_clearance_mm: float = Field(default=1.0, ge=0)
    preferred_component_side: str = "F.Cu"
    placements: list[ComponentPlacement]
    placement_constraints: list[PlacementConstraint] = Field(default_factory=list)

    @model_validator(mode="after")
    def _supported(self) -> BoardConstraints:
        if self.layer_count != 2:
            raise ValueError("only deterministic 2-layer PCB generation is supported")
        refs = [p.component_ref for p in self.placements]
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate component placements")
        return self

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class FootprintSource(BaseModel):
    library_id: str
    upstream_file_sha256: str
    license: str
    derivation: str


class FootprintPad(BaseModel):
    number: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    kind: str = "smd"
    shape: str = "roundrect"
    mechanical: bool = False


class FootprintDefinition(BaseModel):
    footprint_id: str
    width_mm: float
    height_mm: float
    pads: list[FootprintPad]
    source: FootprintSource


class FootprintBinding(BaseModel):
    component_ref: str
    part_id: str
    package: str
    footprint_id: str
    source: FootprintSource


class PadBinding(BaseModel):
    component_ref: str
    pin_number: str
    pad_number: str
    net_name: str | None = None


class PhysicalRuleStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


class PhysicalFinding(BaseModel):
    rule_id: str
    status: PhysicalRuleStatus
    description: str
    component_refs: list[str] = Field(default_factory=list)
    measured_mm: float | None = None
    limit_mm: float | None = None


class PhysicalVerificationReport(BaseModel):
    findings: list[PhysicalFinding]

    @property
    def passed(self) -> bool:
        return not any(f.status is PhysicalRuleStatus.FAIL for f in self.findings)

