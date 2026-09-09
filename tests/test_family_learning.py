"""Learning stories must describe the chosen circuit, including optional blocks."""

from types import SimpleNamespace

import pytest

from ohmni.application.naming import net_term
from ohmni.application.product import (
    RepairReplay,
    _assembly_confidence,
    _brief_label,
    _bring_up,
    _purpose,
    _readable,
)
from ohmni.application.systems import SystemId, build_flows, build_systems, group_components
from ohmni.bom.models import AssemblyDifficulty, AssemblyReport, AssemblyRisk
from ohmni.catalog import default_catalog
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    synthesize,
)
from ohmni.verifier import verify


@pytest.mark.parametrize("difficulty,status", [
    (AssemblyDifficulty.UNKNOWN, "UNKNOWN"),
    (AssemblyDifficulty.REFLOW_RECOMMENDED, "NEEDS_REVIEW"),
    (AssemblyDifficulty.DIFFICULT, "NEEDS_REVIEW"),
    (AssemblyDifficulty.MODERATE, "PASS"),
])
def test_assembly_confidence_keeps_unknown_separate_from_unsuitable(difficulty, status):
    report = AssemblyReport(risks=[AssemblyRisk(
        references=["U3"], package="example", difficulty=difficulty, detail="recorded classification",
    )], hand_solder_requirement_satisfied=difficulty is AssemblyDifficulty.MODERATE)
    line = _assembly_confidence(report)
    assert line.status == status
    if difficulty is AssemblyDifficulty.UNKNOWN:
        assert "not established" in line.detail
        assert "not met" not in line.detail


def _learning(brief):
    catalog = default_catalog()
    result = synthesize(brief)
    assert result.accepted, result.refusal
    grouping = group_components(result.circuit, catalog, {}, result.placement_request)
    return result, grouping, build_flows(result.circuit, catalog, grouping)


def _memory(with_sensor=False):
    return SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
                          sensors=(I2cSensorSlot(part_id="BME280"),) if with_sensor else (),
                          spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),) * 2,
                          status_led_count=0)


def test_memory_is_storage_with_spi_connections_not_sensor_measurement():
    result, grouping, flows = _learning(_memory())
    systems = {item.system: item for item in build_systems(grouping)}
    assert systems[SystemId.SENSE].label == "Storage"
    assert "measurement" not in systems[SystemId.SENSE].summary.lower()
    assert "read and write memory" in systems[SystemId.COMPUTE].summary
    assert "sensor_data" not in {flow.flow_id for flow in flows}
    spi = next(flow for flow in flows if flow.flow_id == "spi_data")
    assert set(spi.net_names) == {"SPI_SCK", "SPI_MOSI", "SPI_MISO", "SPI_CS1", "SPI_CS2"}
    assert {"U3", "U4"} <= set(spi.component_refs)
    catalog = default_catalog()
    assert net_term(result.circuit, catalog, "SPI_MOSI").human == "Data sent to device"
    assert net_term(result.circuit, catalog, "SPI_MISO").human == "Data returned by device"
    assert net_term(result.circuit, catalog, "SPI_CS2").human == "Device select"
    purpose = _purpose(result.circuit, catalog, "U3", next(item for item in grouping if item.component_ref == "U3"))
    assert "Stores data" in purpose and "firmware" in purpose.lower()


def test_combined_memory_and_sensor_keeps_distinct_bus_stories():
    _, grouping, flows = _learning(_memory(True))
    systems = {item.system: item for item in build_systems(grouping)}
    assert systems[SystemId.SENSE].label == "Sensing and storage"
    sensor = next(flow for flow in flows if flow.flow_id == "sensor_data")
    assert set(sensor.net_names) == {"SDA", "SCL"}
    assert "U5" in sensor.component_refs and not {"U3", "U4"} & set(sensor.component_refs)


def test_all_controller_leds_and_buttons_have_learning_coverage():
    result, grouping, flows = _learning(SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), status_led_count=4, button_count=2,
    ))
    lights = [flow for flow in flows if flow.flow_id.startswith("led_")]
    assert len(lights) == 4
    assert all(f"D{index}" in flow.component_refs for index, flow in enumerate(lights, 1))
    buttons = next(flow for flow in flows if flow.flow_id == "buttons")
    assert {"SW1", "SW2"} <= set(buttons.component_refs)
    assert "firmware" in buttons.stages[-1].detail.lower()
    assert "sensor_data" not in {flow.flow_id for flow in flows}
    processor = next(item for item in grouping if item.component_ref == "U1")
    assert "sensor" not in _purpose(result.circuit, default_catalog(), "U1", processor).lower()
    assert net_term(result.circuit, default_catalog(), "BUTTON1").human == "Button input"


def test_declared_capacitor_ownership_survives_misleading_display_distance():
    result = synthesize(_memory(True))
    positions = {part.ref: (0, 0) for part in result.circuit.components}
    positions["U1"] = (100, 100)
    grouping = {item.component_ref: item for item in group_components(
        result.circuit, default_catalog(), positions, result.placement_request,
    )}
    assert grouping["C3"].attached_to == grouping["C4"].attached_to == "U1"
    assert grouping["C6"].attached_to == "U3" and grouping["C7"].attached_to == "U4"
    assert "Compiler-declared" in grouping["C3"].basis
    changed = synthesize(SynthesisBrief(status_led_count=0))
    with pytest.raises(ValueError, match="another circuit"):
        group_components(changed.circuit, default_catalog(), {}, result.placement_request)


def test_memory_bringup_has_no_invented_sensor_reading_or_transaction_result():
    result, _, _ = _learning(_memory())
    design = SimpleNamespace(semantic_attempts=[verify(result.circuit, default_catalog(), result.requirements)])
    steps = _bring_up(design, result.circuit, default_catalog(), RepairReplay(happened=False, headline="No repair"))
    memory = next(step for step in steps if "known pattern" in step.action)
    assert memory.prediction is None and memory.rule_id == "PB-SPI-001"
    assert not any("sensor" in step.action.lower() for step in steps)


def test_brief_labels_explain_indexed_slots_and_absent_budget():
    assert _brief_label("sensors.1.address") == "Sensor 2 bus address"
    assert _brief_label("spi_devices.0.part_id") == "Memory chip 1"
    assert _readable("budget_usd", "Not specified") == "Not specified"
    assert _readable("budget_usd", "12.5") == "$12.5"
    assert _readable("archetype", "a2_usb_gpio_controller") == "Buttons and lights"
