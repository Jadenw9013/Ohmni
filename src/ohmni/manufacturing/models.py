"""Provenance-aware manufacturing, fabrication, and release models."""
from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from ..domain.events import EngineeringEvent


class ConstraintSource(StrEnum): SYNTHETIC_PROFILE="synthetic_profile"; MANUFACTURER="manufacturer"; PROJECT_DEFAULT="project_default"
class ManufacturingLimit(BaseModel): value: float; unit: str="mm"; source: ConstraintSource; rationale: str
class ManufacturingProfile(BaseModel):
    profile_id: str; display_name: str; source_name: str; source_version: str; provenance: ConstraintSource
    minimum_track_width: ManufacturingLimit; minimum_clearance: ManufacturingLimit; minimum_drill: ManufacturingLimit
    minimum_via_diameter: ManufacturingLimit; minimum_edge_clearance: ManufacturingLimit
    supported_layer_counts: list[int]; minimum_board_width_mm: float; minimum_board_height_mm: float
    maximum_board_width_mm: float; maximum_board_height_mm: float; board_thickness_options_mm:list[float]=Field(default_factory=lambda:[1.6])
    copper_weight_options_oz:list[float]=Field(default_factory=lambda:[1.0]); supported_finishes:list[str]=Field(default_factory=lambda:["HASL","ENIG"])
    supports_slots: bool=False
    @property
    def content_hash(self):return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

def prototype_profile():
    def limit(value,rationale):return ManufacturingLimit(value=value,source=ConstraintSource.SYNTHETIC_PROFILE,rationale=rationale)
    return ManufacturingProfile(profile_id="generic-prototype-2l-v1",display_name="Generic synthetic 2-layer prototype profile",source_name="Ohmni synthetic test/demo profile — not a fab quote",source_version="1.0",provenance=ConstraintSource.SYNTHETIC_PROFILE,minimum_track_width=limit(.15,"synthetic capability for deterministic evaluation"),minimum_clearance=limit(.15,"synthetic capability for deterministic evaluation"),minimum_drill=limit(.30,"synthetic capability for deterministic evaluation"),minimum_via_diameter=limit(.60,"synthetic capability for deterministic evaluation"),minimum_edge_clearance=limit(.30,"synthetic capability for deterministic evaluation"),supported_layer_counts=[2],minimum_board_width_mm=5,minimum_board_height_mm=5,maximum_board_width_mm=500,maximum_board_height_mm=500)

class ManufacturingStatus(StrEnum): PASS="pass"; FAIL="fail"; UNKNOWN="unknown"
class ManufacturingFinding(BaseModel): rule_id:str; status:ManufacturingStatus; subject:str; designed:float|str|None=None; limit:float|str|None=None; margin:float|None=None; unit:str|None=None; detail:str
class ManufacturingReport(BaseModel):
    profile:ManufacturingProfile
    routed_pcb_fingerprint:str
    routing_plan_fingerprint:str
    findings:list[ManufacturingFinding]
    events:list[EngineeringEvent]=Field(default_factory=list)

    @property
    def passed(self):return all(x.status is ManufacturingStatus.PASS for x in self.findings)
    @property
    def content_hash(self):return hashlib.sha256(self.model_dump_json(exclude={"events"}).encode()).hexdigest()

class FabricationFile(BaseModel): relative_path:str; sha256:str; size_bytes:int; kind:str
class ReleaseStatus(StrEnum): NOT_READY="not_ready"; READY_FOR_MANUFACTURING_REVIEW="ready_for_manufacturing_review"; BLOCKED="blocked"; STALE="stale"
class FabricationPackage(BaseModel):
    directory:Path; source_pcb_path:Path; source_pcb_fingerprint:str; source_schematic_fingerprint:str; routing_plan_fingerprint:str
    drc_fingerprint:str; manufacturing_profile_fingerprint:str; files:list[FabricationFile]; manifest_path:Path; package_fingerprint:str; status:ReleaseStatus
    limitations:list[str]=Field(default_factory=lambda:["Generated files are ready for human manufacturing review, not guaranteed fabrication success.","Not simulation, thermal, EMC/RF, assembly, or bench verified."])
    verification_findings:list[ManufacturingFinding]=Field(default_factory=list)
    events:list[EngineeringEvent]=Field(default_factory=list)
    @property
    def is_current(self):
        return self.source_pcb_path.is_file() and hashlib.sha256(self.source_pcb_path.read_bytes()).hexdigest()==self.source_pcb_fingerprint
    def files_current(self):
        return all((self.directory/x.relative_path).is_file() and (self.directory/x.relative_path).stat().st_size>0 and hashlib.sha256((self.directory/x.relative_path).read_bytes()).hexdigest()==x.sha256 for x in self.files)
    def is_valid_for(self,pcb_fingerprint:str,profile_fingerprint:str):
        return self.is_current and self.files_current() and self.source_pcb_fingerprint==pcb_fingerprint and self.manufacturing_profile_fingerprint==profile_fingerprint
