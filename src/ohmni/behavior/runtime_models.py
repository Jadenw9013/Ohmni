"""Explicit circuit-to-model bindings, separate from electrical CircuitIR."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import BehaviorFidelity, SourceAnchor


class FactBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    unit: str
    scope_contains: str | None = None


class RuntimeRecipe(BaseModel):
    """An authored mapping; numeric electrical facts stay in sourced records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str = Field(pattern=r"^OHM-\d{3}$")
    behavior_id: str
    package: str
    catalog_parts: list[str] = Field(default_factory=list)
    catalog_identity_pin_map: dict[str, str] = Field(default_factory=dict)
    terminal_roles: dict[str, str]
    template_key: str = "netlist_template"
    instance_value_unit: str | None = None
    critical_facts: dict[str, FactBinding]
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


class CompiledComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: str
    entry_id: str
    behavior_id: str
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
    components: list[CompiledComponent] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @property
    def runnable(self) -> bool:
        return bool(self.netlist) and not self.problems
