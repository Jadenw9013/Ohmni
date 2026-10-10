"""Exercise compiled CircuitIR bindings against an existing analytical contract."""

from __future__ import annotations

import json
import re

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import _facts, compile_circuit, load_recipes
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation, PWLExcitation, PWLPoint
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point, parse_transient

from .audit import _atomic_json, _atomic_text, _now, _sha_bytes
from .benches import numeric_contract


def run_runtime_recipes(audit, entry_ids=None):
    """Run every selected binding through its authored product-path probe."""
    from .ic_benches import run_ic_recipes

    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    selected = set(recipes.entries) if entry_ids is None else set(entry_ids)
    unknown = selected - recipes.entries.keys()
    if unknown:
        raise ValueError(f"no runtime recipe for {sorted(unknown)}")
    runners = {}
    ic_classes = {"BEH-IC-TIMER555", "BEH-IC-LOGIC-HC", "BEH-IC-LOGIC-SEQ",
                  "BEH-IC-OPAMP", "BEH-IC-LDO-SOT235", "BEH-IC-OPTO-DIP6", "BEH-FREQ-XO"}
    for key in sorted(selected):
        behavior = recipes.entries[key].behavior_id
        runner = (run_tran_probes if behavior in TRAN_PROBES else
                  run_resistor_recipes if behavior == "BEH-RES-FIXED" else
                  run_mosfet_recipes if behavior == "BEH-TRN-MOSFET" else
                  run_ic_recipes if behavior in ic_classes else run_dc_probes)
        runners.setdefault(runner, []).append(key)
    return [receipt for runner, keys in runners.items() for receipt in runner(audit, keys)]


def resistor_divider(entry_id, package):
    """5 V / two 10 kohm divider from BEH-RES-FIXED/B1, not a new fit."""
    return CircuitIR(ir_id=f"runtime-{entry_id}", name="Authored B1 divider topology", components=[
        CircuitComponent(ref=ref, part_id=entry_id, package=package, value=Quantity.ohms(10000))
        for ref in ["R1", "R2"]
    ], nets=[
        Net(name="supply", kind="power", connections=[PinRef(component="R1", pin="1")],
            external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(5)))),
        Net(name="middle", connections=[PinRef(component="R1", pin="2"), PinRef(component="R2", pin="1")]),
        Net(name="return", kind="ground", connections=[PinRef(component="R2", pin="2")]),
    ])


def run_resistor_recipes(audit, entry_ids):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    adapter = NgspiceAdapter()
    contract = audit._bench_contracts(corrected=False)["BEH-RES-FIXED/B1"]
    if _sha_bytes((audit.root / contract["file"]).read_bytes()) != contract["netlist_sha256"]:
        raise ValueError("locked analytical source deck changed")
    expected_row = next(x for x in contract["expected"] if x["measure"] == "v(out)")
    expected = numeric_contract(expected_row)
    receipts = []
    for entry_id in entry_ids:
        recipe = recipes.entries[entry_id]
        if recipe.behavior_id != "BEH-RES-FIXED":
            raise ValueError("divider bench applies only to fixed resistors")
        circuit = resistor_divider(entry_id, recipe.package)
        selections = {c.ref: BehaviorSelection(entry_id=entry_id) for c in circuit.components}
        for analysis in ("op", "tran"):
            compiled = compile_circuit(circuit, registry, recipes, selections, analysis=analysis)
            relative = f"runtime-bench-output/{entry_id}-{analysis}"
            result = adapter.behavior_circuit(compiled, work_dir=audit.run_dir / relative, analysis=analysis)
            observations = []
            if result["status"] == "ran":
                node = compiled.node_names["middle"]
                if analysis == "op":
                    value = result["operating_point"]["node_voltages"].get(node)
                    if value:
                        observations.append(value["value"])
                else:
                    for series in result["transient"]["series"]:
                        if series["name"] == f"v({node})":
                            observations.extend(series["values"])
            passed = bool(observations) and all(
                abs(value - expected["expected"]) <= expected["tolerance"] for value in observations
            )
            output = result.get("stdout", "") + result.get("stderr", "")
            _atomic_text(audit.run_dir / relative / "output.txt", output)
            _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
            receipt = {
                "run_id": audit._state()["run_id"], "ran_at": _now(), "entry_id": entry_id,
                "analysis": analysis, "run_status": "passed" if passed else "failed",
                "observation_status": result["status"], "version_output": result["version_output"],
                "product_code_path": result.get("product_code_path"),
                "analytical_source": "BEH-RES-FIXED/B1", "source_deck_sha256": contract["netlist_sha256"],
                "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
                "recipe_source_sha256": recipes.source.document_sha256,
                "class_source_sha256": registry.behavior_class(recipe.behavior_id).source.document_sha256,
                "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
                "expected": expected, "observations": observations, "output_sha256": _sha_bytes(output.encode()),
                "raw_output": relative + "/output.txt", "problems": result["problems"],
                "version_file": relative + "/version.txt",
                "version_sha256": _sha_bytes(result["version_output"].encode()),
                "limits": "Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.",
            }
            _atomic_json(audit.run_dir / f"runtime-bench-results/{entry_id}-{analysis}.json", receipt)
            receipts.append(receipt)
    return receipts


