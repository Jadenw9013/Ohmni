"""Exercise compiled CircuitIR bindings against an existing analytical contract."""

from __future__ import annotations

import json
import re

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import _facts, compile_circuit, load_recipes
from ohmni.behavior.runtime_models import BehaviorSelection, DCExcitation
from ohmni.domain.circuit import CircuitComponent, CircuitIR, ExternalSource, Net, PinRef
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point, parse_transient

from .audit import _atomic_json, _atomic_text, _now, _sha_bytes
from .benches import numeric_contract


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
    contract = audit._state()["bench_contracts"]["BEH-RES-FIXED/B1"]
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
    contract = audit._state()["bench_contracts"]["BEH-RES-FIXED/B1"]
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
    contract = audit._state()["bench_contracts"]["BEH-TRN-MOSFET/B1"]
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
    contract = audit._state()["bench_contracts"]["BEH-TRN-MOSFET/B1"]
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
    if behavior == "BEH-RES-FIXED":
        return resistor_receipt_errors(audit, entry_id)
    if behavior == "BEH-TRN-MOSFET":
        return mosfet_receipt_errors(audit, entry_id)
    if behavior in {"BEH-DIO-PN", "BEH-TRN-BJT"}:
        return dc_probe_receipt_errors(audit, entry_id)
    return [f"{entry_id}: no runtime analytical receipt validator for {behavior}"]


def dc_probe_definition(audit, entry_id):
    """Definitions are separate from execution and re-used to re-derive receipts."""
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    recipe = recipes.entries[entry_id]
    values, evidence = _facts(registry.entry(entry_id), recipe)
    if recipe.behavior_id == "BEH-DIO-PN":
        contract = audit._state()["bench_contracts"]["BEH-DIO-PN/B1"]
        expected = numeric_contract(contract["expected"][0])
        # Relocate the source stimulus rather than treating it as a device rating.
        source_deck = (audit.root / contract["file"]).read_text()
        if "dc I1 10m 10m 1m" not in source_deck or _sha_bytes((audit.root / contract["file"]).read_bytes()) != contract["netlist_sha256"]:
            raise ValueError("locked diode forward test condition changed")
        roles = {"A": "anode", "K": "return"}
        supplies = {}
        excitations = [DCExcitation(positive_net="return", negative_net="anode", value=Quantity(value=0.01, unit="A"))]
        comparison = dict(expected, kind="absolute", observable="anode_voltage",
                          analytical_source="BEH-DIO-PN/B1", source_deck_sha256=contract["netlist_sha256"])
        limits = "Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value."
    elif recipe.behavior_id == "BEH-TRN-BJT":
        # Source-defined hFE measurement: VCE=2 V, IC=150 mA for BCX56-16.
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
    return compiled, identity


def _dc_observation(compiled, comparison, output):
    parsed = parse_operating_point(output)
    if comparison["observable"] == "anode_voltage":
        voltage = parsed.node_voltages.get(compiled.node_names["anode"])
        return voltage.value if voltage else None
    if comparison["observable"] == "current_gain":
        current = parsed.branch_currents.get(compiled.source_elements["collector"])
        return abs(current.value) / comparison["base_current"] if current else None
    raise ValueError("unknown probe observable")


def _dc_matches(comparison, value):
    if value is None:
        return False
    if comparison["kind"] == "absolute":
        return abs(value - comparison["expected"]) <= comparison["tolerance"]
    return comparison["minimum"] <= value <= comparison["maximum"]


def run_dc_probes(audit, entry_ids):
    receipts = []
    for entry_id in entry_ids:
        compiled, identity = dc_probe_definition(audit, entry_id)
        relative = f"runtime-bench-output/{entry_id}-op"
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
        _atomic_json(audit.run_dir / f"runtime-bench-results/{entry_id}-op.json", receipt)
        receipts.append(receipt)
    return receipts


def dc_probe_receipt_errors(audit, entry_id):
    compiled, identity = dc_probe_definition(audit, entry_id)
    path = audit.run_dir / f"runtime-bench-results/{entry_id}-op.json"
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
