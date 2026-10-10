import math
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


def _single(registry, recipes, entry_id, pin_nets):
    from ohmni.domain.circuit import CircuitComponent, CircuitIR, Net, PinRef

    nets = [Net(name=name, kind="ground" if name == "return" else "signal",
                connections=[PinRef(component="U1", pin=pin) for pin in pins]) for name, pins in pin_nets.items()]
    circuit = CircuitIR(ir_id="t", name="t", nets=nets,
                        components=[CircuitComponent(ref="U1", part_id=entry_id, package=recipes.entries[entry_id].package)])
    from ohmni.behavior.runtime_models import DCExcitation
    from ohmni.domain.units import Quantity

    excitation = DCExcitation(positive_net="return", negative_net="a", value=Quantity(value=0.01, unit="A"))
    result = compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)},
                             excitations=[excitation], measure_currents=True)
    assert result.runnable, result.problems
    return result


def _point(component, volts, amps):
    return {"status": "ran", "analysis": "op", "operating_point": {
        "node_voltages": {component.role_nodes[r]: {"value": v, "unit": "V"} for r, v in volts.items()},
        "branch_currents": {component.role_current_probes[r]: {"value": i, "unit": "A"} for r, i in amps.items()}}}


def _checks(report):
    return {x["name"]: x for x in report["components"][0]["reference_checks"]}


def test_series_dual_diode_uses_double_loaded_limit_only_when_both_conduct():
    registry = BehaviorRegistry(repo_root=ROOT)
    recipes = load_recipes(registry, ROOT)
    c = _single(registry, recipes, "OHM-070", {"a": ["1"], "return": ["2"], "m": ["3"]})
    comp = c.components[0]
    context = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    # Both junctions forward at 150 mA: above the double-loaded limit, power/thermal stay unknown.
    both = evaluate_ratings(c, _point(comp, {"A1": 1.8, "K1A2": 0.9, "K2": 0},
                                      {"A1": 0.15, "K1A2": 0, "K2": -0.15}), registry, context)
    checks = _checks(both)
    assert checks["forward current D1"]["status"] == "violation"
    assert checks["total power"]["status"] == "unknown"
    assert "one diode loaded" in checks["total power"]["reason"]
    # Only D1 conducting at 150 mA: within the single-loaded limit.
    single = evaluate_ratings(c, _point(comp, {"A1": 0.9, "K1A2": 0, "K2": 0},
                                        {"A1": 0.15, "K1A2": -0.15, "K2": 0}), registry, context)
    checks = _checks(single)
    assert checks["forward current D1"]["status"] == "within_limit"
    assert checks["total power"]["status"] == "within_limit"


def test_power_led_junction_check_uses_solder_point_temperature():
    registry = BehaviorRegistry(repo_root=ROOT)
    recipes = load_recipes(registry, ROOT)
    c = _single(registry, recipes, "OHM-085", {"a": ["2"], "return": ["1"], "th": ["3"]})
    comp = c.components[0]
    point = _point(comp, {"A": 2.9, "K": 0, "TH": 0}, {"A": 0.35, "K": -0.35})
    name = "junction temperature (all electrical power as heat)"
    missing = _checks(evaluate_ratings(c, point, registry, RatingContext(thermal_scope_confirmed=True)))
    assert missing[name]["status"] == "unknown"
    cool = _checks(evaluate_ratings(c, point, registry, RatingContext(case_c=85, thermal_scope_confirmed=True)))
    assert cool[name]["status"] == "within_limit"
    hot = _checks(evaluate_ratings(c, point, registry, RatingContext(case_c=148, thermal_scope_confirmed=True)))
    assert hot[name]["status"] == "violation"


def _each_pin(registry, recipes, entry_id):
    recipe = recipes.entries[entry_id]
    isolated = set(recipe.required_isolated_roles or [])
    driven = [pin for pin, role in recipe.terminal_roles.items() if role not in isolated][:2]
    rest = [pin for pin in recipe.terminal_roles if pin not in driven]
    nets = {"a": [driven[0]], "return": [driven[1]], **{f"n{k}": [pin] for k, pin in enumerate(rest)}}
    return _single(registry, recipes, entry_id, nets)


def _report(entry_id, volts, amps=None, context=None):
    registry = BehaviorRegistry(repo_root=ROOT)
    recipes = load_recipes(registry, ROOT)
    c = _each_pin(registry, recipes, entry_id)
    comp = c.components[0]
    amps = {r: i for r, i in (amps or {}).items() if r in comp.role_current_probes}
    volts = {r: volts.get(r, 0.0) for r in comp.role_nodes}
    point = _point(comp, volts, amps)
    return _checks(evaluate_ratings(c, point, registry, context or RatingContext(ambient_c=25, thermal_scope_confirmed=True)))


