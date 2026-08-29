"""Derived views over a circuit, computed once and shared by every rule.

The important thing in this module is :meth:`VerificationContext.net_voltage`.
Nothing declares what voltage a net sits at. It is derived from what physically
drives the net -- an external source, or a regulator's output pin -- and a
component's rail voltage is then found by following its own power pin to its
net. A language model can assert that a pin is "3V3"; it cannot assert its way
out of being wired to the 5 V rail (PRE_IMPLEMENTATION_REVIEW.md 4.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property

from ..adapters import PartCatalog
from ..domain.circuit import CircuitComponent, CircuitIR, Net, NetKind, PinRef
from ..domain.component import (
    PASSIVE_CATEGORIES,
    ComponentCategory,
    ComponentSpec,
    PinRole,
    PinSpec,
)
from ..domain.evidence import Evidence, EvidenceKind, calculated_evidence
from ..domain.requirements import RequirementsSpec
from ..domain.units import Quantity, Unit, ValueRange

GROUND = ValueRange.exact(Quantity.volts(0.0))


@dataclass(frozen=True)
class ResolvedPin:
    """One pin of one instance, joined up with its part facts and its net."""

    ref: PinRef
    instance: CircuitComponent
    spec: ComponentSpec | None
    pin: PinSpec | None
    net: Net | None

    @property
    def is_resolved(self) -> bool:
        return self.spec is not None and self.pin is not None

    def __str__(self) -> str:
        name = self.pin.name if self.pin else "?"
        return f"{self.ref.component}.{self.ref.pin} ({name})"


@dataclass
class NetVoltage:
    """What voltage a net sits at, and how we know.

    ``voltage is None`` means unknown -- normal for a signal net, and a reason
    to report INSUFFICIENT_DATA rather than a pass on a power net.
    """

    net_name: str
    voltage: ValueRange | None = None
    driver_descriptions: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    conflicting_drivers: list[str] = field(default_factory=list)

    @property
    def is_known(self) -> bool:
        return self.voltage is not None

    @property
    def has_conflict(self) -> bool:
        return len(self.conflicting_drivers) > 1

    @property
    def nominal(self) -> Quantity | None:
        return self.voltage.nominal if self.voltage else None

    @property
    def worst_case_high(self) -> Quantity | None:
        return self.voltage.worst_case_high if self.voltage else None

    @property
    def worst_case_low(self) -> Quantity | None:
        return self.voltage.worst_case_low if self.voltage else None


@dataclass(frozen=True)
class TwoTerminalBridge:
    """A two-pin part connecting two nets. The workhorse topology primitive.

    Pull-ups, decoupling capacitors, LED series resistors and USB-C CC
    terminations are all the same shape, so they are all found the same way.
    """

    instance: CircuitComponent
    spec: ComponentSpec
    net_a: str
    net_b: str

    @property
    def ref(self) -> str:
        return self.instance.ref

    @property
    def value(self) -> Quantity | None:
        return self.instance.value


class VerificationContext:
    """Everything a rule needs, resolved once.

    Rules receive this and stay pure functions of it, which is what makes each
    rule independently testable without constructing a whole project.
    """

    def __init__(
        self,
        circuit: CircuitIR,
        catalog: PartCatalog,
        requirements: RequirementsSpec | None = None,
    ) -> None:
        self.circuit = circuit
        self.catalog = catalog
        self.requirements = requirements

        self.specs: dict[str, ComponentSpec] = {}
        self.unresolved_parts: dict[str, str] = {}
        for component in circuit.components:
            spec = catalog.get(component.part_id)
            if spec is None:
                self.unresolved_parts[component.ref] = component.part_id
            else:
                self.specs[component.ref] = spec

        self._net_voltages: dict[str, NetVoltage] | None = None

    # -- basic lookups ---------------------------------------------------

    def spec_of(self, ref: str) -> ComponentSpec | None:
        return self.specs.get(ref)

    def instance(self, ref: str) -> CircuitComponent | None:
        return self.circuit.component(ref)

    def resolve(self, ref: PinRef) -> ResolvedPin | None:
        instance = self.circuit.component(ref.component)
        if instance is None:
            return None
        spec = self.specs.get(ref.component)
        pin = spec.pin(ref.pin) if spec else None
        return ResolvedPin(
            ref=ref,
            instance=instance,
            spec=spec,
            pin=pin,
            net=self.circuit.net_of(ref.component, ref.pin),
        )

    def pins_on(self, net: Net) -> list[ResolvedPin]:
        out: list[ResolvedPin] = []
        for ref in net.connections:
            resolved = self.resolve(ref)
            if resolved is not None:
                out.append(resolved)
        return out

    def instances_of_category(self, *categories: ComponentCategory) -> list[CircuitComponent]:
        wanted = set(categories)
        return [
            c
            for c in self.circuit.components
            if (spec := self.specs.get(c.ref)) is not None and spec.category in wanted
        ]

    @cached_property
    def ground_net_names(self) -> set[str]:
        return {n.name for n in self.circuit.nets if n.kind is NetKind.GROUND}

    def is_ground(self, net_name: str | None) -> bool:
        return net_name is not None and net_name in self.ground_net_names

    # -- net voltage derivation -----------------------------------------

    def net_voltage(self, net_name: str) -> NetVoltage:
        if self._net_voltages is None:
            self._net_voltages = self._derive_net_voltages()
        return self._net_voltages.get(net_name, NetVoltage(net_name=net_name))

    def _derive_net_voltages(self) -> dict[str, NetVoltage]:
        """Compute every net's voltage from its drivers.

        Sources considered, in this order:

        1. Ground nets are 0 V by definition.
        2. A declared external source (USB VBUS, battery). This is the one
           legitimate declaration, because nothing on the board produces it.
        3. A regulator output pin sitting on the net.

        A net with two drivers at different voltages is recorded as a conflict
        rather than silently taking the first one. Two supplies shorted together
        is a real and destructive mistake, and the derivation is where it
        becomes visible.
        """
        out: dict[str, NetVoltage] = {}

        for net in self.circuit.nets:
            nv = NetVoltage(net_name=net.name)

            if net.kind is NetKind.GROUND:
                nv.voltage = GROUND
                nv.driver_descriptions.append("ground net")
                out[net.name] = nv
                continue

            candidates: list[tuple[str, ValueRange, list[Evidence]]] = []

            if net.external_source is not None:
                candidates.append(
                    (
                        f"external {net.external_source.kind.value}",
                        net.external_source.voltage,
                        list(net.external_source.evidence),
                    )
                )

            for resolved in self.pins_on(net):
                if resolved.spec is None or resolved.pin is None:
                    continue
                regulator = resolved.spec.regulator
                if regulator is None:
                    continue
                # Only the regulator's *output* drives a net. Its VIN pin is a
                # load on whatever feeds it, not a source.
                if not resolved.pin.has_role(PinRole.POWER):
                    continue
                from ..domain.component import PinElectricalType

                if resolved.pin.electrical_type is not PinElectricalType.POWER_OUT:
                    continue
                candidates.append(
                    (
                        f"{resolved.instance.ref} ({resolved.spec.display_name}) output",
                        regulator.output_voltage,
                        list(regulator.evidence),
                    )
                )

            if not candidates:
                out[net.name] = nv
                continue

            first_desc, first_range, first_evidence = candidates[0]
            nv.voltage = first_range
            nv.driver_descriptions = [desc for desc, _, _ in candidates]
            nv.evidence = list(first_evidence)

            if len(candidates) > 1:
                distinct: list[str] = []
                for desc, rng, _ in candidates:
                    nominal = rng.nominal
                    reference = first_range.nominal
                    if (
                        nominal is not None
                        and reference is not None
                        and not nominal.is_close(reference, rel_tol=1e-3)
                    ):
                        distinct.append(desc)
                if distinct:
                    nv.conflicting_drivers = [first_desc, *distinct]

            out[net.name] = nv

        return out

    def rail_voltage(self, ref: str, rail_name: str) -> NetVoltage | None:
        """The actual voltage on a component's named supply rail.

        Follows the derivation chain: the part's power pins for that rail ->
        the nets they are on -> those nets' drivers. Returns None when the part
        has no such pin or the pin is not connected, which the caller must
        report as missing data rather than assume.
        """
        spec = self.specs.get(ref)
        if spec is None:
            return None
        rail = spec.rail(rail_name)
        if rail is None:
            return None
        for pin in spec.pins:
            if pin.supply_rail != rail_name or not pin.has_role(PinRole.POWER):
                continue
            net = self.circuit.net_of(ref, pin.number)
            if net is None:
                continue
            voltage = self.net_voltage(net.name)
            if voltage.is_known:
                return voltage
        return None

    def rail_nets(self, ref: str, rail_name: str) -> list[Net]:
        """Every net a component's named supply rail is connected to.

        Normally one. More than one means the part's rail pins were wired to
        different nets, which is itself worth surfacing.
        """
        spec = self.specs.get(ref)
        if spec is None:
            return []
        out: list[Net] = []
        for pin in spec.pins:
            if pin.supply_rail != rail_name or not pin.has_role(PinRole.POWER):
                continue
            net = self.circuit.net_of(ref, pin.number)
            if net is not None and net.name not in {n.name for n in out}:
                out.append(net)
        return out

    def power_pins_of_rail(self, ref: str, rail_name: str) -> list[PinSpec]:
        spec = self.specs.get(ref)
        if spec is None:
            return []
        return [
            p
            for p in spec.pins
            if p.supply_rail == rail_name and p.has_role(PinRole.POWER)
        ]

    def logic_domain(self, resolved: ResolvedPin) -> NetVoltage | None:
        """The supply voltage that sets an I/O pin's logic levels.

        Derived the same way: the pin declares which rail references it (a
        datasheet fact), and the rail's voltage comes from the board.
        """
        if resolved.spec is None or resolved.pin is None or resolved.pin.supply_rail is None:
            return None
        return self.rail_voltage(resolved.ref.component, resolved.pin.supply_rail)

    # -- topology primitives --------------------------------------------

    @cached_property
    def two_terminal_bridges(self) -> list[TwoTerminalBridge]:
        """Every two-pin part, with the pair of nets it connects.

        Parts whose two pins are on the same net, or where either pin is
        unconnected, are excluded: they bridge nothing.
        """
        out: list[TwoTerminalBridge] = []
        for instance in self.circuit.components:
            spec = self.specs.get(instance.ref)
            if spec is None or len(spec.pins) != 2:
                continue
            nets = [self.circuit.net_of(instance.ref, p.number) for p in spec.pins]
            if any(n is None for n in nets):
                continue
            a, b = nets[0], nets[1]
            assert a is not None and b is not None
            if a.name == b.name:
                continue
            out.append(TwoTerminalBridge(instance=instance, spec=spec, net_a=a.name, net_b=b.name))
        return out

    def bridges_between(
        self,
        net_a: str,
        net_b: str | None = None,
        *,
        categories: frozenset[ComponentCategory] | None = None,
    ) -> list[TwoTerminalBridge]:
        """Two-terminal parts connecting ``net_a`` to ``net_b`` (or to anything)."""
        out: list[TwoTerminalBridge] = []
        for bridge in self.two_terminal_bridges:
            ends = {bridge.net_a, bridge.net_b}
            if net_a not in ends:
                continue
            if net_b is not None and net_b not in ends:
                continue
            if categories is not None and bridge.spec.category not in categories:
                continue
            out.append(bridge)
        return out

    def bridges_to_ground(
        self, net_name: str, *, categories: frozenset[ComponentCategory] | None = None
    ) -> list[TwoTerminalBridge]:
        out: list[TwoTerminalBridge] = []
        for bridge in self.bridges_between(net_name, categories=categories):
            other = bridge.net_b if bridge.net_a == net_name else bridge.net_a
            if self.is_ground(other):
                out.append(bridge)
        return out

    def pull_ups_on(self, net_name: str) -> list[tuple[TwoTerminalBridge, NetVoltage]]:
        """Resistors from ``net_name`` up to a net at a higher, known voltage."""
        out: list[tuple[TwoTerminalBridge, NetVoltage]] = []
        for bridge in self.bridges_between(
            net_name, categories=frozenset({ComponentCategory.RESISTOR})
        ):
            other = bridge.net_b if bridge.net_a == net_name else bridge.net_a
            if self.is_ground(other):
                continue
            voltage = self.net_voltage(other)
            if voltage.is_known and (nominal := voltage.nominal) is not None and nominal.value > 0:
                out.append((bridge, voltage))
        return out

    def opposite_net(self, bridge: TwoTerminalBridge, net_name: str) -> str:
        return bridge.net_b if bridge.net_a == net_name else bridge.net_a

    # -- shared derived facts -------------------------------------------

    @cached_property
    def i2c_buses(self) -> list[I2CBus]:
        """I2C buses, derived from peripheral pins that genuinely are SDA/SCL.

        Derived from the *peripheral* side on purpose. A microcontroller GPIO is
        only an I2C pin because firmware says so, but a sensor's SDA pin is SDA
        in silicon. Starting from the definite end avoids guessing.
        """
        sda_nets: dict[str, list[ResolvedPin]] = {}
        scl_nets: dict[str, list[ResolvedPin]] = {}

        for net in self.circuit.nets:
            for resolved in self.pins_on(net):
                if resolved.pin is None:
                    continue
                if resolved.pin.has_role(PinRole.I2C_SDA):
                    sda_nets.setdefault(net.name, []).append(resolved)
                if resolved.pin.has_role(PinRole.I2C_SCL):
                    scl_nets.setdefault(net.name, []).append(resolved)

        buses: list[I2CBus] = []
        for sda_name, sda_pins in sorted(sda_nets.items()):
            devices = {p.ref.component for p in sda_pins}
            # Pair the SDA net with the SCL net that shares the most devices.
            best: tuple[str, int] | None = None
            for scl_name, scl_pins in scl_nets.items():
                shared = len(devices & {p.ref.component for p in scl_pins})
                if shared and (best is None or shared > best[1]):
                    best = (scl_name, shared)
            buses.append(
                I2CBus(
                    sda_net=sda_name,
                    scl_net=best[0] if best else None,
                    sda_pins=sda_pins,
                    scl_pins=scl_nets.get(best[0], []) if best else [],
                )
            )
        return buses

    @cached_property
    def unconnected_pins(self) -> list[ResolvedPin]:
        """Every pin of every resolved part that is on no net at all."""
        out: list[ResolvedPin] = []
        for instance in self.circuit.components:
            spec = self.specs.get(instance.ref)
            if spec is None:
                continue
            for pin in spec.pins:
                if self.circuit.net_of(instance.ref, pin.number) is None:
                    out.append(
                        ResolvedPin(
                            ref=PinRef(component=instance.ref, pin=pin.number),
                            instance=instance,
                            spec=spec,
                            pin=pin,
                            net=None,
                        )
                    )
        return out

    def total_known_load(self, net_name: str) -> tuple[Quantity, list[str], list[str]]:
        """Sum the current drawn from a net by parts that state a figure.

        Returns (known_sum, contributors, parts_with_unknown_draw). Keeping the
        unknowns separate is what lets the regulator rule distinguish "provably
        overloaded" from "cannot tell", instead of understating the load and
        reporting a pass.
        """
        total = 0.0
        contributors: list[str] = []
        unknown: list[str] = []

        for instance in self.circuit.components:
            spec = self.specs.get(instance.ref)
            if spec is None or spec.category in PASSIVE_CATEGORIES:
                continue
            for rail in spec.supply_rails:
                powered_here = False
                for pin in spec.pins:
                    if pin.supply_rail != rail.name or not pin.has_role(PinRole.POWER):
                        continue
                    net = self.circuit.net_of(instance.ref, pin.number)
                    if net is not None and net.name == net_name:
                        powered_here = True
                        break
                if not powered_here:
                    continue
                if rail.current_max is None:
                    unknown.append(f"{instance.ref} rail {rail.name}")
                else:
                    total += rail.current_max.value
                    contributors.append(
                        f"{instance.ref} rail {rail.name} = {rail.current_max.engineering()}"
                    )

        return Quantity(value=total, unit=Unit.AMPERE), contributors, unknown

    def load_evidence(self, net_name: str, contributors: list[str], total: Quantity) -> Evidence:
        return calculated_evidence(
            f"Total known current draw on {net_name}",
            detail="sum of per-rail maxima: " + "; ".join(contributors),
            quantity=total,
        )


@dataclass(frozen=True)
class I2CBus:
    """One I2C bus as found on the board."""

    sda_net: str
    scl_net: str | None
    sda_pins: list[ResolvedPin]
    scl_pins: list[ResolvedPin]

    @property
    def devices(self) -> list[str]:
        return sorted({p.ref.component for p in self.sda_pins})

    def __str__(self) -> str:
        return f"I2C bus SDA={self.sda_net} SCL={self.scl_net or '?'}"


__all__ = [
    "EvidenceKind",
    "I2CBus",
    "NetVoltage",
    "ResolvedPin",
    "TwoTerminalBridge",
    "VerificationContext",
]
