"""Runtime checks for parts bound to a manufacturer's own simulation model (D074).

Each check is a small application circuit at a condition the part's datasheet states, built from bound
OHMNI parts (resistors, capacitor, inductor) and ideal test sources, and compared with datasheet
intervals. A vendor model is a typical model, so a check compares it with the datasheet's typical-to-
maximum (or minimum-to-maximum) interval, never with a fitted single value.
"""

from __future__ import annotations

import json
import re
from itertools import pairwise

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import _facts, compile_circuit, load_recipes
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation, IdealTestInductor
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point, parse_transient

from .audit import _atomic_json, _atomic_text, _now, _sha_bytes

VENDOR_IC_CLASSES = {"BEH-PWR-LOADSWITCH", "BEH-REG-LINEAR", "BEH-REG-BUCK-DCS"}
# The switching model needs about 2.5 min of ngspice CPU for its 300 us start-up.
VENDOR_TIMEOUT_SECONDS = 900
RESISTOR = ("OHM-004", "0603")
LOAD = ("OHM-012", "Cement")  # 5 W cement resistor: the test loads stay far inside its power rating
OUTPUT_CAP = "OHM-026"  # Murata GRM32ER71E226KE15, 22 uF


def is_vendor_ic(recipe):
    return recipe.vendor_model is not None and recipe.behavior_id in VENDOR_IC_CLASSES


def printed_lower_edge(value):
    """The lowest value a datasheet typical printed as ``value`` can stand for (half its last digit)."""
    text = format(float(value), "g")
    decimals = len(text.split(".")[1]) if "." in text else 0
    return float(value) - 0.5 * 10 ** -decimals


def _fact(registry, entry_id, field, scope=None):
    rows = [f for f in registry.entry(entry_id).research.field_updates
            if f.field == field and (scope is None or scope in f.scope)]
    if len(rows) != 1 or rows[0].basis in {"ASSUMPTION", "RESEARCH_REQUIRED"}:
        raise ValueError(f"{entry_id}: a unique sourced {field} is required")
    return rows[0]


def _circuit(entry_id, recipes, dut_roles, parts, supplies):
    """dut_roles: role -> net; parts: (ref, entry, package, ohms or None, {pin: net})."""
    recipe = recipes.entries[entry_id]
    nets = {}
    for pin, role in recipe.terminal_roles.items():
        nets.setdefault(dut_roles[role], []).append(PinRef(component="U1", pin=pin))
    components = [CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)]
    choices = {"U1": BehaviorSelection(entry_id=entry_id)}
    for ref, part, package, ohms, pins in parts:
        components.append(CircuitComponent(ref=ref, part_id=part, package=package,
                                           value=Quantity.ohms(ohms) if ohms is not None else None))
        choices[ref] = BehaviorSelection(entry_id=part)
        for pin, net in pins.items():
            nets.setdefault(net, []).append(PinRef(component=ref, pin=pin))
    circuit = CircuitIR(ir_id=f"runtime-{entry_id}-vendor", name="Datasheet-condition vendor model check",
                        components=components, nets=[
                            Net(name=name, kind="ground" if name == "return" else "power" if name in supplies else "signal",
                                connections=pins,
                                external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(
                                    Quantity.volts(supplies[name]))) if name in supplies else None)
                            for name, pins in sorted(nets.items())])
    return circuit, choices


