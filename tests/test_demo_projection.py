"""Truthful application projection over existing engineering reports."""

from types import SimpleNamespace

import pytest

from ohmni.application import demo
from ohmni.application.demo import (
    DEMO_REQUEST,
    DemoPipeline,
    _evidence_rows,
    project_demo_report,
)
from ohmni.application.visuals import pcb_svg, schematic_svg
from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadSchematicCompiler
from ohmni.eda.models import ArtifactFingerprint
from ohmni.eda.pcb_models import CompiledTrackGeometry, CompiledViaGeometry
from ohmni.generation import DesignOrchestrator
from ohmni.generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider


def test_scripted_demo_exposes_real_failure_repair_and_notebook(tmp_path):
    report=DesignOrchestrator(flawed_logger_provider(),default_catalog()).design(GOLDEN_REQUEST,run_eda=False)
    assert report.state.value=="complete"
    assert report.semantic_attempts[0].export_blocked
    assert any(f.rule_id=="PB-PWR-001" for f in report.semantic_attempts[0].findings)
    assert report.repairs and len(report.repairs[0].patch.operations)==2
    assert not report.semantic_attempts[-1].export_blocked
    kinds={event.kind.value for event in report.notebook.events}
    assert {"verification_failed","repair_applied","verification_passed"}<=kinds
    assert report.lessons[0].derived_from_event_ids
    unsupported=tmp_path/"unsupported"
    with pytest.raises(ValueError,match="displayed deterministic"):
        DemoPipeline().run(unsupported,"Build a motor controller with a $30 budget")
    assert not unsupported.exists()
    contradictory_request="Build a motor controller with a $30 budget"
    contradictory=DesignOrchestrator(flawed_logger_provider(),default_catalog()).design(
        contradictory_request,run_eda=False,
    )
    assert {
        statement.source_text
        for statement in contradictory.requirements.provenance
        if statement.origin.value=="explicit"
    }=={contradictory_request}
    with pytest.raises(ValueError,match="displayed deterministic"):
        project_demo_report(request=GOLDEN_REQUEST,design=contradictory)


def test_evidence_projection_keeps_catalog_strength_truthful():
    rows=_evidence_rows(default_catalog())
    assert rows and {row["component"] for row in rows}=={"BME280"}
    assert all(row["status"]=="CATALOG_REPORTED" for row in rows)
    assert any("absolute maximum" in row["claim"] for row in rows)
    assert all(row["source"] and row["page"] for row in rows)


def test_visuals_are_tied_to_compiled_artifact_and_exact_route_geometry(tmp_path,golden,catalog):
    artifact=KiCadSchematicCompiler(catalog).compile(golden,tmp_path/"golden.kicad_sch")
    schematic=schematic_svg(artifact)
    assert artifact.fingerprint.digest in schematic and "U3" in schematic and "BME280" in schematic
    assert {binding.component_ref for binding in artifact.compilation.symbol_bindings}=={item.ref for item in golden.components}
    for binding in artifact.compilation.symbol_bindings:
        assert f'data-component-ref="{binding.component_ref}"' in schematic
        for pin in binding.pins:
            assert f'data-endpoint-uuid="{pin.endpoint_uuid}"' in schematic
    for net in golden.nets:
        assert f'data-net="{net.name}"' in schematic
    for driver in artifact.compilation.driver_bindings:
        assert f'data-compiler-driver="{driver.reference}"' in schematic
    mismatched=artifact.model_copy(deep=True)
    mismatched.compilation.source_artifact_fingerprint.digest="b"*64
    with pytest.raises(ValueError,match="fingerprint"):
        schematic_svg(mismatched)
    pcb_fingerprint=ArtifactFingerprint(digest="c"*64);routing_fingerprint="d"*64
    board=SimpleNamespace(content_hash="e"*64,outline=SimpleNamespace(width_mm=10,height_mm=8),placements=[])
    track=CompiledTrackGeometry(source_segment_id="route-track",emitted_uuid="track-uuid",net_name="SDA",net_number=1,layer="F.Cu",start_x_mm=1,start_y_mm=1,end_x_mm=9,end_y_mm=7,width_mm=.25)
    via=CompiledViaGeometry(source_via_id="route-via",emitted_uuid="via-uuid",net_name="SDA",net_number=1,x_mm=9,y_mm=7,diameter_mm=.8,drill_mm=.4)
    compilation=SimpleNamespace(artifact_fingerprint=pcb_fingerprint,constraints_hash=board.content_hash,routing_plan_fingerprint=routing_fingerprint,emitted_tracks=[track],emitted_vias=[via])
    pcb=SimpleNamespace(fingerprint=pcb_fingerprint,constraints_hash=board.content_hash,routing_plan_fingerprint=routing_fingerprint,compilation=compilation)
    rendered=pcb_svg(board,pcb)
    assert "SDA" in rendered and "F.Cu" in rendered and 'data-track-uuid="track-uuid"' in rendered
    assert 'data-via-uuid="via-uuid"' in rendered and pcb_fingerprint.digest in rendered
    compilation.artifact_fingerprint=ArtifactFingerprint(digest="f"*64)
    with pytest.raises(ValueError,match="fingerprint"):
        pcb_svg(board,pcb)


