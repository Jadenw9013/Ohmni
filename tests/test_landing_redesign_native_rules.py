"""Bind KiCad's independent checks to the exact authored geometry policy."""

import json

import pytest

from tools.landing_redesign.native_rules import verify_native_rules, write_native_rules
from tools.landing_redesign.physical import routing_constraints


def _pcb(tmp_path):
    path = tmp_path / "redesign.kicad_pcb"
    path.write_text('(kicad_pcb (version 20240108) (net 1 "3V3") (net 2 "SDA") '
                    '(net 3 "SW_NODE") (net 4 "FB_REFB"))', encoding="utf-8")
    return path


def _write(path):
    return write_native_rules(path, routing_constraints(), circuit_hash="1" * 64, routing_plan_hash="2" * 64)


def test_native_rules_use_the_same_profile_without_exclusions(tmp_path):
    path = _pcb(tmp_path)
    original = path.read_bytes()
    manifest = _write(path)
    assert verify_native_rules(manifest)
    assert path.read_bytes() == original
    project = json.loads(path.with_suffix(".kicad_pro").read_text())
    native = project["board"]["design_settings"]["rules"]
    assert native["min_clearance"] == native["min_track_width"] == .15
    assert native["min_copper_edge_clearance"] == .5
    assert native["min_via_diameter"] == .8
    assert native["min_through_hole_diameter"] == .4
    rules = path.with_suffix(".kicad_dru").read_text()
    assert "(constraint clearance (min 0.15mm))" in rules
    assert "(constraint track_width (min 0.15mm))" in rules
    assert "A.NetName == 'SW_NODE'" in rules
    assert "(constraint track_width (min 0.25mm))" in rules
    assert manifest["net_minimum_width_mm"] == {"3V3": .25, "SDA": .15, "SW_NODE": .25, "FB_REFB": .15}
    assert "severity" not in rules and "ignore" not in rules and "exclusion" not in rules
    assert manifest == _write(path)


@pytest.mark.parametrize("suffix", [".kicad_pro", ".kicad_dru", ".kicad_pcb"])
def test_stale_native_inputs_are_rejected(tmp_path, suffix):
    path = _pcb(tmp_path)
    manifest = _write(path)
    altered = path.with_suffix(suffix)
    altered.write_bytes(altered.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="changed"):
        verify_native_rules(manifest)


def test_changed_routing_profile_and_missing_sidecar_are_rejected(tmp_path):
    manifest = _write(_pcb(tmp_path))
    manifest["routing_constraints"]["profile"]["clearance_mm"]["value"] = .1
    with pytest.raises(ValueError, match="policy changed"):
        verify_native_rules(manifest)
    manifest = _write(_pcb(tmp_path))
    manifest["files"].pop()
    with pytest.raises(ValueError, match="lacks both"):
        verify_native_rules(manifest)


def test_does_not_replace_existing_user_project(tmp_path):
    path = _pcb(tmp_path)
    project = path.with_suffix(".kicad_pro")
    project.write_text('{"owner": "human"}', encoding="utf-8")
    with pytest.raises(ValueError, match="unowned"):
        _write(path)
    assert project.read_text() == '{"owner": "human"}'
    assert not path.with_suffix(".kicad_dru").exists()


def test_net_condition_injection_is_not_accepted(tmp_path):
    path = _pcb(tmp_path)
    path.write_text('(kicad_pcb (net 1 "SW_NODE") (net 2 "FB_REFB") (net 3 "bad\' || A.Type"))')
    with pytest.raises(ValueError, match="unsupported net name"):
        _write(path)
