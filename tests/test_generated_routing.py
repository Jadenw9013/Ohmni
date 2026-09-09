"""Real PCB acceptance for generated family placements and physical copper.

Each case retains all transformation reports in its pytest temporary directory.
The budget bounds work; it does not replace connectivity, KiCad, or profile gates.
"""

import hashlib
import json
import math
import re
from collections import Counter
from time import monotonic

import pytest

from ohmni.adapters.tools import find_kicad_cli
from ohmni.eda.kicad import KiCadCliAdapter, KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.eda.pcb_models import DrcStatus
from ohmni.manufacturing import prototype_profile, verify_manufacturing
from ohmni.physical.footprints import footprint
from ohmni.physical.placement import generate_placement
from ohmni.routing.router import DeterministicRouter
from ohmni.routing.verifier import verify_routing
from ohmni.synthesis import ArchetypeId, SpiPeripheralSlot, SynthesisBrief, synthesize
from ohmni.verifier import verify

pytestmark = [
    pytest.mark.slow_integration,
    pytest.mark.kicad,
    pytest.mark.skipif(find_kicad_cli() is None, reason="KiCad CLI unavailable"),
]

ROUTING_BUDGET_SECONDS = 180


def _save(directory, name, model):
    (directory / name).write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _physical_connections(pcb, board):
    """Count physical copper contacts directly from compiled pad bindings.

    This intentionally does not use the router's terminal enumeration: dropping
    a same-number switch land there must change the acceptance result here.
    """
    positions = {place.component_ref: place for place in board.placements}
    definitions = {item.component_ref: footprint(item.footprint_id)
                   for item in pcb.compilation.footprint_bindings}
    locations = {}
    for binding in pcb.compilation.pad_bindings:
        if binding.net_name is None:
            continue
        place = positions[binding.component_ref]
        angle = math.radians(place.rotation_deg)
        for pad in definitions[binding.component_ref].pads:
            if pad.number != binding.pad_number:
                continue
            location = (round(place.x_mm + pad.x_mm*math.cos(angle) - pad.y_mm*math.sin(angle), 6),
                        round(place.y_mm + pad.x_mm*math.sin(angle) + pad.y_mm*math.cos(angle), 6))
            locations.setdefault(binding.net_name, set()).add(location)
    return sum(max(0, len(contacts)-1) for contacts in locations.values())


