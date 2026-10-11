"""LED and display bindings of D070: Kingbright lamps, Broadcom HDSP-55xx digits, WS2812B-V7 and the NHD 16x2 module."""

from pathlib import Path

import pytest

from ohmni.application.component_behavior import ComponentBehaviorService
from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, entry_problems, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation
from ohmni.domain.circuit import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.domain.units import Quantity
from tools.behavior_audit.runtime_benches import dc_probe_variants, display_segment_common

ROOT = Path(__file__).resolve().parents[1]
BOUND = ["OHM-075", "OHM-076", "OHM-084", "OHM-087", "OHM-088", "OHM-091"]


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


@pytest.fixture(scope="module")
def audit():
    from tools.behavior_audit.audit import BehaviorAudit

    return BehaviorAudit(ROOT)


def compile_nets(registry, recipes, entry_id, nets, drive="a", **kwargs):
    recipe = recipes.entries[entry_id]
    circuit = CircuitIR(ir_id=f"d070-{entry_id}", name="D070 binding", components=[
        CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)], nets=[
        Net(name=name, kind="ground" if name == "gnd" else "signal",
            connections=[PinRef(component="U1", pin=pin) for pin in pins]) for name, pins in nets.items()])
    excitation = DCExcitation(positive_net="gnd", negative_net=drive, value=Quantity(value=0.02, unit="A"))
    return compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)},
                           excitations=[excitation], **kwargs)


def op_result(component, voltages, currents):
    nodes = {role: node.lower() for role, node in component.role_nodes.items()}
    probes = {role: probe.lower() for role, probe in component.role_current_probes.items()}
    return {"status": "ran", "analysis": "op", "operating_point": {
        "node_voltages": {nodes[r]: {"value": v, "unit": "V"} for r, v in voltages.items() if nodes[r] != "0"},
        "branch_currents": {probes[r]: {"value": i, "unit": "A"} for r, i in currents.items()}}}


@pytest.mark.parametrize("entry_id,part,rth,vf_max", [("OHM-075", "WP813ID", 500, 2.5), ("OHM-076", "WP113IDT", 580, 2.3)])
def test_lamps_bind_the_kingbright_sheet_with_sourced_thermal_resistance(registry, recipes, entry_id, part, rth, vf_max):
    recipe = recipes.entries[entry_id]
    assert part in recipe.reference_part and part in recipe.limitations[0]
    compiled = compile_nets(registry, recipes, entry_id, {"a": ["2"], "gnd": ["1"]})
    assert compiled.runnable, compiled.problems
    params = compiled.components[0].parameters
    assert params["rth_ja"] == rth and params["tj_max"] == 125 and params["vf_max"] == vf_max
    assert params["if_max"] == pytest.approx(0.03) and params["p_rated"] == pytest.approx(0.075)
    assert compiled.components[0].parameter_evidence["rth_ja"]["basis"] == "MFR_DATASHEET"
    assert dc_probe_variants(recipe.behavior_id, recipe) == [None, "forward_fit1", "forward_fit2", "forward_fit3"]


def test_single_digit_redundant_cathodes_are_one_common(registry, recipes):
    recipe = recipes.entries["OHM-087"]
    assert [p for p, r in recipe.terminal_roles.items() if r == "COM"] == ["3", "8"]
    nets = {"a": ["7"], "gnd": ["3", "8"], "idle": ["1", "2", "4", "5", "6", "9", "10"]}
    assert compile_nets(registry, recipes, "OHM-087", nets).runnable
    split = {"a": ["7"], "gnd": ["3"], "other": ["8"], "idle": ["1", "2", "4", "5", "6", "9", "10"]}
    compiled = compile_nets(registry, recipes, "OHM-087", split)
    assert not compiled.runnable and any("internally common COM" in p for p in compiled.problems)


def test_display_probe_drives_every_segment_through_its_own_common(recipes):
    single, dual = recipes.entries["OHM-087"], recipes.entries["OHM-088"]
    variants = dc_probe_variants(single.behavior_id, single)
    assert set(variants[:8]) == {"a", "b", "c", "d", "e", "f", "g", "dp"} and variants[8:] == [
        "segment_a_fit1", "segment_a_fit2", "segment_a_fit3"]
    variants = dc_probe_variants(dual.behavior_id, dual)
    assert len([v for v in variants if "fit" not in v]) == 16 and variants[-1] == "segment_a1_fit3"
    roles = set(dual.terminal_roles.values())
    assert display_segment_common(roles, "DP1") == "COM1" and display_segment_common(roles, "A2") == "COM2"
    assert display_segment_common(set(single.terminal_roles.values()), "DP") == "COM"