def vendor_ic_definition(audit, entry_id):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    recipe = recipes.entries[entry_id]
    if not is_vendor_ic(recipe):
        raise ValueError("vendor IC check applies only to a bound manufacturer IC model")
    values, evidence = _facts(registry.entry(entry_id), recipe)
    behavior = recipe.behavior_id
    excitations, observe, analysis, step, stop = [], [], "op", None, None
    if behavior == "BEH-PWR-LOADSWITCH":
        fact = evidence["ron_max"]
        condition = re.search(r"VIN = (\d+(?:\.\d+)?) V, IOUT = [-–]?(\d+(?:\.\d+)?) mA", fact["scope"])
        if condition is None:
            raise ValueError("on-resistance test condition is not explicit in the source field")
        vin, iout = float(condition[1]), float(condition[2]) / 1000
        if not values["supply_min"] <= vin <= values["supply_max"] or vin > values["en_max"]:
            raise ValueError("source test condition lies outside the recommended VIN or EN range")
        # EN/UVLO tied to VIN; CT and QOD left open (CT sets slew only; QOD is idle while on).
        roles = {"VIN": "vin", "EN_UVLO": "vin", "GND": "return", "VOUT": "out", "CT": "ct", "QOD": "qod"}
        circuit, choices = _circuit(entry_id, recipes, roles, [], {"vin": vin})
        excitations = [DCExcitation(positive_net="out", negative_net="return", value=Quantity(value=iout, unit="A"))]
        typ_mohm = fact["value"]["typ"]
        comparison = [{"kind": "interval", "observable": "on_resistance", "supply": "vin", "node": "out",
                       "supply_voltage": vin, "load_current": iout,
                       "minimum": printed_lower_edge(typ_mohm) / 1000, "maximum": values["ron_max"],
                       "source_fact": fact,
                       "derivation": "(VIN - VOUT) / IOUT at the datasheet RON test condition, against the 25 C "
                                     "typical (less half its last printed digit) to maximum interval."}]
        limits = ("Operating-point RON of TI's model at the datasheet's VIN 12 V / IOUT 200 mA / 25 C row. Does not "
                  "check CT rise time, QOD discharge, UVLO or thermal behavior.")
    elif behavior == "BEH-REG-LINEAR":
        vref = values["vref"]
        r2, r1 = 10_000.0, 31_250.0
        vset = vref * (1 + r1 / r2)
        accuracy = evidence["acc_min"]
        if "VOUT + 0.5 V <= VIN" not in accuracy["scope"] or "100 mA <= IOUT <= 1 A" not in accuracy["scope"]:
            raise ValueError("output accuracy test condition changed")
        vin = vset + 0.5
        load = 33.0
        if not values["supply_min"] <= vin <= values["supply_max"] or not 0.1 <= vset / load <= values["iout_recommended"]:
            raise ValueError("test condition lies outside the accuracy row or recommended range")
        roles = {"IN": "vin", "EN": "vin", "GND": "return", "OUT": "out", "FB": "fb", "NR": "nr"}
        circuit, choices = _circuit(entry_id, recipes, roles, [
            ("R1", *RESISTOR, r1, {"1": "out", "2": "fb"}), ("R2", *RESISTOR, r2, {"1": "fb", "2": "return"}),
            ("RL", *LOAD, load, {"1": "out", "2": "return"})], {"vin": vin})
        lo, hi = 1 + values["acc_min"] / 100, 1 + values["acc_max"] / 100
        source = {name: evidence[name] for name in ("acc_min", "acc_max", "vref")}
        comparison = [
            {"kind": "interval", "observable": "node_voltage", "node": "out", "minimum": vset * lo, "maximum": vset * hi,
             "setpoint": vset, "supply_voltage": vin, "load_ohm": load, "source_facts": source,
             "derivation": "VOUT = 0.8 V x (1 + R1/R2) = 3.3 V (datasheet Equation 2) within the -3%..3% accuracy row at "
                           "VIN = VOUT + 0.5 V and IOUT = 100 mA; ideal divider resistors (the row excludes their tolerance)."},
            {"kind": "interval", "observable": "node_voltage", "node": "fb", "minimum": vref * lo, "maximum": vref * hi,
             "source_facts": source, "derivation": "FB regulates to the 0.8 V reference; same accuracy band."}]
        limits = ("Operating-point output and feedback of TI's model at the datasheet output-accuracy condition. The model "
                  "omits quiescent current, NR and temperature; does not check dropout, current limit, start-up or stability.")
    else:  # BEH-REG-BUCK-DCS
        vref = values["vref"]
        r2, r1, rpg, load = 100_000.0, 312_500.0, 100_000.0, 6.6
        vset = vref * (1 + r1 / r2)
        lc = _fact(registry, entry_id, "recommended_lc_filter").model_dump(mode="json")
        # The inductor is an ideal test fixture at the datasheet's standard 2.2 uH: the only bound power
        # inductor near it (OHM-045, 1.8 uH) uses a nonlinear-inductance card that stops ngspice ("timestep too
        # small" on its internal node) at the first switching edges of TI's model. The capacitor is a bound part.
        inductor = lc["value"]["inductance_uH"] * 1e-6
        capacitor = _facts(registry.entry(OUTPUT_CAP), recipes.entries[OUTPUT_CAP])[0]["value"]
        if abs(capacitor / (lc["value"]["capacitance_uF"] * 1e-6) - 1) > 1e-9:
            raise ValueError("bound output capacitor is not the datasheet's standard 22 uF")
        vin = 12.0
        if not values["supply_min"] <= vin <= values["supply_max"] or vin < vset + 1:
            raise ValueError("test condition lies outside the PWM accuracy row")
        roles = {"VIN": "vin", "EN": "vin", "AGND": "return", "PGND": "return", "SW": "sw", "VOS": "out",
                 "FB": "fb", "PG": "pg"}
        circuit, choices = _circuit(entry_id, recipes, roles, [
            ("C2", OUTPUT_CAP, recipes.entries[OUTPUT_CAP].package, None, {"1": "out", "2": "return"}),
            ("R1", *RESISTOR, r1, {"1": "out", "2": "fb"}), ("R2", *RESISTOR, r2, {"1": "fb", "2": "return"}),
            ("R3", *RESISTOR, rpg, {"1": "out", "2": "pg"}), ("RL", *LOAD, load, {"1": "out", "2": "return"})],
            {"vin": vin})
        excitations = [IdealTestInductor(positive_net="sw", negative_net="out",
                                         inductance=Quantity(value=inductor, unit="H"))]
        analysis, step, stop, observe = "tran", "500n", "300u", ["out", "fb", "pg"]
        window = [250e-6, 300e-6]
        lo, hi = 1 + values["acc_min"] / 100, 1 + values["acc_max"] / 100
        source = {name: evidence[name] for name in ("acc_min", "acc_max", "vref", "pg_leak")}
        comparison = [
            {"kind": "interval", "observable": "window_mean", "node": "out", "window": window,
             "minimum": vset * lo, "maximum": vset * hi, "setpoint": vset, "supply_voltage": vin, "load_ohm": load,
             "source_facts": source, "lc_fact": lc, "ideal_test_inductor_h": inductor, "capacitor_f": capacitor,
             "derivation": "VOUT = 0.8 V x (1 + R1/R2) = 3.3 V (datasheet Equation 6) within the -3%..3% PWM accuracy "
                           "row (VIN 12 V >= VOUT + 1 V; 0.5 A load exceeds half the ~0.6 A ripple, so PWM), averaged "
                           "over 250-300 us after a start-up from 0 V, with the datasheet's standard 2.2 uH / 22 uF "
                           "filter (ideal 2.2 uH test inductor, bound 22 uF capacitor)."},
            {"kind": "interval", "observable": "window_mean", "node": "fb", "window": window,
             "minimum": vref * lo, "maximum": vref * hi, "source_facts": source,
             "derivation": "FB regulates to the 0.8 V reference; same accuracy band."},
            {"kind": "interval", "observable": "window_mean", "node": "pg", "window": window,
             "minimum": vset * lo - values["pg_leak"] * rpg, "maximum": vset * hi, "pull_up_ohm": rpg,
             "source_facts": source,
             "derivation": "PG released (open drain off) once VOUT is above 95% of nominal: the 100 kohm pull-up to VOUT "
                           "then holds PG within the VOUT band less the 400 nA maximum PG leakage drop."}]
        limits = ("Start-up of TI's switching model into the standard LC filter at VIN 12 V, 3.3 V, 0.5 A, with output, "
                  "feedback and power-good averaged once settled. Uses a 20 ns maximum internal step. Does not check "
                  "ripple, efficiency, current limit, load transients, PSM or thermal behavior.")
    compiled = compile_circuit(circuit, registry, recipes, choices, analysis=analysis, excitations=excitations)
    identity = {"run_id": audit._state()["run_id"], "entry_id": entry_id, "analysis": analysis,
                "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
                "recipe_source_sha256": recipes.source.document_sha256,
                "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
                "class_source_sha256": registry.behavior_class(behavior).source.document_sha256,
                "vendor_model": recipe.vendor_model.model_dump(mode="json"),
                "ngspice_compatibility": compiled.ngspice_compatibility,
                "comparison": comparison, "observe_nets": observe, "tstep": step, "tstop": stop, "limits": limits}
    return compiled, identity


