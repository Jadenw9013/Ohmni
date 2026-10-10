"""Evidence-bound SPICE model contracts, separate from CAD admission."""

from __future__ import annotations

import hashlib
import json
import posixpath
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


def content_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


class SpiceDialect(StrEnum):
    NGSPICE_42 = "ngspice-42"
    PSPICE = "pspice"
    LTSPICE = "ltspice"
    UNKNOWN = "unknown"


class ModelFidelity(StrEnum):
    VENDOR = "vendor_model"
    APPROXIMATION = "behavioural_approximation"


class SimulationAnalysis(StrEnum):
    OP = "op"
    TRAN = "tran"
    AC = "ac"


class ModelFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _contained(self):
        normalized = posixpath.normpath(self.path.replace("\\", "/"))
        if (normalized != self.path or normalized.startswith(("/", "../"))
                or normalized in {".", ".."} or ":" in normalized):
            raise ValueError("model file path must be normalized and manifest-relative")
        return self


class ModelProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: str = Field(min_length=1, max_length=200)
    source_url: str = Field(pattern=r"^https://", max_length=1000)
    acquired_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license: str = Field(min_length=1, max_length=500)
    source_document_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class SpiceModelManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    model_id: str = Field(min_length=1, max_length=160)
    entrypoint: str
    model_name: str = Field(min_length=1, max_length=160)
    dialect: SpiceDialect
    fidelity: ModelFidelity
    files: tuple[ModelFile, ...] = Field(min_length=1, max_length=64)
    provenance: ModelProvenance
    supported_analyses: tuple[SimulationAnalysis, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _complete(self):
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("model manifest file paths must be unique")
        if self.entrypoint not in paths:
            raise ValueError("model entrypoint must be manifest-listed")
        if len(self.supported_analyses) != len(set(self.supported_analyses)):
            raise ValueError("supported analyses must be unique")
        return self

    @property
    def manifest_sha256(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class ModelPinBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    symbol_pin: str = Field(min_length=1, max_length=40)
    model_port: str = Field(min_length=1, max_length=80)
    model_position: int = Field(ge=1, le=512)


class OperatingCondition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=100)
    minimum: float
    maximum: float
    unit: str = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def _ordered(self):
        if self.minimum > self.maximum:
            raise ValueError("operating condition minimum exceeds maximum")
        return self


class SpiceModelBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    component_revision_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    part_id: str = Field(min_length=1, max_length=200)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pins: tuple[ModelPinBinding, ...] = Field(min_length=1, max_length=512)
    conditions: tuple[OperatingCondition, ...] = ()

    @model_validator(mode="after")
    def _one_to_one(self):
        symbol = [item.symbol_pin for item in self.pins]
        positions = [item.model_position for item in self.pins]
        if len(symbol) != len(set(symbol)) or len(positions) != len(set(positions)):
            raise ValueError("model pin map must be one-to-one")
        if sorted(positions) != list(range(1, len(positions) + 1)):
            raise ValueError("model positions must be complete and contiguous")
        return self


class AssertionKind(StrEnum):
    VOLTAGE = "voltage"
    CURRENT = "current"
    GAIN_DB = "gain_db"


class MeasuredAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    assertion_id: str = Field(min_length=1, max_length=120)
    kind: AssertionKind
    signal: str = Field(min_length=1, max_length=120)
    minimum: float
    maximum: float
    unit: str = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def _ordered(self):
        if self.minimum > self.maximum:
            raise ValueError("assertion minimum exceeds maximum")
        return self


class SimulationPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    analysis: SimulationAnalysis
    assertions: tuple[MeasuredAssertion, ...] = Field(min_length=1, max_length=64)
    conditions: tuple[OperatingCondition, ...] = ()

    @model_validator(mode="after")
    def _unique(self):
        identifiers = [item.assertion_id for item in self.assertions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("assertion IDs must be unique")
        return self

    @property
    def plan_sha256(self) -> str:
        return content_hash(self.model_dump(mode="json"))


class SimulationEligibilityState(StrEnum):
    CAD_ONLY = "cad_only"
    ELIGIBLE = "simulation_eligible"


class SimulationEligibility(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    component_revision_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    state: SimulationEligibilityState
    binding: SpiceModelBinding | None = None
    manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _honest(self):
        ready = self.binding is not None and self.manifest_sha256 is not None
        if (self.state is SimulationEligibilityState.ELIGIBLE) != ready:
            raise ValueError("simulation eligibility requires an exact model binding and manifest")
        if self.binding and self.binding.manifest_sha256 != self.manifest_sha256:
            raise ValueError("eligibility manifest differs from binding")
        return self


__all__ = [
    "AssertionKind", "MeasuredAssertion", "ModelFidelity", "ModelFile", "ModelPinBinding",
    "ModelProvenance", "OperatingCondition", "SimulationAnalysis", "SimulationEligibility",
    "SimulationEligibilityState", "SimulationPlan", "SpiceDialect", "SpiceModelBinding",
    "SpiceModelManifest", "content_hash",
]
