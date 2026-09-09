"""Deterministic placement geometry checks, separate from copper and RF checks."""

from __future__ import annotations

import math

from ..domain import CircuitIR
from .footprints import footprint
from .models import (
    BoardConstraints,
    BoardEdge,
    ComponentPlacement,
    FootprintDefinition,
    PadBinding,
    PhysicalFinding,
    PhysicalRuleStatus,
    PhysicalVerificationReport,
    PlacementConstraint,
    PlacementConstraintKind,
    PlacementRegion,
)

_EPSILON = 1e-9

# The historical pad subset stored a symmetric 19.5 x 20.5 mm envelope,
# omitting the ESP32 antenna body's extension toward local negative Y. Keep
# that serialized subset and its old source identity intact; this additional
# F.Fab body envelope is independently pinned to the inspected KiCad source.
BODY_ENVELOPE_SOURCES = {
    "RF_Module:ESP32-WROOM-32": {
        "source": "RF_Module.pretty/ESP32-WROOM-32.kicad_mod (KiCad 10 F.Fab)",
        "sha256": "e08a57b98669dbb126e5006854fdefad7226c6fceeb34c94d6449fd48db8cbc9",
        "region": PlacementRegion(x_min_mm=-9, y_min_mm=-15.74, x_max_mm=9, y_max_mm=9.76),
    },
}


def _transform(x: float, y: float, placement: ComponentPlacement) -> tuple[float, float]:
    angle = math.radians(placement.rotation_deg)
    return (
        placement.x_mm + x * math.cos(angle) - y * math.sin(angle),
        placement.y_mm + x * math.sin(angle) + y * math.cos(angle),
    )


def _corners(region: PlacementRegion) -> list[tuple[float, float]]:
    return [(x, y) for x in (region.x_min_mm, region.x_max_mm)
            for y in (region.y_min_mm, region.y_max_mm)]


def _bounds(points: list[tuple[float, float]]) -> PlacementRegion:
    return PlacementRegion(x_min_mm=min(x for x, _ in points),
                           y_min_mm=min(y for _, y in points),
                           x_max_mm=max(x for x, _ in points),
                           y_max_mm=max(y for _, y in points))


def footprint_bounds(fp: FootprintDefinition, placement: ComponentPlacement) -> PlacementRegion:
    """Rotated envelope including every physical pad, including asymmetric origins.

    This conservative axis-aligned envelope is exact for orthogonal rotations;
    it may reject a tighter arrangement of non-orthogonal rectangular bodies.
    """
    regions = [PlacementRegion(x_min_mm=-fp.width_mm / 2, y_min_mm=-fp.height_mm / 2,
                               x_max_mm=fp.width_mm / 2, y_max_mm=fp.height_mm / 2)]
    if body := BODY_ENVELOPE_SOURCES.get(fp.footprint_id):
        regions.append(body["region"])
    regions.extend(PlacementRegion(
        x_min_mm=pad.x_mm - pad.width_mm / 2, y_min_mm=pad.y_mm - pad.height_mm / 2,
        x_max_mm=pad.x_mm + pad.width_mm / 2, y_max_mm=pad.y_mm + pad.height_mm / 2,
    ) for pad in fp.pads)
    return _bounds([_transform(x, y, placement) for region in regions for x, y in _corners(region)])


def pad_position(
    fp: FootprintDefinition, placement: ComponentPlacement, pad_number: str,
) -> tuple[float, float]:
    matches = [pad for pad in fp.pads if pad.number == pad_number and not pad.mechanical]
    if len(matches) != 1:
        raise ValueError(f"{placement.component_ref}: expected one physical pad {pad_number!r}")
    return _transform(matches[0].x_mm, matches[0].y_mm, placement)


def resolved_keepout_region(
    constraint: PlacementConstraint, placements: dict[str, ComponentPlacement],
) -> PlacementRegion:
    """Resolve an owner-relative exclusion rectangle into board coordinates."""
    if constraint.kind is not PlacementConstraintKind.KEEPOUT or constraint.keepout_region is None:
        raise ValueError("a keepout constraint requires its exclusion rectangle")
    if constraint.component_ref not in placements:
        raise ValueError(f"keepout owner {constraint.component_ref!r} has no placement")
    if not constraint.relative_to_component:
        return constraint.keepout_region
    owner = placements[constraint.component_ref]
    return _bounds([_transform(x, y, owner) for x, y in _corners(constraint.keepout_region)])


