"""AC analysis: explicit RMS excitations, marker-attributed phasors, exact ripple checks, honest linearity."""

import math
import shutil
from pathlib import Path

import pytest

from ohmni.application.component_behavior import ComponentBehaviorService, DesignRunRequest
from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, circuit_is_linear, evaluate_ratings
from ohmni.behavior.runtime_models import ACExcitation, BehaviorSelection, DCExcitation
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter, ac_deck, parse_ac

ROOT = Path(__file__).resolve().parents[1]
live_only = pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice 42 is not installed")


@pytest.fixture(scope="module")
def registry():
    return BehaviorRegistry(repo_root=ROOT)


@pytest.fixture(scope="module")
def recipes(registry):
    return load_recipes(registry, ROOT)


def tantalum(recipes, extra=()):
    package = recipes.entries["OHM-033"].package
    return CircuitIR(ir_id="tant", name="Tantalum ripple", components=[
        CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR", package="0603", value=Quantity.ohms(1000)),
        CircuitComponent(ref="C1", part_id="OHM-033", package=package), *extra,
    ], nets=[
        Net(name="vin", kind="power", connections=[PinRef(component="R1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(5)))),
        Net(name="rail", connections=[PinRef(component="R1", pin="2"), PinRef(component="C1", pin="1")]),
        Net(name="gnd", kind="ground", connections=[PinRef(component="C1", pin="2")]),
    ])


def ripple(amps):
    return ACExcitation(positive_net="gnd", negative_net="rail", ac_rms=Quantity.amps(amps))


def test_ac_excitation_is_explicit_rms_and_only_for_ac(registry, recipes):
    with pytest.raises(ValueError):
        ACExcitation(positive_net="a", negative_net="b", ac_rms=Quantity.amps(0))
    with pytest.raises(ValueError):
        ACExcitation(positive_net="a", negative_net="b", ac_rms=Quantity.amps(1), dc=Quantity.volts(1))
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    ok = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac", excitations=[ripple(0.1)])
    assert ok.runnable and "Iexcitation1 0 n2 DC 0 AC 0.10000000000000001" in ok.netlist
    op = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="op", excitations=[ripple(0.1)])
    assert not op.runnable and any("AC excitations" in p for p in op.problems)
    bare = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac")
    assert any("needs at least one explicit AC excitation" in p for p in bare.problems)
    dc = DCExcitation(positive_net="gnd", negative_net="rail", value=Quantity.amps(0.01))
    assert not compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1), dc]).runnable


def test_ac_deck_marks_every_point_and_refuses_unsafe_requests():
    deck = ac_deck("t\nR1 a 0 1k\n.end\n", nodes=["a"], currents=["vp"], points_hz=[100e3],
                   sweep=(10.0, 1e6, 5), sweep_nodes=["a"])
    assert ("echo OHMNI_AC_POINT 0\nac lin 1 100000 100000\n"
            "print real(frequency) real(v(a)) imag(v(a)) real(i(vp)) imag(i(vp))") in deck
    assert deck.rstrip().endswith(".endc\n.end".rstrip()) and "ac dec 5 10 1000000" in deck
    for bad in ([], [0.0], [math.inf], [1.0] * 9):
        with pytest.raises(ValueError):
            ac_deck("t\n.end\n", nodes=[], currents=[], points_hz=bad)
    with pytest.raises(ValueError):
        ac_deck("t\n.ac lin 1 1 1\n.end\n", nodes=[], currents=[], points_hz=[1.0])
    with pytest.raises(ValueError):
        ac_deck("t\n.end\n", nodes=["a"], currents=[], points_hz=[1.0], sweep=(1.0, 1e9, 50), sweep_nodes=["a"])


def test_parse_ac_attributes_values_by_marker_and_joins_column_groups():
    lines = [
        "OHMNI_AC_OP", "v(a) = 5.0", "i(vp) = -1e-3",
        "OHMNI_AC_POINT 1", "real(frequency) = 1000.0", "real(v(a)) = 1.0", "imag(v(a)) = 2.0",
        "OHMNI_AC_POINT 0", "real(frequency) = 100.0", "real(v(a)) = 3.0",  # no imaginary part: dropped
        "OHMNI_AC_SWEEP",
        "Index   frequency       vm(a)           vp(a)",
        "0\t1.0e+01\t1.0\t0.0", "1\t1.0e+02\t0.5\t-1.0",
        "Index   frequency       vm(b)           vp(b)",
        "0\t1.0e+01\t2.0\t0.0", "1\t1.0e+02\t1.5\t0.5",
    ]
    out = "\n".join(lines)
    parsed = parse_ac(out, [100.0, 1000.0])
    assert parsed["operating_point"].node_voltages["a"].value == 5.0
    assert [p["frequency_hz"] for p in parsed["points"]] == [1000.0]
    assert parsed["points"][0]["node_voltages"] == {"a": [1.0, 2.0]}
    series = {s["name"]: s for s in parsed["sweep"]["series"]}
    assert series["v(b)"]["magnitude"] == [2.0, 1.5]
    assert series["v(a)"]["phase_deg"][1] == pytest.approx(math.degrees(-1.0))


