"""Pin geometry and real mechanical features in the isolated controller author."""
import hashlib
import json
import math
import subprocess
import sys
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import pytest

from ohmni.adapters.tools import find_kicad_cli
from ohmni.eda.kicad.compiler import KiCadSchematicCompiler
from ohmni.eda.kicad.component_asset_parser import parse
from ohmni.eda.kicad.pcb_compiler import PcbCompilationError
from ohmni.physical.footprints import FOOTPRINTS, footprint_geometry_fingerprint
from ohmni.physical.rules import pad_position
from ohmni.routing.router import DeterministicRouter
from tools.landing_controller import physical
from tools.landing_controller.design import build_design


def test_pinned_bytes_are_checked_and_overlay_restores_exact_objects_even_after_failure():
    original = dict(FOOTPRINTS)
    before = footprint_geometry_fingerprint()
    for row in physical.footprint_manifest():
        assert hashlib.sha256((physical.SOURCE_DIRECTORY / row["file"]).read_bytes()).hexdigest() == row["sha256"]
    with pytest.raises(RuntimeError, match="interrupted"), physical.scoped_footprints() as extra:
        assert len(extra) == 5
        assert not (original.keys() & extra.keys())
        raise RuntimeError("interrupted")
    assert footprint_geometry_fingerprint() == before
    assert FOOTPRINTS.keys() == original.keys()
    assert all(FOOTPRINTS[key] is value for key, value in original.items())


def test_tampered_pinned_source_is_not_admitted(monkeypatch, tmp_path):
    item = physical.SOURCES[0]
    (tmp_path / item[1]).write_bytes((physical.SOURCE_DIRECTORY / item[1]).read_bytes()+b"\n")
    monkeypatch.setattr(physical, "SOURCE_DIRECTORY", tmp_path)
    before = footprint_geometry_fingerprint()
    with pytest.raises(ValueError, match="bytes changed"), physical.scoped_footprints():
        pytest.fail("modified source admitted")
    assert footprint_geometry_fingerprint() == before


def test_lqfp_pin_one_and_every_side_are_source_aligned_and_not_mirrored():
    with physical.scoped_footprints() as overlay:
        fp = overlay[physical.SOURCES[0][0]]
        assert (fp.width_mm, fp.height_mm) == (17.46, 17.46)
        assert len(fp.pads) == 100
        assert [p.number for p in fp.pads] == [str(n) for n in range(1, 101)]
        for i, pad in enumerate(fp.pads):
            side, offset = divmod(i, 25)
            expected = ((-7.675, -6+.5*offset), (-6+.5*offset, 7.675),
                        (7.675, 6-.5*offset), (6-.5*offset, -7.675))[side]
            assert (pad.x_mm, pad.y_mm) == pytest.approx(expected)
            assert (pad.width_mm, pad.height_mm) == ((1.6, .3) if side % 2 == 0 else (.3, 1.6))


def test_headers_have_explicit_centred_origin_without_mutating_existing_header():
    with physical.scoped_footprints() as overlay:
        header = overlay[physical.SOURCES[2][0]]
        assert len(header.pads) == 40
        assert [(p.x_mm, p.y_mm) for p in header.pads[:2]] == [(-1.27, -24.13), (1.27, -24.13)]
        assert [(p.x_mm, p.y_mm) for p in header.pads[-2:]] == [(-1.27, 24.13), (1.27, 24.13)]
        assert all(p.kind == "thru_hole" and p.drill.width_mm == 1 for p in header.pads)
        old = FOOTPRINTS["Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"]
        centred = overlay[physical.SOURCES[3][0]]
        assert old.pads[0].y_mm == 0
        assert [p.y_mm for p in centred.pads] == pytest.approx([-6.35, -3.81, -1.27, 1.27, 3.81, 6.35])
        board = physical.build_board_constraints(build_design().circuit)
        pose = next(p for p in board.placements if p.component_ref == "J2")
        assert pad_position(header, pose, "1") == pytest.approx((25.87, 8.27))
        assert pad_position(header, pose, "2") == pytest.approx((25.87, 5.73))
        assert pad_position(header, pose, "40") == pytest.approx((74.13, 5.73))


