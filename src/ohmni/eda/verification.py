"""Mapping external ERC into an additional Ohmni verification result."""

from __future__ import annotations

from ..domain import (
    RuleCategory,
    RuleOutcome,
    RuleResult,
    Severity,
    SubsystemStatus,
    VerificationFinding,
    VerificationReport,
)
from .models import ErcReport, ErcStatus


def erc_rule_result(erc: ErcReport) -> RuleResult:
    limitations = list(erc.limitations)
    if erc.status in {ErcStatus.UNAVAILABLE, ErcStatus.ERROR, ErcStatus.STALE_ARTIFACT}:
        return RuleResult(
            rule_id="KICAD-ERC", title="KiCad schematic electrical rules check",
            category=RuleCategory.EDA, outcome=RuleOutcome.ERROR,
            error_text=erc.stderr or erc.status.value,
            limitations=limitations,
        )
    findings = []
    for item in erc.findings:
        if item.excluded:
            continue
        severity = Severity.ERROR if item.severity == "error" else (
            Severity.WARNING if item.severity == "warning" else Severity.INFO
        )
        refs = sorted({
            word for erc_item in item.items
            for word in erc_item.description.replace("[", " ").split()
            if len(word) >= 2 and word[0] in "URCDJQ" and word[1:].isdigit()
        })
        findings.append(VerificationFinding(
            rule_id="KICAD-ERC", severity=severity,
            title=item.description, description=(
                f"KiCad ERC type={item.type}; sheet={item.sheet_path}. "
                "This finding came from the external EDA engine and is preserved independently."
            ),
            affected_components=refs,
            evidence=erc.evidence,
        ))
    return RuleResult(
        rule_id="KICAD-ERC", title="KiCad schematic electrical rules check",
        category=RuleCategory.EDA,
        outcome=RuleOutcome.FAIL if findings else RuleOutcome.PASS,
        findings=findings,
        examined=[f"artifact sha256:{erc.artifact_fingerprint.digest}"],
        limitations=limitations,
        notes=[f"KiCad {erc.kicad_version}; raw findings preserved: {len(erc.findings)}"],
    )


def aggregate_eda(semantic: VerificationReport, erc: ErcReport) -> VerificationReport:
    combined = semantic.model_copy(deep=True)
    combined.results.append(erc_rule_result(erc))
    if erc.status is ErcStatus.PASS:
        combined.subsystem_status["eda"] = SubsystemStatus.VERIFIED
    elif erc.status is ErcStatus.PASS_WITH_WARNINGS:
        combined.subsystem_status["eda"] = SubsystemStatus.PARTIALLY_VERIFIED
    elif erc.status in {ErcStatus.UNAVAILABLE, ErcStatus.ERROR, ErcStatus.STALE_ARTIFACT}:
        combined.subsystem_status["eda"] = SubsystemStatus.UNSUPPORTED
    else:
        combined.subsystem_status["eda"] = SubsystemStatus.NOT_VERIFIED
    return combined
