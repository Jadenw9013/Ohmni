"""Fail-closed provenance and geometric escape tests for scoped controller routing."""
import pytest

from tools.landing_controller.design import (
    HEADER_GPIO_PINS,
    HEADER_SIDE_GPIO_PINS,
    HEADER_TOP_GPIO_PINS,
    build_design,
)
from tools.landing_controller.physical import (
    ControllerPcbCompiler,
    build_board_constraints,
    routing_constraints,
    scoped_footprints,
)
from tools.landing_controller.routing import (
    _geometry,
    npth_search_obstacles,
    repair,
    structured_route,
)
from tools.landing_controller.schematic import ControllerSchematicCompiler


@pytest.fixture
def authored(tmp_path):
    design = build_design()
    with scoped_footprints():
        board = build_board_constraints(design.circuit)
        schematic = ControllerSchematicCompiler(design.catalog).compile(design.circuit, tmp_path / "controller.kicad_sch")
        pcb = ControllerPcbCompiler(design.catalog).compile(design.circuit, schematic, board, tmp_path / "controller-placed.kicad_pcb")
        constraints = routing_constraints(design.circuit)
        # Force a bounded incomplete run; this test never relies on router speed
        # or declares a board connected merely because its exits are legal.
        proposal, manifest = structured_route(design.circuit, pcb, board, constraints, time_budget_seconds=1e-12)
        yield design, board, pcb, constraints, proposal, manifest


def test_custom_header_preserves_exact_gpio_set_and_near_row_order():
    expected = set(range(1, 6)) | set(range(55, 68)) | {78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 91, 92, 93, 95, 96, 97, 98}
    assert len(HEADER_GPIO_PINS) == len(expected) == 36
    assert set(HEADER_GPIO_PINS) == expected
    assert HEADER_GPIO_PINS[::2] == HEADER_TOP_GPIO_PINS
    assert HEADER_GPIO_PINS[1::2] == HEADER_SIDE_GPIO_PINS
    assert list(HEADER_TOP_GPIO_PINS) == sorted(HEADER_TOP_GPIO_PINS, reverse=True)


def test_fanout_geometry_checks_do_not_turn_timeout_into_connected(authored):
    design, _, _, _, proposal, manifest = authored
    assert manifest["seed_geometry_checked"]
    assert not manifest["rules_relaxed"]
    assert manifest["reserved_via_room_mm"] == .6
    seeded = set(manifest["seeded_complete_gpio_nets"])
    assert len(seeded) == 18
    assert {failure.net_name for failure in proposal.failures} == {net.name for net in design.circuit.nets} - seeded
    assert proposal.statistics.routed_net_count == 18
    assert all(f.reason.value == "routing_incomplete" for f in proposal.failures)
    assert all(bool(net.paths) == (net.net_name in seeded) for net in proposal.routed_nets)


@pytest.mark.parametrize("mutation", ["footprint_hash", "pad_net", "artifact_circuit", "profile", "placement_hash"])
def test_proposal_cannot_be_rebound_after_identity_or_geometry_changes(authored, mutation):
    design, board, pcb, constraints, proposal, _ = authored
    before = proposal.model_dump_json()
    prior = pcb.model_copy(deep=True)
    candidate = proposal.model_copy(deep=True)
    if mutation == "footprint_hash":
        prior.compilation.footprint_bindings[0].geometry_fingerprint = "0"*64
    elif mutation == "pad_net":
        prior.compilation.pad_bindings[0].net_name = "INVALID"
    elif mutation == "artifact_circuit":
        prior.circuit_content_hash = "0"*64
    elif mutation == "profile":
        candidate.profile.signal_width_mm = candidate.profile.signal_width_mm.model_copy(update={"value": .1})
    else:
        candidate.source_constraints_hash = "0"*64
    with pytest.raises(ValueError, match="geometry|lineage"):
        repair(design.circuit, pcb, board, constraints, candidate, prior, displaced_nets=(), time_budget_seconds=1)
    assert proposal.model_dump_json() == before


def test_fresh_repair_is_a_new_proposal_and_keeps_incomplete_failures(authored):
    design, board, pcb, constraints, proposal, _ = authored
    before = proposal.model_dump_json()
    updated, manifest = repair(design.circuit, pcb, board, constraints, proposal, pcb,
                               displaced_nets=(), time_budget_seconds=1e-12)
    assert updated is not proposal
    assert updated.failures
    assert manifest["proposal_hash"] == proposal.content_hash
    assert proposal.model_dump_json() == before


def test_usb_npth_search_clearance_does_not_modify_source_geometry(authored):
    _, board, pcb, constraints, _, manifest = authored
    before = pcb.compilation.model_dump_json()
    actual = _geometry(pcb, board)[2]
    expanded = npth_search_obstacles(pcb, board, constraints.profile, actual)
    changed = [(a, b) for a, b in zip(actual, expanded, strict=True) if a != b]
    assert len(changed) == 2
    for original, reserved in changed:
        assert original[0] is reserved[0] is None
        assert original[1] == reserved[1]
        assert reserved[2] == pytest.approx(original[2]+.2)
        assert reserved[3] == pytest.approx(original[3]+.2)
        assert original[4] == reserved[4] == ("F.Cu", "B.Cu")
    assert manifest["minimum_npth_copper_clearance_mm"] == .25
    assert _geometry(pcb, board)[2] == actual
    assert pcb.compilation.model_dump_json() == before
