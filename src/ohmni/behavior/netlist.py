"""Deterministic, fail-closed translation from CircuitIR to authored models.

No source fetching, fitting, solver or rating verdict lives here. A recipe is
an explicit join between the package and its sourced behavior record.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

from ..domain.circuit import CircuitIR, NetKind
from .expressions import evaluate
from .loader import (
    BehaviorRegistry,
    BehaviorRegistryError,
    _find_repo_root,
    _json,
    _safe_local_path,
    _validate_anchor,
)
from .runtime_models import (
    BehaviorCompilation,
    BehaviorSelection,
    CompiledComponent,
    DCExcitation,
    PWLExcitation,
    RuntimeRecipe,
    RuntimeRecipes,
)


def load_recipes(registry: BehaviorRegistry, root) -> RuntimeRecipes:
    recipes = RuntimeRecipes.model_validate(_json(registry.directory / "runtime-recipes.json"))
    _validate_anchor(root, recipes.source, "runtime recipes")
    for key, recipe in recipes.entries.items():
        if key != recipe.entry_id:
            raise BehaviorRegistryError(f"runtime recipe key differs from entry: {key}")
        validate_reference_function(registry.entry(key), recipe)
        if recipe.template_override is not None and recipe.template_provenance is None:
            raise BehaviorRegistryError(f"runtime template requires provenance: {key}")
        for anchor in [*recipe.inline_assets, *(p.source for p in recipe.derived_parameters.values())]:
            _validate_anchor(root, anchor, key)
        for parameter in recipe.quoted_parameters.values():
            if parameter.source:
                _validate_anchor(root, parameter.source, key)
        if recipe.template_provenance:
            _validate_anchor(root, recipe.template_provenance, key)
        if recipe.pin_role_fact and recipe.pin_role_fact.permutation_provenance:
            _validate_anchor(root, recipe.pin_role_fact.permutation_provenance, key)
    return recipes


def validate_reference_function(entry, recipe):
    if recipe.behavior_id in entry.behavior_class_ids and recipe.reference_function is None:
        return
    binding = recipe.reference_function
    if (binding is None or recipe.pin_role_fact is None or entry.research is None
            or not set(entry.behavior_class_ids) & {"BEH-IC-PKGBIND", "BEH-PKG-IC-BINDING"}):
        raise BehaviorRegistryError(f"runtime recipe class differs from entry without a sourced reference function: {entry.entry_id}")
    facts = [f for f in entry.research.field_updates if f.field == binding.field
             and binding.scope_contains in f.scope and f.value == binding.value]
    if len(facts) != 1 or facts[0].basis not in {"MFR_DATASHEET", "STANDARD"} or not facts[0].sources:
        raise BehaviorRegistryError(f"sourced reference function does not match the package record: {entry.entry_id}")


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
        value = fact.value
        for key in binding.value_path:
            try:
                value = value[key]
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError(f"critical field {binding.field} has no selected condition {key}") from exc
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"critical field {binding.field} needs a finite scalar")
        values[name] = convert_unit(float(value), binding.unit, binding.output_unit or binding.unit)
        evidence[name] = fact.model_dump(mode="json")
        if binding.value_path:
            evidence[name]["selected_value_path"] = binding.value_path
            evidence[name]["selected_value"] = value
        if binding.output_unit:
            evidence[name]["converted_unit"] = binding.output_unit
            evidence[name]["converted_value"] = values[name]
    return values, evidence


def _number(value):
    return format(value, ".17g")


def convert_unit(value, source, target):
    if source == target:
        return value
    units = {
        "V": ("V", 1), "mV": ("V", 1e-3), "A": ("A", 1), "mA": ("A", 1e-3),
        "uA": ("A", 1e-6), "ohm": ("ohm", 1), "mohm": ("ohm", 1e-3),
        "W": ("W", 1), "mW": ("W", 1e-3), "F": ("F", 1), "uF": ("F", 1e-6),
        "nF": ("F", 1e-9), "pF": ("F", 1e-12), "H": ("H", 1), "uH": ("H", 1e-6),
        "nH": ("H", 1e-9), "s": ("s", 1), "ms": ("s", 1e-3), "us": ("s", 1e-6),
        "ns": ("s", 1e-9), "C": ("degC", 1), "degC": ("degC", 1),
        "Hz": ("Hz", 1), "kHz": ("Hz", 1e3), "MHz": ("Hz", 1e6), "GHz": ("Hz", 1e9),
    }
    if source not in units or target not in units or units[source][0] != units[target][0]:
        raise ValueError(f"unsupported unit conversion {source} -> {target}")
    return value * units[source][1] / units[target][1]


def inline_asset(root, anchor):
    path = _safe_local_path(root, anchor.document)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != anchor.document_sha256:
        raise ValueError(f"inline model asset changed: {anchor.document}")
    text = raw.decode("utf-8")
    if re.search(r"^\s*(?:\.(?:include|inc|lib|control|end)\b|(?:shell|source|write|wrdata)\b)", text, re.IGNORECASE | re.MULTILINE):
        raise ValueError("inline model asset contains file or analysis commands")
    validate_mosfet_cards(text)
    return text


def validate_mosfet_cards(text):
    logical = re.sub(r"\r?\n\s*\+", " ", text)
    for line in logical.splitlines():
        if (re.match(r"\s*\.model\s+\S+\s+[NP]MOS\b", line, re.IGNORECASE)
                and not re.search(r"\bIS\s*=\s*0(?:\.0*)?(?=\s|\))", line, re.IGNORECASE)):
            raise ValueError("every MOSFET card must explicitly set IS=0")


def pin_ground_strays(roles, parameters, parameter_evidence, mapping, reference):
    """Physical pin capacitance returns only to ground, never across pin pairs."""
    lines = []
    for i, (role, parameter) in enumerate(sorted(mapping.items()), 1):
        if role not in roles or parameter not in parameters:
            raise ValueError("stray requires an explicit pin role and capacitance parameter")
        evidence = parameter_evidence[parameter]
        if evidence.get("converted_unit", evidence.get("unit")) != "F" or parameters[parameter] <= 0:
            raise ValueError("stray capacitance must be positive and in farads")
        if roles[role] != "0":
            lines.append(f"Cstray_{reference}_{i} {roles[role]} 0 {_number(parameters[parameter])}")
    return lines


def _parameter_defaults(behavior, recipe, values, evidence, root):
    for alias, name in recipe.class_parameters.items():
        if alias in values:
            raise ValueError(f"class default cannot replace a critical or instance value: {alias}")
        parameter = behavior.canonical_payload["parameters"][name]
        value = float(parameter["default"])
        if not math.isfinite(value):
            raise ValueError("non-finite authored parameter")
        values[alias], evidence[alias] = value, dict(parameter, source=behavior.source.model_dump(mode="json"))
    authored = json.dumps(behavior.canonical_payload)
    for name, parameter in recipe.quoted_parameters.items():
        quote_source = authored
        if parameter.source:
            _validate_anchor(root, parameter.source, recipe.entry_id)
            quote_source = _safe_local_path(root, parameter.source.document).read_text(encoding="utf-8")
        if name in values or parameter.source_fragment not in quote_source or parameter.value_text not in parameter.source_fragment:
            raise ValueError(f"quoted parameter does not relocate to the authored class: {name}")
        value = float(parameter.value_text)
        if not math.isfinite(value):
            raise ValueError("non-finite quoted parameter")
        values[name], evidence[name] = value, parameter.model_dump(mode="json")
    pending = dict(recipe.derived_parameters)
    while pending:
        advanced = False
        for name, parameter in list(pending.items()):
            try:
                value = evaluate(parameter.expression, values)
            except ValueError:
                continue
            if name in values:
                raise ValueError(f"derived parameter cannot replace another value: {name}")
            values[name] = float(value)
            evidence[name] = parameter.model_dump(mode="json")
            del pending[name]
            advanced = True
        if not advanced:
            raise ValueError(f"derived parameter missing input, invalid equation or cycle: {sorted(pending)}")


def compile_circuit(circuit: CircuitIR, registry: BehaviorRegistry, recipes: RuntimeRecipes,
                    selections: dict[str, BehaviorSelection] | None = None, *, analysis="op",
                    excitations: list[DCExcitation | PWLExcitation] | None = None):
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
    assets = {}
    root = _find_repo_root(registry.directory)
    source_count = 0
    source_elements = {}
    excitations = sorted(excitations or [], key=lambda x: x.model_dump_json())
    for i, net in enumerate(sorted(circuit.nets, key=lambda n: n.name), 1):
        if net.external_source:
            typical = net.external_source.voltage.typical
            if net.kind is NetKind.GROUND or typical is None:
                problems.append(f"{net.name}: source requires an explicit typical voltage on a non-ground net")
                continue
            lines.append(f"Vsource{i} {nodes[net.name]} 0 DC {_number(typical.value)}")
            source_elements[net.name] = f"vsource{i}"
            source_count += 1
            limitations.append(f"{net.name}: ideal declared DC source; source impedance and current limiting are not modeled")
    voltage_pairs = {frozenset((net.name, ground[0].name)) for net in circuit.nets
                     if net.external_source and len(ground) == 1}
    for i, source in enumerate(excitations, 1):
        if source.positive_net not in nodes or source.negative_net not in nodes:
            problems.append("An excitation refers to a net outside the circuit")
            continue
        pair = frozenset((source.positive_net, source.negative_net))
        value = source.points[0].value if isinstance(source, PWLExcitation) else source.value
        if value.unit.value == "V" and pair in voltage_pairs:
            problems.append("Duplicate ideal voltage sources on the same nets are not allowed")
            continue
        if value.unit.value == "V":
            voltage_pairs.add(pair)
        prefix = "V" if value.unit.value == "V" else "I"
        stimulus = ("PWL(" + " ".join(f"{_number(p.time.value)} {_number(p.value.value)}" for p in source.points) + ")"
                    if isinstance(source, PWLExcitation) else f"DC {_number(value.value)}")
        lines.append(f"{prefix}excitation{i} {nodes[source.positive_net]} {nodes[source.negative_net]} {stimulus}")
        source_count += 1
        limitations.append("Explicit ideal test excitation; a stimulus is not physical source capability or evidence")
    if not source_count:
        problems.append("No explicit external DC source or test excitation is connected")
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
            validate_reference_function(entry, recipe)
            if component.placeholder:
                raise ValueError("unresolved placeholder component")
            if component.part_id != entry_id and component.part_id not in recipe.catalog_parts:
                raise ValueError("catalog part is not bound to this reference model")
            if component.package != recipe.package:
                raise ValueError("selected package differs from the bound reference model")
            if analysis not in recipe.supported_analyses:
                raise ValueError(f"analysis {analysis} is not supported by this binding")
            role_fact = None
            if recipe.pin_role_fact:
                binding = recipe.pin_role_fact
                candidates = [f for f in entry.research.field_updates if f.field == binding.field
                              and (not binding.scope_contains or binding.scope_contains in f.scope)]
                if len(candidates) != 1 or candidates[0].basis in {"ASSUMPTION", "RESEARCH_REQUIRED"}:
                    raise ValueError("a unique sourced pin-role map is required")
                role_fact = candidates[0]
                sourced_roles = dict(role_fact.value)
                for feature in binding.tied_features:
                    role = sourced_roles.pop(feature)
                    if role not in sourced_roles.values():
                        raise ValueError("tied package feature has no matching electrical terminal")
                if binding.manufacturer_to_package_terminal:
                    if set(binding.manufacturer_to_package_terminal) != set(sourced_roles):
                        raise ValueError("manufacturer permutation must cover exactly the sourced terminals")
                    _validate_anchor(root, binding.permutation_provenance, entry_id)
                    sourced_roles = {binding.manufacturer_to_package_terminal[pin]: role
                                     for pin, role in sourced_roles.items()}
                if sourced_roles != recipe.terminal_roles:
                    raise ValueError("recipe pin roles differ from the sourced manufacturer map")
            terminals = terminal_nodes(circuit, component, entry_id, recipe.terminal_roles, registry,
                                       nodes, recipe.catalog_identity_pin_map)
            roles = {}
            for terminal, role in recipe.terminal_roles.items():
                node = terminals[terminal]
                if role in roles and roles[role] != node:
                    raise ValueError(f"internally common {role} terminals are on different nets")
                roles[role] = node
            for role in recipe.required_ground_roles:
                if roles[role] != "0":
                    raise ValueError(f"this reference model requires {role} on circuit ground")
            for group in recipe.required_same_net_roles:
                if len({roles[role] for role in group}) != 1:
                    raise ValueError(f"this reference model requires roles {group} on the same net")
            for role in recipe.required_isolated_roles:
                net = next(n for n in circuit.nets if nodes[n.name] == roles[role])
                if (net.kind is NetKind.GROUND or net.external_source or len(net.connections) != 1
                        or any(net.name in (s.positive_net, s.negative_net) for s in excitations)):
                    raise ValueError(f"unmodeled role {role} must remain isolated")
            values, evidence = _facts(entry, recipe)
            if role_fact:
                evidence["terminal_roles"] = role_fact.model_dump(mode="json")
                if recipe.pin_role_fact.manufacturer_to_package_terminal:
                    evidence["manufacturer_to_package_terminal"] = {
                        "basis": "DERIVED", "confidence": "H",
                        "value": recipe.pin_role_fact.manufacturer_to_package_terminal,
                        "source": recipe.pin_role_fact.permutation_provenance.model_dump(mode="json"),
                    }
            if recipe.instance_value_unit:
                if component.value is None or component.value.unit.value != recipe.instance_value_unit:
                    raise ValueError(f"an explicit instance value in {recipe.instance_value_unit} is required")
                if component.value.value <= 0:
                    raise ValueError("instance value must be positive; no implicit zero-value substitution")
                values["value"] = component.value.value
                evidence["value"] = {"basis": "circuit_instance", "unit": recipe.instance_value_unit,
                                     "value": component.value.value}
            elif component.value is not None:
                if "value" not in values or not math.isclose(
                    values["value"], convert_unit(component.value.value, component.value.unit.value,
                                                 evidence["value"].get("converted_unit", evidence["value"]["unit"])),
                    rel_tol=1e-12, abs_tol=0,
                ):
                    raise ValueError("instance value differs from the fixed sourced reference")
            behavior = registry.behavior_class(recipe.behavior_id)
            _parameter_defaults(behavior, recipe, values, evidence, root)
            template = recipe.template_override or behavior.canonical_payload["model"][recipe.template_key]
            if recipe.template_override:
                if recipe.template_provenance is None:
                    raise ValueError("template override lacks provenance")
                _validate_anchor(root, recipe.template_provenance, entry_id)
            for parameter in recipe.derived_parameters.values():
                _validate_anchor(root, parameter.source, entry_id)
            asset_names = {}
            for anchor in recipe.inline_assets:
                asset_names[anchor.document.rsplit("/", 1)[-1]] = anchor
                assets[anchor.document] = inline_asset(root, anchor)
            kept = []
            for line in template.splitlines():
                include = re.match(r"\s*\.(?:include|inc)\s+(.+?)\s*$", line, re.IGNORECASE)
                if include:
                    if include[1].strip("\"'") not in asset_names:
                        raise ValueError("include has no explicit, hashed inline asset binding")
                else:
                    kept.append(line)
            template = "\n".join(kept)
            substitutions = {**roles, **{k: _number(v) for k, v in values.items()}, "ref": f"c{i}"}
            fragment = template.format_map(substitutions)
            if re.search(r"^\s*\.(?:include|inc|lib|control|end)\b", fragment, re.IGNORECASE | re.MULTILINE):
                raise ValueError("model must be self-contained without includes or analysis commands")
            original = behavior.canonical_payload["model"][recipe.template_key]
            if ".nodeset" in original.lower() and ".nodeset" not in fragment.lower():
                raise ValueError("regulator binding must preserve its authored nodeset")
            validate_mosfet_cards(fragment)
            strays = pin_ground_strays(roles, values, evidence, recipe.ground_strays, f"c{i}")
            lines.extend(fragment.splitlines())
            lines.extend(strays)
            components.append(CompiledComponent(
                ref=component.ref, entry_id=entry_id, behavior_id=recipe.behavior_id,
                reference_part=recipe.reference_part,
                fidelity=behavior.fidelity, source_status=entry.status.value,
                confidence=behavior.canonical_payload.get("confidence", {}).get("model", "L"),
                source_confidence=behavior.canonical_payload.get("confidence", {}),
                rating_confidence=min((evidence[k]["confidence"] for k in recipe.critical_facts),
                                      key={"L": 0, "M": 1, "H": 2}.get, default="L"),
                role_nodes=roles, terminal_nodes=terminals, parameters=values,
                parameter_evidence=evidence,
                element_names=[line.split()[0] for line in fragment.splitlines()
                               if line.strip() and not line.lstrip().startswith(("*", ".", "+"))],
                limitations=recipe.limitations + behavior.canonical_payload["model"].get("known_limitations", []),
            ))
        except (ValueError, KeyError) as exc:
            problems.append(f"{component.ref} ({entry_id}): {exc}")
    lines.extend(text for _, text in sorted(assets.items()))
    lines.append(".end")
    netlist = None if problems else "\n".join(lines) + "\n"
    return BehaviorCompilation(
        circuit_hash=circuit.content_hash, analysis=analysis, netlist=netlist,
        netlist_sha256=hashlib.sha256(netlist.encode()).hexdigest() if netlist else None,
        node_names=nodes, source_elements=source_elements, excitations=excitations, components=components,
        problems=problems, limitations=limitations,
    )
