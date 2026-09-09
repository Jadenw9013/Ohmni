"""The spatial broad phase must preserve the exact original copper predicate."""

from __future__ import annotations

import math
import random

import pytest

from ohmni.domain import CircuitComponent, CircuitIR, Net, PinRef, Quantity
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.models import BoardConstraints, BoardOutline, ComponentPlacement
from ohmni.routing import spatial
from ohmni.routing.models import Point, RoutingProfile
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.spatial import RoutingObstacles
from ohmni.routing.verifier import verify_routing


def _point(x, y):
    return Point(x_mm=x, y_mm=y)


def _linear(net, profile, pads, occupied, point, layer, radius):
    return DeterministicRouter._blocked(net, point, layer, profile, pads, occupied,
                                        _point(0, 0), _point(1, 1), radius)


def test_index_matches_original_predicate_on_random_obstacles_and_queries():
    rng = random.Random(10303)
    profile = RoutingProfile()
    pads = [(rng.choice((None, "OWN", "FOREIGN")), _point(rng.uniform(-10, 60), rng.uniform(-10, 60)),
             rng.uniform(.1, 6), rng.uniform(.1, 6), rng.choice((("F.Cu",), ("B.Cu",), ("F.Cu", "B.Cu"))))
            for _ in range(65)]
    occupied = {"OWN": [], "FOREIGN": [], "SECOND": []}
    for _ in range(100):
        a = _point(rng.uniform(-10, 60), rng.uniform(-10, 60))
        b = a if rng.random() < .3 else _point(a.x_mm + rng.uniform(-15, 15), a.y_mm + rng.uniform(-15, 15))
        occupied[rng.choice(tuple(occupied))].append((a, b, rng.choice(("F.Cu", "B.Cu")), rng.uniform(.1, 1.8)))
    indexed = RoutingObstacles("OWN", profile, pads, occupied)
    results = set()
    for _ in range(4000):
        point = _point(rng.uniform(-15, 65), rng.uniform(-15, 65))
        layer, radius = rng.randrange(2), rng.choice((.05, .125, .4, .9, 2.5))
        expected = _linear("OWN", profile, pads, occupied, point, layer, radius)
        assert indexed.blocked(point, layer, radius) is expected
        results.add(expected)
    assert results == {False, True}


def test_boundary_inclusive_pad_and_strict_segment_clearance_are_unchanged():
    profile = RoutingProfile()
    pads = [("FOREIGN", _point(2, 2), 1, 1, ("F.Cu",))]
    occupied = {"FOREIGN": [(_point(2, 5), _point(6, 5), "B.Cu", .25)]}
    indexed = RoutingObstacles("OWN", profile, pads, occupied)
    radius = .125
    pad_edge = 2 + .5 + .2 + radius
    track_edge = 5 + .25 / 2 + .2 + radius
    for x in (math.nextafter(pad_edge, -math.inf), pad_edge, math.nextafter(pad_edge, math.inf)):
        point = _point(x, 2)
        assert indexed.blocked(point, 0, radius) is _linear("OWN", profile, pads, occupied, point, 0, radius)
    for y in (math.nextafter(track_edge, -math.inf), track_edge, math.nextafter(track_edge, math.inf)):
        point = _point(4, y)
        assert indexed.blocked(point, 1, radius) is _linear("OWN", profile, pads, occupied, point, 1, radius)


def test_same_net_via_spacing_preserves_coincident_and_small_radius_exceptions():
    profile = RoutingProfile()
    occupied = {"OWN": [(_point(4, 4), _point(4, 4), layer, .8) for layer in ("F.Cu", "B.Cu")]}
    indexed = RoutingObstacles("OWN", profile, [], occupied)
    for offset in (0, 1e-10, 1e-9, .1, .649999999, .65, .650000001):
        for radius in (.125, .399999, .4, .8):
            point = _point(4 + offset, 4)
            for layer in (0, 1):
                assert indexed.blocked(point, layer, radius) is _linear(
                    "OWN", profile, [], occupied, point, layer, radius,
                )


def test_large_keepout_and_query_use_bounded_fallback_without_changing_verdict():
    profile = RoutingProfile()
    pads = [(None, _point(0, 0), 1e6, 1e6, ("F.Cu", "B.Cu"))]
    indexed = RoutingObstacles("OWN", profile, pads, {})
    assert all(len(index.cells) == 0 and len(index.overflow) == 1 for index in indexed.layers)
    for point, radius in ((_point(0, 0), .4), (_point(2e6, 2e6), .4), (_point(2e6, 0), 3e6)):
        assert indexed.blocked(point, 0, radius) is _linear("OWN", profile, pads, {}, point, 0, radius)


def test_obstacle_snapshot_is_rebuilt_after_new_copper():
    profile = RoutingProfile()
    occupied = {"FOREIGN": []}
    old = RoutingObstacles("OWN", profile, [], occupied)
    point = _point(3, 3)
    occupied["FOREIGN"].append((point, point, "F.Cu", .8))
    new = RoutingObstacles("OWN", profile, [], occupied)
    assert not old.blocked(point, 0, .125)
    assert new.blocked(point, 0, .125)


@pytest.mark.parametrize("rotation", [0, 90])
def test_indexed_search_has_identical_geometry_to_linear_obstacle_search(tmp_path, catalog, monkeypatch, rotation):
    circuit = CircuitIR(
        ir_id="spatial-equivalence", name="Obstacle-index equivalence",
        components=[CircuitComponent(ref=f"R{i}", part_id="GENERIC_RESISTOR", package="0805",
                                      value=Quantity.ohms(1000)) for i in range(1, 5)],
        nets=[Net(name=name, connections=[PinRef(component=f"R{i}", pin=pin) for i in range(1, 5)])
              for name, pin in (("A", "1"), ("B", "2"))],
    )
    board = BoardConstraints(outline=BoardOutline(width_mm=32, height_mm=26), placements=[
        ComponentPlacement(component_ref=f"R{i}", x_mm=x, y_mm=y,
                           rotation_deg=rotation if i == 1 else 0, reason="equivalence test")
        for i, x, y in ((1, 5, 5), (2, 27, 5), (3, 5, 21), (4, 27, 21))
    ])
    schematic = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "board.kicad_sch")
    placed = KiCadPcbCompiler(catalog).compile(circuit, schematic, board, tmp_path / "board.kicad_pcb")
    indexed = DeterministicRouter().route(circuit, placed, board)

    class LinearObstacles:
        def __init__(self, net, profile, pads, occupied):
            self.inputs = net, profile, pads, occupied

        def blocked(self, point, layer_index, candidate_radius):
            return _linear(*self.inputs, point, layer_index, candidate_radius)

    monkeypatch.setattr(spatial, "RoutingObstacles", LinearObstacles)
    linear = DeterministicRouter().route(circuit, placed, board)
    assert not linear.failures
    assert verify_routing(circuit, placed, board, indexed).passed
    assert indexed.model_dump_json(exclude={"events"}) == linear.model_dump_json(exclude={"events"})
    assert indexed.content_hash == linear.content_hash
    assert [event.model_dump(exclude={"occurred_at"}) for event in indexed.events] == [
        event.model_dump(exclude={"occurred_at"}) for event in linear.events
    ]