def _display_rows(registry, recipes, segment_amps, ambient=None, reverse=0.0):
    nets = {"a": ["7"], "gnd": ["3", "8"], "e": ["1"], "idle": ["2", "4", "5", "6", "9", "10"]}
    compiled = compile_nets(registry, recipes, "OHM-087", nets, measure_currents=True)
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    voltages = {"A": 2.05, "COM": 0.0, "E": -reverse}
    currents = {role: 0.0 for role in component.role_current_probes}
    currents.update(A=segment_amps, COM=-segment_amps)
    ratings = evaluate_ratings(compiled, op_result(component, voltages, currents), registry,
                               RatingContext(ambient_c=ambient, thermal_scope_confirmed=True))
    return {r["name"]: r for r in ratings["components"][0]["reference_checks"]}, ratings["components"][0]["status"]


def test_segment_current_passes_only_at_or_below_the_derating_knee(registry, recipes):
    rows, _ = _display_rows(registry, recipes, 0.025, ambient=25)
    assert rows["segment A current"]["status"] == "within_limit"
    assert rows["segment A power"]["status"] == "within_limit"
    rows, status = _display_rows(registry, recipes, 0.025, ambient=70)
    assert rows["segment A current"]["status"] == "unknown" and "knee" in rows["segment A current"]["reason"]
    assert status == "unknown"
    rows, _ = _display_rows(registry, recipes, 0.025)
    assert rows["segment A current"]["status"] == "unknown"
    rows, status = _display_rows(registry, recipes, 0.031)
    assert rows["segment A current"]["status"] == "violation" and status == "violation"
    rows, _ = _display_rows(registry, recipes, 0.040, ambient=25)
    assert rows["segment A power"]["status"] == "violation"
    assert not any(name.startswith("segment COM") for name in rows)


def test_segment_reverse_bias_is_never_accepted(registry, recipes):
    rows, _ = _display_rows(registry, recipes, 0.01, ambient=25)
    assert "segment E reverse voltage" not in rows
    rows, _ = _display_rows(registry, recipes, 0.01, ambient=25, reverse=1.0)
    assert rows["segment E reverse voltage"]["status"] == "unknown"
    rows, _ = _display_rows(registry, recipes, 0.01, ambient=25, reverse=3.5)
    assert rows["segment E reverse voltage"]["status"] == "violation"


def test_l3_entries_simulate_only_their_bound_electrical_reference(registry, recipes):
    for entry_id in ("OHM-084", "OHM-091"):
        entry = registry.entry(entry_id)
        assert entry.layer.value == "L3" and entry.simulation_disposition.value == "simulable"  # D066 item 3
        assert entry_problems(entry, recipes.entries[entry_id]) == []
        assert "L3 protocol behavior is not simulable by ngspice" in entry_problems(entry, None)
        assert recipes.entries[entry_id].limitations[0].startswith("L1 ")
    unbound = registry.entry("OHM-092")
    assert unbound.layer.value == "L3" and entry_problems(unbound, recipes.entries.get("OHM-092"))


def test_addressable_led_full_white_load_uses_the_v7_currents(audit):
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    compiled, identity = dc_probe_definition(audit, "OHM-084")
    params = compiled.components[0].parameters
    assert params["ich"] == pytest.approx(16.12e-3) and params["iq"] == pytest.approx(1e-6)
    assert (params["vdd_min"], params["vdd_max"]) == (3.3, 5.3)
    assert identity["comparison"]["expected"] == pytest.approx(3 * 16.12e-3 + 1e-6)
    assert identity["comparison"]["supply_voltage"] == 5.0
    assert "+ 3*" in compiled.netlist


def test_lcd_backlight_is_the_sourced_operating_point_not_the_assumed_diode(audit):
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    compiled, identity = dc_probe_definition(audit, "OHM-091", "backlight")
    params = compiled.components[0].parameters
    assert params["rbl"] == pytest.approx(5.0 / 0.130)
    assert identity["comparison"]["expected"] == pytest.approx(0.130)
    assert " BL" not in compiled.netlist and "38.46" in compiled.netlist
    compiled, identity = dc_probe_definition(audit, "OHM-091", "logic")
    assert identity["comparison"]["expected"] == pytest.approx(1.0e-3)


def test_reference_only_reasons_name_why_the_record_is_not_simulable(tmp_path):
    service = ComponentBehaviorService(ROOT, tmp_path)
    # D066 item 3: the L3 addressable LED simulates its electrical pins only, and says so.
    state, reason = service.behavior_state("OHM-084")
    assert state == "simulated" and "WS2812B-V7" in reason and "electrical pins only" in reason
    assert "(L3) are not modeled" in reason
    state, reason = service.behavior_state("OHM-087")
    assert state == "reference_only" and "research_required" in reason and "package" not in reason