def resistor_receipt_errors(audit, entry_id):
    """Re-derive observation and input identity before counting an implementation."""
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    recipe = recipes.entries[entry_id]
    circuit = resistor_divider(entry_id, recipe.package)
    choices = {c.ref: BehaviorSelection(entry_id=entry_id) for c in circuit.components}
    contract = audit._bench_contracts(corrected=False)["BEH-RES-FIXED/B1"]
    expected = numeric_contract(next(x for x in contract["expected"] if x["measure"] == "v(out)"))
    errors = []
    for analysis in ("op", "tran"):
        path = audit.run_dir / f"runtime-bench-results/{entry_id}-{analysis}.json"
        if not path.is_file():
            errors.append(f"{entry_id}/{analysis}: runtime receipt missing")
            continue
        receipt = json.loads(path.read_text(encoding="utf-8"))
        compiled = compile_circuit(circuit, registry, recipes, choices, analysis=analysis)
        required = {
            "run_id": audit._state()["run_id"], "entry_id": entry_id, "analysis": analysis,
            "run_status": "passed", "observation_status": "ran", "expected": expected,
            "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
            "recipe_source_sha256": recipes.source.document_sha256,
            "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
            "class_source_sha256": registry.behavior_class(recipe.behavior_id).source.document_sha256,
            "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit",
            "analytical_source": "BEH-RES-FIXED/B1", "source_deck_sha256": contract["netlist_sha256"],
        }
        for name, value in required.items():
            if receipt.get(name) != value:
                errors.append(f"{entry_id}/{analysis}: stale or invalid runtime {name}")
        version = receipt.get("version_output", "")
        if not re.search(r"\bngspice-42\b", version):
            errors.append(f"{entry_id}/{analysis}: ngspice 42 evidence missing")
        output_path = audit._safe_run_path(receipt["raw_output"])
        version_path = audit._safe_run_path(receipt["version_file"])
        output = output_path.read_text(encoding="utf-8")
        if _sha_bytes(output_path.read_bytes()) != receipt["output_sha256"]:
            errors.append(f"{entry_id}/{analysis}: raw output changed")
        if _sha_bytes(version_path.read_bytes()) != receipt["version_sha256"] or version_path.read_text(encoding="utf-8") != version:
            errors.append(f"{entry_id}/{analysis}: raw version changed")
        node = compiled.node_names["middle"]
        if analysis == "op":
            value = parse_operating_point(output).node_voltages.get(node)
            actual = [value.value] if value else []
        else:
            curve = parse_transient(output, analysis="tran")
            actual = [value for series in curve.series if series.name == f"v({node})" for value in series.values]
        if not actual or actual != receipt.get("observations") or not all(
                abs(value - expected["expected"]) <= expected["tolerance"] for value in actual):
            errors.append(f"{entry_id}/{analysis}: observations do not match the raw output and locked expectation")
    return errors


def mosfet_case(registry, recipes, entry_id):
    """Relocate the manufacturer's Rds test condition, with no guessed bias."""
    recipe = recipes.entries[entry_id]
    values, evidence = _facts(registry.entry(entry_id), recipe)
    fact = evidence["rds_on_max_10V"]
    condition = fact["scope"] + " " + " ".join(str(p) for p in fact.get("selected_value_path", []))
    number = r"\d+(?:\.\d+)?"
    match = re.search(rf"\bVGS({number})[_\sV,]+ID({number})\s*A", condition)
    if not match:
        raise ValueError("on-resistance test bias is not explicit in the source field")
    gate, current = float(match[1]), float(match[2])
    target = values["rds_on_max_10V"]
    nets = []
    for role, name, voltage in [("D", "drain", current * target), ("G", "gate", gate), ("S", "source", None)]:
        pins = [PinRef(component="M1", pin=pin) for pin, value in recipe.terminal_roles.items() if value == role]
        source = ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(voltage))) if voltage is not None else None
        nets.append(Net(name=name, kind="power" if source else "ground", connections=pins, external_source=source))
    circuit = CircuitIR(ir_id=f"runtime-{entry_id}", name="Sourced on-resistance bias",
                        components=[CircuitComponent(ref="M1", part_id=entry_id, package=recipe.package)], nets=nets)
    compiled = compile_circuit(circuit, registry, recipes, {"M1": BehaviorSelection(entry_id=entry_id)})
    return compiled, {"gate_voltage": gate, "test_current": current,
                      "drain_voltage": current * target, "target_resistance": target,
                      "source_fact": fact}


def run_mosfet_recipes(audit, entry_ids):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    adapter = NgspiceAdapter()
    contract = audit._bench_contracts(corrected=False)["BEH-TRN-MOSFET/B1"]
    source_expectation = numeric_contract(contract["expected"][0])
    relative_tolerance = source_expectation["tolerance"] / abs(source_expectation["expected"])
    receipts = []
    for entry_id in entry_ids:
        compiled, point = mosfet_case(registry, recipes, entry_id)
        relative = f"runtime-bench-output/{entry_id}-op"
        result = adapter.behavior_circuit(compiled, work_dir=audit.run_dir / relative)
        current, resistance = None, None
        if result["status"] == "ran":
            branch = result["operating_point"]["branch_currents"].get(compiled.source_elements["drain"])
            current = abs(branch["value"]) if branch else None
            if current:
                resistance = point["drain_voltage"] / current
        expected = {"expected": point["target_resistance"],
                    "tolerance": point["target_resistance"] * relative_tolerance}
        passed = resistance is not None and abs(resistance - expected["expected"]) <= expected["tolerance"]
        output = result.get("stdout", "") + result.get("stderr", "")
        _atomic_text(audit.run_dir / relative / "output.txt", output)
        _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
        recipe = recipes.entries[entry_id]
        receipt = {
            "run_id": audit._state()["run_id"], "ran_at": _now(), "entry_id": entry_id,
            "analysis": "op", "run_status": "passed" if passed else "failed",
            "observation_status": result["status"], "version_output": result["version_output"],
            "product_code_path": result.get("product_code_path"), "expected": expected,
            "observed_current": current, "observed_resistance": resistance, "bias": point,
            "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
            "recipe_source_sha256": recipes.source.document_sha256,
            "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
            "class_source_sha256": registry.behavior_class(recipe.behavior_id).source.document_sha256,
            "tolerance_contract": "BEH-TRN-MOSFET/B1", "source_deck_sha256": contract["netlist_sha256"],
            "output_sha256": _sha_bytes(output.encode()), "raw_output": relative + "/output.txt",
            "version_sha256": _sha_bytes(result["version_output"].encode()), "version_file": relative + "/version.txt",
            "limits": "Isothermal authored fit at 25 C; no SOA, avalanche, board thermal or destructive-failure acceptance. Uses the unchanged B1 relative fit tolerance with the scoped datasheet on-resistance target.",
        }
        _atomic_json(audit.run_dir / f"runtime-bench-results/{entry_id}-op.json", receipt)
        receipts.append(receipt)
    return receipts


