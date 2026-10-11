"""Read-only reference learning runs, isolated from projects and manufacturing."""

from __future__ import annotations

import re
import threading
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..behavior.examples import compile_reference, load_reference_circuits
from ..behavior.loader import BehaviorRegistry
from ..behavior.netlist import compile_circuit, load_recipes
from ..behavior.ratings import RatingContext
from ..behavior.runtime_models import ACExcitation, BehaviorSelection, DCExcitation, PWLExcitation
from ..catalog.loader import default_catalog
from ..domain.circuit import CircuitIR
from ..eda.simulation import NgspiceAdapter

MAX_DESIGN_COMPONENTS = 40
MAX_DESIGN_NETS = 120
DESIGN_SCOPE = (
    "Runs your circuit with the sourced reference model bound to each part. Every part must be an "
    "audited simulable entry; a part that is not stops the whole run instead of being guessed. "
    "Nothing here changes a saved project, and a rating that cannot be proven is reported unknown."
)
DESIGN_LIMITATIONS = [
    ("Each part is checked against its own sourced limits; copper heating, trace resistance, layout "
     "parasitics and source current capability are not simulated."),
    ("A part runs on its bound reference model, named per part; a different manufacturer's part in the "
     "same package can behave differently."),
]
_COLOURS = ("red", "green", "blue", "white", "yellow", "orange", "amber")


class BehaviorRunBusy(ValueError):
    pass


class ACSweep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    start_hz: float = Field(gt=0)
    stop_hz: float = Field(gt=0)
    points_per_decade: int = Field(ge=1, le=50)


