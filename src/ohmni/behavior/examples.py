"""Typed, fixed reference circuits exported from the authored validation probes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter

from ..domain.circuit import CircuitIR
from .loader import BehaviorRegistryError
from .netlist import compile_circuit
from .runtime_models import BehaviorSelection, DCExcitation, PWLExcitation

DATA_PATH = Path(__file__).with_name("reference-circuits.json")


def load_reference_circuits(registry, recipes, root, *, path=DATA_PATH):
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        data.get("schema_version") != 1
        or data.get("recipe_sha256") != recipes.source.document_sha256
    ):
        raise BehaviorRegistryError("Reference circuits are detached from the runtime recipes")
    generator = root / "scripts/generate_behavior_examples.py"
    if data.get("generator_sha256") != hashlib.sha256(generator.read_bytes()).hexdigest():
        raise BehaviorRegistryError("Reference-circuit generator changed; regenerate its output")
    if set(data["examples"]) != set(recipes.entries):
        raise BehaviorRegistryError("Reference circuits must cover exactly the available bindings")
    for key, row in data["examples"].items():
        if row.get("entry_research_sha256") != registry.entry(key).research.source.document_sha256:
            raise BehaviorRegistryError(f"{key}: reference-circuit research is stale")
        if row.get("entry_id") != key or row.get("package") != recipes.entries[key].package:
            raise BehaviorRegistryError(f"{key}: reference selection mismatch")
    if set(data["blocked"]) & set(data["examples"]):
        raise BehaviorRegistryError("A reference cannot be both blocked and bound")
    return data


def compile_reference(row, registry, recipes, *, measure_currents=True):
    circuit = CircuitIR.model_validate(row["circuit"])
    selections = {
        ref: BehaviorSelection.model_validate(value) for ref, value in row["selections"].items()
    }
    excitations = TypeAdapter(list[DCExcitation | PWLExcitation]).validate_python(
        row["excitations"]
    )
    compiled = compile_circuit(
        circuit,
        registry,
        recipes,
        selections,
        analysis=row["analysis"],
        excitations=excitations,
        measure_currents=False,
    )
    if compiled.netlist_sha256 != row["original_netlist_sha256"]:
        raise BehaviorRegistryError("Reference circuit no longer reproduces its authored probe")
    if measure_currents:
        compiled = compile_circuit(
            circuit,
            registry,
            recipes,
            selections,
            analysis=row["analysis"],
            excitations=excitations,
            measure_currents=True,
        )
    if set(row["options"]) - {"tstep", "tstop", "observe_nets"}:
        raise BehaviorRegistryError("Unsupported reference run option")
    return compiled, dict(row["options"], analysis=row["analysis"])