def mosfet_receipt_errors(audit, entry_id):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    compiled, point = mosfet_case(registry, recipes, entry_id)
    path = audit.run_dir / f"runtime-bench-results/{entry_id}-op.json"
    if not path.is_file():
        return [f"{entry_id}: runtime receipt missing"]
    receipt = json.loads(path.read_text(encoding="utf-8"))
    contract = audit._bench_contracts(corrected=False)["BEH-TRN-MOSFET/B1"]
    base = numeric_contract(contract["expected"][0])
    expected = {"expected": point["target_resistance"],
                "tolerance": point["target_resistance"] * (base["tolerance"] / abs(base["expected"]))}
    required = {
        "run_id": audit._state()["run_id"], "entry_id": entry_id, "analysis": "op",
        "run_status": "passed", "observation_status": "ran", "expected": expected, "bias": point,
        "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
        "recipe_source_sha256": recipes.source.document_sha256,
        "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
        "class_source_sha256": registry.behavior_class(recipes.entries[entry_id].behavior_id).source.document_sha256,
        "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit",
        "tolerance_contract": "BEH-TRN-MOSFET/B1", "source_deck_sha256": contract["netlist_sha256"],
    }
    errors = [f"{entry_id}: stale or invalid runtime {k}" for k, v in required.items() if receipt.get(k) != v]
    output_path = audit._safe_run_path(receipt["raw_output"])
    output = output_path.read_text(encoding="utf-8")
    branch = parse_operating_point(output).branch_currents.get(compiled.source_elements["drain"])
    current = abs(branch.value) if branch else None
    resistance = point["drain_voltage"] / current if current else None
    if current != receipt.get("observed_current") or resistance != receipt.get("observed_resistance") or resistance is None or abs(resistance - expected["expected"]) > expected["tolerance"]:
        errors.append(f"{entry_id}: resistance does not follow captured current and source expectation")
    if _sha_bytes(output_path.read_bytes()) != receipt["output_sha256"]:
        errors.append(f"{entry_id}: raw output changed")
    version_path = audit._safe_run_path(receipt["version_file"])
    version = version_path.read_text(encoding="utf-8")
    if _sha_bytes(version_path.read_bytes()) != receipt["version_sha256"] or version != receipt["version_output"] or not re.search(r"\bngspice-42\b", version):
        errors.append(f"{entry_id}: ngspice 42 version evidence invalid")
    return errors


def runtime_receipt_errors(audit, entry_id):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    behavior = recipes.entries[entry_id].behavior_id
    if behavior in {"BEH-IC-TIMER555", "BEH-IC-LOGIC-HC", "BEH-IC-LOGIC-SEQ",
                    "BEH-IC-OPAMP", "BEH-IC-LDO-SOT235", "BEH-IC-OPTO-DIP6", "BEH-FREQ-XO"}:
        from .ic_benches import ic_receipt_errors

        return ic_receipt_errors(audit, entry_id)
    if entry_id == "OHM-069":
        from .calibration import tvs_calibration_errors

        return tvs_calibration_errors(audit) + dc_probe_receipt_errors(audit, entry_id)
    if behavior in TRAN_PROBES:
        return tran_probe_receipt_errors(audit, entry_id)
    if behavior == "BEH-RES-FIXED":
        return resistor_receipt_errors(audit, entry_id)
    if behavior == "BEH-TRN-MOSFET":
        return mosfet_receipt_errors(audit, entry_id)
    if behavior in {"BEH-DIO-PN", "BEH-TRN-BJT", "BEH-MAG-INDUCTOR", "BEH-LED-INDICATOR",
                    "BEH-RES-SENSE", "BEH-RES-NETWORK", "BEH-DIO-BRIDGE", "BEH-LED-RGB",
                    "BEH-DIO-ZENER", "BEH-DIO-TVS", "BEH-DIO-SCHOTTKY", "BEH-LED-POWER"} or behavior in PATH_PROBES:
        return dc_probe_receipt_errors(audit, entry_id)
    return [f"{entry_id}: no runtime analytical receipt validator for {behavior}"]


# One DC current through one bound path, compared with that path's sourced resistance (D049).
# Rows: variant, driven role, return role, resistance alias candidates, current rule.
_CONTACT = [(None, "P1", ("W1", "M1", "C1"), ("rmate", "rpath", "rc"), "rated")]
PATH_PROBES = {
    "BEH-RES-POT": [(None, "A", ("B",), ("value",), "pot")],
    "BEH-CAP-CERAMIC": [(None, "T1", ("T2",), ("rleak",), "leak")],
    "BEH-CAP-TANT": [(None, "A", ("K",), (), "tant")],
    "BEH-MAG-CMC": [("A", "A1", ("A2",), ("rdc",), "rated"), ("B", "B1", ("B2",), ("rdc",), "rated")],
    "BEH-MAG-XFMR-SIGNAL": [("primary", "P_A", ("P_B",), ("rp",), "unbalance"),
                            ("secondary", "S_A", ("S_B",), ("rs",), "unbalance")],
    "BEH-CON-WTB": _CONTACT, "BEH-CON-TERMINAL": _CONTACT, "BEH-CON-USB": _CONTACT,
    "BEH-CON-HDMI": _CONTACT, "BEH-CON-MODJACK": _CONTACT, "BEH-CON-SDSOCKET": _CONTACT,
    "BEH-CON-AUDIO": [(None, "TIP", ("M_TIP",), ("rc",), "rated")],
    "BEH-CON-DCJACK": [(None, "CENTER", ("M_TIP",), ("rc",), "rated")],
}
PATH_TOLERANCE = 1e-3


def _path_probe(recipe, values, evidence, variant):
    row = next(r for r in PATH_PROBES[recipe.behavior_id] if r[0] == variant)
    _, drive, returns, aliases, rule = row
    roles = set(recipe.terminal_roles.values())
    back = next((r for r in returns if r in roles), None)
    if drive not in roles or back is None:
        raise ValueError("bound path roles are missing")
    if rule == "tant":
        resistance, current, facts = values["vr"] / values["ileak"], values["ileak"], ("vr", "ileak")
    else:
        alias = next((a for a in aliases if a in values), None)
        if alias is None:
            raise ValueError("path resistance fact is missing")
        resistance = values[alias]
        if rule == "rated":
            current_alias = next(a for a in ("i_rated", "i_nom", "irated") if a in values)
            current, facts = values[current_alias], (alias, current_alias)
        elif rule == "unbalance":
            current, facts = values["idc_unbalance"], (alias, "idc_unbalance")
        elif rule == "leak":
            current, facts = values["vr"] / resistance, (alias, "vr")
        else:  # pot: the locked B1 deck's 10 V across the track
            current, facts = 10 / resistance, (alias, "tol")
    if rule == "pot":
        tol = values["tol"] / 100
        comparison = {"kind": "interval", "minimum": resistance * (1 - tol), "maximum": resistance * (1 + tol)}
    else:
        comparison = {"kind": "absolute", "expected": resistance, "tolerance": resistance * PATH_TOLERANCE}
    comparison.update(observable="path_resistance", current=current, drive_role=drive, return_role=back,
                      source_facts={name: evidence[name] for name in facts})
    isolated = set(recipe.required_isolated_roles)
    node_of = {role: ("anode" if role == drive else f"iso_{role}".lower() if role in isolated else "return")
               for role in roles}
    return node_of, comparison