def _inside(inner: PlacementRegion, outer: PlacementRegion) -> bool:
    return (
        inner.x_min_mm >= outer.x_min_mm - _EPSILON
        and inner.y_min_mm >= outer.y_min_mm - _EPSILON
        and inner.x_max_mm <= outer.x_max_mm + _EPSILON
        and inner.y_max_mm <= outer.y_max_mm + _EPSILON
    )


def _overlap(a: PlacementRegion, b: PlacementRegion) -> bool:
    return (a.x_min_mm < b.x_max_mm - _EPSILON and a.x_max_mm > b.x_min_mm + _EPSILON
            and a.y_min_mm < b.y_max_mm - _EPSILON and a.y_max_mm > b.y_min_mm + _EPSILON)


def _gap(a: PlacementRegion, b: PlacementRegion) -> float:
    dx = max(a.x_min_mm - b.x_max_mm, b.x_min_mm - a.x_max_mm, 0)
    dy = max(a.y_min_mm - b.y_max_mm, b.y_min_mm - a.y_max_mm, 0)
    return math.hypot(dx, dy)


def _shape_error(constraint: PlacementConstraint) -> str | None:
    allowed = {
        PlacementConstraintKind.FIXED: {"fixed_pose"},
        PlacementConstraintKind.BOARD_EDGE: {"maximum_distance_mm", "preferred_edge"},
        PlacementConstraintKind.NEAR_COMPONENT: {
            "maximum_distance_mm", "target_ref", "component_pin", "target_pin",
        },
        PlacementConstraintKind.AWAY_FROM_COMPONENT: {"minimum_distance_mm", "target_ref"},
        PlacementConstraintKind.REGION: {"region"},
        PlacementConstraintKind.ORIENTATION: {"allowed_rotations_deg"},
        PlacementConstraintKind.KEEPOUT: {"keepout_region", "relative_to_component"},
    }[constraint.kind]
    common = {"constraint_id", "kind", "component_ref", "reason", "evidence"}
    unused = [name for name in type(constraint).model_fields if name not in common | allowed
              and getattr(constraint, name) is not None
              and getattr(constraint, name) is not False
              and getattr(constraint, name) != ()]
    return f"unsupported fields for {constraint.kind.value}: {', '.join(unused)}" if unused else None


