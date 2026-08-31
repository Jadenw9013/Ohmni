"""Truthful application projection over existing engineering reports."""

from types import SimpleNamespace

import pytest

from ohmni.application.demo import DemoPipeline, _evidence_rows, project_demo_report
from ohmni.application.visuals import pcb_svg, schematic_svg
from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadSchematicCompiler
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
    board=SimpleNamespace(outline=SimpleNamespace(width_mm=10,height_mm=8),placements=[])
    track=SimpleNamespace(start=SimpleNamespace(x_mm=1,y_mm=1),end=SimpleNamespace(x_mm=9,y_mm=7),layer="F.Cu",width_mm=.25,net_name="SDA")
    plan=SimpleNamespace(tracks=[track],vias=[])
    rendered=pcb_svg(board,plan)
    assert "SDA" in rendered and "F.Cu" in rendered and "<line" in rendered
