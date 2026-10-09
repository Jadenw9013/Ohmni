"""The scoped power marker must be reviewable, gated, and bound to final bytes."""

import copy
import hashlib

import pytest

from ohmni.domain import EventKind
from ohmni.eda.kicad import KiCadSchematicCompiler
from ohmni.eda.kicad.component_asset_parser import parse
from tools.landing_redesign.checks import check_design
from tools.landing_redesign.design import build_design
from tools.landing_redesign.schematic import DRIVER_ROLE, LIBRARY_ID, build_schematic


def _property(node, name):
    return next(child.atoms()[1] for child in node.children("property") if child.atoms()[0] == name)


@pytest.mark.parametrize("extension", [False, True])
def test_derived_marker_preserves_all_real_bindings_and_updates_final_lineage(tmp_path, extension):
    design = build_design(extension)
    before = design.circuit.model_dump(mode="json")
    report = check_design(design.circuit, design.catalog, include_i2c_extension=extension)
    base = KiCadSchematicCompiler(design.catalog).compile(design.circuit, tmp_path / "base.kicad_sch")
    result = build_schematic(design, tmp_path / "derived.kicad_sch", report)
    assert design.circuit.model_dump(mode="json") == before
    assert result.compilation.symbol_bindings == base.compilation.symbol_bindings
    assert result.compilation.net_mapping == base.compilation.net_mapping
    assert result.circuit_content_hash == design.circuit.content_hash
    assert result.compilation.circuit_content_hash == design.circuit.content_hash
    assert result.is_current
    assert result.current_fingerprint() == result.fingerprint == result.compilation.source_artifact_fingerprint
    assert result.fingerprint != base.fingerprint
    assert result.fingerprint.digest == hashlib.sha256(result.path.read_bytes()).hexdigest()
    derived = [item for item in result.compilation.driver_bindings if item.role == DRIVER_ROLE]
    assert len(derived) == 1 and derived[0].net_name == "3V3"
    assert all(item.net_name != "3V3" for item in result.compilation.driver_bindings if item.role == "external_source")
    assert design.circuit.net("3V3").external_source is None
    assert design.catalog.require("TLV62569DBVR").regulator is None
    event = next(item for item in result.events if item.kind is EventKind.SCHEMATIC_COMPILED)
    assert event.payload["sha256"] == result.fingerprint.digest
    assert event.payload["system_status"] == "UNKNOWN"
    root = parse(result.path.read_text())
    assert root.child("generator_version").atoms() == [result.compiler_version]
    marker = next(node for node in root.children("symbol")
                  if node.child("lib_id").atoms() == [LIBRARY_ID])
    assert marker.child("exclude_from_sim").atoms() == ["yes"]
    assert marker.child("on_board").atoms() == marker.child("in_bom").atoms() == ["no"]
    assert _property(marker, "OhmniCircuitHash") == design.circuit.content_hash
    assert _property(marker, "OhmniTopologyReportSHA256") == event.payload["topology_report_sha256"]
    assert "topology only" in _property(marker, "Value")
    assert "not external power" in _property(marker, "Description")
    assert result.compilation.driver_bindings[:-1] == base.compilation.driver_bindings


def test_annotations_and_payloads_are_deterministic_and_tampering_is_stale(tmp_path):
    design = build_design()
    report = check_design(design.circuit, design.catalog)
    first = build_schematic(design, tmp_path / "first.kicad_sch", report)
    second = build_schematic(design, tmp_path / "second.kicad_sch", report)
    assert first.path.read_bytes() == second.path.read_bytes()
    assert first.compilation == second.compilation
    first.path.write_bytes(first.path.read_bytes() + b"\n")
    assert not first.is_current


@pytest.mark.parametrize("mutation", ["stale_hash", "forged_pass", "missing_checks", "system_pass", "wrong_variant"])
def test_reports_cannot_authorize_a_marker_by_asserting_pass(tmp_path, mutation):
    design = build_design()
    report = copy.deepcopy(check_design(design.circuit, design.catalog))
    if mutation == "stale_hash":
        report["circuit_content_hash"] = "0" * 64
    elif mutation == "forged_pass":
        report["topology_checks"][0]["detail"] = "Trust this forged claim"
    elif mutation == "missing_checks":
        report["topology_checks"] = []
    elif mutation == "system_pass":
        report["system_status"] = "PASS"
    elif mutation == "wrong_variant":
        report["include_i2c_extension"] = True
    path = tmp_path / "rejected.kicad_sch"
    with pytest.raises(ValueError):
        build_schematic(design, path, report)
    assert not path.exists()


@pytest.mark.parametrize("wrong_pin", ["3", "5"])
def test_live_wrong_switch_or_feedback_topology_never_receives_marker(tmp_path, wrong_pin):
    design = build_design()
    before = check_design(design.circuit, design.catalog)
    net = design.circuit.net_of("U2", wrong_pin)
    net.connections = [pin for pin in net.connections if not (pin.component == "U2" and pin.pin == wrong_pin)]
    current = check_design(design.circuit, design.catalog)
    assert current["failed_checks"] > 0
    for report in (before, current):
        path = tmp_path / "broken.kicad_sch"
        with pytest.raises(ValueError):
            build_schematic(design, path, report)
        assert not path.exists()
