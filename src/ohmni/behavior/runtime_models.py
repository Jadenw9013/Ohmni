"""Explicit circuit-to-model bindings, separate from electrical CircuitIR."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain.units import Quantity
from .models import BehaviorFidelity, SourceAnchor


class FactBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    unit: str
    scope_contains: str | None = None
    output_unit: str | None = None
    value_path: list[str | int] = Field(default_factory=list)


class AuthoredExpression(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expression: str
    unit: str
    basis: Literal["DERIVED"] = "DERIVED"
    confidence: Literal["H", "M", "L"]
    source: SourceAnchor
    detail: str


class QuotedParameter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value_text: str
    unit: str
    source_fragment: str
    basis: Literal["ASSUMPTION", "DERIVED"]
    confidence: Literal["M", "L"]
    source: SourceAnchor | None = None


class PinRoleFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = "manufacturer_pin_roles"
    scope_contains: str | None = None
    tied_features: list[str] = Field(default_factory=list)


class RuntimeRecipe(BaseModel):
    """An authored mapping; numeric electrical facts stay in sourced records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str = Field(pattern=r"^OHM-\d{3}$")
    behavior_id: str
    package: str
    reference_part: str | None = None
    catalog_parts: list[str] = Field(default_factory=list)
    catalog_identity_pin_map: dict[str, str] = Field(default_factory=dict)
    terminal_roles: dict[str, str]
    pin_role_fact: PinRoleFact | None = None
    template_key: str = "netlist_template"
    instance_value_unit: str | None = None
    critical_facts: dict[str, FactBinding]
    derived_parameters: dict[str, AuthoredExpression] = Field(default_factory=dict)
    class_parameters: dict[str, str] = Field(default_factory=dict)
    quoted_parameters: dict[str, QuotedParameter] = Field(default_factory=dict)
    template_override: str | None = None
    template_provenance: SourceAnchor | None = None
    inline_assets: list[SourceAnchor] = Field(default_factory=list)
    ground_strays: dict[str, str] = Field(default_factory=dict, description="Pin role to sourced capacitance parameter; every stray returns to node 0")
    supported_analyses: list[Literal["op", "tran"]] = Field(default_factory=lambda: ["op"])
    limitations: list[str]


class RuntimeRecipes(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    entries: dict[str, RuntimeRecipe]
    source: SourceAnchor


class BehaviorSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str = Field(pattern=r"^OHM-\d{3}$")


class DCExcitation(BaseModel):
    """An explicit simulation stimulus; never a component rating or evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    positive_net: str
    negative_net: str
    value: Quantity

    @model_validator(mode="after")
    def valid_dc(self):
        if self.value.unit.value not in {"V", "A"}:
            raise ValueError("DC excitation requires volts or amperes")
        if self.positive_net == self.negative_net:
            raise ValueError("DC excitation requires distinct nets")
        return self


class CompiledComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: str
    entry_id: str
    behavior_id: str
    reference_part: str | None = None
    fidelity: BehaviorFidelity
    source_status: str
    confidence: str
    rating_confidence: str
    source_confidence: dict[str, str]
    role_nodes: dict[str, str]
    terminal_nodes: dict[str, str]
    parameters: dict[str, float]
    parameter_evidence: dict[str, dict]
    element_names: list[str]
    limitations: list[str]


class BehaviorCompilation(BaseModel):
    model_config = ConfigDict(frozen=True)

    circuit_hash: str
    analysis: Literal["op", "tran"] = "op"
    netlist: str | None = None
    netlist_sha256: str | None = None
    node_names: dict[str, str] = Field(default_factory=dict)
    source_elements: dict[str, str] = Field(default_factory=dict)
    excitations: list[DCExcitation] = Field(default_factory=list)
    components: list[CompiledComponent] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @property
    def runnable(self) -> bool:
        return bool(self.netlist) and not self.problems
