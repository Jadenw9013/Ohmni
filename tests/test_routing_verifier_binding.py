"""Adversarial checks for electrical ownership of physically routed copper."""

from itertools import pairwise

import pytest

from ohmni.domain import CircuitComponent, CircuitIR, Net, PinRef, Quantity
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.models import BoardConstraints, BoardOutline, ComponentPlacement
from ohmni.routing.models import Point, RoutedNet, RoutingProfile, TrackSegment, Via
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.verifier import verify_routing


@pytest.fixture(scope="module")
def routed_board(tmp_path_factory, catalog):
    destination=tmp_path_factory.mktemp("routing-binding")
    circuit=CircuitIR(ir_id="routing-binding",name="Independent copper binding checks",
        components=[CircuitComponent(ref=f"R{i}",part_id="GENERIC_RESISTOR",package="0805",
                                     value=Quantity.ohms(1000)) for i in (1,2,3)],
        nets=[Net(name=name,connections=[PinRef(component=f"R{i}",pin=pin) for i in (1,2)])
              for name,pin in (("A","1"),("B","2"))]
             +[Net(name="SINGLE",connections=[PinRef(component="R3",pin="1")]),Net(name="EMPTY")])
    board=BoardConstraints(outline=BoardOutline(width_mm=40,height_mm=30),
        placements=[ComponentPlacement(component_ref=f"R{i}",x_mm=x,y_mm=y,
                                       reason="Independent verifier regression")
                    for i,x,y in ((1,8,10),(2,30,10),(3,20,23))])
    schematic=KiCadSchematicCompiler(catalog).compile(circuit,destination/"source.kicad_sch")
    pcb=KiCadPcbCompiler(catalog).compile(circuit,schematic,board,destination/"placed.kicad_pcb")
    plan=DeterministicRouter().route(circuit,pcb,board)
    assert not plan.failures and verify_routing(circuit,pcb,board,plan).passed
    return circuit,pcb,board,plan


def _finding(fixture, plan, rule):
    circuit,pcb,board,_=fixture
    return next(f for f in verify_routing(circuit,pcb,board,plan).findings if f.rule_id==rule)


@pytest.mark.parametrize("copper", ["tracks","vias"])
def test_copper_cannot_borrow_another_valid_semantic_net(routed_board,copper):
    plan=routed_board[3].model_copy(deep=True)
    a=next(net for net in plan.routed_nets if net.net_name=="A")
    if copper=="tracks":
        for track in plan.tracks:
            track.net_name="B"
    else:
        a.paths[0].vias.append(Via(via_id="borrowed",net_name="B",position=a.paths[0].tracks[0].start,
                                  diameter_mm=.8,drill_mm=.4,attempt_id="adversarial"))
    finding=_finding(routed_board,plan,"PB-ROUTE-003")
    assert finding.status.value=="fail" and "A" in finding.net_names


@pytest.mark.parametrize("endpoint", ["source_pad","target_pad"])
def test_path_endpoint_must_be_a_physical_terminal_of_its_container_net(routed_board,endpoint):
    plan=routed_board[3].model_copy(deep=True)
    a=next(net for net in plan.routed_nets if net.net_name=="A")
    setattr(a.paths[0],endpoint,"R1.2")
    assert _finding(routed_board,plan,"PB-ROUTE-003").status.value=="fail"


@pytest.mark.parametrize("mutation", ["unknown","duplicate","missing"])
def test_net_container_contract_cannot_hide_or_duplicate_required_nets(routed_board,mutation):
    plan=routed_board[3].model_copy(deep=True)
    a=next(net for net in plan.routed_nets if net.net_name=="A")
    if mutation=="unknown":
        plan.routed_nets.append(RoutedNet(net_name="UNKNOWN",terminal_pads=[],paths=[]))
    elif mutation=="duplicate":
        plan.routed_nets.append(a.model_copy(deep=True))
    else:
        plan.routed_nets.remove(a)
    assert _finding(routed_board,plan,"PB-ROUTE-003").status.value=="fail"


@pytest.mark.parametrize("terminals", [[],["R1.1","R2.1","R1.1"],["R1.1","R2.2"]])
def test_terminal_inventory_is_complete_unique_and_owned_by_the_net(routed_board,terminals):
    plan=routed_board[3].model_copy(deep=True)
    next(net for net in plan.routed_nets if net.net_name=="A").terminal_pads=terminals
    assert _finding(routed_board,plan,"PB-ROUTE-003").status.value=="fail"


def test_empty_and_single_location_nets_need_no_copper_container(routed_board):
    plan=routed_board[3].model_copy(deep=True)
    plan.routed_nets=[net for net in plan.routed_nets if net.net_name not in {"SINGLE","EMPTY"}]
    circuit,pcb,board,_=routed_board
    assert verify_routing(circuit,pcb,board,plan).passed


