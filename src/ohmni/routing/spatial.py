"""Per-search obstacle snapshots with an exact, indexed collision predicate.

The grid is only a broad-phase filter. Every returned candidate is checked
using the router's original inequalities and distance calculation. Nothing
about A* ordering, cost or legal copper geometry changes.
"""

from __future__ import annotations

import math

from .models import Point, RoutingProfile

_CELL_MM = 2.0
_INDEX_EPSILON = 1e-9
_MAX_CELLS_PER_OBSTACLE = 4096
_PAD = 0
_SEGMENT = 1
_OWN_VIA = 2


class _LayerIndex:
    def __init__(self) -> None:
        self.entries: list[tuple[int, tuple[float, ...]]] = []
        self.cells: dict[tuple[int, int], list[int]] = {}
        self.overflow: list[int] = []

    def add(self, kind, values, left, bottom, right, top) -> None:
        index = len(self.entries)
        self.entries.append((kind, values))
        x0, x1 = math.floor((left - _INDEX_EPSILON) / _CELL_MM), math.floor((right + _INDEX_EPSILON) / _CELL_MM)
        y0, y1 = math.floor((bottom - _INDEX_EPSILON) / _CELL_MM), math.floor((top + _INDEX_EPSILON) / _CELL_MM)
        # A huge keepout/segment must not create an unbounded index. Testing it
        # directly on every query is conservative and keeps the same verdict.
        if (x1 - x0 + 1) * (y1 - y0 + 1) > _MAX_CELLS_PER_OBSTACLE:
            self.overflow.append(index)
            return
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                self.cells.setdefault((x, y), []).append(index)

    def candidates(self, x: float, y: float, margin: float):
        x0, x1 = math.floor((x - margin - _INDEX_EPSILON) / _CELL_MM), math.floor((x + margin + _INDEX_EPSILON) / _CELL_MM)
        y0, y1 = math.floor((y - margin - _INDEX_EPSILON) / _CELL_MM), math.floor((y + margin + _INDEX_EPSILON) / _CELL_MM)
        if (x1 - x0 + 1) * (y1 - y0 + 1) > _MAX_CELLS_PER_OBSTACLE:
            yield from self.entries
            return
        seen = set(self.overflow)
        for index in self.overflow:
            yield self.entries[index]
        for ix in range(x0, x1 + 1):
            for iy in range(y0, y1 + 1):
                for index in self.cells.get((ix, iy), ()):
                    if index not in seen:
                        seen.add(index)
                        yield self.entries[index]


class RoutingObstacles:
    """A snapshot valid for exactly one connection search.

    Rebuild after copper is added. Keepouts use the same rectangle obstacle
    representation as pads and remain active on both declared layers.
    """

    def __init__(self, net: str, profile: RoutingProfile, pads, occupied) -> None:
        self.clearance = float(profile.clearance_mm.value)
        self.via_radius = float(profile.via_diameter_mm.value) / 2
        self.own_via_spacing = float(profile.via_drill_mm.value) + .25
        self.layers = (_LayerIndex(), _LayerIndex())
        for pad_net, centre, width, height, layers in pads:
            if pad_net == net:
                continue
            x, y, half_w, half_h = centre.x_mm, centre.y_mm, width / 2, height / 2
            for layer in layers:
                self.layers[("F.Cu", "B.Cu").index(layer)].add(
                    _PAD, (x, y, half_w, half_h), x - half_w, y - half_h, x + half_w, y + half_h,
                )
        for other, segments in occupied.items():
            for start, end, layer, width in segments:
                index = self.layers[("F.Cu", "B.Cu").index(layer)]
                x, y = start.x_mm, start.y_mm
                if other == net:
                    # Evaluate Point equality once while building the snapshot,
                    # not millions of times in A*'s collision loop.
                    if start == end:
                        radius = self.own_via_spacing
                        index.add(_OWN_VIA, (x, y), x - radius, y - radius, x + radius, y + radius)
                    continue
                dx, dy = end.x_mm - x, end.y_mm - y
                half_width = width / 2
                index.add(
                    _SEGMENT, (x, y, dx, dy, dx * dx + dy * dy, half_width),
                    min(x, end.x_mm) - half_width, min(y, end.y_mm) - half_width,
                    max(x, end.x_mm) + half_width, max(y, end.y_mm) + half_width,
                )

    def blocked(self, point: Point, layer_index: int, candidate_radius: float) -> bool:
        x, y = point.x_mm, point.y_mm
        clearance = self.clearance + candidate_radius
        for kind, values in self.layers[layer_index].candidates(x, y, clearance):
            if kind == _PAD:
                px, py, half_w, half_h = values
                if abs(x - px) <= half_w + clearance and abs(y - py) <= half_h + clearance:
                    return True
            elif kind == _OWN_VIA:
                if candidate_radius >= self.via_radius:
                    px, py = values
                    distance = math.hypot(x - px, y - py)
                    if 1e-9 < distance < self.own_via_spacing:
                        return True
            else:
                px, py, dx, dy, denominator, half_width = values
                if dx == dy == 0:
                    distance = math.hypot(x - px, y - py)
                else:
                    t = max(0, min(1, ((x - px) * dx + (y - py) * dy) / denominator))
                    distance = math.hypot(x - (px + t * dx), y - (py + t * dy))
                if distance < clearance + half_width:
                    return True
        return False
