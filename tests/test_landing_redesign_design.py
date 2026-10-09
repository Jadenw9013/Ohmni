"""Electrical identity, no false verification, and deterministic overlay boundaries."""

import pytest

from ohmni.catalog import default_catalog
from ohmni.domain.component import PinElectricalType, PinRole
from ohmni.domain.evidence import ClaimStatus
from ohmni.domain.units import Quantity
from tools.landing_redesign.catalog import ADDED_PART_IDS, redesign_catalog
from tools.landing_redesign.design import build_design


def _nodes(circuit, name):
    return {str(pin) for pin in circuit.net(name).connections}


def test_overlay_preserves_default_catalog_and_isolates_mutable_records():
    base = default_catalog()
    original = [part.model_dump(mode="json") for part in base.all_parts()]
    overlay = redesign_catalog()
    assert all(base.get(part_id) is None for part_id in ADDED_PART_IDS)
    assert all(overlay.get(part_id) is not None for part_id in ADDED_PART_IDS)
    overlay.require("ESP32-WROOM-32E").pins[0].name = "local mutation"
    overlay.require("GENERIC_LED_GREEN").packages.clear()
    assert [part.model_dump(mode="json") for part in base.all_parts()] == original
    assert redesign_catalog().require("ESP32-WROOM-32E").pins[0].name != "local mutation"


@pytest.mark.parametrize("extension,count", [(False, 32), (True, 38)])
def test_design_and_source_records_are_deterministic_and_pin_complete(extension, count):
    first, second = build_design(extension), build_design(extension)
    assert len(first.circuit.components) == count
    assert first.circuit.model_dump(mode="json") == second.circuit.model_dump(mode="json")
    assert first.requirements == second.requirements
    assert [p.model_dump(mode="json") for p in first.catalog.all_parts()] == [
        p.model_dump(mode="json") for p in second.catalog.all_parts()]
    assert first.circuit.parent_hash and first.circuit.parent_hash != first.circuit.content_hash
    for net in first.circuit.nets:
        for pin in net.connections:
            component = first.circuit.component(pin.component)
            assert first.catalog.require(component.part_id).pin(pin.pin) is not None


def test_switching_node_is_not_fabricated_as_dc_regulator_or_external_source():
    design = build_design()
    buck = design.catalog.require("TLV62569DBVR")
    assert buck.regulator is None
    assert buck.pin("3").name == "SW"
    assert buck.pin("3").electrical_type is PinElectricalType.OUTPUT
    assert PinRole.POWER not in buck.pin("3").roles
    assert design.circuit.net("3V3").external_source is None
    assert design.circuit.net("VBUS").external_source.current_limit is None
    assert design.catalog.require("ESP32-WROOM-32E").rail("VDD").current_max is None
    assert default_catalog().require("ESP32-WROOM-32E").rail("VDD").current_max == Quantity.amps(.5)
    assert _nodes(design.circuit, "SW_NODE") == {"U2.3", "L1.1"}
    assert _nodes(design.circuit, "FB_REFB") == {"U2.5", "R6.2", "R7.1"}
    assert {"U2.1", "U2.4"} <= _nodes(design.circuit, "VBUS")
    assert "U2.2" in _nodes(design.circuit, "GND")
    assert {"L1.2", "R6.1", "C2.1"} <= _nodes(design.circuit, "3V3")
    assert "R7.2" in _nodes(design.circuit, "GND")
    assert design.circuit.component("R6").value == Quantity.ohms(453_000)
    assert design.circuit.component("R7").value == Quantity.ohms(100_000)


def test_led_catalog_polarity_and_physical_permutation_are_both_preserved():
    design = build_design()
    led = design.catalog.require("GENERIC_LED_GREEN")
    assert led.pin("1").has_role(PinRole.ANODE)
    assert led.pin("2").has_role(PinRole.CATHODE)
    for index in range(1, 5):
        instance = design.circuit.component(f"D{index}")
        package = next(p for p in led.packages if p.name == instance.package)
        assert package.catalog_pin_to_pad == {"1": "2", "2": "1"}
        assert f"D{index}.1" in _nodes(design.circuit, f"LED{index}_A")
        assert f"D{index}.2" in _nodes(design.circuit, "GND")
        assert design.circuit.component(f"R{9+index}").value == Quantity.ohms(330)
    assert design.circuit.component("SW1") and design.circuit.component("SW2")
    assert design.circuit.component("J2").part_id == "HEADER_1X6_254"


def test_extension_uses_separate_header_and_proper_pass_fet_bias_without_5v_on_sensor():
    base, design = build_design(), build_design(True)
    circuit = design.circuit
    assert base.circuit.component("U4") is None and base.circuit.component("J3") is None
    assert circuit.content_hash != base.circuit.content_hash
    assert _nodes(circuit, "I2C_BIAS") == {"U4.7", "U4.8", "R14.2", "C8.1"}
    assert circuit.component("R14").value == Quantity.ohms(200_000)
    assert circuit.component("C8").value == Quantity.farads(100e-12)
    assert circuit.net_of("R14", "1").name == "VBUS"
    assert circuit.net_of("J3", "1").name == "GND"
    assert circuit.net_of("J3", "2").name == "VBUS"
    assert circuit.net_of("J3", "3").name == "SDA_5V"
    assert circuit.net_of("J3", "4").name == "SCL_5V"
    assert _nodes(circuit, "SDA_5V") == {"U4.5", "J3.3", "R8.1"}
    assert _nodes(circuit, "SCL_5V") == {"U4.6", "J3.4", "R9.1"}
    assert {"U1.33", "U3.3", "U4.4", "R4.1"} == _nodes(circuit, "SDA_3V3")
    assert {"U1.36", "U3.4", "U4.3", "R5.1"} == _nodes(circuit, "SCL_3V3")
    assert circuit.net_of("U3", "6").name == circuit.net_of("U3", "8").name == "3V3"
    assert not any(pin.component == "J1" for name in ("SDA_5V", "SCL_5V")
                   for pin in circuit.net(name).connections)
    assert any("100 kHz" in item for item in circuit.design_assumptions)
    assert any("backfeed" in item and "unverified" in item for item in circuit.design_assumptions)


def test_new_manufacturer_records_are_reported_not_machine_verified():
    catalog = redesign_catalog()
    for part_id in ADDED_PART_IDS[:-1]:
        part = catalog.require(part_id)
        assert part.datasheet.url.startswith("https://")
        assert part.evidence
        for evidence in part.evidence:
            assert evidence.status is ClaimStatus.CATALOG_REPORTED
            assert not evidence.provenance_machine_verified
            assert evidence.document.url and evidence.page
    assert catalog.require("HEADER_1X4_254").is_generic
    assert catalog.require("HEADER_1X4_254").evidence[0].status is ClaimStatus.ASSUMED


def test_no_timestamps_or_removed_ldo_evidence_leak_into_redesigned_support():
    design = build_design(True)
    for ref in ("U2", "L1", "R6", "R7", "C1", "C2", "R10", "R11", "R12", "R13", "R20", "R21"):
        component = design.circuit.component(ref)
        assert not any(e.document and e.document.part_number == "AP2112K-3.3TRG1"
                       for e in component.evidence)
    for ref, value in (("C3", .1e-6), ("C4", 22e-6), ("C5", 1e-6)):
        assert design.circuit.component(ref).value == Quantity.farads(value)
    assert design.circuit.component("R3").value == Quantity.ohms(10_000)
    with pytest.raises(TypeError, match="explicit boolean"):
        build_design("yes")
