"""Pure physical-design intent, independent of any EDA file format."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain import Evidence


class BoardOutline(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)


class PlacementRegion(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    x_min_mm: float
    y_min_mm: float
    x_max_mm: float
    y_max_mm: float

    @model_validator(mode="after")
    def _ordered(self) -> PlacementRegion:
        if self.x_min_mm >= self.x_max_mm or self.y_min_mm >= self.y_max_mm:
            raise ValueError("placement region must have positive width and height")
        return self


class BoardEdge(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class PlacementPose(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    x_mm: float
    y_mm: float
    rotation_deg: float = 0
    side: Literal["F.Cu"] = "F.Cu"


class PlacementConstraintKind(StrEnum):
    FIXED = "fixed"
    BOARD_EDGE = "board_edge"
    NEAR_COMPONENT = "near_component"
    AWAY_FROM_COMPONENT = "away_from_component"
    REGION = "region"
    ORIENTATION = "orientation"
    KEEPOUT = "keepout"


class PlacementConstraint(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    constraint_id: str
    kind: PlacementConstraintKind
    component_ref: str
    target_ref: str | None = None
    maximum_distance_mm: float | None = Field(default=None, ge=0)
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)
    minimum_distance_mm: float | None = Field(default=None, ge=0)
    fixed_pose: PlacementPose | None = None
    region: PlacementRegion | None = None
    allowed_rotations_deg: tuple[float, ...] = ()
    preferred_edge: BoardEdge | None = None
    component_pin: str | None = None
    target_pin: str | None = None
    keepout_region: PlacementRegion | None = None
    relative_to_component: bool = False


class ComponentPlacement(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    component_ref: str
    x_mm: float
    y_mm: float
    rotation_deg: float = 0
    side: Literal["F.Cu"] = "F.Cu"
    reason: str


class BoardConstraints(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    outline: BoardOutline
    layer_count: int = Field(default=2, ge=1)
    minimum_edge_clearance_mm: float = Field(default=1.0, ge=0)
    preferred_component_side: Literal["F.Cu"] = "F.Cu"
    placements: list[ComponentPlacement]
    placement_constraints: list[PlacementConstraint] = Field(default_factory=list)

    @model_validator(mode="after")
    def _supported(self) -> BoardConstraints:
        if self.layer_count != 2:
            raise ValueError("only deterministic 2-layer PCB generation is supported")
        refs = [p.component_ref for p in self.placements]
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate component placements")
        ids = [constraint.constraint_id for constraint in self.placement_constraints]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate placement constraint IDs")
        return self

    @property
    def content_hash(self) -> str:
        # Existing constraints retain their identity when new optional fields
        # are absent. Newly requested geometric policies remain hash-bound.
        values = self.model_dump(mode="json")
        for constraint in values["placement_constraints"]:
            for field in (
                "minimum_distance_mm", "fixed_pose", "region", "allowed_rotations_deg",
                "preferred_edge", "component_pin", "target_pin", "keepout_region",
                "relative_to_component",
            ):
                if constraint[field] is None or constraint[field] == [] or constraint[field] is False:
                    del constraint[field]
        payload = json.dumps(values, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()


class PlacementGroupKind(StrEnum):
    POWER = "power"
    PROCESSOR = "processor"
    SENSOR = "sensor"
    SPI = "spi"
    GPIO = "gpio"
    CONNECTOR = "connector"


class PlacementGroup(BaseModel):
    """One electrical block; members include the anchor exactly once."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    group_id: str = Field(min_length=1)
    kind: PlacementGroupKind
    anchor_ref: str = Field(min_length=1)
    member_refs: tuple[str, ...] = Field(min_length=1)
    reason: str

    @model_validator(mode="after")
    def _members(self) -> PlacementGroup:
        if self.anchor_ref not in self.member_refs:
            raise ValueError("placement group members must include its anchor")
        if len(self.member_refs) != len(set(self.member_refs)) or any(not ref for ref in self.member_refs):
            raise ValueError("placement group members must be unique nonempty references")
        return self


class DecouplingTarget(BaseModel):
    """Authored capacitor ownership, with a pad-to-pad distance policy."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    capacitor_ref: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    target_pin: str = Field(min_length=1)
    capacitor_pin: str = Field(default="1", min_length=1)
    maximum_distance_mm: float = Field(default=6, gt=0)
    reason: str
    evidence: tuple[Evidence, ...] = ()


class PlacementRequest(BaseModel):
    """Separate physical intent bound to one immutable electrical fingerprint."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    circuit_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    outline: BoardOutline
    groups: tuple[PlacementGroup, ...]
    decoupling: tuple[DecouplingTarget, ...] = ()
    constraints: tuple[PlacementConstraint, ...] = ()
    minimum_edge_clearance_mm: float = Field(default=1, ge=0)
    allowed_rotations_deg: tuple[float, ...] = (0,)
    side: Literal["F.Cu"] = "F.Cu"

    @model_validator(mode="after")
    def _unambiguous(self) -> PlacementRequest:
        group_ids = [group.group_id for group in self.groups]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("duplicate placement group IDs")
        refs = [ref for group in self.groups for ref in group.member_refs]
        if len(refs) != len(set(refs)):
            raise ValueError("a component cannot belong to multiple placement groups")
        if not self.allowed_rotations_deg:
            raise ValueError("at least one allowed placement rotation is required")
        ids = [constraint.constraint_id for constraint in self.constraints]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate placement constraint IDs")
        targets = [(item.capacitor_ref, item.capacitor_pin) for item in self.decoupling]
        if len(targets) != len(set(targets)):
            raise ValueError("duplicate decoupling ownership for a capacitor pin")
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
    model_config = ConfigDict(allow_inf_nan=False)
    number: str
    x_mm: float
    y_mm: float
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    kind: str = "smd"
    shape: str = "roundrect"
    mechanical: bool = False


class FootprintDefinition(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    footprint_id: str
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
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
    model_config = ConfigDict(allow_inf_nan=False)
    rule_id: str
    status: PhysicalRuleStatus
    description: str
    component_refs: list[str] = Field(default_factory=list)
    measured_mm: float | None = None
    limit_mm: float | None = None
    constraint_id: str | None = None


class PhysicalVerificationReport(BaseModel):
    findings: list[PhysicalFinding]
    limitations: list[str] = Field(default_factory=list)
    geometry_sources: dict[str, str] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return bool(self.findings) and all(f.status is PhysicalRuleStatus.PASS for f in self.findings)