def test_coincident_usb_aliases_may_use_one_valid_terminal_identity(tmp_path,catalog):
    circuit=CircuitIR(ir_id="coincident-terminals",name="Coincident physical lands",
        components=[CircuitComponent(ref="J1",part_id="USB_C_RECEPTACLE_16P",package="USB-C-16P-SMD")],
        nets=[Net(name="GND",connections=[PinRef(component="J1",pin=pin) for pin in ("A1","B12")])])
    board=BoardConstraints(outline=BoardOutline(width_mm=40,height_mm=30),
        placements=[ComponentPlacement(component_ref="J1",x_mm=20,y_mm=15,reason="Coincident alias regression")])
    schematic=KiCadSchematicCompiler(catalog).compile(circuit,tmp_path/"usb.kicad_sch")
    pcb=KiCadPcbCompiler(catalog).compile(circuit,schematic,board,tmp_path/"usb.kicad_pcb")
    plan=DeterministicRouter().route(circuit,pcb,board)
    assert len(plan.routed_nets[0].terminal_pads)==1
    for identity in ("J1.A1","J1.B12"):
        plan.routed_nets[0].terminal_pads=[identity]
        assert verify_routing(circuit,pcb,board,plan).passed
    plan.routed_nets=[]
    assert verify_routing(circuit,pcb,board,plan).passed


@pytest.mark.parametrize("copper", ["track","via"])
@pytest.mark.parametrize("boundary", ["left","right","top","bottom"])
@pytest.mark.parametrize("margin,valid", [(0,False),(.999,False),(1,True)])
def test_board_edge_clearance_measures_copper_radius(routed_board,copper,boundary,margin,valid):
    circuit,pcb,board,original=routed_board
    plan=original.model_copy(deep=True)
    edge=float(plan.profile.edge_clearance_mm.value)
    centre={"left":(edge+margin,15),"right":(board.outline.width_mm-edge-margin,15),
            "top":(20,edge+margin),"bottom":(20,board.outline.height_mm-edge-margin)}[boundary]
    point=Point(x_mm=centre[0],y_mm=centre[1])
    a=next(net for net in plan.routed_nets if net.net_name=="A").paths[0]
    if copper=="track":
        end=Point(x_mm=point.x_mm+(1 if boundary in {"top","bottom"} else 0),
                  y_mm=point.y_mm+(1 if boundary in {"left","right"} else 0))
        a.tracks.append(TrackSegment(segment_id="edge",net_name="A",layer="B.Cu",start=point,end=end,
                                     width_mm=2,attempt_id="adversarial"))
    else:
        a.vias.append(Via(via_id="edge",net_name="A",position=point,diameter_mm=2,drill_mm=.4,
                          attempt_id="adversarial"))
    finding=next(f for f in verify_routing(circuit,pcb,board,plan).findings if f.rule_id=="PB-ROUTE-004")
    assert (finding.status.value=="pass") is valid


@pytest.mark.parametrize("start_x,goal_x,width,valid", [(.5,10,.25,False),(10,19.5,.25,False),
    (1.5,10,2,True),(1.25,10,2,False),(.63,10,.25,True)])
def test_search_checks_start_goal_and_snapped_nodes_against_copper_edge(start_x,goal_x,width,valid):
    board=BoardConstraints(outline=BoardOutline(width_mm=20,height_mm=20),placements=[])
    result=DeterministicRouter()._find("N",Point(x_mm=start_x,y_mm=10),Point(x_mm=goal_x,y_mm=10),
                                       board,RoutingProfile(),[],{},width_mm=width)
    assert (result is not None) is valid


def test_search_checks_via_radius_when_changing_layers_near_edge():
    board=BoardConstraints(outline=BoardOutline(width_mm=20,height_mm=20),placements=[])
    profile=RoutingProfile()
    # The front-layer barrier forces two layer transitions. Legal signal
    # centers at x=.75 do not leave enough room for the default .8 mm via.
    barrier={"OTHER":[(Point(x_mm=.5,y_mm=10),Point(x_mm=19.5,y_mm=10),"F.Cu",.25)]}
    result=DeterministicRouter()._find("N",Point(x_mm=.75,y_mm=2),Point(x_mm=.75,y_mm=18),
                                      board,profile,[],barrier)
    assert result is not None
    states=result[0]
    transitions=[a for a,b in pairwise(states) if a.layer!=b.layer]
    assert transitions
    inset=profile.edge_clearance_mm.value+profile.via_diameter_mm.value/2
    assert all(inset<=state.x*profile.grid_mm.value<=board.outline.width_mm-inset
               and inset<=state.y*profile.grid_mm.value<=board.outline.height_mm-inset for state in transitions)


