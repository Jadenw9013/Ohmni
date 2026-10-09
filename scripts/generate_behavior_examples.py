"""Export existing authored probe circuits as reproducible, explicit test inputs.

The application consumes only the exported CircuitIR data, never audit tools or
arbitrary netlist text. These stimuli are not component ratings or source facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import compile_circuit, load_recipes
from ohmni.behavior.runtime_models import BehaviorSelection
from tools.behavior_audit import ic_benches, runtime_benches
from tools.behavior_audit.audit import BehaviorAudit

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src/ohmni/behavior/reference-circuits.json"


def generate(root=ROOT):
    registry = BehaviorRegistry(repo_root=root)
    recipes = load_recipes(registry, root)
    audit = BehaviorAudit(root)
    examples = {}
    for key, recipe in sorted(recipes.entries.items()):
        captured = {}

        def capture(circuit, registry, recipes, selections=None, _captured=captured, **kwargs):
            _captured.update(circuit=circuit.model_dump(mode="json"),
                            selections={ref: value.model_dump(mode="json") for ref, value in (selections or {}).items()},
                            excitations=[x.model_dump(mode="json") for x in kwargs.get("excitations", [])],
                            analysis=kwargs.get("analysis", "op"))
            return compile_circuit(circuit, registry, recipes, selections, **kwargs)

        original = runtime_benches.compile_circuit, ic_benches.compile_circuit
        runtime_benches.compile_circuit = ic_benches.compile_circuit = capture
        try:
            if recipe.behavior_id == "BEH-RES-FIXED":
                circuit = runtime_benches.resistor_divider(key, recipe.package)
                compiled = capture(circuit, registry, recipes, {c.ref: BehaviorSelection(entry_id=key) for c in circuit.components})
                identity = {"analytical_source": "BEH-RES-FIXED/B1"}
            elif recipe.behavior_id == "BEH-TRN-MOSFET":
                compiled, _ = runtime_benches.mosfet_case(registry, recipes, key)
                identity = {"analytical_source": "BEH-TRN-MOSFET/B1"}
            elif recipe.behavior_id.startswith("BEH-IC-") or recipe.behavior_id == "BEH-FREQ-XO":
                case = ic_benches.ic_cases(recipe.behavior_id, recipe)[0]
                compiled, identity = ic_benches.ic_definition(audit, key, case)
            elif recipe.behavior_id in runtime_benches.TRAN_PROBES:
                compiled, identity = runtime_benches.tran_probe_definition(audit, key)
            else:
                variant = runtime_benches.dc_probe_variants(recipe.behavior_id, recipe)[0]
                compiled, identity = runtime_benches.dc_probe_definition(audit, key, variant)
            if not compiled.runnable:
                raise ValueError(f"{key}: {compiled.problems}")
            captured.update(entry_id=key, package=recipe.package, reference_part=recipe.reference_part,
                            original_netlist_sha256=compiled.netlist_sha256,
                            entry_research_sha256=registry.entry(key).research.source.document_sha256,
                            options={k: identity[k] for k in ("tstep", "tstop", "observe_nets") if identity.get(k)},
                            scope="Authored reference test circuit; not your saved design or a physical component qualification.")
            examples[key] = captured
        finally:
            runtime_benches.compile_circuit, ic_benches.compile_circuit = original
    return {"schema_version": 1, "recipe_sha256": recipes.source.document_sha256,
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "examples": examples, "blocked": audit._state()["model_blockers"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = generate()
    expected = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != expected:
            raise SystemExit("Reference circuits are stale; regenerate with this script")
    else:
        TARGET.write_text(expected, encoding="utf-8", newline="\n")
    print(f"{len(data['examples'])} authored reference circuits exported and validated")


if __name__ == "__main__":
    main()
