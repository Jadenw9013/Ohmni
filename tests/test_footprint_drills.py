"""Source-pinned through-hole geometry, emitted drills, and geometry lineage."""

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.eda.kicad.pcb_compiler import PCB_COMPILER_VERSION, PcbCompilationError
from ohmni.physical.footprints import FOOTPRINTS, footprint, footprint_geometry_fingerprint
from ohmni.physical.models import FootprintDrill, FootprintPad
from ohmni.physical.placement import generate_placement
from ohmni.routing.models import Point, RoutingProfile, TrackSegment
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.spatial import RoutingObstacles
from ohmni.routing.verifier import _pad_clearance_violations
from ohmni.synthesis import ArchetypeId, SynthesisBrief, synthesize

SOURCES = Path(__file__).resolve().parents[1] / "fixtures" / "footprint_sources"
HEADER = "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical"
USB = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
BUTTON = "Button_Switch_THT:SW_PUSH_6mm"


def _sexpr(text):
    """Read only test snapshots/output, independently of the PCB serializer."""
    root, stack = [], []
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        if token == "(":
            value = []
            (stack[-1] if stack else root).append(value)
            stack.append(value)
        elif token == ")":
            stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    assert not stack and len(root) == 1
    return root[0]


def _pad_record(pad, translation=(0, 0)):
    fields = {item[0]: item[1:] for item in pad[4:] if isinstance(item, list)}
    x, y = (float(value) for value in fields["at"][:2])
    width, height = (float(value) for value in fields["size"])
    drill = fields.get("drill")
    shape = "oval" if drill and drill[0] == "oval" else "circle" if drill else None
    dimensions = tuple(float(value) for value in drill[1:]) if shape == "oval" else (float(drill[0]),) * 2 if drill else ()
    return (pad[1], pad[2], pad[3], round(x+translation[0], 6), round(y+translation[1], 6),
            width, height, shape, *dimensions)


def _local_record(pad):
    return (pad.number, pad.kind, pad.shape, round(pad.x_mm, 6), round(pad.y_mm, 6),
            pad.width_mm, pad.height_mm, pad.drill.shape if pad.drill else None,
            *((pad.drill.width_mm, pad.drill.height_mm) if pad.drill else ()))


@pytest.mark.parametrize("identifier,translation", [(HEADER, (0, 0)), (USB, (0, 0)), (BUTTON, (-3.25, -2.25))])
def test_local_pad_and_drill_geometry_matches_unmodified_pinned_source(identifier, translation):
    definition = footprint(identifier)
    raw = (SOURCES / (identifier.split(":", 1)[1]+".kicad_mod")).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == definition.source.upstream_file_sha256
    source = _sexpr(raw.decode("utf-8"))
    expected = Counter(_pad_record(item, translation) for item in source if isinstance(item, list) and item[0] == "pad")
    assert Counter(_local_record(pad) for pad in definition.pads) == expected


@pytest.mark.parametrize("changes", [
    {"kind": "thru_hole"},
    {"drill": {"shape": "circle", "width_mm": .5, "height_mm": .5}},
    {"kind": "thru_hole", "drill": {"shape": "circle", "width_mm": 2, "height_mm": 2}},
    {"kind": "thru_hole", "drill": {"shape": "circle", "width_mm": .5, "height_mm": .6}},
    {"kind": "thru_hole", "drill": {"shape": "oval", "width_mm": .5, "height_mm": .5}},
    {"kind": "thru_hole", "drill": {"shape": "circle", "width_mm": float("nan"), "height_mm": .5}},
    {"kind": "np_thru_hole", "shape": "circle", "drill": {"shape": "circle", "width_mm": .5, "height_mm": .5}},
    {"kind": "np_thru_hole", "shape": "circle", "number": "", "mechanical": True,
     "drill": {"shape": "circle", "width_mm": .5, "height_mm": .5}},
    {"kind": "future_pad"},
])
def test_unknown_missing_or_inconsistent_drills_are_rejected(changes):
    with pytest.raises(ValueError):
        FootprintPad.model_validate({"number": "1", "x_mm": 0, "y_mm": 0,
                                     "width_mm": 2, "height_mm": 2, **changes})


@pytest.fixture
def controller(tmp_path, catalog):
    result = synthesize(SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
                                      sensors=(), button_count=1), catalog)
    assert result.accepted
    generated = generate_placement(result.circuit, result.placement_request, catalog)
    schematic = KiCadSchematicCompiler(catalog).compile(result.circuit, tmp_path / "controller.kicad_sch")
    pcb = KiCadPcbCompiler(catalog).compile(result.circuit, schematic, generated.board, tmp_path / "controller.kicad_pcb")
    return result.circuit, schematic, pcb, generated.board


