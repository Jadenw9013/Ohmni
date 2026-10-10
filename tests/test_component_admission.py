from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from ohmni.catalog import ComponentStore, default_catalog
from ohmni.catalog.component_store import (
    _MIGRATIONS,
    LATEST_SCHEMA_VERSION,
    ActivationDisabledError,
    BlobReference,
    ComponentStoreError,
    _apply_migrations,
)
from ohmni.domain import (
    AdmissionRequest,
    ApplicableRuleOutcome,
    ApplicableRuleResult,
    CheckedElectricalClaims,
    CheckedElectricalFact,
    ComponentCategory,
    ElectricalProfile,
    PinElectricalType,
    PinRole,
    evaluate_admission,
)
from ohmni.domain.component_synthesis import (
    CHECKER_CONTRACT_VERSION,
    Capability,
    DimensionKind,
    LengthValue,
    LimitColumn,
    PadSlot,
    ReceiptOutcome,
    SourceUnit,
    TerminalKind,
    VerificationReceipt,
    VerifiedConstraintSet,
    VerifiedDimension,
    VerifiedIdentity,
    VerifiedPadOrdering,
    VerifiedTerminal,
    claim_hash,
)

DIGEST = "1" * 64
OBSERVATION = "2" * 64
PUBLICATION = "3" * 64


def _receipt(receipt_id: str, payload: dict) -> VerificationReceipt:
    return VerificationReceipt(
        receipt_id=receipt_id,
        checker="CS-ELECTRICAL",
        checker_version=CHECKER_CONTRACT_VERSION,
        outcome=ReceiptOutcome.SUPPORTED,
        claim_hash=claim_hash(payload),
        document_digest=DIGEST,
        observation_digest=OBSERVATION,
    )


def _constraints(pin_count: int = 2, *, manufacturer: str = "Acme") -> VerifiedConstraintSet:
    identity = VerifiedIdentity(
        manufacturer=manufacturer,
        base_device="R100",
        orderable_part_number="R100-0603",
        package_code="0603",
        package_description="0603",
        pin_count=pin_count,
        document_revision="A",
        drawing_number="DWG-1",
        receipt_id="IDENTITY",
    )
    dimension = VerifiedDimension(
        kind=DimensionKind.LAND_PAD_WIDTH,
        dimension_symbol="X",
        limit=LimitColumn.NOM,
        value=LengthValue.parse("0.8", SourceUnit.MILLIMETRE),
        basic_dimension=False,
        applies_to_terminals=pin_count,
        receipt_id="DIMENSION",
    )
    terminals = tuple(
        VerifiedTerminal(
            package_column="0603",
            pin_number=str(number),
            symbol=str(number),
            function=f"Terminal {number}",
            kind=TerminalKind.ELECTRICAL,
            receipt_id=f"TERMINAL-{number}",
        )
        for number in range(1, pin_count + 1)
    )
    ordering = VerifiedPadOrdering(
        traversal="counter_clockwise_from_pin_1",
        first_pin_corner="bottom_left",
        slots=tuple(
            PadSlot(pin_number=str(number), row=0, column=number - 1)
            for number in range(1, pin_count + 1)
        ),
        receipt_id="ORDERING",
    )
    values = [(identity.receipt_id, identity.claim()), (dimension.receipt_id, dimension.claim())]
    values.extend((terminal.receipt_id, terminal.claim()) for terminal in terminals)
    values.append((ordering.receipt_id, ordering.claim()))
    receipts = tuple(_receipt(receipt_id, payload) for receipt_id, payload in values)
    return VerifiedConstraintSet(
        document_digest=DIGEST,
        observation_digest=OBSERVATION,
        identity=identity,
        dimensions=(dimension,),
        terminals=terminals,
        pad_ordering=ordering,
        receipts=receipts,
    )


def _claims(
    *,
    profile: ElectricalProfile = ElectricalProfile.PASSIVE_TWO_TERMINAL,
    omit: frozenset[str] = frozenset(),
    overrides: dict[str, str | int | bool | tuple[str, ...]] | None = None,
) -> CheckedElectricalClaims:
    values: dict[str, str | int | bool | tuple[str, ...]] = {
        "component.manufacturer": "Acme",
        "component.mpn": "R100-0603",
        "component.category": ComponentCategory.RESISTOR.value,
        "component.description": "100 ohm chip resistor",
        "package.name": "0603",
        "pin.1.name": "1",
        "pin.1.roles": (PinRole.TERMINAL.value,),
        "pin.1.electrical_type": PinElectricalType.PASSIVE.value,
        "pin.2.name": "2",
        "pin.2.roles": (PinRole.TERMINAL.value,),
        "pin.2.electrical_type": PinElectricalType.PASSIVE.value,
    }
    values.update(overrides or {})
    facts = tuple(
        CheckedElectricalFact(fact_id=fact_id, value=value, receipt_id=f"E-{index}")
        for index, (fact_id, value) in enumerate(sorted(values.items()))
        if fact_id not in omit
    )
    receipts = tuple(_receipt(fact.receipt_id, fact.claim()) for fact in facts)
    return CheckedElectricalClaims(
        document_digest=DIGEST,
        observation_digest=OBSERVATION,
        profile=profile,
        facts=facts,
        receipts=receipts,
    )