@pytest.mark.parametrize("angle,expected_size,expected_drill", [
    (0, (2., 1.), (.8, .4)), (90, (1., 2.), (.4, .8)),
    (180, (2., 1.), (.8, .4)), (270, (1., 2.), (.4, .8)),
])
def test_local_pad_and_slot_orientation_is_normalized_without_rotating_pad_centre(angle, expected_size, expected_drill):
    root = parse(f'''(footprint "test"
        (pad "1" thru_hole oval (at 3 4 {angle}) (size 2 1) (drill oval .8 .4))
        (fp_rect (start -5 -5) (end 5 5) (layer "F.CrtYd")))''')
    fp = physical._parsed_definition("test", "test.kicad_mod", "a"*64, (-1., -2.), root)
    pad = fp.pads[0]
    assert (pad.x_mm, pad.y_mm) == (2., 2.)
    assert (pad.width_mm, pad.height_mm) == expected_size
    assert (pad.drill.width_mm, pad.drill.height_mm) == expected_drill


@pytest.mark.parametrize("at,drill,expected", [
    ("3 4 45", ".5", "orthogonal"),
    ("3 4 0", ".5 (offset .1 0)", "Offset drills"),
])
def test_unsupported_pad_transform_fails_closed(at, drill, expected):
    root = parse(f'''(footprint "test"
        (pad "1" thru_hole oval (at {at}) (size 2 1) (drill {drill}))
        (fp_rect (start -5 -5) (end 5 5) (layer "F.CrtYd")))''')
    with pytest.raises(ValueError, match=expected):
        physical._parsed_definition("test", "test.kicad_mod", "a"*64, (0., 0.), root)


def test_unknown_or_incomplete_inventory_cannot_reuse_the_authored_layout():
    with pytest.raises(ValueError, match="requires"):
        physical.build_board_constraints(SimpleNamespace(components=[]))
    with pytest.raises(ValueError, match="no authored position"):
        physical.build_board_constraints(SimpleNamespace(components=[SimpleNamespace(ref="GHOST")]))


def _compile(tmp_path, board=None):
    design = build_design()
    board = board or physical.build_board_constraints(design.circuit)
    schematic = KiCadSchematicCompiler(design.catalog).compile(design.circuit, tmp_path / "controller.kicad_sch")
    artifact = physical.ControllerPcbCompiler(design.catalog).compile(
        design.circuit, schematic, board, tmp_path / "controller.kicad_pcb")
    return design, board, artifact


def test_actual_controller_has_no_placement_failures_and_all_holes_are_real_source_bound_drills(tmp_path):
    reference = Path(__file__).resolve().parents[1] / "apps/web/reference-board.json"
    original = reference.read_bytes()
    with physical.scoped_footprints():
        design, board, artifact = _compile(tmp_path)
        report = artifact.compilation.physical_verification
        assert report.passed, [f.model_dump() for f in report.findings if f.status.value != "pass"]
        assert len(design.circuit.components) == len(artifact.compilation.footprint_bindings) == 69
        assert not any(p.component_ref.startswith("H") for p in artifact.compilation.pad_bindings)
        root = parse(artifact.path.read_text())
        holes = {node.atoms()[0].removeprefix("ohmni_generated_"): node
                 for node in root.children("footprint") if node.atoms()[0].startswith("ohmni_generated_H")}
        assert set(holes) == {"H1", "H2", "H3", "H4"}
        for expected in physical.MOUNTING_HOLES:
            node = holes[expected["ref"]]
            assert list(map(float, node.child("at").atoms()[:2])) == [expected["x_mm"], expected["y_mm"]]
            pad, = node.children("pad")
            assert pad.atoms() == ["", "np_thru_hole", "circle"]
            assert pad.child("drill").atoms() == ["3.2"]
            assert pad.optional("net") is None
            assert "board_only" in node.child("attr").atoms()
        obstacles = DeterministicRouter._pad_obstacles(artifact, board, {})
        for expected in physical.MOUNTING_HOLES:
            assert any(net is None and point.x_mm == expected["x_mm"] and point.y_mm == expected["y_mm"]
                and width == pytest.approx(6.9) and height == pytest.approx(6.9)
                and layers == ("F.Cu", "B.Cu") for net, point, width, height, layers in obstacles)
        assert artifact.fingerprint.digest == hashlib.sha256(artifact.path.read_bytes()).hexdigest()
        # Removing mechanical bytes invalidates the artifact just as removing copper does.
        artifact.path.write_bytes(artifact.path.read_bytes().replace(b'(drill 3.2)', b'(drill 3.1)', 1))
        assert not artifact.is_current
    assert reference.read_bytes() == original