def test_capacitor_voltage_ratings_flag_overvoltage_and_reverse_bias():
    assert _report("OHM-024", {"T1": 36})["rated DC voltage"]["status"] == "violation"
    assert _report("OHM-024", {"T1": 12})["rated DC voltage"]["status"] == "within_limit"
    tant = _report("OHM-033", {"A": 12})
    assert tant["rated voltage"]["status"] == "within_limit"
    assert tant["application voltage (manufacturer MnO2 derating recommendation)"]["status"] == "unknown"
    assert _report("OHM-033", {"A": 17})["rated voltage"]["status"] == "violation"
    assert _report("OHM-033", {"K": 3})["reverse voltage"]["status"] == "violation"
    assert _report("OHM-033", {"K": 0.5})["reverse voltage"]["status"] == "unknown"  # transient-only limit
    hot = RatingContext(ambient_c=75, thermal_scope_confirmed=True)
    assert _report("OHM-040", {"P": 2.5}, context=hot)["rated voltage at ambient"]["status"] == "violation"
    assert _report("OHM-040", {"P": 2.5})["rated voltage at ambient"]["status"] == "within_limit"
    assert _report("OHM-040", {"N": 1})["polarity"]["status"] == "violation"
    assert _report("OHM-040", {"P": 2.5}, context=RatingContext())["rated voltage at ambient"]["status"] == "unknown"


def test_connector_checks_cover_every_contact_and_typical_column_voltages():
    usb = _report("OHM-163", {"P1": 5}, {"P1": 1.5, "M1": -1.5})
    assert usb["contact current P1"]["status"] == "violation"
    assert usb["contact-to-contact voltage"]["status"] == "within_limit"
    assert _report("OHM-163", {"P1": 31})["contact-to-contact voltage"]["status"] == "violation"
    # OHM-171 publishes its voltage in a typical column, used as the rating by owner decision (D053).
    assert _report("OHM-171", {"TIP": 5})["contact-to-contact voltage"]["status"] == "within_limit"
    assert _report("OHM-171", {"TIP": 13})["contact-to-contact voltage"]["status"] == "violation"
    # Phoenix nominal current only holds below an unbound derating knee.
    assert _report("OHM-161", {}, {"P1": 5, "W1": -5})["contact current P1"]["status"] == "unknown"
    assert _report("OHM-161", {}, {"P1": 13, "W1": -13})["contact current P1"]["status"] == "violation"


def test_magnetics_and_pot_ratings():
    assert _report("OHM-050", {}, {"A1": 1.0, "A2": -1.0})["winding A current"]["status"] == "violation"
    assert _report("OHM-050", {"A1": 81})["line voltage"]["status"] == "violation"
    assert _report("OHM-052", {}, {"P_A": 0.02, "P_B": -0.02})["primary DC unbalance current"]["status"] == "violation"
    assert _report("OHM-018", {"A": 301})["track voltage"]["status"] == "violation"
    assert _report("OHM-018", {"A": 100}, {"A": 0.01, "B": -0.01})["track power"]["status"] == "violation"
    assert _report("OHM-018", {"A": 10}, {"A": 0.001, "B": -0.001})["track power"]["status"] == "within_limit"


def test_mains_choke_line_voltage_uses_its_ac_rating_conservatively():
    assert _report("OHM-051", {"A1": 260})["line voltage"]["status"] == "violation"
    assert _report("OHM-051", {"A1": 230})["line voltage"]["status"] == "within_limit"


def _tran_result(component, waveforms, *, cycles_time=1e-3, samples=401):
    """Synthetic ngspice print table: waveforms maps ('v', role) or ('i', role) to f(t)."""
    import math  # noqa: F401  (waveform lambdas use it)

    columns = []
    for role, node in component.role_nodes.items():
        if node != "0":
            columns.append((f"v({node})", waveforms.get(("v", role), lambda t: 0.0)))
    for role, probe in component.role_current_probes.items():
        columns.append((f"i({probe})", waveforms.get(("i", role), lambda t: 0.0)))
    lines = ["Index   time            " + "  ".join(name for name, _ in columns)]
    for k in range(samples):
        t = cycles_time * k / (samples - 1)
        lines.append("\t".join([str(k), f"{t:.15e}", *(f"{f(t):.15e}" for _, f in columns)]))
    return {"status": "ran", "analysis": "tran", "stdout": "\n".join(lines) + "\n"}


