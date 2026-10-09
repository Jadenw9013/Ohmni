"""Isolated, source-bound physical authoring for the controller landing board.

Only this author uses the additions and mechanical compiler. The product's
accepted footprint registry is restored even when authoring is interrupted.
Coordinates are top-view board millimetres, with +Y toward the bottom.
"""
from __future__ import annotations

import hashlib
import math
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from ohmni.eda.kicad.component_asset_parser import parse
from ohmni.eda.kicad.pcb_compiler import KiCadPcbCompiler, PcbCompilationError
from ohmni.physical.footprints import FOOTPRINTS, LICENSE, footprint_geometry_fingerprint
from ohmni.physical.models import (
    BoardConstraints,
    BoardOutline,
    ComponentPlacement,
    FootprintDefinition,
    FootprintDrill,
    FootprintPad,
    FootprintSource,
    PlacementConstraint,
    PlacementPose,
    PlacementRegion,
)
from ohmni.routing.models import (
    NetRoutingConstraint,
    ProfileValue,
    RoutingConstraints,
    RoutingProfile,
)
from ohmni.synthesis.placement import policy_evidence

SOURCE_DIRECTORY = Path(__file__).resolve().parents[2] / "examples/landing-controller/footprints"
# Public identity, pinned filename, SHA256, common (x,y) origin translation.
SOURCES = (
    ("Package_QFP:LQFP-100_14x14mm_P0.5mm", "LQFP-100_14x14mm_P0.5mm.kicad_mod",
     "777168782dd4ed12f1ad208fd3d882297d1404158aeaedaa26ae42ddf1839623", (0., 0.)),
    ("Package_SO:SOIC-16_3.9x9.9mm_P1.27mm", "SOIC-16_3.9x9.9mm_P1.27mm.kicad_mod",
     "a3e0cad48591b1bf41f77aa964868c62b28d32f1014a42a763a17ac184231f7f", (0., 0.)),
    ("Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
     "PinHeader_2x20_P2.54mm_Vertical.kicad_mod",
     "98adf9a263feb8ec4e92e68d7494a0ebb6bea4f124fc4fe02c3458719ba9cac6", (-1.27, -24.13)),
    ("Ohmni_Landing:PinHeader_1x06_P2.54mm_Vertical_Centered",
     "PinHeader_1x06_P2.54mm_Vertical.kicad_mod",
     "e3c3501f520fc1fc39eeb5d72137e680e509c0df2348ca77fef1b9db6ab974f0", (0., -6.35)),
    ("MountingHole:MountingHole_3.2mm_M3", "MountingHole_3.2mm_M3.kicad_mod",
     "3853c52bba27d3e3e3e18db44a20dfb296eb9e6cd16ebf26fe4a96a2ee8add3b", (0., 0.)),
)