@pytest.mark.parametrize("mutation", ["remove", "move", "relative"])
def test_missing_or_changed_hole_exclusion_blocks_compilation(tmp_path, mutation):
    design = build_design()
    board = physical.build_board_constraints(design.circuit)
    index = next(i for i, c in enumerate(board.placement_constraints) if c.constraint_id == "mechanical-H1")
    if mutation == "remove":
        del board.placement_constraints[index]
    elif mutation == "relative":
        board.placement_constraints[index] = board.placement_constraints[index].model_copy(update={"relative_to_component": True})
    else:
        region = board.placement_constraints[index].keepout_region.model_copy(update={"x_min_mm": 0})
        board.placement_constraints[index] = board.placement_constraints[index].model_copy(update={"keepout_region": region})
    with physical.scoped_footprints(), pytest.raises(PcbCompilationError, match="mechanical exclusion"):
        _compile(tmp_path, board)


def test_component_cannot_overlap_a_mounting_hole(tmp_path):
    design = build_design()
    board = physical.build_board_constraints(design.circuit)
    board.placements = [p.model_copy(update={"x_mm": 5, "y_mm": 5}) if p.component_ref == "R1" else p
                        for p in board.placements]
    with physical.scoped_footprints():
        _, _, artifact = _compile(tmp_path, board)
    assert any(f.constraint_id == "mechanical-H1" and f.status.value == "fail"
               for f in artifact.compilation.physical_verification.findings)


def test_local_bus_placement_and_indicator_fanout_reduce_crossings():
    design = build_design()
    board = physical.build_board_constraints(design.circuit)
    poses = {p.component_ref: p for p in board.placements}
    with physical.scoped_footprints():
        def position(ref, pin):
            instance = design.circuit.component(ref)
            package = design.catalog.require(instance.part_id).packages[0]
            return pad_position(FOOTPRINTS[package.kicad_footprint], poses[ref], str(pin))
        for mcu_pin, memory_pin in ((29, 1), (30, 6), (31, 2), (32, 5)):
            assert math.dist(position("U1", mcu_pin), position("U3", memory_pin)) < 16
        for mcu_pin, debug_pin in ((72, 2), (76, 4)):
            assert math.dist(position("U1", mcu_pin), position("J3", debug_pin)) < 20
        for driver, first_resistor in (("U4", 21), ("U5", 29)):
            driver_points = [position(driver, pin) for pin in range(1, 8)]
            resistor_points = [position(f"R{index}", 1) for index in range(first_resistor, first_resistor+7)]
            assert all(point[0] > poses[driver].x_mm for point in driver_points)
            assert all(a[1] > b[1] for a, b in pairwise(driver_points))
            assert all(a[1] > b[1] for a, b in pairwise(resistor_points))


@pytest.mark.parametrize("angle,centre,size,drill", [
    (0, (3, 4), (2, 1), (.8, .4)),
    (90, (-4, 3), (1, 2), (.4, .8)),
    (180, (-3, -4), (2, 1), (.8, .4)),
    (270, (4, -3), (1, 2), (.4, .8)),
])
def test_controller_emission_bakes_pose_into_copper_drill_and_courtyard(angle, centre, size, drill):
    source = parse('''(footprint "test"
        (pad "1" thru_hole oval (at 3 4) (size 2 1) (drill oval .8 .4))
        (fp_rect (start -5 -6) (end 5 6) (layer "F.CrtYd")))''')
    fp = physical._parsed_definition("test", "test.kicad_mod", "a"*64, (0., 0.), source)
    original_hash = fp.content_hash
    pose = SimpleNamespace(x_mm=20, y_mm=30, rotation_deg=angle)
    rows = physical.ControllerPcbCompiler(None)._render_footprint(
        "test", SimpleNamespace(ref="TEST", part_id="test"), fp, pose, {}, {})
    emitted = parse("\n".join(rows))
    assert list(map(float, emitted.child("at").atoms())) == [20, 30, 0]
    pad, = emitted.children("pad")
    assert tuple(map(float, pad.child("at").atoms())) == centre
    assert tuple(map(float, pad.child("size").atoms())) == size
    assert tuple(map(float, pad.child("drill").atoms()[1:])) == drill
    assert tuple(map(float, emitted.child("fp_rect").child("end").atoms())) == (
        (6, 5) if angle in (90, 270) else (5, 6))
    assert fp.content_hash == original_hash
    assert pose.rotation_deg == angle


