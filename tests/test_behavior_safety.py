"""D069 bindings of the D066 mains/isolation/safety group: electrical models only, never a safety claim."""

import math
from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation
from ohmni.domain.circuit import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.domain.units import Quantity

ROOT = Path(__file__).resolve().parents[1]
BOUND = ["OHM-038", "OHM-053", "OHM-055", "OHM-173", "OHM-174"]


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


def circuit(recipe, entry_id, nets):
    return CircuitIR(ir_id=f"d069-{entry_id}", name="D069 binding", components=[
        CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)], nets=[
        Net(name=name, kind="ground" if name == "gnd" else "signal",
            connections=[PinRef(component="U1", pin=pin) for pin in pins])
        for name, pins in nets.items()])


def compile_nets(registry, recipes, entry_id, nets, drive, **kwargs):
    recipe = recipes.entries[entry_id]
    excitation = DCExcitation(positive_net="gnd", negative_net=drive, value=Quantity(value=1e-3, unit="A"))
    return compile_circuit(circuit(recipe, entry_id, nets), registry, recipes,
                           {"U1": BehaviorSelection(entry_id=entry_id)}, excitations=[excitation], **kwargs)


@pytest.mark.parametrize("entry_id", BOUND)
def test_every_safety_binding_states_no_safety_acceptance_first(recipes, entry_id):
    limitations = recipes.entries[entry_id].limitations
    assert limitations[0].startswith("No mains, isolation or safety acceptance (D066)")


def test_current_transformer_stays_blocked_without_a_recipe(recipes, registry):
    assert "OHM-054" not in recipes.entries
    research = registry.entry("OHM-054").research
    assert research.simulation_blockers
    assert any("not a pad" in item for item in research.remaining_open_items)


@pytest.mark.parametrize(("entry_id", "variant", "resistance", "current"), [
    ("OHM-053", "n1", 0.015, 16.0), ("OHM-053", "n2", 0.012, 16.0), ("OHM-053", "n3", 0.018, 16.0),
    ("OHM-055", "td", 0.6, 0.008), ("OHM-055", "rd", 0.6, 0.008),
    ("OHM-055", "tx", 1.1, 0.008), ("OHM-055", "rx", 1.1, 0.008),
    ("OHM-173", None, 1.2e-3, 20.0), ("OHM-174", None, 1.2e-3, 35.0),
])
def test_path_probes_use_each_parts_sourced_resistance_and_stimulus(audit, entry_id, variant, resistance, current):
    from tools.behavior_audit.runtime_benches import dc_probe_definition, dc_probe_variants

    compiled, identity = dc_probe_definition(audit, entry_id, variant)
    assert compiled.runnable, compiled.problems
    comparison = identity["comparison"]
    assert comparison["observable"] == "path_resistance"
    assert comparison["expected"] == pytest.approx(resistance)
    assert comparison["tolerance"] == pytest.approx(resistance * 1e-3)
    assert comparison["current"] == pytest.approx(current)
    assert all(fact["basis"] == "MFR_DATASHEET" for fact in comparison["source_facts"].values())
    assert variant in dc_probe_variants(compiled.components[0].behavior_id, None)


def test_x2_capacitor_charge_probe_uses_the_bound_wima_row(audit):
    from tools.behavior_audit.runtime_benches import tran_probe_definition

    compiled, identity = tran_probe_definition(audit, "OHM-038")
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    assert component.reference_part.startswith("WIMA MKX2AW31004C00")
    assert component.parameters["value"] == pytest.approx(1e-7)
    assert component.parameters["vr"] == 305
    assert "MKX2AW31004C00" in component.parameter_evidence["vr"]["scope"]
    assert identity["comparison"][0]["expected"] == pytest.approx(1e-3 * (1e-3 - 0.5e-9) / 1e-7)


def test_x2_capacitor_never_reports_a_rating_pass(registry, recipes):
    compiled = compile_nets(registry, recipes, "OHM-038", {"line": ["1"], "gnd": ["2"]}, "line", measure_currents=True)
    component = compiled.components[0]
    node = component.role_nodes["T1"].lower()
    probes = [p.lower() for p in component.role_current_probes.values()]
    result = {"status": "ran", "analysis": "op", "operating_point": {
        "node_voltages": {node: {"value": 100.0, "unit": "V"}},
        "branch_currents": {p: {"value": 0.0, "unit": "A"} for p in probes}}}
    ratings = evaluate_ratings(compiled, result, registry, RatingContext(ambient_c=25, thermal_scope_confirmed=True))
    assert ratings["components"][0]["status"] == "unknown"
    assert not ratings["components"][0]["reference_checks"]


