"""Fine-pitch entry, local-connection fallback, and honest search diagnostics."""

import pytest

from ohmni.domain import CircuitComponent, CircuitIR, EventKind, Net, PinRef, Quantity
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.models import BoardConstraints, BoardOutline, ComponentPlacement
from ohmni.physical.placement import generate_placement
from ohmni.routing.models import Point, RoutingConstraints, RoutingFailureReason, RoutingProfile
from ohmni.routing.router import DeterministicRouter, _segment_pad_distance
from ohmni.routing.spatial import RoutingObstacles
from ohmni.routing.verifier import verify_routing
from ohmni.synthesis import I2cSensorSlot, SynthesisBrief, synthesize


def _compile(circuit, board, catalog, root):
    schematic = KiCadSchematicCompiler(catalog).compile(circuit, root / "board.kicad_sch")
    placed = KiCadPcbCompiler(catalog).compile(circuit, schematic, board, root / "board.placed.kicad_pcb")
    return placed


def _small_board(tmp_path, catalog):
    circuit = CircuitIR(ir_id="bounded-retry", name="Bounded routing retry",
        components=[CircuitComponent(ref=f"R{i}", part_id="GENERIC_RESISTOR", package="0805",
                                     value=Quantity.ohms(1000)) for i in (1, 2, 3)],
        nets=[Net(name=name, connections=[PinRef(component=f"R{i}", pin=pin) for i in (1, 2, 3)])
              for name, pin in (("A", "1"), ("B", "2"))])
    board = BoardConstraints(outline=BoardOutline(width_mm=40, height_mm=30),
        placements=[ComponentPlacement(component_ref=f"R{i}", x_mm=x, y_mm=y, reason="Test pose")
                    for i, x, y in ((1, 6, 6), (2, 34, 6), (3, 20, 23))])
    return circuit, _compile(circuit, board, catalog, tmp_path), board


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_fine_pitch_entries_and_entire_stubs_clear_adjacent_foreign_pads(tmp_path, catalog, rotation):
    circuit = CircuitIR(ir_id="fine-pitch", name="Fine-pitch pad entry",
        components=[CircuitComponent(ref="U1", part_id="TMP102AIDRLR", package="SOT-563")],
        nets=[Net(name=f"N{pin}", connections=[PinRef(component="U1", pin=str(pin))]) for pin in range(1, 7)])
    board = BoardConstraints(outline=BoardOutline(width_mm=20, height_mm=20),
        placements=[ComponentPlacement(component_ref="U1", x_mm=10, y_mm=10,
                                       rotation_deg=rotation, reason="Fine-pitch orientation")])
    placed = _compile(circuit, board, catalog, tmp_path)
    router, profile = DeterministicRouter(), RoutingProfile()
    centres = router._pad_centres(placed, board)
    pads = router._pad_obstacles(placed, board, centres)
    blocked = []
    access = router._pad_access(placed, board, centres, profile, on_blocked=blocked.append)
    assert not blocked
    for key, binding, _ in router._physical_pads(placed):
        obstacles = RoutingObstacles(binding.net_name, profile, pads, {})
        assert not obstacles.blocked(access[key], 0, .125)
        # Pin pitch remains 0.5 mm; the route still needs 0.2 mm to foreign
        # copper. No package geometry or clearance value is reduced.
        for other, point, width, height, _ in pads:
            if other != binding.net_name:
                assert _segment_pad_distance(centres[key], access[key], point, width, height) >= .325-1e-6
    assert profile.clearance_mm.value == .2


def test_stub_rectangle_check_detects_obstruction_between_clear_endpoints():
    start, end = Point(x_mm=2, y_mm=5), Point(x_mm=8, y_mm=5)
    assert _segment_pad_distance(start, end, Point(x_mm=5, y_mm=5), 1, 1) == 0
    assert _segment_pad_distance(start, end, Point(x_mm=5, y_mm=6), 1, 1) == .5


def test_blocked_entry_is_reported_without_exhausting_the_search_space():
    board = BoardConstraints(outline=BoardOutline(width_mm=20, height_mm=20), placements=[])
    goal = Point(x_mm=15, y_mm=10)
    reasons = []
    result = DeterministicRouter()._find("N", Point(x_mm=5, y_mm=10), goal,
        board, RoutingProfile(), [("OTHER", goal, 1, 1, ("F.Cu",))], {},
        on_failure=lambda reason, expanded: reasons.append((reason, expanded)))
    assert result is None
    assert reasons == [(RoutingFailureReason.PAD_ACCESS_BLOCKED, 0)]