def _parsed_definition(identifier, filename, digest, translation, root):
    """Normalize orthogonal local-pad axes without changing the pad centre.

FootprintPad does not store local rotation. An orthogonal rotation therefore
swaps width/height (including an oval drill), preserving the actual envelope.
Arbitrary angles, offset drills and unsupported pad kinds fail closed.
"""
    if root.head != "footprint" or root.atoms()[0] != Path(filename).stem:
        raise ValueError(f"Unexpected footprint identity in {filename}")
    tx, ty = translation
    pads = []
    for node in root.children("pad"):
        number, kind, shape = node.atoms()
        at = list(map(float, node.child("at").atoms()))
        angle = at[2] if len(at) == 3 else 0.
        if len(at) not in (2, 3) or not math.isclose(angle % 90, 0, abs_tol=1e-8):
            raise ValueError("Only orthogonal local pad rotations are supported")
        width, height = map(float, node.child("size").atoms())
        quarter_turn = round(angle / 90) % 2
        if quarter_turn:
            width, height = height, width
        drill = None
        if drill_node := node.optional("drill"):
            values = drill_node.atoms()
            if any(not isinstance(item, str) for item in drill_node.items):
                raise ValueError("Offset drills are not supported")
            if len(values) == 1:
                dw = dh = float(values[0])
                drill_shape = "circle"
            elif len(values) == 3 and values[0] == "oval":
                dw, dh = map(float, values[1:])
                drill_shape = "oval"
            else:
                raise ValueError("Only centered circle and oval drills are supported")
            if quarter_turn:
                dw, dh = dh, dw
            drill = FootprintDrill(shape=drill_shape, width_mm=dw, height_mm=dh)
        pads.append(FootprintPad(number=number, kind=kind, shape=shape,
            x_mm=at[0]+tx, y_mm=at[1]+ty, width_mm=width, height_mm=height,
            mechanical=kind == "np_thru_hole", drill=drill))
    courtyard = []
    for kind in ("fp_line", "fp_rect", "fp_circle"):
        for node in root.children(kind):
            if node.child("layer").atoms() != ["F.CrtYd"]:
                continue
            if kind == "fp_circle":
                cx, cy = map(float, node.child("center").atoms())
                ex, ey = map(float, node.child("end").atoms())
                radius = math.hypot(ex-cx, ey-cy)
                courtyard.extend(((cx-radius+tx, cy-radius+ty), (cx+radius+tx, cy+radius+ty)))
            else:
                for endpoint in ("start", "end"):
                    x, y = map(float, node.child(endpoint).atoms())
                    courtyard.append((x+tx, y+ty))
    if not pads or not courtyard:
        raise ValueError(f"Pinned footprint lacks pads or courtyard: {filename}")
    detail = ("Source pad-centre and orthogonal envelope subset parsed from the pinned local "
              "KiCad 10 library bytes; conservative symmetric courtyard bounding rectangle. "
              "Library provenance, not manufacturer land-pattern verification. "
              "Roundrect corner ratio is represented by the compiler default; it is not a full footprint clone.")
    if tx or ty:
        detail += f" All pads and courtyard translated by ({tx:g}, {ty:g}) mm to centre the pin array."
    return FootprintDefinition(footprint_id=identifier,
        width_mm=2*max(abs(x) for x, _ in courtyard),
        height_mm=2*max(abs(y) for _, y in courtyard), pads=pads,
        source=FootprintSource(library_id=identifier, upstream_file_sha256=digest,
                               license=LICENSE, derivation=detail))


def _definition(identifier, filename, digest, translation):
    raw = (SOURCE_DIRECTORY / filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"Pinned controller footprint bytes changed: {filename}")
    return _parsed_definition(identifier, filename, digest, translation, parse(raw.decode("utf-8")))


def footprint_manifest():
    return [{"footprint_id": item[0], "file": item[1], "sha256": item[2],
             "translation_mm": list(item[3]), "geometry_fingerprint": _definition(*item).content_hash,
             "source_kind": "pinned_KiCad_library", "license": LICENSE} for item in SOURCES]


@contextmanager
def scoped_footprints():
    original = dict(FOOTPRINTS)
    before = footprint_geometry_fingerprint()
    definitions = {item[0]: _definition(*item) for item in SOURCES}
    if set(original) & set(definitions):
        raise ValueError("Controller overlay must not replace an existing footprint identity")
    try:
        FOOTPRINTS.update(definitions)
        yield definitions
    finally:
        FOOTPRINTS.clear()
        FOOTPRINTS.update(original)
        if footprint_geometry_fingerprint() != before:
            raise RuntimeError("Original footprint registry changed during controller authoring")


BOARD_WIDTH_MM = 100.
BOARD_HEIGHT_MM = 70.
MOUNTING_HOLES = tuple({"ref": f"H{i}", "x_mm": x, "y_mm": y,
    "diameter_mm": 3.2, "keepout_diameter_mm": 6.9, "kind": "np_thru_hole",
    "source_footprint": SOURCES[-1][0], "source_sha256": SOURCES[-1][2]}
    for i, (x, y) in enumerate(((5., 5.), (95., 5.), (5., 65.), (95., 65.)), 1))

POSITIONS = {
    "U1": (49., 35., 0), "U2": (24., 52., 0), "U3": (35., 49., 90),
    "U4": (73., 24.5, 180), "U5": (73., 48.5, 180),
    "J1": (50., 65., 0), "J2": (50., 7., 270), "J3": (64.5, 40., 0),
    "SW1": (16., 16., 0), "SW2": (16., 38., 0),
    "C1": (21., 48., 0), "C2": (28., 48., 0),
    "C3": (37., 34., 180), "C4": (39.5, 47., 90),
    "C5": (59.5, 47., 90), "C6": (60.5, 24.5, 0), "C7": (39., 24.5, 180),
    "C8": (30., 55., 0), "C9": (37., 31., 180),
    "C10": (37., 38., 180), "C11": (37., 41., 180), "C12": (37., 36., 180),
    "C13": (36., 55., 0), "C14": (67., 31., 180), "C15": (67., 55., 180),
    "R1": (43., 61., 0), "R2": (57., 61., 0), "R3": (32., 35., 0),
    "R4": (34., 22., 0), "R5": (40., 57., 90), "R6": (37.5, 44., 180),
    "R7": (44., 57., 90), "R8": (48., 57., 90), "R9": (52., 57., 90),
    "R10": (56., 57., 90), "R11": (60., 57., 90), "R12": (28., 39., 0),
}
for _index in range(16):
    # Numbering is electrical; reverse display order to follow the rotated
    # register's QB..QH lead order without crossing all seven signal paths.
    _y = (15. if _index < 8 else 42.) + (7 - _index % 8)*3.2
    POSITIONS[f"D{_index+1}"] = (88., _y, 0)
    POSITIONS[f"R{_index+20}"] = (83., _y, 0)