def _dual_diode(recipe):
    return recipe is not None and {"A1", "K2", "K1A2"} <= set(recipe.terminal_roles.values())


# Replaying a fitted curve at several read points (CBH-R03). The bound (0..vf_max) check alone
# accepts a model that outputs almost nothing; these rows reject it. The tolerance is the
# datasheet-read uncertainty, not a fit residual: plots read from vector paths (M) get 5% or 15 mV,
# raster or coarse reads (L) 8% or 25 mV, whichever is larger.
FIT_TOLERANCE = {"H": (0.03, 0.010), "M": (0.05, 0.015), "L": (0.08, 0.025)}


def fit_variants(recipe):
    return [f"{name}_fit{k + 1}" for name, curve in (recipe.fit_curves if recipe else {}).items()
            for k in range(curve.points)]


def _fit_variant(recipe, variant):
    for name, curve in recipe.fit_curves.items():
        if variant and variant.startswith(name + "_fit"):
            return name, curve, int(variant[len(name) + 4:]) - 1
    return None


def fit_points(curve, field):
    """Lowest, highest and evenly spaced read points, so the whole plotted range is replayed."""
    points = sorted((float(i), float(v)) for i, v in field["value"]["points_a_v"])
    if len(points) < 2:
        raise ValueError("a fit curve needs at least two read points")
    if curve.points >= len(points):
        return points
    idx = [round(k * (len(points) - 1) / (curve.points - 1)) for k in range(curve.points)]
    return [points[i] for i in idx]


def dc_probe_variants(behavior_id, recipe=None):
    if behavior_id == "BEH-DIO-PN" and _dual_diode(recipe):
        return ["d1", "d2"]
    if behavior_id in PATH_PROBES:
        return [row[0] for row in PATH_PROBES[behavior_id]]
    if behavior_id == "BEH-DIO-BRIDGE":
        return ["positive", "negative"]
    if behavior_id == "BEH-LED-RGB":
        return ["red", "green", "blue", *fit_variants(recipe)]
    if behavior_id in {"BEH-DIO-ZENER", "BEH-DIO-TVS"}:
        return ["legacy", "source_bound"]
    if recipe is not None and recipe.fit_curves:
        return [None, *fit_variants(recipe)]
    return [None]


def _locked_probe_deck(audit, bench_id):
    contract = audit._bench_contracts(corrected=False)[bench_id]
    path = audit.root / contract["file"]
    if _sha_bytes(path.read_bytes()) != contract["netlist_sha256"]:
        raise ValueError("locked analytical source deck changed")
    return contract, path.read_text()