def _rules(
    changed: dict[str, ApplicableRuleOutcome] | None = None,
) -> tuple[ApplicableRuleResult, ...]:
    outcomes = {
        "source.constraints": ApplicableRuleOutcome.PASS,
        "assets.geometry": ApplicableRuleOutcome.PASS,
        "assets.native": ApplicableRuleOutcome.PASS,
        "electrical.passive": ApplicableRuleOutcome.PASS,
    }
    outcomes.update(changed or {})
    return tuple(
        ApplicableRuleResult(
            rule_id=rule_id,
            outcome=outcome,
            report_digest=hashlib.sha256(rule_id.encode()).hexdigest(),
            detail=f"{rule_id} evaluated {outcome.value}",
        )
        for rule_id, outcome in sorted(outcomes.items())
    )


def _request(
    *,
    claims: CheckedElectricalClaims | None = None,
    rules: tuple[ApplicableRuleResult, ...] | None = None,
    requested: tuple[Capability, ...] = (Capability.ELECTRICAL_PROFILE, Capability.ROUTING),
    revision_id: str = "a" * 32,
    publication_digest: str = PUBLICATION,
    constraints: VerifiedConstraintSet | None = None,
) -> AdmissionRequest:
    return AdmissionRequest(
        revision_id=revision_id,
        publication_digest=publication_digest,
        constraints=constraints or _constraints(),
        electrical=claims or _claims(),
        applicable_rules=rules or _rules(),
        requested_capabilities=requested,
    )


def test_complete_passive_profile_builds_component_and_support_matrix():
    decision = evaluate_admission(_request())

    assert decision.admitted
    assert decision.reasons == ()
    assert decision.component_spec is not None
    assert decision.component_spec.mpn == "R100-0603"
    assert [pin.electrical_type for pin in decision.component_spec.pins] == [
        PinElectricalType.PASSIVE,
        PinElectricalType.PASSIVE,
    ]
    assert decision.capabilities.supports(Capability.ELECTRICAL_PROFILE)
    assert decision.capabilities.supports(Capability.ROUTING)
    assert not decision.capabilities.supports(Capability.SIMULATION)


def test_complete_i2c_profile_constructs_rails_roles_interface_and_address():
    values: dict[str, str | int | bool | tuple[str, ...]] = {
        "component.category": ComponentCategory.SENSOR.value,
        "pin.1.name": "VDD",
        "pin.1.roles": (PinRole.POWER.value,),
        "pin.1.electrical_type": PinElectricalType.POWER_IN.value,
        "pin.1.supply_rail": "VDD",
        "pin.2.name": "GND",
        "pin.2.roles": (PinRole.GROUND.value,),
        "pin.2.electrical_type": PinElectricalType.POWER_IN.value,
        "pin.3.name": "SDA",
        "pin.3.roles": (PinRole.I2C_SDA.value,),
        "pin.3.electrical_type": PinElectricalType.BIDIRECTIONAL.value,
        "pin.3.supply_rail": "VDD",
        "pin.4.name": "SCL",
        "pin.4.roles": (PinRole.I2C_SCL.value,),
        "pin.4.electrical_type": PinElectricalType.INPUT.value,
        "pin.4.supply_rail": "VDD",
        "interface.i2c": True,
        "rail.names": ("VDD",),
        "rail.vdd.minimum": "1.8V",
        "rail.vdd.maximum": "3.6V",
        "i2c.addresses": ("0x48",),
    }
    claims = _claims(profile=ElectricalProfile.I2C_PERIPHERAL, overrides=values)
    rules = tuple(
        item for item in _rules() if item.rule_id != "electrical.passive"
    ) + (
        ApplicableRuleResult(
            rule_id="electrical.i2c",
            outcome=ApplicableRuleOutcome.PASS,
            report_digest="4" * 64,
            detail="I2C role and rail rules passed",
        ),
    )
    decision = evaluate_admission(_request(
        claims=claims,
        rules=rules,
        constraints=_constraints(pin_count=4),
    ))

    assert decision.admitted
    assert decision.component_spec is not None
    assert decision.component_spec.interfaces == ["i2c"]
    assert decision.component_spec.i2c_addresses[0].address == 0x48
    assert decision.component_spec.rail("VDD").operating.maximum.value == 3.6


def test_missing_required_fact_blocks_even_when_every_report_passes():
    decision = evaluate_admission(_request(claims=_claims(omit=frozenset({"pin.2.roles"}))))

    assert not decision.admitted
    assert decision.component_spec is None
    assert any("pin.2.roles" in reason for reason in decision.reasons)
    result = next(item for item in decision.required_facts if item.fact_id == "pin.2.roles")
    assert not result.present


