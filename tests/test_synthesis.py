"""M10-T01 acceptance tests for bounded deterministic A1 synthesis."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ohmni.catalog import default_catalog
from ohmni.domain import SafetyDomain
from ohmni.fixtures.esp32_env_logger import golden
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    InputPower,
    RefusalCode,
    SynthesisBrief,
    synthesize_a1,
)
from ohmni.verifier import verify


def _accepted(brief: SynthesisBrief | None = None):
    result = synthesize_a1(brief or SynthesisBrief())
    assert result.accepted, result.refusal
    assert result.circuit is not None
    assert result.requirements is not None
    return result


def test_default_a1_is_catalog_derived_and_semantically_exportable():
    result = _accepted()

    assert result.circuit is not None
    assert [component.ref for component in result.circuit.components] == [
        "J1", "R1", "R2", "U2", "C1", "C2", "U1", "C3", "C4", "R3",
        "C5", "U3", "C6", "C7", "R4", "R5", "D1", "R6", "J2",
    ]
    report = verify(result.circuit, default_catalog(), result.requirements)
    assert not report.blocking_findings
    assert result.circuit.content_hash == golden().content_hash


def test_identical_briefs_produce_identical_results_and_circuit_hashes():
    first = _accepted(SynthesisBrief())
    second = _accepted(SynthesisBrief())

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.brief_fingerprint == second.brief_fingerprint
    assert first.circuit is not None and second.circuit is not None
    assert first.circuit.content_hash == second.circuit.content_hash


def test_meaningful_slot_change_changes_hash_and_remains_semantically_clean():
    with_led = _accepted(SynthesisBrief(status_led_count=1))
    without_led = _accepted(SynthesisBrief(status_led_count=0))

    assert with_led.circuit is not None and without_led.circuit is not None
    assert with_led.circuit.content_hash != without_led.circuit.content_hash
    assert without_led.circuit.component("D1") is None
    report = verify(without_led.circuit, default_catalog(), without_led.requirements)
    assert not report.blocking_findings


def test_programming_header_is_a_real_optional_slot():
    with_header = _accepted(SynthesisBrief(include_programming_header=True))
    without_header = _accepted(SynthesisBrief(include_programming_header=False))

    assert with_header.circuit is not None and without_header.circuit is not None
    assert with_header.circuit.content_hash != without_header.circuit.content_hash
    assert without_header.circuit.component("J2") is None
    assert without_header.circuit.net("UART_TX") is None
    report = verify(without_header.circuit, default_catalog(), without_header.requirements)
    assert not report.blocking_findings


def test_catalog_address_option_changes_strap_topology():
    result = _accepted(
        SynthesisBrief(sensors=(I2cSensorSlot(part_id="BME280", address=0x77),))
    )

    assert result.circuit is not None
    sensor = result.circuit.component("U3")
    logic = result.circuit.net("3V3")
    ground = result.circuit.net("GND")
    assert sensor is not None and sensor.selected_i2c_address == 0x77
    assert logic is not None and logic.has("U3", "5")
    assert ground is not None and not ground.has("U3", "5")
    report = verify(result.circuit, default_catalog(), result.requirements)
    assert not report.blocking_findings


def test_safety_scope_is_refused_with_stable_code():
    result = synthesize_a1(SynthesisBrief(safety_domains=(SafetyDomain.MAINS,)))

    assert not result.accepted
    assert result.refusal is not None
    assert result.refusal.code is RefusalCode.SAFETY_DOMAIN_UNSUPPORTED
    assert result.refusal.field_paths == ("safety_domains",)


def test_mains_power_is_refused_as_a_safety_domain_even_without_an_extra_tag():
    result = synthesize_a1(SynthesisBrief(input_power=InputPower.MAINS))

    assert result.refusal is not None
    assert result.refusal.code is RefusalCode.SAFETY_DOMAIN_UNSUPPORTED


def test_brief_schema_rejects_unknown_fields_instead_of_ignoring_them():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SynthesisBrief.model_validate({"project_name": "node", "mystery_option": True})


def test_valid_but_unsupported_briefs_return_typed_refusals():
    cases = [
        (
            SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER),
            RefusalCode.ARCHETYPE_NOT_IMPLEMENTED,
        ),
        (SynthesisBrief(input_power=InputPower.BATTERY), RefusalCode.INPUT_POWER_UNSUPPORTED),
        (SynthesisBrief(input_voltage_v=9.0), RefusalCode.INPUT_VOLTAGE_UNSUPPORTED),
        (SynthesisBrief(logic_voltage_v=5.0), RefusalCode.LOGIC_VOLTAGE_UNSUPPORTED),
        (SynthesisBrief(sensors=()), RefusalCode.SENSOR_COUNT_UNSUPPORTED),
        (SynthesisBrief(status_led_count=2), RefusalCode.STATUS_LED_COUNT_UNSUPPORTED),
        (
            SynthesisBrief(sensors=(I2cSensorSlot(part_id="NOT_A_REAL_SENSOR"),)),
            RefusalCode.SENSOR_UNAVAILABLE,
        ),
        (
            SynthesisBrief(sensors=(I2cSensorSlot(part_id="BME280", address=0x40),)),
            RefusalCode.SENSOR_ADDRESS_UNAVAILABLE,
        ),
    ]

    for brief, expected in cases:
        result = synthesize_a1(brief)
        assert not result.accepted
        assert result.refusal is not None
        assert result.refusal.code is expected


def test_led_resistor_is_calculated_from_catalog_limits_and_rounded_to_e12():
    result = _accepted()
    assert result.circuit is not None
    resistor = result.circuit.component("R6")
    assert resistor is not None and resistor.value is not None
    assert resistor.value == resistor.value.ohms(330)