def dc_probe_definition(audit, entry_id, variant=None):
    """Definitions are separate from execution and re-used to re-derive receipts."""
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    recipe = recipes.entries[entry_id]
    values, evidence = _facts(registry.entry(entry_id), recipe)
    variants = dc_probe_variants(recipe.behavior_id, recipe)
    variant = variant or variants[0]
    if variant not in variants:
        raise ValueError("unknown probe variant")
    # A binding whose forward terms are fitted to the part's own datasheet curve is checked against
    # that part's sourced maximum, not against the shared class card it no longer uses (D048).
    own_forward_fit = {"IS", "N", "RS"} <= set(recipe.model_facts)
    fit = _fit_variant(recipe, variant)
    if fit is not None:
        name, curve, index = fit
        field = next((f for f in registry.entry(entry_id).research.field_updates if f.field == curve.field), None)
        if field is None or field.basis in {"ASSUMPTION", "RESEARCH_REQUIRED"}:
            raise ValueError("fit curve read points are not a sourced field")
        field = field.model_dump(mode="json")
        current, expected = fit_points(curve, field)[index]
        relative, floor = FIT_TOLERANCE[field.get("confidence", "L")]
        roles = {role: "idle" for role in recipe.terminal_roles.values()}
        roles[curve.anode_role], roles[curve.cathode_role] = "anode", "return"
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=current, unit="A"))]
        comparison = {"kind": "absolute", "expected": expected, "tolerance": max(relative * expected, floor),
                      "observable": "anode_voltage", "source_fact": field, "curve": name, "point_index": index,
                      "test_current": current, "tolerance_rule": f"max({relative:g}*V, {floor:g} V) for a {field.get('confidence')}-confidence datasheet read"}
        limits = ("Replays the fitted forward model at one of the sourced curve read points and requires the "
                  "read voltage within the read uncertainty. Together with the other fit points and the "
                  "maximum-VF bound this validates the fit over the plotted range at 25 C; it does not validate "
                  "temperature, reverse behavior, capacitance or ratings.")
    elif recipe.behavior_id == "BEH-DIO-PN" and _dual_diode(recipe):
        # Series pair (D050): drive one junction at the source VF test current, leave the third terminal idle.
        fact = evidence["vf_max"]
        current = re.search(r"\bIF\s*=?\s*(\d+(?:\.\d+)?)\s*(m?A)", fact["scope"])
        if current is None:
            raise ValueError("forward voltage source test current is missing")
        amps = float(current[1]) / (1000 if current[2] == "mA" else 1)
        roles = ({"A1": "anode", "K1A2": "return", "K2": "idle"} if variant == "d1"
                 else {"K1A2": "anode", "K2": "return", "A1": "idle"})
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=amps, unit="A"))]
        comparison = {"kind": "interval", "minimum": 0, "maximum": values["vf_max"], "observable": "anode_voltage",
                      "source_fact": fact, "junction": variant}
        limits = ("One junction of the series pair at the source forward test current against its maximum VF, the other "
                  "terminal idle; uses the class 1N4148-family card, not a BAV99 fit. Does not validate both-loaded "
                  "thermal behavior, recovery or capacitance.")
    elif recipe.behavior_id == "BEH-LED-POWER":
        fact = evidence["vf_max"]
        condition = re.search(r"(\d+(?:\.\d+)?)\s*mA", fact["scope"])
        if condition is None:
            raise ValueError("LED source test current is missing")
        if values.get("tj_vf") is None:
            raise ValueError("source forward-voltage junction temperature is missing")
        current = float(condition[1]) / 1000
        roles = {"A": "anode", "K": "return", "TH": "idle"}
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=current, unit="A"))]
        comparison = {"kind": "interval", "minimum": 0, "maximum": values["vf_max"], "observable": "anode_voltage",
                      "source_fact": fact, "test_current": current, "junction_temperature_c": values["tj_vf"]}
        limits = ("Forward voltage at the source test current with the diode instance held at the source junction "
                  "temperature (the datasheet publishes this VF only at that temperature). Isolated thermal pad. Does not "
                  "validate optics, the thermal path to ambient or other temperatures.")
    elif (recipe.behavior_id == "BEH-DIO-PN" and (entry_id in {"OHM-057", "OHM-058", "OHM-064", "OHM-065"} or own_forward_fit)
            or recipe.behavior_id == "BEH-DIO-SCHOTTKY"):
        fact = evidence["vf_max"]
        current = re.search(r"\bIF\s*=?\s*(\d+(?:\.\d+)?)\s*(m?A)", fact["scope"])
        if current is None:
            raise ValueError("forward voltage source test current is missing")
        roles = {"A": "anode", "K": "return"}
        supplies = {}
        amps = float(current[1]) / (1000 if current[2] == "mA" else 1)
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=amps, unit="A"))]
        comparison = {"kind": "interval", "minimum": 0, "maximum": values["vf_max"],
                      "observable": "anode_voltage", "source_fact": fact}
        limits = "Isothermal25 C forward voltage against the scoped primary-source maximum at its test current; a source-bound check does not validate typical fit, temperature, reverse recovery or ratings."
    elif recipe.behavior_id in {"BEH-LED-INDICATOR", "BEH-LED-RGB"} and (entry_id != "OHM-073" or own_forward_fit):
        rgb = recipe.behavior_id == "BEH-LED-RGB"
        fact = evidence["vf_" + variant if rgb else "vf_max"]
        condition = re.search(r"(?:IF)?\s*(\d+(?:\.\d+)?)\s*mA", fact["scope"])
        if condition is None:
            raise ValueError("LED source test current is missing")
        current = float(condition[1]) / 1000
        roles = ({role: "return" if role == variant + "_cathode" else "anode"
                  for role in recipe.terminal_roles.values()} if rgb else {"A": "anode", "K": "return"})
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=current, unit="A"))]
        comparison = {"kind": "interval", "minimum": 0, "maximum": values["vf_" + variant if rgb else "vf_max"],
                      "observable": "anode_voltage", "source_fact": fact, "test_current": current}
        limits = (("Per-part forward fit" if own_forward_fit else "Explicit color-family proxy")
                  + " at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.")
    elif recipe.behavior_id == "BEH-RES-SENSE":
        contract, deck = _locked_probe_deck(audit, "BEH-RES-SENSE/B1")
        if not re.search(r"(?im)^I\S*\s+\S+\s+\S+\s+(?:DC\s+)?10\s*$", deck):
            raise ValueError("authored sense-resistor current stimulus changed")
        target = 10 * values["value"]
        locked = numeric_contract(contract["expected"][0])
        roles = {"I1": "anode", "I2": "return"}
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=10, unit="A"))]
        comparison = {"kind": "absolute", "expected": target,
                      "tolerance": target * locked["tolerance"] / locked["expected"], "observable": "anode_voltage",
                      "analytical_source": "BEH-RES-SENSE/B1", "source_deck_sha256": contract["netlist_sha256"],
                      "derivation": "Same authored I*Rs equation and relative tolerance, evaluated at the bound 5 milliohm reference instead of the class bench's 1 milliohm example.",
                      "source_fact": evidence["value"]}
        limits = "Two-terminal isothermal DC Ohm's law only; no Kelvin, lead-drop, temperature or safe-current acceptance."
    elif recipe.behavior_id == "BEH-RES-NETWORK":
        contract, deck = _locked_probe_deck(audit, "BEH-RES-NETWORK/B2")
        if not re.search(r"(?im)^V\S*\s+\S+\s+\S+\s+(?:DC\s+)?5\s*$", deck):
            raise ValueError("authored network voltage stimulus changed")
        locked = numeric_contract(contract["expected"][0])
        target = (len(recipe.terminal_roles)-1)*5/values["value"]
        roles = {role: "return" if role == "P1" else "supply" for role in recipe.terminal_roles.values()}
        supplies = {"supply": 5}
        excitations = []
        comparison = {"kind": "absolute", "expected": target,
                      "tolerance": target*locked["tolerance"]/locked["expected"], "observable": "supply_current",
                      "analytical_source": "BEH-RES-NETWORK/B2", "source_deck_sha256": contract["netlist_sha256"],
                      "derivation": "Same authored parallel sum N*V/R and relative tolerance, evaluated for the bound seven 10 kohm branches; the original four 1 kohm branch contract remains unchanged.",
                      "source_fact": evidence["value"]}
        limits = "Total DC branch current for the sourced bussed topology only; per-element and whole-package thermal ratings remain separate."
    elif recipe.behavior_id == "BEH-DIO-BRIDGE":
        contract, deck = _locked_probe_deck(audit, "BEH-DIO-BRIDGE/B1")
        if "SIN(0 10 50)" not in deck:
            raise ValueError("authored bridge amplitude changed")
        fact = evidence["vf_max"]
        match = re.search(r";\s*(\d+(?:\.\d+)?)A", fact["scope"])
        if match is None:
            raise ValueError("bridge per-diode voltage test current missing")
        current = float(match[1])
        roles = {"AC1": "supply", "AC2": "return", "PLUS": "plus", "MINUS": "minus"}
        supplies = {"supply": 10 if variant == "positive" else -10}
        excitations = [DCExcitation(positive_net="plus", negative_net="minus", value=Quantity(value=current, unit="A"))]
        comparison = {"kind": "interval", "minimum": 0, "maximum": 2*values["vf_max"],
                      "observable": "bridge_drop", "supply_magnitude": 10,
                      "source_fact": fact, "test_current": current,
                      "stimulus_source": "BEH-DIO-BRIDGE/B1", "source_deck_sha256": contract["netlist_sha256"],
                      "derivation": "Two conducting junctions; sum of two source per-diode forward-voltage maxima. Both AC polarities use the original bench's 10 V input amplitude."}
        limits = "Isothermal DC rectification and two-junction voltage bound under both AC polarities; does not validate ripple, shared thermal behavior, surge or safe sustained output current."
    elif recipe.behavior_id in {"BEH-DIO-ZENER", "BEH-DIO-TVS"}:
        tvs = recipe.behavior_id == "BEH-DIO-TVS"
        current = values["IPP" if tvs else "IZT"]
        roles = {"K": "cathode", "A": "return"}
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="cathode", value=Quantity(value=current, unit="A"))]
        if variant == "legacy":
            contract_id = recipe.behavior_id + "/B1"
            contract, _ = _locked_probe_deck(audit, contract_id)
            comparison = dict(numeric_contract(contract["expected"][0]), kind="absolute",
                              analytical_source=contract_id, source_deck_sha256=contract["netlist_sha256"])
        else:
            comparison = {"kind": "interval", "minimum": 0 if tvs else values["vz_min"],
                          "maximum": values["VC" if tvs else "vz_max"],
                          "source_fact": evidence["VC" if tvs else "vz_max"]}
        comparison.update(observable="node_voltage", node="cathode", test_current=current,
                          test_current_evidence=evidence["IPP" if tvs else "IZT"])
        limits = ("Static isothermal clamp-curve probe at 25 C only. The source rating describes a pulse; an operating-point result does not establish allowable continuous current, pulse waveform, heating or protected-load survival. Legacy numerical tolerance and the source voltage maximum are checked separately."
                  if tvs else "Isothermal 25 C voltage at the source short-pulse test current. Does not validate equilibrium self-heating, the impedance/knee envelope, surge, forward-current limit or destructive behavior.")
    elif recipe.behavior_id in {"BEH-DIO-PN", "BEH-LED-INDICATOR"}:
        is_led = recipe.behavior_id == "BEH-LED-INDICATOR"
        contract_id = "BEH-LED-INDICATOR/B1" if is_led else "BEH-DIO-PN/B1"
        # The first item is numeric in the (possibly corrected) contract; see CORRECTION-002.
        contract = audit._bench_contracts()[contract_id]
        expected = numeric_contract(contract["expected"][0])
        # Relocate the source stimulus rather than treating it as a device rating.
        source_deck = (audit.root / contract["file"]).read_text()
        source_text = "I1 0 a1 DC 20m" if is_led else "dc I1 10m 10m 1m"
        if source_text not in source_deck or _sha_bytes((audit.root / contract["file"]).read_bytes()) != contract["netlist_sha256"]:
            raise ValueError("locked diode forward test condition changed")
        roles = {"A": "anode", "K": "return"}
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=0.02 if is_led else 0.01, unit="A"))]
        comparison = dict(expected, kind="absolute", observable="anode_voltage",
                          analytical_source=contract_id, source_deck_sha256=contract["netlist_sha256"])
        limits = "Authored proxy forward curve only, compared at 25 C against the 25 C analytic value of its locked bench."
    elif recipe.behavior_id == "BEH-TRN-BJT":
        # Bias is supplied by the entry's scoped hFE test fields.
        vce = values["gain_test_vce"]
        collector_current = values["gain_test_ic"]
        gain = (values["gain_min"] * values["gain_max"]) ** 0.5
        roles = {"C": "collector", "B": "base", "E": "return"}
        supplies = {"collector": vce}
        excitations = [DCExcitation(positive_net="return", negative_net="base", value=Quantity(value=collector_current / gain, unit="A"))]
        comparison = {"kind": "interval", "minimum": values["gain_min"], "maximum": values["gain_max"],
                      "observable": "current_gain", "base_current": collector_current / gain,
                      "source_facts": {name: evidence[name] for name in ("gain_min", "gain_max", "gain_test_vce", "gain_test_ic")}}
        limits = "One-point DC gain-bin check using a geometric-mean BF and assumed IS. Does not validate gain roll-off, transient response, temperature behavior, ratings or SOA."
    elif recipe.behavior_id == "BEH-MAG-INDUCTOR":
        roles = {"A": "winding", "B": "return"}
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="winding", value=Quantity(value=values["irms"], unit="A"))]
        comparison = {"kind": "interval", "minimum": 0, "maximum": values["rdc_max"],
                      "observable": "dc_resistance", "current": values["irms"],
                      "source_facts": {name: evidence[name] for name in ("rdc_max", "irms")}}
        limits = "Cold isothermal DC winding resistance against the sourced upper bound. Does not validate nonlinear inductance, resonant response, core loss, self-heating or safe sustained operation at the stimulus current."
    elif recipe.behavior_id in PATH_PROBES:
        roles, comparison = _path_probe(recipe, values, evidence, variant)
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=comparison["current"], unit="A"))]
        limits = ("Binding check of one bound DC path: the sourced current through the path must reproduce the sourced path "
                  "resistance (0.1% numerical tolerance, or the sourced tolerance band). It does not validate frequency response, "
                  "heating, contact wear, isolation, protocol behavior or any rating beyond the stated facts.")
    else:
        raise ValueError("no authored DC probe for this class")
    nets = [Net(name=name, kind="ground" if name == "return" else "power" if name in supplies else "signal",
                connections=[PinRef(component="U1", pin=pin) for pin, role in recipe.terminal_roles.items() if roles[role] == name],
                external_source=ExternalSource(kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(supplies[name]))) if name in supplies else None)
            for name in sorted(set(roles.values()))]
    circuit = CircuitIR(ir_id=f"runtime-{entry_id}", name="Source-scoped DC probe",
                        components=[CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)], nets=nets)
    compiled = compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)}, excitations=excitations)
    identity = {"run_id": audit._state()["run_id"], "entry_id": entry_id, "analysis": "op",
                "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
                "recipe_source_sha256": recipes.source.document_sha256,
                "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
                "class_source_sha256": registry.behavior_class(recipe.behavior_id).source.document_sha256,
                "comparison": comparison, "limits": limits}
    if variant:
        identity["variant"] = variant
    return compiled, identity


