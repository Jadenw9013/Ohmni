"""CS-T10 source-bound LM317/DCY admission, design and model checks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ohmni.catalog.lm317 import lm317_asset_record, lm317_limits, lm317_record
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
from ohmni.domain.adjustable_regulator import (
    AdjustableRegulatorDesign,
    FeedbackNetwork,
    RegulatorFindingCode,
    verify_adjustable_regulator,
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
from ohmni.eda.kicad.component_asset_parser import measure_footprint
from ohmni.eda.kicad.reusable_asset_library import asset_mutation_errors, compile_asset
from ohmni.eda.vendor_model_runner import run_lm317_vendor_model


def test_source_record_pins_tab_limits_and_vendor_hashes_are_explicit():
    record = lm317_record()
    assert record["pins"] == {
        "1": "ADJUST",
        "2": "OUTPUT",
        "3": "INPUT",
        "4": "OUTPUT_TAB",
    }
    assert record["source"]["pin_mapping_page"] == 5
    assert record["source"]["land_pattern_page"] == 36
    assert record["vendor_model"]["dialect"] == "pspice"
    assert record["vendor_model"]["ports"] == ["IN", "ADJ", "OUT_0", "OUT_1"]


def test_sot223_asset_is_a_data_row_with_source_drawn_tab_geometry():
    record = lm317_asset_record()
    compiled = compile_asset(record)
    measured = measure_footprint(compiled.footprint_text)
    assert asset_mutation_errors(record, compiled.footprint_text) == ()
    assert measured.pad("1").centre_x_nm == -2_900_000
    assert measured.pad("3").centre_y_nm == -2_300_000
    assert measured.pad("4").centre_x_nm == 2_900_000
    assert measured.pad("4").height_nm == 3_250_000


def valid_design(**changes):
    values = {
        "pin_nets": {"1": "adj", "2": "out", "3": "in", "4": "out"},
        "ground_net": "gnd",
        "input_voltage_v": 12.0,
        "load_current_a": 0.1,
        "divider": FeedbackNetwork(
            r1_ohm=240,
            r2_ohm=720,
            r1_from="out",
            r1_to="adj",
            r2_from="adj",
            r2_to="gnd",
        ),
    }
    values.update(changes)
    return AdjustableRegulatorDesign(**values)


def test_adjustable_feedback_keeps_the_sourced_adjust_current_term():
    result = verify_adjustable_regulator(valid_design(), lm317_limits())
    assert result.passed
    assert result.output_voltage_v == pytest.approx(5.036)


def test_incorrect_divider_and_tab_mapping_fail_independently():
    reversed_divider = valid_design().divider.model_copy(
        update={"r1_from": "adj", "r1_to": "out"}
    )
    result = verify_adjustable_regulator(valid_design(divider=reversed_divider), lm317_limits())
    assert RegulatorFindingCode.DIVIDER_TOPOLOGY in {item.code for item in result.findings}

    wrong_tab = valid_design(pin_nets={"1": "adj", "2": "out", "3": "in", "4": "gnd"})
    result = verify_adjustable_regulator(wrong_tab, lm317_limits())
    assert RegulatorFindingCode.TAB_NET in {item.code for item in result.findings}


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"input_voltage_v": 7.0}, RegulatorFindingCode.HEADROOM),
        ({"input_voltage_v": 50.0}, RegulatorFindingCode.HEADROOM),
        ({"load_current_a": 0.001}, RegulatorFindingCode.LOAD_CURRENT),
        ({"load_current_a": 2.0}, RegulatorFindingCode.LOAD_CURRENT),
    ],
)
def test_condition_incomplete_or_out_of_range_designs_fail(changes, code):
    result = verify_adjustable_regulator(valid_design(**changes), lm317_limits())
    assert code in {item.code for item in result.findings}


def _receipt(identifier: str, payload: dict, document: str) -> VerificationReceipt:
    return VerificationReceipt(
        receipt_id=identifier,
        checker="CS-SOURCE",
        checker_version=CHECKER_CONTRACT_VERSION,
        outcome=ReceiptOutcome.SUPPORTED,
        claim_hash=claim_hash(payload),
        document_digest=document,
        observation_digest="2" * 64,
    )


def _constraints() -> VerifiedConstraintSet:
    source = lm317_record()["source"]["sha256"]
    identity = VerifiedIdentity(
        manufacturer="Texas Instruments",
        base_device="LM317",
        orderable_part_number="LM317DCYR",
        package_code="DCY",
        package_description="SOT-223",
        pin_count=4,
        document_revision="SLVS044Z",
        drawing_number="DCY0004A",
        receipt_id="IDENTITY",
    )
    dimension = VerifiedDimension(
        kind=DimensionKind.LAND_PAD_WIDTH,
        dimension_symbol="X",
        limit=LimitColumn.BASIC,
        value=LengthValue.parse("2.15", SourceUnit.MILLIMETRE),
        basic_dimension=True,
        applies_to_terminals=4,
        receipt_id="DIMENSION",
    )
    terminals = tuple(
        VerifiedTerminal(
            package_column="DCY",
            pin_number=number,
            symbol=name,
            function=name,
            kind=TerminalKind.ELECTRICAL,
            receipt_id=f"PIN-{number}",
        )
        for number, name in lm317_record()["pins"].items()
    )
    ordering = VerifiedPadOrdering(
        traversal="counter_clockwise_from_pin_1",
        first_pin_corner="top_left",
        slots=(
            PadSlot(pin_number="1", row=0, column=0),
            PadSlot(pin_number="2", row=0, column=1),
            PadSlot(pin_number="3", row=0, column=2),
            PadSlot(pin_number="4", row=1, column=1),
        ),
        receipt_id="ORDERING",
    )
    claims = [(identity.receipt_id, identity.claim()), (dimension.receipt_id, dimension.claim())]
    claims.extend((item.receipt_id, item.claim()) for item in terminals)
    claims.append((ordering.receipt_id, ordering.claim()))
    verified = VerifiedConstraintSet(
        document_digest=source,
        observation_digest="2" * 64,
        identity=identity,
        dimensions=(dimension,),
        terminals=terminals,
        pad_ordering=ordering,
        receipts=tuple(_receipt(identifier, payload, source) for identifier, payload in claims),
    )
    return verified


def test_verified_package_constraint_set_keeps_pin4_as_an_electrical_tab():
    verified = _constraints()
    assert verified.revalidate() == ()
    assert next(item for item in verified.terminals if item.pin_number == "4").kind is (
        TerminalKind.ELECTRICAL
    )


def _lm317_claims() -> CheckedElectricalClaims:
    values = {
        "component.manufacturer": "Texas Instruments",
        "component.mpn": "LM317DCYR",
        "component.category": ComponentCategory.REGULATOR_LINEAR.value,
        "component.description": "Adjustable linear regulator",
        "package.name": "DCY",
        "pin.1.name": "ADJUST",
        "pin.1.roles": (PinRole.ADJUST.value,),
        "pin.1.electrical_type": PinElectricalType.INPUT.value,
        "pin.2.name": "OUTPUT",
        "pin.2.roles": (PinRole.POWER.value,),
        "pin.2.electrical_type": PinElectricalType.POWER_OUT.value,
        "pin.3.name": "INPUT",
        "pin.3.roles": (PinRole.POWER.value,),
        "pin.3.electrical_type": PinElectricalType.POWER_IN.value,
        "pin.4.name": "OUTPUT_TAB",
        "pin.4.roles": (PinRole.POWER.value,),
        "pin.4.electrical_type": PinElectricalType.POWER_OUT.value,
        "regulator.reference_voltage": "1.25V",
        "regulator.adjust_current_typical": "50uA",
        "regulator.output_minimum": "1.25V",
        "regulator.output_maximum": "37V",
        "regulator.differential_minimum": "3V",
        "regulator.differential_maximum": "40V",
        "regulator.load_minimum": "10mA",
        "regulator.load_maximum": "1.5A",
        "package.tab_pin": "4",
        "package.tab_role": "output",
    }
    facts = tuple(
        CheckedElectricalFact(fact_id=fact_id, value=value, receipt_id=f"E-{index}")
        for index, (fact_id, value) in enumerate(sorted(values.items()))
    )
    source = lm317_record()["source"]["sha256"]
    receipts = tuple(
        VerificationReceipt(
            receipt_id=fact.receipt_id,
            checker="CS-ELECTRICAL",
            checker_version=CHECKER_CONTRACT_VERSION,
            outcome=ReceiptOutcome.SUPPORTED,
            claim_hash=claim_hash(fact.claim()),
            document_digest=source,
            observation_digest="2" * 64,
        )
        for fact in facts
    )
    return CheckedElectricalClaims(
        document_digest=source,
        observation_digest="2" * 64,
        profile=ElectricalProfile.ADJUSTABLE_LINEAR_REGULATOR,
        facts=facts,
        receipts=receipts,
    )


def _admission_rules(tab_outcome=ApplicableRuleOutcome.PASS):
    outcomes = {
        "source.constraints": ApplicableRuleOutcome.PASS,
        "assets.geometry": ApplicableRuleOutcome.PASS,
        "assets.native": ApplicableRuleOutcome.PASS,
        "electrical.adjustable_regulator": ApplicableRuleOutcome.PASS,
        "package.tab_output": tab_outcome,
    }
    return tuple(
        ApplicableRuleResult(
            rule_id=rule_id,
            outcome=outcome,
            report_digest=claim_hash({"rule": rule_id, "outcome": outcome.value}),
            detail=f"{rule_id} evaluated {outcome.value}",
        )
        for rule_id, outcome in sorted(outcomes.items())
    )


def test_lm317_is_admitted_only_with_adjustable_profile_and_tab_rule_pass():
    request = AdmissionRequest(
        revision_id="a" * 32,
        publication_digest="3" * 64,
        constraints=_constraints(),
        electrical=_lm317_claims(),
        applicable_rules=_admission_rules(),
        requested_capabilities=(Capability.ELECTRICAL_PROFILE, Capability.ROUTING),
    )
    decision = evaluate_admission(request)
    assert decision.admitted, decision.reasons
    assert decision.component_spec is not None
    assert decision.component_spec.pin("1").roles == [PinRole.ADJUST]
    assert decision.component_spec.pin("4").name == "OUTPUT_TAB"

    rejected = evaluate_admission(
        request.model_copy(update={"applicable_rules": _admission_rules(ApplicableRuleOutcome.FAIL)})
    )
    assert not rejected.admitted
    assert "applicable rule package.tab_output is fail" in rejected.reasons


MODEL_PATH = os.environ.get("OHMNI_LM317_MODEL")
NGSPICE = os.environ.get("OHMNI_NGSPICE")


@pytest.mark.simulation_integration
@pytest.mark.skipif(not MODEL_PATH or not NGSPICE, reason="exact TI model/ngspice paths not provided")
def test_exact_ti_vendor_model_runs_under_ngspice_42(tmp_path: Path):
    model = Path(MODEL_PATH).read_bytes()
    expected = lm317_record()["vendor_model"]["file_sha256"]
    result = run_lm317_vendor_model(NGSPICE, model, expected, tmp_path)
    assert result.status == "compatible", result.detail
    assert result.output_voltage_v == pytest.approx(5.005542, abs=1e-6)
    assert result.adjust_voltage_v == pytest.approx(3.754157, abs=1e-6)


def test_vendor_model_hash_tampering_fails_before_process_launch(tmp_path: Path):
    with pytest.raises(ValueError, match="SHA-256"):
        run_lm317_vendor_model("never-run", b"changed", "0" * 64, tmp_path)