@pytest.mark.parametrize("pin", ["1","2"])
@pytest.mark.parametrize("copper", ["front_track","back_track","via"])
def test_tracks_and_vias_cannot_touch_singleton_or_unassigned_smd_pads(routed_board,pin,copper):
    circuit,pcb,board,original=routed_board
    plan=original.model_copy(deep=True)
    point=DeterministicRouter._pad_centres(pcb,board)[("R3",pin)]
    path=next(net for net in plan.routed_nets if net.net_name=="A").paths[0]
    _append_copper(path,point,copper)
    finding=_finding(routed_board,plan,"PB-ROUTE-007")
    if copper=="back_track":
        assert verify_routing(circuit,pcb,board,plan).passed
    else:
        assert finding.status.value=="fail" and f"A/R3.{pin}" in finding.net_names


def test_same_net_physical_pad_is_not_a_foreign_obstacle(routed_board):
    _circuit,pcb,board,original=routed_board
    plan=original.model_copy(deep=True)
    point=DeterministicRouter._pad_centres(pcb,board)[("R1","1")]
    path=next(net for net in plan.routed_nets if net.net_name=="A").paths[0]
    _append_copper(path,point,"front_track")
    assert "A/R1.1" not in _finding(routed_board,plan,"PB-ROUTE-007").net_names


@pytest.mark.parametrize("copper,radius", [("front_track",.125),("via",.4)])
@pytest.mark.parametrize("gap,valid", [(-.01,False),(0,True),(.01,True)])
def test_pad_clearance_includes_copper_radius_and_accepts_legal_tangency(routed_board,copper,radius,gap,valid):
    _circuit,pcb,board,original=routed_board
    plan=original.model_copy(deep=True)
    centre=DeterministicRouter._pad_centres(pcb,board)[("R3","2")]
    point=Point(x_mm=centre.x_mm+.5+plan.profile.clearance_mm.value+radius+gap,y_mm=centre.y_mm)
    _append_copper(next(net for net in plan.routed_nets if net.net_name=="A").paths[0],point,copper)
    finding=_finding(routed_board,plan,"PB-ROUTE-007")
    assert ("A/R3.2" not in finding.net_names) is valid


@pytest.mark.parametrize("rotation", [0,90])
@pytest.mark.parametrize("copper", ["front_track","back_track","via"])
@pytest.mark.parametrize("obstacle", ["unused_header","mechanical_shell"])
def test_plated_and_mechanical_lands_block_both_layers(tmp_path,catalog,rotation,copper,obstacle):
    part,package=("HEADER_1X6_254","1x6-2.54mm-THT") if obstacle=="unused_header" else (
        "USB_C_RECEPTACLE_16P","USB-C-16P-SMD")
    # Reuse a valid routed pair while adding a separate unused connector. Its
    # pads are absent from electrical nets, so no routed tracks reveal them.
    base=CircuitIR(ir_id="physical-obstacle",name="Unused physical copper obstacles",
        components=[CircuitComponent(ref=f"R{i}",part_id="GENERIC_RESISTOR",package="0805",
                                     value=Quantity.ohms(1000)) for i in (1,2)]
                   +[CircuitComponent(ref="J1",part_id=part,package=package)],
        nets=[Net(name=name,connections=[PinRef(component=f"R{i}",pin=pin) for i in (1,2)])
              for name,pin in (("A","1"),("B","2"))])
    board=BoardConstraints(outline=BoardOutline(width_mm=50,height_mm=45),
        placements=[ComponentPlacement(component_ref=f"R{i}",x_mm=x,y_mm=8,reason="Pad obstacle regression")
                    for i,x in ((1,8),(2,40))]
                   +[ComponentPlacement(component_ref="J1",x_mm=25,y_mm=27,rotation_deg=rotation,
                                        reason="Pad obstacle regression")])
    schematic=KiCadSchematicCompiler(catalog).compile(base,tmp_path/"pads.kicad_sch")
    pcb=KiCadPcbCompiler(catalog).compile(base,schematic,board,tmp_path/"pads.kicad_pcb")
    plan=DeterministicRouter().route(base,pcb,board)
    assert verify_routing(base,pcb,board,plan).passed
    x,y=(0,0) if obstacle=="unused_header" else (-4.32,1.05)
    x,y=(x,y) if rotation==0 else (-y,x)
    point=Point(x_mm=25+x,y_mm=27+y)
    _append_copper(next(net for net in plan.routed_nets if net.net_name=="A").paths[0],point,copper)
    finding=next(f for f in verify_routing(base,pcb,board,plan).findings if f.rule_id=="PB-ROUTE-007")
    assert finding.status.value=="fail"
    assert any(name.startswith("A/J1.") for name in finding.net_names)


def _append_copper(path,point,kind):
    if kind=="via":
        path.vias.append(Via(via_id="pad-probe",net_name="A",position=point,
                             diameter_mm=.8,drill_mm=.4,attempt_id="adversarial"))
    else:
        path.tracks.append(TrackSegment(segment_id="pad-probe",net_name="A",
            layer="B.Cu" if kind=="back_track" else "F.Cu",
            start=Point(x_mm=point.x_mm,y_mm=point.y_mm-2),
            end=Point(x_mm=point.x_mm,y_mm=point.y_mm+2),width_mm=.25,attempt_id="adversarial"))
