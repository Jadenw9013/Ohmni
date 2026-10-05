"""Deterministic, fail-closed translation from CircuitIR to authored models.

No source fetching, fitting, solver or rating verdict lives here. A recipe is
an explicit join between the package and its sourced behavior record.
"""

from __future__ import annotations

import hashlib
import math
import re

from ..domain.circuit import CircuitIR, NetKind
from .loader import BehaviorRegistry, BehaviorRegistryError, _json, _validate_anchor
from .runtime_models import (
    BehaviorCompilation,
    BehaviorSelection,
    CompiledComponent,
    RuntimeRecipe,
    RuntimeRecipes,
)


def load_recipes(registry: BehaviorRegistry, root) -> RuntimeRecipes:
    recipes = RuntimeRecipes.model_validate(_json(registry.directory / "runtime-recipes.json"))
    _validate_anchor(root, recipes.source, "runtime recipes")
    for key, recipe in recipes.entries.items():
        if key != recipe.entry_id:
            raise BehaviorRegistryError(f"runtime recipe key differs from entry: {key}")
        if recipe.behavior_id not in registry.entry(key).behavior_class_ids:
            raise BehaviorRegistryError(f"runtime recipe class differs from entry: {key}")
    return recipes


def terminal_nodes(circuit, component, entry_id, terminal_roles, registry, nodes, identity_map=None):
    """Catalog numbers are never assumed to be physical terminal numbers."""
    by_pin = {pin.pin: nodes[net.name] for net in circuit.nets
              for pin in net.connections if pin.component == component.ref}
    if component.part_id in registry.bindings:
        binding = registry.binding(component.part_id)
        if entry_id not in binding.entry_ids:
            raise ValueError("catalog binding does not target the selected entry")
        order = binding.package(component.package)
        if order.package_terminal_roles != terminal_roles:
            raise ValueError("recipe terminal roles disagree with approved catalog permutation")
        mapping = order.catalog_to_package_terminal
    elif component.part_id == entry_id:
        mapping = {pin: pin for pin in terminal_roles}
    elif identity_map:
        mapping = identity_map
        if any(pin != terminal for pin, terminal in mapping.items()) or set(mapping.values()) != set(terminal_roles):
            raise ValueError("identity pin binding is invalid")
    else:
        raise ValueError("explicit catalog pin permutation is missing")
    if set(by_pin) != set(mapping):
        raise ValueError("connected pins must exactly match the bound package terminals")
    return {terminal: by_pin[pin] for pin, terminal in mapping.items()}


def entry_problems(entry, recipe: RuntimeRecipe | None) -> list[str]:
    reasons = []
    if entry.layer.value == "L3":
        reasons.append("L3 protocol behavior is not simulable by ngspice")
    if entry.research is None:
        reasons.append("Primary-source gap research has not been completed")
    else:
        reasons.extend(entry.research.simulation_blockers)
        if entry.research.research_result != "sources_reviewed":
            reasons.append("No usable primary-source research is available")
    if recipe is None:
        reasons.append("No executable package-to-model recipe is bound to this entry")
    return reasons


def _facts(entry, recipe):
    values, evidence = {}, {}
    for name, binding in recipe.critical_facts.items():
        candidates = [f for f in entry.research.field_updates
                      if f.field == binding.field
                      and (not binding.scope_contains or binding.scope_contains in f.scope)]
        if len(candidates) != 1:
            raise ValueError(f"critical field {binding.field} is missing or has ambiguous scope")
        fact = candidates[0]
        if fact.basis in {"ASSUMPTION", "RESEARCH_REQUIRED"} or not fact.sources:
            raise ValueError(f"critical field {binding.field} is unsourced")
        if fact.unit != binding.unit:
            raise ValueError(f"critical field {binding.field} has the wrong unit")
        if isinstance(fact.value, bool) or not isinstance(fact.value, (int, float)) or not math.isfinite(fact.value):
            raise ValueError(f"critical field {binding.field} needs a finite scalar")
        values[name] = float(fact.value)
        evidence[name] = fact.model_dump(mode="json")
    return values, evidence


def _number(value):
    return format(value, ".17g")


