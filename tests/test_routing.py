import hashlib

import pytest

from ohmni.application.demo import DEMO_REQUEST, project_demo_report
from ohmni.bom import calculate_cost, classify_assembly, generate_bom, synthetic_fixture_supplier
from ohmni.eda.kicad import KiCadCliAdapter, KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.eda.kicad.placement import golden_board_constraints
from ohmni.eda.pcb_models import DrcStatus
from ohmni.generation import DesignOrchestrator
from ohmni.generation.fixtures import flawed_logger_provider
from ohmni.manufacturing import KiCadFabricationExporter, prototype_profile, verify_manufacturing
from ohmni.physical.models import BoardConstraints, BoardOutline
from ohmni.routing.models import (
    Point,
    RoutingPlan,
    RoutingProfile,
    RoutingStatistics,
    TrackSegment,
    Via,
)
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.verifier import verify_routing


def empty_board():
    return BoardConstraints(outline=BoardOutline(width_mm=20,height_mm=20),placements=[])


def test_track_and_via_models_reject_invalid_geometry():
    with pytest.raises(ValueError,match="zero-length"):
        TrackSegment(segment_id="x",net_name="N",layer="F.Cu",start=Point(x_mm=1,y_mm=1),end=Point(x_mm=1,y_mm=1),width_mm=.25,attempt_id="a")
    with pytest.raises(ValueError,match="unsupported copper"):
        TrackSegment(segment_id="x",net_name="N",layer="In1.Cu",start=Point(x_mm=1,y_mm=1),end=Point(x_mm=2,y_mm=1),width_mm=.25,attempt_id="a")
    with pytest.raises(ValueError,match="through-vias"):
        Via(via_id="v",net_name="N",position=Point(x_mm=1,y_mm=1),diameter_mm=.8,drill_mm=.4,source_layer="F.Cu",destination_layer="In1.Cu",attempt_id="a")
    with pytest.raises(ValueError,match="drill"):
        Via(via_id="v",net_name="N",position=Point(x_mm=1,y_mm=1),diameter_mm=.4,drill_mm=.4,attempt_id="a")


def test_profile_is_explicit_two_layer_and_provenance_aware():
    p=RoutingProfile();assert p.allowed_layers==("F.Cu","B.Cu")
    assert p.signal_width_mm.provenance.value=="project_default"
    assert p.clearance_mm.provenance.value=="board_profile"


def test_astar_straight_route_is_deterministic():
    router=DeterministicRouter();p=RoutingProfile();args=("N",Point(x_mm=2,y_mm=2),Point(x_mm=8,y_mm=2),empty_board(),p,[],{})
    a=router._find(*args);b=router._find(*args)
    assert a==b and a is not None and all(state.layer==0 for state in a[0])


def test_astar_avoids_obstacle_with_layer_change():
    occupied={"OTHER":[(Point(x_mm=5,y_mm=.5),Point(x_mm=5,y_mm=19.5),"F.Cu",.25)]}
    result=DeterministicRouter()._find("N",Point(x_mm=2,y_mm=10),Point(x_mm=8,y_mm=10),empty_board(),RoutingProfile(),[],occupied)
    assert result is not None and {state.layer for state in result[0]}=={0,1}


def test_astar_search_exhaustion_is_bounded():
    p=RoutingProfile();p.maximum_expanded_nodes=p.maximum_expanded_nodes.model_copy(update={"value":1})
    assert DeterministicRouter()._find("N",Point(x_mm=2,y_mm=2),Point(x_mm=18,y_mm=18),empty_board(),p,[],{}) is None