def _hole_region(hole):
    r = hole["keepout_diameter_mm"]/2
    return PlacementRegion(x_min_mm=hole["x_mm"]-r, y_min_mm=hole["y_mm"]-r,
        x_max_mm=hole["x_mm"]+r, y_max_mm=hole["y_mm"]+r)


def build_board_constraints(circuit):
    refs = {part.ref for part in circuit.components}
    unknown = refs - POSITIONS.keys()
    if unknown:
        raise ValueError(f"Controller layout has no authored position for {sorted(unknown)}")
    if missing := POSITIONS.keys() - refs:
        raise ValueError(f"Controller layout requires {sorted(missing)}")
    placements = [ComponentPlacement(component_ref=ref, x_mm=POSITIONS[ref][0],
        y_mm=POSITIONS[ref][1], rotation_deg=POSITIONS[ref][2],
        reason="Authored controller functional layout; physical envelopes and routed copper checked separately")
        for ref in sorted(refs)]
    constraints = []

    def add(identifier, kind, ref, reason, **values):
        constraints.append(PlacementConstraint(constraint_id=identifier, kind=kind,
            component_ref=ref, reason=reason,
            evidence=[policy_evidence("Controller physical authoring policy", reason)], **values))

    for ref in ("U1", "J1", "J2", "J3"):
        x, y, angle = POSITIONS[ref]
        add(f"fixed-{ref}", "fixed", ref, "Keep the authored IC and connector poses stable.",
            fixed_pose=PlacementPose(x_mm=x, y_mm=y, rotation_deg=angle))
    for ref, edge, distance in (("J1", "bottom", 1), ("J2", "top", 4)):
        add(f"edge-{ref}", "board_edge", ref, "Keep the connector accessible at its authored edge.",
            preferred_edge=edge, maximum_distance_mm=distance)
    for hole in MOUNTING_HOLES:
        add(f"mechanical-{hole['ref']}", "keepout", "U1",
            "Source 3.2 mm NPTH with 6.9 mm source courtyard used as a conservative copper/component exclusion; independent mechanical feature, not an electrical component.",
            keepout_region=_hole_region(hole))
    for ref, target, target_pin, distance in (
        ("C3", "U1", "11", 6), ("C4", "U1", "28", 6),
        ("C5", "U1", "50", 6), ("C6", "U1", "75", 6), ("C7", "U1", "100", 6),
        ("C9", "U1", "6", 6), ("C10", "U1", "22", 6), ("C11", "U1", "22", 6),
        ("C12", "U1", "14", 6), ("C13", "U3", "8", 6),
        ("C14", "U4", "16", 6), ("C15", "U5", "16", 6),
        ("C1", "U2", "1", 6), ("C2", "U2", "5", 6),
    ):
        add(f"near-{ref}-{target}-{target_pin}", "near_component", ref,
            "Authored maximum capacitor-to-supply pad distance; not an impedance or transient-performance claim.",
            component_pin="1", target_ref=target, target_pin=target_pin, maximum_distance_mm=distance)
    return BoardConstraints(outline=BoardOutline(width_mm=BOARD_WIDTH_MM, height_mm=BOARD_HEIGHT_MM),
        placements=placements, placement_constraints=constraints)


