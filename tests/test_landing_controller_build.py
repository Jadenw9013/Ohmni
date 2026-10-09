"""Independent failure and source-preservation checks for controller authoring."""
import hashlib

import pytest

from tools.landing_controller.schematic import ControllerSchematicCompiler


def test_large_symbol_pin_endpoints_never_join_other_component_labels(tmp_path):
    from tools.landing_controller.design import build_design

    design = build_design()
    artifact = ControllerSchematicCompiler(design.catalog).compile(
        design.circuit, tmp_path / "controller.kicad_sch",
    )
    coordinates = {}
    for binding in artifact.compilation.symbol_bindings:
        for pin in binding.pins:
            key = (round(pin.x_mm, 6), round(pin.y_mm, 6))
            assert key not in coordinates, (key, coordinates.get(key), pin.component_ref)
            coordinates[key] = (pin.component_ref, pin.circuit_pin)
    assert sum(ref == "U1" for ref, _ in coordinates.values()) == 100
    assert artifact.is_current


def test_pipeline_rejects_failed_topology_before_emitting_pcb(tmp_path, monkeypatch):
    from tools.landing_controller import build, checks

    reference = build.ROOT / "apps/web/reference-board.json"
    original = hashlib.sha256(reference.read_bytes()).hexdigest()
    monkeypatch.setattr(checks, "check_design", lambda *_: {"failed_checks": 1})
    monkeypatch.setattr(build, "_tool_version", lambda *_: {"status": "NOT_RUN"})
    output = tmp_path / "failed"
    result = build.generate(output, captured_on="2026-10-09", native=False)
    assert result["status"] == "TOPOLOGY_CHECKS_FAILED"
    assert not list(output.glob("*.kicad_pcb"))
    assert not (output / "candidate-board.json").exists()
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == original


def test_previous_authoring_evidence_is_not_overwritten(tmp_path):
    from tools.landing_controller.build import generate

    evidence = tmp_path / "report.json"
    evidence.write_text("prior evidence")
    with pytest.raises(ValueError, match="empty output directory"):
        generate(tmp_path, captured_on="2026-10-09", native=False)
    assert evidence.read_text() == "prior evidence"
