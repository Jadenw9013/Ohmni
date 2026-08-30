from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ohmni.bom import (
    AssemblyDifficulty,
    Bom,
    BomLine,
    ManufacturerPartIdentity,
    PriceBreak,
    StaticSupplierProvider,
    SupplierOffer,
    calculate_cost,
    classify_assembly,
    generate_bom,
    synthetic_fixture_supplier,
)
from ohmni.manufacturing import ManufacturingStatus, prototype_profile, verify_manufacturing
from ohmni.physical.models import BoardConstraints, BoardOutline
from ohmni.routing.models import (
    Point,
    RoutedNet,
    RoutePath,
    RoutingPlan,
    RoutingProfile,
    RoutingStatistics,
    TrackSegment,
    Via,
)


def minimal_plan(track=.25,drill=.4,diameter=.8,clearance=.2,edge=.5):
    profile=RoutingProfile();profile.signal_width_mm=profile.signal_width_mm.model_copy(update={"value":track});profile.clearance_mm=profile.clearance_mm.model_copy(update={"value":clearance});profile.edge_clearance_mm=profile.edge_clearance_mm.model_copy(update={"value":edge})
    t=TrackSegment(segment_id="t",net_name="N",layer="F.Cu",start=Point(x_mm=2,y_mm=2),end=Point(x_mm=8,y_mm=2),width_mm=track,attempt_id="a")
    v=Via(via_id="v",net_name="N",position=Point(x_mm=8,y_mm=2),diameter_mm=diameter,drill_mm=drill,attempt_id="a")
    path=RoutePath(source_pad="A.1",target_pad="B.1",tracks=[t],vias=[v]);net=RoutedNet(net_name="N",terminal_pads=["A.1","B.1"],paths=[path])
    stats=RoutingStatistics(required_connections=1,routed_net_count=1,unresolved_net_count=0,track_segment_count=1,via_count=1,total_track_length_mm=6,expanded_nodes=2,routing_attempts=1,route_order=["N"])
    return RoutingPlan(source_pcb_fingerprint="a"*64,source_pcb_path="p.kicad_pcb",source_constraints_hash="b"*64,circuit_content_hash="c"*64,profile=profile,routed_nets=[net],statistics=stats)

def fake_pcb(provenance=True):
    source=SimpleNamespace(upstream_file_sha256="hash" if provenance else "")
    return SimpleNamespace(fingerprint=SimpleNamespace(digest="a"*64),compilation=SimpleNamespace(footprint_bindings=[SimpleNamespace(footprint_id="FP",source=source)]))

def board(layers=2):return BoardConstraints(outline=BoardOutline(width_mm=100,height_mm=70),layer_count=layers,placements=[])

def test_profile_is_provenance_aware_and_fingerprinted():
    p=prototype_profile();assert p.provenance.value=="synthetic_profile" and "not a fab quote" in p.source_name
    assert p.content_hash==prototype_profile().content_hash

@pytest.mark.parametrize("field,value,rule",[("track",.1,"PB-MFG-001"),("clearance",.1,"PB-MFG-002"),("drill",.2,"PB-MFG-003"),("diameter",.5,"PB-MFG-003"),("edge",.2,"PB-MFG-006")])
def test_drc_clean_geometry_can_fail_stricter_manufacturing_profile(field,value,rule):
    kwargs={field:value};report=verify_manufacturing(fake_pcb(),board(),minimal_plan(**kwargs),prototype_profile())
    assert any(x.rule_id==rule and x.status is ManufacturingStatus.FAIL for x in report.findings)

def test_layer_dimension_and_footprint_provenance_failures():
    profile=prototype_profile();profile.supported_layer_counts=[4]
    report=verify_manufacturing(fake_pcb(False),board(),minimal_plan(),profile)
    assert {x.rule_id for x in report.findings if x.status is ManufacturingStatus.FAIL}>={"PB-MFG-005","PB-MFG-007"}

def test_golden_bom_aggregation_is_identity_safe(golden,catalog):
    bom=generate_bom(golden,catalog);assert bom.reference_count==19 and len(bom.lines)==13
    pullups=next(x for x in bom.lines if x.references==["R4","R5"]);assert pullups.quantity_per_board==2
    assert next(x for x in bom.lines if x.references==["R1","R2"]).identity.value_key!=pullups.identity.value_key

def test_missing_price_is_unknown_never_zero(golden,catalog):
    bom=generate_bom(golden,catalog);report=calculate_cost(bom,StaticSupplierProvider([]),1)
    assert report.pricing_coverage==0 and report.known_purchase_requirement==0
    assert all(x.knowledge.value=="unknown" and x.purchase_cost is None for x in report.lines)
    assert any(event.kind.value == "pricing_unknown" for event in report.events)

def test_moq_price_breaks_and_board_scenarios(golden,catalog):
    bom=generate_bom(golden,catalog);provider=synthetic_fixture_supplier(bom)
    one,five,ten=[calculate_cost(bom,provider,n) for n in (1,5,10)]
    assert one.known_consumption_cost==Decimal("5.680") and one.known_purchase_requirement==Decimal("23.000")
    assert five.known_purchase_requirement==Decimal("32.600") and ten.known_purchase_requirement==Decimal("53.200")
    assert one.pricing_coverage==pytest.approx(12/13)

def test_supplier_exact_identity_blocks_dev_board_suffix_and_package_substitution():
    requested=ManufacturerPartIdentity(part_id="BME280",manufacturer="Bosch",mpn="BME280",package="LGA-8")
    wrong=requested.model_copy(update={"mpn":"BME280-SHUTTLE-BOARD"})
    offer=SupplierOffer(supplier="fixture",returned_identity=wrong,currency="USD",price_breaks=[PriceBreak(quantity=1,unit_price=Decimal(1))],verified_on=date(2026,8,1),provenance="synthetic")
    assert StaticSupplierProvider([offer]).lookup(requested,1).offer is None
    assert StaticSupplierProvider([offer]).lookup(requested.model_copy(update={"package":"QFN"}),1).offer is None

def test_assembly_classification_surfaces_lga_and_unknown():
    lga=BomLine(identity=ManufacturerPartIdentity(part_id="S",package="LGA-8"),description="",quantity_per_board=1,references=["U1"],footprint="x",evidence_status="catalog")
    unknown=lga.model_copy(update={"identity":ManufacturerPartIdentity(part_id="X",package="MYSTERY"),"references":["U2"]})
    report=classify_assembly(Bom(circuit_fingerprint="x",lines=[lga,unknown]))
    assert {x.difficulty for x in report.risks}=={AssemblyDifficulty.REFLOW_RECOMMENDED,AssemblyDifficulty.UNKNOWN}
    assert not report.hand_solder_requirement_satisfied
    assert report.events