class DesignRunRequest(BaseModel):
    """A user's own circuit plus the explicit choices a design run needs; nothing is defaulted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    circuit: CircuitIR
    selections: dict[str, BehaviorSelection] = Field(default_factory=dict)
    analysis: Literal["op", "tran", "ac"] = "op"
    excitations: list[DCExcitation | PWLExcitation | ACExcitation] = Field(default_factory=list, max_length=8)
    ac_points_hz: list[float] = Field(default_factory=list, max_length=8)
    ac_sweep: ACSweep | None = None
    tstep: str | None = None
    tstop: str | None = None
    observe_nets: list[str] | None = None
    rating_context: RatingContext = Field(default_factory=RatingContext)


class ComponentBehaviorService:
    def __init__(self, root, output_root, *, adapter=None):
        self.registry = BehaviorRegistry(repo_root=root)
        self.recipes = load_recipes(self.registry, root)
        self.data = load_reference_circuits(self.registry, self.recipes, root)
        self.output_root = output_root
        self.adapter = adapter or NgspiceAdapter(timeout_seconds=90)
        self._run_lock = threading.Lock()

    def behavior_state(self, entry_id):
        """Same rule as the audit's coverage count: a bound runtime recipe and a simulable record.

        The reason names the actual blocker for this entry, not the class-level sentence the spec
        projects (QA-01/QA-02): a documented-only entry reports its recorded model blocker, and a
        reference-only entry reports what keeps its record from being simulable even though a
        sourced reference part is bound.
        """
        entry = self.registry.entry(entry_id)
        recipe = self.recipes.entries.get(entry_id)
        if recipe and entry.simulation_disposition.value == "simulable":
            if recipe.reference_part and 103 <= int(entry_id.split("-")[1]) <= 140:
                # D066: a package simulates only as the exact part bound to it; say which.
                return "simulated", f"Simulates as the sourced reference part bound to this package ({recipe.reference_part})."
            if entry.layer.value == "L3":
                # D066 item 3: say plainly that only the electrical pins are simulated.
                return "simulated", entry.simulation_reason
            return "simulated", None
        blocker = self.data["blocked"].get(entry_id)
        if recipe:
            part = recipe.reference_part or f"a scoped {recipe.package} reference"
            if entry.simulation_disposition.value == "not_simulable" and entry.layer.value == "L3":
                # D071: a bound L3 entry is not simulable only while the spec lists it as research_required.
                reason = (f"A sourced reference ({part}) runs as an electrical model only, but the protected "
                          "spec lists this entry as research_required, so its record stays not simulable "
                          "until the owner changes that status; protocol, firmware or controller behavior "
                          "(L3) is not modeled either way.")
            elif (entry.simulation_disposition.value == "not_simulable"
                  and not 103 <= int(entry_id.split("-")[1]) <= 140):
                reason = (f"A sourced reference ({part}) runs, but the protected spec lists this entry as "
                          "research_required, so its record stays not simulable until the owner changes "
                          "that status.")
            elif entry.simulation_disposition.value == "not_simulable":
                reason = (f"A sourced reference ({part}) runs, but the catalog record for this package stays "
                          "not simulable: the package itself has no electrical function, and the spec counts "
                          "only the bound reference, not the package, as verified.")
            else:
                reason = f"A sourced reference ({part}) runs; its record is not yet audited as simulable."
            return "reference_only", reason
        if blocker:
            return "documented", blocker
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
            "scope": "Runs an authored reference test circuit for this part; it does not touch any saved project.",
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
            projection = self._project(compilation, result)
            projection.update(entry_id=entry_id, run_id=run_id, scope=metadata["scope"])
            return projection
        finally:
            self._run_lock.release()

    def _candidates(self, component):
        binding = self.registry.bindings.get(component.part_id)
        bound = set(binding.entry_ids) if binding else set()
        return sorted(
            key
            for key, recipe in self.recipes.entries.items()
            if recipe.package == component.package
            and (component.part_id == key or component.part_id in recipe.catalog_parts or key in bound)
        )

    def _colour_problem(self, component, recipe):
        spec = default_catalog().get(component.part_id)
        colour = getattr(getattr(spec, "led", None), "colour", None)
        if not colour:
            return None
        text = (recipe.reference_part or "").lower()
        named = [c for c in _COLOURS if re.search(rf"\b{c}\b", text)]
        if named == [colour.lower()]:
            return None
        reference = recipe.reference_part or recipe.entry_id
        return (f"The catalog part is a {colour} LED but the bound reference is {reference}; another colour "
                "has a different forward voltage, so it is not substituted")

    def design_bindings(self, request):
        """Resolve every part to an audited simulable entry, or say exactly why it cannot be."""
        circuit = request.circuit
        problems = []
        if len(circuit.components) > MAX_DESIGN_COMPONENTS or len(circuit.nets) > MAX_DESIGN_NETS:
            # Refuse before resolving any part: the bound keeps a run's work bounded too.
            return [], [f"A design run is limited to {MAX_DESIGN_COMPONENTS} parts and {MAX_DESIGN_NETS} nets"]
        refs = {c.ref for c in circuit.components}
        for ref in sorted(set(request.selections) - refs):
            problems.append(f"{ref}: a selection names a part that is not in this circuit")
        rows = []
        for component in sorted(circuit.components, key=lambda c: c.ref):
            candidates = self._candidates(component)
            chosen = request.selections.get(component.ref)
            row = {
                "ref": component.ref,
                "part_id": component.part_id,
                "package": component.package,
                "candidates": candidates,
                "entry_id": None,
                "reference_part": None,
                "behavior_state": None,
                "problem": None,
            }
            entry_id = chosen.entry_id if chosen else candidates[0] if len(candidates) == 1 else None
            if entry_id is None:
                row["problem"] = (
                    "Several sourced entries fit this part; choose one explicitly: " + ", ".join(candidates)
                    if candidates
                    else "No sourced behavior entry is bound to this catalog part and package"
                )
            elif entry_id not in self.registry.entries:
                row["problem"] = f"Unknown behavior entry {entry_id}"
            else:
                state, reason = self.behavior_state(entry_id)
                recipe = self.recipes.entries.get(entry_id)
                row.update(
                    entry_id=entry_id,
                    behavior_state=state,
                    reference_part=(recipe.reference_part or f"Scoped {recipe.package} reference")
                    if recipe
                    else None,
                )
                if state != "simulated":
                    row["problem"] = reason or "This entry is not audited simulable"
                elif entry_id not in candidates:
                    row["problem"] = "This catalog part and package are not bound to the selected entry"
                else:
                    row["problem"] = self._colour_problem(component, recipe)
            if row["problem"]:
                problems.append(f"{component.ref}: {row['problem']}")
            rows.append(row)
        return rows, problems

    def run_design(self, request):
        """Compile and run a user's multi-part circuit; every part's ratings are checked together."""
        rows, problems = self.design_bindings(request)
        refused = {
            "status": "not_run",
            "rating_status": "not_run",
            "ratings": None,
            "analysis": request.analysis,
            "problems": problems,
            "limitations": [],
            "components": [],
            "transient": None,
            "failure_rerun": None,
            "bindings": rows,
            "design_summary": None,
            "circuit_hash": request.circuit.content_hash,
            "scope": DESIGN_SCOPE,
        }
        if problems:
            return refused
        selections = {row["ref"]: BehaviorSelection(entry_id=row["entry_id"]) for row in rows}
        compilation = compile_circuit(
            request.circuit,
            self.registry,
            self.recipes,
            selections,
            analysis=request.analysis,
            excitations=list(request.excitations),
            measure_currents=True,
        )
        if not compilation.runnable:
            return {**refused, "problems": list(compilation.problems)}
        options = {}
        if request.analysis == "tran":
            options.update({k: v for k, v in (("tstep", request.tstep), ("tstop", request.tstop)) if v})
        if request.analysis in {"tran", "ac"} and request.observe_nets is not None:
            options["observe_nets"] = list(request.observe_nets)
        if request.analysis == "ac":
            options["ac_points_hz"] = list(request.ac_points_hz)
            if request.ac_sweep:
                sweep = request.ac_sweep
                options["ac_sweep"] = (sweep.start_hz, sweep.stop_hz, sweep.points_per_decade)
        if not self._run_lock.acquire(blocking=False):
            raise BehaviorRunBusy("A behavior run is already active")
        try:
            run_id = uuid.uuid4().hex
            result = self.adapter.behavior_circuit(
                compilation,
                work_dir=self.output_root / run_id,
                analysis=request.analysis,
                rating_context=request.rating_context.model_dump(mode="json"),
                rating_registry=self.registry,
                **options,
            )
        finally:
            self._run_lock.release()
        projection = self._project(compilation, result)
        projection["limitations"] = [*(projection["limitations"] or []), *DESIGN_LIMITATIONS]
        projection.update(run_id=run_id, scope=DESIGN_SCOPE, bindings=rows,
                          design_summary=design_summary(result.get("ratings")))
        return projection

    @staticmethod
    def _project(compilation, result):
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
        projection["components"] = []
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
        projection["ac"] = result.get("ac") if result["status"] == "ran" else None
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


def design_summary(ratings):
    """Count part verdicts; a design is within limits only when every part is, never by majority."""
    if not ratings:
        return None
    counts = {"within_model_limits": 0, "unknown": 0, "violation": 0}
    unknown, violations = [], []
    for row in ratings["components"]:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        if row["status"] == "violation":
            violations.append(row["ref"])
        elif row["status"] != "within_model_limits":
            unknown.append(row["ref"])
    return {"status": ratings["status"], "counts": counts, "unknown_parts": unknown, "violating_parts": violations}
