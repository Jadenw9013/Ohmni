"""Independent placement-review regressions for bounds and refusal contracts."""

from __future__ import annotations

import builtins
import math

import pytest

from ohmni.catalog import default_catalog
from ohmni.domain import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.physical import placement as placement_module
from ohmni.physical.footprints import footprint
from ohmni.physical.models import (
    BoardOutline,
    PlacementConstraint,
    PlacementConstraintKind,
    PlacementGroup,
    PlacementGroupKind,
    PlacementRequest,
)
from ohmni.physical.placement import PlacementFailure, PlacementFailureCode, generate_placement
from ohmni.physical.rules import footprint_bounds
from ohmni.synthesis import SynthesisBrief, synthesize


def _pair(kind, **fields):
    circuit = CircuitIR(
        ir_id="placement-review-pair", name="Physical review pair",
        components=[CircuitComponent(ref=ref, part_id="GENERIC_RESISTOR", package="0805")
                    for ref in ("R1", "R2")],
        nets=[Net(name=f"connection{number}", connections=[PinRef(component=ref, pin=number)
                                                          for ref in ("R1", "R2")])
              for number in ("1", "2")],
    )
    request = PlacementRequest(
        circuit_content_hash=circuit.content_hash, outline=BoardOutline(width_mm=100, height_mm=70),
        groups=tuple(PlacementGroup(group_id=f"group-{index}", kind=PlacementGroupKind.GPIO,
                    anchor_ref=ref, member_refs=(ref,), reason="Independent resistor block")
                     for index, ref in enumerate(("R1", "R2"))),
        constraints=(PlacementConstraint(constraint_id="review-constraint", kind=kind,
                     component_ref="R2", target_ref="R1", reason="Explicit review constraint", **fields),),
    )
    return circuit, request


def test_separation_search_measures_envelope_gaps_before_selecting_candidate():
    circuit, request = _pair(PlacementConstraintKind.AWAY_FROM_COMPONENT, minimum_distance_mm=12)
    generated = generate_placement(circuit, request, default_catalog())
    definition = footprint("Resistor_SMD:R_0805_2012Metric")
    a, b = [footprint_bounds(definition, pose) for pose in generated.board.placements]
    gap = math.hypot(
        max(a.x_min_mm - b.x_max_mm, b.x_min_mm - a.x_max_mm, 0),
        max(a.y_min_mm - b.y_max_mm, b.y_min_mm - a.y_max_mm, 0),
    )
    assert gap >= 12 - 1e-9


@pytest.mark.parametrize("radius", [1e6, 1e100])
def test_large_proximity_radius_cannot_create_an_unbounded_candidate_grid(monkeypatch, radius):
    circuit, request = _pair(PlacementConstraintKind.NEAR_COMPONENT, maximum_distance_mm=radius)

    def bounded_range(*args):
        result = builtins.range(*args)
        # Fail immediately if a regression recreates the old astronomical grid;
        # never actually iterate it while testing the execution bound.
        assert len(result) <= 1000, "candidate axis escaped the supported board dimensions"
        return result

    monkeypatch.setattr(placement_module, "range", bounded_range, raising=False)
    generated = generate_placement(circuit, request, default_catalog())
    maximum_board_grid = (2 * 100 + 1) * (2 * 70 + 1)
    assert generated.metrics.candidate_count <= 2 * maximum_board_grid
    assert len(generated.board.placements) == 2


def test_nonexistent_proximity_pad_is_a_typed_refusal():
    circuit, request = _pair(PlacementConstraintKind.NEAR_COMPONENT,
                             maximum_distance_mm=5, target_pin="404")
    with pytest.raises(PlacementFailure) as failure:
        generate_placement(circuit, request, default_catalog())
    assert failure.value.code is PlacementFailureCode.INVALID_INTENT
    assert "404" in str(failure.value)


@pytest.mark.parametrize("update", [{"side": "B.Cu"}, {"minimum_edge_clearance_mm": math.nan}])
def test_copied_invalid_request_is_revalidated_and_refused(update):
    circuit, request = _pair(PlacementConstraintKind.NEAR_COMPONENT, maximum_distance_mm=20)
    invalid = request.model_copy(update=update)
    with pytest.raises(PlacementFailure) as failure:
        generate_placement(circuit, invalid, default_catalog())
    assert failure.value.code is PlacementFailureCode.INVALID_INTENT


def test_copied_duplicate_group_ownership_is_not_silently_collapsed():
    circuit, request = _pair(PlacementConstraintKind.NEAR_COMPONENT, maximum_distance_mm=20)
    extra = request.groups[0].model_copy(update={"group_id": "ambiguous-other"})
    invalid = request.model_copy(update={"groups": (*request.groups, extra)})
    with pytest.raises(PlacementFailure) as failure:
        generate_placement(circuit, invalid, default_catalog())
    assert failure.value.code is PlacementFailureCode.INVALID_INTENT


def test_consistent_reference_renaming_preserves_generated_geometry():
    result = synthesize(SynthesisBrief())
    original = generate_placement(result.circuit, result.placement_request, default_catalog())
    # A uniform prefix preserves documented identity tie ordering while proving
    # that the solver does not look up fixture reference designators for poses.
    mapping = {part.ref: f"renamed_{part.ref}" for part in result.circuit.components}
    circuit_values = result.circuit.model_dump()
    for component in circuit_values["components"]:
        component["ref"] = mapping[component["ref"]]
    for net in circuit_values["nets"]:
        for pin in net["connections"]:
            pin["component"] = mapping[pin["component"]]
    renamed = CircuitIR.model_validate(circuit_values)
    request_values = result.placement_request.model_dump()
    request_values["circuit_content_hash"] = renamed.content_hash
    for group in request_values["groups"]:
        group["anchor_ref"] = mapping[group["anchor_ref"]]
        group["member_refs"] = tuple(mapping[ref] for ref in group["member_refs"])
    for target in request_values["decoupling"]:
        target["capacitor_ref"] = mapping[target["capacitor_ref"]]
        target["target_ref"] = mapping[target["target_ref"]]
    for constraint in request_values["constraints"]:
        constraint["component_ref"] = mapping[constraint["component_ref"]]
        if constraint["target_ref"] is not None:
            constraint["target_ref"] = mapping[constraint["target_ref"]]
    request = PlacementRequest.model_validate(request_values)
    generated = generate_placement(renamed, request, default_catalog())
    expected = {mapping[pose.component_ref]: (pose.x_mm, pose.y_mm, pose.rotation_deg)
                for pose in original.board.placements}
    actual = {pose.component_ref: (pose.x_mm, pose.y_mm, pose.rotation_deg)
              for pose in generated.board.placements}
    assert actual == expected
    assert generated.metrics == original.metrics
    assert generated.circuit_content_hash == renamed.content_hash
    assert generated.request_fingerprint == request.content_hash
