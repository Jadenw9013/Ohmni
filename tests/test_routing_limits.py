"""Bounded execution and geometry regression tests for the deterministic router."""

from itertools import pairwise

import pytest

from ohmni.domain import CircuitComponent, CircuitIR, Net, PinRef, Quantity
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.models import (
    BoardConstraints,
    BoardOutline,
    ComponentPlacement,
    PlacementConstraint,
    PlacementConstraintKind,
    PlacementRegion,
)
from ohmni.routing.models import (
    NetRoutingConstraint,
    Point,
    RoutingConstraints,
    RoutingFailureReason,
    RoutingProfile,
)
from ohmni.routing.router import DeterministicRouter, _segment_in_keepout
from ohmni.routing.verifier import verify_routing


def _placed(tmp_path, catalog, *, rotation=0, keepout=False):
    circuit = CircuitIR(ir_id="routing-test", name="Three-node routing test",
        components=[CircuitComponent(ref=f"R{i}", part_id="GENERIC_RESISTOR", package="0805", value=Quantity.ohms(1000))
                    for i in (1,2,3)],
        nets=[Net(name=name, connections=[PinRef(component=f"R{i}", pin=pin) for i in (1,2,3)])
              for name,pin in (("A","1"),("B","2"))])
    regions = [PlacementConstraint(constraint_id="antenna", kind=PlacementConstraintKind.KEEPOUT,
               component_ref="R3", keepout_region=PlacementRegion(x_min_mm=17,y_min_mm=3,x_max_mm=23,y_max_mm=9),
               reason="Test absolute copper exclusion region")] if keepout else []
    board = BoardConstraints(outline=BoardOutline(width_mm=40,height_mm=30),
        placements=[ComponentPlacement(component_ref=f"R{i}", x_mm=x,y_mm=y,
                                       rotation_deg=rotation if i==1 else 0, reason="Test placement")
                    for i,x,y in ((1,6,6),(2,34,6),(3,20,23))], placement_constraints=regions)
    schematic = KiCadSchematicCompiler(catalog).compile(circuit,tmp_path/"circuit.kicad_sch")
    placed = KiCadPcbCompiler(catalog).compile(circuit,schematic,board,tmp_path/"placed.kicad_pcb")
    return circuit,placed,board


def _placed_button(tmp_path, catalog):
    circuit = CircuitIR(ir_id="physical-terminal-test", name="Button physical terminal routing",
        components=[CircuitComponent(ref="SW1",part_id="GENERIC_MOMENTARY_BUTTON",package="6mm-THT"),
                    CircuitComponent(ref="R1",part_id="GENERIC_RESISTOR",package="0805",value=Quantity.ohms(10000))],
        nets=[Net(name=name,connections=[PinRef(component="SW1",pin=pin),PinRef(component="R1",pin=pin)])
              for name,pin in (("BUTTON","1"),("GND","2"))])
    board = BoardConstraints(outline=BoardOutline(width_mm=40,height_mm=30),
        placements=[ComponentPlacement(component_ref=ref,x_mm=x,y_mm=12,reason="Physical terminal regression")
                    for ref,x in (("SW1",12),("R1",28))])
    schematic = KiCadSchematicCompiler(catalog).compile(circuit,tmp_path/"button.kicad_sch")
    placed = KiCadPcbCompiler(catalog).compile(circuit,schematic,board,tmp_path/"button.placed.kicad_pcb")
    return circuit,schematic,placed,board


def test_every_duplicate_numbered_physical_land_requires_real_copper(tmp_path,catalog):
    circuit,_schematic,placed,board = _placed_button(tmp_path,catalog)
    plan = DeterministicRouter().route(circuit,placed,board)
    assert not plan.failures and plan.statistics.required_connections == 4
    assert verify_routing(circuit,placed,board,plan).passed
    for net,pin in (("BUTTON","1"),("GND","2")):
        routed = next(item for item in plan.routed_nets if item.net_name == net)
        assert set(routed.terminal_pads) == {f"R1.{pin}",f"SW1.{pin}",f"SW1.{pin}#2"}
    centres = DeterministicRouter._pad_centres(placed,board)
    assert centres[("SW1","1")] != centres[("SW1","1#2")]
    # A legacy plan that claims the electrical terminal is connected while
    # omitting its second physical leg must fail regardless of its statistics.
    altered = plan.model_copy(deep=True)
    for routed in altered.routed_nets:
        routed.paths = [path for path in routed.paths if "#2" not in path.source_pad+path.target_pad]
        routed.terminal_pads = [name for name in routed.terminal_pads if "#2" not in name]
    report = verify_routing(circuit,placed,board,altered)
    missing = next(finding for finding in report.findings if finding.rule_id == "PB-ROUTE-001")
    assert missing.status.value == "fail" and set(missing.net_names) == {"BUTTON","GND"}


