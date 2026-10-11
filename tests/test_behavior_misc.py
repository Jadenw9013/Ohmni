"""D072 bindings: Vishay WSBS8518L1000JT20 Kelvin shunt, Bourns 3361P trimmer and Murata LQM21PH2R2MGEL."""

from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation
from ohmni.domain.circuit import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.domain.units import Quantity
from tools.behavior_audit.runtime_benches import dc_probe_definition

ROOT = Path(__file__).resolve().parents[1]


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


def compile_nets(registry, recipes, entry_id, nets, amps, drive="a", **kwargs):
    recipe = recipes.entries[entry_id]
    circuit = CircuitIR(ir_id=f"d072-{entry_id}", name="D072 binding", components=[
        CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)], nets=[
        Net(name=name, kind="ground" if name == "gnd" else "signal",
            connections=[PinRef(component="U1", pin=pin) for pin in pins]) for name, pins in nets.items()])
    excitation = DCExcitation(positive_net="gnd", negative_net=drive, value=Quantity(value=amps, unit="A"))
    return compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)},
                           excitations=[excitation], **kwargs)


def test_kelvin_shunt_binds_the_two_sense_pin_option(registry, recipes):
    recipe = recipes.entries["OHM-015"]
    assert "WSBS8518L1000JT20" in recipe.reference_part
    assert recipe.terminal_roles == {"1": "I1", "2": "I2", "3": "E1", "4": "E2"}
    compiled = compile_nets(registry, recipes, "OHM-015", {"a": ["1"], "gnd": ["2"], "s1": ["3"], "s2": ["4"]}, 10)
    assert compiled.runnable, compiled.problems
    params = compiled.components[0].parameters
    assert params["value"] == pytest.approx(1e-4) and params["p_rated"] == 36
    assert params["t_knee"] == 70 and params["t_end"] == 170
    # The bound facts come from the ...20 sheet (doc 30341), not the base-model sheet 30134.
    evidence = compiled.components[0].parameter_evidence
    assert all(evidence[k]["sources"] == ["https://www.vishay.com/doc?30341"] for k in ("value", "p_rated", "t_knee"))


def test_kelvin_probe_reads_across_the_sense_terminals(audit):
    compiled, identity = dc_probe_definition(audit, "OHM-015")
    comparison = identity["comparison"]
    assert comparison["observable"] == "kelvin_voltage"
    assert comparison["expected"] == pytest.approx(1e-3)
    assert {"sense_high", "sense_low"} <= set(compiled.node_names)
    # The two-terminal shunt keeps its original probe.
    _, two_terminal = dc_probe_definition(audit, "OHM-014")
    assert two_terminal["comparison"]["observable"] == "anode_voltage"


def test_trimmer_alternate_refuses_a_connected_wiper(registry, recipes):
    recipe = recipes.entries["OHM-019"]
    assert "3361P-1-103GLF" in recipe.reference_part and recipe.required_isolated_roles == ["W"]
    compiled = compile_nets(registry, recipes, "OHM-019", {"a": ["1"], "gnd": ["3"], "w": ["2"]}, 1e-3)
    assert compiled.runnable, compiled.problems
    params = compiled.components[0].parameters
    assert params["value"] == 10000 and params["tol"] == 10 and params["p_rated"] == 0.5 and params["v_max"] == 300
    loaded = compile_nets(registry, recipes, "OHM-019", {"a": ["1"], "gnd": ["3", "2"]}, 1e-3)
    assert not loaded.runnable


def _inductor_rows(registry, recipes, amps, ambient=None):
    compiled = compile_nets(registry, recipes, "OHM-042", {"a": ["1"], "gnd": ["2"]}, amps, measure_currents=True)
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    nodes = {role: node.lower() for role, node in component.role_nodes.items()}
    probes = {role: probe.lower() for role, probe in component.role_current_probes.items()}
    point = {"node_voltages": {nodes["A"]: {"value": amps * 0.39, "unit": "V"}},
             "branch_currents": {probes["A"]: {"value": amps, "unit": "A"}, probes["B"]: {"value": -amps, "unit": "A"}}}
    ratings = evaluate_ratings(compiled, {"status": "ran", "analysis": "op", "operating_point": point}, registry,
                               RatingContext(ambient_c=ambient, thermal_scope_confirmed=True))
    return {r["name"]: r for r in ratings["components"][0]["reference_checks"]}


def test_inductor_binds_lqm21ph_facts_not_the_lqm21pn_list(registry, recipes):
    compiled = compile_nets(registry, recipes, "OHM-042", {"a": ["1"], "gnd": ["2"]}, 0.1)
    params = compiled.components[0].parameters
    assert params["rdc"] == 0.39 and params["irms"] == 0.8 and params["irms_tamb_max"] == 85
    assert params["value"] == pytest.approx(2.2e-6) and params["tmax_part"] == 150
    assert all("LQM21PH2R2MGEL" in e["scope"] for e in compiled.components[0].parameter_evidence.values())


def test_inductor_heating_current_passes_only_up_to_the_rated_ambient(registry, recipes):
    assert _inductor_rows(registry, recipes, 0.5, ambient=25)["heating current"]["status"] == "within_limit"
    assert _inductor_rows(registry, recipes, 0.5, ambient=85)["heating current"]["status"] == "within_limit"
    hot = _inductor_rows(registry, recipes, 0.5, ambient=100)["heating current"]
    assert hot["status"] == "unknown" and "ambient" in hot["reason"]
    assert _inductor_rows(registry, recipes, 0.5)["heating current"]["status"] == "unknown"
    assert _inductor_rows(registry, recipes, 0.9)["heating current"]["status"] == "violation"
    assert _inductor_rows(registry, recipes, 0.9, ambient=100)["heating current"]["status"] == "violation"


def test_unresolved_entries_stay_unbound(recipes):
    # OHM-100 needs owner decisions (IS=0 card rule, typical-vs-maximum MOSFET probe mode).
    assert not {"OHM-017", "OHM-020", "OHM-060", "OHM-100"} & set(recipes.entries)