def test_plan_fingerprint_is_stable_and_tracks_lineage():
    stats=RoutingStatistics(required_connections=0,routed_net_count=0,unresolved_net_count=0,track_segment_count=0,via_count=0,total_track_length_mm=0,expanded_nodes=0,routing_attempts=0,route_order=[])
    a=RoutingPlan(source_pcb_fingerprint="a"*64,source_pcb_path="placed.kicad_pcb",source_constraints_hash="b"*64,circuit_content_hash="c"*64,profile=RoutingProfile(),routed_nets=[],statistics=stats)
    assert a.content_hash==a.model_copy(deep=True).content_hash
    assert a.content_hash!=a.model_copy(update={"source_pcb_fingerprint":"d"*64}).content_hash


@pytest.mark.kicad
def test_golden_routing_closes_real_kicad_drc_and_stales_on_change(tmp_path,golden,catalog):
    from ohmni.adapters.tools import find_kicad_cli
    if find_kicad_cli() is None:pytest.skip("KiCad unavailable")
    board=golden_board_constraints();compiler=KiCadPcbCompiler(catalog)
    schematic=KiCadSchematicCompiler(catalog).compile(golden,tmp_path/"golden.kicad_sch")
    placed=compiler.compile(golden,schematic,board,tmp_path/"placed.kicad_pcb")
    plan=DeterministicRouter().route(golden,placed,board);report=verify_routing(golden,placed,board,plan)
    assert plan.statistics.required_connections==51 and not plan.failures and report.passed
    assert golden.content_hash==plan.circuit_content_hash
    first_net=plan.routed_nets[0]
    opened=plan.model_copy(deep=True);opened.routed_nets[0]=first_net.model_copy(update={"paths":first_net.paths[:-1]})
    assert any(f.rule_id=="PB-ROUTE-001" and f.status.value=="fail" for f in verify_routing(golden,placed,board,opened).findings)
    wrong=plan.model_copy(deep=True);via_path=next(path for net in wrong.routed_nets for path in net.paths if path.vias);via_path.vias[0]=via_path.vias[0].model_copy(update={"net_name":"UNKNOWN"})
    assert any(f.rule_id=="PB-ROUTE-003" and f.status.value=="fail" for f in verify_routing(golden,placed,board,wrong).findings)
    narrow=plan.model_copy(deep=True);narrow.routed_nets[0].paths[0].tracks[0]=narrow.routed_nets[0].paths[0].tracks[0].model_copy(update={"width_mm":.1})
    assert any(f.rule_id=="PB-ROUTE-005" and f.status.value=="fail" for f in verify_routing(golden,placed,board,narrow).findings)
    outside=plan.model_copy(deep=True);outside.routed_nets[0].paths[0].tracks[0]=outside.routed_nets[0].paths[0].tracks[0].model_copy(update={"start":Point(x_mm=-1,y_mm=-1)})
    assert any(f.rule_id=="PB-ROUTE-004" and f.status.value=="fail" for f in verify_routing(golden,placed,board,outside).findings)
    routed=compiler.compile(golden,schematic,board,tmp_path/"routed.kicad_pcb",plan)
    drc=KiCadCliAdapter().run_drc(routed)
    assert drc.status is DrcStatus.PASS and not drc.findings and not drc.unconnected_items
    profile=prototype_profile();manufacturing=verify_manufacturing(routed,board,plan,profile)
    assert manufacturing.passed
    package=KiCadFabricationExporter().export(routed,drc,manufacturing,profile,tmp_path/"fab")
    assert {"F.Cu","B.Cu","F.Mask","B.Mask","F.Silkscreen","B.Silkscreen","Edge.Cuts","Drill"}<={x.kind for x in package.files}
    assert {finding.rule_id for finding in package.verification_findings}=={"PB-MFG-009","PB-MFG-010"}
    assert package.events
    assert package.manifest.kind=="Manifest"
    assert package.manifest.sha256==hashlib.sha256(package.manifest_path.read_bytes()).hexdigest()
    assert package.files_current() and package.is_valid_for(routed.fingerprint.digest,profile.content_hash)
    changed_profile=profile.model_copy(update={"source_version":"2.0"})
    assert not package.is_valid_for(routed.fingerprint.digest,changed_profile.content_hash)
    design=DesignOrchestrator(flawed_logger_provider(),catalog).design(DEMO_REQUEST,output=tmp_path/"demo.kicad_sch",run_eda=True)
    bom=generate_bom(golden,catalog);costs=calculate_cost(bom,synthetic_fixture_supplier(bom),1);assembly=classify_assembly(bom)
    demo=project_demo_report(request=DEMO_REQUEST,design=design,catalog=catalog,board=board,placed=placed,plan=plan,route_report=report,routed=routed,drc=drc,manufacturing=manufacturing,bom=bom,costs=costs,assembly=assembly,package=package)
    with pytest.raises(ValueError,match="displayed deterministic"):
        project_demo_report(request="Build a motor controller with a $30 budget",design=design,catalog=catalog,board=board,placed=placed,plan=plan,route_report=report,routed=routed,drc=drc,manufacturing=manufacturing,bom=bom,costs=costs,assembly=assembly,package=package)
    assert demo.project["request"]==DEMO_REQUEST
    assert {row["source_text"] for row in demo.requirements if row["origin"]=="explicit"}=={DEMO_REQUEST}
    assert demo.failure_and_repair["rule"]=="PB-PWR-001"
    assert demo.pcb["violations"]==0 and demo.pcb["unrouted"]==0
    assert demo.release["status"]=="READY_FOR_MANUFACTURING_REVIEW"
    assert demo.release["manifest"]["sha256"]==package.manifest.sha256
    assert demo.economics["fabrication"]=="UNKNOWN"
    assert [row["sequence"] for row in demo.notebook]==list(range(1,len(demo.notebook)+1))
    kinds=[row["kind"] for row in demo.notebook]
    first_pcb_started=kinds.index("pcb_compilation_started")
    first_pcb_compiled=kinds.index("pcb_artifact_compiled",first_pcb_started)
    routing_started=kinds.index("routing_started")
    routing_completed=kinds.index("routing_completed")
    second_pcb_started=kinds.index("pcb_compilation_started",routing_completed)
    second_pcb_compiled=kinds.index("pcb_artifact_compiled",second_pcb_started)
    drc_started=kinds.index("drc_started")
    assert first_pcb_started<first_pcb_compiled<routing_started<routing_completed<second_pcb_started<second_pcb_compiled<drc_started
    assert any(row["phase"]=="assembly" and row["kind"]=="assembly_risk_identified" for row in demo.notebook)
    manifest_bytes=package.manifest_path.read_bytes();package.manifest_path.write_bytes(b"changed manifest")
    assert not package.files_current() and not package.is_valid_for(routed.fingerprint.digest,profile.content_hash)
    stale_demo=project_demo_report(request=DEMO_REQUEST,design=design,catalog=catalog,board=board,placed=placed,plan=plan,route_report=report,routed=routed,drc=drc,manufacturing=manufacturing,bom=bom,costs=costs,assembly=assembly,package=package)
    assert not stale_demo.release["current"] and stale_demo.release["status"]=="STALE" and stale_demo.project["status"]=="STALE"
    package.manifest_path.write_bytes(manifest_bytes);assert package.files_current()
    package.manifest_path.unlink();assert not package.files_current()
    package.manifest_path.write_bytes(manifest_bytes);assert package.files_current()
    victim=package.directory/package.files[0].relative_path;victim.unlink();assert not package.files_current()
    placed_text=placed.path.read_text();placed.path.write_text(placed_text+"\n;changed")
    assert KiCadCliAdapter(executable="never-run").run_drc(routed).status is DrcStatus.STALE_ARTIFACT
    placed.path.write_text(placed_text)
    routed.path.write_text(routed.path.read_text()+"\n;changed")
    assert KiCadCliAdapter(executable="never-run").run_drc(routed).status is DrcStatus.STALE_ARTIFACT
