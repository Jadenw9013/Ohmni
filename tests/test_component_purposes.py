"""Instructional explanations must follow pin roles and actual connections."""

import pytest

from ohmni.application.product import _purpose
from ohmni.application.systems import group_components
from ohmni.domain.circuit import PinRef


def purpose(circuit, catalog, ref):
    grouping = next(item for item in group_components(circuit, catalog, {})
                    if item.component_ref == ref)
    return _purpose(circuit, catalog, ref, grouping)


@pytest.mark.parametrize("ref", ["R1", "R2"])
def test_usb_cc_explanation_uses_connector_pin_role_even_after_renaming(golden, catalog, ref):
    for index, net in enumerate(golden.nets):
        net.name = f"connection_{index}"
    text = purpose(golden, catalog, ref)
    assert "USB-C configuration" in text and "sink-identification" in text
    assert "limit" not in text.lower()


def test_a_connector_signal_name_does_not_establish_a_usb_cc_role(golden, catalog):
    net = golden.net("CC1")
    net.connections = [PinRef(component="J1", pin="A8"), PinRef(component="R1", pin="1")]
    text = purpose(golden, catalog, "R1")
    assert "pull-down" in text and "USB-C" not in text


@pytest.mark.parametrize("ref", ["R3", "R4", "R5"])
def test_signal_to_supply_resistors_are_explained_as_pullups(golden, catalog, ref):
    text = purpose(golden, catalog, ref)
    assert "pull-up" in text and "supply" in text
    assert "never" not in text  # The explanation is not an electrical pass claim.


def test_signal_to_ground_resistor_is_explained_as_a_pulldown(golden, catalog):
    rail = golden.net("3V3")
    terminal = next(pin for pin in rail.connections if pin.component == "R3")
    rail.connections.remove(terminal)
    golden.net("GND").connections.append(terminal)
    assert "pull-down" in purpose(golden, catalog, "R3")


@pytest.mark.parametrize("power_side", [False, True])
def test_exclusive_led_series_connection_establishes_current_limiting(golden, catalog, power_side):
    if power_side:
        net = golden.net("LED_DRIVE")
        terminal = next(pin for pin in net.connections if pin.component == "R6")
        net.connections.remove(terminal)
        golden.net("3V3").connections.append(terminal)
    text = purpose(golden, catalog, "R6")
    assert "series with the indicator light" in text and "limit its current" in text
    assert "pull-up" not in text


def test_sharing_an_led_net_does_not_establish_an_exclusive_series_role(golden, catalog):
    net = golden.net("IO0")
    terminal = next(pin for pin in net.connections if pin.component == "J2")
    net.connections.remove(terminal)
    golden.net("LED_A").connections.append(terminal)
    assert "limit its current" not in purpose(golden, catalog, "R6")


def test_a_resistor_with_an_unconnected_terminal_has_no_inferred_role(golden, catalog):
    net = golden.net("3V3")
    net.connections = [pin for pin in net.connections if pin.component != "R4"]
    text = purpose(golden, catalog, "R4")
    assert text == "A 4.7 kohm resistor."


def test_signal_capacitor_does_not_get_an_invented_timing_purpose(golden, catalog):
    text = purpose(golden, catalog, "C5")
    assert "stores electrical charge" in text
    assert "timing" not in text and "delay" not in text


def test_sensor_readings_go_to_a_processor_not_the_bus_resistors(golden, catalog):
    text = purpose(golden, catalog, "U3")
    assert "I2C data and clock" in text and "main computer" in text
    assert "resistor" not in text


@pytest.mark.parametrize("alteration", ["no_processor", "missing_clock", "shorted_lines", "no_mode"])
def test_incomplete_or_unselected_sensor_bus_does_not_claim_a_complete_i2c_link(
    golden, catalog, alteration,
):
    if alteration == "no_processor":
        for name in ("SDA", "SCL"):
            net = golden.net(name)
            net.connections = [pin for pin in net.connections if pin.component != "U1"]
    elif alteration == "missing_clock":
        net = golden.net("SCL")
        net.connections = [pin for pin in net.connections if pin.component != "U3"]
    elif alteration == "shorted_lines":
        clock = golden.net("SCL")
        golden.net("SDA").connections.extend(clock.connections)
        golden.nets.remove(clock)
    else:
        golden.component("U3").selected_interfaces = []
    text = purpose(golden, catalog, "U3")
    assert "I2C data and clock" not in text and "resistor" not in text
    if alteration == "no_processor":
        assert "main computer" not in text


def test_programming_header_explanation_requires_serial_and_boot_connections(golden, catalog):
    assert "external programming adapter" in purpose(golden, catalog, "J2")
    for net in golden.nets:
        if net.name not in {"3V3", "GND"}:
            net.connections = [pin for pin in net.connections if pin.component != "J2"]
    text = purpose(golden, catalog, "J2")
    assert "programming" not in text and "external cable or accessory" in text


def test_connector_is_not_always_a_power_input(golden, catalog):
    golden.net("VBUS").external_source = None
    assert "external cable or accessory" in purpose(golden, catalog, "J1")
