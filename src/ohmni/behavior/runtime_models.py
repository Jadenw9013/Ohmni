"""Explicit circuit-to-model bindings, separate from electrical CircuitIR."""

from __future__ import annotations

import math
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
    manufacturer_to_package_terminal: dict[str, str] = Field(default_factory=dict)
    permutation_provenance: SourceAnchor | None = None

    @model_validator(mode="after")
    def explicit_permutation(self):
        if bool(self.manufacturer_to_package_terminal) != bool(self.permutation_provenance):
            raise ValueError("manufacturer permutation and its provenance must be supplied together")
        if len(set(self.manufacturer_to_package_terminal.values())) != len(self.manufacturer_to_package_terminal):
            raise ValueError("manufacturer permutation must be one-to-one")
        return self


class ReferenceFunction(BaseModel):
    """Exact researched reference selected for an otherwise functionless package."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str = "reference_part"
    value: str
    scope_contains: str


class FitCurve(BaseModel):
    """A sourced curve the fitted model must replay at several currents, not only at one bound."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    points: int = Field(default=3, ge=2, le=8, description="How many read points the runtime check replays")
    anode_role: str = "A"
    cathode_role: str = "K"


class PinLevelPull(BaseModel):
    """A pull resistor the source states is active in the reset state, with its sourced range."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    resistance: str = Field(description="Value alias passed to the pad as rpu")
    minimum: str
    maximum: str


class PinLevelPad(BaseModel):
    """One I/O pin frozen in its datasheet reset state (output disabled; pull only when sourced).

    Every limit is a value alias; a missing or unsourced alias leaves its rating row unknown.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    supply: str = Field(description="Role of the rail the pad's clamp and pull-up return to")
    subckt: Literal["dio_pin", "dio_pin_ft"] = "dio_pin"
    pull_up: PinLevelPull | None = None
    parameters: dict[str, str] = Field(default_factory=dict, description="dio_pin parameter -> value alias override")
    vmax: str
    vmax_relative: bool = Field(description="True: the limit is the pad supply plus vmax; False: vmax itself")
    vmin: str = Field(description="Magnitude the pin may go below ground")
    current: str | None = None
    injection: str | None = None
    injection_negative_only: bool = False
    above_supply_unknown: str | None = Field(
        default=None, description="Margin above the pad supply beyond which the source states no valid condition"
        " for this pad in its reset state; the result there is unknown, never a pass")
    above_supply_reason: str | None = None