def test_flyback_coupling_and_winding_inductances_follow_the_sourced_ratio(audit):
    from tools.behavior_audit.runtime_benches import dc_probe_definition

    compiled, _ = dc_probe_definition(audit, "OHM-053", "n1")
    p = compiled.components[0].parameters
    assert p["lp"] == pytest.approx(12e-6)
    assert p["ls"] == pytest.approx(3e-6)
    assert p["la"] == pytest.approx(1.92e-6)
    assert p["k"] == pytest.approx(math.sqrt(1 - 0.4 / 12))
    assert compiled.components[0].source_status == "research_required"


def test_flyback_parallel_pins_must_share_a_net(registry, recipes):
    nets = {"p": ["1", "2"], "pr": ["3", "4"], "a": ["5"], "ar": ["6"], "gnd": ["7", "8", "9"], "s": ["10", "11", "12"]}
    assert compile_nets(registry, recipes, "OHM-053", nets, "p").runnable
    split = dict(nets, p=["1"], p2=["2"])
    result = compile_nets(registry, recipes, "OHM-053", split, "pr")
    assert not result.runnable
    assert any("internally common N1_DOT" in problem for problem in result.problems)


def test_ethernet_magnetics_refuse_unmapped_pins_and_biased_centre_taps(registry, recipes):
    nets = {"tdp": ["1"], "tdct": ["2"], "tdn": ["3"], "rdp": ["6"], "rdct": ["7"], "rdn": ["8"],
            "rxn": ["9"], "rxct": ["10"], "rxp": ["11"], "txn": ["14"], "txct": ["15"], "gnd": ["16"]}
    assert compile_nets(registry, recipes, "OHM-055", nets, "tdp").runnable
    with_nc = dict(nets, extra=["4"])
    assert not compile_nets(registry, recipes, "OHM-055", with_nc, "tdp").runnable
    biased = {k: v for k, v in nets.items() if k != "tdct"}
    biased["gnd"] = ["16", "2"]
    result = compile_nets(registry, recipes, "OHM-055", biased, "tdp")
    assert not result.runnable
    assert any("TD_CT must remain isolated" in problem for problem in result.problems)


@pytest.mark.parametrize("entry_id", ["OHM-173", "OHM-174"])
def test_xt_binding_is_symmetric_with_no_polarity_role(recipes, entry_id):
    recipe = recipes.entries[entry_id]
    assert set(recipe.terminal_roles.values()) == {"P1", "P2", "M1", "M2"}
    assert recipe.template_override == "R{ref}_c1 {P1} {M1} {rc}\nR{ref}_c2 {P2} {M2} {rc}\n"
    assert any(text.startswith("POLARITY IS NOT ASSIGNED") and "physical part" in text for text in recipe.limitations)


@pytest.mark.parametrize(("entry_id", "amps", "volts", "current_status", "voltage_status"), [
    ("OHM-173", 20.0, 80.0, "within_limit", "within_limit"),
    ("OHM-173", 21.0, 12.0, "violation", "within_limit"),
    ("OHM-173", 10.0, 81.0, "within_limit", "violation"),
    ("OHM-174", 35.0, 48.0, "within_limit", "within_limit"),
    ("OHM-174", 36.0, 48.0, "violation", "within_limit"),
])
def test_xt_contact_ratings_use_the_m30_values(registry, recipes, entry_id, amps, volts, current_status, voltage_status):
    compiled = compile_nets(registry, recipes, entry_id, {"bat": ["1", "M1"], "gnd": ["2", "M2"]}, "bat", measure_currents=True)
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    nodes = {role: node.lower() for role, node in component.role_nodes.items()}
    probes = {role: probe.lower() for role, probe in component.role_current_probes.items()}
    voltages = {nodes["P1"]: volts, nodes["M1"]: volts}
    currents = {probes["P1"]: amps, probes["M1"]: -amps, probes["P2"]: -amps, probes["M2"]: amps}
    result = {"status": "ran", "analysis": "op", "operating_point": {
        "node_voltages": {n: {"value": v, "unit": "V"} for n, v in voltages.items() if n != "0"},
        "branch_currents": {p: {"value": i, "unit": "A"} for p, i in currents.items()}}}
    ratings = evaluate_ratings(compiled, result, registry, RatingContext(ambient_c=25, thermal_scope_confirmed=True))
    rows = {r["name"]: r for r in ratings["components"][0]["reference_checks"]}
    assert rows["contact current P1"]["status"] == current_status
    assert rows["contact-to-contact voltage"]["status"] == voltage_status
    assert rows["contact temperature"]["status"] == "unknown"
