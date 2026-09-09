"""Personal builds use generated placement and bounded, truthful copper projection."""

import json
from types import SimpleNamespace

import pytest

from ohmni.application.demo import DemoPipeline, RoutingIncompleteError, _pcb_quality_metrics
from ohmni.application.projects import ProjectPipeline
from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadSchematicCompiler
from ohmni.eda.models import ArtifactFingerprint, ErcReport
from ohmni.eda.pcb_models import CompiledTrackGeometry, CompiledViaGeometry
from ohmni.physical.models import PlacementRequest
from ohmni.physical.placement import GeneratedPlacement, generate_placement
from ohmni.routing.models import RoutingPlan
from ohmni.routing.router import DeterministicRouter
from ohmni.synthesis import SynthesisBrief, synthesize_a1


def test_personal_pipeline_passes_generated_board_and_persists_placement_lineage(tmp_path, monkeypatch):
    from ohmni.application import projects

    brief = SynthesisBrief(status_led_count=0, include_programming_header=False)
    expected = synthesize_a1(brief)
    captured = []

    class CapturePipeline(ProjectPipeline):
        def finish_design(self, destination, request, design, catalog, board, *, scripted,
                          placement_request=None,confirmed_brief=None):
            assert scripted is False
            assert placement_request==expected.placement_request and confirmed_brief==brief
            captured.append(board)
            assert design.final_circuit.content_hash == expected.circuit.content_hash
            return SimpleNamespace(project={}, pcb={})

    # This test exercises application handoff, with ERC explicitly stubbed.
    def erc(artifact):
        return ErcReport(status="pass", tool_status="ok", run_id="test-stub",
                         artifact_fingerprint=artifact.fingerprint)

    monkeypatch.setattr(projects, "KiCadCliAdapter", lambda: SimpleNamespace(run_erc=erc))
    report = CapturePipeline().run(tmp_path, brief)
    request = PlacementRequest.model_validate_json((tmp_path / "placement-request.json").read_text())
    placement = GeneratedPlacement.model_validate_json((tmp_path / "placement.json").read_text())
    assert request.content_hash == expected.placement_request.content_hash == placement.request_fingerprint
    assert placement.circuit_content_hash == expected.circuit.content_hash
    assert placement.board.content_hash == captured[0].content_hash
    assert report.project["placement_request_fingerprint"] == request.content_hash
    assert report.pcb["placement"]["constraints_hash"] == placement.board.content_hash
    assert report.pcb["placement"]["metrics"]["board_area_mm2"] == 7000


@pytest.mark.parametrize("scripted", [False, True])
def test_product_router_has_finite_budget_and_incomplete_runs_never_publish(tmp_path, monkeypatch, scripted):
    from ohmni.application import demo

    catalog = default_catalog()
    result = synthesize_a1(SynthesisBrief())
    board = generate_placement(result.circuit, result.placement_request, catalog).board
    schematic = KiCadSchematicCompiler(catalog).compile(result.circuit, tmp_path / "golden.kicad_sch")
    received_budgets = []

    class ImmediateDeadlineRouter:
        def route(self, circuit, placed, constraints, *, time_budget_seconds):
            received_budgets.append(time_budget_seconds)
            return DeterministicRouter().route(circuit, placed, constraints, time_budget_seconds=0)

    monkeypatch.setattr(demo, "DeterministicRouter", ImmediateDeadlineRouter)
    events = []
    pipeline = DemoPipeline(progress=events.append)
    with pytest.raises(RoutingIncompleteError, match="Routing incomplete.*wall-clock budget exhausted"):
        pipeline.finish_design(tmp_path, "sensor", SimpleNamespace(final_circuit=result.circuit, artifact=schematic),
                               catalog, board, scripted=scripted)
    assert received_budgets == [180]
    plan = RoutingPlan.model_validate_json((tmp_path / "routing-plan.json").read_text())
    assert plan.failures and all(failure.reason.value == "routing_incomplete" for failure in plan.failures)
    assert plan.source_constraints_hash == board.content_hash
    assert plan.circuit_content_hash == result.circuit.content_hash
    checks = json.loads((tmp_path / "routing-verification.json").read_text())
    assert any(finding["status"] == "fail" for finding in checks["findings"])
    assert events[-1].status == "FAIL" and events[-1].stage == "routing"
    assert not (tmp_path / "golden.kicad_pcb").exists()
    assert not (tmp_path / "fabrication").exists()


@pytest.mark.parametrize("budget", [None, float("inf"), float("nan"), -1, True, "180"])
def test_product_entry_rejects_unbounded_or_invalid_routing_budget(budget):
    with pytest.raises(ValueError, match="finite, nonnegative"):
        DemoPipeline().finish_design(None, None, None, None, None, routing_time_budget_seconds=budget)


def _quality_fixture():
    fingerprint = ArtifactFingerprint(digest="a" * 64)
    board = SimpleNamespace(content_hash="b" * 64, outline=SimpleNamespace(width_mm=100, height_mm=70))
    track = CompiledTrackGeometry(source_segment_id="track", emitted_uuid="track-uuid", net_name="SDA",
                                  net_number=1, layer="F.Cu", start_x_mm=1, start_y_mm=1,
                                  end_x_mm=4, end_y_mm=5, width_mm=.25)
    via = CompiledViaGeometry(source_via_id="via", emitted_uuid="via-uuid", net_name="SDA", net_number=1,
                              x_mm=4, y_mm=5, diameter_mm=.8, drill_mm=.4)
    statistics = SimpleNamespace(track_segment_count=1, via_count=1, total_track_length_mm=5,
                                 modeled_layer_transition_count=7, coalesced_layer_transition_count=6)
    compilation = SimpleNamespace(artifact_fingerprint=fingerprint, constraints_hash=board.content_hash,
                                   emitted_tracks=[track], emitted_vias=[via], copper_statistics=statistics)
    return board, SimpleNamespace(fingerprint=fingerprint, constraints_hash=board.content_hash, compilation=compilation)


def test_quality_metrics_use_emitted_copper_not_raw_transition_intent():
    board, artifact = _quality_fixture()
    metrics = _pcb_quality_metrics(board, artifact)
    assert metrics["board_area_mm2"] == 7000
    assert metrics["track_length_mm"] == 5
    assert metrics["via_count"] == 1  # Seven modeled transitions coalesced to one drilled via.
    assert metrics["track_segment_count"] == 1
    assert metrics["source_pcb_fingerprint"] == artifact.fingerprint.digest
    assert metrics["constraints_hash"] == board.content_hash
    assert "optimal" in metrics["limitation"]


@pytest.mark.parametrize("change", ["length", "vias", "fingerprint", "constraints"])
def test_quality_metrics_reject_mismatched_report_geometry(change):
    board, artifact = _quality_fixture()
    if change == "length":
        artifact.compilation.copper_statistics.total_track_length_mm = 99
    elif change == "vias":
        artifact.compilation.copper_statistics.via_count = 7
    elif change == "fingerprint":
        artifact.compilation.artifact_fingerprint = ArtifactFingerprint(digest="c" * 64)
    else:
        artifact.constraints_hash = "d" * 64
    with pytest.raises(ValueError, match="emitted artifact"):
        _pcb_quality_metrics(board, artifact)
