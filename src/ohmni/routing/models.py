"""Typed deterministic routing intent, separate from electrical and placement intent."""

from __future__ import annotations

import hashlib
import math
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain.events import EngineeringEvent


class ConstraintProvenance(StrEnum):
    PROJECT_DEFAULT = "project_default"
    BOARD_PROFILE = "board_profile"
    USER_REQUIREMENT = "user_requirement"
    DERIVED = "derived"


class ProfileValue(BaseModel):
    value: float | int
    provenance: ConstraintProvenance
    rationale: str


class RoutingProfile(BaseModel):
    name: str = "two-layer prototype"
    allowed_layers: tuple[str, str] = ("F.Cu", "B.Cu")
    signal_width_mm: ProfileValue = ProfileValue(value=0.25, provenance=ConstraintProvenance.PROJECT_DEFAULT, rationale="active prototype routing profile")
    power_width_mm: ProfileValue = ProfileValue(value=0.25, provenance=ConstraintProvenance.PROJECT_DEFAULT, rationale="prototype routing default; no current-density or thermal claim")
    clearance_mm: ProfileValue = ProfileValue(value=0.2, provenance=ConstraintProvenance.BOARD_PROFILE, rationale="prototype board design rule")
    via_diameter_mm: ProfileValue = ProfileValue(value=0.8, provenance=ConstraintProvenance.BOARD_PROFILE, rationale="prototype through-via geometry")
    via_drill_mm: ProfileValue = ProfileValue(value=0.4, provenance=ConstraintProvenance.BOARD_PROFILE, rationale="prototype through-via drill")
    grid_mm: ProfileValue = ProfileValue(value=0.25, provenance=ConstraintProvenance.PROJECT_DEFAULT, rationale="bounded path-search grid with clearance-scale resolution")
    edge_clearance_mm: ProfileValue = ProfileValue(value=0.5, provenance=ConstraintProvenance.BOARD_PROFILE, rationale="routing boundary inset")
    maximum_vias_per_connection: ProfileValue = ProfileValue(value=4, provenance=ConstraintProvenance.PROJECT_DEFAULT, rationale="bounded search policy")
    maximum_expanded_nodes: ProfileValue = ProfileValue(value=300000, provenance=ConstraintProvenance.PROJECT_DEFAULT, rationale="bounded search policy")

    @model_validator(mode="after")
    def _supported(self) -> RoutingProfile:
        if self.allowed_layers != ("F.Cu", "B.Cu"):
            raise ValueError("only F.Cu/B.Cu routing is supported")
        if float(self.via_drill_mm.value) >= float(self.via_diameter_mm.value):
            raise ValueError("via drill must be smaller than via diameter")
        return self

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class NetRoutingConstraint(BaseModel):
    net_name: str
    preferred_layer: str | None = None
    width_mm: float | None = None
    provenance: ConstraintProvenance = ConstraintProvenance.DERIVED
    rationale: str = "derived from net role"


class RoutingConstraints(BaseModel):
    profile: RoutingProfile = Field(default_factory=RoutingProfile)
    nets: list[NetRoutingConstraint] = Field(default_factory=list)


class Point(BaseModel):
    model_config = ConfigDict(frozen=True)
    x_mm: float
    y_mm: float


class TrackSegment(BaseModel):
    segment_id: str
    net_name: str
    layer: str
    start: Point
    end: Point
    width_mm: float = Field(gt=0)
    attempt_id: str

    @model_validator(mode="after")
    def _valid(self) -> TrackSegment:
        if self.layer not in {"F.Cu", "B.Cu"}:
            raise ValueError("unsupported copper layer")
        if self.start == self.end:
            raise ValueError("zero-length track")
        return self

    @property
    def length_mm(self) -> float:
        return math.hypot(self.end.x_mm-self.start.x_mm, self.end.y_mm-self.start.y_mm)


class Via(BaseModel):
    via_id: str
    net_name: str
    position: Point
    diameter_mm: float = Field(gt=0)
    drill_mm: float = Field(gt=0)
    source_layer: str = "F.Cu"
    destination_layer: str = "B.Cu"
    attempt_id: str

    @model_validator(mode="after")
    def _valid(self) -> Via:
        if {self.source_layer, self.destination_layer} != {"F.Cu", "B.Cu"}:
            raise ValueError("only F.Cu/B.Cu through-vias are supported")
        if self.drill_mm >= self.diameter_mm:
            raise ValueError("via drill must be smaller than diameter")
        return self


class RoutePath(BaseModel):
    source_pad: str
    target_pad: str
    tracks: list[TrackSegment]
    vias: list[Via] = Field(default_factory=list)
    expanded_nodes: int = 0


class RoutedNet(BaseModel):
    net_name: str
    terminal_pads: list[str]
    paths: list[RoutePath]


class RoutingFailureReason(StrEnum):
    NO_PATH = "no_path"
    SEARCH_LIMIT_REACHED = "search_limit_reached"
    VIA_LIMIT_REACHED = "via_limit_reached"
    PAD_ACCESS_BLOCKED = "pad_access_blocked"
    BOARD_CONSTRAINT_VIOLATION = "board_constraint_violation"
    ROUTE_COLLISION = "route_collision"
    UNSUPPORTED_GEOMETRY = "unsupported_geometry"
    NET_INCONSISTENCY = "net_inconsistency"
    ROUTING_INCOMPLETE = "routing_incomplete"


class RoutingFailure(BaseModel):
    net_name: str
    reason: RoutingFailureReason
    detail: str


class RoutingStatistics(BaseModel):
    required_connections: int
    routed_net_count: int
    unresolved_net_count: int
    track_segment_count: int
    via_count: int
    total_track_length_mm: float
    expanded_nodes: int
    routing_attempts: int
    reroute_count: int = 0
    route_order: list[str]


class RoutingPlan(BaseModel):
    source_pcb_fingerprint: str
    source_pcb_path: Path
    source_constraints_hash: str
    circuit_content_hash: str
    profile: RoutingProfile
    routed_nets: list[RoutedNet]
    failures: list[RoutingFailure] = Field(default_factory=list)
    statistics: RoutingStatistics
    events: list[EngineeringEvent] = Field(default_factory=list)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.model_dump_json(exclude={"events"}).encode()).hexdigest()

    @property
    def tracks(self) -> list[TrackSegment]:
        return [track for net in self.routed_nets for path in net.paths for track in path.tracks]

    @property
    def vias(self) -> list[Via]:
        return [via for net in self.routed_nets for path in net.paths for via in path.vias]


class RoutingRuleStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class RoutingFinding(BaseModel):
    rule_id: str
    status: RoutingRuleStatus
    description: str
    net_names: list[str] = Field(default_factory=list)


class RoutingVerificationReport(BaseModel):
    plan_fingerprint: str
    findings: list[RoutingFinding]

    @property
    def passed(self) -> bool:
        return all(f.status is RoutingRuleStatus.PASS for f in self.findings)
