"""Strict contracts at the model-proposal trust boundary."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..adapters import SimulationRun
from ..domain import (
    CircuitIR,
    EngineeringNotebook,
    Evidence,
    Interface,
    Lesson,
    RequirementsSpec,
    VerificationReport,
)
from ..eda.models import ErcReport, SchematicArtifact


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementOrigin(StrEnum):
    EXPLICIT = "explicit"
    DEFAULT = "default"
    DERIVED = "derived"
    ASSUMPTION = "assumption"


class RequirementStatement(StrictModel):
    field: str
    value: str
    origin: RequirementOrigin
    source_text: str | None = None


class RequirementInterpretation(StrictModel):
    project_name: str
    description: str
    max_input_voltage_v: float = Field(gt=0, le=12)
    target_logic_voltage_v: float | None = Field(default=None, gt=0, le=12)
    budget_usd: float | None = Field(default=None, ge=0)
    max_board_layers: int | None = Field(default=None, ge=1, le=8)
    hand_solderable: bool | None = None
    interfaces: list[Interface] = Field(default_factory=list)
    required_part_ids: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class CompiledRequirements(StrictModel):
    requirements: RequirementsSpec
    provenance: list[RequirementStatement]


class ComponentRequest(StrictModel):
    capability: str
    input_voltage_v: float | None = None
    output_voltage_v: float | None = None
    minimum_current_a: float | None = None
    required_interfaces: list[Interface] = Field(default_factory=list)
    hand_solderable_preferred: bool = False


class ComponentCandidate(StrictModel):
    part_id: str
    display_name: str
    fact_statuses: dict[str, str]
    evidence: list[Evidence] = Field(default_factory=list)


class ArchitectureBlock(StrictModel):
    block_id: str
    purpose: str
    selected_part_id: str | None = None
    required_interfaces: list[Interface] = Field(default_factory=list)
    required_rails: list[str] = Field(default_factory=list)
    unresolved_decisions: list[str] = Field(default_factory=list)
    evidence_source_ids: list[str] = Field(default_factory=list)
    alternatives_considered: list[str] = Field(default_factory=list)


class ArchitectureRelationship(StrictModel):
    source_block: str
    target_block: str
    interface: str


class ArchitectureProposal(StrictModel):
    blocks: list[ArchitectureBlock]
    relationships: list[ArchitectureRelationship] = Field(default_factory=list)
    component_requests: list[ComponentRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valid_graph(self) -> ArchitectureProposal:
        ids = [block.block_id for block in self.blocks]
        if len(ids) != len(set(ids)):
            raise ValueError("architecture block IDs must be unique")
        known = set(ids)
        for edge in self.relationships:
            if edge.source_block not in known or edge.target_block not in known:
                raise ValueError("architecture relationship references an unknown block")
        return self


class CircuitProposal(StrictModel):
    circuit: CircuitIR
    architecture_block_ids: list[str]
    rationale: list[str] = Field(default_factory=list)


class MovePinOperation(StrictModel):
    operation: str = Field(pattern="^move_pin$")
    component_ref: str
    pin: str
    from_net: str
    to_net: str


class CircuitPatch(StrictModel):
    original_circuit_hash: str
    triggering_finding_ids: list[str]
    operations: list[MovePinOperation] = Field(min_length=1)
    rationale: str


class GenerationIssueCode(StrEnum):
    REQUIREMENTS_INVALID = "requirements_invalid"
    REQUIREMENTS_CONFLICT = "requirements_conflict"
    COMPONENT_UNRESOLVED = "component_unresolved"
    PROPOSAL_SCHEMA_INVALID = "proposal_schema_invalid"
    PROPOSAL_STRUCTURALLY_INVALID = "proposal_structurally_invalid"
    SEMANTIC_VERIFICATION_FAILED = "semantic_verification_failed"
    REPAIR_FAILED = "repair_failed"
    REPAIR_CYCLE_DETECTED = "repair_cycle_detected"
    REPAIR_LIMIT_REACHED = "repair_limit_reached"
    SCHEMATIC_COMPILATION_FAILED = "schematic_compilation_failed"
    ERC_FAILED = "erc_failed"
    INFRASTRUCTURE_UNAVAILABLE = "infrastructure_unavailable"


class GenerationIssue(StrictModel):
    code: GenerationIssueCode
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class GenerationState(StrEnum):
    CREATED = "created"
    REQUIREMENTS_READY = "requirements_ready"
    EVIDENCE_READY = "evidence_ready"
    ARCHITECTURE_READY = "architecture_ready"
    CIRCUIT_PROPOSED = "circuit_proposed"
    SEMANTIC_VERIFYING = "semantic_verifying"
    REPAIRING = "repairing"
    SEMANTIC_VERIFIED = "semantic_verified"
    SCHEMATIC_COMPILED = "schematic_compiled"
    ERC_COMPLETE = "erc_complete"
    COMPLETE = "complete"
    FAILED = "failed"


TRANSITIONS = {
    GenerationState.CREATED: {GenerationState.REQUIREMENTS_READY, GenerationState.FAILED},
    GenerationState.REQUIREMENTS_READY: {GenerationState.EVIDENCE_READY, GenerationState.FAILED},
    GenerationState.EVIDENCE_READY: {GenerationState.ARCHITECTURE_READY, GenerationState.FAILED},
    GenerationState.ARCHITECTURE_READY: {GenerationState.CIRCUIT_PROPOSED, GenerationState.FAILED},
    GenerationState.CIRCUIT_PROPOSED: {GenerationState.SEMANTIC_VERIFYING, GenerationState.FAILED},
    GenerationState.SEMANTIC_VERIFYING: {GenerationState.REPAIRING, GenerationState.SEMANTIC_VERIFIED, GenerationState.FAILED},
    GenerationState.REPAIRING: {GenerationState.SEMANTIC_VERIFYING, GenerationState.FAILED},
    GenerationState.SEMANTIC_VERIFIED: {GenerationState.SCHEMATIC_COMPILED, GenerationState.COMPLETE, GenerationState.FAILED},
    GenerationState.SCHEMATIC_COMPILED: {GenerationState.ERC_COMPLETE, GenerationState.FAILED},
    GenerationState.ERC_COMPLETE: {GenerationState.COMPLETE, GenerationState.FAILED},
    GenerationState.COMPLETE: set(), GenerationState.FAILED: set(),
}


class GenerationStateMachine:
    def __init__(self) -> None:
        self.state = GenerationState.CREATED

    def transition(self, target: GenerationState) -> None:
        if target not in TRANSITIONS[self.state]:
            raise ValueError(f"invalid generation transition: {self.state.value} -> {target.value}")
        self.state = target


class RepairRecord(StrictModel):
    attempt: int
    original_circuit_hash: str
    triggering_finding_ids: list[str]
    patch: CircuitPatch
    patch_valid: bool
    resulting_circuit_hash: str | None = None
    post_repair_report: VerificationReport | None = None


class LlmCallRecord(StrictModel):
    """One structured proposal call, and what it cost to get it.

    The counts are per *call*, summed over every attempt that call took, so a
    request that needed two re-asks reports the tokens all three attempts spent.
    ``attempts`` is what makes that visible: without it a retried call and a
    first-time success look identical in the record, and a retry loop is only a
    cost control if someone can see it run.
    """

    provider: str
    model_id: str | None = None
    request_type: str
    response_schema: str
    success: bool
    attempts: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    token_usage: int | None = None
    latency_ms: float | None = None
    error: str | None = None


class DesignReport(StrictModel):
    state: GenerationState
    requirements: CompiledRequirements | None = None
    architecture: ArchitectureProposal | None = None
    initial_circuit_hash: str | None = None
    final_circuit: CircuitIR | None = None
    semantic_attempts: list[VerificationReport] = Field(default_factory=list)
    repairs: list[RepairRecord] = Field(default_factory=list)
    artifact: SchematicArtifact | None = None
    erc: ErcReport | None = None
    #: Corroboration, never a verdict. None means no attempt was made at all
    #: (no EDA stage ran); a run with status UNAVAILABLE or FAILED means one was
    #: attempted and did not produce an operating point. Neither is a pass.
    simulation: SimulationRun | None = None
    issues: list[GenerationIssue] = Field(default_factory=list)
    notebook: EngineeringNotebook | None = None
    lessons: list[Lesson] = Field(default_factory=list)
    llm_calls: list[LlmCallRecord] = Field(default_factory=list)
