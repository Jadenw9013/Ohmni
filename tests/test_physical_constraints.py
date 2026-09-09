"""Physical constraints fail closed and measure actual rotated geometry."""

from __future__ import annotations

import hashlib
import json
import math

import pytest
from pydantic import ValidationError

from ohmni.domain import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.eda.kicad.placement import golden_board_constraints
from ohmni.physical.footprints import FOOTPRINTS, footprint
from ohmni.physical.models import (
    BoardConstraints,
    BoardEdge,
    BoardOutline,
    ComponentPlacement,
    DecouplingTarget,
    FootprintDefinition,
    FootprintPad,
    FootprintSource,
    PadBinding,
    PhysicalFinding,
    PhysicalRuleStatus,
    PhysicalVerificationReport,
    PlacementConstraint,
    PlacementConstraintKind,
    PlacementGroup,
    PlacementGroupKind,
    PlacementPose,
    PlacementRegion,
    PlacementRequest,
)
from ohmni.physical.rules import (
    footprint_bounds,
    pad_position,
    resolved_keepout_region,
    verify_physical,
)


@pytest.fixture
def physical(monkeypatch):
    definition = FootprintDefinition(
        footprint_id="TEST:rectangle", width_mm=4, height_mm=2,
        pads=[FootprintPad(number="1", x_mm=1.5, y_mm=0, width_mm=.5, height_mm=.5)],
        source=FootprintSource(library_id="TEST", upstream_file_sha256="a" * 64,
                               license="test", derivation="test geometry"),
    )
    monkeypatch.setitem(FOOTPRINTS, definition.footprint_id, definition)
    circuit = CircuitIR(
        ir_id="physical-test", name="Constraint test",
        components=[CircuitComponent(ref=ref, part_id="TEST") for ref in ("A", "B")],
        nets=[Net(name="signal", connections=[PinRef(component=ref, pin="1") for ref in ("A", "B")])],
    )
    board = BoardConstraints(
        outline=BoardOutline(width_mm=40, height_mm=30),
        placements=[ComponentPlacement(component_ref=ref, x_mm=x, y_mm=10, reason="test")
                    for ref, x in (("A", 10), ("B", 20))],
    )
    return circuit, board, {ref: definition.footprint_id for ref in ("A", "B")}, [
        PadBinding(component_ref=ref, pin_number="1", pad_number="1", net_name="signal")
        for ref in ("A", "B")
    ]


def _constraint(kind, **kwargs):
    return PlacementConstraint(constraint_id="checked", kind=kind, component_ref="A",
                               reason="Explicit test geometry policy", **kwargs)


def _checked(physical, constraint):
    physical[1].placement_constraints = [constraint]
    report = verify_physical(*physical)
    matches = [finding for finding in report.findings if finding.constraint_id == "checked"]
    assert len(matches) == 1, report.model_dump_json()
    return report, matches[0]


@pytest.mark.parametrize("kind,fields", [
    (PlacementConstraintKind.FIXED, {"fixed_pose": PlacementPose(x_mm=10, y_mm=10)}),
    (PlacementConstraintKind.BOARD_EDGE, {"preferred_edge": BoardEdge.LEFT, "maximum_distance_mm": 8}),
    (PlacementConstraintKind.NEAR_COMPONENT, {"target_ref": "B", "maximum_distance_mm": 10}),
    (PlacementConstraintKind.AWAY_FROM_COMPONENT, {"target_ref": "B", "minimum_distance_mm": 6}),
    (PlacementConstraintKind.REGION, {"region": PlacementRegion(x_min_mm=8, y_min_mm=9, x_max_mm=12, y_max_mm=11)}),
    (PlacementConstraintKind.ORIENTATION, {"allowed_rotations_deg": (0,)}),
    (PlacementConstraintKind.KEEPOUT, {"keepout_region": PlacementRegion(x_min_mm=0, y_min_mm=0, x_max_mm=2, y_max_mm=2)}),
])
def test_every_supported_constraint_has_a_measured_verdict(physical, kind, fields):
    report, finding = _checked(physical, _constraint(kind, **fields))
    assert finding.status is PhysicalRuleStatus.PASS
    assert report.passed
    assert report.limitations


@pytest.mark.parametrize("kind,fields", [
    (PlacementConstraintKind.FIXED, {"fixed_pose": PlacementPose(x_mm=11, y_mm=10)}),
    (PlacementConstraintKind.BOARD_EDGE, {"preferred_edge": BoardEdge.RIGHT, "maximum_distance_mm": 8}),
    (PlacementConstraintKind.NEAR_COMPONENT, {"target_ref": "B", "maximum_distance_mm": 9}),
    (PlacementConstraintKind.AWAY_FROM_COMPONENT, {"target_ref": "B", "minimum_distance_mm": 6.1}),
    (PlacementConstraintKind.REGION, {"region": PlacementRegion(x_min_mm=8, y_min_mm=9, x_max_mm=11.5, y_max_mm=11)}),
    (PlacementConstraintKind.ORIENTATION, {"allowed_rotations_deg": (90,)}),
    (PlacementConstraintKind.KEEPOUT, {"keepout_region": PlacementRegion(x_min_mm=18, y_min_mm=9, x_max_mm=22, y_max_mm=11)}),
])
def test_constraint_violation_blocks_the_physical_gate(physical, kind, fields):
    report, finding = _checked(physical, _constraint(kind, **fields))
    assert finding.status is PhysicalRuleStatus.FAIL
    assert not report.passed