def test_compiler_emits_exact_round_drills_oval_slots_and_nonplated_holes(controller):
    _circuit, _schematic, pcb, _board = controller
    assert pcb.compiler_version == PCB_COMPILER_VERSION == "0.2.0"
    emitted = _sexpr(pcb.path.read_text(encoding="utf-8"))
    by_id = {}
    for item in emitted:
        if isinstance(item, list) and item[0] == "footprint":
            identifier = next(prop[2] for prop in item if isinstance(prop, list) and prop[:2] == ["property", "OhmniFootprintSource"])
            by_id[identifier] = item
    for identifier in (HEADER, USB, BUTTON):
        actual = Counter(_pad_record(item) for item in by_id[identifier] if isinstance(item, list) and item[0] == "pad")
        assert actual == Counter(_local_record(pad) for pad in footprint(identifier).pads)
    for binding in pcb.compilation.footprint_bindings:
        assert binding.geometry_fingerprint == footprint(binding.footprint_id).content_hash
    usb_ref = next(binding.component_ref for binding in pcb.compilation.footprint_bindings if binding.footprint_id == USB)
    assert all(binding.pin_number for binding in pcb.compilation.pad_bindings if binding.component_ref == usb_ref)


def test_compiler_refuses_model_copy_that_bypasses_drill_validation(controller, catalog, tmp_path, monkeypatch):
    circuit, schematic, _pcb, board = controller
    definition = footprint(HEADER)
    invalid = definition.model_copy(update={"pads": [definition.pads[0].model_copy(update={"drill": None}), *definition.pads[1:]]})
    monkeypatch.setitem(FOOTPRINTS, HEADER, invalid)
    destination = tmp_path / "invalid.kicad_pcb"
    with pytest.raises(PcbCompilationError, match="explicit source-recorded drill"):
        KiCadPcbCompiler(catalog).compile(circuit, schematic, board, destination)
    assert not destination.exists()


def test_geometry_hash_changes_with_local_drill_even_when_source_identity_is_unchanged(monkeypatch):
    original = footprint(HEADER)
    before = footprint_geometry_fingerprint([HEADER, USB])
    assert before == footprint_geometry_fingerprint([USB, HEADER, HEADER])
    changed = original.model_copy(deep=True)
    changed.pads[0].drill = FootprintDrill(shape="circle", width_mm=.9, height_mm=.9)
    assert changed.source == original.source
    assert changed.content_hash != original.content_hash
    monkeypatch.setitem(FOOTPRINTS, HEADER, changed)
    assert footprint_geometry_fingerprint([HEADER, USB]) != before
    with pytest.raises(ValueError, match="unknown footprint"):
        footprint_geometry_fingerprint(["invented:footprint"])


@pytest.mark.parametrize("layer", ["F.Cu", "B.Cu"])
def test_nonplated_locating_holes_are_obstacles_on_both_layers(controller, layer):
    _circuit, _schematic, pcb, board = controller
    binding = next(binding for binding in pcb.compilation.footprint_bindings if binding.footprint_id == USB)
    hole = next(pad for pad in footprint(USB).pads if pad.kind == "np_thru_hole")
    place = next(place for place in board.placements if place.component_ref == binding.component_ref)
    angle = math.radians(place.rotation_deg)
    point = Point(x_mm=place.x_mm+hole.x_mm*math.cos(angle)-hole.y_mm*math.sin(angle),
                  y_mm=place.y_mm+hole.x_mm*math.sin(angle)+hole.y_mm*math.cos(angle))
    centres = DeterministicRouter._pad_centres(pcb, board)
    pads = DeterministicRouter._pad_obstacles(pcb, board, centres)
    assert RoutingObstacles("TEST", RoutingProfile(), pads, {}).blocked(point, ("F.Cu", "B.Cu").index(layer), .125)
    track = TrackSegment(segment_id="test", attempt_id="test", net_name="TEST", layer=layer,
        start=Point(x_mm=point.x_mm-.1, y_mm=point.y_mm), end=Point(x_mm=point.x_mm+.1, y_mm=point.y_mm), width_mm=.25)
    violations = _pad_clearance_violations(pcb, board, SimpleNamespace(tracks=[track], vias=[]), .2)
    assert f"TEST/{binding.component_ref}." in violations