def verify_physical(
    circuit: CircuitIR, constraints: BoardConstraints, footprint_ids: dict[str, str],
    pad_bindings: list[PadBinding],
) -> PhysicalVerificationReport:
    """Evaluate every submitted constraint, including invalid or unresolved inputs."""
    findings: list[PhysicalFinding] = []
    limitations = [
        ("Placement checks use conservative component/pad envelopes. Copper clearance "
         "and connectivity require the independent routing verifier and KiCad DRC."),
        ("An antenna keepout check establishes geometric exclusion only; RF performance "
         "and the adequacy of an ASSUMED clearance policy are not verified."),
    ]

    def add(rule_id, ok, description, refs=(), measured=None, limit=None, constraint_id=None):
        findings.append(PhysicalFinding(
            rule_id=rule_id, status=PhysicalRuleStatus.PASS if ok else PhysicalRuleStatus.FAIL,
            description=description, component_refs=list(refs), measured_mm=measured,
            limit_mm=limit, constraint_id=constraint_id,
        ))

    def error(description, refs=(), constraint_id=None):
        findings.append(PhysicalFinding(rule_id="PB-PCB-008", status=PhysicalRuleStatus.ERROR,
            description=description, component_refs=list(refs), constraint_id=constraint_id))

    # model_copy(update=...) deliberately bypasses Pydantic validation. Recheck
    # here so a copied NaN/unsupported side never becomes a clean geometry run.
    try:
        constraints = BoardConstraints.model_validate(constraints.model_dump())
    except ValueError as exc:
        error(f"Invalid placement input: {exc}")
        return PhysicalVerificationReport(findings=findings, limitations=limitations)
    placements = {p.component_ref: p for p in constraints.placements}
    circuit_refs = {part.ref for part in circuit.components}
    if set(placements) - circuit_refs:
        error("Placement refers to a component outside CircuitIR", sorted(set(placements) - circuit_refs))
    if not circuit_refs:
        error("No circuit components were available for physical verification")
    board = PlacementRegion(x_min_mm=0, y_min_mm=0,
                            x_max_mm=constraints.outline.width_mm, y_max_mm=constraints.outline.height_mm)
    boxes: dict[str, PlacementRegion] = {}
    footprints: dict[str, FootprintDefinition] = {}
    margin = constraints.minimum_edge_clearance_mm
    for ref in sorted(circuit_refs):
        placement = placements.get(ref)
        fp_id = footprint_ids.get(ref)
        fp = footprint(fp_id) if fp_id else None
        if placement is None or fp is None:
            error(f"{ref} lacks a resolved placement or footprint", [ref])
            continue
        try:
            fp = FootprintDefinition.model_validate(fp.model_dump())
            box = footprint_bounds(fp, placement)
        except ValueError as exc:
            error(f"{ref} has invalid footprint geometry: {exc}", [ref])
            continue
        footprints[ref] = fp
        boxes[ref] = box
        add("PB-PCB-002", _inside(box, board), f"{ref} footprint and pads lie inside the board outline", [ref])
        clearance = min(box.x_min_mm, box.y_min_mm,
                        board.x_max_mm - box.x_max_mm, board.y_max_mm - box.y_max_mm)
        add("PB-PCB-003", clearance >= margin - _EPSILON,
            f"{ref} envelope clearance to the board edge", [ref], clearance, margin)
    overlaps = False
    refs = sorted(boxes)
    for index, ref in enumerate(refs):
        for other in refs[index + 1:]:
            if _overlap(boxes[ref], boxes[other]):
                overlaps = True
                add("PB-PCB-001", False, f"{ref} and {other} footprint/pad envelopes overlap", [ref, other])
    if not overlaps and len(boxes) == len(circuit_refs) and boxes:
        add("PB-PCB-001", True, "No component/pad envelopes overlap")

    bound: dict[tuple[str, str], list[PadBinding]] = {}
    for binding in pad_bindings:
        bound.setdefault((binding.component_ref, binding.pin_number), []).append(binding)

    def endpoint(ref: str, pin: str | None) -> tuple[float, float]:
        if pin is None:
            return placements[ref].x_mm, placements[ref].y_mm
        bindings = bound.get((ref, pin), [])
        if len(bindings) != 1:
            raise ValueError(f"{ref}.{pin} lacks one unambiguous pin-to-pad binding")
        return pad_position(footprints[ref], placements[ref], bindings[0].pad_number)

    missing = False
    for net in circuit.nets:
        for pin in net.connections:
            try:
                bindings = bound.get((pin.component, pin.pin), [])
                if len(bindings) != 1:
                    raise ValueError(f"{pin} lacks one unambiguous pin-to-pad binding")
                binding = bindings[0]
                if not any(pad.number == binding.pad_number and not pad.mechanical
                           for pad in footprints[pin.component].pads):
                    raise ValueError(f"{pin} does not resolve to an actual physical pad")
                if binding.net_name != net.name:
                    raise ValueError(f"{pin} physical pad is assigned to another net")
            except (ValueError, KeyError) as exc:
                missing = True
                error(str(exc), [pin.component])
    if not missing and circuit.nets:
        add("PB-PCB-006", True, "Every connected pin resolves to its actual physical pad and net")

    for constraint in constraints.placement_constraints:
        ref, target = constraint.component_ref, constraint.target_ref
        args = {"constraint_id": constraint.constraint_id}
        if ref not in boxes:
            error(f"{constraint.constraint_id}: component {ref!r} has no usable geometry", [ref], **args)
            continue
        if problem := _shape_error(constraint):
            error(f"{constraint.constraint_id}: {problem}", [ref], **args)
            continue
        placement = placements[ref]
        try:
            if constraint.kind is PlacementConstraintKind.BOARD_EDGE:
                if constraint.maximum_distance_mm is None:
                    raise ValueError("board-edge constraint requires maximum_distance_mm")
                box = boxes[ref]
                distances = {
                    BoardEdge.TOP: box.y_min_mm, BoardEdge.BOTTOM: board.y_max_mm - box.y_max_mm,
                    BoardEdge.LEFT: box.x_min_mm, BoardEdge.RIGHT: board.x_max_mm - box.x_max_mm,
                }
                d = distances[constraint.preferred_edge] if constraint.preferred_edge else min(distances.values())
                add("PB-PCB-005", -_EPSILON <= d <= constraint.maximum_distance_mm + _EPSILON,
                    constraint.reason, [ref], d, constraint.maximum_distance_mm, **args)
            elif constraint.kind in (PlacementConstraintKind.NEAR_COMPONENT, PlacementConstraintKind.AWAY_FROM_COMPONENT):
                if target not in boxes:
                    raise ValueError(f"target {target!r} has no usable geometry")
                if target == ref:
                    raise ValueError("a component cannot be its own proximity target")
                if constraint.kind is PlacementConstraintKind.NEAR_COMPONENT:
                    if constraint.maximum_distance_mm is None:
                        raise ValueError("proximity constraint requires maximum_distance_mm")
                    d = math.dist(endpoint(ref, constraint.component_pin), endpoint(target, constraint.target_pin))
                    limit = constraint.maximum_distance_mm
                    add("PB-PCB-004", d <= limit + _EPSILON, constraint.reason, [ref, target], d, limit, **args)
                else:
                    if constraint.minimum_distance_mm is None:
                        raise ValueError("separation constraint requires minimum_distance_mm")
                    d, limit = _gap(boxes[ref], boxes[target]), constraint.minimum_distance_mm
                    add("PB-PCB-009", d >= limit - _EPSILON, constraint.reason, [ref, target], d, limit, **args)
            elif constraint.kind is PlacementConstraintKind.FIXED:
                pose = constraint.fixed_pose
                if pose is None:
                    raise ValueError("fixed constraint requires fixed_pose")
                ok = (math.isclose(placement.x_mm, pose.x_mm, abs_tol=_EPSILON, rel_tol=0)
                      and math.isclose(placement.y_mm, pose.y_mm, abs_tol=_EPSILON, rel_tol=0)
                      and abs((placement.rotation_deg - pose.rotation_deg + 180) % 360 - 180) <= _EPSILON
                      and placement.side == pose.side)
                add("PB-PCB-010", ok, constraint.reason, [ref], **args)
            elif constraint.kind is PlacementConstraintKind.REGION:
                if constraint.region is None:
                    raise ValueError("region constraint requires region")
                add("PB-PCB-011", _inside(boxes[ref], constraint.region), constraint.reason, [ref], **args)
            elif constraint.kind is PlacementConstraintKind.ORIENTATION:
                if not constraint.allowed_rotations_deg:
                    raise ValueError("orientation constraint requires allowed_rotations_deg")
                ok = any(abs((placement.rotation_deg - angle + 180) % 360 - 180) <= _EPSILON
                         for angle in constraint.allowed_rotations_deg)
                add("PB-PCB-012", ok, constraint.reason, [ref], **args)
            elif constraint.kind is PlacementConstraintKind.KEEPOUT:
                region = resolved_keepout_region(constraint, placements)
                intruders = [other for other in refs if other != ref and _overlap(boxes[other], region)]
                add("PB-PCB-013", not intruders,
                    constraint.reason + "; component exclusion only, RF performance not verified",
                    [ref, *intruders], **args)
            else:
                raise ValueError(f"unsupported placement constraint {constraint.kind!r}")
        except (ValueError, KeyError) as exc:
            error(f"{constraint.constraint_id}: {exc}", [ref], **args)
    geometry_sources = {
        f"footprint:{fp.footprint_id}": fp.source.upstream_file_sha256
        for fp in footprints.values()
    }
    geometry_sources.update({
        f"body:{fp.footprint_id}": BODY_ENVELOPE_SOURCES[fp.footprint_id]["sha256"]
        for fp in footprints.values() if fp.footprint_id in BODY_ENVELOPE_SOURCES
    })
    return PhysicalVerificationReport(findings=findings, limitations=limitations,
                                      geometry_sources=geometry_sources)
