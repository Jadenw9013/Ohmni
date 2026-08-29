"""The semantic circuit representation.

CircuitIR describes *intent and connectivity*, not graphics. It carries no
coordinates, no wires and no sheet layout, because none of those are needed to
decide whether a circuit is electrically sound.

Two deliberate choices:

* Connectivity lives on nets, as a list of pin references. A pin belongs to
  exactly one net or to none. Storing it in one place removes the entire class
  of bug where a pin's idea of its net and the net's idea of its members
  disagree.
* Voltage is **not** declared per pin. It is derived from what drives each net
  (see :mod:`ohmni.verifier.analysis`). A declared voltage is a fact a
  language model can assert; a derived one is a fact about the actual topology
  (PRE_IMPLEMENTATION_REVIEW.md 4.1).
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence import Evidence
from .units import Quantity, Unit, ValueRange


class NetKind(StrEnum):
    POWER = "power"
    GROUND = "ground"
    SIGNAL = "signal"


class ExternalSourceKind(StrEnum):
    USB_VBUS = "usb_vbus"
    DC_JACK = "dc_jack"
    BATTERY = "battery"
    BENCH_SUPPLY = "bench_supply"
    HEADER_FEED = "header_feed"


class PinRef(BaseModel):
    """A reference to one pin of one component instance."""

    model_config = ConfigDict(frozen=True)

    component: str = Field(description="Reference designator, e.g. 'U1'.")
    pin: str = Field(description="Pin number as it appears in the part's ComponentSpec.")

    def __str__(self) -> str:
        return f"{self.component}.{self.pin}"


class ExternalSource(BaseModel):
    """Declares that a net is fed from outside the board.

    This is the one legitimate place a voltage is declared rather than derived,
    because nothing on the board produces it. It still carries evidence.
    """

    kind: ExternalSourceKind
    voltage: ValueRange
    current_limit: Quantity | None = None
    description: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_units(self) -> ExternalSource:
        if self.voltage.unit is not Unit.VOLT:
            raise ValueError("external source voltage must be in volts")
        if self.current_limit is not None and self.current_limit.unit is not Unit.AMPERE:
            raise ValueError("external source current_limit must be in amperes")
        return self


class Net(BaseModel):
    """An electrical node: a set of pins that are connected together."""

    name: str
    kind: NetKind = NetKind.SIGNAL
    connections: list[PinRef] = Field(default_factory=list)
    external_source: ExternalSource | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Net:
        seen = {str(ref) for ref in self.connections}
        if len(seen) != len(self.connections):
            raise ValueError(f"net {self.name!r} lists the same pin more than once")
        if self.external_source is not None and self.kind is NetKind.SIGNAL:
            raise ValueError(
                f"net {self.name!r} has an external power source but is marked as a signal net"
            )
        return self

    def has(self, component: str, pin: str) -> bool:
        return any(ref.component == component and ref.pin == pin for ref in self.connections)

    def components(self) -> set[str]:
        return {ref.component for ref in self.connections}

    def pins_of(self, component: str) -> list[str]:
        return [ref.pin for ref in self.connections if ref.component == component]


class CircuitComponent(BaseModel):
    """One instance of a part on the board.

    Instance-level facts only. What the part *is* lives in its ComponentSpec,
    looked up by ``part_id``.
    """

    ref: str = Field(description="Reference designator, e.g. 'U1', 'R3', 'C12'.")
    part_id: str
    package: str | None = Field(
        default=None, description="Chosen package. Must be one the part actually offers."
    )
    value: Quantity | None = Field(
        default=None, description="For passives: the resistance, capacitance or inductance."
    )
    selected_i2c_address: int | None = Field(
        default=None, ge=0x00, le=0x7F, description="7-bit address as strapped on this board."
    )
    placeholder: bool = Field(
        default=False,
        description="True when the part is a stand-in that has not been resolved to a real part.",
    )
    notes: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class ConstraintKind(StrEnum):
    VOLTAGE = "voltage"
    CURRENT = "current"
    THERMAL = "thermal"
    LAYOUT = "layout"
    COST = "cost"
    ASSEMBLY = "assembly"
    INTERFACE = "interface"
    OTHER = "other"


class DesignConstraint(BaseModel):
    """A constraint the design must respect, carried with its origin.

    ``hard`` constraints block a verified export when violated; soft ones are
    preferences. Naming this explicitly stops "should" and "must" from being
    decided by tone of voice.
    """

    constraint_id: str
    kind: ConstraintKind
    description: str
    hard: bool = True
    applies_to: list[str] = Field(
        default_factory=list, description="Component refs or net names this constrains."
    )
    source_requirement_id: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class CircuitIR(BaseModel):
    """A complete, self-consistent semantic circuit.

    Self-consistency here means internal referential integrity only: every pin
    reference names a component that exists, refs are unique, a pin is on at
    most one net. Whether those pins exist *on the real part* needs the catalog
    and is therefore a verification rule, not a model validator -- the domain
    layer does not reach for infrastructure.
    """

    ir_id: str
    name: str
    revision: int = Field(default=1, ge=1)
    parent_hash: str | None = Field(
        default=None, description="content_hash of the revision this was derived from."
    )

    components: list[CircuitComponent] = Field(default_factory=list)
    nets: list[Net] = Field(default_factory=list)
    constraints: list[DesignConstraint] = Field(default_factory=list)
    design_assumptions: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _check_referential_integrity(self) -> CircuitIR:
        refs = [c.ref for c in self.components]
        duplicates = sorted({r for r in refs if refs.count(r) > 1})
        if duplicates:
            raise ValueError(f"duplicate component references: {duplicates}")

        net_names = [n.name for n in self.nets]
        dup_nets = sorted({n for n in net_names if net_names.count(n) > 1})
        if dup_nets:
            raise ValueError(f"duplicate net names: {dup_nets}")

        known = set(refs)
        seen_pins: dict[str, str] = {}
        for net in self.nets:
            for ref in net.connections:
                if ref.component not in known:
                    raise ValueError(
                        f"net {net.name!r} references unknown component {ref.component!r}"
                    )
                key = str(ref)
                if key in seen_pins:
                    raise ValueError(
                        f"pin {key} is on two nets: {seen_pins[key]!r} and {net.name!r}"
                    )
                seen_pins[key] = net.name

        constraint_ids = [c.constraint_id for c in self.constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("duplicate constraint ids")
        return self

    # -- identity --------------------------------------------------------

    def canonical_form(self) -> dict[str, object]:
        """The semantic content, in a stable order, with bookkeeping stripped.

        Two circuits with the same canonical form are the same circuit, however
        they were reached. ``revision``, ``parent_hash`` and free-text notes are
        excluded: they describe the history, not the design.
        """
        return {
            "components": sorted(
                (
                    {
                        "ref": c.ref,
                        "part_id": c.part_id,
                        "package": c.package,
                        "value": None if c.value is None else [c.value.value, c.value.unit.value],
                        "i2c_address": c.selected_i2c_address,
                        "placeholder": c.placeholder,
                    }
                    for c in self.components
                ),
                key=lambda d: str(d["ref"]),
            ),
            "nets": sorted(
                (
                    {
                        "name": n.name,
                        "kind": n.kind.value,
                        "connections": sorted(str(r) for r in n.connections),
                        "external_source": (
                            None
                            if n.external_source is None
                            else n.external_source.model_dump(mode="json", exclude={"evidence"})
                        ),
                    }
                    for n in self.nets
                ),
                key=lambda d: str(d["name"]),
            ),
            "constraints": sorted(
                (
                    {
                        "id": c.constraint_id,
                        "kind": c.kind.value,
                        "hard": c.hard,
                        "applies_to": sorted(c.applies_to),
                    }
                    for c in self.constraints
                ),
                key=lambda d: str(d["id"]),
            ),
        }

    @property
    def content_hash(self) -> str:
        """SHA-256 over the canonical form.

        Used by the repair loop to detect oscillation: if applying a patch
        produces a hash already seen, the loop is going in circles and must stop
        and say so rather than burn its iteration budget
        (PRE_IMPLEMENTATION_REVIEW.md 3.4).
        """
        blob = json.dumps(self.canonical_form(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    # -- lookups ---------------------------------------------------------

    def component(self, ref: str) -> CircuitComponent | None:
        for c in self.components:
            if c.ref == ref:
                return c
        return None

    def net(self, name: str) -> Net | None:
        for n in self.nets:
            if n.name == name:
                return n
        return None

    def net_of(self, component: str, pin: str) -> Net | None:
        for n in self.nets:
            if n.has(component, pin):
                return n
        return None

    def nets_of(self, component: str) -> list[Net]:
        return [n for n in self.nets if component in n.components()]

    def components_of_kind(self, part_id_prefix: str) -> list[CircuitComponent]:
        return [c for c in self.components if c.part_id.startswith(part_id_prefix)]

    @property
    def ground_nets(self) -> list[Net]:
        return [n for n in self.nets if n.kind is NetKind.GROUND]

    @property
    def power_nets(self) -> list[Net]:
        return [n for n in self.nets if n.kind is NetKind.POWER]


class CircuitPatchOp(BaseModel):
    """One typed edit to a CircuitIR.

    The repair planner emits these. It never writes files and never mutates
    state directly (AGENT_DESIGN.md); the application applies the patch, and the
    verifier decides whether it helped.
    """

    op: Literal[
        "add_component",
        "remove_component",
        "set_component_value",
        "set_component_package",
        "add_net",
        "remove_net",
        "connect",
        "disconnect",
        "set_i2c_address",
    ]
    target: str = Field(description="Component ref or net name the op applies to.")
    payload: dict[str, object] = Field(default_factory=dict)
    rationale: str
    addresses_finding_ids: list[str] = Field(default_factory=list)


class CircuitPatch(BaseModel):
    """A proposed, reviewable set of edits."""

    patch_id: str
    base_hash: str = Field(description="content_hash of the IR this patch was computed against.")
    operations: list[CircuitPatchOp] = Field(default_factory=list)
    summary: str = ""
    proposed_by: str = "unknown"
