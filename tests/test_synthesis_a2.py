"""A2 electrical topology, bounded refusals and real compiler bindings."""

import pytest

from ohmni.adapters.fakes import InMemoryPartCatalog
from ohmni.catalog import default_catalog
from ohmni.domain import Interface, PinElectricalType, PinRole, Quantity, SafetyDomain
from ohmni.eda.kicad import KiCadSchematicCompiler
from ohmni.synthesis.a2 import BUTTON_PART_ID, synthesize_a2
from ohmni.synthesis.base import build_usb_esp32_base, common_preflight
from ohmni.synthesis.models import ArchetypeId, InputPower, RefusalCode, SynthesisBrief
from ohmni.verifier import verify


def _brief(**changes):
    values = {"archetype": ArchetypeId.A2_USB_GPIO_CONTROLLER, "sensors": (),
              "project_name": "Button and light controller", "description": "A two-input indicator board.",
              "status_led_count": 2, "button_count": 2}
    return SynthesisBrief(**(values | changes))


def _accepted(brief=None, catalog=None):
    result = synthesize_a2(brief or _brief(), catalog)
    assert result.accepted, result.refusal
    return result


@pytest.mark.parametrize("leds", [1, 2, 3, 4])
@pytest.mark.parametrize("buttons", [1, 2])
@pytest.mark.parametrize("header", [True, False])
def test_every_supported_gpio_configuration_has_complete_semantic_coverage_and_compiles(leds, buttons, header, tmp_path):
    catalog = default_catalog()
    result = _accepted(_brief(status_led_count=leds, button_count=buttons, include_programming_header=header))
    circuit = result.circuit
    report = verify(circuit, catalog, result.requirements)
    assert report.coverage == 1.0
    assert not report.export_blocked, report.blocking_findings
    assert sum(part.ref.startswith("D") for part in circuit.components) == leds
    assert sum(part.ref.startswith("SW") for part in circuit.components) == buttons
    assert (circuit.component("J2") is not None) is header
    assert not any(part.part_id == "BME280" for part in circuit.components)
    assert Interface.I2C not in result.requirements.interfaces
    artifact = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "gpio.kicad_sch")
    projected = {(pin.net_name, pin.component_ref, pin.circuit_pin)
                 for binding in artifact.compilation.symbol_bindings for pin in binding.pins if pin.net_name}
    expected = {(net.name, pin.component, pin.pin) for net in circuit.nets for pin in net.connections}
    assert projected == expected
    assert set(artifact.compilation.net_mapping) == {net.name for net in circuit.nets}


def test_gpio_assignments_are_distinct_catalog_non_strapping_pins_with_real_pullups():
    circuit = _accepted(_brief(status_led_count=4, button_count=2)).circuit
    mcu = default_catalog().require("ESP32-WROOM-32E")
    chosen = []
    for net in circuit.nets:
        if net.name.startswith("LED") and net.name.endswith("_DRIVE") or net.name.startswith("BUTTON"):
            number = net.pins_of("U1")[0]
            pin = next(item for item in mcu.pins if item.number == number)
            assert PinRole.GPIO in pin.roles and PinRole.BOOT_STRAP not in pin.roles
            chosen.append(number)
    assert len(chosen) == len(set(chosen)) == 6
    for index in (1, 2):
        switch, pullup = f"SW{index}", f"R{19 + index}"
        assert circuit.net(f"BUTTON{index}").has(switch, "1")
        assert circuit.net(f"BUTTON{index}").has(pullup, "1")
        assert circuit.net("GND").has(switch, "2")
        assert circuit.net("3V3").has(pullup, "2")
        assert circuit.component(pullup).value == Quantity.ohms(10_000)


def test_led_resistors_have_individual_private_nodes_and_inherit_source_limits():
    result = _accepted(_brief(status_led_count=4))
    circuit = result.circuit
    for index in range(1, 5):
        resistor = circuit.component(f"R{9 + index}")
        assert resistor.value == Quantity.ohms(330)
        assert resistor.evidence
        assert "I(max)" in resistor.notes
        assert circuit.net(f"LED{index}_A").components() == {f"D{index}", resistor.ref}
    report = verify(circuit, default_catalog(), result.requirements)
    led_rule = next(item for item in report.results if item.rule_id == "PB-LED-001")
    assert led_rule.outcome.value == "pass"
    assert any("current rating is not checked" in limit for limit in led_rule.limitations)
    assert any("debounce" in text or "switch bounce" in text for text in result.requirements.assumptions)


def test_identical_gpio_briefs_are_deterministic_and_meaningful_changes_change_connectivity():
    first = _accepted()
    second = _accepted()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    for change in ({"status_led_count": 1}, {"button_count": 1}, {"include_programming_header": False}):
        assert _accepted(_brief(**change)).circuit.content_hash != first.circuit.content_hash
    assert first.brief_fingerprint == _brief().fingerprint