def test_linearity_is_read_from_the_netlist_not_the_class():
    assert circuit_is_linear("t\nR1 a b 1k\nC1 b 0 1u\nvprobe a x 0\n.model X D\n.end")
    assert not circuit_is_linear("t\nR1 a b 1k\nD1 b 0 DX\n.end")
    assert not circuit_is_linear("t\nLnl x b L='L0*(1/cosh(i(Lnl)/ia))'\n.end")
    assert not circuit_is_linear("")


def fake_result(compilation, i_rms, freq=100e3, v_ac=0.01):
    c1 = next(c for c in compilation.components if c.ref == "C1")
    r1 = next(c for c in compilation.components if c.ref == "R1")
    probe_c, probe_r = c1.role_current_probes["A"].lower(), r1.role_current_probes["A"].lower()
    rail, vin = c1.role_nodes["A"].lower(), r1.role_nodes["A"].lower()
    k_probe = c1.role_current_probes["K"].lower()
    a_probe_r = r1.role_current_probes["B"].lower()
    op = {"node_voltages": {rail: {"value": 5.0, "unit": "V"}, vin: {"value": 5.0, "unit": "V"}},
          "branch_currents": {p: {"value": 0.0, "unit": "A"} for p in (probe_c, probe_r, k_probe, a_probe_r)}}
    point = {"frequency_hz": freq, "node_voltages": {rail: [v_ac, 0.0], vin: [0.0, 0.0]},
             "branch_currents": {probe_c: [i_rms, 0.0], k_probe: [-i_rms, 0.0],
                                 probe_r: [0.0, 0.0], a_probe_r: [0.0, 0.0]}}
    return {"status": "ran", "analysis": "ac", "operating_point": op, "ac": {"points": [point]}}


def rows(ratings, ref="C1"):
    return {r["name"]: r for c in ratings["components"] if c["ref"] == ref for r in c["reference_checks"]}


def test_tantalum_ripple_is_exact_only_at_the_rating_frequency_and_temperature(registry, recipes):
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    compiled = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1)], measure_currents=True)
    cool = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    # The card carries the maximum ESR (D058): at the rating conditions the real current is at least the simulated
    # one, so these rows can prove a violation but never a pass (D061).
    within = rows(evaluate_ratings(compiled, fake_result(compiled, 0.150), registry, cool))
    assert within["ripple current (rating frequency) at 100000 Hz"]["status"] == "unknown"
    assert within["ESR heating with the maximum 100 kHz ESR at 100000 Hz"]["status"] == "unknown"
    over = rows(evaluate_ratings(compiled, fake_result(compiled, 0.170), registry, cool))
    assert over["ripple current (rating frequency) at 100000 Hz"]["status"] == "violation"
    # 0.170^2 * 3 ohm = 86.7 mW > 75 mW: the same sourced limit, seen as ESR heating.
    assert over["ESR heating with the maximum 100 kHz ESR at 100000 Hz"]["status"] == "violation"
    warm = rows(evaluate_ratings(compiled, fake_result(compiled, 0.150), registry,
                                 RatingContext(ambient_c=60, thermal_scope_confirmed=True)))
    assert warm["ripple current (rating frequency) at 100000 Hz"]["status"] == "unknown"
    for amps in (0.150, 0.170):
        low = rows(evaluate_ratings(compiled, fake_result(compiled, amps, freq=10e3), registry, cool))
        assert low["ripple current at 10000 Hz"]["status"] == "unknown"
    high = rows(evaluate_ratings(compiled, fake_result(compiled, 0.010, freq=1e6), registry, cool))
    assert high["ripple current at 1e+06 Hz"]["status"] == "unknown"


