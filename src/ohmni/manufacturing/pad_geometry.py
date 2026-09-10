"""Measurements of the compiler's emitted copper lands and component holes.

Route clearance alone does not constrain the fixed copper inside a footprint.
For orthogonal placements, supported pads are rectangles offset by a disk:
that gives exact distances for rect, roundrect, circle and oval copper lands.
"""

from dataclasses import dataclass
from itertools import combinations
from math import cos, hypot, isclose, radians, sin

from ..physical.footprints import footprint


@dataclass(frozen=True)
class PadMeasurements:
    minimum_gap_mm: float | None
    closest_pair: tuple[str, str] | None
    minimum_drill_mm: float | None
    copper_pad_count: int
    slot_count: int
    minimum_slot_width_mm: float | None
    nonplated_hole_count: int


def measure_pads(pcb, board) -> PadMeasurements:
    """Read the same source-pinned pad dimensions used by PCB emission.

    Unconnected and mechanical copper still count. Only pads on the same
    explicitly named electrical net are exempt from a mutual-clearance check.
    Unsupported/missing geometry fails closed through the caller's UNKNOWN.
    """
    if not pcb.lineage_is_current:
        raise ValueError("PCB lineage is stale")
    if board.content_hash != pcb.constraints_hash or board.content_hash != pcb.compilation.constraints_hash:
        raise ValueError("Placement does not match the compiled PCB")
    placements = {item.component_ref: item for item in board.placements}
    bindings = pcb.compilation.footprint_bindings
    nets = {(item.component_ref, item.pad_number): item.net_name
            for item in pcb.compilation.pad_bindings}
    if not bindings or {item.component_ref for item in bindings} != set(placements):
        raise ValueError("Complete placed footprint geometry is required")
    lands, drills, slots = [], [], []
    nonplated_hole_count = 0
    for binding in bindings:
        definition = footprint(binding.footprint_id)
        if definition is None or definition.source.upstream_file_sha256 != binding.source.upstream_file_sha256:
            raise ValueError("Footprint geometry does not match its recorded source")
        if getattr(binding, "geometry_fingerprint", None) != definition.content_hash:
            raise ValueError("Local footprint geometry does not match the compiled PCB")
        place = placements[binding.component_ref]
        if place.side != "F.Cu" or not isclose(place.rotation_deg % 90, 0, abs_tol=1e-9):
            raise ValueError("Pad measurement requires front-side orthogonal geometry")
        angle = radians(place.rotation_deg)
        for ordinal, pad in enumerate(definition.pads):
            if pad.kind not in {"smd", "thru_hole", "np_thru_hole"}:
                raise ValueError(f"Unsupported emitted pad kind: {pad.kind}")
            if pad.kind in {"thru_hole", "np_thru_hole"}:
                if pad.drill is None:
                    raise ValueError("Component hole has no explicit source drill dimensions")
                minor = min(pad.drill.width_mm, pad.drill.height_mm)
                drills.append(minor)
                if pad.drill.shape == "oval":
                    slots.append(minor)
            if pad.kind == "np_thru_hole":
                nonplated_hole_count += 1
                continue  # A nonplated locating hole is a hole, not a copper land.
            width, height = pad.width_mm, pad.height_mm
            radius = {"rect": 0, "roundrect": min(width, height) * .2,
                      "circle": min(width, height) / 2, "oval": min(width, height) / 2}.get(pad.shape)
            if radius is None or (pad.shape == "circle" and not isclose(width, height)):
                raise ValueError(f"Unsupported emitted pad shape: {pad.shape}")
            if round(place.rotation_deg / 90) % 2:
                width, height = height, width
            x = round(place.x_mm + pad.x_mm*cos(angle) - pad.y_mm*sin(angle), 6)
            y = round(place.y_mm + pad.x_mm*sin(angle) + pad.y_mm*cos(angle), 6)
            lands.append((f"{binding.component_ref}.{pad.number}#{ordinal}",
                          nets.get((binding.component_ref, pad.number)), x, y,
                          width / 2 - radius, height / 2 - radius, radius))
    closest, minimum = None, None
    for a, b in combinations(lands, 2):
        if a[1] is not None and a[1] == b[1]:
            continue
        gap = max(0, hypot(max(0, abs(a[2]-b[2])-a[4]-b[4]),
                           max(0, abs(a[3]-b[3])-a[5]-b[5])) - a[6] - b[6])
        if minimum is None or gap < minimum:
            minimum, closest = gap, (a[0], b[0])
    return PadMeasurements(round(minimum, 6) if minimum is not None else None,
                           closest, min(drills) if drills else None, len(lands),
                           len(slots), min(slots) if slots else None, nonplated_hole_count)
