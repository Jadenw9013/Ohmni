"""Controlled evidence upgrade for an existing catalog ComponentSpec."""

from __future__ import annotations

from ..domain import ComponentSpec, Interface
from .models import EvidenceConflict, FactType, VerifiedCandidate


def apply_verified_claims(
    component: ComponentSpec, claims: list[VerifiedCandidate]
) -> tuple[ComponentSpec, list[EvidenceConflict]]:
    """Attach verified evidence without silently replacing conflicting values."""
    updated = component.model_copy(deep=True)
    conflicts: list[EvidenceConflict] = []
    for result in claims:
        if not result.claim_supported or result.evidence is None:
            continue
        claim = result.candidate
        evidence = result.evidence
        if claim.fact_type in {
            FactType.SUPPLY_OPERATING_MIN, FactType.SUPPLY_OPERATING_TYP,
            FactType.SUPPLY_OPERATING_MAX, FactType.SUPPLY_ABSOLUTE_MIN,
            FactType.SUPPLY_ABSOLUTE_MAX,
        }:
            rail = updated.rail(claim.rail or "")
            if rail is None:
                conflicts.append(EvidenceConflict(
                    subject=f"unknown rail {claim.rail}", existing_value="missing",
                    proposed_value=claim.quantity.engineering(), proposed_evidence=evidence,
                    existing_evidence=[],
                ))
                continue
            if claim.fact_type is FactType.SUPPLY_OPERATING_MIN:
                existing = rail.operating.minimum
            elif claim.fact_type is FactType.SUPPLY_OPERATING_TYP:
                existing = rail.operating.typical
            elif claim.fact_type is FactType.SUPPLY_OPERATING_MAX:
                existing = rail.operating.maximum
            elif claim.fact_type is FactType.SUPPLY_ABSOLUTE_MIN:
                existing = rail.absolute_min
            else:
                existing = rail.absolute_max
            if existing is not None and not existing.is_close(claim.quantity):
                conflicts.append(EvidenceConflict(
                    subject=f"{updated.part_id} {rail.name} {claim.fact_type.value}",
                    existing_value=existing.engineering(), proposed_value=claim.quantity.engineering(),
                    existing_evidence=rail.evidence, proposed_evidence=evidence,
                ))
                continue
            rail.evidence.append(evidence)
        elif claim.fact_type is FactType.DECOUPLING_CAPACITANCE:
            matching = [r for r in updated.decoupling_rules if r.rail == claim.rail]
            if matching and matching[0].per_pin_capacitance is not None and matching[0].per_pin_capacitance.is_close(claim.quantity):
                matching[0].evidence.append(evidence)
            elif matching:
                conflicts.append(EvidenceConflict(
                    subject=f"{updated.part_id} {claim.rail} decoupling",
                    existing_value=str(matching[0].per_pin_capacitance),
                    proposed_value=claim.quantity.engineering(),
                    existing_evidence=matching[0].evidence, proposed_evidence=evidence,
                ))
            elif claim.rail is None:
                # The document may state C1/C2 values without text-extractable
                # diagram connectivity. Preserve the verified general requirement
                # at component level; do not invent which capacitor belongs to a rail.
                updated.evidence.append(evidence)
        elif claim.fact_type is FactType.INTERFACE:
            try:
                interface = Interface(claim.text_value)
            except ValueError:
                continue
            if interface in updated.interfaces:
                updated.evidence.append(evidence)
        elif claim.fact_type is FactType.I2C_ADDRESS:
            matching = [a for a in updated.i2c_addresses if a.address == claim.integer_value]
            if matching:
                updated.evidence.append(evidence)
        elif claim.fact_type is FactType.PIN:
            pin = updated.pin(claim.pin_number or "")
            if pin is not None and pin.name.casefold() == (claim.text_value or "").casefold():
                pin.evidence.append(evidence)
        elif claim.fact_type in {
            FactType.MANUFACTURER, FactType.PART_NUMBER, FactType.REVISION, FactType.PACKAGE,
            FactType.PULL_UP_REQUIREMENT, FactType.CONTROL_CONDITION,
        }:
            updated.evidence.append(evidence)
    first_evidence = next((result.evidence for result in claims if result.evidence), None)
    if first_evidence is not None:
        updated.datasheet = first_evidence.document
    return updated, conflicts
