"""Verification results.

The important type here is :class:`RuleOutcome`. The specification gave every
rule exactly two possible outcomes -- it fires a finding or it does not -- which
makes "I checked and it is fine" indistinguishable from "I had no data to check
with". For an evidence-first product that is the worst available defect, so
outcomes are explicit and a report states its own coverage
(PRE_IMPLEMENTATION_REVIEW.md 5.1).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field

from .evidence import Evidence, SubsystemStatus


class Severity(StrEnum):
    """How bad a finding is.

    CRITICAL -- will damage hardware, or violates an absolute maximum rating.
    ERROR    -- the board will not work as intended.
    WARNING  -- likely a problem, or a real risk under conditions we cannot check.
    INFO     -- worth knowing; includes things we deliberately did not verify.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
    Severity.CRITICAL: 3,
}


def severity_rank(severity: Severity) -> int:
    return _SEVERITY_RANK[severity]


#: Severities that prevent a design being exported as *verified*.
#:
#: VERIFICATION.md says critical errors block export. ERROR is included as well:
#: shipping a design we know does not work, labelled verified, violates the
#: product's own hard target "unsupported claims marked verified: 0". A user may
#: still export the artifacts -- clearly marked unresolved -- which is a UI
#: decision, not a change to this policy.
BLOCKING_SEVERITIES: frozenset[Severity] = frozenset({Severity.ERROR, Severity.CRITICAL})


class RuleOutcome(StrEnum):
    """What actually happened when a rule ran."""

    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


class RuleCategory(StrEnum):
    """Verification layers, per VERIFICATION.md."""

    IDENTITY = "identity"
    CONNECTIVITY = "connectivity"
    PIN_SEMANTICS = "pin_semantics"
    ELECTRICAL = "electrical"
    INTERFACE = "interface"
    THERMAL = "thermal"
    EDA = "eda"
    SIMULATION = "simulation"


class VerificationFinding(BaseModel):
    """One problem, tied to the rule that found it and the evidence for it."""

    rule_id: str
    severity: Severity
    title: str
    description: str
    affected_components: list[str] = Field(default_factory=list)
    affected_nets: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    auto_fixable: bool = False
    suggested_fix: str | None = None
    lesson_topic: str | None = Field(
        default=None, description="Key into the teaching content for this class of mistake."
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def finding_id(self) -> str:
        """Stable id derived from the rule and what it points at.

        Deterministic so the same defect in the same circuit produces the same
        id across runs, which is what lets a repair say which finding it is
        addressing and lets tests assert on findings without ordering games.
        """
        subject = "|".join(
            [
                self.rule_id,
                ",".join(sorted(self.affected_components)),
                ",".join(sorted(self.affected_nets)),
                self.title,
            ]
        )
        return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:12]

    def describe(self) -> str:
        where = ", ".join(sorted(self.affected_components) + sorted(self.affected_nets))
        location = f" [{where}]" if where else ""
        return f"{self.severity.value.upper()} {self.rule_id}: {self.title}{location}"


class RuleResult(BaseModel):
    """The outcome of one rule against one circuit."""

    rule_id: str
    title: str
    category: RuleCategory
    outcome: RuleOutcome
    findings: list[VerificationFinding] = Field(default_factory=list)
    examined: list[str] = Field(
        default_factory=list, description="What the rule actually looked at. Auditable coverage."
    )
    missing_data: list[str] = Field(
        default_factory=list,
        description="Why the outcome is INSUFFICIENT_DATA. Must be non-empty when it is.",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description=(
            "What a PASS from this rule does NOT establish. The decoupling rule uses this "
            "to state that presence was checked and placement was not."
        ),
    )
    notes: list[str] = Field(default_factory=list)
    error_text: str | None = None

    @property
    def max_severity(self) -> Severity | None:
        if not self.findings:
            return None
        return max((f.severity for f in self.findings), key=severity_rank)


class VerificationReport(BaseModel):
    """The full result of verifying one circuit.

    Coverage is reported alongside pass/fail. A report in which seven rules
    returned INSUFFICIENT_DATA is presented as such, not as a clean bill of
    health.
    """

    report_id: str
    circuit_ir_id: str
    circuit_content_hash: str
    circuit_revision: int = 1
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    results: list[RuleResult] = Field(default_factory=list)
    subsystem_status: dict[str, SubsystemStatus] = Field(default_factory=dict)

    # -- derived views ---------------------------------------------------

    @computed_field  # type: ignore[prop-decorator]
    @property
    def findings(self) -> list[VerificationFinding]:
        """All findings, worst first, then by rule id for stable ordering."""
        every = [f for r in self.results for f in r.findings]
        return sorted(every, key=lambda f: (-severity_rank(f.severity), f.rule_id, f.title))

    def findings_of(self, severity: Severity) -> list[VerificationFinding]:
        return [f for f in self.findings if f.severity is severity]

    def finding_ids(self) -> set[str]:
        return {f.finding_id for f in self.findings}

    def rule(self, rule_id: str) -> RuleResult | None:
        for r in self.results:
            if r.rule_id == rule_id:
                return r
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def counts_by_severity(self) -> dict[Severity, int]:
        counts = dict.fromkeys(Severity, 0)
        for f in self.findings:
            counts[f.severity] += 1
        return counts

    @property
    def counts_by_outcome(self) -> dict[RuleOutcome, int]:
        counts = dict.fromkeys(RuleOutcome, 0)
        for r in self.results:
            counts[r.outcome] += 1
        return counts

    @property
    def applicable_rules(self) -> list[RuleResult]:
        """Rules that had something to check. NOT_APPLICABLE is excluded.

        A circuit with no LEDs is not penalised for the LED rule having nothing
        to say; a circuit whose LED lacks a forward-voltage spec is.
        """
        return [r for r in self.results if r.outcome is not RuleOutcome.NOT_APPLICABLE]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def coverage(self) -> float:
        """Fraction of applicable rules that reached a real verdict.

        1.0 means every rule that had work to do could actually do it. Anything
        less means the report is partly silence, and the UI must say so.
        """
        applicable = self.applicable_rules
        if not applicable:
            return 1.0
        decided = sum(
            1 for r in applicable if r.outcome in (RuleOutcome.PASS, RuleOutcome.FAIL)
        )
        return decided / len(applicable)

    @property
    def undecided_rules(self) -> list[RuleResult]:
        return [
            r
            for r in self.results
            if r.outcome in (RuleOutcome.INSUFFICIENT_DATA, RuleOutcome.ERROR)
        ]

    @property
    def blocking_findings(self) -> list[VerificationFinding]:
        return [f for f in self.findings if f.severity in BLOCKING_SEVERITIES]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def export_blocked(self) -> bool:
        """True when the design must not be presented as verified."""
        return bool(self.blocking_findings)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def limitations(self) -> list[str]:
        """Everything the passing rules explicitly did not establish."""
        out: list[str] = []
        for r in self.results:
            for text in r.limitations:
                entry = f"{r.rule_id}: {text}"
                if entry not in out:
                    out.append(entry)
        return out

    def summary_line(self) -> str:
        counts = self.counts_by_severity
        return (
            f"{len(self.findings)} findings "
            f"({counts[Severity.CRITICAL]} critical, {counts[Severity.ERROR]} error, "
            f"{counts[Severity.WARNING]} warning, {counts[Severity.INFO]} info); "
            f"coverage {self.coverage:.0%}; "
            f"export {'BLOCKED' if self.export_blocked else 'allowed'}"
        )
