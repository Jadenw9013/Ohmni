"""Exercise compiled CircuitIR bindings against an existing analytical contract."""

from __future__ import annotations

import json
import re

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.runtime_models import BehaviorSelection
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