def test_node_limit_has_distinct_reason_and_counts_both_bounded_attempts(tmp_path, catalog):
    circuit, placed, board = _small_board(tmp_path, catalog)
    profile = RoutingProfile()
    profile.maximum_expanded_nodes = profile.maximum_expanded_nodes.model_copy(update={"value": 1})
    plan = DeterministicRouter().route(circuit, placed, board, RoutingConstraints(profile=profile))
    assert {failure.reason for failure in plan.failures} == {RoutingFailureReason.SEARCH_LIMIT_REACHED}
    assert plan.statistics.reroute_count == 1
    assert plan.statistics.expanded_nodes == plan.statistics.routing_attempts == 4
    assert not plan.tracks
    assert not verify_routing(circuit, placed, board, plan).passed
    retry = next(event for event in plan.events if event.kind is EventKind.REROUTE_ATTEMPTED)
    assert all(failure["reason"] == "search_limit_reached" for failure in retry.payload["retry_failures"])


def test_successful_first_attempt_keeps_exact_geometry_and_skips_retry(tmp_path, catalog):
    circuit, placed, board = _small_board(tmp_path, catalog)
    router = DeterministicRouter()
    first = router._route_attempt(circuit, placed, board, None, deadline=None,
                                 clock=lambda: 0, cancelled=None)
    result = router.route(circuit, placed, board)
    assert not first.failures
    assert result.content_hash == first.content_hash
    assert result.statistics.reroute_count == 0
    assert not any(event.kind is EventKind.REROUTE_ATTEMPTED for event in result.events)


def test_retry_receives_the_original_deadline_and_preserves_timeout_diagnostics(tmp_path, catalog):
    circuit, placed, board = _small_board(tmp_path, catalog)
    current_time = 0
    deadlines = []
    class ExpireOnRetry(DeterministicRouter):
        def _route_attempt(self, *args, **kwargs):
            nonlocal current_time
            deadlines.append(kwargs["deadline"])
            if kwargs.get("shortest_first"):
                current_time = 20
            return super()._route_attempt(*args, **kwargs)
    profile = RoutingProfile()
    profile.maximum_expanded_nodes = profile.maximum_expanded_nodes.model_copy(update={"value": 1})
    plan = ExpireOnRetry().route(circuit, placed, board, RoutingConstraints(profile=profile),
                                time_budget_seconds=20, clock=lambda: current_time)
    assert deadlines == [20, 20]
    retry = next(event for event in plan.events if event.kind is EventKind.REROUTE_ATTEMPTED)
    assert all(failure["reason"] == "routing_incomplete" for failure in retry.payload["retry_failures"])
    assert plan.statistics.reroute_count == 1
    assert not verify_routing(circuit, placed, board, plan).passed


def test_exact_sensor_trio_routes_without_relaxing_any_constraint(tmp_path, catalog):
    brief = SynthesisBrief(project_name="Sensor trio · browser check", sensors=(
        I2cSensorSlot(part_id="BME280"), I2cSensorSlot(part_id="BME280"),
        I2cSensorSlot(part_id="TMP102AIDRLR")), status_led_count=1, include_programming_header=True)
    result = synthesize(brief, catalog)
    assert result.accepted
    generated = generate_placement(result.circuit, result.placement_request, catalog)
    placed = _compile(result.circuit, generated.board, catalog, tmp_path)
    plan = DeterministicRouter().route(result.circuit, placed, generated.board, time_budget_seconds=60)
    report = verify_routing(result.circuit, placed, generated.board, plan)
    (tmp_path / "routing-plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    (tmp_path / "routing-verification.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    assert not plan.failures
    assert report.passed
    assert sum(len(net.paths) for net in plan.routed_nets) == plan.statistics.required_connections == 70
    assert plan.statistics.reroute_count == 1
    assert plan.profile == RoutingProfile()
    assert plan.source_constraints_hash == generated.board.content_hash
    assert plan.circuit_content_hash == result.circuit.content_hash
    retry = next(event for event in plan.events if event.kind is EventKind.REROUTE_ATTEMPTED)
    assert {failure["net_name"] for failure in retry.payload["first_failures"]} == {"GND", "3V3"}
    assert retry.payload["selected_attempt"] == 2
    # Statistics include work discarded by the fallback, while displayed
    # copper metrics describe only the selected physical route.
    failed_expansions = sum(event.payload["expanded_nodes"] for event in plan.events
                            if event.kind is EventKind.ROUTE_SEARCH_FAILED)
    assert failed_expansions > 0
    assert plan.statistics.expanded_nodes > failed_expansions
    assert plan.statistics.track_segment_count == len(plan.tracks)
    assert plan.statistics.via_count == len(plan.vias)
    assert plan.statistics.total_track_length_mm == pytest.approx(sum(track.length_mm for track in plan.tracks), abs=1e-6)
