from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, apply_open_faults, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection
from tools.behavior_audit.runtime_benches import resistor_divider

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def compiled():
    registry = BehaviorRegistry(repo_root=ROOT)
    recipes = load_recipes(registry, ROOT)
    circuit = resistor_divider("OHM-004", "0603")
    result = compile_circuit(
        circuit,
        registry,
        recipes,
        {c.ref: BehaviorSelection(entry_id="OHM-004") for c in circuit.components},
        measure_currents=True,
    )
    assert result.runnable, result.problems
    return registry, result


def observed(compilation, voltage=2.5, current=0.00025, status="ran"):
    voltages = {}
    currents = {}
    for c in compilation.components:
        for role, node in c.role_nodes.items():
            # Synthetic isolated resistor observations: explicitly labeled test inputs.
            voltages[node] = {"value": voltage if role == "A" else 0, "unit": "V"}
            currents[c.role_current_probes[role]] = {
                "value": current if role == "A" else -current,
                "unit": "A",
            }
    # Only one component avoids inconsistent shared-node test observations.
    c = compilation.components[0]
    voltages = {
        c.role_nodes["A"]: {"value": voltage, "unit": "V"},
        c.role_nodes["B"]: {"value": 0, "unit": "V"},
    }
    return {
        "status": status,
        "analysis": "op",
        "operating_point": {"node_voltages": voltages, "branch_currents": currents},
    }


def one(compiled):
    registry, c = compiled
    return registry, c.model_copy(update={"components": [c.components[0]]})


def test_missing_context_never_defaults_thermal_to_25(compiled):
    registry, c = one(compiled)
    result = evaluate_ratings(c, observed(c), registry)
    assert result["status"] == "unknown"
    power = next(x for x in result["components"][0]["reference_checks"] if x["name"] == "power")
    assert power["status"] == "unknown"


def test_sourced_derating_and_violation_are_distinct_from_execution(compiled):
    registry, c = one(compiled)
    context = RatingContext(ambient_c=155, thermal_scope_confirmed=True)
    report = evaluate_ratings(c, observed(c), registry, context)
    assert report["status"] == "violation"
    assert report["components"][0]["observations"]["P_allowed"] == 0
    assert (
        next(x for x in report["components"][0]["failure_modes"] if x["id"] == "overpower_mild")[
            "status"
        ]
        == "triggered"
    )


@pytest.mark.parametrize("status", ["not_run", "failed", "timed_out"])
def test_stale_observations_never_become_pass_or_damage(compiled, status):
    registry, c = one(compiled)
    result = evaluate_ratings(
        c,
        observed(c, 200, 1, status),
        registry,
        RatingContext(ambient_c=25, thermal_scope_confirmed=True),
    )
    assert result["status"] == "not_run"
    assert not result["fault_requests"]
    assert all(x["status"] == "unknown" for x in result["components"][0]["reference_checks"])


def test_undefined_damage_duration_stays_unknown(compiled):
    registry, c = one(compiled)
    result = evaluate_ratings(
        c,
        observed(c, 40, 0.004),
        registry,
        RatingContext(ambient_c=25, thermal_scope_confirmed=True),
    )
    failures = result["components"][0]["failure_modes"]
    assert next(x for x in failures if x["id"] == "overpower_open")["status"] == "unknown"
    assert not result["fault_requests"]


def test_explicit_voltage_failure_produces_traceable_open_deck(compiled):
    registry, c = one(compiled)
    result = evaluate_ratings(c, observed(c, 100, 0.01), registry)
    assert result["status"] == "violation"
    assert result["fault_requests"][0]["basis"] == "ASSUMPTION"
    faulted = apply_open_faults(c, result["fault_requests"])
    assert faulted.netlist_sha256 != c.netlist_sha256
    assert "Rfailure0" in faulted.netlist and "1e9" in faulted.netlist
    assert c.netlist != faulted.netlist


def test_missing_or_assumed_rating_cannot_pass(compiled):
    registry, c = one(compiled)
    component = c.components[0]
    evidence = dict(component.parameter_evidence)
    evidence["u_limit"] = dict(evidence["u_limit"], basis="ASSUMPTION")
    c = c.model_copy(
        update={"components": [component.model_copy(update={"parameter_evidence": evidence})]}
    )
    result = evaluate_ratings(c, observed(c, 200, 1), registry)
    assert not result["fault_requests"]
    row = next(
        x for x in result["components"][0]["reference_checks"] if x["name"] == "working voltage"
    )
    assert row["status"] == "unknown" and "sourced limit" in row["reason"]


def test_all_declared_expressions_and_failure_responses_remain_visible(compiled):
    registry, c = one(compiled)
    for behavior in registry.classes.values():
        altered = c.model_copy(
            update={
                "components": [
                    c.components[0].model_copy(update={"behavior_id": behavior.behavior_id})
                ]
            }
        )
        report = evaluate_ratings(altered, {"status": "not_run"}, registry)["components"][0]
        assert [x["check"] for x in report["class_checks"]] == [
            x["check"] for x in behavior.canonical_payload.get("ratings", [])
        ]
        assert [x["sim_response"] for x in report["failure_modes"]] == [
            x["sim_response"] for x in behavior.canonical_payload.get("failure_modes", [])
        ]
        assert report["status"] == "unknown"
