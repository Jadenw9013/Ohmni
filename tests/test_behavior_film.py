"""OHM-037 WIMA MKS 4 film capacitor: sourced binding and rating rows (D059)."""

from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import ACExcitation, BehaviorSelection
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def film(recipes, volts=100.0):
    package = recipes.entries["OHM-037"].package
    return CircuitIR(ir_id="film", name="Film capacitor", components=[
        CircuitComponent(ref="C1", part_id="OHM-037", package=package)], nets=[
        Net(name="rail", kind="power", connections=[PinRef(component="C1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(volts)))),
        Net(name="gnd", kind="ground", connections=[PinRef(component="C1", pin="2")])])


def compiled(registry, recipes, **kwargs):
    return compile_circuit(film(recipes), registry, recipes, {"C1": BehaviorSelection(entry_id="OHM-037")},
                           measure_currents=True, **kwargs)


def result_at(compilation, volts, ac=None, freq=50.0):
    c1 = compilation.components[0]
    node = c1.role_nodes["T1"].lower()
    probes = [p.lower() for p in c1.role_current_probes.values()]
    op = {"node_voltages": {node: {"value": volts, "unit": "V"}},
          "branch_currents": {p: {"value": 0.0, "unit": "A"} for p in probes}}
    result = {"status": "ran", "analysis": "op" if ac is None else "ac", "operating_point": op}
    if ac is not None:
        result["ac"] = {"points": [{"frequency_hz": freq, "node_voltages": {node: [ac, 0.0]},
                                    "branch_currents": {p: [0.0, 0.0] for p in probes}}]}
    return result


def rows(ratings):
    return {r["name"]: r for r in ratings["components"][0]["reference_checks"]}


def test_binding_uses_only_sourced_wima_mks4_facts(registry, recipes):
    component = compiled(registry, recipes).components[0]
    assert component.reference_part.startswith("WIMA MKS4G031003F")
    assert component.parameters["value"] == pytest.approx(1e-7)
    assert component.parameters["vr"] == 400 and component.parameters["vac"] == 200
    assert component.parameters["rleak"] == 3e10
    for name in ("value", "vr", "vac", "derate_pct_per_k", "t_max", "rleak"):
        evidence = component.parameter_evidence[name]
        assert evidence["basis"] == "MFR_DATASHEET"
        assert evidence["sources"] == ["https://www.wima.de/wp-content/uploads/media/WIMA_Main_Catalogue_2026.pdf"]
        assert "MKS4G031003F" in evidence["scope"] or "MKS 4" in evidence["scope"]


@pytest.mark.parametrize(("volts", "ambient", "status"), [
    (190, None, "unknown"),          # no declared ambient: only the full 400 V rating proves anything (D060)
    (300, None, "unknown"),
    (300, 105, "within_limit"),      # 400*(1-0.0125*20) = 300 V at 105 C
    (301, 105, "violation"),
    (350, None, "unknown"),          # within 400 V, above the 125 C derated value: ambient decides
    (350, 25, "within_limit"),
    (410, None, "violation"),
])
def test_dc_rating_is_derated_above_85c_and_ambient_decides_in_between(registry, recipes, volts, ambient, status):
    compilation = compiled(registry, recipes)
    context = RatingContext(ambient_c=ambient) if ambient is not None else RatingContext()
    row = rows(evaluate_ratings(compilation, result_at(compilation, volts), registry, context))[
        "DC voltage (derated above 85 C)"]
    assert row["status"] == status


def test_ac_rule_is_exact_only_at_50_hz(registry, recipes):
    compilation = compiled(registry, recipes, analysis="ac",
                           excitations=[ACExcitation(positive_net="gnd", negative_net="rail", ac_rms=Quantity.amps(1e-3))])
    assert compilation.runnable, compilation.problems
    cool = RatingContext(ambient_c=25)
    ok = rows(evaluate_ratings(compilation, result_at(compilation, 100, ac=150.0), registry, cool))
    # 1.4 * 150 + 100 = 310 <= 400 and 150 <= 200 V rms.
    assert ok["AC voltage rule (1.4 x Urms + UDC) at 50 Hz"]["status"] == "within_limit"
    over = rows(evaluate_ratings(compilation, result_at(compilation, 200, ac=150.0), registry, cool))
    assert over["AC voltage rule (1.4 x Urms + UDC) at 50 Hz"]["status"] == "violation"
    other = rows(evaluate_ratings(compilation, result_at(compilation, 0, ac=150.0, freq=1e3), registry, cool))
    assert other["AC voltage at 1000 Hz"]["status"] == "unknown"