def test_gpio_and_core_have_no_incidental_sensor_or_spi_catalog_dependency():
    ids = {"USB_C_RECEPTACLE_16P", "AP2112K-3.3TRG1", "GENERIC_RESISTOR", "GENERIC_CAPACITOR",
           "ESP32-WROOM-32E", "HEADER_1X6_254", "GENERIC_LED_GREEN", BUTTON_PART_ID}
    catalog = InMemoryPartCatalog([part for part in default_catalog().all_parts() if part.part_id in ids])
    assert _accepted(catalog=catalog).accepted
    assert common_preflight(_brief(), catalog) is None
    core = build_usb_esp32_base(_brief(), catalog)
    assert not any(part.part_id in {"BME280", "GENERIC_LED_GREEN", BUTTON_PART_ID} for part in core.components)
    assert {net.name for net in core.nets} == {"VBUS", "GND", "CC1", "CC2", "3V3", "EN", "UART_TX", "UART_RX", "IO0"}


@pytest.mark.parametrize("changes,code", [
    ({"status_led_count": 0}, RefusalCode.STATUS_LED_COUNT_UNSUPPORTED),
    ({"status_led_count": 5}, RefusalCode.STATUS_LED_COUNT_UNSUPPORTED),
    ({"button_count": 0}, RefusalCode.BUTTON_COUNT_UNSUPPORTED),
    ({"button_count": 3}, RefusalCode.BUTTON_COUNT_UNSUPPORTED),
    ({"sensors": [{"part_id": "BME280"}, {"part_id": "TMP102AIDRLR"}]}, RefusalCode.SENSOR_COUNT_UNSUPPORTED),
    ({"sensors": [{"part_id": "missing"}]}, RefusalCode.SENSOR_UNAVAILABLE),
    ({"sensors": [{"part_id": "BME280", "address": 0x48}]}, RefusalCode.SENSOR_ADDRESS_UNAVAILABLE),
    ({"spi_devices": [{"part_id": "BME280"}]}, RefusalCode.PERIPHERAL_SLOTS_UNSUPPORTED),
    ({"input_power": InputPower.MAINS}, RefusalCode.SAFETY_DOMAIN_UNSUPPORTED),
    ({"safety_domains": [SafetyDomain.MAINS]}, RefusalCode.SAFETY_DOMAIN_UNSUPPORTED),
    ({"input_power": InputPower.BATTERY}, RefusalCode.INPUT_POWER_UNSUPPORTED),
    ({"input_voltage_v": 9}, RefusalCode.INPUT_VOLTAGE_UNSUPPORTED),
    ({"logic_voltage_v": 5}, RefusalCode.LOGIC_VOLTAGE_UNSUPPORTED),
    ({"max_board_layers": 4}, RefusalCode.LAYER_COUNT_UNSUPPORTED),
])
def test_gpio_rejects_unsupported_slots_and_envelopes(changes, code):
    brief = _brief(**changes)
    result = synthesize_a2(brief)
    assert not result.accepted
    assert result.circuit is None and result.requirements is None
    assert result.refusal.code is code
    assert result.brief_fingerprint == brief.fingerprint


def test_missing_button_and_missing_gpio_capability_are_typed_refusals():
    catalog = default_catalog()
    missing = InMemoryPartCatalog([part for part in catalog.all_parts() if part.part_id != BUTTON_PART_ID])
    assert synthesize_a2(_brief(), missing).refusal.code is RefusalCode.PART_UNAVAILABLE
    mcu = catalog.require("ESP32-WROOM-32E")
    modified = mcu.model_copy(update={"pins": [pin.model_copy(update={"electrical_type": PinElectricalType.INPUT})
                                               if pin.name == "IO25" else pin for pin in mcu.pins]})
    insufficient = InMemoryPartCatalog([modified if part.part_id == mcu.part_id else part for part in catalog.all_parts()])
    assert synthesize_a2(_brief(), insufficient).refusal.code is RefusalCode.CATALOG_CAPABILITY_MISSING