@pytest.mark.parametrize("case,brief", [
    pytest.param("a1-default", SynthesisBrief(), id="a1-default"),
    pytest.param("a2-minimum", SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER, sensors=(), status_led_count=1,
        button_count=1, include_programming_header=False,
    ), id="a2-minimum"),
    pytest.param("a3-maximum", SynthesisBrief(
        archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
        spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),) * 2,
        status_led_count=1, include_programming_header=True,
    ), id="a3-maximum"),
])
def test_generated_family_copper_closes_real_drc_and_manufacturing(tmp_path, catalog, case, brief):
    _save(tmp_path, "brief.json", brief)
    result = synthesize(brief, catalog)
    _save(tmp_path, "synthesis.json", result)
    assert result.accepted, result.refusal
    assert result.brief_fingerprint == brief.fingerprint
    semantic = verify(result.circuit, catalog, result.requirements)
    _save(tmp_path, "semantic.json", semantic)
    assert semantic.coverage == 1 and not semantic.export_blocked, semantic.model_dump_json()

    generated = generate_placement(result.circuit, result.placement_request, catalog)
    _save(tmp_path, "placement.json", generated)
    board = generated.board
    assert generated.request_fingerprint == result.placement_request.content_hash
    assert generated.circuit_content_hash == result.circuit.content_hash
    assert generated.metrics.component_count == len(result.circuit.components)
    assert generated.metrics.board_area_mm2 == board.outline.width_mm * board.outline.height_mm
    schematic = KiCadSchematicCompiler(catalog).compile(result.circuit, tmp_path / "board.kicad_sch")
    compiler = KiCadPcbCompiler(catalog)
    placed = compiler.compile(result.circuit, schematic, board, tmp_path / "board.placed.kicad_pcb")
    _save(tmp_path, "placed-pcb.json", placed)
    assert placed.compilation.physical_verification.passed
    expected_constraints = {item.constraint_id for item in board.placement_constraints}
    checked_constraints = {item.constraint_id for item in placed.compilation.physical_verification.findings
                           if item.constraint_id is not None}
    assert expected_constraints == checked_constraints

    started = monotonic()
    plan = DeterministicRouter().route(result.circuit, placed, board,
                                       time_budget_seconds=ROUTING_BUDGET_SECONDS)
    route_elapsed_seconds = monotonic() - started
    _save(tmp_path, "routing.json", plan)
    independent = verify_routing(result.circuit, placed, board, plan)
    _save(tmp_path, "routing-verification.json", independent)
    assert not plan.failures, f"{case}: {plan.model_dump_json()}; diagnostics: {tmp_path}"
    assert independent.passed, independent.model_dump_json()
    assert plan.statistics.required_connections == _physical_connections(placed, board)
    assert plan.statistics.routed_net_count == len(result.circuit.nets)
    assert plan.statistics.unresolved_net_count == 0
    assert sum(len(net.paths) for net in plan.routed_nets) == plan.statistics.required_connections
    assert plan.circuit_content_hash == result.circuit.content_hash
    assert plan.source_pcb_fingerprint == placed.fingerprint.digest
    assert plan.source_constraints_hash == board.content_hash

    # The minimum A2 contains one four-land/two-terminal switch. Both separate
    # legs of each electrical terminal must be in the actual routed graph.
    if case == "a2-minimum":
        assert plan.statistics.required_connections == 35
        button = next(component for component in result.circuit.components
                      if component.part_id == "GENERIC_MOMENTARY_BUTTON")
        terminals = {name for net in plan.routed_nets for name in net.terminal_pads}
        assert {f"{button.ref}.{pin}{suffix}" for pin in ("1", "2") for suffix in ("", "#2")} <= terminals

    routed = compiler.compile(result.circuit, schematic, board, tmp_path / "board.kicad_pcb", plan)
    _save(tmp_path, "routed-pcb.json", routed)
    statistics = routed.compilation.copper_statistics
    pcb_text = routed.path.read_text(encoding="utf-8")
    assert routed.lineage_is_current
    assert routed.fingerprint.digest == hashlib.sha256(routed.path.read_bytes()).hexdigest()
    assert routed.source_placed_pcb_fingerprint == placed.fingerprint
    assert routed.schematic_fingerprint == schematic.fingerprint
    assert routed.routing_plan_fingerprint == independent.plan_fingerprint == plan.content_hash
    assert statistics.track_segment_count == len(re.findall(r"^  \(segment ", pcb_text, re.MULTILINE)) > 0
    assert statistics.via_count == len(re.findall(r"^  \(via ", pcb_text, re.MULTILINE))
    assert statistics.modeled_track_segment_count == len(plan.tracks)
    assert statistics.modeled_layer_transition_count == len(plan.vias)
    assert statistics.modeled_layer_transition_count == (
        statistics.via_count + statistics.coalesced_layer_transition_count
        + statistics.plated_through_hole_transition_count
    )
    # Read endpoints from the serialized KiCad artifact, not the placement
    # estimate or the pre-rounding routing plan.
    segments = re.findall(r"^  \(segment \(start ([^ ]+) ([^)]+)\) \(end ([^ ]+) ([^)]+)\)",
                          pcb_text, re.MULTILINE)
    actual_length = round(sum(math.hypot(float(x2)-float(x1), float(y2)-float(y1))
                              for x1,y1,x2,y2 in segments), 6)
    assert statistics.total_track_length_mm == actual_length > 0

    drc = KiCadCliAdapter().run_drc(routed)
    _save(tmp_path, "drc.json", drc)
    assert drc.status is DrcStatus.PASS, drc.model_dump_json()
    assert not drc.findings and not drc.unconnected_items
    assert drc.pcb_fingerprint == routed.fingerprint
    assert drc.report_path and drc.report_path.is_file()
    profile = prototype_profile()
    manufacturing = verify_manufacturing(routed, board, plan, profile)
    _save(tmp_path, "manufacturing.json", manufacturing)
    assert manufacturing.passed, manufacturing.model_dump_json()
    assert manufacturing.routed_pcb_fingerprint == routed.fingerprint.digest
    assert manufacturing.routing_plan_fingerprint == plan.content_hash
    assert manufacturing.profile.content_hash == profile.content_hash

    summary = {
        "case": case, "brief_fingerprint": brief.fingerprint,
        "placement_request_fingerprint": generated.request_fingerprint,
        "circuit_content_hash": result.circuit.content_hash, "board_constraints_hash": board.content_hash,
        "routing_plan_fingerprint": plan.content_hash, "routed_pcb_fingerprint": routed.fingerprint.digest,
        "routing_budget_seconds": ROUTING_BUDGET_SECONDS, "routing_elapsed_seconds": route_elapsed_seconds,
        "required_connections": plan.statistics.required_connections,
        "actual_copper": statistics.model_dump(mode="json"), "kicad_version": drc.kicad_version,
        "drc_status": drc.status.value, "drc_findings": len(drc.findings),
        "drc_unconnected": len(drc.unconnected_items),
        "drc_ignored_checks": drc.ignored_checks,
        "manufacturing_profile": profile.model_dump(mode="json"),
        "semantic_findings": dict(Counter(finding.severity.value for finding in semantic.findings)),
        "limitations": list(generated.limitations),
    }
    (tmp_path / "acceptance-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{case}: {plan.statistics.required_connections} connections; "
          f"{statistics.track_segment_count} emitted segments; {statistics.via_count} emitted vias; "
          f"{statistics.total_track_length_mm} mm; route {route_elapsed_seconds:.2f}s; "
          f"KiCad {drc.kicad_version} DRC 0 violations / 0 unconnected; diagnostics={tmp_path}")
