"""Actual ngspice rating and failure-substitution probes with revalidated output."""

from __future__ import annotations

import json

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.ratings import RatingContext, evaluate_ratings
from ohmni.behavior.runtime_models import BehaviorSelection
from ohmni.domain.circuit import ExternalSource
from ohmni.domain.units import Quantity, ValueRange
from ohmni.eda.simulation import NgspiceAdapter, parse_operating_point

from .audit import _atomic_json, _atomic_text, _now, _sha_bytes
from .benches import numeric_contract
from .runtime_benches import resistor_divider

CASES = {
    "within_stated_conditions": (5, True, "within_model_limits", False),
    "over_voltage": (80, True, "violation", False),
    "modeled_open": (300, True, "violation", True),
    "unknown_mounting": (5, False, "unknown", False),
}


def definition(audit, case):
    voltage, known, expected, rerun = CASES[case]
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    circuit = resistor_divider("OHM-004", recipes.entries["OHM-004"].package)
    circuit.nets[0].external_source = ExternalSource(
        kind="bench_supply", voltage=ValueRange.exact(Quantity.volts(voltage))
    )
    compiled = compile_circuit(
        circuit,
        registry,
        recipes,
        {c.ref: BehaviorSelection(entry_id="OHM-004") for c in circuit.components},
        measure_currents=True,
    )
    contract = audit._state()["bench_contracts"]["BEH-RES-FIXED/B1"]
    source = audit.root / contract["file"]
    assert _sha_bytes(source.read_bytes()) == contract["netlist_sha256"]
    row = numeric_contract(next(x for x in contract["expected"] if x["measure"] == "v(out)"))
    # Same divider equation and absolute tolerance; stimulus scale is explicit.
    identity = {
        "case": case,
        "netlist_sha256": compiled.netlist_sha256,
        "circuit_hash": compiled.circuit_hash,
        "recipe_sha256": recipes.source.document_sha256,
        "analytical_source": "BEH-RES-FIXED/B1",
        "source_deck_sha256": contract["netlist_sha256"],
        "expected_voltage": row["expected"] * voltage / 5,
        "tolerance": row["tolerance"],
        "expected_rating_status": expected,
        "expected_fault_rerun": rerun,
        "rating_context": RatingContext(
            ambient_c=25 if known else None, thermal_scope_confirmed=known
        ).model_dump(mode="json"),
        "limits": "Synthetic source mounting condition for equation testing, not evidence of a real board thermal path. The failure rerun is an authored approximation.",
    }
    return registry, compiled, identity


def run_rating_probes(audit):
    receipts = []
    for case in CASES:
        registry, compiled, identity = definition(audit, case)
        relative = f"rating-bench-output/{case}"
        result = NgspiceAdapter().behavior_circuit(
            compiled,
            work_dir=audit.run_dir / relative,
            rating_context=RatingContext(**identity["rating_context"]),
            rating_registry=registry,
        )
        output = result.get("stdout", "") + result.get("stderr", "")
        _atomic_text(audit.run_dir / relative / "output.txt", output)
        _atomic_text(audit.run_dir / relative / "version.txt", result["version_output"])
        receipt = dict(
            identity,
            ran_at=_now(),
            result=result,
            output_sha256=_sha_bytes(output.encode()),
            version_sha256=_sha_bytes(result["version_output"].encode()),
        )
        _atomic_json(audit.run_dir / f"rating-bench-results/{case}.json", receipt)
        receipts.append(receipt)
    errors = rating_receipt_errors(audit)
    _atomic_json(
        audit.run_dir / "RATING_RESULTS.json",
        {
            "passed": not errors,
            "errors": errors,
            "cases": list(CASES),
            "run_id": audit._state()["run_id"],
        },
    )
    return errors


