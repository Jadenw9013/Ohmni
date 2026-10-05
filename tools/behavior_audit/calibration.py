"""Re-derive the TVS calibration receipt from unchanged source facts and raw runs."""

import hashlib
import json
import re

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import load_recipes
from ohmni.eda.simulation import operating_point_deck


def tvs_trial_deck(deck, resistance):
    result, count = re.subn(r"(?m)^(\.model DTVS_\S+ D \([^\n]*?\bRS=)\S+",
                            lambda m: m[1] + format(resistance, ".17g"), deck)
    if count != 1:
        raise ValueError("expected one authored TVS series resistance")
    return result


def tvs_calibration_errors(audit, record=None):
    from .runtime_benches import _dc_observation, dc_probe_definition

    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    recipe = recipes.entries["OHM-069"]
    parameter = recipe.quoted_parameters.get("RDYN")
    if parameter is None:
        return []  # Original authored coefficient has no new calibration claim.
    path = audit.root / parameter.source.document
    record = record if record is not None else json.loads(path.read_text())
    compiled, identity = dc_probe_definition(audit, "OHM-069", "source_bound")
    errors = []
    if record.get("basis") != "DERIVED" or record.get("value_text") != parameter.value_text:
        errors.append("TVS calibration coefficient/provenance differs from recipe")
    contract = record.get("source_contract", {})
    for key in ("entry_id", "class_source_sha256", "entry_research_sha256", "comparison"):
        if contract.get(key) != identity[key]:
            errors.append(f"TVS calibration has stale source {key}")
    original = registry.behavior_class(recipe.behavior_id).canonical_payload["parameters"]["RDYN"]["default"]
    if record.get("original_authored_resistance") != original:
        errors.append("TVS calibration changed the original coefficient baseline")
    trials = record.get("trials", [])
    for index, trial in enumerate(trials, 1):
        output_path = (audit.root / trial["output_path"]).resolve()
        if audit.run_dir.resolve() not in output_path.parents:
            errors.append("TVS calibration output escapes run directory")
            continue
        deck = tvs_trial_deck(compiled.netlist, trial["series_resistance_ohm"])
        if hashlib.sha256(deck.encode()).hexdigest() != trial["netlist_sha256"]:
            errors.append(f"TVS trial {index}: stale model inputs")
        if (output_path.parent / "bench.cir").read_text(encoding="utf-8") != operating_point_deck(deck):
            errors.append(f"TVS trial {index}: executed deck changed")
        raw = output_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != trial["output_sha256"]:
            errors.append(f"TVS trial {index}: raw output changed")
        observed = _dc_observation(compiled, identity["comparison"], raw.decode())
        if observed != trial["observed_voltage"]:
            errors.append(f"TVS trial {index}: observation changed")
        version = (output_path.parent / "version.txt").read_text()
        if version != trial["version_output"] or not re.search(r"\bngspice-42\b", version):
            errors.append(f"TVS trial {index}: version evidence invalid")
        if trial.get("product_code_path") != "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit":
            errors.append(f"TVS trial {index}: product path missing")
    if (not trials or trials[-1]["series_resistance_ohm"] != float(parameter.value_text)
            or trials[-1]["observed_voltage"] != identity["comparison"]["maximum"]):
        errors.append("TVS final calibration does not meet the unchanged source maximum")
    return errors
