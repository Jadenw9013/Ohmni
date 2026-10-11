"""Crystal bindings of D073: Kyocera CX3225FB16000D0FZZH1 (OHM-143) and CX2016FB24000D0FZZH1 (OHM-145)."""

import math
from pathlib import Path

import pytest

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, convert_unit, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import ACExcitation, BehaviorSelection
from ohmni.domain.circuit import CircuitComponent, CircuitIR, Net, PinRef
from ohmni.domain.units import Quantity
from tools.behavior_audit.runtime_benches import XTAL_PROBES, _zero_crossing, xtal_expected

ROOT = Path(__file__).resolve().parents[1]
PARTS = {
    "OHM-143": {"part": "CX3225FB16000D0FZZH1", "f": 16e6, "c1": (1.65, 2.47), "c0": (0.67, 0.99), "l1": (38.52, 57.76)},
    "OHM-145": {"part": "CX2016FB24000D0FZZH1", "f": 24e6, "c1": (1.32, 1.98), "c0": (0.42, 0.62), "l1": (21.36, 32.04)},
}


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def compile_crystal(registry, recipes, entry_id, recipe=None, analysis="ac"):
    recipe = recipe or recipes.entries[entry_id]
    if recipe is not recipes.entries[entry_id]:
        recipes = recipes.model_copy(update={"entries": {**recipes.entries, entry_id: recipe}})
    nets = [Net(name=name, kind="ground" if name == "gnd" else "signal",
                connections=[PinRef(component="U1", pin=pin) for pin, role in recipe.terminal_roles.items()
                             if (role == "A") == (name == "drive")]) for name in ("drive", "gnd")]
    circuit = CircuitIR(ir_id=f"d073-{entry_id}", name="D073 crystal", nets=nets,
                        components=[CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)])
    excitation = ACExcitation(positive_net="gnd", negative_net="drive", ac_rms=Quantity(value=1e-4, unit="A"))
    return compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)},
                           analysis=analysis, excitations=[excitation] if analysis == "ac" else [])


@pytest.mark.parametrize("entry_id", sorted(PARTS))
def test_recipe_selects_only_the_kyocera_scoped_facts(registry, recipes, entry_id):
    spec = PARTS[entry_id]
    compiled = compile_crystal(registry, recipes, entry_id)
    assert compiled.runnable, compiled.problems
    component = compiled.components[0]
    params, evidence = component.parameters, component.parameter_evidence
    # The entry still carries the earlier Abracon facts (ESR 70 ohm, CL 18 pF ...); scope_contains keeps them out.
    assert params["R1"] == 50 and params["cl"] == pytest.approx(8e-12) and params["dl_max"] == 100
    assert params["f_nom"] == spec["f"] and (params["top_min"], params["top_max"]) == (-40, 105)
    for name in ("f_nom", "cl", "R1", "c1_min", "c0_max", "l1_max", "dl_max", "top_min"):
        assert spec["part"] in evidence[name]["scope"] and evidence[name]["basis"] == "MFR_DATASHEET"
    assert spec["part"] in recipes.entries[entry_id].reference_part
    assert spec["part"] in evidence["terminal_roles"]["scope"]


@pytest.mark.parametrize("entry_id", sorted(PARTS))
def test_femtofarad_and_millihenry_scaling_is_explicit(registry, recipes, entry_id):
    spec = PARTS[entry_id]
    # convert_unit has no fF or mH entry, so the recipe scales them explicitly and must keep doing so.
    with pytest.raises(ValueError):
        convert_unit(1.0, "fF", "F")
    with pytest.raises(ValueError):
        convert_unit(1.0, "mH", "H")
    params = compile_crystal(registry, recipes, entry_id).components[0].parameters
    assert (params["c1_min"], params["c1_max"]) == spec["c1"]  # still in fF
    assert params["C1"] == pytest.approx(sum(spec["c1"]) / 2 * 1e-15, rel=1e-12)
    assert params["C0"] == pytest.approx(sum(spec["c0"]) / 2 * 1e-12, rel=1e-12)
    fs = 1 / (2 * math.pi * math.sqrt(params["L1"] * params["C1"]))
    fl = fs * math.sqrt(1 + params["C1"] / (params["C0"] + params["cl"]))
    assert fl == pytest.approx(spec["f"], rel=1e-12)
    assert spec["l1"][0] * 1e-3 <= params["L1"] <= spec["l1"][1] * 1e-3


def test_permutation_puts_the_crystal_on_library_pads_two_and_four(registry, recipes):
    for entry_id in PARTS:
        recipe = recipes.entries[entry_id]
        assert recipe.terminal_roles == {"1": "LID2", "2": "A", "3": "LID1", "4": "B"}
        assert recipe.pin_role_fact.permutation_provenance.document == "docs/behavior/KYOCERA-CXFB-PERMUTATION.md"
        identity = recipe.model_copy(update={"pin_role_fact": recipe.pin_role_fact.model_copy(
            update={"manufacturer_to_package_terminal": {"1": "1", "2": "2", "3": "3", "4": "4"}})})
        compiled = compile_crystal(registry, recipes, entry_id, identity)
        assert not compiled.runnable
        assert any("differ from the sourced manufacturer map" in p for p in compiled.problems)


def test_2016_part_is_24_mhz_with_a_sourced_c0_below_the_class_minimum(registry, recipes):
    params = compile_crystal(registry, recipes, "OHM-145").components[0].parameters
    class_min = float(registry.behavior_class("BEH-FREQ-XTAL").canonical_payload["parameters"]["C0"]["min"])
    # D073: the class range is not a compile gate; the exact part's sourced C0 wins for its binding.
    assert params["C0"] == pytest.approx(0.52e-12) and params["C0"] < class_min == pytest.approx(0.8e-12)
    limitations = " ".join(recipes.entries["OHM-145"].limitations)
    assert "24 MHz, not 16 MHz" in limitations and "below the BEH-FREQ-XTAL class parameter minimum" in limitations


