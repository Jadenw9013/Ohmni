import json

import pytest

from ohmni.domain import Interface, PinElectricalType, resolve_pin_behavior
from ohmni.eda.kicad import (
    KiCadCliAdapter,
    KiCadPcbCompiler,
    KiCadSchematicCompiler,
    PcbCompilationError,
)
from ohmni.eda.kicad.pcb_parser import DrcReportParseError, parse_drc_json
from ohmni.eda.kicad.placement import golden_board_constraints
from ohmni.eda.models import ArtifactFingerprint
from ohmni.eda.pcb_models import DrcStatus


def compile_pcb(tmp_path,golden,catalog,constraints=None,name="board"):
    schematic=KiCadSchematicCompiler(catalog).compile(golden,tmp_path/f"{name}.kicad_sch")
    return KiCadPcbCompiler(catalog).compile(golden,schematic,constraints or golden_board_constraints(),tmp_path/f"{name}.kicad_pcb")


def test_active_i2c_mode_resolves_sdo_as_input(golden,catalog):
    instance=golden.component("U3");pin=catalog.require("BME280").pin("5")
    assert pin.electrical_type is PinElectricalType.TRI_STATE
    resolved=resolve_pin_behavior("U3",pin,instance.selected_interfaces)
    assert resolved.electrical_type is PinElectricalType.INPUT
    assert resolved.selected_interface is Interface.I2C


def test_spi_mode_preserves_catalog_tristate(catalog):
    pin=catalog.require("BME280").pin("5")
    assert resolve_pin_behavior("U3",pin,[Interface.SPI]).electrical_type is PinElectricalType.TRI_STATE


def test_i2c_address_requires_explicit_i2c_mode():
    from ohmni.domain import CircuitComponent
    with pytest.raises(ValueError,match="requires selected interface i2c"):
        CircuitComponent(ref="U3",part_id="BME280",selected_i2c_address=0x76)


def test_pcb_output_is_deterministic_and_fingerprinted(tmp_path,golden,catalog):
    a=compile_pcb(tmp_path,golden,catalog,name="a");b=compile_pcb(tmp_path,golden,catalog,name="b")
    assert a.path.read_bytes()==b.path.read_bytes()
    assert a.fingerprint==b.fingerprint
    assert a.compilation.constraints_hash==golden_board_constraints().content_hash


def test_every_component_and_pin_has_explicit_physical_binding(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog)
    assert {x.component_ref for x in pcb.compilation.footprint_bindings}=={x.ref for x in golden.components}
    expected={(c.ref,p.number) for c in golden.components for p in catalog.require(c.part_id).pins}
    assert {(x.component_ref,x.pin_number) for x in pcb.compilation.pad_bindings}==expected
    assert all(x.source.upstream_file_sha256 for x in pcb.compilation.footprint_bindings)


def test_board_is_two_layer_with_closed_rectangular_outline(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog);text=pcb.path.read_text()
    assert '(0 "F.Cu" signal)' in text and '(31 "B.Cu" signal)' in text
    assert text.count('(layer "Edge.Cuts")')==4


def test_net_mapping_is_stable_and_comes_from_circuit(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog)
    assert set(pcb.compilation.net_mapping)=={n.name for n in golden.nets}
    for binding in pcb.compilation.pad_bindings:
        if binding.net_name:
            assert golden.net(binding.net_name).has(binding.component_ref,binding.pin_number)


def test_stale_or_mismatched_schematic_blocks_compilation(tmp_path,golden,catalog):
    schematic=KiCadSchematicCompiler(catalog).compile(golden,tmp_path/"x.kicad_sch")
    schematic.path.write_text(schematic.path.read_text()+"\n;changed")
    with pytest.raises(PcbCompilationError,match="stale"):
        KiCadPcbCompiler(catalog).compile(golden,schematic,golden_board_constraints(),tmp_path/"x.kicad_pcb")


def test_swapped_pad_membership_fails_consistency(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog);pads=pcb.compilation.pad_bindings.copy()
    pads[0]=pads[0].model_copy(update={"pin_number":"not-a-pin"})
    schematic=KiCadSchematicCompiler(catalog).compile(golden,tmp_path/"other.kicad_sch")
    with pytest.raises(PcbCompilationError,match="pin/pad"):
        KiCadPcbCompiler(catalog)._validate_consistency(golden,schematic,pcb.compilation.footprint_bindings,pads)


def test_overlap_and_far_decoupling_are_physical_failures(tmp_path,golden,catalog):
    constraints=golden_board_constraints();c1=next(x for x in constraints.placements if x.component_ref=="C1");c2=next(x for x in constraints.placements if x.component_ref=="C2")
    constraints.placements[constraints.placements.index(c1)]=c1.model_copy(update={"x_mm":c2.x_mm,"y_mm":c2.y_mm})
    pcb=compile_pcb(tmp_path,golden,catalog,constraints)
    assert not pcb.compilation.physical_verification.passed
    assert any(f.rule_id=="PB-PCB-001" and f.status.value=="fail" for f in pcb.compilation.physical_verification.findings)


