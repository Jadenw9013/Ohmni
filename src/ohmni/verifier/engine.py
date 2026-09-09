"""Runs every registered rule against a circuit and assembles the report."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from ..adapters import PartCatalog
from ..domain.circuit import CircuitIR
from ..domain.evidence import SubsystemStatus
from ..domain.requirements import RequirementsSpec
from ..domain.verification import (
    RuleCategory,
    RuleOutcome,
    RuleResult,
    Severity,
    VerificationReport,
)

# Importing the rules package is what registers the rules.
from . import rules as _rules  # noqa: F401  (side-effecting import, intentional)
from .context import VerificationContext
from .registry import RegisteredRule, all_rules


def verify(
    circuit: CircuitIR,
    catalog: PartCatalog,
    requirements: RequirementsSpec | None = None,
    *,
    rule_subset: Sequence[str] | None = None,
) -> VerificationReport:
    """Verify a circuit deterministically.

    Same circuit and same catalog produce the same report, every time. No model
    is consulted, no network call is made, and no rule is allowed to skip
    quietly: a rule that cannot reach a verdict says so.
    """
    ctx = VerificationContext(circuit, catalog, requirements)

    selected: list[RegisteredRule] = all_rules()
    if rule_subset is not None:
        wanted = set(rule_subset)
        selected = [r for r in selected if r.rule_id in wanted]

    results: list[RuleResult] = [r.run(ctx) for r in selected]

    report_id = hashlib.sha256(
        f"{circuit.ir_id}:{circuit.content_hash}:{len(selected)}".encode()
    ).hexdigest()[:16]

    report = VerificationReport(
        report_id=report_id,
        circuit_ir_id=circuit.ir_id,
        circuit_content_hash=circuit.content_hash,
        circuit_revision=circuit.revision,
        results=results,
    )
    report.subsystem_status = _roll_up_subsystems(report)
    return report


#: Which rule categories speak for which subsystem. Kept explicit rather than
#: inferred, so a new rule cannot silently change what a subsystem's label means.
SUBSYSTEM_CATEGORIES: dict[str, tuple[RuleCategory, ...]] = {
    "identity": (RuleCategory.IDENTITY,),
    "connectivity": (RuleCategory.CONNECTIVITY,),
    "pin_semantics": (RuleCategory.PIN_SEMANTICS,),
    "electrical": (RuleCategory.ELECTRICAL,),
    "interfaces": (RuleCategory.INTERFACE,),
    "thermal": (RuleCategory.THERMAL,),
    "eda": (RuleCategory.EDA,),
    "simulation": (RuleCategory.SIMULATION,),
}


def _roll_up_subsystems(report: VerificationReport) -> dict[str, SubsystemStatus]:
    """Give each subsystem an honest label.

    The ordering matters. A subsystem with a failure is NOT_VERIFIED even if
    most of its rules passed, and a subsystem where some rules could not run is
    PARTIALLY_VERIFIED rather than VERIFIED. Only "every applicable rule ran and
    passed" earns VERIFIED.
    """
    out: dict[str, SubsystemStatus] = {}

    for name, categories in SUBSYSTEM_CATEGORIES.items():
        results = [r for r in report.results if r.category in categories]
        if not results:
            out[name] = SubsystemStatus.UNSUPPORTED
            continue

        applicable = [r for r in results if r.outcome is not RuleOutcome.NOT_APPLICABLE]
        if not applicable:
            out[name] = SubsystemStatus.UNSUPPORTED
            continue

        has_blocking = any(
            f.severity in (Severity.ERROR, Severity.CRITICAL)
            for r in applicable
            for f in r.findings
        )
        if has_blocking:
            out[name] = SubsystemStatus.NOT_VERIFIED
            continue

        undecided = [
            r
            for r in applicable
            if r.outcome in (RuleOutcome.INSUFFICIENT_DATA, RuleOutcome.ERROR)
        ]
        has_warnings = any(f.severity is Severity.WARNING for r in applicable for f in r.findings)

        if undecided or has_warnings:
            out[name] = SubsystemStatus.PARTIALLY_VERIFIED
        else:
            out[name] = SubsystemStatus.VERIFIED

    return out


def format_report(report: VerificationReport, *, verbose: bool = False) -> str:
    """A plain-text rendering, for the CLI and for test failure output."""
    lines: list[str] = [
        f"Ohmni verification report {report.report_id}",
        f"  circuit : {report.circuit_ir_id} rev {report.circuit_revision}",
        f"  hash    : {report.circuit_content_hash[:16]}",
        f"  summary : {report.summary_line()}",
        "",
    ]

    counts = report.counts_by_outcome
    lines.append(
        "Rules: "
        + ", ".join(f"{outcome.value}={counts[outcome]}" for outcome in RuleOutcome if counts[outcome])
    )
    lines.append("")

    if report.findings:
        lines.append("Findings")
        lines.append("-" * 60)
        for finding in report.findings:
            lines.append(f"[{finding.finding_id}] {finding.describe()}")
            lines.append(f"    {finding.description}")
            if finding.suggested_fix:
                lines.append(f"    fix: {finding.suggested_fix}")
            for evidence in finding.evidence:
                lines.append(f"    evidence ({evidence.status.value}): {evidence.describe()}")
            lines.append("")
    else:
        lines.append("No findings.")
        lines.append("")

    undecided = report.undecided_rules
    if undecided:
        lines.append("Could not be checked")
        lines.append("-" * 60)
        for result in undecided:
            lines.append(f"{result.rule_id} {result.title} [{result.outcome.value}]")
            for missing in result.missing_data:
                lines.append(f"    - {missing}")
            if result.error_text:
                lines.append(f"    ! {result.error_text}")
        lines.append("")

    if report.limitations:
        lines.append("What a pass here does not establish")
        lines.append("-" * 60)
        for limitation in report.limitations:
            lines.append(f"  - {limitation}")
        lines.append("")

    lines.append("Subsystems")
    lines.append("-" * 60)
    for name, status in sorted(report.subsystem_status.items()):
        lines.append(f"  {name:<14} {status.value}")

    if verbose:
        lines.append("")
        lines.append("All rules")
        lines.append("-" * 60)
        for result in report.results:
            lines.append(
                f"  {result.rule_id:<12} {result.outcome.value:<18} {result.title}"
            )
            for note in result.notes:
                lines.append(f"      note: {note}")

    return "\n".join(lines)