def _dc_observation(compiled, comparison, output):
    parsed = parse_operating_point(output)
    if comparison["observable"] == "node_voltage":
        voltage = parsed.node_voltages.get(compiled.node_names[comparison["node"]])
        return voltage.value if voltage else None
    if comparison["observable"] == "anode_voltage":
        voltage = parsed.node_voltages.get(compiled.node_names["anode"])
        return voltage.value if voltage else None
    if comparison["observable"] == "current_gain":
        current = parsed.branch_currents.get(compiled.source_elements["collector"])
        return abs(current.value) / comparison["base_current"] if current else None
    if comparison["observable"] == "supply_current":
        current = parsed.branch_currents.get(compiled.source_elements["supply"])
        return -current.value if current else None
    if comparison["observable"] == "bridge_drop":
        plus = parsed.node_voltages.get(compiled.node_names["plus"])
        minus = parsed.node_voltages.get(compiled.node_names["minus"])
        return comparison["supply_magnitude"] - (plus.value - minus.value) if plus and minus else None
    if comparison["observable"] == "path_resistance":
        voltage = parsed.node_voltages.get(compiled.node_names["anode"])
        return voltage.value / comparison["current"] if voltage else None
    if comparison["observable"] == "dc_resistance":
        voltage = parsed.node_voltages.get(compiled.node_names["winding"])
        return voltage.value / comparison["current"] if voltage else None
    raise ValueError("unknown probe observable")