def test_nonlinear_circuit_never_proves_an_ac_result(registry, recipes, monkeypatch):
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    compiled = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1)], measure_currents=True)
    nonlinear = compiled.model_copy(update={"netlist": compiled.netlist.replace(".end", "D9 n1 0 DX\n.end")})
    cool = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    for amps in (0.150, 0.170):
        result = rows(evaluate_ratings(nonlinear, fake_result(nonlinear, amps), registry, cool))
        row = result["ripple current (rating frequency) at 100000 Hz"]
        assert row["status"] == "unknown"
    assert "linearization" in row["reason"]  # the computed violation at 0.170 A is downgraded
    # The operating-point rows of the same run are unaffected.
    assert result["rated voltage"]["status"] == "within_limit"


@pytest.mark.integration
@live_only
def test_design_ac_run_checks_ripple_against_the_sourced_rating(tmp_path):
    service = ComponentBehaviorService(ROOT, tmp_path, adapter=NgspiceAdapter())
    recipes = service.recipes

    def run(amps):
        return service.run_design(DesignRunRequest(
            circuit=tantalum(recipes), selections={"C1": {"entry_id": "OHM-033"}}, analysis="ac",
            excitations=[ripple(amps)], ac_points_hz=[1e5], rating_context={"ambient_c": 25, "thermal_scope_confirmed": True},
            ac_sweep={"start_hz": 100, "stop_hz": 1e6, "points_per_decade": 2}))

    ok, hot = run(0.1), run(0.2)
    assert ok["status"] == hot["status"] == "ran"
    assert rows(ok["ratings"])["ripple current (rating frequency) at 100000 Hz"]["status"] == "unknown"
    assert rows(hot["ratings"])["ripple current (rating frequency) at 100000 Hz"]["status"] == "violation"
    assert hot["rating_status"] == "violation"
    names = {s["name"] for s in ok["ac"]["sweep"]["series"]}
    assert names == {"rail", "vin"} and len(ok["ac"]["sweep"]["frequency_hz"]) == 9
    # The bound card (D058) in parallel with the 1 kohm feed (the ideal DC source is an AC short):
    # |V| = I * |Zc || 1k| with Zc = ESR + 1/(j w C) and ESR the sourced 3 ohm maximum.
    c1 = next(c for c in ok["components"] if c["ref"] == "C1")
    assert c1["entry_id"] == "OHM-033"
    point = ok["ac"]["points"][0]
    node = next(n for n, v in point["node_voltages"].items() if abs(complex(*v)) > 0)
    zc = 3.0 + 1 / (1j * 2 * math.pi * 1e5 * 10e-6)
    expected = 0.1 * abs(zc * 1000 / (zc + 1000))
    assert abs(complex(*point["node_voltages"][node])) == pytest.approx(expected, rel=2e-3)



def test_parse_ac_refuses_a_point_whose_solved_frequency_or_values_do_not_match():
    lines = ["OHMNI_AC_OP", "v(a) = 5.0",
             # A failed solve prints the previous plot: its frequency gives it away.
             "OHMNI_AC_POINT 0", "real(frequency) = 1000.0", "real(v(a)) = 1.0", "imag(v(a)) = 2.0",
             "OHMNI_AC_POINT 1", "real(frequency) = 1000.0", "real(v(a)) = 1.0", "imag(v(a)) = 2.0",
             "real(v(a)) = 9.0",
             "OHMNI_AC_POINT 2", "real(v(a)) = 1.0", "imag(v(a)) = 2.0"]
    assert parse_ac("\n".join(lines), [100.0, 1000.0, 10.0])["points"] == []


def test_linearity_reads_continuations_poly_and_refuses_unscanned_files():
    assert not circuit_is_linear("t\nL1 a b\n+ L='1u*(1+i(L1))'\n.end")
    assert not circuit_is_linear("t\nE1 a 0 POLY(1) b 0 0 1 0.5\n.end")
    assert not circuit_is_linear("t\n.include models.lib\nR1 a 0 1k\n.end")
    assert circuit_is_linear("t\nE1 a 0 b 0 2\nR1 a 0 1k\n.end")


def test_missing_operating_value_never_becomes_zero(registry, recipes):
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    compiled = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1)], measure_currents=True)
    result = fake_result(compiled, 0.150)
    rail = next(c for c in compiled.components if c.ref == "C1").role_nodes["A"].lower()
    del result["operating_point"]["node_voltages"][rail]
    ratings = evaluate_ratings(compiled, result, registry, RatingContext(ambient_c=25, thermal_scope_confirmed=True))
    c1 = rows(ratings)
    assert c1["AC checks"]["status"] == "unknown" and "DC part" in c1["AC checks"]["reason"]
    assert not any(name.endswith("at 100000 Hz") for name in c1)