def vendor_observations(compiled, identity, output):
    values = []
    point = parse_operating_point(output) if identity["analysis"] == "op" else None
    curve = parse_transient(output, analysis="tran", limit=100000) if identity["analysis"] == "tran" else None
    for row in identity["comparison"]:
        value = None
        if row["observable"] == "on_resistance" and point:
            voltage = point.node_voltages.get(compiled.node_names[row["node"]])
            if voltage is not None:
                value = (row["supply_voltage"] - voltage.value) / row["load_current"]
        elif row["observable"] == "node_voltage" and point:
            voltage = point.node_voltages.get(compiled.node_names[row["node"]])
            value = voltage.value if voltage else None
        elif row["observable"] == "window_mean" and curve:
            series = next((x for x in curve.series if x.name == f"v({compiled.node_names[row['node']]})"), None)
            t0, t1 = row["window"]
            if series and curve.time_s and curve.time_s[-1] >= t1 * (1 - 1e-9):
                pairs = [(t, v) for t, v in zip(curve.time_s, series.values, strict=True) if t0 <= t <= t1 * (1 + 1e-9)]
                if len(pairs) > 1:
                    area = sum((b[0] - a[0]) * (a[1] + b[1]) / 2 for a, b in pairwise(pairs))
                    value = area / (pairs[-1][0] - pairs[0][0])
        values.append(value)
    return values


