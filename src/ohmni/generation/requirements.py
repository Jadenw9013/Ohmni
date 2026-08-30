"""Requirements compilation with explicit provenance and deterministic gates."""

from ..domain import FunctionalRequirement, Quantity, RequirementsSpec
from .models import (
    CompiledRequirements,
    RequirementInterpretation,
    RequirementOrigin,
    RequirementStatement,
)


def compile_requirements(value: RequirementInterpretation, request: str) -> CompiledRequirements:
    layers = value.max_board_layers if value.max_board_layers is not None else 2
    solder = value.hand_solderable if value.hand_solderable is not None else True
    assumptions = list(value.assumptions)
    provenance = [
        RequirementStatement(field="description", value=value.description, origin=RequirementOrigin.EXPLICIT, source_text=request),
        RequirementStatement(field="max_input_voltage", value=f"{value.max_input_voltage_v} V", origin=RequirementOrigin.EXPLICIT, source_text=request),
    ]
    provenance.append(RequirementStatement(field="max_board_layers", value=str(layers), origin=RequirementOrigin.EXPLICIT if value.max_board_layers is not None else RequirementOrigin.DEFAULT, source_text=request if value.max_board_layers is not None else None))
    provenance.append(RequirementStatement(field="hand_solderable", value=str(solder), origin=RequirementOrigin.EXPLICIT if value.hand_solderable is not None else RequirementOrigin.DEFAULT, source_text=request if value.hand_solderable is not None else None))
    if value.target_logic_voltage_v is not None:
        provenance.append(RequirementStatement(field="target_logic_voltage", value=f"{value.target_logic_voltage_v} V", origin=RequirementOrigin.EXPLICIT, source_text=request))
    if value.budget_usd is not None:
        provenance.append(RequirementStatement(field="budget_usd", value=str(value.budget_usd), origin=RequirementOrigin.EXPLICIT, source_text=request))
    provenance.extend(RequirementStatement(field="interface", value=i.value, origin=RequirementOrigin.EXPLICIT, source_text=request) for i in value.interfaces)
    provenance.extend(RequirementStatement(field="required_part_id", value=p, origin=RequirementOrigin.EXPLICIT, source_text=request) for p in value.required_part_ids)
    provenance.extend(RequirementStatement(field="assumption", value=a, origin=RequirementOrigin.ASSUMPTION) for a in assumptions)
    spec = RequirementsSpec(
        project_name=value.project_name, description=value.description,
        max_input_voltage=Quantity.volts(value.max_input_voltage_v),
        target_logic_voltage=None if value.target_logic_voltage_v is None else Quantity.volts(value.target_logic_voltage_v),
        budget_usd=value.budget_usd, max_board_layers=layers, hand_solderable=solder,
        interfaces=value.interfaces, required_part_ids=value.required_part_ids,
        assumptions=assumptions,
        functional_requirements=[FunctionalRequirement(requirement_id=f"REQ-{i:03}", description=text) for i, text in enumerate(value.functional_requirements, 1)],
    )
    return CompiledRequirements(requirements=spec, provenance=provenance)


def requirement_conflicts(compiled: CompiledRequirements, known_parts: set[str]) -> list[str]:
    req = compiled.requirements
    conflicts = []
    if not req.is_supported_scope:
        conflicts.append("request is outside the supported low-voltage safety scope")
    missing = sorted(set(req.required_part_ids) - known_parts)
    if missing:
        conflicts.append(f"required components are unavailable: {', '.join(missing)}")
    overlap = sorted(set(req.required_part_ids) & set(req.prohibited_part_ids))
    if overlap:
        conflicts.append(f"components are both required and prohibited: {', '.join(overlap)}")
    return conflicts