def _tran_checks(entry_id, pin_nets, waveforms, context, **kw):
    registry = BehaviorRegistry(repo_root=ROOT)
    recipes = load_recipes(registry, ROOT)
    c = _single(registry, recipes, entry_id, pin_nets)
    report = evaluate_ratings(c, _tran_result(c.components[0], waveforms, **kw), registry, context)
    return report["components"][0], _checks(report)


def test_transient_window_statistics():
    from ohmni.behavior.ratings import TransientWindow

    t = [k / 1000 for k in range(1001)]
    sine = [math.sin(2 * math.pi * 10 * x) for x in t]
    w = TransientWindow(t, {}, {})
    assert abs(w.mean(sine)) < 1e-3
    assert abs(w.rms(sine) - 1 / math.sqrt(2)) < 1e-3
    assert abs(w.ac_rms([2 + x for x in sine]) - 1 / math.sqrt(2)) < 1e-3
    assert abs(w.frequency(sine) - 10) < 0.2


def test_tantalum_ripple_and_transient_reverse_limits():
    hot = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    ripple = lambda t: 0.25 * math.sin(2 * math.pi * 10e3 * t)
    comp, checks = _tran_checks("OHM-033", {"a": ["1"], "return": ["2"]},
                                {("v", "A"): lambda t: 5.0, ("i", "A"): ripple, ("i", "K"): lambda t: -ripple(t)}, hot)
    assert checks["ripple current"]["status"] == "violation"  # 0.177 A rms at 10 kHz > 0.158 A at 100 kHz
    assert comp["basis"].startswith("transient")
    small = lambda t: 0.05 * math.sin(2 * math.pi * 10e3 * t)
    _, checks = _tran_checks("OHM-033", {"a": ["1"], "return": ["2"]},
                             {("v", "A"): lambda t: 5.0, ("i", "A"): small, ("i", "K"): lambda t: -small(t)}, hot)
    assert checks["ripple current"]["status"] == "unknown"  # below 100 kHz a lower, unbound limit applies
    # A brief reverse excursion within the 25 C transient limit (2.4 V) passes; beyond it fails.
    dip = lambda depth: (lambda t: 5.0 - depth * (1 if 4e-4 < t < 5e-4 else 0) - 5.0 * (1 if 4e-4 < t < 5e-4 else 0))
    _, checks = _tran_checks("OHM-033", {"a": ["1"], "return": ["2"]}, {("v", "A"): dip(2.0)}, hot)
    assert checks["peak reverse voltage (transient limit)"]["status"] == "within_limit"
    _, checks = _tran_checks("OHM-033", {"a": ["1"], "return": ["2"]}, {("v", "A"): dip(3.0)}, hot)
    assert checks["peak reverse voltage (transient limit)"]["status"] == "violation"


def test_peaks_are_checked_even_when_the_average_is_safe():
    ctx = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    # Ceramic 35 V part with a 0 V average but 40 V peaks.
    _, checks = _tran_checks("OHM-024", {"a": ["1"], "return": ["2"]},
                             {("v", "T1"): lambda t: 40 * math.sin(2 * math.pi * 1e3 * t)}, ctx)
    assert checks["rated DC voltage (time average)"]["status"] == "within_limit"
    assert checks["peak voltage"]["status"] == "violation"
    # EDLC peak current beyond its 5.09 A table value.
    _, checks = _tran_checks("OHM-040", {"a": ["1"], "return": ["2"]},
                             {("v", "P"): lambda t: 1.0, ("i", "P"): lambda t: 8 * math.sin(2 * math.pi * 1e3 * t),
                              ("i", "N"): lambda t: -8 * math.sin(2 * math.pi * 1e3 * t)}, ctx)
    assert checks["peak current"]["status"] == "violation"


def test_schottky_surge_average_and_leakage_runaway():
    ctx = RatingContext(ambient_c=25, thermal_scope_confirmed=True)
    half = lambda t: max(0.0, 4 * math.sin(2 * math.pi * 1e3 * t))
    _, checks = _tran_checks("OHM-066", {"a": ["2"], "return": ["1"]},
                             {("v", "A"): lambda t: 0.4 if half(t) else 0.0, ("i", "A"): half,
                              ("i", "K"): lambda t: -half(t)}, ctx)
    assert checks["average forward current"]["status"] == "within_limit"  # about 1.27 A average
    assert checks["peak forward current against the surge rating"]["status"] == "unknown"
    # Steady 40 V reverse: stable at 25 C ambient, thermal runaway at 100 C.
    for ambient, expected in ((25, "within_limit"), (100, "violation")):
        assert _report("OHM-066", {"K": 40}, {}, RatingContext(ambient_c=ambient, thermal_scope_confirmed=True))[
            "leakage thermal stability"]["status"] == expected