@pytest.mark.kicad
def test_duplicate_numbered_button_lands_close_real_kicad_drc(tmp_path,catalog):
    from ohmni.adapters.tools import find_kicad_cli
    from ohmni.eda.kicad import KiCadCliAdapter
    from ohmni.eda.pcb_models import DrcStatus
    if find_kicad_cli() is None:
        pytest.skip("KiCad unavailable")
    circuit,schematic,placed,board = _placed_button(tmp_path,catalog)
    plan = DeterministicRouter().route(circuit,placed,board)
    assert not plan.failures and verify_routing(circuit,placed,board,plan).passed
    routed = KiCadPcbCompiler(catalog).compile(circuit,schematic,board,tmp_path/"button.kicad_pcb",plan)
    drc = KiCadCliAdapter().run_drc(routed)
    assert drc.status is DrcStatus.PASS and not drc.findings and not drc.unconnected_items


def test_zero_budget_marks_all_nets_unresolved_without_a_fake_completed_net(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog)
    plan = DeterministicRouter().route(circuit,placed,board,time_budget_seconds=0,clock=lambda:0)
    assert {failure.net_name for failure in plan.failures} == {net.name for net in circuit.nets}
    assert all(failure.reason is RoutingFailureReason.ROUTING_INCOMPLETE for failure in plan.failures)
    assert plan.statistics.routing_attempts == plan.statistics.routed_net_count == 0
    assert plan.statistics.unresolved_net_count == 2
    assert not plan.tracks and not plan.vias
    assert not verify_routing(circuit,placed,board,plan).passed


def test_deadline_is_checked_inside_astar_with_a_deterministic_clock(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog)
    ticks = iter(range(100))
    plan = DeterministicRouter().route(circuit,placed,board,time_budget_seconds=5,clock=lambda:next(ticks))
    assert plan.statistics.routing_attempts == 1
    assert 0 < plan.statistics.expanded_nodes < 5
    assert plan.statistics.unresolved_net_count == 2
    assert all(failure.reason is RoutingFailureReason.ROUTING_INCOMPLETE for failure in plan.failures)
    assert not plan.tracks


def test_cancel_between_connections_preserves_real_partial_work_and_names_every_open_net(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog)
    cancelled = False
    class StopAfterFirstConnection(DeterministicRouter):
        def _find(self,*args,**kwargs):
            nonlocal cancelled
            result = super()._find(*args,**kwargs)
            assert result is not None
            cancelled = True
            return result
    plan = StopAfterFirstConnection().route(circuit,placed,board,cancelled=lambda:cancelled)
    assert plan.statistics.routing_attempts == 1
    assert len(plan.routed_nets[0].paths) == 1
    assert plan.statistics.routed_net_count == 0
    assert {failure.net_name for failure in plan.failures} == {"A","B"}
    assert plan.tracks


def test_unbudgeted_runs_never_read_the_clock_and_are_geometry_deterministic(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog)
    def forbidden_clock():
        raise AssertionError("an unbudgeted run must remain independent of wall-clock time")
    first = DeterministicRouter().route(circuit,placed,board,clock=forbidden_clock)
    second = DeterministicRouter().route(circuit,placed,board,clock=forbidden_clock)
    assert not first.failures
    assert first.content_hash == second.content_hash
    assert first.tracks == second.tracks and first.vias == second.vias


@pytest.mark.parametrize("rotation,direction", [(0,(-1,0)),(90,(0,-1)),(180,(1,0)),(270,(0,1))])
def test_orthogonal_pad_rectangles_and_breakout_directions_rotate_with_footprint(tmp_path,catalog,rotation,direction):
    _,placed,board = _placed(tmp_path,catalog,rotation=rotation)
    centres = DeterministicRouter._pad_centres(placed,board)
    access = DeterministicRouter._pad_access(placed,board,centres,RoutingProfile())
    centre,entry = centres[("R1","1")],access[("R1","1")]
    assert (entry.x_mm-centre.x_mm)*direction[0]+(entry.y_mm-centre.y_mm)*direction[1] > 0
    obstacles = DeterministicRouter._pad_obstacles(placed,board,centres)
    obstacle = next(item for item in obstacles if item[1] == centre)
    assert obstacle[2:4] == ((1.4,1.0) if rotation in (90,270) else (1.0,1.4))


def test_nonorthogonal_placements_are_explicitly_refused(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog,rotation=45)
    plan = DeterministicRouter().route(circuit,placed,board)
    assert len(plan.failures) == len(circuit.nets)
    assert all(failure.reason is RoutingFailureReason.UNSUPPORTED_GEOMETRY for failure in plan.failures)
    assert not plan.tracks