class PinLevelSupply(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    minimum: str
    maximum: str
    absolute: str
    current: str | None = Field(default=None, description="Total current limit into this rail's pins")


class PinLevelGroup(BaseModel):
    """A collective current limit the source states over several pins (absolute sum)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    roles: list[str] = Field(min_length=1)
    limit: str


class PinLevelModel(BaseModel):
    """D075: a programmable device bound as its electrical pins only, frozen in the datasheet reset state.

    Each pad role becomes one instance of the hashed dio.lib pad (or its no-upper-clamp variant) with
    dout, oe and pu tied to internal nodes, so no firmware state is invented. Every terminal role is
    exactly one of: a pad, a supply rail, the ground, a role tied by a connection constraint, or an
    unmodeled role (metadata only, no conductive model).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ground: str
    ground_current: str | None = None
    supplies: list[PinLevelSupply] = Field(min_length=1)
    pads: dict[str, PinLevelPad] = Field(min_length=1)
    parameters: dict[str, str] = Field(default_factory=dict, description="dio_pin parameter -> value alias for every pad")
    tied: list[str] = Field(default_factory=list)
    unmodeled: list[str] = Field(default_factory=list)
    groups: list[PinLevelGroup] = Field(default_factory=list)
    rth_ja: str | None = None
    tj_max: str | None = None
    thermal_reason: str | None = None
    probe_leakage: str
    reset_state: str

    @model_validator(mode="after")
    def consistent(self):
        supplies = [s.role for s in self.supplies]
        if len(set(supplies)) != len(supplies) or self.ground in supplies:
            raise ValueError("pin-level supply roles must be distinct and differ from the ground")
        buckets = [set(self.pads), set(supplies), {self.ground}, set(self.tied), set(self.unmodeled)]
        if sum(len(b) for b in buckets) != len(set().union(*buckets)):
            raise ValueError("a pin-level role belongs to exactly one of pads, supplies, ground, tied, unmodeled")
        if any(p.supply not in supplies for p in self.pads.values()):
            raise ValueError("a pad returns to an undeclared supply")
        if any(set(g.roles) - set(self.pads) for g in self.groups):
            raise ValueError("a pin-level group names a role that is not a pad")
        if bool(self.rth_ja) != bool(self.tj_max) or (self.rth_ja is None) == (self.thermal_reason is None):
            raise ValueError("thermal limits are bound together, or the reason they are unpublished is stated")
        return self

    def roles(self):
        return {*self.pads, *(s.role for s in self.supplies), self.ground, *self.tied, *self.unmodeled}


class RuntimeRecipe(BaseModel):
    """An authored mapping; numeric electrical facts stay in sourced records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str = Field(pattern=r"^OHM-\d{3}$")
    behavior_id: str
    package: str
    reference_part: str | None = None
    reference_function: ReferenceFunction | None = None
    catalog_parts: list[str] = Field(default_factory=list)
    catalog_identity_pin_map: dict[str, str] = Field(default_factory=dict)
    terminal_roles: dict[str, str]
    required_ground_roles: list[str] = Field(default_factory=list)
    required_same_net_roles: list[list[str]] = Field(default_factory=list)
    required_isolated_roles: list[str] = Field(default_factory=list)
    open_mating_roles: list[str] = Field(
        default_factory=list,
        description="Connector mating-side contacts (cable, card or plug side). They are not PCB pads, so a"
        " design may leave them unconnected; each then gets its own private node, as an unmated contact would.",
    )
    pin_role_fact: PinRoleFact | None = None
    template_key: str = "netlist_template"
    instance_value_unit: str | None = None
    critical_facts: dict[str, FactBinding]
    model_facts: dict[str, FactBinding] = Field(
        default_factory=dict,
        description="Model parameters fitted from the part's own sourced curves; held to the same sourcing"
        " rules as critical facts but excluded from rating confidence",
    )
    fit_curves: dict[str, FitCurve] = Field(
        default_factory=dict,
        description="Sourced read-point curves behind fitted model facts; each adds multi-point runtime checks",
    )
    derived_parameters: dict[str, AuthoredExpression] = Field(default_factory=dict)
    class_parameters: dict[str, str] = Field(default_factory=dict)
    quoted_parameters: dict[str, QuotedParameter] = Field(default_factory=dict)
    template_override: str | None = None
    template_provenance: SourceAnchor | None = None
    inline_assets: list[SourceAnchor] = Field(default_factory=list)
    ground_strays: dict[str, str] = Field(default_factory=dict, description="Pin role to sourced capacitance parameter; every stray returns to node 0")
    supported_analyses: list[Literal["op", "tran"]] = Field(default_factory=lambda: ["op"])
    pin_level: PinLevelModel | None = None
    limitations: list[str]

    @model_validator(mode="after")
    def valid_connection_constraints(self):
        roles = set(self.terminal_roles.values())
        if self.pin_level is not None:
            if self.pin_level.roles() != roles:
                raise ValueError("a pin-level model must classify exactly the bound terminal roles")
            if self.template_override is not None or self.template_provenance is None:
                raise ValueError("a pin-level model generates its template and needs template provenance")
            if self.pin_level.ground not in self.required_ground_roles:
                raise ValueError("the pin-level ground must be required on circuit ground")
            constrained = set(self.required_ground_roles) | {r for g in self.required_same_net_roles for r in g}
            if set(self.pin_level.tied) - constrained:
                raise ValueError("a tied pin-level role needs a connection constraint")
        constrained = set(self.required_ground_roles) | set(self.required_isolated_roles)
        for group in self.required_same_net_roles:
            if len(set(group)) < 2:
                raise ValueError("same-net constraint requires at least two distinct roles")
            constrained.update(group)
        if constrained - roles:
            raise ValueError("connection constraint refers to an unknown terminal role")
        if set(self.open_mating_roles) - roles:
            raise ValueError("open mating role refers to an unknown terminal role")
        if set(self.open_mating_roles) & constrained:
            raise ValueError("an open mating role cannot also carry a connection constraint")
        if any(pin.isdigit() for pin, role in self.terminal_roles.items() if role in self.open_mating_roles):
            raise ValueError("a numbered package pin cannot be an open mating contact")
        return self


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


class PWLPoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    time: Quantity
    value: Quantity

    @model_validator(mode="after")
    def valid_point(self):
        if self.time.unit.value != "s" or not math.isfinite(self.time.value) or self.time.value < 0:
            raise ValueError("PWL time requires finite nonnegative seconds")
        if self.value.unit.value not in {"V", "A"} or not math.isfinite(self.value.value):
            raise ValueError("PWL value requires finite volts or amperes")
        return self


class PWLExcitation(BaseModel):
    """Typed ideal test waveform; values never establish device ratings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    positive_net: str
    negative_net: str
    points: list[PWLPoint] = Field(min_length=2, max_length=10000)

    @model_validator(mode="after")
    def valid_waveform(self):
        if self.positive_net == self.negative_net:
            raise ValueError("PWL excitation requires distinct nets")
        if self.points[0].time.value != 0:
            raise ValueError("PWL waveform must declare its initial value at zero seconds")
        if any(b.time.value <= a.time.value for a, b in zip(self.points, self.points[1:])):
            raise ValueError("PWL times must strictly increase")
        if len({p.value.unit for p in self.points}) != 1:
            raise ValueError("PWL waveform cannot mix voltage and current")
        return self


class ACExcitation(BaseModel):
    """Ideal small-signal sine source for AC analysis: an optional DC bias plus an RMS amplitude.

    The amplitude is the RMS value of the sine, so every AC result is an RMS phasor. A stimulus is
    never a component rating or evidence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    positive_net: str
    negative_net: str
    dc: Quantity | None = None
    ac_rms: Quantity

    @model_validator(mode="after")
    def valid_ac(self):
        if self.positive_net == self.negative_net:
            raise ValueError("AC excitation requires distinct nets")
        unit = self.ac_rms.unit.value
        if unit not in {"V", "A"} or not math.isfinite(self.ac_rms.value) or self.ac_rms.value <= 0:
            raise ValueError("AC excitation requires a positive finite RMS amplitude in volts or amperes")
        if self.dc is not None and (self.dc.unit.value != unit or not math.isfinite(self.dc.value)):
            raise ValueError("AC excitation bias must be finite and in the amplitude's unit")
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
    role_current_probes: dict[str, str] = Field(default_factory=dict)
    limitations: list[str]
    pin_level: PinLevelModel | None = None


class BehaviorCompilation(BaseModel):
    model_config = ConfigDict(frozen=True)

    circuit_hash: str
    analysis: Literal["op", "tran", "ac"] = "op"
    netlist: str | None = None
    netlist_sha256: str | None = None
    node_names: dict[str, str] = Field(default_factory=dict)
    source_elements: dict[str, str] = Field(default_factory=dict)
    excitations: list[DCExcitation | PWLExcitation | ACExcitation] = Field(default_factory=list)
    components: list[CompiledComponent] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @property
    def runnable(self) -> bool:
        return bool(self.netlist) and not self.problems
