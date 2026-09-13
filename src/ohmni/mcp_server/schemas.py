"""Bounded proposal contracts. Domain validators still own electrical semantics."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, model_validator

from ..domain.circuit import (
    CircuitComponent,
    CircuitIR,
    DesignConstraint,
    ExternalSource,
    Net,
    PinRef,
)
from ..domain.component import ComponentSpec, Interface
from ..domain.requirements import FunctionalRequirement, RequirementsSpec, SafetyDomain
from ..domain.units import Quantity, ValueRange
from ..domain.verification import VerificationReport

MAX_COMPONENTS = 128
MAX_NETS = 256
MAX_CONNECTIONS = 2048
MAX_STRING_LENGTH = 4096
MAX_ARGUMENT_BYTES = 1_048_576
Identifier = Annotated[str, Field(min_length=1, max_length=128)]
Text = Annotated[str, Field(max_length=MAX_STRING_LENGTH)]
EmptyEvidence = Annotated[list[None], Field(max_length=0)]


class InputModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_max_length=MAX_STRING_LENGTH,
        hide_input_in_errors=True,
    )


class ProposedQuantity(Quantity, InputModel):
    value: StrictFloat

    @model_validator(mode="before")
    @classmethod
    def _accept_shorthand(cls, data):
        # Override the fixture convenience parser: the wire schema requires an object.
        if isinstance(data, str):
            raise ValueError("Quantity proposals require a value/unit object")  # noqa: TRY004 -- validation
        return data


class ProposedRange(ValueRange, InputModel):
    minimum: ProposedQuantity | None = None
    typical: ProposedQuantity | None = None
    maximum: ProposedQuantity | None = None


class ProposedSource(ExternalSource, InputModel):
    voltage: ProposedRange
    current_limit: ProposedQuantity | None = None
    evidence: EmptyEvidence = Field(default_factory=list)


class ProposedPin(PinRef, InputModel):
    component: Identifier
    pin: Identifier


class ProposedNet(Net, InputModel):
    name: Identifier
    connections: list[ProposedPin] = Field(default_factory=list, max_length=MAX_CONNECTIONS)
    external_source: ProposedSource | None = None


class ProposedComponent(CircuitComponent, InputModel):
    ref: Identifier
    part_id: Identifier
    value: ProposedQuantity | None = None
    selected_i2c_address: int | None = Field(default=None, strict=True, ge=0, le=127)
    selected_interfaces: list[Interface] = Field(default_factory=list, max_length=32)
    placeholder: StrictBool = False
    evidence: EmptyEvidence = Field(default_factory=list)


class ProposedConstraint(DesignConstraint, InputModel):
    constraint_id: Identifier
    hard: StrictBool = True
    applies_to: list[Identifier] = Field(default_factory=list, max_length=MAX_COMPONENTS + MAX_NETS)
    evidence: EmptyEvidence = Field(default_factory=list)


class CircuitProposal(CircuitIR, InputModel):
    """Untrusted intent; evidence must be omitted or empty at every input location."""

    ir_id: Identifier
    name: Identifier
    revision: int = Field(default=1, strict=True, ge=1)
    components: list[ProposedComponent] = Field(default_factory=list, max_length=MAX_COMPONENTS)
    nets: list[ProposedNet] = Field(default_factory=list, max_length=MAX_NETS)
    constraints: list[ProposedConstraint] = Field(default_factory=list, max_length=128)
    design_assumptions: list[Text] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def bounded_connections(self):
        if sum(len(net.connections) for net in self.nets) > MAX_CONNECTIONS:
            raise ValueError("Too many connections")
        return self


class ProposedFunction(FunctionalRequirement, InputModel):
    requirement_id: Identifier
    mandatory: StrictBool = True


class RequirementsProposal(RequirementsSpec, InputModel):
    max_input_voltage: ProposedQuantity
    target_logic_voltage: ProposedQuantity | None = None
    budget_usd: StrictFloat | None = Field(default=None, ge=0)
    max_board_layers: int = Field(default=2, strict=True, ge=1, le=8)
    hand_solderable: StrictBool = True
    min_package_pitch_mm: StrictFloat | None = Field(default=None, gt=0)
    interfaces: list[Interface] = Field(default_factory=list, max_length=32)
    functional_requirements: list[ProposedFunction] = Field(default_factory=list, max_length=128)
    required_part_ids: list[Identifier] = Field(default_factory=list, max_length=MAX_COMPONENTS)
    prohibited_part_ids: list[Identifier] = Field(default_factory=list, max_length=MAX_COMPONENTS)
    safety_domains: list[SafetyDomain] = Field(default_factory=list, max_length=32)
    assumptions: list[Text] = Field(default_factory=list, max_length=128)
    evidence: EmptyEvidence = Field(default_factory=list)


class VerifyRequest(InputModel):
    circuit: CircuitProposal
    requirements: RequirementsProposal | None = None


class ListPartsRequest(InputModel):
    offset: int = Field(default=0, strict=True, ge=0)
    limit: int = Field(default=25, strict=True, ge=1, le=100)


class GetPartRequest(InputModel):
    part_id: Identifier


class Capabilities(BaseModel):
    schema_version: Literal["1"] = "1"
    scope: Literal["semantic_only"] = "semantic_only"
    tools: list[str]
    catalog_hash: str
    verifier_hash: str
    rule_ids: list[str]
    limits: dict[str, int]
    limitations: list[str]


class PartSummary(BaseModel):
    part_id: str
    manufacturer: str | None
    mpn: str | None
    category: str


class PartPage(BaseModel):
    catalog_hash: str
    total: int
    offset: int
    parts: list[PartSummary]
    next_offset: int | None


class PartDetail(BaseModel):
    catalog_hash: str
    part: ComponentSpec


class VerificationResult(BaseModel):
    schema_version: Literal["1"] = "1"
    input_hash: str
    catalog_hash: str
    verifier_hash: str
    requirements_supported: bool | None
    report: VerificationReport
    undecided_rule_ids: list[str]
    limitations: list[str]