def routing_constraints(circuit=None):
    return RoutingConstraints(nets=[NetRoutingConstraint(net_name="GND", preferred_layer="B.Cu",
        provenance="board_profile", rationale="Prefer back copper for long return links to leave front-side LQFP escape space; not a ground-plane or impedance claim")], profile=RoutingProfile(
        name="controller fine-pitch two-layer draft geometry",
        signal_width_mm=ProfileValue(value=.15, provenance="board_profile", rationale="0.5 mm LQFP escape; process capability not qualified"),
        power_width_mm=ProfileValue(value=.25, provenance="board_profile", rationale="Draft low-power geometry, not a copper-current capacity result"),
        clearance_mm=ProfileValue(value=.15, provenance="board_profile", rationale="Authored fine-pitch geometry, subject to fabricator review"),
        via_diameter_mm=ProfileValue(value=.6, provenance="board_profile", rationale="Authored 0.6/0.3 mm through-via geometry for LQFP fanout; fabrication capability not yet qualified"),
        via_drill_mm=ProfileValue(value=.3, provenance="board_profile", rationale="Paired with 0.6 mm via diameter; same 0.15 mm minimum annular ring on both layers"),
        grid_mm=ProfileValue(value=.125, provenance="project_default", rationale="Bounded grid resolves 0.5 mm lead pitch"),
        maximum_expanded_nodes=ProfileValue(value=900000, provenance="project_default", rationale="Larger bounded search for the dense 100-pin breakout; preserves clearance and widths"),
    ))


class ControllerPcbCompiler(KiCadPcbCompiler):
    """Emit independent, source-derived mechanical holes without fake pins.

The normal compiler hashes the completed file after this render hook, so all
mechanical bytes belong to the resulting PCB artifact identity. Absolute hole
keepouts are mandatory router input, not a renderer-only decoration.
"""

    def compile(self, circuit, schematic, constraints, destination, routing_plan=None):
        by_id = {item.constraint_id: item for item in constraints.placement_constraints}
        definition = _definition(*SOURCES[-1])
        for hole in MOUNTING_HOLES:
            pad = definition.pads[0]
            if (pad.kind != hole["kind"] or pad.width_mm != hole["diameter_mm"]
                    or definition.width_mm != hole["keepout_diameter_mm"]):
                raise PcbCompilationError("Mounting-hole geometry differs from its pinned source")
            constraint = by_id.get(f"mechanical-{hole['ref']}")
            if (constraint is None or constraint.kind.value != "keepout"
                    or constraint.keepout_region != _hole_region(hole) or constraint.relative_to_component):
                raise PcbCompilationError(f"Missing or changed mechanical exclusion for {hole['ref']}")
        return super().compile(circuit, schematic, constraints, destination, routing_plan)

    def _render_footprint(self, seed, instance, fp, place, nets, pad_nets):
        # Native KiCad interprets footprint rotation with the opposite sign to
        # the controller's board-XY matrix, and pad angles are board-absolute.
        # Bake orthogonal poses into a temporary geometry copy, leaving the
        # original footprint/pose bindings intact for routing and the viewer.
        # This also rotates rectangular copper and oval drill axes explicitly.
        if not math.isclose(place.rotation_deg % 90, 0, abs_tol=1e-8):
            raise PcbCompilationError("Controller serialization requires orthogonal placements")
        turns = round(place.rotation_deg / 90) % 4
        cosine, sine = ((1, 0), (0, 1), (-1, 0), (0, -1))[turns]
        pads = []
        for pad in fp.pads:
            values = {"x_mm": pad.x_mm*cosine-pad.y_mm*sine,
                      "y_mm": pad.x_mm*sine+pad.y_mm*cosine}
            if turns % 2:
                values.update(width_mm=pad.height_mm, height_mm=pad.width_mm)
                if pad.drill is not None:
                    values["drill"] = pad.drill.model_copy(update={
                        "width_mm": pad.drill.height_mm, "height_mm": pad.drill.width_mm})
            pads.append(pad.model_copy(update=values))
        values = {"pads": pads}
        if turns % 2:
            values.update(width_mm=fp.height_mm, height_mm=fp.width_mm)
        emitted_fp = fp.model_copy(update=values)
        emitted_pose = SimpleNamespace(x_mm=place.x_mm, y_mm=place.y_mm, rotation_deg=0)
        result = super()._render_footprint(seed, instance, emitted_fp, emitted_pose, nets, pad_nets)
        result.insert(4, f'    (property "OhmniAuthoredRotationDeg" "{place.rotation_deg:g}" '
                      '(at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))')
        if instance.ref == "U1":
            hole_definition = _definition(*SOURCES[-1])
            for hole in MOUNTING_HOLES:
                rows = super()._render_footprint(seed,
                    SimpleNamespace(ref=hole["ref"], part_id="M3 non-plated mounting hole"),
                    hole_definition, SimpleNamespace(x_mm=hole["x_mm"], y_mm=hole["y_mm"], rotation_deg=0), {}, {})
                result.extend(row.replace("(attr smd)", "(attr board_only exclude_from_pos_files exclude_from_bom)") for row in rows)
        return result