def test_probe_expectations_come_from_the_sourced_facts():
    values = {"f_nom": 16e6, "C1": 2.06e-15, "C0": 0.83e-12, "cl": 8e-12, "R1": 50.0}
    expected = xtal_expected(values)
    assert expected["load_resonance_hz"] == 16e6 and expected["zmin_ohm"] == 50.0
    assert expected["series_resonance_hz"] == pytest.approx(16e6 / math.sqrt(1 + 2.06e-15 / 8.83e-12))
    assert _zero_crossing(0.0, -1.0, 10.0, 1.0) == 5.0
    assert _zero_crossing(0.0, 1.0, 10.0, 2.0) is None and _zero_crossing(0.0, 1.0, 10.0, 1.0) is None
    assert set(XTAL_PROBES) == {"BEH-FREQ-XTAL"}


def _ac_ratings(registry, compiled, frequency, current, ambient=None):
    """Synthetic AC result: the exact BVD impedance of the bound card driven by `current` at `frequency`."""
    component = compiled.components[0]
    p = component.parameters
    w = 2 * math.pi * frequency
    zm = complex(p["R1"], w * p["L1"] - 1 / (w * p["C1"]))
    z = 1 / (1 / zm + 1j * w * p["C0"])
    v = current * z
    node = component.role_nodes["A"].lower()
    result = {"status": "ran", "analysis": "ac",
              "operating_point": {"node_voltages": {node: {"value": 0.0, "unit": "V"}}, "branch_currents": {}},
              "ac": {"points": [{"frequency_hz": frequency, "node_voltages": {node: [v.real, v.imag]},
                                 "branch_currents": {}}]}}
    ratings = evaluate_ratings(compiled, result, registry, RatingContext(ambient_c=ambient))
    rows = {r["name"]: r for r in ratings["components"][0]["reference_checks"]}
    return rows, ratings["components"][0], current ** 2 * abs(z / zm) ** 2 * p["R1"] * 1e6


def test_drive_level_is_r1_times_the_motional_current_squared(registry, recipes):
    compiled = compile_crystal(registry, recipes, "OHM-143")
    fs = 1 / (2 * math.pi * math.sqrt(compiled.components[0].parameters["L1"] * compiled.components[0].parameters["C1"]))
    rows, component, expected_uw = _ac_ratings(registry, compiled, fs, 1e-3, ambient=25)
    row = rows[f"drive level (R1*|I_motional|^2) at {fs:.12g} Hz"]
    assert row["status"] == "within_limit" and expected_uw == pytest.approx(50.0, rel=1e-3)
    assert component["observations"][f"dl_uw_{fs:.12g}".replace(".", "p").replace("+", "")] == pytest.approx(expected_uw)
    assert rows["operating temperature"]["status"] == "within_limit"
    # gain margin needs an oscillator loop: the class row stays unknown, so the part never passes overall.
    assert component["status"] == "unknown"
    rows, component, expected_uw = _ac_ratings(registry, compiled, fs, 2e-3)
    assert rows[f"drive level (R1*|I_motional|^2) at {fs:.12g} Hz"]["status"] == "violation"
    assert expected_uw == pytest.approx(200.0, rel=1e-3) and component["status"] == "violation"
    assert rows["operating temperature"]["status"] == "unknown"


def test_operating_point_leaves_drive_level_unknown_and_checks_the_sourced_range(registry, recipes):
    compiled = compile_crystal(registry, recipes, "OHM-145", analysis="op")
    assert not compiled.runnable  # no source: a crystal alone has no DC operating point to run
    compiled = compile_crystal(registry, recipes, "OHM-145")
    component = compiled.components[0]
    node = component.role_nodes["A"].lower()
    op = {"status": "ran", "analysis": "op",
          "operating_point": {"node_voltages": {node: {"value": 0.0, "unit": "V"}}, "branch_currents": {}}}
    for ambient, status in ((25, "within_limit"), (110, "violation"), (-45, "violation")):
        ratings = evaluate_ratings(compiled, op, registry, RatingContext(ambient_c=ambient))
        rows = {r["name"]: r for r in ratings["components"][0]["reference_checks"]}
        assert rows["operating temperature"]["status"] == status
        assert rows["drive level"]["status"] == "unknown" and "AC run" in rows["drive level"]["reason"]


@pytest.mark.parametrize("entry_id", sorted(PARTS))
def test_runtime_receipts_validate(entry_id):
    from tools.behavior_audit.audit import BehaviorAudit
    from tools.behavior_audit.runtime_benches import runtime_receipt_errors

    assert runtime_receipt_errors(BehaviorAudit(ROOT), entry_id) == []


def test_reference_example_runs_as_ac_at_the_probe_frequencies(registry, recipes):
    import json

    from ohmni.behavior.examples import compile_reference

    data = json.loads((ROOT / "src/ohmni/behavior/reference-circuits.json").read_text(encoding="utf-8"))
    for entry_id in PARTS:
        row = data["examples"][entry_id]
        assert row["analysis"] == "ac" and len(row["options"]["ac_points_hz"]) == 5
        compiled, options = compile_reference(row, registry, recipes)
        assert compiled.runnable and options["analysis"] == "ac"
        assert options["ac_points_hz"] == row["options"]["ac_points_hz"]
