"""Capacitor bindings of D067: Murata/KEMET/Vishay ceramics and Nichicon aluminium electrolytic/polymer cards."""

from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import ACExcitation, BehaviorSelection
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from tools.behavior_audit.runtime_benches import AC_PROBES, PATH_PROBES

ROOT = Path(__file__).resolve().parents[1]
CERAMICS = {"OHM-021": (1e-7, 6.3, 5e8), "OHM-022": (1e-7, 16, 5e9), "OHM-023": (1e-6, 25, 5e7),
            "OHM-025": (1e-5, 25, 5e6), "OHM-026": (2.2e-5, 25, 50 / 22e-6), "OHM-027": (1e-6, 100, 1e9),
            "OHM-028": (4.7e-8, 50, 1e10)}
# entry: (C, VR, Ileak, t_min, t_max)
ALUMINIUM = {"OHM-029": (2.2e-4, 25, 165e-6, -55, 105), "OHM-030": (4.7e-5, 25, 35.25e-6, -55, 105),
             "OHM-031": (2.2e-3, 35, 832.466e-6, -40, 85), "OHM-032": (1e-4, 16, 320e-6, -55, 105)}


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def circuit(recipes, entry_id, volts=1.0):
    package = recipes.entries[entry_id].package
    return CircuitIR(ir_id="cap", name="Capacitor", components=[
        CircuitComponent(ref="C1", part_id=entry_id, package=package)], nets=[
        Net(name="rail", kind="power", connections=[PinRef(component="C1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(volts)))),
        Net(name="gnd", kind="ground", connections=[PinRef(component="C1", pin="2")])])


def compiled(registry, recipes, entry_id, **kwargs):
    return compile_circuit(circuit(recipes, entry_id), registry, recipes, {"C1": BehaviorSelection(entry_id=entry_id)},
                           measure_currents=True, **kwargs)


def result_at(compilation, volts, ac=None, freq=100e3, iac=0.0):
    c1 = compilation.components[0]
    node = c1.role_nodes["A"].lower()
    probes = [p.lower() for p in c1.role_current_probes.values()]
    op = {"node_voltages": {node: {"value": volts, "unit": "V"}},
          "branch_currents": {p: {"value": 0.0, "unit": "A"} for p in probes}}
    result = {"status": "ran", "analysis": "op" if ac is None else "ac", "operating_point": op}
    if ac is not None:
        result["ac"] = {"points": [{"frequency_hz": freq, "node_voltages": {node: [ac, 0.0]},
                                    "branch_currents": {p: [iac, 0.0] for p in probes}}]}
    return result


def rows(ratings):
    return {r["name"]: r for r in ratings["components"][0]["reference_checks"]}


@pytest.mark.parametrize("entry_id", sorted(CERAMICS))
def test_ceramic_bindings_use_the_bound_parts_sourced_minimum_insulation_resistance(registry, recipes, entry_id):
    value, vr, rleak = CERAMICS[entry_id]
    component = compiled(registry, recipes, entry_id).components[0]
    assert component.parameters["value"] == pytest.approx(value)
    assert component.parameters["vr"] == vr
    assert component.parameters["rleak"] == pytest.approx(rleak)
    assert component.parameter_evidence["vr"]["basis"] == "MFR_DATASHEET"


def test_disc_binding_states_the_value_difference_and_no_safety_rating(recipes):
    recipe = recipes.entries["OHM-028"]
    text = " ".join(recipe.limitations)
    assert "47 nF" in recipe.reference_part and "NOT the 100 nF spec default" in recipe.reference_part
    assert "VALUE DIFFERS FROM THE SPEC DEFAULT" in text and "NO SAFETY RATING - NOT FOR MAINS" in text


def test_snap_in_binding_is_two_pin_only(registry, recipes):
    recipe = recipes.entries["OHM-031"]
    assert recipe.terminal_roles == {"1": "A", "2": "K"}
    assert "TWO-PIN VARIANT ONLY" in " ".join(recipe.limitations)
    three = circuit(recipes, "OHM-031")
    three.nets[1].connections.append(PinRef(component="C1", pin="3"))
    refused = compile_circuit(three, registry, recipes, {"C1": BehaviorSelection(entry_id="OHM-031")})
    assert not refused.runnable
    assert any("connected pins must exactly match" in p for p in refused.problems)


@pytest.mark.parametrize("entry_id", sorted(ALUMINIUM))
def test_aluminium_cards_reproduce_the_sourced_leakage(registry, recipes, entry_id):
    value, vr, ileak, t_min, t_max = ALUMINIUM[entry_id]
    component = compiled(registry, recipes, entry_id).components[0]
    assert component.parameters["value"] == pytest.approx(value)
    assert component.parameters["rleak"] == pytest.approx(vr / ileak)
    assert (component.parameters["t_min"], component.parameters["t_max"]) == (t_min, t_max)
    assert PATH_PROBES[component.behavior_id][0][4] == "tant"


def test_polymer_card_carries_the_sourced_100khz_esr_and_has_the_ac_probe(registry, recipes):
    component = compiled(registry, recipes, "OHM-032").components[0]
    assert component.parameters["esr_max"] == pytest.approx(0.024)
    assert "100 kHz" in component.parameter_evidence["esr_max"]["scope"]
    assert "BEH-CAP-ALPOLY" in AC_PROBES and "BEH-CAP-ALEL" not in AC_PROBES


@pytest.mark.parametrize(("volts", "ambient", "status"), [
    (20, None, "unknown"),        # no declared ambient: the rating holds only inside the category range
    (26, None, "violation"),      # above 25 V at any ambient
    (20, 105, "within_limit"),
    (25, 25, "within_limit"),
    (26, 25, "violation"),
])
def test_rated_voltage_needs_a_declared_ambient_for_a_pass(registry, recipes, volts, ambient, status):
    compilation = compiled(registry, recipes, "OHM-029")
    context = RatingContext(ambient_c=ambient) if ambient is not None else RatingContext()
    row = rows(evaluate_ratings(compilation, result_at(compilation, volts), registry, context))["rated voltage"]
    assert row["status"] == status


def test_ambient_outside_the_category_range_is_a_violation(registry, recipes):
    compilation = compiled(registry, recipes, "OHM-031")
    hot = rows(evaluate_ratings(compilation, result_at(compilation, 10), registry, RatingContext(ambient_c=95)))
    assert hot["ambient within category range"]["status"] == "violation"   # LKG is an 85 C series


def test_reverse_voltage_is_always_a_violation(registry, recipes):
    compilation = compiled(registry, recipes, "OHM-030")
    checks = rows(evaluate_ratings(compilation, result_at(compilation, -0.5), registry, RatingContext(ambient_c=25)))
    assert checks["reverse voltage (not permitted)"]["status"] == "violation"
    forward = rows(evaluate_ratings(compilation, result_at(compilation, 5), registry, RatingContext(ambient_c=25)))
    assert "reverse voltage (not permitted)" not in forward


def test_ac_peak_reverse_swing_and_ripple_rows(registry, recipes):
    compilation = compiled(registry, recipes, "OHM-032", analysis="ac",
                           excitations=[ACExcitation(positive_net="gnd", negative_net="rail", ac_rms=Quantity.amps(1e-3))])
    assert compilation.runnable, compilation.problems
    cool = RatingContext(ambient_c=25)
    ok = rows(evaluate_ratings(compilation, result_at(compilation, 10, ac=1.0, iac=1.0), registry, cool))
    assert ok["peak voltage (DC plus AC peak) at 100000 Hz"]["status"] == "within_limit"
    assert "reverse voltage (not permitted) at 100000 Hz" not in ok
    # The ripple rating is never decided by the card (D067), even far below it.
    assert ok["ripple current at 100000 Hz"]["status"] == "unknown"
    over = rows(evaluate_ratings(compilation, result_at(compilation, 15, ac=1.0), registry, cool))
    assert over["peak voltage (DC plus AC peak) at 100000 Hz"]["status"] == "violation"   # 15 + 1.414 > 16
    swing = rows(evaluate_ratings(compilation, result_at(compilation, 1, ac=1.0), registry, cool))
    assert swing["reverse voltage (not permitted) at 100000 Hz"]["status"] == "violation"  # 1 - 1.414 < 0
