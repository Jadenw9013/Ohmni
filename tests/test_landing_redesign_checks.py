"""Mutation tests for the deliberately scoped landing-board topology checks."""

from __future__ import annotations

import json
from math import nan

import pytest

from ohmni.domain.circuit import PinRef
from ohmni.domain.units import Quantity, Unit
from tools.landing_redesign.checks import check_design, feedback_voltage_bounds
from tools.landing_redesign.design import build_design


def move_pin(circuit, ref: str, pin: str, target: str) -> None:
    for net in circuit.nets:
        net.connections = [p for p in net.connections if (p.component, p.pin) != (ref, pin)]
    circuit.net(target).connections.append(PinRef(component=ref, pin=pin))


def drop(circuit, ref: str) -> None:
    circuit.components = [part for part in circuit.components if part.ref != ref]
    for net in circuit.nets:
        net.connections = [p for p in net.connections if p.component != ref]


def evaluate(design, variant: bool = False):
    return check_design(design.circuit, design.catalog, include_i2c_extension=variant)


def failed(report):
    return {item["id"] for item in report["topology_checks"] if item["status"] == "FAIL"}


@pytest.mark.parametrize("variant", [False, True])
def test_correct_topology_never_claims_system_or_manufacturing_pass(variant):
    design = build_design(variant)
    before = design.circuit.model_dump_json()
    report = evaluate(design, variant)
    assert report["failed_checks"] == 0, failed(report)
    assert report["status"] == "SCOPED_CHECKS_PASS_SYSTEM_UNKNOWN"
    assert report["system_status"] == "UNKNOWN"
    assert report["manufacturing_ready"] is False
    assert report["bench_run"] is False
    assert report["board_current_capability_A"] is None
    assert all(item["status"] == "UNKNOWN" for item in report["remaining_checks"])
    assert "USB_CURRENT_ENTITLEMENT" in {item["id"] for item in report["remaining_checks"]}
    assert design.circuit.model_dump_json() == before
    assert json.loads(json.dumps(report)) == report
    assert evaluate(design, variant) == report


def test_attachment_sw_and_vin_swap_is_detected():
    design = build_design()
    move_pin(design.circuit, "U2", "3", "VBUS")
    move_pin(design.circuit, "U2", "4", "SW_NODE")
    report = evaluate(design)
    assert {"BUCK_PIN_NETS", "BUCK_OUTPUT_FILTER"} <= failed(report)
    assert report["calculations"]["feedback"] is None


@pytest.mark.parametrize("variant,ref,first,second,expected", [
    (False, "U2", "1", "3", "BUCK_CATALOG_PINOUT"),
    (True, "U4", "3", "4", "PCA_CATALOG_PINOUT"),
])
def test_catalog_pin_name_swap_cannot_pass_with_unchanged_wires(
    variant, ref, first, second, expected
):
    design = build_design(variant)
    part_id = design.circuit.component(ref).part_id
    altered = design.catalog.get(part_id).model_copy(deep=True)
    altered.pin(first).name, altered.pin(second).name = (
        altered.pin(second).name, altered.pin(first).name
    )

    class AlteredCatalog:
        def get(self, requested):
            return altered if requested == part_id else design.catalog.get(requested)

    report = check_design(design.circuit, AlteredCatalog(), include_i2c_extension=variant)
    assert expected in failed(report)


@pytest.mark.parametrize("ref,expected", [
    ("L1", "BUCK_OUTPUT_FILTER"),
    ("C1", "BUCK_FILTER_CAPACITORS"),
    ("C2", "BUCK_FILTER_CAPACITORS"),
    ("R6", "BUCK_FEEDBACK_DIVIDER"),
    ("R7", "BUCK_FEEDBACK_DIVIDER"),
    ("C3", "ESP32_SUPPLY_DECOUPLING"),
    ("C4", "ESP32_SUPPLY_DECOUPLING"),
    ("C5", "ESP32_ENABLE_RC"),
    ("R1", "USB_SEPARATE_CC_RD"),
    ("R2", "USB_SEPARATE_CC_RD"),
])
def test_missing_required_support_part_fails(ref, expected):
    design = build_design()
    drop(design.circuit, ref)
    assert expected in failed(evaluate(design))


def test_feedback_short_to_input_is_detected_without_dc_calculation():
    design = build_design()
    move_pin(design.circuit, "R6", "1", "VBUS")
    report = evaluate(design)
    assert "BUCK_FEEDBACK_DIVIDER" in failed(report)
    assert report["calculations"]["feedback"] is None


