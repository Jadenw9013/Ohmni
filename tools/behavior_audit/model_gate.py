"""Script-derived model coverage and measurement limits at a Stage 3 checkpoint."""

from collections import Counter

from ohmni.behavior.loader import BehaviorRegistry
from ohmni.behavior.netlist import entry_problems, load_recipes

from .audit import _atomic_text, _json
from .runtime_benches import runtime_receipt_errors


def write_model_gate(audit):
    registry = BehaviorRegistry(repo_root=audit.root)
    recipes = load_recipes(registry, audit.root)
    state = audit._state()
    receipts = [_json(p) for p in sorted((audit.run_dir / "runtime-bench-results").glob("*.json"))]
    counts = Counter(r["run_status"] for r in receipts)
    valid = {key: runtime_receipt_errors(audit, key) for key in recipes.entries}
    lines = ["# Stage 3 model checkpoint", "", "> Generated from recipes, scoped records and revalidated runtime receipts.", "",
             f"Registered bindings: {len(recipes.entries)}. Bindings with current passing runtime comparisons: {sum(not errors for errors in valid.values())}.",
             f"Runtime comparison results: {dict(sorted(counts.items()))}.",
             "This is an in-progress checkpoint, not stage acceptance. Runtime comparisons only cover the measurement stated in each receipt; they do not establish complete model accuracy, ratings or safe operation.", "",
             "| Entry | Source status before → after | Bound reference | Runtime comparisons / blockers |",
             "| --- | --- | --- | --- |"]
    for number in range(1, 103):
        entry_id = f"OHM-{number:03}"
        entry = registry.entry(entry_id)
        recipe = recipes.entries.get(entry_id)
        before = state["entry_status"][entry_id]["before"]
        issues = valid.get(entry_id) if recipe else entry_problems(entry, None)
        reference = (recipe.reference_part or "Scoped package record") if recipe else "Unbound"
        text = "; ".join(issues) if issues else "Current runtime comparisons pass; limits below apply"
        lines.append(f"| {entry_id} | {before} → {entry.status.value} | {reference} | {text.replace('|', '/')} |")
    lines.extend(["", "## Captured measurements", ""])
    for receipt in receipts:
        entry_id = receipt["entry_id"]
        comparison = receipt.get("comparison", receipt.get("expected"))
        observed = receipt.get("observed", receipt.get("observed_resistance", receipt.get("observations")))
        if isinstance(observed, list):
            observed = {"samples": len(observed), "minimum": min(observed) if observed else None,
                        "maximum": max(observed) if observed else None}
        lines.extend([f"### {entry_id} / {receipt['analysis']}", "",
                      f"- Recorded comparison: {receipt['run_status']}.",
                      f"- Contract: {comparison}.", f"- Captured observation: {observed}.",
                      f"- Limits: {receipt['limits']}", ""])
    output = audit.root / "out/component-behavior/stage-3/MODEL-GATE.md"
    _atomic_text(output, "\n".join(lines))
    return output
