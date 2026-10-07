"""Reproduce a bounded series-resistance fit against the sourced clamp point.

This authors a model coefficient, never a device rating or vendor model. It
uses the product ngspice adapter and retains every trial. The legacy class
parameter and benchmark contract remain untouched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.eda.simulation import NgspiceAdapter
from tools.behavior_audit.audit import BehaviorAudit, _atomic_json, _atomic_text
from tools.behavior_audit.calibration import tvs_calibration_errors, tvs_trial_deck
from tools.behavior_audit.runtime_benches import _dc_observation, dc_probe_definition


def bracket_fit(observe, lower, upper, target, max_trials=40):
    """Bisect a monotone model coefficient without changing the target."""
    lo_value, hi_value = observe(lower), observe(upper)
    if lo_value > target or hi_value < target:
        raise ValueError("source target is not bracketed by the model")
    for _ in range(max_trials):
        middle = (lower + upper) / 2
        value = observe(middle)
        if value == target:
            return middle
        if value < target:
            lower = middle
        else:
            upper = middle
    raise ValueError("fit did not reach the unchanged source target at captured solver precision")


def main():
    root = Path(__file__).resolve().parents[1]
    audit = BehaviorAudit(root)
    output_path = root / "docs/behavior/calibration/OHM-069.json"
    recipes_path = root / "docs/behavior/runtime-recipes.json"
    recipes = json.loads(recipes_path.read_text())
    if (output_path.exists() and "RDYN" in recipes["entries"]["OHM-069"].get("quoted_parameters", {})
            and not tvs_calibration_errors(audit)):
        print("Existing calibration is current; no fit rerun needed")
        return
    compiled, identity = dc_probe_definition(audit, "OHM-069", "source_bound")
    if not compiled.runnable:
        raise ValueError(compiled.problems)
    registry = BehaviorRegistry(repo_root=root)
    original = registry.behavior_class("BEH-DIO-TVS").canonical_payload["parameters"]["RDYN"]["default"]
    target = identity["comparison"]["maximum"]
    trials = []

    def observe(resistance):
        deck = tvs_trial_deck(compiled.netlist, resistance)
        digest = hashlib.sha256(deck.encode()).hexdigest()
        candidate = compiled.model_copy(update={"netlist": deck, "netlist_sha256": digest})
        folder = audit.run_dir / "calibration-output/OHM-069" / str(len(trials) + 1)
        result = NgspiceAdapter().behavior_circuit(candidate, work_dir=folder)
        if result["status"] != "ran":
            _atomic_json(folder / "failure.json", result)
            raise ValueError("calibration trial did not run: " + result.get("stderr", ""))
        output = result["stdout"] + result["stderr"]
        observed = _dc_observation(candidate, identity["comparison"], output)
        if observed is None:
            raise ValueError("calibration observation unavailable")
        _atomic_text(folder / "output.txt", output)
        _atomic_text(folder / "version.txt", result["version_output"])
        trials.append({"series_resistance_ohm": resistance, "observed_voltage": observed,
                       "netlist_sha256": digest, "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
                       "output_path": (folder / "output.txt").relative_to(root).as_posix(),
                       "version_output": result["version_output"], "product_code_path": result["product_code_path"]})
        return observed

    fitted = bracket_fit(observe, 0, original, target)
    value_text = format(fitted, ".17g")
    record = {"entry_id": "OHM-069", "basis": "DERIVED", "confidence": "M",
              "scope": "Isothermal 25 C maximum-corner static curve, not a typical curve or a safe pulse envelope",
              "method": "Bisection of the authored model's series resistance against the unchanged sourced VC at IPP. The source formula defines the series resistance as the residual voltage drop divided by current; the solver includes the nonlinear junction and leakage terms.",
              "method_source": "COMPONENT_BEHAVIOR_SPEC.md:4127",
              "parameter": "RDYN", "value_text": value_text, "unit": "ohm",
              "original_authored_resistance": original, "source_contract": identity,
              "trials": trials, "limitations": "Calibration at one point does not establish surge-waveform, thermal, leakage, capacitance, failure timing or protected-load behavior."}
    _atomic_json(output_path, record)
    recipe = recipes["entries"]["OHM-069"]
    recipe["class_parameters"].pop("RDYN", None)
    recipe["quoted_parameters"] = {"RDYN": {
        "value_text": value_text, "unit": "ohm", "basis": "DERIVED", "confidence": "M",
        "source_fragment": f'"value_text": "{value_text}"',
        "source": {"document": output_path.relative_to(root).as_posix(), "line": 1,
                   "document_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()}}}
    recipe["limitations"][-1] = "The original rounded 0.266 ohm fit exceeded the source maximum. A separately recorded ngspice calibration changes only the runtime coefficient; source values and legacy class/bench contracts remain unchanged."
    _atomic_json(recipes_path, recipes)
    print(json.dumps({"coefficient": fitted, "target": target, "trials": len(trials)}))


if __name__ == "__main__":
    main()
