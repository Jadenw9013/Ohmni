"""Electrical compilation emits complete, source-bound physical intent."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from ohmni.adapters.tools import find_kicad_cli
from ohmni.domain import ClaimStatus, PinRole
from ohmni.physical.models import BoardEdge, PlacementConstraintKind, PlacementRequest
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    SynthesisResult,
    synthesize,
)
from ohmni.synthesis.base import build_usb_esp32_base
from ohmni.synthesis.peripherals import add_i2c_bus, add_i2c_sensor
from ohmni.synthesis.placement import (
    ANTENNA_REGION,
    ANTENNA_SOURCE_SHA256,
    PlacementIntentBuilder,
)

CASES = [
    SynthesisBrief(),
    SynthesisBrief(status_led_count=0, include_programming_header=False),
    SynthesisBrief(sensors=(I2cSensorSlot(part_id="TMP102AIDRLR"),)),
    SynthesisBrief(sensors=(I2cSensorSlot(part_id="BME280", address=0x76),
                            I2cSensorSlot(part_id="BME280", address=0x77),
                            I2cSensorSlot(part_id="TMP102AIDRLR"))),
] + [
    SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(),
                   status_led_count=leds, button_count=buttons, include_programming_header=header)
    for leds in (1, 4) for buttons in (1, 2) for header in (False, True)
] + [
    SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
                   spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),) * count,
                   sensors=sensors, status_led_count=0 if not sensors else 1)
    for count in (1, 2) for sensors in ((), (I2cSensorSlot(part_id="BME280"),),
                                      (I2cSensorSlot(part_id="TMP102AIDRLR"),))
]


@pytest.mark.parametrize("brief", CASES)
def test_each_emitted_component_has_one_block_and_exact_capacitor_owner(catalog, brief):
    result = synthesize(brief, catalog)
    assert result.accepted, result.refusal
    request, circuit = result.placement_request, result.circuit
    assert request is not None
    assert request.circuit_content_hash == circuit.content_hash
    members = [ref for group in request.groups for ref in group.member_refs]
    assert sorted(members) == sorted(component.ref for component in circuit.components)
    assert len(members) == len(set(members))
    owners = {member: group.anchor_ref for group in request.groups for member in group.member_refs}
    nets = {(pin.component, pin.pin): net.name for net in circuit.nets for pin in net.connections}
    for target in request.decoupling:
        assert owners[target.capacitor_ref] == target.target_ref
        spec = catalog.require(circuit.component(target.target_ref).part_id)
        assert PinRole.POWER in spec.pin(target.target_pin).roles
        assert nets[(target.capacitor_ref, target.capacitor_pin)] == nets[(target.target_ref, target.target_pin)]
        assert any(evidence.status is ClaimStatus.ASSUMED for evidence in target.evidence)
    # The enable-delay capacitor must never masquerade as a supply bypass.
    assert "C5" not in {target.capacitor_ref for target in request.decoupling}
    enable = next(rule for rule in request.constraints if rule.component_ref == "C5")
    assert enable.kind is PlacementConstraintKind.NEAR_COMPONENT
    assert enable.target_pin == next(pin.number for pin in catalog.require(brief.mcu_part_id).pins if pin.name == "EN")
    assert request == PlacementRequest.model_validate_json(request.model_dump_json())


@pytest.mark.parametrize("brief", CASES)
def test_physical_intent_is_repeatable_without_runtime_evidence_timestamps(brief):
    first, second = synthesize(brief), synthesize(brief)
    assert first.circuit.content_hash == second.circuit.content_hash
    assert first.placement_request.content_hash == second.placement_request.content_hash
    assert first.placement_request.model_dump_json() == second.placement_request.model_dump_json()


def test_legacy_brief_and_circuit_fingerprints_remain_unchanged():
    full = SynthesisBrief()
    assert full.fingerprint == "a65f1fbf3bf3329a60560a5ad98fe1522921bd03378604f36001348641ef5dae"
    assert synthesize(full).circuit.content_hash == "e5bbe5e0ee6efdab4f44c6b594f305d2216d557aea553a3241f0ba1c637adfc8"
    small = SynthesisBrief(status_led_count=0, include_programming_header=False)
    assert small.fingerprint == "f010024c12c1338ce6b61823bbcbc6a27c9531b4858035502d5baabd2bcbd9cb"
    assert synthesize(small).circuit.content_hash == "9f8cc0ea6efec910ec9b0886fc187fc2f945b4d349bcd8196182a1ec2f0d48a5"


def test_peripheral_ownership_survives_arbitrary_compiler_references_and_removed_notes(catalog):
    intent = PlacementIntentBuilder()
    brief = SynthesisBrief()
    base = build_usb_esp32_base(brief, catalog, placement=intent)
    add_i2c_bus(base.components, base.nets, catalog, True,
                resistor_refs=("RPULL_A", "RPULL_B"), placement=intent)
    add_i2c_sensor(base.components, base.nets, catalog, I2cSensorSlot(part_id="BME280"), True,
                   ref="SENSOR_TEMP", cap_refs=("CAP_VDD", "CAP_IO"), placement=intent)
    for component in base.components:
        component.notes = None
    request = intent.finish(base)
    targets = {item.capacitor_ref: (item.target_ref, item.target_pin) for item in request.decoupling}
    assert targets["CAP_VDD"] == ("SENSOR_TEMP", "8")
    assert targets["CAP_IO"] == ("SENSOR_TEMP", "6")


def test_shared_logic_net_cannot_silently_reassign_capacitor_to_another_block(catalog):
    intent = PlacementIntentBuilder()
    circuit = build_usb_esp32_base(SynthesisBrief(), catalog, placement=intent)
    index = next(i for i, item in enumerate(intent.decoupling) if item.capacitor_ref == "C3")
    # Both pins are on 3V3, so mere net matching cannot establish ownership.
    intent.decoupling[index] = intent.decoupling[index].model_copy(update={"target_ref": "U2", "target_pin": "5"})
    with pytest.raises(ValueError, match="authored placement block"):
        intent.finish(circuit)


def test_changed_electrical_fingerprint_cannot_reuse_old_placement_intent():
    result = synthesize(SynthesisBrief())
    payload = result.model_dump()
    next(component for component in payload["circuit"]["components"] if component["ref"] == "R1")["value"]["value"] = 1000
    with pytest.raises(ValueError, match="accepted circuit fingerprint"):
        SynthesisResult.model_validate(payload)


def test_refused_design_has_no_placement_request():
    result = synthesize(SynthesisBrief(logic_voltage_v=5))
    assert not result.accepted and result.placement_request is None
    payload = result.model_dump()
    payload["placement_request"] = synthesize(SynthesisBrief()).placement_request.model_dump()
    with pytest.raises(ValueError, match="accepted circuit fingerprint"):
        SynthesisResult.model_validate(payload)


def test_board_access_and_source_keepout_are_explicit_qualified_policies():
    result = synthesize(SynthesisBrief())
    edges = {rule.component_ref: rule.preferred_edge for rule in result.placement_request.constraints
             if rule.kind is PlacementConstraintKind.BOARD_EDGE}
    assert edges == {"J1": BoardEdge.BOTTOM, "J2": BoardEdge.RIGHT, "U1": BoardEdge.TOP}
    keepout = next(rule for rule in result.placement_request.constraints if rule.kind is PlacementConstraintKind.KEEPOUT)
    assert keepout.relative_to_component and keepout.keepout_region == ANTENNA_REGION
    assert all(evidence.status is ClaimStatus.ASSUMED for evidence in keepout.evidence)
    assert ANTENNA_SOURCE_SHA256 in keepout.evidence[0].detail
    assert "RF performance" in keepout.evidence[0].detail


@pytest.mark.integration
def test_antenna_polygon_matches_separately_pinned_installed_footprint():
    executable = find_kicad_cli()
    if executable is None:
        pytest.skip("KiCad not installed")
    source = Path(executable).resolve().parent.parent / "share/kicad/footprints/RF_Module.pretty/ESP32-WROOM-32.kicad_mod"
    if not source.is_file():
        pytest.skip("KiCad source footprint unavailable")
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ANTENNA_SOURCE_SHA256:
        pytest.skip("Installed source revision differs from separately pinned antenna policy")
    source_text = raw.decode().replace("\r\n", "\n")
    keepout = source_text[source_text.index("\n\t(zone\n"):]
    assert all(f"({kind} not_allowed)" in keepout
               for kind in ("tracks", "vias", "pads", "copperpour", "footprints"))
    coordinates = [(float(x), float(y)) for x, y in re.findall(r"\(xy ([^ ]+) ([^)]+)\)", keepout)]
    assert set(coordinates) == {(-24, -9.8), (24, -9.8), (24, -30.74), (-24, -30.74)}
