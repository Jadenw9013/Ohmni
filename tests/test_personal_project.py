"""The editable A1 contract, diagnostics, and real artifact boundary."""

from itertools import product
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ohmni.application.diagnostics import evaluate_sensor_exercise
from ohmni.application.projects import (
    ProjectPipeline,
    ProjectRefusalError,
    prepare_project,
    preview_project,
)
from ohmni.catalog import default_catalog
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.placement import generate_placement
from ohmni.physical.sensor_layout import sensor_board_constraints
from ohmni.synthesis import I2cSensorSlot, SynthesisBrief, synthesize_a1
from ohmni.verifier import verify


@pytest.mark.parametrize("led,header,address", list(product((0, 1), (False, True), (0x76, 0x77))))
def test_every_offered_configuration_has_matching_geometry_and_checked_topology(tmp_path, led, header, address):
    brief = SynthesisBrief(status_led_count=led, include_programming_header=header,
                           sensors=(I2cSensorSlot(part_id="BME280", address=address),))
    circuit, requirements = prepare_project(brief)
    catalog = default_catalog()
    report = verify(circuit, catalog, requirements.requirements)
    assert report.coverage == 1 and not report.export_blocked
    board = generate_placement(circuit, synthesize_a1(brief).placement_request, catalog).board
    assert {p.component_ref for p in board.placements} == {p.ref for p in circuit.components}
    assert all(p.component_ref in {part.ref for part in circuit.components}
               for p in board.placement_constraints)
    schematic = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "project.kicad_sch")
    pcb = KiCadPcbCompiler(catalog).compile(circuit, schematic, board, tmp_path / "project.kicad_pcb")
    assert pcb.compilation.physical_verification.passed
    assert pcb.circuit_content_hash == circuit.content_hash
    assert (circuit.component("D1") is not None) == bool(led)
    assert (circuit.component("J2") is not None) == header
    assert circuit.component("U3").selected_i2c_address == address


def test_preview_preserves_explicit_choices_and_names_missing_programming_path():
    brief = SynthesisBrief(project_name="Desk monitor", status_led_count=0,
                           include_programming_header=False,
                           sensors=(I2cSensorSlot(part_id="BME280", address=0x77),))
    preview = preview_project(brief)
    assert preview.project_name == "Desk monitor"
    explicit = {line.field: line.value for line in preview.asked_for}
    assert explicit["status_led_count"] == "0"
    assert explicit["include_programming_header"] == "No"
    assert explicit["sensors.0.address"] == "0x77"
    assert any("no supplied programming connector" in line.value for line in preview.assumed)


@pytest.mark.parametrize("updates", [{"max_board_layers": 1}, {"logic_voltage_v": 5},
                                     {"status_led_count": 2}])
def test_unsupported_confirmed_choices_are_refused_before_eda(updates):
    with pytest.raises(ProjectRefusalError):
        preview_project(SynthesisBrief(**updates))


def test_nonfinite_brief_values_never_enter_fingerprints():
    with pytest.raises(ValidationError):
        SynthesisBrief(budget_usd=float("inf"))


@pytest.mark.parametrize("status", ["fail", "error"])
def test_failed_or_unavailable_physical_check_stops_before_routing(tmp_path, monkeypatch, status):
    from ohmni.application import demo
    from ohmni.physical.models import PhysicalFinding, PhysicalVerificationReport

    circuit, _ = prepare_project(SynthesisBrief())
    physical = PhysicalVerificationReport(findings=[PhysicalFinding(
        rule_id="PB-PHY-004", status=status, description="Required proximity was not established",
    )])
    placed = SimpleNamespace(compilation=SimpleNamespace(physical_verification=physical))
    monkeypatch.setattr(demo, "KiCadPcbCompiler", lambda catalog: SimpleNamespace(compile=lambda *args: placed))

    def routing_must_not_start():
        raise AssertionError("routing started after a failed physical check")

    monkeypatch.setattr(demo, "DeterministicRouter", routing_must_not_start)
    with pytest.raises(RuntimeError, match="physical placement"):
        ProjectPipeline().finish_design(tmp_path, "sensor", SimpleNamespace(final_circuit=circuit, artifact=None),
                                        default_catalog(), sensor_board_constraints(circuit), scripted=False)


@pytest.mark.parametrize("choice,count,correct", [("leave_5v", 2, False), ("move_vdd", 1, False), ("move_both", 0, True)])
def test_exercise_reports_the_actual_remaining_supply_violations(choice, count, correct):
    result = evaluate_sensor_exercise(choice)
    assert result["correct"] is correct
    assert len(result["before"]["findings"]) == 2
    assert len(result["after"]["findings"]) == count
    assert result["after"]["outcome"] == ("pass" if correct else "fail")
    assert all(e["status"] != "DATASHEET_SUPPORTED" for e in result["evidence"])
    if choice == "leave_5v":
        assert result["before"]["circuit_hash"] == result["after"]["circuit_hash"]
    else:
        assert result["before"]["circuit_hash"] != result["after"]["circuit_hash"]


def test_exercise_rejects_unknown_actions_and_does_not_mutate_saved_intent():
    brief = SynthesisBrief()
    before, _ = prepare_project(brief)
    with pytest.raises(ValueError):
        evaluate_sensor_exercise("pretend_pass")
    evaluate_sensor_exercise("move_vdd")
    after, _ = prepare_project(brief)
    assert before.model_dump() == after.model_dump()


@pytest.mark.slow_integration
@pytest.mark.parametrize("led,header,address", [(1, True, 0x76), (0, False, 0x77)])
def test_personal_project_reaches_real_kicad_release_without_scripted_provider(tmp_path, monkeypatch, led, header, address):
    from ohmni.application import demo

    def forbidden(*args, **kwargs):
        raise AssertionError("a personal project must not replay the fixture")

    monkeypatch.setattr(demo, "flawed_logger_provider", forbidden)
    monkeypatch.setattr(demo, "golden_board_constraints", forbidden)
    report = ProjectPipeline().run(tmp_path, SynthesisBrief(
        project_name="Personal project", status_led_count=led,
        include_programming_header=header,
        sensors=(I2cSensorSlot(part_id="BME280", address=address),),
    ))
    assert report.mode == "bounded_synthesis"
    assert report.project["name"] == "Personal project"
    assert report.pcb["violations"] == report.pcb["unrouted"] == 0
    assert report.release["current"]
    assert report.experience.repair.happened is False
    assert report.failure_and_repair["status"] == "NOT_NEEDED"
    assert (tmp_path / "confirmed-brief.json").is_file()
    assert (tmp_path / "circuit.json").is_file()
    assert all(Path(tmp_path / "fabrication" / item["relative_path"]).is_file()
               for item in report.release["files"])