def test_golden_physical_rules_pass_and_emit_events(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog)
    assert pcb.compilation.physical_verification.passed
    kinds={e.kind.value for e in pcb.events}
    assert {"pcb_compilation_started","footprint_resolved","pad_binding_resolved","placement_constraint_applied","component_placed","physical_validation_run","pcb_artifact_compiled"} <= kinds
    assert {lesson.topic for lesson in pcb.compilation.lessons}=={"Decoupling placement","Connector placement"}


def test_stale_pcb_drc_is_rejected_without_running_tool(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog);pcb.path.write_text(pcb.path.read_text()+"\n;changed")
    report=KiCadCliAdapter(executable="never-run").run_drc(pcb)
    assert report.status is DrcStatus.STALE_ARTIFACT
    assert report.pcb_fingerprint==pcb.fingerprint


def test_changed_upstream_schematic_invalidates_pcb_drc(tmp_path,golden,catalog):
    pcb=compile_pcb(tmp_path,golden,catalog)
    pcb.source_schematic_path.write_text(pcb.source_schematic_path.read_text()+"\n;changed")
    report=KiCadCliAdapter(executable="never-run").run_drc(pcb)
    assert report.status is DrcStatus.STALE_ARTIFACT
    assert "source schematic" in report.stderr


FP=ArtifactFingerprint(digest="b"*64)
def parse(tmp_path,payload):
    path=tmp_path/"drc.json";path.write_text(json.dumps(payload))
    return parse_drc_json(path,pcb_fingerprint=FP,schematic_fingerprint=FP,run_id="r",command=["kicad-cli"],return_code=5)


def test_drc_parser_types_violations_unrouted_and_unknown_fields(tmp_path):
    report=parse(tmp_path,{"kicad_version":"10.0.5","ignored_checks":[],"violations":[{"type":"clearance","severity":"warning","description":"gap","future":1}],"unconnected_items":[{"type":"unconnected_items","severity":"error","description":"missing","items":[]}]})
    assert report.status is DrcStatus.FAIL
    assert report.findings[0].classification.value=="clearance"
    assert report.findings[0].raw["future"]==1
    assert report.unconnected_items[0].classification.value=="unrouted"


@pytest.mark.parametrize("payload",[{}, {"kicad_version":"10","violations":[],"unconnected_items":{}}, {"violations":[],"unconnected_items":[]}])
def test_drc_parser_rejects_malformed_json(tmp_path,payload):
    with pytest.raises(DrcReportParseError): parse(tmp_path,payload)


@pytest.mark.kicad
def test_real_kicad_accepts_golden_board_and_reports_unrouted(tmp_path,golden,catalog):
    from ohmni.adapters.tools import find_kicad_cli
    if find_kicad_cli() is None: pytest.skip("KiCad unavailable")
    pcb=compile_pcb(tmp_path,golden,catalog);report=KiCadCliAdapter().run_drc(pcb)
    assert report.kicad_version=="10.0.5"
    assert report.status is DrcStatus.FAIL
    assert len(report.findings)==0
    assert len(report.unconnected_items)>0
    assert all(x.classification.value=="unrouted" for x in report.unconnected_items)


@pytest.mark.kicad
def test_real_kicad_catches_overlapping_different_net_pads(tmp_path,golden,catalog):
    from ohmni.adapters.tools import find_kicad_cli
    if find_kicad_cli() is None: pytest.skip("KiCad unavailable")
    constraints=golden_board_constraints();a=next(x for x in constraints.placements if x.component_ref=="C1");b=next(x for x in constraints.placements if x.component_ref=="C2")
    constraints.placements[constraints.placements.index(a)]=a.model_copy(update={"x_mm":b.x_mm,"y_mm":b.y_mm})
    pcb=compile_pcb(tmp_path,golden,catalog,constraints,"overlap");report=KiCadCliAdapter().run_drc(pcb)
    assert any(f.type=="shorting_items" for f in report.findings)
    assert any(f.type=="courtyards_overlap" for f in report.findings)


@pytest.mark.kicad
def test_ohmni_catches_far_decoupling_that_kicad_does_not(tmp_path,golden,catalog):
    from ohmni.adapters.tools import find_kicad_cli
    if find_kicad_cli() is None: pytest.skip("KiCad unavailable")
    constraints=golden_board_constraints();cap=next(x for x in constraints.placements if x.component_ref=="C6")
    constraints.placements[constraints.placements.index(cap)]=cap.model_copy(update={"x_mm":5,"y_mm":50})
    pcb=compile_pcb(tmp_path,golden,catalog,constraints,"far-decoupling");report=KiCadCliAdapter().run_drc(pcb)
    assert any(f.rule_id=="PB-PCB-004" and f.status.value=="fail" for f in pcb.compilation.physical_verification.findings)
    assert not report.findings