def test_feedback_wrong_value_and_wrong_unit_fail():
    for value in (Quantity(value=453, unit=Unit.OHM), Quantity(value=453000, unit=Unit.FARAD)):
        design = build_design()
        design.circuit.component("R6").value = value
        assert "BUCK_FEEDBACK_DIVIDER" in failed(evaluate(design))


@pytest.mark.parametrize("ref,pin", [("R4", "2"), ("R5", "2"), ("U3", "6")])
def test_low_side_5v_feed_is_detected(ref, pin):
    design = build_design(True)
    move_pin(design.circuit, ref, pin, "VBUS")
    report = evaluate(design, True)
    expected = "SENSOR_LOW_VOLTAGE_DOMAIN" if ref == "U3" else "LOW_I2C_PULLUPS"
    assert expected in failed(report)
    if ref != "U3":
        assert "I2C_RESISTIVE_DOMAIN_ISOLATION" in failed(report)


def test_extra_high_rail_pullup_is_not_hidden_by_correct_original_pullups():
    design = build_design(True)
    move_pin(design.circuit, "R8", "1", "SDA_3V3")
    report = evaluate(design, True)
    assert "LOW_I2C_PULLUPS" not in failed(report)
    assert "I2C_RESISTIVE_DOMAIN_ISOLATION" in failed(report)


@pytest.mark.parametrize("ref,pin,target,expected", [
    ("U4", "3", "SDA_3V3", "PCA_DOMAIN_PINOUT"),
    ("U4", "7", "VBUS", "PCA_DOMAIN_PINOUT"),
    ("U4", "8", "VBUS", "PCA_DOMAIN_PINOUT"),
    ("R14", "1", "3V3", "PCA_BIAS_NETWORK"),
    ("R9", "2", "3V3", "HIGH_I2C_PULLUPS"),
    ("J3", "2", "3V3", "I2C_EXTENSION_HEADER"),
    ("J1", "A6", "SDA_5V", "USB_POWER_ONLY"),
])
def test_translator_and_connector_wiring_errors(ref, pin, target, expected):
    design = build_design(True)
    move_pin(design.circuit, ref, pin, target)
    assert expected in failed(evaluate(design, True))


def test_missing_translator_cannot_be_mistaken_for_base_variant():
    design = build_design(True)
    drop(design.circuit, "U4")
    assert "PCA_DOMAIN_PINOUT" in failed(evaluate(design, True))


def test_unrequested_extension_is_not_silently_accepted():
    assert "NO_UNREQUESTED_I2C_EXTENSION" in failed(evaluate(build_design(True)))


def test_current_rating_does_not_become_usb_entitlement():
    design = build_design()
    design.circuit.net("VBUS").external_source.current_limit = Quantity.amps(2)
    report = evaluate(design)
    assert "USB_CURRENT_NOT_INFERRED" in failed(report)
    assert report["board_current_capability_A"] is None


def test_ic_minimum_input_does_not_imply_step_up_operation():
    design = build_design()
    source = design.circuit.net("VBUS").external_source
    source.voltage = source.voltage.model_copy(update={"minimum": Quantity.volts(2.5)})
    assert "BUCK_INPUT_DESIGN_RANGE" in failed(evaluate(design))


def test_duplicate_net_membership_is_rejected_even_after_mutating_valid_ir():
    design = build_design()
    design.circuit.net("VBUS").connections.append(PinRef(component="U1", pin="2"))
    assert "IR_PIN_MEMBERSHIP" in failed(evaluate(design))


def test_divider_has_bounded_conditional_tolerance_and_honest_nominal():
    result = feedback_voltage_bounds(453000, 100000)
    assert result["nominal_V"] == pytest.approx(3.318)
    assert result["minimum_V"] == pytest.approx(0.588 * (1 + 453000 * .99 / 101000))
    assert result["maximum_V"] == pytest.approx(0.612 * (1 + 453000 * 1.01 / 99000))
    assert result["minimum_V"] < result["nominal_V"] < result["maximum_V"]
    assert result["status"] == "CONDITIONAL_CALCULATION"
    assert result["tolerance_status"] == "BOM_REQUIREMENT_NOT_COMPONENT_VERIFIED"


@pytest.mark.parametrize("upper,lower,tolerance", [
    (0, 100000, .01), (453000, 0, .01), (453000, 100000, -1),
    (453000, 100000, 1), (nan, 100000, .01),
])
def test_invalid_divider_values_do_not_create_plausible_numbers(upper, lower, tolerance):
    with pytest.raises(ValueError):
        feedback_voltage_bounds(upper, lower, tolerance)
