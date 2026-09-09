"""Optional personal-project blocks must remain optional in instructional prose."""

from types import SimpleNamespace

import pytest

from ohmni.application.product import RepairReplay, _bring_up, _confidence
from ohmni.application.systems import (
    ComponentGrouping,
    SystemId,
    build_flows,
    build_systems,
    group_components,
)
from ohmni.synthesis import SynthesisBrief, synthesize_a1
from ohmni.verifier import verify


@pytest.mark.parametrize("led", [0, 1])
@pytest.mark.parametrize("header", [False, True])
def test_summaries_and_flows_only_describe_included_blocks(catalog, led, header):
    synthesis = synthesize_a1(SynthesisBrief(status_led_count=led,
                                            include_programming_header=header))
    circuit = synthesis.circuit
    grouping = group_components(circuit, catalog, {})
    systems = {item.system: item for item in build_systems(grouping)}
    flows = {flow.flow_id for flow in build_flows(circuit, catalog, grouping)}
    assert ("status_led" in flows) is bool(led)
    assert ("programming" in flows) is header
    assert ("indicator" in systems[SystemId.COMPUTE].summary) is bool(led)
    if led or header:
        summary = systems[SystemId.IO].summary
        assert ("indicator light" in summary) is bool(led)
        assert ("header" in summary) is header
    else:
        assert SystemId.IO not in systems
    assert all(item.category == catalog.require(item.part_id).category for item in grouping)


def test_legacy_grouping_without_category_uses_neutral_summary():
    grouping = ComponentGrouping(component_ref="J2", part_id="unknown-part", system=SystemId.IO,
                                 anchor=True, basis="legacy grouping")
    summary = build_systems([grouping])[0].summary
    assert "indicator" not in summary and "header" not in summary


def test_a_failed_hand_soldering_preference_is_not_projected_as_a_pass():
    confidence = _confidence(
        SimpleNamespace(results=[], coverage=1.0), None,
        SimpleNamespace(compilation=SimpleNamespace(
            physical_verification=SimpleNamespace(passed=True, findings=[]),
            copper_statistics=SimpleNamespace(track_segment_count=0))),
        SimpleNamespace(passed=True),
        SimpleNamespace(status=SimpleNamespace(value="pass"), findings=[], unconnected_items=[]),
        SimpleNamespace(profile=SimpleNamespace(display_name="Synthetic test profile")),
        SimpleNamespace(pricing_coverage=0),
        SimpleNamespace(hand_solder_requirement_satisfied=False,
                        risks=[SimpleNamespace(difficulty="reflow_recommended")],
                        limitations=["The sensor requires reflow equipment."]),
    )
    item = next(line for line in confidence.not_verified if line.label == "Assembly by hand")
    assert item.status == "NEEDS_REVIEW"
    assert "beyond a soldering iron" in item.detail and "reflow equipment" in item.detail


def test_bring_up_does_not_predict_an_open_circuit_between_populated_supply_rails(golden, catalog):
    design = SimpleNamespace(semantic_attempts=[verify(golden, catalog)])
    steps = _bring_up(design, golden, catalog, RepairReplay(happened=False, headline="No repair"))
    assert "unintended short" in steps[0].prediction
    assert "resistance reading" in steps[0].basis
    assert "instantly" not in steps[0].basis