def rating_receipt_errors(audit):
    from ohmni.behavior.ratings import apply_open_faults

    errors = []
    for case in CASES:
        registry, compiled, identity = definition(audit, case)
        path = audit.run_dir / f"rating-bench-results/{case}.json"
        if not path.is_file():
            errors.append(f"{case}: missing receipt")
            continue
        receipt = json.loads(path.read_text(encoding="utf-8"))
        result = receipt["result"]
        for key, value in identity.items():
            if receipt.get(key) != value:
                errors.append(f"{case}: changed {key}")
        if result["status"] != "ran" or "ngspice-42" not in result["version_output"]:
            errors.append(f"{case}: no successful ngspice42 observation")
            continue
        directory = audit.run_dir / f"rating-bench-output/{case}"
        output = (directory / "output.txt").read_bytes()
        version = (directory / "version.txt").read_bytes()
        if (
            _sha_bytes(output) != receipt["output_sha256"]
            or output.decode() != result["stdout"] + result["stderr"]
            or _sha_bytes(version) != receipt["version_sha256"]
            or version.decode() != result["version_output"]
        ):
            errors.append(f"{case}: raw output or version changed")
        deck = (directory / "bench.cir").read_text(encoding="utf-8")
        from ohmni.eda.simulation import operating_point_deck

        if deck != operating_point_deck(compiled.netlist):
            errors.append(f"{case}: emitted deck differs")
        point = parse_operating_point(result["stdout"]).model_dump(mode="json")
        observed = point["node_voltages"].get(compiled.node_names["middle"], {}).get("value")
        if observed is None or abs(observed - identity["expected_voltage"]) > identity["tolerance"]:
            errors.append(f"{case}: analytical divider mismatch")
        recomputed = evaluate_ratings(
            compiled,
            dict(result, operating_point=point),
            registry,
            RatingContext(**identity["rating_context"]),
        )
        if (
            result["ratings"] != recomputed
            or recomputed["status"] != identity["expected_rating_status"]
        ):
            errors.append(f"{case}: rating result mismatch")
        rerun = result.get("failure_rerun")
        if bool(rerun) != identity["expected_fault_rerun"]:
            errors.append(f"{case}: missing/unexpected fault rerun")
        if rerun:
            faulted = apply_open_faults(compiled, recomputed["fault_requests"])
            if (
                rerun.get("status") != "ran"
                or rerun.get("netlist_sha256") != faulted.netlist_sha256
                or "ngspice-42" not in rerun.get("version_output", "")
            ):
                errors.append(f"{case}: invalid modeled failure run")
            after = parse_operating_point(rerun.get("stdout", ""))
            current = after.branch_currents.get(compiled.source_elements["supply"])
            expected = CASES[case][0] / (2e9)
            if current is None or abs(abs(current.value) - expected) > expected * 0.01:
                errors.append(f"{case}: open-circuit current is not the authored 1G-ohm result")
    return errors


def write_rating_gate(audit):
    errors = rating_receipt_errors(audit)
    registry = BehaviorRegistry(repo_root=audit.root)
    inventory = []
    for key, cls in sorted(registry.classes.items()):
        for kind in ("ratings", "failure_modes"):
            for row in cls.canonical_payload.get(kind, []):
                inventory.append({"behavior_id": key, "kind": kind, "declaration": row})
    _atomic_json(
        audit.run_dir / "RATING_EXPRESSION_INVENTORY.json",
        {
            "declarations": inventory,
            "limits": "All declarations are retained. Unsupported grammar, missing scope or missing observations evaluates UNKNOWN. This inventory does not claim all declarations are executable.",
        },
    )
    lines = [
        "# Stage5 ratings and failure gate",
        "",
        f"Executable receipt validation: {'FAIL' if errors else 'PASS'}.",
        f"{len(inventory)} class rating/failure declarations preserved across {len(registry.classes)} classes.",
        "",
        "Four actual ngspice42 probes exercise within-limit, violation, explicit modeled-open rerun and unknown mounting conditions. All source statuses and locked analytical contracts remain unchanged.",
        "",
        "Stage acceptance remains partial: transient peak/RMS/pulse-energy checks, reference thermal context, unbound classes and nonquantitative failure responses remain unknown. No duration or physical damage outcome is invented.",
        "",
        *[f"- {e}" for e in errors],
    ]
    for case in CASES:
        receipt = json.loads(
            (audit.run_dir / f"rating-bench-results/{case}.json").read_text(encoding="utf-8")
        )
        lines.append(
            f"- {case}: simulation {receipt['result']['status']}; ratings {receipt['result']['rating_status']}; failure rerun {bool(receipt['result'].get('failure_rerun'))}."
        )
    _atomic_text(
        audit.root / "out/component-behavior/stage-5/RATING-GATE.md", "\n".join(lines) + "\n"
    )
    return errors