def test_a_part_without_an_ac_translation_cannot_pass_an_ac_run(registry, recipes):
    """A resistor without its bound limits gets no AC row: the explicit unknown row keeps it from passing."""
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    compiled = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1)], measure_currents=True)
    r1 = next(c for c in compiled.components if c.ref == "R1")
    stripped = r1.model_copy(update={"behavior_id": "BEH-LED-INDICATOR"})
    compiled = compiled.model_copy(update={"components": [stripped if c.ref == "R1" else c for c in compiled.components]})
    ratings = evaluate_ratings(compiled, fake_result(compiled, 0.150), registry,
                               RatingContext(ambient_c=25, thermal_scope_confirmed=True))
    row = rows(ratings, "R1")["AC swing at 100000 Hz"]
    assert row["status"] == "unknown"
    assert next(c for c in ratings["components"] if c["ref"] == "R1")["status"] == "unknown"


def test_tantalum_ripple_needs_thermal_scope_and_an_ambient_for_its_rating(registry, recipes):
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    compiled = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1)], measure_currents=True)
    unconfirmed = rows(evaluate_ratings(compiled, fake_result(compiled, 0.150), registry, RatingContext(ambient_c=25)))
    assert unconfirmed["ripple current (rating frequency) at 100000 Hz"]["status"] == "unknown"
    no_ambient = rows(evaluate_ratings(compiled, fake_result(compiled, 0.150), registry, RatingContext()))
    assert no_ambient["rated voltage"]["status"] == "unknown"
    assert no_ambient["peak forward voltage (DC plus AC peak) at 100000 Hz"]["status"] == "unknown"
    over = rows(evaluate_ratings(compiled, fake_result(compiled, 0.170), registry, RatingContext()))
    assert over["ripple current (rating frequency) at 100000 Hz"]["status"] == "violation", \
        "above the 25 C rating the ripple is over the limit at any ambient"


def test_ripple_conditions_come_from_the_record_scope(registry, recipes):
    choice = {"C1": BehaviorSelection(entry_id="OHM-033")}
    compiled = compile_circuit(tantalum(recipes), registry, recipes, choice, analysis="ac",
                               excitations=[ripple(0.1)], measure_currents=True)
    c1 = next(c for c in compiled.components if c.ref == "C1")
    evidence = dict(c1.parameter_evidence, irip_max=dict(c1.parameter_evidence["irip_max"], scope="KEMET T491"))
    changed = compiled.model_copy(update={"components": [
        c1.model_copy(update={"parameter_evidence": evidence}) if c.ref == "C1" else c for c in compiled.components]})
    cool = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    row = rows(evaluate_ratings(changed, fake_result(changed, 0.150), registry, cool))["ripple current at 100000 Hz"]
    assert row["status"] == "unknown" and "not stated in its source scope" in row["reason"]


@pytest.mark.parametrize("entry_id", ["OHM-033", "OHM-034", "OHM-035", "OHM-036"])
def test_tantalum_cards_carry_the_sourced_maximum_esr_in_series(entry_id, registry, recipes):
    """D058: Resr -> (Cb || Rlk), the class card topology, with ESR = the sourced 100 kHz maximum."""
    recipe = recipes.entries[entry_id]
    circuit = CircuitIR(ir_id="t", name="t", components=[
        CircuitComponent(ref="C1", part_id=entry_id, package=recipe.package)], nets=[
        Net(name="a", kind="power", connections=[PinRef(component="C1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(5)))),
        Net(name="g", kind="ground", connections=[PinRef(component="C1", pin="2")])])
    compiled = compile_circuit(circuit, registry, recipes, {"C1": BehaviorSelection(entry_id=entry_id)})
    component = compiled.components[0]
    esr = component.parameters["esr_max"]
    assert "100 kHz" in component.parameter_evidence["esr_max"]["scope"]
    lines = compiled.netlist.splitlines()
    assert f"Rc1_esr n1 c1_cb {esr:.17g}" in lines
    assert any(line.startswith("Cc1 c1_cb 0 ") for line in lines)
    assert any(line.startswith("Rc1_lk c1_cb 0 ") for line in lines)
    assert circuit_is_linear(compiled.netlist)