@pytest.mark.integration
def test_native_kicad_loads_every_controller_pad_at_router_position_with_correct_axes(tmp_path):
    """Independent native loader catches sign errors and absolute pad angles.

    The old positive-angle writer fails for C4, U3 and J2, even though its
    source-side physical checks pass. Include every copper and mechanical pad.
    """
    executable = find_kicad_cli()
    if executable is None:
        pytest.skip("Native KiCad unavailable")
    bundled_python = Path(executable).with_name("python.exe")
    python = str(bundled_python) if bundled_python.is_file() else sys.executable
    probe = subprocess.run([python, "-c", "import pcbnew"], capture_output=True, text=True, timeout=30, check=False)
    if probe.returncode:
        pytest.skip("Native pcbnew Python bindings unavailable")
    expected = {}
    with physical.scoped_footprints():
        _design, board, artifact = _compile(tmp_path)
        poses = {p.component_ref: p for p in board.placements}
        pad_nets = {(b.component_ref, b.pad_number): b.net_name or ""
                    for b in artifact.compilation.pad_bindings}
        for binding in artifact.compilation.footprint_bindings:
            ref = binding.component_ref
            pose = poses[ref]
            fp = FOOTPRINTS[binding.footprint_id]
            theta = math.radians(pose.rotation_deg)
            quarter_turn = round(pose.rotation_deg / 90) % 2
            rows = []
            for pad in fp.pads:
                x = pose.x_mm+pad.x_mm*math.cos(theta)-pad.y_mm*math.sin(theta)
                y = pose.y_mm+pad.x_mm*math.sin(theta)+pad.y_mm*math.cos(theta)
                width, height = (pad.height_mm, pad.width_mm) if quarter_turn else (pad.width_mm, pad.height_mm)
                dw, dh = (pad.drill.width_mm, pad.drill.height_mm) if pad.drill else (0., 0.)
                if quarter_turn:
                    dw, dh = dh, dw
                rows.append([pad.number, round(x, 6), round(y, 6), width, height, dw, dh,
                             pad_nets.get((ref, pad.number), "")])
            expected[ref] = sorted(rows)
            assert binding.geometry_fingerprint == fp.content_hash
        for hole in physical.MOUNTING_HOLES:
            expected[hole["ref"]] = [["", hole["x_mm"], hole["y_mm"], 3.2, 3.2, 3.2, 3.2, ""]]
    script = '''import json,sys,pcbnew
board=pcbnew.LoadBoard(sys.argv[1])
result={}
for footprint in board.GetFootprints():
    assert footprint.GetOrientationDegrees() == 0
    pads=[]
    for pad in footprint.Pads():
        assert pad.GetOrientationDegrees() == 0
        pos,size,drill=pad.GetPosition(),pad.GetSize(),pad.GetDrillSize()
        pads.append([pad.GetNumber(),*[round(pcbnew.ToMM(v),6) for v in
            (pos.x,pos.y,size.x,size.y,drill.x,drill.y)],pad.GetNetname()])
    result[footprint.GetReference()]=sorted(pads)
print(json.dumps(result))
'''
    result = subprocess.run([python, "-c", script, str(artifact.path)],
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    actual = json.loads(result.stdout)
    assert actual.keys() == expected.keys()
    for ref, pads in expected.items():
        assert len(actual[ref]) == len(pads)
        for loaded, source in zip(actual[ref], pads, strict=True):
            assert loaded[0] == source[0], ref
            assert loaded[-1] == source[-1], ref
            # The shared serializer emits three decimal places; tolerate at
            # most half a micrometre, not a pin-pitch/orientation discrepancy.
            assert loaded[1:-1] == pytest.approx(source[1:-1], abs=.000501), (ref, source[0])
