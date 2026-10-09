"""The authoring overlay never changes the production registry or saved demo."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from ohmni.physical.footprints import FOOTPRINTS, footprint_geometry_fingerprint
from ohmni.physical.models import ComponentPlacement
from ohmni.physical.rules import pad_position
from tools.landing_redesign import physical


def test_overlay_has_exact_pinned_source_bytes_and_no_registry_import_side_effect():
    before = footprint_geometry_fingerprint()
    entries = physical.footprint_manifest()
    assert len(entries) == 3
    for item in entries:
        assert item["footprint_id"] not in FOOTPRINTS
        raw = (physical.SOURCE_DIRECTORY / item["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert item["source_kind"] == "pinned_KiCad_library"
    assert footprint_geometry_fingerprint() == before


@pytest.mark.parametrize("fail", [False, True])
def test_overlay_restores_exact_existing_objects_and_reference_bytes(fail):
    original = dict(FOOTPRINTS)
    fingerprint = footprint_geometry_fingerprint()
    reference = Path(__file__).resolve().parents[1] / "apps/web/reference-board.json"
    saved = reference.read_bytes()
    try:
        with physical.scoped_footprints() as overlay:
            assert len(FOOTPRINTS) == len(original) + 3
            assert all(FOOTPRINTS[key] is value for key, value in original.items())
            assert set(overlay) <= FOOTPRINTS.keys()
            if fail:
                raise RuntimeError("deliberately interrupted authoring")
    except RuntimeError as exc:
        assert fail and str(exc) == "deliberately interrupted authoring"
    assert set(FOOTPRINTS) == set(original)
    assert all(FOOTPRINTS[key] is value for key, value in original.items())
    assert footprint_geometry_fingerprint() == fingerprint
    assert reference.read_bytes() == saved


def test_overlay_rejects_source_tampering_before_installing(monkeypatch, tmp_path):
    item = physical.SOURCES[0]
    (tmp_path / item[1]).write_bytes((physical.SOURCE_DIRECTORY / item[1]).read_bytes() + b"\n")
    before = footprint_geometry_fingerprint()
    monkeypatch.setattr(physical, "SOURCE_DIRECTORY", tmp_path)
    with pytest.raises(ValueError, match="bytes changed"), physical.scoped_footprints():
        pytest.fail("changed source was admitted")
    assert footprint_geometry_fingerprint() == before


def test_exact_land_dimensions_numbering_and_documented_header_translation():
    with physical.scoped_footprints() as overlay:
        coil = overlay[physical.SOURCES[0][0]]
        assert (coil.width_mm, coil.height_mm) == (4.8, 4.8)
        assert [(p.number, p.x_mm, p.y_mm, p.width_mm, p.height_mm) for p in coil.pads] == [
            ("1", -1.185, 0, .98, 3.4), ("2", 1.185, 0, .98, 3.4)]
        ic = overlay[physical.SOURCES[1][0]]
        assert (ic.width_mm, ic.height_mm) == (4.56, 2.5)
        assert [(p.number, p.x_mm, p.y_mm) for p in ic.pads] == [
            ("1", -1.4, -.75), ("2", -1.4, -.25), ("3", -1.4, .25), ("4", -1.4, .75),
            ("5", 1.4, .75), ("6", 1.4, .25), ("7", 1.4, -.25), ("8", 1.4, -.75)]
        header = overlay[physical.SOURCES[2][0]]
        assert header.width_mm == 3.54
        assert header.height_mm == pytest.approx(11.16)
        assert [p.number for p in header.pads] == ["1", "2", "3", "4"]
        assert [p.y_mm for p in header.pads] == pytest.approx([-3.81, -1.27, 1.27, 3.81])
        assert all(p.drill.width_mm == 1 and p.drill.height_mm == 1 for p in header.pads)
        assert "translated by (0, -3.81)" in header.source.derivation
        pose = ComponentPlacement(component_ref="L1", x_mm=15, y_mm=43,
                                  rotation_deg=180, reason="authored orientation")
        assert pad_position(coil, pose, "1") == pytest.approx((16.185, 43))
        assert pad_position(coil, pose, "2") == pytest.approx((13.815, 43))


def _inventory(extension=True):
    refs = set(physical.POSITIONS)
    if not extension:
        refs -= {"U4", "J3", "R8", "R9", "R14", "C8"}
    return SimpleNamespace(components=[SimpleNamespace(ref=ref) for ref in sorted(refs)])


@pytest.mark.parametrize("extension,count", [(False, 32), (True, 38)])
def test_layout_is_deterministic_complete_and_keeps_port_and_switching_constraints(extension, count):
    circuit = _inventory(extension)
    board = physical.build_board_constraints(circuit)
    assert len(board.placements) == count
    assert board.content_hash == physical.build_board_constraints(circuit).content_hash
    assert (board.outline.width_mm, board.outline.height_mm) == (90, 55)
    by_id = {item.constraint_id: item for item in board.placement_constraints}
    assert by_id["fixed-port-J1"].fixed_pose.rotation_deg == 0
    assert by_id["edge-J1"].preferred_edge.value == "bottom"
    assert by_id["antenna-U1"].relative_to_component
    assert by_id["near-L1-1-U2-3"].maximum_distance_mm == 4
    assert by_id["near-C1-1-U2-4"].component_pin == "1"
    assert by_id["near-C1-1-U2-4"].target_pin == "4"
    assert ("fixed-port-J3" in by_id) is extension


def test_layout_fails_closed_for_unrecognized_or_incomplete_circuit():
    circuit = _inventory()
    circuit.components.append(SimpleNamespace(ref="UNKNOWN"))
    with pytest.raises(ValueError, match="no authored position"):
        physical.build_board_constraints(circuit)
    with pytest.raises(ValueError, match="requires"):
        physical.build_board_constraints(SimpleNamespace(components=[]))


def test_switching_route_checks_reject_long_via_bottom_and_stale_routes():
    circuit = SimpleNamespace(content_hash="circuit")
    board = SimpleNamespace(content_hash="board")

    def plan(sw_length=3, layer="F.Cu", vias=()):
        return SimpleNamespace(circuit_content_hash="circuit", source_constraints_hash="board",
            content_hash="plan", vias=list(vias), tracks=[
                SimpleNamespace(net_name="SW_NODE", length_mm=sw_length, layer=layer),
                SimpleNamespace(net_name="FB_REFB", length_mm=5, layer="F.Cu")])

    assert physical.audit_switching_routes(circuit, board, plan())["status"] == "PASS"
    assert physical.audit_switching_routes(circuit, board, plan(sw_length=6.01))["status"] == "FAIL"
    assert physical.audit_switching_routes(circuit, board, plan(layer="B.Cu"))["status"] == "FAIL"
    assert physical.audit_switching_routes(circuit, board, plan(vias=[SimpleNamespace(net_name="SW_NODE")]))["status"] == "FAIL"
    stale = plan()
    stale.source_constraints_hash = "old board"
    with pytest.raises(ValueError, match="different circuit/placement lineage"):
        physical.audit_switching_routes(circuit, board, stale)


@pytest.mark.parametrize("extension,count", [(False, 32), (True, 38)])
def test_real_candidate_compiles_with_all_physical_checks_and_led_permutation(tmp_path, extension, count):
    from ohmni.eda.kicad.compiler import KiCadSchematicCompiler
    from ohmni.eda.kicad.pcb_compiler import KiCadPcbCompiler
    from tools.landing_redesign.design import build_design

    design = build_design(include_i2c_extension=extension)
    board = physical.build_board_constraints(design.circuit)
    with physical.scoped_footprints():
        schematic = KiCadSchematicCompiler(design.catalog).compile(design.circuit, tmp_path / "candidate.kicad_sch")
        artifact = KiCadPcbCompiler(design.catalog).compile(design.circuit, schematic, board, tmp_path / "candidate.kicad_pcb")
    checks = artifact.compilation.physical_verification
    assert checks.passed, [finding.model_dump() for finding in checks.findings if finding.status.value != "pass"]
    assert len(artifact.compilation.footprint_bindings) == count
    bindings = {(p.component_ref, p.pin_number): p for p in artifact.compilation.pad_bindings}
    for ref in ("D1", "D2", "D3", "D4"):
        assert bindings[ref, "1"].pad_number == "2"
        assert bindings[ref, "2"].pad_number == "1"
        assert bindings[ref, "2"].net_name == "GND"


def test_real_candidate_rejects_switching_stage_in_antenna_keepout(tmp_path):
    from ohmni.eda.kicad.compiler import KiCadSchematicCompiler
    from ohmni.eda.kicad.pcb_compiler import KiCadPcbCompiler
    from tools.landing_redesign.design import build_design

    design = build_design(include_i2c_extension=True)
    board = physical.build_board_constraints(design.circuit)
    board.placements = [p.model_copy(update={"x_mm": 24, "y_mm": 5}) if p.component_ref == "L1" else p
                        for p in board.placements]
    with physical.scoped_footprints():
        schematic = KiCadSchematicCompiler(design.catalog).compile(design.circuit, tmp_path / "candidate.kicad_sch")
        artifact = KiCadPcbCompiler(design.catalog).compile(design.circuit, schematic, board, tmp_path / "candidate.kicad_pcb")
    checks = artifact.compilation.physical_verification
    assert not checks.passed
    assert any(f.constraint_id == "antenna-U1" and f.status.value == "fail" for f in checks.findings)
    assert any(f.constraint_id == "near-L1-1-U2-3" and f.status.value == "fail" for f in checks.findings)