@pytest.mark.parametrize("sensor,address", [("BME280", 0x77), ("TMP102AIDRLR", 0x49)])
@pytest.mark.parametrize("leds,buttons,header", [(1, 1, False), (4, 2, True)])
def test_sensor_controller_composes_real_nets_and_complete_verification(sensor, address, leds, buttons, header, tmp_path):
    catalog = default_catalog()
    result = _accepted(_brief(sensors=[{"part_id": sensor, "address": address}],
                              status_led_count=leds, button_count=buttons, include_programming_header=header))
    circuit = result.circuit
    report = verify(circuit, catalog, result.requirements)
    assert report.coverage == 1.0 and not report.export_blocked, report.blocking_findings
    assert circuit.component("U3").selected_i2c_address == address
    assert Interface.I2C in result.requirements.interfaces
    assert sensor in result.requirements.required_part_ids
    for name, ref in (("SDA", "R4"), ("SCL", "R5")):
        assert circuit.net(name).components() == {"U1", "U3", ref}
        assert circuit.component(ref).value == Quantity.ohms(4700)
        assert circuit.net("3V3").has(ref, "2")
    cap_count = 2 if sensor == "BME280" else 1
    assert len([target for target in result.placement_request.decoupling if target.target_ref == "U3"]) == cap_count
    assert len(circuit.components) == 12 - (not header) + 2 * leds + 2 * buttons + 3 + cap_count
    pins = [pin.pin for net in circuit.nets for pin in net.connections if pin.component == "U1"]
    assert len(pins) == len(set(pins))
    artifact = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "sensor-controller.kicad_sch")
    projected = {(pin.net_name, pin.component_ref, pin.circuit_pin)
                 for binding in artifact.compilation.symbol_bindings for pin in binding.pins if pin.net_name}
    assert projected == {(net.name, pin.component, pin.pin) for net in circuit.nets for pin in net.connections}


def test_sensor_controller_changes_are_deterministic_and_really_change_inventory_and_nets():
    brief = _brief(sensors=[{"part_id": "BME280"}], status_led_count=4)
    first, second = _accepted(brief), _accepted(brief)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    for changes in ({"sensors": []}, {"sensors": [{"part_id": "TMP102AIDRLR"}]},
                    {"sensors": [{"part_id": "BME280", "address": 0x77}]},
                    {"status_led_count": 2}, {"button_count": 1}, {"include_programming_header": False}):
        changed = _accepted(SynthesisBrief.model_validate(brief.model_dump() | changes))
        assert changed.circuit.content_hash != first.circuit.content_hash
        report = verify(changed.circuit, default_catalog(), changed.requirements)
        assert report.coverage == 1.0 and not report.export_blocked


def test_sensor_bus_pin_conflicts_and_strapping_pins_are_refused(monkeypatch):
    from ohmni.synthesis import a2

    brief = _brief(sensors=[{"part_id": "BME280"}])
    monkeypatch.setattr(a2, "LED_GPIO_NAMES", ("IO21", "IO26", "IO27", "IO32"))
    refused = synthesize_a2(brief)
    assert refused.refusal.code is RefusalCode.CATALOG_CAPABILITY_MISSING
    assert "already allocated" in refused.refusal.message
    monkeypatch.undo()
    catalog = default_catalog()
    mcu = catalog.require(brief.mcu_part_id)
    for changes in ({"roles": [PinRole.GPIO, PinRole.BOOT_STRAP]},
                    {"electrical_type": PinElectricalType.OUTPUT}):
        modified = mcu.model_copy(update={"pins": [pin.model_copy(update=changes) if pin.name == "IO21" else pin
                                                  for pin in mcu.pins]})
        changed = InMemoryPartCatalog([modified if part.part_id == mcu.part_id else part for part in catalog.all_parts()])
        assert synthesize_a2(brief, changed).refusal.code is RefusalCode.CATALOG_CAPABILITY_MISSING


def test_sensor_requires_its_catalog_facts_but_plain_controller_does_not():
    catalog = default_catalog()
    missing = InMemoryPartCatalog([part for part in catalog.all_parts() if part.part_id != "BME280"])
    assert synthesize_a2(_brief(sensors=[{"part_id": "BME280"}]), missing).refusal.code is RefusalCode.SENSOR_UNAVAILABLE
    assert _accepted(catalog=missing).accepted


@pytest.mark.parametrize("changes,brief_hash,circuit_hash,placement_hash", [
    ({}, "bcac932f1184a11872c3cc6c2f5af4f5d103c92383a43ccd7768158a7f352852",
     "c102f954b1f15bcc32e9f8f1273fd47f3fa080c42206053953086aa0696f1369",
     "2751abb8c846bb5a973d9928dcccee87ebcdf3aa48610fbae7cd353fcb3ecbc0"),
    ({"status_led_count": 4}, "30ff4e563bec64f5824ae5c7605609b1a4b479021594f4792fad67a6f39e6666",
     "f5b54a4960e369f839f962ca0f6843c2a3ed05c5b6ad0bed00fd66792550b483",
     "31ef3dfcb037435f5d5ef07dd61163c94e448bdff2b4cddaf655833611112202"),
])
def test_existing_sensorless_controller_identities_are_unchanged(changes, brief_hash, circuit_hash, placement_hash):
    result = _accepted(_brief(**changes))
    assert result.brief_fingerprint == brief_hash
    assert result.circuit.content_hash == circuit_hash
    assert result.placement_request.content_hash == placement_hash