def _matches(row, value):
    return value is not None and row["minimum"] <= value <= row["maximum"]


def _adapter():
    return NgspiceAdapter(timeout_seconds=VENDOR_TIMEOUT_SECONDS)


def run_vendor_ic_recipes(audit, entry_ids):
    receipts = []
    for entry_id in entry_ids:
        compiled, identity = vendor_ic_definition(audit, entry_id)
        relative = f"runtime-bench-output/{entry_id}-vendor"
        kwargs = {"analysis": identity["analysis"]}
        if identity["analysis"] == "tran":
            kwargs.update(tstep=identity["tstep"], tstop=identity["tstop"], observe_nets=identity["observe_nets"])
        result = _adapter().behavior_circuit(compiled, work_dir=audit.run_dir / relative, **kwargs)
        output = result.get("stdout", "") + result.get("stderr", "")
        values = (vendor_observations(compiled, identity, output) if result["status"] == "ran"
                  else [None] * len(identity["comparison"]))
        passed = result["status"] == "ran" and all(_matches(r, v) for r, v in zip(identity["comparison"], values, strict=True))
        _atomic_text(audit.run_dir / relative / "output.txt", output)
        _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
        receipt = dict(identity, ran_at=_now(), run_status="passed" if passed else "failed",
                       observation_status=result["status"], observed=values,
                       product_code_path=result.get("product_code_path"), problems=result["problems"],
                       output_sha256=_sha_bytes(output.encode()), raw_output=relative + "/output.txt",
                       version_output=result["version_output"], version_file=relative + "/version.txt",
                       version_sha256=_sha_bytes(result["version_output"].encode()))
        _atomic_json(audit.run_dir / f"runtime-bench-results/{entry_id}-vendor.json", receipt)
        receipts.append(receipt)
    return receipts


def vendor_ic_receipt_errors(audit, entry_id):
    compiled, identity = vendor_ic_definition(audit, entry_id)
    path = audit.run_dir / f"runtime-bench-results/{entry_id}-vendor.json"
    if not path.is_file():
        return [f"{entry_id}: vendor runtime receipt missing"]
    receipt = json.loads(path.read_text(encoding="utf-8"))
    required = dict(identity, observation_status="ran", run_status="passed",
                    product_code_path="ohmni.eda.simulation.NgspiceAdapter.behavior_circuit")
    errors = [f"{entry_id}: stale or invalid vendor runtime {k}" for k, v in required.items() if receipt.get(k) != v]
    output_path = audit._safe_run_path(receipt["raw_output"])
    observed = vendor_observations(compiled, identity, output_path.read_text(encoding="utf-8"))
    if observed != receipt.get("observed") or not all(
            _matches(r, v) for r, v in zip(identity["comparison"], observed, strict=True)):
        errors.append(f"{entry_id}: raw vendor observation does not meet its sourced interval")
    if _sha_bytes(output_path.read_bytes()) != receipt["output_sha256"]:
        errors.append(f"{entry_id}: raw output changed")
    version_path = audit._safe_run_path(receipt["version_file"])
    version = version_path.read_text(encoding="utf-8")
    if (_sha_bytes(version_path.read_bytes()) != receipt["version_sha256"] or version != receipt["version_output"]
            or not re.search(r"\bngspice-42\b", version)):
        errors.append(f"{entry_id}: ngspice 42 evidence invalid")
    return errors
