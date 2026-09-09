"""Real catalog composition, refusal, and saved-input compatibility checks."""

import hashlib
import json
from itertools import product

import pytest

from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadSchematicCompiler
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    synthesize,
)
from ohmni.verifier import verify


def test_existing_a1_input_fingerprint_survives_new_empty_slots():
    brief = SynthesisBrief()
    legacy = brief.model_dump(mode="json")
    del legacy["button_count"], legacy["spi_devices"]
    expected = hashlib.sha256(json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert brief.fingerprint == expected
    assert SynthesisBrief.model_validate(legacy).fingerprint == expected
    assert brief.model_copy(update={"button_count": 1}).fingerprint != expected


def test_auto_address_reserves_later_explicit_choices():
    result = synthesize(SynthesisBrief(sensors=(
        I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="BME280", address=0x76))))
    assert result.accepted, result.refusal
    assert result.circuit.component("U3").selected_i2c_address == 0x77
    assert result.circuit.component("U4").selected_i2c_address == 0x76
    assert not verify(result.circuit, default_catalog(), result.requirements).export_blocked


@pytest.mark.parametrize("count,led,header,sensor", list(product((1, 2), (0, 1), (False, True), (None, "BME280", "TMP102AIDRLR"))))
def test_a3_real_catalog_composition_is_checked_and_compileable(tmp_path, count, led, header, sensor):
    brief = SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
        sensors=() if sensor is None else (I2cSensorSlot(part_id=sensor),),
        spi_devices=tuple(SpiPeripheralSlot(part_id="25LC256-I/SN") for _ in range(count)),
        status_led_count=led, include_programming_header=header)
    result = synthesize(brief)
    assert result.accepted, result.refusal
    report = verify(result.circuit, default_catalog(), result.requirements)
    assert report.coverage == 1 and not report.export_blocked, report.model_dump_json()
    assert next(r for r in report.results if r.rule_id == "PB-SPI-001").outcome.value == "pass"
    assert result.circuit.content_hash == synthesize(brief).circuit.content_hash
    memories = [part for part in result.circuit.components if part.part_id == "25LC256-I/SN"]
    assert len(memories) == count
    selects = [next(net.name for net in result.circuit.nets if net.has(part.ref, "1")) for part in memories]
    assert len(set(selects)) == count
    assert (result.circuit.component("D1") is not None) == bool(led)
    assert (result.circuit.component("J2") is not None) == header
    required = {item.requirement_id for item in result.requirements.functional_requirements}
    assert ("FR-I2C" in required) == (sensor is not None)
    assert ("FR-LED" in required) == bool(led)
    assert ("FR-UART" in required) == header
    artifact = KiCadSchematicCompiler(default_catalog()).compile(result.circuit, tmp_path / "spi.kicad_sch")
    assert artifact.path.is_file()


@pytest.mark.parametrize("sensors", [
    (I2cSensorSlot(part_id="TMP102AIDRLR"),),
    (I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="BME280")),
    (I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="TMP102AIDRLR")),
    (I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="TMP102AIDRLR")),
])
def test_extended_a1_assigns_real_unique_addresses_and_supply_capacitors(sensors):
    brief = SynthesisBrief(sensors=sensors)
    result = synthesize(brief)
    assert result.accepted, result.refusal
    report = verify(result.circuit, default_catalog(), result.requirements)
    assert report.coverage == 1 and not report.export_blocked, report.model_dump_json()
    instances = [part for part in result.circuit.components if part.selected_i2c_address is not None]
    assert len(instances) == len(sensors)
    assert len({part.selected_i2c_address for part in instances}) == len(sensors)
    required = {item.requirement_id for item in result.requirements.functional_requirements}
    assert {"FR-I2C", "FR-LED", "FR-UART"} <= required
    assert result.circuit.content_hash == synthesize(brief).circuit.content_hash


@pytest.mark.parametrize("kwargs,code", [
    ({"archetype": ArchetypeId.A3_USB_SPI_PERIPHERAL, "spi_devices": ()}, "spi_count_unsupported"),
    ({"archetype": ArchetypeId.A3_USB_SPI_PERIPHERAL, "spi_devices": (SpiPeripheralSlot(part_id="made-up"),)}, "spi_unavailable"),
    ({"archetype": ArchetypeId.A3_USB_SPI_PERIPHERAL, "spi_devices": (SpiPeripheralSlot(part_id="25LC256-I/SN"),), "button_count": 1}, "peripheral_slots_unsupported"),
    ({"sensors": (I2cSensorSlot(part_id="BME280", address=0x76),)*2}, "sensor_address_conflict"),
    ({"sensors": (I2cSensorSlot(part_id="BME280"),)*3}, "sensor_address_conflict"),
    ({"sensors": (I2cSensorSlot(part_id="TMP102AIDRLR", address=0x4A),)}, "sensor_address_unavailable"),
    ({"spi_devices": (SpiPeripheralSlot(part_id="25LC256-I/SN"),)}, "peripheral_slots_unsupported"),
])
def test_unused_or_conflicting_slots_are_refused_instead_of_ignored(kwargs, code):
    result = synthesize(SynthesisBrief(**kwargs))
    assert not result.accepted
    assert result.refusal.code.value == code