def compile_circuit(circuit: CircuitIR, registry: BehaviorRegistry, recipes: RuntimeRecipes,
                    selections: dict[str, BehaviorSelection] | None = None, *, analysis="op"):
    selections = selections or {}
    problems, components, limitations = [], [], []
    if set(selections) - {c.ref for c in circuit.components}:
        problems.append("A behavior selection refers to a component outside this circuit")
    ground = [n for n in circuit.nets if n.kind is NetKind.GROUND]
    if len(ground) != 1:
        problems.append("Exactly one explicit ground net is required; separate grounds cannot be silently joined")
    nodes = {net.name: ("0" if net.kind is NetKind.GROUND else f"n{i}")
             for i, net in enumerate(sorted(circuit.nets, key=lambda n: n.name), 1)}
    lines = ["OHMNI sourced behavior circuit", ".options tnom=25", ".temp 25"]
    source_count = 0
    for i, net in enumerate(sorted(circuit.nets, key=lambda n: n.name), 1):
        if net.external_source:
            typical = net.external_source.voltage.typical
            if net.kind is NetKind.GROUND or typical is None:
                problems.append(f"{net.name}: source requires an explicit typical voltage on a non-ground net")
                continue
            lines.append(f"Vsource{i} {nodes[net.name]} 0 DC {_number(typical.value)}")
            source_count += 1
            limitations.append(f"{net.name}: ideal declared DC source; source impedance and current limiting are not modeled")
    if not source_count:
        problems.append("No explicit external DC source is connected")
    for i, component in enumerate(sorted(circuit.components, key=lambda c: c.ref), 1):
        selected = selections.get(component.ref)
        candidates = [r for r in recipes.entries.values()
                      if component.part_id in r.catalog_parts and component.package == r.package]
        entry_id = selected.entry_id if selected else candidates[0].entry_id if len(candidates) == 1 else None
        if not entry_id:
            problems.append(f"{component.ref}: select an explicit sourced package/reference binding")
            continue
        try:
            entry = registry.entry(entry_id)
            recipe = recipes.entries.get(entry_id)
            reasons = entry_problems(entry, recipe)
            if reasons:
                raise ValueError("; ".join(reasons))
            if component.placeholder:
                raise ValueError("unresolved placeholder component")
            if component.part_id != entry_id and component.part_id not in recipe.catalog_parts:
                raise ValueError("catalog part is not bound to this reference model")
            if component.package != recipe.package:
                raise ValueError("selected package differs from the bound reference model")
            if analysis not in recipe.supported_analyses:
                raise ValueError(f"analysis {analysis} is not supported by this binding")
            terminals = terminal_nodes(circuit, component, entry_id, recipe.terminal_roles, registry,
                                       nodes, recipe.catalog_identity_pin_map)
            roles = {}
            for terminal, role in recipe.terminal_roles.items():
                node = terminals[terminal]
                if role in roles and roles[role] != node:
                    raise ValueError(f"internally common {role} terminals are on different nets")
                roles[role] = node
            values, evidence = _facts(entry, recipe)
            if recipe.instance_value_unit:
                if component.value is None or component.value.unit.value != recipe.instance_value_unit:
                    raise ValueError(f"an explicit instance value in {recipe.instance_value_unit} is required")
                if component.value.value <= 0:
                    raise ValueError("instance value must be positive; no implicit zero-value substitution")
                values["value"] = component.value.value
                evidence["value"] = {"basis": "circuit_instance", "unit": recipe.instance_value_unit,
                                     "value": component.value.value}
            behavior = registry.behavior_class(recipe.behavior_id)
            template = behavior.canonical_payload["model"][recipe.template_key]
            substitutions = {**roles, **{k: _number(v) for k, v in values.items()}, "ref": f"c{i}"}
            fragment = template.format_map(substitutions)
            if re.search(r"^\s*\.(?:include|inc|lib|control|end)\b", fragment, re.IGNORECASE | re.MULTILINE):
                raise ValueError("model must be self-contained without includes or analysis commands")
            lines.extend(fragment.splitlines())
            components.append(CompiledComponent(
                ref=component.ref, entry_id=entry_id, behavior_id=recipe.behavior_id,
                fidelity=behavior.fidelity, source_status=entry.status.value,
                confidence=behavior.canonical_payload.get("confidence", {}).get("model", "L"),
                source_confidence=behavior.canonical_payload.get("confidence", {}),
                rating_confidence=min((f["confidence"] for f in evidence.values() if "confidence" in f),
                                      key={"L": 0, "M": 1, "H": 2}.get, default="L"),
                role_nodes=roles, terminal_nodes=terminals, parameters=values,
                parameter_evidence=evidence,
                element_names=[line.split()[0] for line in fragment.splitlines()
                               if line.strip() and not line.lstrip().startswith(("*", ".", "+"))],
                limitations=recipe.limitations + behavior.canonical_payload["model"].get("known_limitations", []),
            ))
        except (ValueError, KeyError) as exc:
            problems.append(f"{component.ref} ({entry_id}): {exc}")
    lines.append(".end")
    netlist = None if problems else "\n".join(lines) + "\n"
    return BehaviorCompilation(
        circuit_hash=circuit.content_hash, analysis=analysis, netlist=netlist,
        netlist_sha256=hashlib.sha256(netlist.encode()).hexdigest() if netlist else None,
        node_names=nodes, components=components, problems=problems, limitations=limitations,
    )
