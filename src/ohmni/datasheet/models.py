"""Contracts between candidate extraction, citation checking, and review UI."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, computed_field, model_validator

from ..domain import ClaimStatus, DatasheetDocument, DocumentSpan, Evidence, Quantity, Unit


class FactType(StrEnum):
    MANUFACTURER = "manufacturer"
    PART_NUMBER = "part_number"
    REVISION = "revision"
    PACKAGE = "package"
    PIN = "pin"
    SUPPLY_OPERATING_MIN = "supply_operating_min"
    SUPPLY_OPERATING_TYP = "supply_operating_typ"
    SUPPLY_OPERATING_MAX = "supply_operating_max"
    SUPPLY_ABSOLUTE_MIN = "supply_absolute_min"
    SUPPLY_ABSOLUTE_MAX = "supply_absolute_max"
    INTERFACE = "interface"
    I2C_ADDRESS = "i2c_address"
    DECOUPLING_CAPACITANCE = "decoupling_capacitance"
    PULL_UP_REQUIREMENT = "pull_up_requirement"
    CONTROL_CONDITION = "control_condition"


class CandidateClaim(BaseModel):
    candidate_id: str
    fact_type: FactType
    page: int = Field(ge=1)
    supporting_text: str
    quantity: Quantity | None = None
    text_value: str | None = None
    integer_value: int | None = None
    rail: str | None = None
    pin_number: str | None = None
    pin_function: str | None = None
    part_variant: str | None = None
    ambiguity: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_value(self) -> CandidateClaim:
        if sum(v is not None for v in (self.quantity, self.text_value, self.integer_value)) != 1:
            raise ValueError("candidate must propose exactly one typed value")
        quantity_types = {
            FactType.SUPPLY_OPERATING_MIN, FactType.SUPPLY_OPERATING_TYP,
            FactType.SUPPLY_OPERATING_MAX, FactType.SUPPLY_ABSOLUTE_MIN,
            FactType.SUPPLY_ABSOLUTE_MAX, FactType.DECOUPLING_CAPACITANCE,
        }
        if self.fact_type in quantity_types and self.quantity is None:
            raise ValueError(f"{self.fact_type.value} requires a quantity")
        expected = Unit.FARAD if self.fact_type is FactType.DECOUPLING_CAPACITANCE else Unit.VOLT
        if self.quantity is not None and self.fact_type in quantity_types and self.quantity.unit is not expected:
            raise ValueError(f"{self.fact_type.value} requires {expected.value}")
        if self.fact_type.value.startswith("supply_") and not self.rail:
            raise ValueError("supply claims require a rail name")
        return self


class ClaimVerificationStatus(StrEnum):
    VERIFIED = "verified"
    SOURCE_NOT_FOUND = "source_not_found"
    CLAIM_NOT_SUPPORTED = "claim_not_supported"
    AMBIGUOUS = "ambiguous"


class VerifiedCandidate(BaseModel):
    candidate: CandidateClaim
    status: ClaimVerificationStatus
    source_found: bool
    claim_supported: bool
    matched_span: DocumentSpan | None = None
    evidence: Evidence | None = None
    reasons: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def claim_status(self) -> ClaimStatus:
        return self.evidence.status if self.evidence is not None else ClaimStatus.UNKNOWN


class ConflictSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class EvidenceConflict(BaseModel):
    subject: str
    existing_value: str
    proposed_value: str
    existing_evidence: list[Evidence] = Field(default_factory=list)
    proposed_evidence: Evidence
    severity: ConflictSeverity = ConflictSeverity.ERROR
    recommendation: str = "Review the cited source and select the applicable datasheet revision."


class DatasheetIngestionReport(BaseModel):
    document: DatasheetDocument
    candidates: list[CandidateClaim] = Field(default_factory=list)
    results: list[VerifiedCandidate] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    unknown_required_fields: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def verified(self) -> list[VerifiedCandidate]:
        return [r for r in self.results if r.status is ClaimVerificationStatus.VERIFIED]

    @computed_field
    @property
    def rejected(self) -> list[VerifiedCandidate]:
        return [r for r in self.results if r.status in {
            ClaimVerificationStatus.SOURCE_NOT_FOUND,
            ClaimVerificationStatus.CLAIM_NOT_SUPPORTED,
        }]

    @computed_field
    @property
    def ambiguous(self) -> list[VerifiedCandidate]:
        return [r for r in self.results if r.status is ClaimVerificationStatus.AMBIGUOUS]
