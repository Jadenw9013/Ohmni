"""Mutation tests for the silent electrical failures most likely in this demo."""
import json
from pathlib import Path

import pytest

from ohmni.catalog import default_catalog
from ohmni.domain.circuit import PinRef
from ohmni.domain.component import PinRole
from ohmni.domain.units import Quantity
from tools.landing_controller.checks import check_design
from tools.landing_controller.design import build_design


def failed(design):
    return {f["id"] for f in check_design(design.circuit, design.catalog)["topology_checks"]
            if f["status"] == "FAIL"}


def move(design, ref, pin, new_net):
    for net in design.circuit.nets:
        net.connections = [p for p in net.connections if (p.component, p.pin) != (ref, str(pin))]
    if new_net:
        design.circuit.net(new_net).connections.append(PinRef(component=ref, pin=str(pin)))


def test_real_parts_deterministic_and_no_scope_upgrade():
    original = {p.part_id: p.model_dump_json() for p in default_catalog().all_parts()}
    first, second = build_design(), build_design()
    assert first.circuit.content_hash == second.circuit.content_hash
    assert len(first.circuit.components) == 69
    assert not failed(first)
    report = check_design(first.circuit, first.catalog)
    assert report["status"] == "SCOPED_CHECKS_PASS_SYSTEM_UNKNOWN"
    assert report["system_status"] == "UNKNOWN"
    assert not report["bench_run"] and not report["manufacturing_ready"]
    assert all(first.catalog.require(c.part_id).mpn and not first.catalog.require(c.part_id).is_generic
               for c in first.circuit.components)
    first.catalog.require("AP2112K-3.3TRG1").description = "local mutation"
    assert {p.part_id: p.model_dump_json() for p in default_catalog().all_parts()} == original


def test_research_connected_pin_map_matches_authored_circuit():
    research = json.loads((Path(__file__).resolve().parents[1] /
                           "examples/landing-controller/research.json").read_text(encoding="utf-8"))
    actual = {}
    for net in build_design().circuit.nets:
        for pin in net.connections:
            actual.setdefault(pin.component, {})[pin.pin] = net.name
    assert research["connected_pin_map"] == actual


@pytest.mark.parametrize("pin", [6, 10, 11, 19, 20, 21, 22, 27, 28, 49, 50, 74, 75, 99, 100])
def test_every_mcu_supply_or_reference_pin_required(pin):
    design = build_design()
    move(design, "U1", pin, None)
    assert "MCU_SUPPLY_PINS" in failed(design)


@pytest.mark.parametrize("pin", [12, 13, 73])
def test_clock_and_nc_pins_not_falsely_connected(pin):
    design = build_design()
    move(design, "U1", pin, "GND")
    assert "MCU_NC_AND_INTERNAL_CLOCK" in failed(design)


def test_top_view_pin_identity_swap_is_caught():
    design = build_design()
    mcu = design.catalog.require("STM32F103VBT6")
    mcu.pin("1").name, mcu.pin("100").name = mcu.pin("100").name, mcu.pin("1").name
    assert "MCU_PINOUT" in failed(design)


@pytest.mark.parametrize("index", range(16))
def test_each_led_polarity_and_series_path(index):
    design = build_design()
    move(design, f"D{index+1}", 1, f"LED{index}_ANODE")
    move(design, f"D{index+1}", 2, "GND")
    assert f"LED_{index}_CHANNEL" in failed(design)


def test_led_model_binding_cannot_inherit_generic_anode_permutation():
    design = build_design()
    led = design.catalog.require("APT1608SGC")
    led.packages = [led.packages[0].model_copy(update={"catalog_pin_to_pad": {"1": "2", "2": "1"}})]
    assert all(f"LED_{i}_CHANNEL" in failed(design) for i in range(16))
    assert led.pin("1").roles == [PinRole.CATHODE]


def test_wrong_parallel_carry_is_not_serial_cascade():
    design = build_design()
    move(design, "U4", 9, None)
    move(design, "U4", 7, "SR_CHAIN")
    assert "SHIFT_CASCADE" in failed(design)


@pytest.mark.parametrize("ref", ["R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12"])
def test_idle_and_boot_pulls_cannot_be_omitted(ref):
    design = build_design()
    move(design, ref, 2, None)
    assert "BOOT_AND_IDLE_PULLS" in failed(design)


@pytest.mark.parametrize("ref", [f"C{i}" for i in range(1, 16)])
def test_each_decoupler_or_reset_cap_required(ref):
    design = build_design()
    next(p for p in design.circuit.components if p.ref == ref).value = Quantity.farads(1e-12)
    assert "DECOUPLING_AND_RESET_CAPS" in failed(design)


def test_header_swap_or_usb_data_repurpose_detected():
    design = build_design()
    move(design, "J2", 3, "GND")
    move(design, "J1", "A6", "SPI_MOSI")
    assert {"HEADER_36_GPIO", "USB_POWER_ONLY"} <= failed(design)


def test_eeprom_hold_and_ap2112_pinout_are_not_optional():
    design = build_design()
    move(design, "U3", 7, "GND")
    move(design, "U2", 3, "3V3")
    assert {"EEPROM_SPI", "LDO_PINOUT"} <= failed(design)
