"""Isolated, authored geometry for the landing circuit experiment.

This is a local authoring helper, never imported by the product runtime. The
existing registry is restored even if compilation fails. Run the complete
authoring operation in one process; this context is not a concurrent registry
service. Placement and route measurements do not establish switching-loop,
thermal, EMC, RF, assembly, or fabrication fitness.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path

from ohmni.eda.kicad.component_asset_parser import parse
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
from ohmni.synthesis.placement import ANTENNA_REGION, policy_evidence

SOURCE_DIRECTORY = Path(__file__).resolve().parents[2] / "examples/landing-redesign/footprints"
SOURCES = (
    ("Inductor_SMD:L_Coilcraft_XAL4020-XXX", "L_Coilcraft_XAL4020-XXX.kicad_mod",
     "2a45a4ea4dbccfc1e2f744c4225f65c4ddc37e555feb81a2021ac838ab920bbd", 0.0),
    ("Package_SO:VSSOP-8_2.3x2mm_P0.5mm", "VSSOP-8_2.3x2mm_P0.5mm.kicad_mod",
     "86c45430902f81c684c44234069616fc5b91e77178e928437c9a103bd4bcaf35", 0.0),
    ("Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
     "PinHeader_1x04_P2.54mm_Vertical.kicad_mod",
     "8952158347d7b7cc13924c62dccb0c48911af892bb009a0de27cb4d3c25cc1bb", -3.81),
)


def _definition(identifier, filename, expected_hash, translate_y):
    raw = (SOURCE_DIRECTORY / filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        raise ValueError(f"Pinned landing footprint bytes changed: {filename}")
    root = parse(raw.decode("utf-8"))
    if root.head != "footprint" or root.atoms()[0] != identifier.split(":", 1)[1]:
        raise ValueError(f"Unexpected footprint identity in {filename}")
    pads = []
    for node in root.children("pad"):
        number, kind, shape = node.atoms()
        at = list(map(float, node.child("at").atoms()))
        if len(at) > 2 and at[2] % 360:
            raise ValueError("Pinned authoring subset does not support rotated local pads")
        width, height = map(float, node.child("size").atoms())
        drill = None
        if drill_node := node.optional("drill"):
            values = drill_node.atoms()
            if len(values) != 1:
                raise ValueError("Only the pinned centered round header drills are supported")
            drill = FootprintDrill(shape="circle", width_mm=float(values[0]), height_mm=float(values[0]))
        pads.append(FootprintPad(number=number, kind=kind, shape=shape,
                                 x_mm=at[0], y_mm=at[1] + translate_y,
                                 width_mm=width, height_mm=height, drill=drill))
    courtyard = []
    for kind in ("fp_line", "fp_rect"):
        for node in root.children(kind):
            if node.child("layer").atoms() != ["F.CrtYd"]:
                continue
            for endpoint in ("start", "end"):
                x, y = map(float, node.child(endpoint).atoms())
                courtyard.append((x, y + translate_y))
    if not pads or not courtyard:
        raise ValueError(f"Pinned footprint lacks pads or courtyard: {filename}")
    # The source header is pin-1-origin; an explicitly recorded common
    # translation centers the entire subset without changing physical spacing.
    width = 2 * max(abs(x) for x, _ in courtyard)
    height = 2 * max(abs(y) for _, y in courtyard)
    detail = ("Exact pad subset and conservative courtyard bounding rectangle parsed from "
              "the pinned local KiCad 10 footprint library file; library provenance, "
              "not a manufacturer-datasheet verification.")
    if translate_y:
        detail += f" Every pad and courtyard translated by (0, {translate_y:g}) mm to center the courtyard."
    return FootprintDefinition(footprint_id=identifier, width_mm=width, height_mm=height,
                               pads=pads, source=FootprintSource(library_id=identifier,
                               upstream_file_sha256=expected_hash, license=LICENSE, derivation=detail))


def footprint_manifest():
    """Return checked, serializable source and subset identities."""
    return [{"footprint_id": item[0], "file": item[1], "sha256": item[2],
             "translation_mm": [0, item[3]], "geometry_fingerprint": _definition(*item).content_hash,
             "source_kind": "pinned_KiCad_library", "license": LICENSE}
            for item in SOURCES]


@contextmanager
def scoped_footprints():
    """Install authoring-only additions, restoring exact original objects."""
    original = dict(FOOTPRINTS)
    definitions = {item[0]: _definition(*item) for item in SOURCES}
    if set(definitions) & set(original):
        raise ValueError("Landing overlay must not replace any existing footprint identity")
    before = footprint_geometry_fingerprint()
    try:
        FOOTPRINTS.update(definitions)
        yield definitions
    finally:
        FOOTPRINTS.clear()
        FOOTPRINTS.update(original)
        if footprint_geometry_fingerprint() != before:
            raise RuntimeError("Original footprint registry mutated during isolated authoring")


# Explicit physical design, separate from semantic connectivity and render pose.
# Positions are millimetres in top-view board coordinates (+Y toward bottom).
POSITIONS = {
    "U1": (40.5, 17, 0), "U2": (20, 40, 0), "U3": (66, 40, 0),
    "J1": (40.5, 50, 0), "J2": (86, 14, 0),
    "L1": (15, 43, 180), "C1": (23.5, 43, 0), "C2": (10, 43, 180),
    "R6": (24.5, 37.3, 180), "R7": (24.5, 40, 0),
    "R1": (36, 42.5, 0), "R2": (43.5, 42.5, 0),
    "C3": (28, 13, 180), "C4": (28, 17, 180),
    "C5": (28, 9, 180), "R3": (24, 9, 0),
    "C6": (62, 40, 180), "C7": (70, 40, 0),
    "R4": (66, 35, 0), "R5": (70, 35, 0),
    "D1": (7, 10, 0), "D2": (7, 15, 0), "D3": (7, 20, 0), "D4": (7, 25, 0),
    "R10": (11, 10, 0), "R11": (11, 15, 0), "R12": (11, 20, 0), "R13": (11, 25, 0),
    "SW1": (70, 17, 0), "SW2": (70, 28, 0), "R20": (62, 17, 0), "R21": (62, 28, 0),
    "U4": (76, 44, 0), "J3": (86, 41, 0), "R8": (81, 42, 0), "R9": (81, 46, 0),
    "R14": (76, 39, 0), "C8": (72, 43.5, 180),
}


def build_board_constraints(circuit):
    """Return the authored 90 x 55 mm layout; reject unrecognized inventory."""
    refs = {part.ref for part in circuit.components}
    unknown = refs - POSITIONS.keys()
    if unknown:
        raise ValueError(f"Landing layout has no authored position for {sorted(unknown)}")
    required = {"U1", "U2", "U3", "J1", "L1", "C1", "C2", "R6", "R7"}
    if not required <= refs:
        raise ValueError(f"Landing layout requires {sorted(required - refs)}")
    placements = [ComponentPlacement(component_ref=ref, x_mm=POSITIONS[ref][0],
                                     y_mm=POSITIONS[ref][1], rotation_deg=POSITIONS[ref][2],
                                     reason="Authored landing redesign layout, independently checked before rendering")
                  for ref in sorted(refs)]
    constraints = []

    def add(identifier, kind, ref, reason, **values):
        constraints.append(PlacementConstraint(constraint_id=identifier, kind=kind,
            component_ref=ref, reason=reason,
            evidence=[policy_evidence("Landing redesign placement policy", reason)], **values))

    for ref in ("J1", "J2", "J3", "U1"):
        if ref not in refs:
            continue
        x, y, angle = POSITIONS[ref]
        add(f"fixed-port-{ref}", "fixed", ref,
            "Keep the authored connector/mating or module-antenna pose unchanged.",
            fixed_pose=PlacementPose(x_mm=x, y_mm=y, rotation_deg=angle))
    for ref, edge in (("J1", "bottom"), ("J2", "right"), ("J3", "right"), ("U1", "top")):
        if ref in refs:
            add(f"edge-{ref}", "board_edge", ref,
                "Authored edge access policy; mating/enclosure fit is not verified.",
                preferred_edge=edge, maximum_distance_mm=3)
    add("antenna-U1", "keepout", "U1",
        "Reuse the existing source-derived ESP32 antenna exclusion; compatibility with WROOM-32E remains assumed and RF unverified.",
        keepout_region=ANTENNA_REGION, relative_to_component=True)
    proximity = [
        ("C1", "1", "U2", "4", 3, "Input bypass positive land beside VIN"),
        ("C1", "2", "U2", "2", 6.5, "Input bypass return land near regulator ground"),
        ("L1", "1", "U2", "3", 4, "Switch node land beside regulator SW"),
        ("C2", "1", "L1", "2", 3.5, "Output capacitor positive land beside inductor output"),
        ("R6", "2", "U2", "5", 3.5, "Upper-divider FB land beside FB input"),
        ("R7", "1", "U2", "5", 3.5, "Lower-divider FB land beside FB input"),
        ("C3", "1", "U1", "2", 5, "Processor local supply bypass"),
        ("C4", "1", "U1", "2", 10, "Processor bulk supply support"),
        ("C5", "1", "U1", "3", 5, "Processor enable delay capacitor"),
        ("C6", "1", "U3", "8", 5, "Sensor supply bypass"),
        ("C7", "1", "U3", "6", 5, "Sensor I/O supply bypass"),
    ]
    for ref, pin, target, target_pin, distance, reason in proximity:
        if ref in refs and target in refs:
            add(f"near-{ref}-{pin}-{target}-{target_pin}", "near_component", ref,
                reason + "; maximum straight-line pad distance is an authored geometric limit, not a loop-performance claim.",
                component_pin=pin, target_ref=target, target_pin=target_pin,
                maximum_distance_mm=distance)
    for ref in ("U2", "C1", "C2", "L1", "R6", "R7"):
        add(f"power-region-{ref}", "region", ref,
            "Keep the complete switching stage inside its compact authored power region.",
            region=PlacementRegion(x_min_mm=8, y_min_mm=35.5, x_max_mm=26.5, y_max_mm=46))
    return BoardConstraints(outline=BoardOutline(width_mm=90, height_mm=55),
                            placements=placements, placement_constraints=constraints)


def routing_constraints(circuit=None):
    """Explicit geometric prototype rules; no current-capacity certification."""
    profile = RoutingProfile(
        name="landing redesign fine-pitch prototype geometry",
        signal_width_mm=ProfileValue(value=.15, provenance="board_profile", rationale="0.5 mm VSSOP lead escape; fabricator review required"),
        power_width_mm=ProfileValue(value=.25, provenance="board_profile", rationale="Prototype geometry only; copper current and thermal capacity unverified"),
        clearance_mm=ProfileValue(value=.15, provenance="board_profile", rationale="Authored fine-pitch geometry; fabrication process not qualified"),
        grid_mm=ProfileValue(value=.125, provenance="project_default", rationale="Bounded grid fine enough for the pinned VSSOP escape"),
    )
    available = {net.name for net in circuit.nets} if circuit is not None else {"SW_NODE", "FB_REFB"}
    nets = [NetRoutingConstraint(net_name=net, preferred_layer="F.Cu", width_mm=width,
                rationale="Keep the authored switching/feedback connection compact; measured after routing")
            for net, width in (("SW_NODE", .25), ("FB_REFB", .15)) if net in available]
    return RoutingConstraints(profile=profile, nets=nets)


def audit_switching_routes(circuit, board, plan):
    """Fail explicit route budgets while keeping electrical/EMC claims unknown."""
    if plan.circuit_content_hash != circuit.content_hash or plan.source_constraints_hash != board.content_hash:
        raise ValueError("Switching-route audit inputs have different circuit/placement lineage")
    rows = []
    for name, budget in (("SW_NODE", 6.0), ("FB_REFB", 8.0)):
        tracks = [track for track in plan.tracks if track.net_name == name]
        vias = [via for via in plan.vias if via.net_name == name]
        length = sum(track.length_mm for track in tracks)
        passed = bool(tracks) and length <= budget and not vias and all(t.layer == "F.Cu" for t in tracks)
        rows.append({"net": name, "length_mm": round(length, 6), "maximum_length_mm": budget,
                     "via_count": len(vias), "layers": sorted({t.layer for t in tracks}),
                     "status": "PASS" if passed else "FAIL"})
    return {"circuit_fingerprint": circuit.content_hash, "constraints_hash": board.content_hash,
            "routing_plan_fingerprint": plan.content_hash,
            "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows,
            "limits": ["These are authored length/layer limits, not manufacturer-qualified routing rules.",
                       "Input/ground hot-loop area and return-plane impedance are not established by these checks.",
                       "Switching stability, ripple, efficiency, thermal capacity and EMC remain unverified."]}