def _dc_matches(comparison, value):
    if value is None:
        return False
    if comparison["kind"] == "absolute":
        return abs(value - comparison["expected"]) <= comparison["tolerance"]
    return comparison["minimum"] <= value <= comparison["maximum"]


def run_dc_probes(audit, entry_ids):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    cases = [(entry_id, variant) for entry_id in entry_ids
             for variant in dc_probe_variants(recipes.entries[entry_id].behavior_id, recipes.entries[entry_id])]
    receipts = []
    for entry_id, variant in cases:
        compiled, identity = dc_probe_definition(audit, entry_id, variant)
        suffix = f"-{variant}" if variant else ""
        relative = f"runtime-bench-output/{entry_id}-op{suffix}"
        result = NgspiceAdapter().behavior_circuit(compiled, work_dir=audit.run_dir / relative)
        output = result.get("stdout", "") + result.get("stderr", "")
        observed = _dc_observation(compiled, identity["comparison"], output)
        passed = result["status"] == "ran" and _dc_matches(identity["comparison"], observed)
        _atomic_text(audit.run_dir / relative / "output.txt", output)
        _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
        receipt = dict(identity, ran_at=_now(), run_status="passed" if passed else "failed",
                       observation_status=result["status"], observed=observed,
                       product_code_path=result.get("product_code_path"), problems=result["problems"],
                       output_sha256=_sha_bytes(output.encode()), raw_output=relative + "/output.txt",
                       version_output=result["version_output"], version_file=relative + "/version.txt",
                       version_sha256=_sha_bytes(result["version_output"].encode()))
        _atomic_json(audit.run_dir / f"runtime-bench-results/{entry_id}-op{suffix}.json", receipt)
        receipts.append(receipt)
    return receipts


def dc_probe_receipt_errors(audit, entry_id):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    return [error for variant in dc_probe_variants(recipes.entries[entry_id].behavior_id, recipes.entries[entry_id])
            for error in _dc_probe_receipt_errors(audit, entry_id, variant)]


def _dc_probe_receipt_errors(audit, entry_id, variant):
    compiled, identity = dc_probe_definition(audit, entry_id, variant)
    suffix = f"-{variant}" if variant else ""
    path = audit.run_dir / f"runtime-bench-results/{entry_id}-op{suffix}.json"
    if not path.is_file():
        return [f"{entry_id}: runtime receipt missing"]
    receipt = json.loads(path.read_text())
    required = dict(identity, observation_status="ran", run_status="passed",
                    product_code_path="ohmni.eda.simulation.NgspiceAdapter.behavior_circuit")
    errors = [f"{entry_id}: stale or invalid runtime {k}" for k, v in required.items() if receipt.get(k) != v]
    output_path = audit._safe_run_path(receipt["raw_output"])
    output = output_path.read_text(encoding="utf-8")
    observed = _dc_observation(compiled, identity["comparison"], output)
    if observed != receipt.get("observed") or not _dc_matches(identity["comparison"], observed):
        errors.append(f"{entry_id}: raw observation does not meet its locked or sourced contract")
    if _sha_bytes(output_path.read_bytes()) != receipt["output_sha256"]:
        errors.append(f"{entry_id}: raw output changed")
    version_path = audit._safe_run_path(receipt["version_file"])
    version = version_path.read_text(encoding="utf-8")
    if _sha_bytes(version_path.read_bytes()) != receipt["version_sha256"] or version != receipt["version_output"] or not re.search(r"\bngspice-42\b", version):
        errors.append(f"{entry_id}: ngspice 42 evidence invalid")
    return errors


# Transient charge checks for capacitor classes whose behavior is only visible in time (D050).
# A current ramp from zero (so the operating point starts discharged) charges the bound
# capacitance; the node voltage at a fixed time is I*ESR + I*(t - ramp/2)/C.
TRAN_PROBES = {
    "BEH-CAP-MICA": {"current": 1e-5, "ramp": 1e-9, "time": 5e-6, "tstop": 6e-6, "tstep": "1n",
                     "tolerance": 1e-3, "contract": "BEH-CAP-MICA/B1"},
    "BEH-CAP-EDLC": {"current": None, "ramp": 1e-3, "time": 10.0, "tstop": 10.5, "tstep": "0.01",
                     "tolerance": 1e-2, "contract": "BEH-CAP-EDLC/B3"},
}