@pytest.mark.parametrize("kind", list(PlacementConstraintKind))
def test_missing_constraint_parameters_are_errors_not_silent_passes(physical, kind):
    report, finding = _checked(physical, _constraint(kind))
    assert finding.status is PhysicalRuleStatus.ERROR
    assert not report.passed


def test_missing_target_and_missing_target_pad_are_errors(physical):
    for fields in ({"target_ref": "missing"}, {"target_ref": "B", "target_pin": "404"}):
        report, finding = _checked(physical, _constraint(
            PlacementConstraintKind.NEAR_COMPONENT, maximum_distance_mm=100, **fields,
        ))
        assert finding.status is PhysicalRuleStatus.ERROR
        assert not report.passed


def test_unknown_component_constraint_is_not_ignored(physical):
    constraint = _constraint(PlacementConstraintKind.ORIENTATION, allowed_rotations_deg=(0,))
    constraint = constraint.model_copy(update={"component_ref": "missing"})
    report, finding = _checked(physical, constraint)
    assert finding.status is PhysicalRuleStatus.ERROR
    assert not report.passed


def test_irrelevant_constraint_parameter_cannot_be_silently_ignored(physical):
    report, finding = _checked(physical, _constraint(
        PlacementConstraintKind.FIXED, fixed_pose=PlacementPose(x_mm=10, y_mm=10),
        maximum_distance_mm=0,
    ))
    assert finding.status is PhysicalRuleStatus.ERROR
    assert not report.passed


def test_pin_to_pin_proximity_uses_rotated_pad_centers(physical):
    physical[1].placements[1] = physical[1].placements[1].model_copy(update={"rotation_deg": 180})
    report, finding = _checked(physical, _constraint(
        PlacementConstraintKind.NEAR_COMPONENT, target_ref="B", component_pin="1",
        target_pin="1", maximum_distance_mm=7,
    ))
    assert finding.measured_mm == pytest.approx(7)
    assert report.passed


def test_rotated_envelope_catches_board_overhang_that_unrotated_bounds_miss(physical):
    physical[1].placements[0] = physical[1].placements[0].model_copy(
        update={"rotation_deg": 90, "y_mm": 1.5},
    )
    report = verify_physical(*physical)
    assert not report.passed
    assert any(f.rule_id == "PB-PCB-002" and f.status is PhysicalRuleStatus.FAIL for f in report.findings)


def test_pad_extent_is_part_of_board_boundary_check(physical):
    definition = footprint("TEST:rectangle")
    definition.pads.append(FootprintPad(number="2", x_mm=5, y_mm=0, width_mm=1, height_mm=1))
    physical[1].placements[1] = physical[1].placements[1].model_copy(update={"x_mm": 36})
    report = verify_physical(*physical)
    assert not report.passed
    assert any(f.rule_id == "PB-PCB-002" and f.status is PhysicalRuleStatus.FAIL for f in report.findings)


def test_relative_keepout_rotates_with_its_owner(physical):
    owner = physical[1].placements[0].model_copy(update={"rotation_deg": 90})
    constraint = _constraint(PlacementConstraintKind.KEEPOUT, relative_to_component=True,
        keepout_region=PlacementRegion(x_min_mm=-2, y_min_mm=-6, x_max_mm=2, y_max_mm=-4))
    region = resolved_keepout_region(constraint, {"A": owner})
    assert region.model_dump() == pytest.approx(
        {"x_min_mm": 14, "y_min_mm": 8, "x_max_mm": 16, "y_max_mm": 12}
    )


def test_pin_binding_must_reference_real_pad_and_correct_net(physical):
    for update in ({"pad_number": "missing"}, {"net_name": "wrong"}):
        altered = [physical[3][0].model_copy(update=update), physical[3][1]]
        report = verify_physical(*physical[:3], altered)
        assert not report.passed
        assert any(f.status is PhysicalRuleStatus.ERROR for f in report.findings)


