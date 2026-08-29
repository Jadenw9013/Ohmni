"""Engineering history: what happened, what was decided, and what was taught.

The lesson generator is the part of this product most likely to drift into
confident fiction. The defence is structural: a :class:`Lesson` cannot be
constructed without naming the events or evidence it was derived from, so a
lesson about a repair that never happened is a validation error rather than a
plausible paragraph.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .evidence import ClaimStatus, Evidence, status_rank


class EventKind(StrEnum):
    REQUIREMENTS_CAPTURED = "requirements_captured"
    SCOPE_REJECTED = "scope_rejected"
    DATASHEET_INGESTED = "datasheet_ingested"
    FACT_EXTRACTED = "fact_extracted"
    CITATION_VERIFICATION_FAILED = "citation_verification_failed"
    PROMPT_INJECTION_SUSPECTED = "prompt_injection_suspected"
    PART_SELECTED = "part_selected"
    PART_REJECTED = "part_rejected"
    CIRCUIT_GENERATED = "circuit_generated"
    SCHEMATIC_COMPILATION_STARTED = "schematic_compilation_started"
    SCHEMATIC_COMPILED = "schematic_compiled"
    SCHEMATIC_COMPILATION_FAILED = "schematic_compilation_failed"
    ERC_STARTED = "erc_started"
    ERC_COMPLETED = "erc_completed"
    ERC_VIOLATION_FOUND = "erc_violation_found"
    ARTIFACT_INVALIDATED = "artifact_invalidated"
    VERIFICATION_RUN = "verification_run"
    FINDING_RAISED = "finding_raised"
    REPAIR_PROPOSED = "repair_proposed"
    REPAIR_APPLIED = "repair_applied"
    REPAIR_REJECTED = "repair_rejected"
    OSCILLATION_DETECTED = "oscillation_detected"
    ERC_RUN = "erc_run"
    DRC_RUN = "drc_run"
    SIMULATION_RUN = "simulation_run"
    TOOL_UNAVAILABLE = "tool_unavailable"
    ASSUMPTION_RECORDED = "assumption_recorded"
    HUMAN_CONFIRMATION = "human_confirmation"
    EXPORT_BLOCKED = "export_blocked"
    EXPORT_COMPLETED = "export_completed"


class EngineeringEvent(BaseModel):
    """One thing that happened, in order, with whatever supported it.

    This log is the only permitted input to the notebook and the lesson
    generator. If it did not happen here, it did not happen.
    """

    event_id: str
    kind: EventKind
    summary: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    circuit_content_hash: str | None = Field(
        default=None, description="Which revision of the design this event refers to."
    )
    related_components: list[str] = Field(default_factory=list)
    related_nets: list[str] = Field(default_factory=list)
    related_finding_ids: list[str] = Field(default_factory=list)
    payload: dict[str, object] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class Alternative(BaseModel):
    """An option that was considered and not taken, and why."""

    option: str
    rejected_because: str
    evidence: list[Evidence] = Field(default_factory=list)


class Lesson(BaseModel):
    """A short teaching note tied to something that actually occurred.

    ``derived_from_event_ids`` or ``evidence`` must be non-empty. A lesson with
    neither is an invented explanation, which AGENT_DESIGN.md forbids.
    """

    topic: str
    body: str
    derived_from_event_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_grounding(self) -> Lesson:
        if not self.derived_from_event_ids and not self.evidence:
            raise ValueError(
                f"lesson {self.topic!r} cites no event and no evidence; "
                "lessons must be derived from what actually happened"
            )
        return self


class DecisionRecord(BaseModel):
    """Why the design looks the way it does.

    The shape follows the educational UX in MASTER_BUILD_PROMPT.md: requirement,
    decision, evidence, alternative, verification, lesson. ``status`` is derived
    from the evidence, so a decision backed by nothing reads as ASSUMED or
    UNKNOWN rather than as a confident statement.
    """

    decision_id: str
    requirement: str
    decision: str
    rationale: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    affected_components: list[str] = Field(default_factory=list)
    affected_nets: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    verified_by_rule_ids: list[str] = Field(default_factory=list)
    source_requirement_id: str | None = None
    lesson: Lesson | None = None

    @property
    def status(self) -> ClaimStatus:
        if not self.evidence:
            return ClaimStatus.UNKNOWN
        return max((e.status for e in self.evidence), key=status_rank)


class EngineeringNotebook(BaseModel):
    """The user-facing record of what was verified, assumed, or left unknown."""

    notebook_id: str
    project_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    events: list[EngineeringEvent] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    lessons: list[Lesson] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _lessons_reference_known_events(self) -> EngineeringNotebook:
        known = {e.event_id for e in self.events}
        for lesson in self.lessons:
            unknown = [eid for eid in lesson.derived_from_event_ids if eid not in known]
            if unknown:
                raise ValueError(
                    f"lesson {lesson.topic!r} cites events not in this notebook: {unknown}"
                )
        return self

    def events_of(self, kind: EventKind) -> list[EngineeringEvent]:
        return [e for e in self.events if e.kind is kind]
