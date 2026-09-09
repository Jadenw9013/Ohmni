"""Generated placements preserve physical intent independently of reference names."""

import pytest

from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.models import BoardOutline
from ohmni.physical.placement import PlacementFailure, PlacementFailureCode, generate_placement
from ohmni.synthesis import (
    ArchetypeId,
    I2cSensorSlot,
    SpiPeripheralSlot,
    SynthesisBrief,
    synthesize,
)

BRIEFS = [
    SynthesisBrief(),
    SynthesisBrief(sensors=(I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="TMP102AIDRLR"),
                           I2cSensorSlot(part_id="TMP102AIDRLR"))),
    SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), status_led_count=1,
                   button_count=1, include_programming_header=False),
    SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), status_led_count=4, button_count=2),
    SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL, sensors=(), status_led_count=0,
                   spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),), include_programming_header=False),
    SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
                   spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),) * 2),
]


@pytest.mark.parametrize("brief", BRIEFS, ids=["a1", "a1-three", "a2-min", "a2-max", "a3-min", "a3-max"])
def test_generated_family_placements_compile_with_all_constraints_checked(tmp_path, brief):
    result = synthesize(brief)
    assert result.accepted, result.refusal
    generated = generate_placement(result.circuit, result.placement_request, default_catalog())
    sch = KiCadSchematicCompiler(default_catalog()).compile(result.circuit, tmp_path / "board.kicad_sch")
    pcb = KiCadPcbCompiler(default_catalog()).compile(result.circuit, sch, generated.board, tmp_path / "board.kicad_pcb")
    assert pcb.compilation.physical_verification.passed, pcb.compilation.physical_verification.model_dump_json()
    constraints = {rule.constraint_id for rule in generated.board.placement_constraints}
    checked = {finding.constraint_id for finding in pcb.compilation.physical_verification.findings if finding.constraint_id}
    assert checked == constraints
    assert generated.request_fingerprint == result.placement_request.content_hash
    assert generated.metrics.board_area_mm2 == 7000
    assert generated.metrics.component_count == len(result.circuit.components)


def test_generated_placement_is_deterministic_and_responds_to_board_dimensions():
    result = synthesize(SynthesisBrief())
    first = generate_placement(result.circuit, result.placement_request, default_catalog())
    second = generate_placement(result.circuit, result.placement_request, default_catalog())
    assert first.model_dump_json() == second.model_dump_json()
    larger = result.placement_request.model_copy(update={"outline": BoardOutline(width_mm=110, height_mm=80)})
    changed = generate_placement(result.circuit, larger, default_catalog())
    assert first.board.content_hash != changed.board.content_hash
    assert changed.metrics.board_area_mm2 == 8800


def test_stale_intent_and_impossible_board_are_refused():
    result = synthesize(SynthesisBrief())
    changed = synthesize(SynthesisBrief(status_led_count=0))
    with pytest.raises(PlacementFailure) as stale:
        generate_placement(changed.circuit, result.placement_request, default_catalog())
    assert stale.value.code == PlacementFailureCode.STALE_INTENT
    tiny = result.placement_request.model_copy(update={"outline": BoardOutline(width_mm=10, height_mm=10)})
    with pytest.raises(PlacementFailure) as impossible:
        generate_placement(result.circuit, tiny, default_catalog())
    assert impossible.value.code == PlacementFailureCode.NO_FEASIBLE_POSITION


def test_unsupported_generated_orientation_is_not_silently_ignored():
    result = synthesize(SynthesisBrief())
    request = result.placement_request.model_copy(update={"allowed_rotations_deg": (90,)})
    with pytest.raises(PlacementFailure) as failure:
        generate_placement(result.circuit, request, default_catalog())
    assert failure.value.code == PlacementFailureCode.UNSUPPORTED_ORIENTATION
