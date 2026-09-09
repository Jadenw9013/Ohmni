"""All implemented compiler families share the personal project preparation path."""

import pytest

from ohmni.application.projects import (
    prepare_project,
    preview_project,
)
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    synthesize,
)


@pytest.mark.parametrize("brief", [
    SynthesisBrief(sensors=(I2cSensorSlot(part_id="TMP102AIDRLR"),)),
    SynthesisBrief(sensors=(I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="TMP102AIDRLR"))),
    SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), button_count=1),
    SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL, sensors=(),
                   spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),)),
])
def test_supported_compiler_configurations_reach_the_same_generic_editor(brief):
    expected=synthesize(brief)
    assert expected.accepted
    circuit,requirements=prepare_project(brief)
    assert circuit.content_hash==expected.circuit.content_hash
    assert requirements.requirements.project_name==brief.project_name
    assert preview_project(brief).asked_for


@pytest.mark.parametrize("address", [0x76, 0x77])
@pytest.mark.parametrize("led", [0, 1])
@pytest.mark.parametrize("header", [False, True])
def test_all_current_editor_variations_keep_their_compiled_circuit(address, led, header):
    brief = SynthesisBrief(sensors=(I2cSensorSlot(part_id="BME280", address=address),),
                           status_led_count=led, include_programming_header=header)
    circuit, requirements = prepare_project(brief)
    assert circuit.content_hash == synthesize(brief).circuit.content_hash
    assert requirements.requirements.project_name == brief.project_name
    assert preview_project(brief).asked_for
