"""The current personal editor cannot save briefs its transport cannot reopen."""

import pytest

from ohmni.application.projects import (
    ProjectPipeline,
    ProjectRefusalError,
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
def test_supported_compiler_configurations_are_refused_by_current_editor(brief, tmp_path, monkeypatch):
    from ohmni.application import projects

    assert synthesize(brief).accepted  # Editor limitations must not redefine compiler support.

    def unexpected_synthesis(_brief):
        raise AssertionError("The editor boundary should refuse before preview or engineering work")

    monkeypatch.setattr(projects, "synthesize_a1", unexpected_synthesis)
    for action in (lambda: preview_project(brief), lambda: ProjectPipeline().run(tmp_path / "build", brief)):
        with pytest.raises(ProjectRefusalError) as caught:
            action()
        refusal = caught.value.refusal.model_dump(mode="json")
        assert refusal["code"] == "editor_configuration_unsupported"
        assert "compiler" in refusal["message"] and "one BME280" in refusal["message"]
        assert refusal["context"] == {"surface": "personal_project_editor"}
        assert "sensors" in refusal["field_paths"]
    assert not (tmp_path / "build").exists()


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