def test_multiple_physical_legs_for_one_electrical_pin_are_valid(physical):
    definition = footprint("TEST:rectangle")
    definition.pads.append(FootprintPad(number="1", x_mm=-1.5, y_mm=0, width_mm=.5, height_mm=.5))
    assert verify_physical(*physical).passed
    with pytest.raises(ValueError, match="expected one physical pad"):
        pad_position(definition, physical[1].placements[0], "1")


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_all_geometric_inputs_reject_nonfinite_numbers(bad):
    constructors = [
        lambda: BoardOutline(width_mm=bad, height_mm=10),
        lambda: PlacementRegion(x_min_mm=bad, y_min_mm=0, x_max_mm=10, y_max_mm=10),
        lambda: ComponentPlacement(component_ref="A", x_mm=bad, y_mm=10, reason="test"),
        lambda: PlacementPose(x_mm=10, y_mm=10, rotation_deg=bad),
        lambda: _constraint(PlacementConstraintKind.ORIENTATION, allowed_rotations_deg=(bad,)),
        lambda: DecouplingTarget(capacitor_ref="C1", target_ref="U1", target_pin="2",
                                 maximum_distance_mm=bad, reason="test"),
        lambda: FootprintPad(number="1", x_mm=0, y_mm=0, width_mm=bad, height_mm=1),
    ]
    for constructor in constructors:
        with pytest.raises(ValidationError):
            constructor()


def test_copied_invalid_geometry_fails_closed_at_verification(physical):
    physical[1].placements[0] = physical[1].placements[0].model_copy(update={"x_mm": math.nan})
    report = verify_physical(*physical)
    assert not report.passed
    assert report.findings[0].status is PhysicalRuleStatus.ERROR


def test_unsupported_component_side_is_rejected():
    with pytest.raises(ValidationError):
        ComponentPlacement(component_ref="A", x_mm=0, y_mm=0, side="B.Cu", reason="unsupported")


def test_error_and_empty_physical_reports_cannot_pass():
    assert not PhysicalVerificationReport(findings=[]).passed
    assert not PhysicalVerificationReport(findings=[PhysicalFinding(
        rule_id="test", status=PhysicalRuleStatus.ERROR, description="could not assess",
    )]).passed


def test_esp32_body_includes_antenna_extension_missing_from_old_envelope():
    definition = footprint("RF_Module:ESP32-WROOM-32")
    bounds = footprint_bounds(definition, ComponentPlacement(
        component_ref="U1", x_mm=0, y_mm=0, reason="body review",
    ))
    assert bounds.y_min_mm == pytest.approx(-15.74)
    assert bounds.y_max_mm >= 9.76
    # Preserving the old subset identity does not retain its incomplete check.
    assert definition.height_mm == 20.5


def test_old_c5_position_is_rejected_by_the_new_true_body_check(golden, catalog):
    board = golden_board_constraints()
    # Preserve this regression even after the current authored layout moves C5.
    board.placements = [placement.model_copy(update={"x_mm": 45, "y_mm": 22})
                        if placement.component_ref == "C5" else placement
                        for placement in board.placements]
    ids, bindings = {}, []
    for component in golden.components:
        spec = catalog.require(component.part_id)
        ids[component.ref] = spec.package(component.package).kicad_footprint
        for pin in spec.pins:
            net = golden.net_of(component.ref, pin.number)
            bindings.append(PadBinding(component_ref=component.ref, pin_number=pin.number,
                                        pad_number=pin.number, net_name=net.name if net else None))
    report = verify_physical(golden, board, ids, bindings)
    assert not report.passed
    assert any(f.rule_id == "PB-PCB-001" and set(f.component_refs) == {"U1", "C5"}
               for f in report.findings)
    assert report.geometry_sources["body:RF_Module:ESP32-WROOM-32"] == (
        "e08a57b98669dbb126e5006854fdefad7226c6fceeb34c94d6449fd48db8cbc9"
    )


def test_saved_constraint_hash_is_stable_when_new_optional_policies_absent():
    board = golden_board_constraints()
    legacy = board.model_dump(mode="json")
    old_fields = {"constraint_id", "kind", "component_ref", "target_ref",
                  "maximum_distance_mm", "reason", "evidence"}
    legacy["placement_constraints"] = [
        {key: value for key, value in constraint.items() if key in old_fields}
        for constraint in legacy["placement_constraints"]
    ]
    digest = hashlib.sha256(json.dumps(legacy, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert board.content_hash == digest


def test_placement_request_binds_source_and_rejects_ambiguous_group_ownership():
    group = PlacementGroup(group_id="core", kind=PlacementGroupKind.PROCESSOR,
                           anchor_ref="U1", member_refs=("U1", "C1"), reason="test")
    request = PlacementRequest(circuit_content_hash="a" * 64,
                                outline=BoardOutline(width_mm=40, height_mm=30), groups=(group,))
    changed = request.model_copy(update={"circuit_content_hash": "b" * 64})
    assert request.content_hash != changed.content_hash
    with pytest.raises(ValidationError, match="multiple placement groups"):
        PlacementRequest(circuit_content_hash="a" * 64, outline=request.outline,
            groups=(group, group.model_copy(update={"group_id": "other"})))
    with pytest.raises(ValidationError, match="include its anchor"):
        PlacementGroup(group_id="bad", kind=PlacementGroupKind.PROCESSOR,
                       anchor_ref="U1", member_refs=("C1",), reason="missing anchor")
