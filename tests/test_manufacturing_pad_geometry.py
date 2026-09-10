"""Fixed footprint lands and drills must satisfy the selected factory profile."""

from types import SimpleNamespace

import pytest
from test_manufacturing import minimal_plan

from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.manufacturing import prototype_profile, verify_manufacturing
from ohmni.manufacturing.pad_geometry import measure_pads
from ohmni.physical.placement import generate_placement
from ohmni.synthesis import I2cSensorSlot, SynthesisBrief, synthesize


@pytest.fixture
def tmp_board(tmp_path):
    catalog = default_catalog()
    result = synthesize(SynthesisBrief(sensors=(I2cSensorSlot(part_id="TMP102AIDRLR"),)), catalog)
    board = generate_placement(result.circuit, result.placement_request, catalog).board
    schematic = KiCadSchematicCompiler(catalog).compile(result.circuit, tmp_path / "board.kicad_sch")
    pcb = KiCadPcbCompiler(catalog).compile(result.circuit, schematic, board, tmp_path / "board.kicad_pcb")
    return pcb, board


def test_actual_fine_pitch_gap_is_not_replaced_by_larger_route_setting(tmp_board):
    pcb, board = tmp_board
    measured = measure_pads(pcb, board)
    assert measured.minimum_gap_mm == pytest.approx(.15)
    assert all(name.startswith("U3.") for name in measured.closest_pair)
    assert measured.minimum_drill_mm == pytest.approx(.6)
    assert measured.slot_count == 4
    assert measured.minimum_slot_width_mm == pytest.approx(.6)
    assert measured.nonplated_hole_count == 2
    permissive = verify_manufacturing(pcb, board, minimal_plan(), prototype_profile())
    assert next(x for x in permissive.findings if x.rule_id == "PB-MFG-011").status.value == "pass"
    strict = prototype_profile().model_copy(deep=True)
    strict.minimum_clearance.value = .2
    report = verify_manufacturing(pcb, board, minimal_plan(clearance=.2), strict)
    pad_gap = next(x for x in report.findings if x.rule_id == "PB-MFG-011")
    assert pad_gap.status.value == "fail" and pad_gap.designed == pytest.approx(.15)
    assert not report.passed


def test_component_drills_are_checked_even_when_plan_has_no_vias(tmp_board):
    pcb, board = tmp_board
    plan = minimal_plan()
    plan.routed_nets[0].paths[0].vias = []
    plan.statistics.via_count = 0
    strict = prototype_profile().model_copy(deep=True)
    strict.minimum_drill.value = .7
    report = verify_manufacturing(pcb, board, plan, strict)
    assert next(x for x in report.findings if x.rule_id == "PB-MFG-012").status.value == "fail"
    assert not report.passed


@pytest.mark.parametrize("supports_slots,width,status", [
    (False, .6, "fail"), (True, None, "unknown"), (True, .7, "fail"), (True, .6, "pass"),
])
def test_usb_mounting_slots_require_explicit_profile_capability(tmp_board, supports_slots, width, status):
    pcb, board = tmp_board
    profile = prototype_profile().model_copy(deep=True)
    profile.supports_slots = supports_slots
    if width is None:
        profile.minimum_slot_width = None
    else:
        profile.minimum_slot_width.value = width
    report = verify_manufacturing(pcb, board, minimal_plan(), profile)
    assert next(x for x in report.findings if x.rule_id == "PB-MFG-013").status.value == status
    if status != "pass":
        assert not report.passed


def test_changed_local_footprint_definition_cannot_reinterpret_existing_pcb(tmp_board, monkeypatch):
    from ohmni.physical.footprints import FOOTPRINTS

    pcb, board = tmp_board
    binding = pcb.compilation.footprint_bindings[0]
    altered = FOOTPRINTS[binding.footprint_id].model_copy(deep=True)
    altered.pads[0].width_mm += .1
    monkeypatch.setitem(FOOTPRINTS, binding.footprint_id, altered)
    with pytest.raises(ValueError, match="Local footprint geometry"):
        measure_pads(pcb, board)
    report = verify_manufacturing(pcb, board, minimal_plan(), prototype_profile())
    assert not report.passed


def test_missing_geometry_cannot_become_a_passing_profile(tmp_board):
    pcb, board = tmp_board
    pcb.compilation.pad_bindings = []
    # Empty bindings cannot assert that neighboring pads share a net. They are
    # all measured as unassigned copper, preserving the conservative gap.
    assert measure_pads(pcb, board).minimum_gap_mm <= .15
    missing = SimpleNamespace(fingerprint=pcb.fingerprint, compilation=SimpleNamespace(
        footprint_bindings=pcb.compilation.footprint_bindings))
    report = verify_manufacturing(missing, board, minimal_plan(), prototype_profile())
    assert next(x for x in report.findings if x.rule_id == "PB-MFG-011").status.value == "unknown"
    assert not report.passed


def test_other_placement_cannot_be_measured_under_the_original_pcb_fingerprint(tmp_board):
    pcb, board = tmp_board
    values = board.model_dump()
    values["placements"][0]["x_mm"] += 1
    moved = type(board).model_validate(values)
    assert moved.content_hash != pcb.constraints_hash
    with pytest.raises(ValueError, match="Placement does not match"):
        measure_pads(pcb, moved)
    report = verify_manufacturing(pcb, moved, minimal_plan(), prototype_profile())
    assert next(x for x in report.findings if x.rule_id == "PB-MFG-011").status.value == "unknown"
    assert not report.passed


def test_modified_pcb_file_cannot_support_fresh_measurements(tmp_board):
    pcb, board = tmp_board
    pcb.path.write_text("modified artifact", encoding="utf-8")
    with pytest.raises(ValueError, match="lineage is stale"):
        measure_pads(pcb, board)
