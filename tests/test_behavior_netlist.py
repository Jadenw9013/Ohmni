"""Behavior compilation preserves topology, evidence and non-run semantics."""

from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes, terminal_nodes
from ohmni.behavior.runtime_models import BehaviorSelection
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def divider(entry_id="OHM-004", package="0603", part_id="GENERIC_RESISTOR"):
    return CircuitIR(ir_id="behavior-divider", name="Explicit divider", components=[
        CircuitComponent(ref=ref, part_id=part_id, package=package, value=Quantity.ohms(10000))
        for ref in ["R1", "R2"]
    ], nets=[
        Net(name="supply", kind="power", connections=[PinRef(component="R1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(5)))),
        Net(name="middle", connections=[PinRef(component="R1", pin="2"), PinRef(component="R2", pin="1")]),
        Net(name="return", kind="ground", connections=[PinRef(component="R2", pin="2")]),
    ])


def test_catalog_join_is_explicit_and_deterministic(registry, recipes):
    circuit = divider()
    a = compile_circuit(circuit, registry, recipes)
    b = compile_circuit(circuit.model_copy(update={"nets": list(reversed(circuit.nets))}), registry, recipes)
    assert a.runnable and b.runnable
    assert a.netlist == b.netlist
    assert a.netlist_sha256 == b.netlist_sha256
    assert ".options tnom=25\n.temp 25" in a.netlist
    assert ".include" not in a.netlist
    assert a.components[0].parameters["p_rated"] == 0.1
    assert a.components[0].parameter_evidence["p_rated"]["scope"].startswith("Vishay CRCW0603")
    assert a.components[0].source_status == "partial"
    assert a.components[0].confidence == "M"
    assert a.components[0].rating_confidence == "H"
    assert a.components[0].source_confidence == registry.behavior_class("BEH-RES-FIXED").canonical_payload["confidence"]


@pytest.mark.parametrize("entry_id", [f"OHM-{i:03}" for i in range(1, 11)])
def test_every_first_batch_entry_uses_its_sourced_fields(entry_id, registry, recipes):
    recipe = recipes.entries[entry_id]
    circuit = divider(entry_id, recipe.package, entry_id)
    choices = {c.ref: BehaviorSelection(entry_id=entry_id) for c in circuit.components}
    result = compile_circuit(circuit, registry, recipes, choices)
    assert result.runnable, result.problems
    for component in result.components:
        for alias, binding in recipe.critical_facts.items():
            fact = next(f for f in registry.entry(entry_id).research.field_updates if f.field == binding.field)
            assert component.parameters[alias] == fact.value
            assert component.parameter_evidence[alias]["sources"] == fact.sources


def test_missing_rating_refuses_entire_circuit(registry, recipes, monkeypatch):
    entry = registry.entry("OHM-004")
    research = entry.research.model_copy(update={"field_updates": [f for f in entry.research.field_updates
                                                                  if f.field != "reference.p_rated"]})
    monkeypatch.setitem(registry.entries, entry.entry_id, entry.model_copy(update={"research": research}))
    result = compile_circuit(divider(), registry, recipes)
    assert not result.runnable and result.netlist is None
    assert "critical field reference.p_rated" in ";".join(result.problems)


def test_assumed_rating_refuses_simulation(registry, recipes, monkeypatch):
    entry = registry.entry("OHM-004")
    facts = [f.model_copy(update={"basis": "ASSUMPTION"}) if f.field == "reference.p_rated" else f
             for f in entry.research.field_updates]
    monkeypatch.setitem(registry.entries, entry.entry_id,
                        entry.model_copy(update={"research": entry.research.model_copy(update={"field_updates": facts})}))
    assert "unsourced" in ";".join(compile_circuit(divider(), registry, recipes).problems)


def test_wrong_package_and_unknown_selection_are_not_substituted(registry, recipes):
    result = compile_circuit(divider(package="0805"), registry, recipes,
                             {"R1": BehaviorSelection(entry_id="OHM-004")})
    assert not result.runnable
    assert "package differs" in ";".join(result.problems)
    bad = compile_circuit(divider(), registry, recipes, {"R1": BehaviorSelection(entry_id="OHM-083")})
    assert not bad.runnable and "primary-source" in ";".join(bad.problems)


def test_missing_pin_and_separate_ground_nets_are_not_shortened(registry, recipes):
    circuit = divider()
    circuit.nets[1].connections.pop()
    assert "connected pins" in ";".join(compile_circuit(circuit, registry, recipes).problems)
    circuit = divider()
    circuit.nets.append(Net(name="isolated_return", kind="ground"))
    assert "separate grounds" in ";".join(compile_circuit(circuit, registry, recipes).problems)


def test_led_catalog_permutation_reaches_the_correct_nodes(registry, monkeypatch):
    circuit = divider()
    component = circuit.components[0].model_copy(update={"part_id": "GENERIC_LED_GREEN", "package": "0603"})
    nodes = {net.name: net.name for net in circuit.nets}
    bound = terminal_nodes(circuit, component, "OHM-078", {"1": "K", "2": "A"}, registry, nodes)
    assert bound == {"1": "middle", "2": "supply"}
    monkeypatch.delitem(registry.bindings, "GENERIC_LED_GREEN")
    with pytest.raises(ValueError, match="permutation is missing"):
        terminal_nodes(circuit, component, "OHM-078", {"1": "K", "2": "A"}, registry, nodes)


def test_zero_resistance_is_not_silently_replaced(registry, recipes):
    circuit = divider()
    circuit.components[0].value = Quantity.ohms(0)
    assert "zero-value substitution" in ";".join(compile_circuit(circuit, registry, recipes).problems)


@pytest.mark.parametrize("analysis", ["op", "tran"])
def test_empty_tool_success_is_not_a_result(registry, recipes, tmp_path, monkeypatch, analysis):
    compiled = compile_circuit(divider(), registry, recipes, analysis=analysis)
    adapter = NgspiceAdapter(executable="fake")
    monkeypatch.setattr(adapter, "behavior_bench", lambda *_a, **_k: {
        "status": "ran", "stdout": "", "stderr": "", "version_output": "ngspice-42"})
    result = adapter.behavior_circuit(compiled, work_dir=tmp_path, analysis=analysis)
    assert result["status"] == "failed"
    assert result["operating_point"] is None and result["transient"] is None


def test_blocked_compile_never_invokes_the_solver(registry, recipes, tmp_path, monkeypatch):
    compiled = compile_circuit(divider(package="unknown"), registry, recipes)
    adapter = NgspiceAdapter(executable="fake")
    def unexpected(*args, **kwargs):
        raise AssertionError("must not run")
    monkeypatch.setattr(adapter, "behavior_bench", unexpected)
    result = adapter.behavior_circuit(compiled, work_dir=tmp_path)
    assert result["status"] == "not_run" and result["problems"]


def test_analysis_must_match_the_validated_compilation(registry, recipes, tmp_path):
    compiled = compile_circuit(divider(), registry, recipes)
    result = NgspiceAdapter(executable="fake").behavior_circuit(compiled, work_dir=tmp_path, analysis="tran")
    assert result["status"] == "not_run"


@pytest.mark.parametrize("step,stop", [("0s", "1ms"), ("-1us", "1ms"), ("1ms", "1us"),
                                      ("1us\n.shell whoami", "1ms")])
def test_invalid_time_arguments_never_reach_the_solver(registry, recipes, tmp_path, step, stop):
    compiled = compile_circuit(divider(), registry, recipes, analysis="tran")
    result = NgspiceAdapter(executable="fake").behavior_circuit(
        compiled, work_dir=tmp_path, analysis="tran", tstep=step, tstop=stop)
    assert result["status"] == "not_run"
    assert "Invalid transient" in ";".join(result["problems"])
