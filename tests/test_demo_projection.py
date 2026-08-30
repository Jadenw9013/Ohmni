"""Truthful application projection over existing engineering reports."""

from types import SimpleNamespace

from ohmni.application.demo import _evidence_rows
from ohmni.application.visuals import pcb_svg, schematic_svg
from ohmni.catalog import default_catalog
from ohmni.generation import DesignOrchestrator
from ohmni.generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider


def test_scripted_demo_exposes_real_failure_repair_and_notebook():
    report=DesignOrchestrator(flawed_logger_provider(),default_catalog()).design(GOLDEN_REQUEST,run_eda=False)
    assert report.state.value=="complete"
    assert report.semantic_attempts[0].export_blocked
    assert any(f.rule_id=="PB-PWR-001" for f in report.semantic_attempts[0].findings)
    assert report.repairs and len(report.repairs[0].patch.operations)==2
    assert not report.semantic_attempts[-1].export_blocked
    kinds={event.kind.value for event in report.notebook.events}
    assert {"verification_failed","repair_applied","verification_passed"}<=kinds
    assert report.lessons[0].derived_from_event_ids


def test_evidence_projection_keeps_catalog_strength_truthful():
    rows=_evidence_rows(default_catalog())
    assert rows and {row["component"] for row in rows}=={"BME280"}
    assert all(row["status"]=="CATALOG_REPORTED" for row in rows)
    assert any("absolute maximum" in row["claim"] for row in rows)
    assert all(row["source"] and row["page"] for row in rows)


def test_visuals_are_tied_to_artifact_and_exact_route_geometry(golden):
    artifact=SimpleNamespace(fingerprint=SimpleNamespace(digest="a"*64))
    schematic=schematic_svg(golden,artifact)
    assert "aaaaaaaaaaaa" in schematic and "U3" in schematic and "BME280" in schematic
    board=SimpleNamespace(outline=SimpleNamespace(width_mm=10,height_mm=8),placements=[])
    track=SimpleNamespace(start=SimpleNamespace(x_mm=1,y_mm=1),end=SimpleNamespace(x_mm=9,y_mm=7),layer="F.Cu",width_mm=.25,net_name="SDA")
    plan=SimpleNamespace(tracks=[track],vias=[])
    rendered=pcb_svg(board,plan)
    assert "SDA" in rendered and "F.Cu" in rendered and "<line" in rendered
