"""Recheck the existing analytical contracts after adding current probes."""

from __future__ import annotations

from ohmni.behavior.examples import compile_reference, load_reference_circuits
from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import load_recipes
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point

from .audit import _atomic_json, _atomic_text, _now, _sha_bytes
from .benches import numeric_contract
from .ic_benches import _matches, _observations, ic_cases, ic_definition
from .runtime_benches import (
    _dc_matches,
    _dc_observation,
    dc_probe_definition,
    dc_probe_variants,
    mosfet_case,
)


def compare(audit, key, compiled, output, registry, recipes):
    behavior = recipes.entries[key].behavior_id
    if behavior.startswith("BEH-IC-") or behavior == "BEH-FREQ-XO":
        _, identity = ic_definition(audit, key, ic_cases(behavior, recipes.entries[key])[0])
        observed = _observations(compiled, identity, output)
        passed = all(
            _matches(row, value)
            for row, value in zip(identity["comparison"], observed, strict=True)
        )
        return {"passed": passed, "observed": observed, "comparison": identity["comparison"]}
    if behavior in {"BEH-RES-FIXED", "BEH-TRN-MOSFET"}:
        point = parse_operating_point(output)
        contract = audit._state()["bench_contracts"][behavior + "/B1"]
        source = audit.root / contract["file"]
        assert _sha_bytes(source.read_bytes()) == contract["netlist_sha256"]
        if behavior == "BEH-RES-FIXED":
            expected = numeric_contract(
                next(row for row in contract["expected"] if row["measure"] == "v(out)")
            )
            q = point.node_voltages.get(compiled.node_names["middle"])
            observed = q.value if q else None
        else:
            _, bias = mosfet_case(registry, recipes, key)
            q = point.branch_currents.get(compiled.source_elements["drain"])
            observed = bias["drain_voltage"] / abs(q.value) if q and q.value else None
            base = numeric_contract(contract["expected"][0])
            expected = {
                "expected": bias["target_resistance"],
                "tolerance": bias["target_resistance"] * base["tolerance"] / abs(base["expected"]),
            }
        return {
            "passed": observed is not None
            and abs(observed - expected["expected"]) <= expected["tolerance"],
            "observed": observed,
            "comparison": expected,
        }
    _, identity = dc_probe_definition(audit, key, dc_probe_variants(behavior)[0])
    observed = _dc_observation(compiled, identity["comparison"], output)
    return {
        "passed": _dc_matches(identity["comparison"], observed),
        "observed": observed,
        "comparison": identity["comparison"],
    }


def run_instrumented(audit):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    data = load_reference_circuits(registry, recipes, audit.root)
    rows = []
    for key, row in data["examples"].items():
        compiled, options = compile_reference(row, registry, recipes)
        relative = f"instrumented-output/{key}"
        result = NgspiceAdapter().behavior_circuit(
            compiled, work_dir=audit.run_dir / relative, rating_registry=registry, **options
        )
        output = result.get("stdout", "") + result.get("stderr", "")
        compared = compare(audit, key, compiled, output, registry, recipes)
        receipt = {
            "entry_id": key,
            "ran_at": _now(),
            "run_id": audit._state()["run_id"],
            "netlist_sha256": compiled.netlist_sha256,
            "observation_status": result["status"],
            "version_output": result["version_output"],
            "comparison": compared,
            "rating_status": result["rating_status"],
            "ratings": result.get("ratings"),
            "output_sha256": _sha_bytes(output.encode()),
            "raw_output": relative + "/output.txt",
            "limits": "Same limited analytical contract with zero-volt current probes. Missing thermal context and unsupported failure rules remain unknown.",
        }
        _atomic_text(audit.run_dir / relative / "output.txt", output)
        _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
        _atomic_json(audit.run_dir / f"instrumented-results/{key}.json", receipt)
        rows.append(receipt)
    return rows


def instrumented_receipt_errors(audit):
    import json

    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    data = load_reference_circuits(registry, recipes, audit.root)
    errors = []
    comparisons = []
    from ohmni.behavior.ratings import evaluate_ratings

    for key, row in data["examples"].items():
        path = audit.run_dir / f"instrumented-results/{key}.json"
        if not path.is_file():
            errors.append(f"{key}: missing instrumented receipt")
            continue
        receipt = json.loads(path.read_text(encoding="utf-8"))
        compiled, options = compile_reference(row, registry, recipes)
        output = (audit.run_dir / receipt["raw_output"]).read_text(encoding="utf-8")
        version = (audit.run_dir / f'instrumented-output/{key}/version.txt').read_text(encoding='utf-8')
        if version != receipt['version_output']:
            errors.append(f'{key}: version artifact differs from receipt')
        compared = compare(audit, key, compiled, output, registry, recipes)
        comparisons.append(compared["passed"])
        if (
            receipt["observation_status"] != "ran"
            or "ngspice-42" not in receipt["version_output"]
            or receipt["netlist_sha256"] != compiled.netlist_sha256
            or receipt["comparison"] != compared
            or receipt["output_sha256"] != _sha_bytes(output.encode())
        ):
            errors.append(f"{key}: stale or non-run instrumented evidence")
        result = {
            "status": receipt["observation_status"],
            "analysis": options["analysis"],
            "operating_point": parse_operating_point(output).model_dump(mode="json")
            if options["analysis"] == "op"
            else None,
        }
        ratings = evaluate_ratings(compiled, result, registry)
        if ratings != receipt["ratings"] or ratings["status"] != receipt["rating_status"]:
            errors.append(f"{key}: rating observations do not reproduce")
    return {
        "evidence_errors": errors,
        "comparison_passed": sum(comparisons),
        "comparison_failed": len(comparisons) - sum(comparisons),
    }