@pytest.mark.parametrize("limit,found", [(0,False),(1,False),(2,True),(4,True)])
def test_astar_never_exceeds_the_configured_layer_transition_limit(limit,found):
    board = BoardConstraints(outline=BoardOutline(width_mm=20,height_mm=20),placements=[])
    profile = RoutingProfile()
    profile.maximum_vias_per_connection = profile.maximum_vias_per_connection.model_copy(update={"value":limit})
    barrier = {"OTHER":[(Point(x_mm=10,y_mm=.5),Point(x_mm=10,y_mm=19.5),"F.Cu",.25)]}
    result = DeterministicRouter()._find("N",Point(x_mm=2,y_mm=10),Point(x_mm=18,y_mm=10),board,profile,[],barrier)
    assert (result is not None) is found
    if result:
        assert sum(a.layer != b.layer for a,b in pairwise(result[0])) <= limit


def test_search_clearance_uses_the_actual_requested_track_width():
    board = BoardConstraints(outline=BoardOutline(width_mm=20,height_mm=20),placements=[])
    walls = [(None,Point(x_mm=10,y_mm=y),40,9.5,("F.Cu","B.Cu")) for y in (4.75,15.25)]
    router = DeterministicRouter()
    args = ("N",Point(x_mm=2,y_mm=10),Point(x_mm=18,y_mm=10),board,RoutingProfile(),walls,{})
    assert router._find(*args,width_mm=.25) is not None
    assert router._find(*args,width_mm=1) is None


def test_net_width_and_soft_layer_preference_are_retained_and_applied(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog)
    constraints = RoutingConstraints(nets=[NetRoutingConstraint(net_name="A",width_mm=.6,preferred_layer="B.Cu")])
    plan = DeterministicRouter().route(circuit,placed,board,constraints)
    assert not plan.failures
    assert plan.net_constraints == constraints.nets
    tracks = [track for track in plan.tracks if track.net_name == "A"]
    assert tracks and all(track.width_mm == .6 for track in tracks)
    assert any(track.layer == "B.Cu" for track in tracks)
    assert verify_routing(circuit,placed,board,plan).passed


def test_copper_and_vias_avoid_keepouts_and_verifier_rejects_intrusion(tmp_path,catalog):
    circuit,placed,board = _placed(tmp_path,catalog,keepout=True)
    plan = DeterministicRouter().route(circuit,placed,board)
    assert not plan.failures
    region = board.placement_constraints[0].keepout_region
    assert all(not _segment_in_keepout(track.start,track.end,region,track.width_mm/2) for track in plan.tracks)
    assert all(not _segment_in_keepout(via.position,via.position,region,via.diameter_mm/2) for via in plan.vias)
    assert verify_routing(circuit,placed,board,plan).passed
    altered = plan.model_copy(deep=True)
    path = next(path for net in altered.routed_nets for path in net.paths if path.tracks)
    path.tracks[0] = path.tracks[0].model_copy(update={"start":Point(x_mm=20,y_mm=6)})
    report = verify_routing(circuit,placed,board,altered)
    assert any(finding.rule_id == "PB-ROUTE-010" and finding.status.value == "fail" for finding in report.findings)


@pytest.mark.parametrize("field,value", [("grid_mm",0),("grid_mm",float("nan")),("clearance_mm",-1),
    ("maximum_expanded_nodes",1.5),("maximum_vias_per_connection",-1)])
def test_invalid_profile_numbers_are_refused(field,value):
    profile = RoutingProfile().model_dump()
    profile[field]["value"] = value
    with pytest.raises(ValueError):
        RoutingProfile.model_validate(profile)


def test_invalid_per_net_intent_is_refused_instead_of_ignored(tmp_path,catalog):
    with pytest.raises(ValueError,match="preferred layer"):
        NetRoutingConstraint(net_name="A",preferred_layer="In1.Cu")
    with pytest.raises(ValueError,match="duplicate"):
        RoutingConstraints(nets=[NetRoutingConstraint(net_name="A")]*2)
    with pytest.raises(ValueError,match="minimum"):
        RoutingConstraints(nets=[NetRoutingConstraint(net_name="A",width_mm=.1)])
    circuit,placed,board = _placed(tmp_path,catalog)
    with pytest.raises(ValueError,match="unknown nets"):
        DeterministicRouter().route(circuit,placed,board,RoutingConstraints(nets=[NetRoutingConstraint(net_name="absent")]))
    plan = DeterministicRouter().route(circuit,placed,board)
    altered = plan.model_copy(update={"net_constraints":[NetRoutingConstraint(net_name="absent",width_mm=.6)]})
    assert any(finding.rule_id == "PB-ROUTE-003" and finding.status.value == "fail"
               for finding in verify_routing(circuit,placed,board,altered).findings)