@pytest.mark.parametrize(
    "outcome",
    [ApplicableRuleOutcome.FAIL, ApplicableRuleOutcome.UNKNOWN,
     ApplicableRuleOutcome.NOT_APPLICABLE],
)
def test_every_applicable_rule_must_explicitly_pass(outcome: ApplicableRuleOutcome):
    decision = evaluate_admission(_request(rules=_rules({"assets.native": outcome})))
    assert not decision.admitted
    assert f"applicable rule assets.native is {outcome.value}" in decision.reasons


def test_missing_and_extra_failed_applicable_rules_both_block():
    missing = tuple(item for item in _rules() if item.rule_id != "assets.native")
    decision = evaluate_admission(_request(rules=missing))
    assert "applicable rule assets.native was not evaluated" in decision.reasons

    extra = _rules() + (
        ApplicableRuleResult(
            rule_id="manufacturing.optional-check",
            outcome=ApplicableRuleOutcome.UNKNOWN,
            report_digest="5" * 64,
            detail="an applicable optional check could not complete",
        ),
    )
    decision = evaluate_admission(_request(rules=extra))
    assert "applicable rule manufacturing.optional-check is unknown" in decision.reasons


def test_unsupported_behaviour_blocks_requested_capability():
    decision = evaluate_admission(_request(claims=_claims(profile=ElectricalProfile.UNSUPPORTED)))
    assert not decision.admitted
    assert not decision.capabilities.supports(Capability.ELECTRICAL_PROFILE)
    assert any("unsupported" in reason for reason in decision.reasons)


def test_changed_checked_fact_cannot_reuse_its_receipt():
    claims = _claims()
    changed = claims.facts[0].model_copy(update={"value": "Changed"})
    with pytest.raises(ValidationError, match="changed after checking"):
        claims.model_copy(update={"facts": (changed, *claims.facts[1:])}).model_dump()
        CheckedElectricalClaims.model_validate({
            **claims.model_dump(mode="json"),
            "facts": [changed.model_dump(mode="json"), *[
                item.model_dump(mode="json") for item in claims.facts[1:]
            ]],
        })


def test_non_electrical_checker_cannot_author_electrical_facts():
    claims = _claims()
    receipt = claims.receipts[0].model_copy(update={"checker": "CS-SOURCE"})
    payload = claims.model_dump(mode="json")
    payload["receipts"][0] = receipt.model_dump(mode="json")
    with pytest.raises(ValidationError, match="non-electrical checker"):
        CheckedElectricalClaims.model_validate(payload)


def test_electrical_identity_must_match_verified_package_identity():
    claims = _claims(overrides={"component.manufacturer": "Other"})
    decision = evaluate_admission(_request(claims=claims))
    assert not decision.admitted
    assert any("identity differs" in reason for reason in decision.reasons)


def test_seed_catalog_is_unchanged_and_keeps_catalog_evidence():
    before = [part.model_dump(mode="json") for part in default_catalog().all_parts()]
    evaluate_admission(_request())
    after = [part.model_dump(mode="json") for part in default_catalog().all_parts()]
    assert after == before


def test_only_passing_decision_enables_active_discovery(tmp_path: Path):
    store = ComponentStore(tmp_path / "catalog.sqlite3", tmp_path / "blobs")
    asset = store.commit_blob(b"footprint")
    revision = store.publish_quarantined(
        idempotency_key="admit",
        component_key="Acme:R100-0603:0603",
        record={"kind": "component"},
        assets=(BlobReference("footprint", asset),),
        reports=(),
    )
    request = _request(
        revision_id=revision.revision_id,
        publication_digest=revision.publication_digest,
    )
    failed_request = request.model_copy(update={
        "applicable_rules": _rules({"assets.geometry": ApplicableRuleOutcome.FAIL})
    })
    with pytest.raises(ActivationDisabledError, match="did not pass"):
        store.activate(failed_request)
    assert store.discover_active() == ()

    active = store.activate(request)
    assert store.activate(request) == active
    assert active.revision_id == revision.revision_id
    assert active.state == "ACTIVE"
    assert store.discover_active() == (active,)

    reopened = ComponentStore(store.database_path, store.blob_root)
    assert reopened.discover_active() == (active,)

    reopened.revoke(revision.revision_id, "source superseded")
    assert reopened.discover_active() == ()


def test_decision_for_other_publication_cannot_activate(tmp_path: Path):
    store = ComponentStore(tmp_path / "catalog.sqlite3", tmp_path / "blobs")
    asset = store.commit_blob(b"footprint")
    revision = store.publish_quarantined(
        idempotency_key="wrong-publication",
        component_key="Acme:R100-0603:0603",
        record={"kind": "component"},
        assets=(BlobReference("footprint", asset),),
        reports=(),
    )
    request = _request(revision_id=revision.revision_id)
    with pytest.raises(ComponentStoreError, match="different publication"):
        store.activate(request)


def test_existing_v2_database_migrates_to_activation_schema(tmp_path: Path):
    path = tmp_path / "catalog.sqlite3"
    with sqlite3.connect(path) as db:
        _apply_migrations(db, _MIGRATIONS[:2])
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    ComponentStore(path, tmp_path / "blobs")
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == LATEST_SCHEMA_VERSION
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE name='component_activations'"
        ).fetchone() == ("component_activations",)
