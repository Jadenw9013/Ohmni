"""Deterministic placement from electrical groups and geometric constraints.

The bounded greedy search uses functional zones, actual pad extents, and net
length as a tie-breaker. It is a placement policy, not an RF/mechanical sign-off
or a guarantee that a two-layer router can connect every accepted placement.
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ..adapters import PartCatalog
from ..domain import CircuitIR
from .footprints import footprint
from .models import (
    BoardConstraints,
    ComponentPlacement,
    PadBinding,
    PlacementConstraint,
    PlacementRequest,
)
from .models import (
    PlacementConstraintKind as Kind,
)
from .models import (
    PlacementGroupKind as GroupKind,
)
from .rules import footprint_bounds, pad_position, resolved_keepout_region, verify_physical

PLACEMENT_VERSION = "functional-groups-v1"


class PlacementFailureCode(StrEnum):
    STALE_INTENT = "stale_placement_intent"
    INVALID_INTENT = "invalid_placement_intent"
    FOOTPRINT_UNAVAILABLE = "footprint_unavailable"
    UNSUPPORTED_ORIENTATION = "unsupported_placement_orientation"
    NO_FEASIBLE_POSITION = "no_feasible_position"
    CONSTRAINTS_FAILED = "placement_constraints_failed"


class PlacementFailure(ValueError):
    def __init__(self, code: PlacementFailureCode, message: str, component_ref: str | None = None):
        super().__init__(message)
        self.code = code
        self.component_ref = component_ref


class PlacementMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    board_area_mm2: float
    component_count: int
    candidate_count: int
    # This is an unrouted estimate. Actual routed length/vias come from emitted
    # PCB copper statistics after routing, not from this placement objective.
    estimated_net_span_mm: float


class GeneratedPlacement(BaseModel):
    model_config = ConfigDict(frozen=True)
    algorithm: str = PLACEMENT_VERSION
    request_fingerprint: str
    circuit_content_hash: str
    board: BoardConstraints
    metrics: PlacementMetrics
    limitations: tuple[str, ...] = (
        "Functional zones and spacing are authored placement policy, not a global optimum.",
        "A passing placement still requires independent routing, KiCad DRC and manufacturing checks.",
        "Antenna exclusion is a geometric policy; RF performance and physical fit need hardware review.",
    )


def _box(region):
    return region.x_min_mm, region.y_min_mm, region.x_max_mm, region.y_max_mm


def _intersects(a, b, gap=0):
    return a[0] < b[2] + gap and a[2] > b[0] - gap and a[1] < b[3] + gap and a[3] > b[1] - gap


def _edge_distance(box, edge, width, height):
    distances = {"left": box[0], "top": box[1], "right": width - box[2], "bottom": height - box[3]}
    return distances[edge] if edge is not None else min(distances.values())


def _pose(ref, x, y, reason):
    return ComponentPlacement(component_ref=ref, x_mm=x, y_mm=y, reason=reason)


def _resolve(circuit, catalog):
    definitions, ids, bindings = {}, {}, []
    nets = {(pin.component, pin.pin): net.name for net in circuit.nets for pin in net.connections}
    for component in circuit.components:
        part = catalog.get(component.part_id)
        package = part.package(component.package) if part and component.package else None
        fp = footprint(package.kicad_footprint) if package and package.kicad_footprint else None
        if fp is None:
            raise PlacementFailure(PlacementFailureCode.FOOTPRINT_UNAVAILABLE,
                                   f"{component.ref} has no supported footprint geometry", component.ref)
        definitions[component.ref] = fp
        ids[component.ref] = fp.footprint_id
        bindings.extend(PadBinding(component_ref=component.ref, pin_number=p.number, pad_number=p.number,
                                   net_name=nets.get((component.ref, p.number)))
                        for p in part.pins if any(pad.number == p.number for pad in fp.pads))
    return definitions, ids, bindings


def _constraints(request):
    constraints = list(request.constraints)
    for target in request.decoupling:
        constraints.append(PlacementConstraint(
            constraint_id=f"generated-decoupling-{target.capacitor_ref}-{target.capacitor_pin}",
            kind=Kind.NEAR_COMPONENT, component_ref=target.capacitor_ref,
            component_pin=target.capacitor_pin, target_ref=target.target_ref,
            target_pin=target.target_pin, maximum_distance_mm=target.maximum_distance_mm,
            reason=target.reason, evidence=list(target.evidence),
        ))
    return constraints


def generate_placement(circuit: CircuitIR, request: PlacementRequest, catalog: PartCatalog) -> GeneratedPlacement:
    """Place one bounded request or raise a specific, non-successful refusal.

    A one-millimetre search grid keeps candidate enumeration bounded. Pin-near
    positions are additionally enumerated relative to exact target-pad centres.
    No per-reference or per-fixture coordinate table participates in placement.
    """
    try:
        request = PlacementRequest.model_validate(request.model_dump())
        return _generate_placement(circuit, request, catalog)
    except PlacementFailure:
        raise
    except (ValueError, KeyError) as error:
        raise PlacementFailure(PlacementFailureCode.INVALID_INTENT,
                               f"Placement intent or physical binding is invalid: {error}") from error


def _generate_placement(circuit, request, catalog):
    if circuit.content_hash != request.circuit_content_hash:
        raise PlacementFailure(PlacementFailureCode.STALE_INTENT, "Placement intent belongs to a different circuit")
    if request.allowed_rotations_deg != (0,):
        raise PlacementFailure(PlacementFailureCode.UNSUPPORTED_ORIENTATION,
                               "Generated placement currently supports front-side zero-degree orientation only")
    refs = {component.ref for component in circuit.components}
    owners = {ref: group for group in request.groups for ref in group.member_refs}
    if set(owners) != refs:
        raise PlacementFailure(PlacementFailureCode.INVALID_INTENT, "Functional groups must cover exactly every circuit component")
    if request.outline.width_mm > 200 or request.outline.height_mm > 200 or len(refs) > 64:
        raise PlacementFailure(PlacementFailureCode.INVALID_INTENT, "Placement search supports at most 64 parts on a 200 × 200 mm board")
    constraints = _constraints(request)
    for rule in constraints:
        if rule.component_ref not in refs or (rule.target_ref is not None and rule.target_ref not in refs):
            raise PlacementFailure(PlacementFailureCode.INVALID_INTENT, f"Constraint {rule.constraint_id} references an absent component")
        if rule.kind == Kind.ORIENTATION and 0 not in rule.allowed_rotations_deg:
            raise PlacementFailure(PlacementFailureCode.UNSUPPORTED_ORIENTATION, f"Constraint {rule.constraint_id} requires another rotation")
        if rule.fixed_pose and (rule.fixed_pose.rotation_deg != 0 or rule.fixed_pose.side != "F.Cu"):
            raise PlacementFailure(PlacementFailureCode.UNSUPPORTED_ORIENTATION, f"Constraint {rule.constraint_id} requires another pose")
    fps, ids, bindings = _resolve(circuit, catalog)
    # Repeated pad numbers (e.g. both legs of a switch terminal) identify one
    # electrical terminal. A real first land anchors the length heuristic;
    # explicit proximity constraints still require an unambiguous pad.
    net_fps = {}
    for ref, fp in fps.items():
        unique = {}
        for pad in fp.pads:
            if not pad.mechanical:
                unique.setdefault(pad.number, pad)
        net_fps[ref] = fp.model_copy(update={"pads": list(unique.values())})
    offsets = {ref: _box(footprint_bounds(fp, _pose(ref, 0, 0, "local geometry"))) for ref, fp in fps.items()}
    rules_by_ref = {ref: [rule for rule in constraints if rule.component_ref == ref] for ref in refs}
    width, height = request.outline.width_mm, request.outline.height_mm
    margin = request.minimum_edge_clearance_mm
    positions, boxes = {}, {}
    candidate_count = 0

    # Group order and fractions express reusable functional placement policy.
    # References are identities/tie-breakers; none selects a saved coordinate.
    order = {GroupKind.PROCESSOR: 0, GroupKind.CONNECTOR: 1, GroupKind.POWER: 2,
             GroupKind.SENSOR: 3, GroupKind.SPI: 3, GroupKind.GPIO: 4}
    groups = sorted(request.groups, key=lambda group: (order[group.kind], group.group_id))
    peers = {kind: [group for group in groups if group.kind == kind] for kind in GroupKind}

    def preferred_anchor(group):
        index = peers[group.kind].index(group)
        count = len(peers[group.kind])
        ref = group.anchor_ref
        if group.kind == GroupKind.PROCESSOR:
            x, y = width * .45, height * .30
        elif group.kind == GroupKind.POWER:
            x, y = width * .20, height * .80
        elif group.kind in (GroupKind.SENSOR, GroupKind.SPI):
            sensors = [g for g in groups if g.kind in (GroupKind.SENSOR, GroupKind.SPI)]
            index, count = sensors.index(group), len(sensors)
            x, y = width * .77, height * (.30 + .42 * (index + .5) / count)
        elif group.kind == GroupKind.GPIO:
            x, y = width * .12 + (index % 2) * 13, height * .27 + (index // 2) * 12
        else:
            x, y = width * (.4 + .2 * (index + .5) / count), height * .60
        local = offsets[ref]
        edge = next((rule.preferred_edge for rule in rules_by_ref[ref] if rule.kind == Kind.BOARD_EDGE), None)
        if edge == "top":
            y = margin + 2 - local[1]
        elif edge == "bottom":
            y = height - margin - local[3]
        elif edge == "left":
            x = margin - local[0]
        elif edge == "right":
            x = width - margin - local[2]
            y = height * .40
        return x, y

    def distance(rule, candidate, target):
        first = pad_position(fps[candidate.component_ref], candidate, rule.component_pin) if rule.component_pin else (candidate.x_mm, candidate.y_mm)
        second = pad_position(fps[target.component_ref], target, rule.target_pin) if rule.target_pin else (target.x_mm, target.y_mm)
        return math.dist(first, second)

    def valid(ref, candidate, box):
        if box[0] < margin or box[1] < margin or box[2] > width - margin or box[3] > height - margin:
            return False
        if any(_intersects(box, other, 1.0) for other in boxes.values()):
            return False
        for rule in rules_by_ref[ref]:
            if rule.kind == Kind.BOARD_EDGE and rule.maximum_distance_mm is not None:
                if _edge_distance(box, rule.preferred_edge, width, height) > rule.maximum_distance_mm:
                    return False
            elif rule.kind == Kind.REGION and rule.region is not None:
                region = _box(rule.region)
                if box[0] < region[0] or box[1] < region[1] or box[2] > region[2] or box[3] > region[3]:
                    return False
            elif rule.kind in (Kind.NEAR_COMPONENT, Kind.AWAY_FROM_COMPONENT) and rule.target_ref in positions:
                target_box = boxes[rule.target_ref]
                d = (math.hypot(max(box[0] - target_box[2], target_box[0] - box[2], 0),
                                max(box[1] - target_box[3], target_box[1] - box[3], 0))
                     if rule.kind == Kind.AWAY_FROM_COMPONENT
                     else distance(rule, candidate, positions[rule.target_ref]))
                if rule.maximum_distance_mm is not None and rule.kind == Kind.NEAR_COMPONENT and d > rule.maximum_distance_mm + 1e-8:
                    return False
                if rule.minimum_distance_mm is not None and rule.kind == Kind.AWAY_FROM_COMPONENT and d < rule.minimum_distance_mm - 1e-8:
                    return False
        all_positions = {**positions, ref: candidate}
        for rule in constraints:
            if rule.kind != Kind.KEEPOUT or rule.component_ref not in all_positions or rule.keepout_region is None:
                continue
            region = _box(resolved_keepout_region(rule, all_positions))
            if rule.component_ref != ref and _intersects(box, region):
                return False
            if rule.component_ref == ref and any(_intersects(other, region) for other_ref, other in boxes.items() if other_ref != ref):
                return False
        return True

    def place(ref, preferred):
        nonlocal candidate_count
        local = offsets[ref]
        fixed = next((rule.fixed_pose for rule in rules_by_ref[ref] if rule.kind == Kind.FIXED and rule.fixed_pose), None)
        near = [rule for rule in rules_by_ref[ref] if rule.kind == Kind.NEAR_COMPONENT and rule.target_ref in positions]
        points = {(round(preferred[0], 6), round(preferred[1], 6))}
        if fixed:
            points = {(fixed.x_mm, fixed.y_mm)}
        elif near:
            # Exact pin-offset candidates avoid a coarse grid excluding valid
            # 5 mm decoupling positions around fine-pitch package pads.
            rule = near[0]
            target = positions[rule.target_ref]
            centre = pad_position(fps[rule.target_ref], target, rule.target_pin) if rule.target_pin else (target.x_mm, target.y_mm)
            radius = rule.maximum_distance_mm or 0
            extent = min(math.ceil(radius + max(abs(v) for v in local)), math.ceil(max(width, height) * 2))
            dx_min = max(-extent * 2, math.ceil((margin - local[0] - centre[0]) * 2))
            dx_max = min(extent * 2, math.floor((width - margin - local[2] - centre[0]) * 2))
            dy_min = max(-extent * 2, math.ceil((margin - local[1] - centre[1]) * 2))
            dy_max = min(extent * 2, math.floor((height - margin - local[3] - centre[1]) * 2))
            points.update((round(centre[0] + dx * .5, 6), round(centre[1] + dy * .5, 6))
                          for dx in range(dx_min, dx_max + 1)
                          for dy in range(dy_min, dy_max + 1))
            preferred = centre
        else:
            points.update((float(x), float(y)) for x in range(math.ceil(margin - local[0]), math.floor(width - margin - local[2]) + 1)
                          for y in range(math.ceil(margin - local[1]), math.floor(height - margin - local[3]) + 1))
        # Resolve real connected pads once, not repeatedly inside the search.
        connected_targets = []
        for net in circuit.nets:
            own_pins = [pin.pin for pin in net.connections if pin.component == ref]
            if not own_pins or len(net.connections) > 8:
                continue
            targets = [pad_position(net_fps[pin.component], positions[pin.component], pin.pin)
                       for pin in net.connections if pin.component in positions]
            if targets:
                connected_targets.append((own_pins[0], targets))
        best = None
        for x, y in sorted(points):
            candidate_count += 1
            box = local[0] + x, local[1] + y, local[2] + x, local[3] + y
            candidate = _pose(ref, x, y, f"Generated {owners[ref].kind.value} placement: {owners[ref].reason}")
            if not valid(ref, candidate, box):
                continue
            score = math.dist((x, y), preferred)
            for pin, targets in connected_targets:
                source = pad_position(net_fps[ref], candidate, pin)
                score += .20 * min(math.dist(source, target) for target in targets)
            key = round(score, 8), x, y
            if best is None or key < best[0]:
                best = key, candidate, box
        if best is None:
            raise PlacementFailure(PlacementFailureCode.NO_FEASIBLE_POSITION,
                                   f"No position satisfies the board, spacing and requested constraints for {ref}", ref)
        _, positions[ref], boxes[ref] = best

    for group in groups:
        place(group.anchor_ref, preferred_anchor(group))
    pending = [ref for group in groups for ref in group.member_refs if ref != group.anchor_ref]
    # Hard pad-proximity requirements get space before unconstrained passives.
    pending.sort(key=lambda ref: (min((rule.maximum_distance_mm for rule in rules_by_ref[ref]
                                     if rule.kind == Kind.NEAR_COMPONENT and rule.maximum_distance_mm is not None),
                                    default=float("inf")), ref))
    while pending:
        ready = next((ref for ref in pending if all(rule.target_ref in positions for rule in rules_by_ref[ref]
                                                  if rule.kind == Kind.NEAR_COMPONENT and rule.target_ref)), None)
        if ready is None:
            raise PlacementFailure(PlacementFailureCode.INVALID_INTENT, "Cyclic or unresolved component proximity targets")
        anchor = positions[owners[ready].anchor_ref]
        place(ready, (anchor.x_mm, anchor.y_mm))
        pending.remove(ready)
    board = BoardConstraints(outline=request.outline, minimum_edge_clearance_mm=margin,
                             placements=[positions[ref] for ref in sorted(positions)], placement_constraints=constraints)
    report = verify_physical(circuit, board, ids, bindings)
    if not report.passed:
        failed = [finding.description for finding in report.findings if finding.status.value != "pass"]
        raise PlacementFailure(PlacementFailureCode.CONSTRAINTS_FAILED, "; ".join(failed))
    span = 0.0
    for net in circuit.nets:
        points = [pad_position(net_fps[pin.component], positions[pin.component], pin.pin) for pin in net.connections]
        if points:
            span += max(p[0] for p in points) - min(p[0] for p in points) + max(p[1] for p in points) - min(p[1] for p in points)
    return GeneratedPlacement(
        request_fingerprint=request.content_hash, circuit_content_hash=circuit.content_hash, board=board,
        metrics=PlacementMetrics(board_area_mm2=width * height, component_count=len(refs),
                                 candidate_count=candidate_count, estimated_net_span_mm=round(span, 6)),
    )
