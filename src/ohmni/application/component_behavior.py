"""Read-only reference learning runs, isolated from projects and manufacturing."""

from __future__ import annotations

import threading
import uuid

from ..behavior.examples import compile_reference, load_reference_circuits
from ..behavior.loader import BehaviorRegistry
from ..behavior.netlist import load_recipes
from ..eda.simulation import NgspiceAdapter


class BehaviorRunBusy(ValueError):
    pass


class ComponentBehaviorService:
    def __init__(self, root, output_root, *, adapter=None):
        self.registry = BehaviorRegistry(repo_root=root)
        self.recipes = load_recipes(self.registry, root)
        self.data = load_reference_circuits(self.registry, self.recipes, root)
        self.output_root = output_root
        self.adapter = adapter or NgspiceAdapter(timeout_seconds=90)
        self._run_lock = threading.Lock()

    def behavior_state(self, entry_id):
        """Same rule as the audit's coverage count: a bound runtime recipe and a simulable record."""
        entry = self.registry.entry(entry_id)
        recipe = self.recipes.entries.get(entry_id)
        if recipe and entry.simulation_disposition.value == "simulable":
            return "simulated", None
        if recipe:
            return "reference_only", entry.simulation_reason
        return "documented", entry.simulation_reason

    def summary(self):
        states = {}
        for entry_id in sorted(self.registry.entries):
            state, reason = self.behavior_state(entry_id)
            states[entry_id] = {"state": state, "reason": reason}
        return states

    def describe(self, entry_id):
        entry = self.registry.entry(entry_id)
        recipe = self.recipes.entries.get(entry_id)
        state, state_reason = self.behavior_state(entry_id)
        classes = [
            self.registry.behavior_class(key)
            for key in ([recipe.behavior_id] if recipe else entry.behavior_class_ids)
        ]
        blockers = (
            []
            if recipe
            else [self.data["blocked"].get(entry_id, "No sourced executable reference binding")]
        )
        return {
            "entry_id": entry_id,
            "name": entry.component,
            "source_status": entry.status.value,
            "available": bool(recipe),
            "behavior_state": state,
            "behavior_state_reason": state_reason,
            "reference_part": (recipe.reference_part or f"Scoped {recipe.package} reference") if recipe else None,
            "package": recipe.package if recipe else None,
            "blockers": blockers,
            "classes": [
                {
                    "behavior_id": c.behavior_id,
                    "layer": c.layer.value,
                    "fidelity": c.fidelity.value,
                    "confidence": c.canonical_payload.get("confidence", {}),
                }
                for c in classes
            ],
            "limitations": recipe.limitations
            if recipe
            else entry.research.remaining_open_items
            if entry.research
            else [],
            "scope": "Authored reference test circuit. This run does not simulate or change a saved project.",
            "analysis": self.data["examples"][entry_id]["analysis"] if recipe else None,
        }

    def run(self, entry_id):
        metadata = self.describe(entry_id)
        if not metadata["available"]:
            return {
                "entry_id": entry_id,
                "status": "not_run",
                "rating_status": "not_run",
                "problems": metadata["blockers"],
                "components": [],
                "operating_point": None,
                "transient": None,
                "version_output": "",
                "scope": metadata["scope"],
            }
        if not self._run_lock.acquire(blocking=False):
            raise BehaviorRunBusy("A reference run is already active")
        try:
            compilation, options = compile_reference(
                self.data["examples"][entry_id], self.registry, self.recipes
            )
            run_id = uuid.uuid4().hex
            result = self.adapter.behavior_circuit(
                compilation,
                work_dir=self.output_root / run_id,
                rating_registry=self.registry,
                **options,
            )
            # Public projection excludes local paths and raw executable output.
            projection = {
                key: result.get(key)
                for key in (
                    "status",
                    "rating_status",
                    "ratings",
                    "version_output",
                    "analysis",
                    "problems",
                    "netlist_sha256",
                    "circuit_hash",
                    "limitations",
                )
            }
            projection.update(
                entry_id=entry_id, run_id=run_id, scope=metadata["scope"], components=[]
            )
            point = result.get("operating_point") or {}
            for component in compilation.components:
                measurements = []
                if result["status"] == "ran":
                    for role, node in component.role_nodes.items():
                        voltage = point.get("node_voltages", {}).get(node.lower())
                        if node == "0" and point:
                            voltage = {"value": 0, "unit": "V"}
                        probe = component.role_current_probes.get(role)
                        current = (
                            point.get("branch_currents", {}).get(probe.lower()) if probe else None
                        )
                        measurements.append(
                            {"role": role, "voltage": voltage, "current_into_pin": current}
                        )
                projection["components"].append(
                    {
                        "ref": component.ref,
                        "entry_id": component.entry_id,
                        "reference_part": component.reference_part,
                        "fidelity": component.fidelity.value,
                        "source_status": component.source_status,
                        "confidence": component.confidence,
                        "rating_confidence": component.rating_confidence,
                        "measurements": measurements,
                    }
                )
            projection["transient"] = result.get("transient") if result["status"] == "ran" else None
            if projection["transient"]:
                names = {f"v({node})": name for name, node in compilation.node_names.items()}
                projection["transient"] = {
                    **projection["transient"],
                    "series": [
                        {**s, "name": names.get(s["name"], s["name"])}
                        for s in projection["transient"]["series"]
                    ],
                }
            projection["failure_rerun"] = None
            if result.get("failure_rerun"):
                rerun = result["failure_rerun"]
                projection["failure_rerun"] = {
                    key: rerun.get(key)
                    for key in (
                        "status",
                        "rating_status",
                        "version_output",
                        "limitation",
                        "netlist_sha256",
                    )
                }
            return projection
        finally:
            self._run_lock.release()
