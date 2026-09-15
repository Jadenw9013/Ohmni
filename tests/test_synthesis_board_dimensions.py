"""Editable outlines are physical intent, not per-component coordinates."""

import pytest
from pydantic import ValidationError

from ohmni.application.project_requirements import project_requirement_results
from ohmni.application.projects import prepare_project, project_options
from ohmni.catalog import default_catalog
from ohmni.physical.placement import PlacementFailure, generate_placement
from ohmni.synthesis import SynthesisBrief, synthesize
from ohmni.verifier import verify

BRIEFS = [
    SynthesisBrief(),
    SynthesisBrief(sensors=[{"part_id": "TMP102AIDRLR"}]),
    SynthesisBrief(archetype="a2_usb_gpio_controller", sensors=[{"part_id": "BME280"}],
                   status_led_count=4, button_count=2),
    SynthesisBrief(archetype="a3_usb_spi_peripheral", spi_devices=[{"part_id": "25LC256-I/SN"}]),
]


@pytest.mark.parametrize("brief", BRIEFS)
def test_outline_changes_propagate_without_changing_electrical_intent(brief):
    original = synthesize(brief)
    smaller = brief.model_copy(update={"board_width_mm": 90.0, "board_height_mm": 55.0})
    result = synthesize(smaller)
    assert result.accepted
    assert smaller.fingerprint != brief.fingerprint
    assert result.circuit.content_hash == original.circuit.content_hash
    assert result.placement_request.content_hash != original.placement_request.content_hash
    assert result.placement_request.outline.width_mm == 90
    assert result.placement_request.outline.height_mm == 55
    catalog = default_catalog()
    first = generate_placement(result.circuit, result.placement_request, catalog)
    second = generate_placement(result.circuit, result.placement_request, catalog)
    assert first == second
    assert first.board.outline == result.placement_request.outline


def test_explicit_default_outline_preserves_saved_brief_identity():
    brief = SynthesisBrief()
    assert brief.fingerprint == "a65f1fbf3bf3329a60560a5ad98fe1522921bd03378604f36001348641ef5dae"
    assert SynthesisBrief(board_width_mm=100.0, board_height_mm=70.0).fingerprint == brief.fingerprint


@pytest.mark.parametrize("changes", [{"board_width_mm": 39}, {"board_width_mm": 101},
                                     {"board_height_mm": 39}, {"board_height_mm": 71},
                                     {"board_width_mm": float("inf")}])
def test_dimensions_outside_bounded_search_are_invalid(changes):
    with pytest.raises(ValidationError):
        SynthesisBrief(**changes)


def test_small_outline_fails_when_physical_constraints_cannot_fit():
    brief = BRIEFS[2].model_copy(update={"board_width_mm": 40.0, "board_height_mm": 40.0})
    result = synthesize(brief)
    assert result.accepted  # electrical intent can be valid while placement fails
    with pytest.raises(PlacementFailure):
        generate_placement(result.circuit, result.placement_request, default_catalog())


def test_dimensions_are_discoverable_recorded_and_compared_to_actual_geometry():
    options = project_options()
    assert options["board_dimensions"] == {
        "board_width_mm": {"min": 40, "max": 100, "default": 100},
        "board_height_mm": {"min": 40, "max": 70, "default": 70},
    }
    controller = next(family for family in options["families"] if family["id"] == "a2_usb_gpio_controller")
    assert controller["sensor_count"] == {"min": 0, "max": 1}
    brief = BRIEFS[2].model_copy(update={"board_width_mm": 90.0, "board_height_mm": 55.0})
    circuit, compiled = prepare_project(brief)
    result = synthesize(brief)
    catalog = default_catalog()
    semantic = verify(circuit, catalog, compiled.requirements)
    board = generate_placement(circuit, result.placement_request, catalog).board
    rows = project_requirement_results(brief, compiled, circuit, semantic, board, catalog)
    dimensions = {row["field"]: row for row in rows if row["field"].startswith("board_")}
    assert dimensions["board_width_mm"]["status"] == dimensions["board_height_mm"]["status"] == "MET"
    assert dimensions["board_width_mm"]["display_value"] == "90.0 mm"
    wrong = board.model_copy(update={"outline": board.outline.model_copy(update={"width_mm": 100.0})})
    rows = project_requirement_results(brief, compiled, circuit, semantic, wrong, catalog)
    assert next(row for row in rows if row["field"] == "board_width_mm")["status"] == "VIOLATED"