class _StopBeforeEngineering(RuntimeError):
    """Marks which branch reached the orchestrator without running one."""


def test_a_provider_adds_the_free_text_branch_without_diverting_the_fixture(tmp_path,monkeypatch):
    """Who proposes a circuit is decided by the request, not by the configuration.

    The scripted fixture must keep using its scripted responses even when a real
    provider is available -- it is the regression and offline path -- and free
    text must reach the configured provider rather than the fixture.
    """
    providers=[]
    class StopOrchestrator:
        def __init__(self,provider,catalog,**kwargs):providers.append(provider)
        def design(self,request,**kwargs):raise _StopBeforeEngineering(request)
    monkeypatch.setattr(demo,"DesignOrchestrator",StopOrchestrator)
    configured=flawed_logger_provider()
    pipeline=DemoPipeline(provider=configured)
    with pytest.raises(_StopBeforeEngineering,match="ESP32 environmental logger"):
        pipeline.run(tmp_path/"scripted",DEMO_REQUEST)
    with pytest.raises(_StopBeforeEngineering,match="motor controller"):
        pipeline.run(tmp_path/"free","Build a motor controller with a $30 budget")
    assert providers[0] is not configured and providers[1] is configured
    unsupported=tmp_path/"unsupported"
    with pytest.raises(ValueError,match="displayed deterministic"):
        DemoPipeline().run(unsupported,"Build a motor controller with a $30 budget")
    assert not unsupported.exists()
    with pytest.raises(ValueError,match="text describing what to build"):
        pipeline.run_proposed(tmp_path/"blank","   ")


def test_a_proposed_design_is_placed_from_its_own_circuit_and_labelled_as_proposed(tmp_path,golden):
    """The proposed circuit decides the board, and the report says a model proposed it."""
    erc=SimpleNamespace(status=SimpleNamespace(value="pass"),tool_status=None,findings=[],
                        model_dump_json=lambda indent=None:"{}")
    design=SimpleNamespace(final_circuit=golden,artifact=SimpleNamespace(),erc=erc,
                           semantic_attempts=[SimpleNamespace()],repairs=[],issues=[])
    captured={}
    class ProposingOrchestrator:
        def __init__(self,provider,catalog,**kwargs):pass
        def design(self,request,**kwargs):return design
    class Pipeline(DemoPipeline):
        def finish_design(self,destination,request,supplied,catalog,board,**kwargs):
            captured.update(destination=destination,request=request,design=supplied,
                            board=board,**kwargs)
            return "projected"
    pipeline=Pipeline(provider=flawed_logger_provider())
    original=demo.DesignOrchestrator
    demo.DesignOrchestrator=ProposingOrchestrator
    try:
        assert pipeline.run(tmp_path/"proposed","Build a USB environmental logger")=="projected"
    finally:
        demo.DesignOrchestrator=original
    assert captured["design"] is design
    assert captured["scripted"] is False and captured["mode"]==demo.MODEL_PROPOSED_MODE
    assert {placement.component_ref for placement in captured["board"].placements}=={
        component.ref for component in golden.components}
    assert (tmp_path/"proposed"/"erc-report.json").read_text(encoding="utf-8")=="{}"
    label,limitation=demo.MODE_PRESENTATION[demo.MODEL_PROPOSED_MODE]
    assert "Model-proposed" in label and "deterministic checks" in limitation


def test_the_brief_preview_answers_free_text_only_through_a_provider():
    """The Agree stage exists for a proposed design too, and never fakes one.

    The scripted request stays scripted even with a provider configured: it is
    the regression fixture, so a model call would quietly make it something else.
    """
    from ohmni.adapters.fakes import RecordingLlmProvider
    from ohmni.application.demo import preview_brief

    free_text="Build a USB-powered CO2 logger with a status light"
    with pytest.raises(ValueError,match="displayed deterministic"):
        preview_brief(free_text)
    provider=RecordingLlmProvider()
    provider.queue({"project_name":"CO2 logger","description":free_text,
                    "max_input_voltage_v":5.25,"target_logic_voltage_v":3.3,
                    "assumptions":["USB-C is used as a 5 V sink without Power Delivery"]})
    brief=preview_brief(free_text,provider=provider)
    assert not provider._queue and len(provider.calls)==1
    assert any(free_text in line.value or line.value=="CO2 logger" for line in brief.asked_for)
    scripted=RecordingLlmProvider()
    assert preview_brief(DEMO_REQUEST,provider=scripted).asked_for
    assert not scripted.calls
    with pytest.raises(ValueError,match="text describing what to build"):
        preview_brief("   ",provider=RecordingLlmProvider())