def tran_probe_definition(audit, entry_id):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    recipe = recipes.entries[entry_id]
    values, evidence = _facts(registry.entry(entry_id), recipe)
    spec = TRAN_PROBES[recipe.behavior_id]
    contract = audit._bench_contracts()[spec["contract"]]
    tolerance = spec["tolerance"]
    if {row["tolerance"] for row in contract["expected"]} != {f"{tolerance * 100:g}%"}:
        raise ValueError("charge probe tolerance no longer matches its locked class bench")
    capacitance = values["value"]
    if spec["current"] is None:
        # KYOCERA AVX capacitance-measurement current rule, I = 4*C*VR in mA (sourced field).
        current, esr = 4 * capacitance * values["vr"] / 1000, values["esr"]
        facts = ("value", "vr", "esr")
    else:
        current, esr, facts = spec["current"], 0.0, ("value", "vr")
    t = spec["time"]
    expected = current * esr + current * (t - spec["ramp"] / 2) / capacitance
    if expected >= values["vr"]:
        raise ValueError("charge probe would exceed the sourced voltage rating")
    pos, neg = ("T1", "T2") if "T1" in recipe.terminal_roles.values() else ("P", "N")
    roles = {pos: "anode", neg: "return"}
    nets = [Net(name=name, kind="ground" if name == "return" else "signal",
                connections=[PinRef(component="U1", pin=pin) for pin, role in recipe.terminal_roles.items() if roles[role] == name])
            for name in ("anode", "return")]
    circuit = CircuitIR(ir_id=f"runtime-{entry_id}-tran", name="Source-scoped charge probe",
                        components=[CircuitComponent(ref="U1", part_id=entry_id, package=recipe.package)], nets=nets)
    excitation = PWLExcitation(positive_net="return", negative_net="anode", points=[
        PWLPoint(time=Quantity(value=0, unit="s"), value=Quantity(value=0, unit="A")),
        PWLPoint(time=Quantity(value=spec["ramp"], unit="s"), value=Quantity(value=current, unit="A")),
        PWLPoint(time=Quantity(value=spec["tstop"], unit="s"), value=Quantity(value=current, unit="A"))])
    compiled = compile_circuit(circuit, registry, recipes, {"U1": BehaviorSelection(entry_id=entry_id)},
                               analysis="tran", excitations=[excitation])
    identity = {"run_id": audit._state()["run_id"], "entry_id": entry_id, "analysis": "tran",
                "netlist_sha256": compiled.netlist_sha256, "circuit_hash": compiled.circuit_hash,
                "recipe_source_sha256": recipes.source.document_sha256,
                "entry_research_sha256": registry.entry(entry_id).research.source.document_sha256,
                "class_source_sha256": registry.behavior_class(recipe.behavior_id).source.document_sha256,
                "tstep": spec["tstep"], "tstop": format(spec["tstop"], "g"), "observe_nets": ["anode"],
                "comparison": [{"kind": "absolute", "node": "anode", "time": t, "expected": expected,
                                "tolerance": abs(expected) * tolerance, "current": current,
                                "tolerance_contract": spec["contract"], "source_deck_sha256": contract["netlist_sha256"],
                                "source_facts": {name: evidence[name] for name in facts}}],
                "limits": ("Constant-current charge from zero against I*ESR + I*t/C at one time point, using the relative "
                           "tolerance of the class bench named in the comparison. Does not validate ESR frequency "
                           "dependence, leakage, RF loss, self-heating or any rating.")}
    return compiled, identity


def run_tran_probes(audit, entry_ids):
    from .ic_benches import _matches, _observations

    receipts = []
    for entry_id in entry_ids:
        compiled, identity = tran_probe_definition(audit, entry_id)
        relative = f"runtime-bench-output/{entry_id}-tran"
        result = NgspiceAdapter().behavior_circuit(compiled, work_dir=audit.run_dir / relative, analysis="tran",
                                                   tstep=identity["tstep"], tstop=identity["tstop"],
                                                   observe_nets=identity["observe_nets"])
        output = result.get("stdout", "") + result.get("stderr", "")
        values = _observations(compiled, identity, output) if result["status"] == "ran" else [None]
        passed = result["status"] == "ran" and all(_matches(row, v) for row, v in zip(identity["comparison"], values, strict=True))
        _atomic_text(audit.run_dir / relative / "output.txt", output)
        _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
        receipt = dict(identity, ran_at=_now(), run_status="passed" if passed else "failed",
                       observation_status=result["status"], observed=values,
                       product_code_path=result.get("product_code_path"), problems=result["problems"],
                       output_sha256=_sha_bytes(output.encode()), raw_output=relative + "/output.txt",
                       version_output=result["version_output"], version_file=relative + "/version.txt",
                       version_sha256=_sha_bytes(result["version_output"].encode()))
        _atomic_json(audit.run_dir / f"runtime-bench-results/{entry_id}-tran.json", receipt)
        receipts.append(receipt)
    return receipts


def tran_probe_receipt_errors(audit, entry_id):
    from .ic_benches import _matches, _observations

    compiled, identity = tran_probe_definition(audit, entry_id)
    path = audit.run_dir / f"runtime-bench-results/{entry_id}-tran.json"
    if not path.is_file():
        return [f"{entry_id}: runtime receipt missing"]
    receipt = json.loads(path.read_text())
    required = dict(identity, observation_status="ran", run_status="passed",
                    product_code_path="ohmni.eda.simulation.NgspiceAdapter.behavior_circuit")
    errors = [f"{entry_id}: stale or invalid runtime {k}" for k, v in required.items() if receipt.get(k) != v]
    output_path = audit._safe_run_path(receipt["raw_output"])
    output = output_path.read_text(encoding="utf-8")
    observed = _observations(compiled, identity, output)
    if observed != receipt.get("observed") or not all(_matches(row, v) for row, v in zip(identity["comparison"], observed, strict=True)):
        errors.append(f"{entry_id}: raw observation does not meet its locked or sourced contract")
    if _sha_bytes(output_path.read_bytes()) != receipt["output_sha256"]:
        errors.append(f"{entry_id}: raw output changed")
    version_path = audit._safe_run_path(receipt["version_file"])
    version = version_path.read_text(encoding="utf-8")
    if _sha_bytes(version_path.read_bytes()) != receipt["version_sha256"] or version != receipt["version_output"] or not re.search(r"\bngspice-42\b", version):
        errors.append(f"{entry_id}: ngspice 42 evidence invalid")
    return errors
