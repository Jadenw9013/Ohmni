"""Functional grouping and signal flows derived from authoritative topology.

Nothing here decides electrical truth. Every grouping is a *presentation*
derived from facts the circuit already states -- net membership, part category,
declared external sources, and the placement Ohmni generated. Each result
carries the ``basis`` it was derived from so the interface can say why a
component is shown where it is, and so a reviewer can check the derivation
instead of trusting it.

Two rules do the work:

* A component whose part category makes it a *functional anchor* defines a
  system. Anchors are never reassigned.
* Every other component attaches to the anchor it shares its most **local**
  net with, and where several anchors share that net, to the physically
  nearest one. Locality matters because a passive on a two-pin net is wired to
  exactly one thing, while a decoupling capacitor on a 14-pin rail is only
  distinguishable by the distance the layout rules already measure.
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, Field

from ..domain.circuit import CircuitIR, NetKind
from ..domain.component import ComponentCategory
from .naming import component_term, humanise_refs, net_term, phrase

#: A net with at most this many pins wires a component to something specific.
#: Larger nets are shared rails, where membership alone proves nothing about
#: which component a passive actually serves.
LOCAL_NET_MAX_PINS = 4


class SystemId(StrEnum):
    POWER = "power"
    COMPUTE = "compute"
    SENSE = "sense"
    IO = "io"


SYSTEM_LABELS: dict[SystemId, tuple[str, str]] = {
    SystemId.POWER: (
        "Power",
        ("Takes power from the USB-C connector and turns it into the steady "
         "low voltage the rest of the board runs on."),
    ),
    SystemId.COMPUTE: (
        "Main computer",
        ("The processor. It reads the sensor, decides what to do, and drives "
         "the indicator."),
    ),
    SystemId.SENSE: (
        "Sensing",
        ("The measurement hardware and the small parts that let it talk to the "
         "processor reliably."),
    ),
    SystemId.IO: (
        "User controls and connections",
        ("The parts you see and touch: the indicator light and the header used "
         "to program the board."),
    ),
}

_ANCHOR_CATEGORIES: dict[ComponentCategory, SystemId] = {
    ComponentCategory.REGULATOR_LINEAR: SystemId.POWER,
    ComponentCategory.REGULATOR_SWITCHING: SystemId.POWER,
    ComponentCategory.MCU: SystemId.COMPUTE,
    ComponentCategory.MCU_MODULE: SystemId.COMPUTE,
    ComponentCategory.SENSOR: SystemId.SENSE,
    ComponentCategory.MEMORY: SystemId.SENSE,
    ComponentCategory.LED: SystemId.IO,
    ComponentCategory.SWITCH: SystemId.IO,
    ComponentCategory.HEADER: SystemId.IO,
}


def system_name(system: SystemId) -> str:
    """What a functional system is called for a reader."""
    return SYSTEM_LABELS[system][0] if system in SYSTEM_LABELS else system.value.capitalize()


class ComponentGrouping(BaseModel):
    """One component's system membership and the derivation that produced it."""

    component_ref: str
    part_id: str
    system: SystemId
    anchor: bool
    attached_to: str | None = None
    basis: str


class FunctionalSystem(BaseModel):
    system: SystemId
    label: str
    summary: str
    component_refs: list[str]
    anchor_refs: list[str]


class FlowStage(BaseModel):
    """One step of a signal or power story, named entirely by real topology."""

    title: str
    detail: str
    net_names: list[str] = Field(default_factory=list)
    component_refs: list[str] = Field(default_factory=list)
    pin_labels: list[str] = Field(default_factory=list)


class Flow(BaseModel):
    flow_id: str
    label: str
    question: str
    summary: str
    stages: list[FlowStage]
    net_names: list[str]
    component_refs: list[str]
    basis: str


def _category(circuit: CircuitIR, catalog, ref: str) -> ComponentCategory | None:
    instance = circuit.component(ref)
    if instance is None:
        return None
    spec = catalog.get(instance.part_id)
    return spec.category if spec else None


def _anchor_system(circuit: CircuitIR, catalog, ref: str) -> SystemId | None:
    """Anchors are decided by part category, plus one topological exception."""
    category = _category(circuit, catalog, ref)
    if category is None:
        return None
    if category is ComponentCategory.CONNECTOR:
        # A connector is a power anchor only when a net it sits on declares an
        # external source. That is a fact the circuit states, not a guess from
        # the part's name.
        for net in circuit.nets:
            if net.external_source is not None and ref in net.components():
                return SystemId.POWER
        return SystemId.IO
    return _ANCHOR_CATEGORIES.get(category)


def _distance(placements: dict[str, tuple[float, float]], a: str, b: str) -> float:
    if a not in placements or b not in placements:
        return math.inf
    ax, ay = placements[a]
    bx, by = placements[b]
    return math.hypot(ax - bx, ay - by)


def group_components(
    circuit: CircuitIR, catalog, placements: dict[str, tuple[float, float]]
) -> list[ComponentGrouping]:
    """Assign every component to one functional system, deterministically."""
    anchors: dict[str, SystemId] = {}
    for instance in circuit.components:
        system = _anchor_system(circuit, catalog, instance.ref)
        if system is not None:
            anchors[instance.ref] = system

    nets_by_component: dict[str, list] = {}
    for net in circuit.nets:
        if net.kind is NetKind.GROUND:
            continue
        for ref in net.components():
            nets_by_component.setdefault(ref, []).append(net)

    groupings: list[ComponentGrouping] = []
    for instance in sorted(circuit.components, key=lambda item: item.ref):
        ref = instance.ref
        if ref in anchors:
            groupings.append(ComponentGrouping(
                component_ref=ref, part_id=instance.part_id, system=anchors[ref],
                anchor=True,
                basis=f"{instance.part_id} is a {_category(circuit, catalog, ref).value.replace('_', ' ')}",
            ))
            continue
        nets = nets_by_component.get(ref, [])
        local = [net for net in nets if len(net.connections) <= LOCAL_NET_MAX_PINS]

        def anchor_candidates(pool, subject=ref):
            found: list[tuple[float, str, str]] = []
            for net in pool:
                for other in sorted(net.components()):
                    if other != subject and other in anchors:
                        found.append((_distance(placements, subject, other), other, net.name))
            return found

        # Local nets are preferred, but only when one of them actually reaches
        # an anchor. A component whose private net connects it to two other
        # passives must still fall back to the shared rails, or it would be
        # reported as attached to nothing while sitting on a rail with four
        # anchors on it.
        candidates = anchor_candidates(local)
        used_local = bool(candidates)
        if not candidates:
            candidates = anchor_candidates(nets)
        if not candidates:
            groupings.append(ComponentGrouping(
                component_ref=ref, part_id=instance.part_id, system=SystemId.IO, anchor=False,
                basis="shares no net with a system anchor",
            ))
            continue
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        distance, anchor_ref, net_name = candidates[0]
        if used_local:
            basis = f"wired to {anchor_ref} on {net_name}, a {len(circuit.net(net_name).connections)}-pin net"
        else:
            basis = (
                f"on shared net {net_name}; placed {distance:.1f} mm from {anchor_ref}, "
                "the nearest part it can serve"
            )
        groupings.append(ComponentGrouping(
            component_ref=ref, part_id=instance.part_id, system=anchors[anchor_ref],
            anchor=False, attached_to=anchor_ref, basis=basis,
        ))
    return groupings


def build_systems(groupings: list[ComponentGrouping]) -> list[FunctionalSystem]:
    systems: list[FunctionalSystem] = []
    for system in SystemId:
        members = [g for g in groupings if g.system is system]
        if not members:
            continue
        label, summary = SYSTEM_LABELS[system]
        systems.append(FunctionalSystem(
            system=system, label=label, summary=summary,
            component_refs=[g.component_ref for g in members],
            anchor_refs=[g.component_ref for g in members if g.anchor],
        ))
    return systems


def _pin_labels(circuit: CircuitIR, net_name: str, refs: set[str] | None = None) -> list[str]:
    net = circuit.net(net_name)
    if net is None:
        return []
    return [str(pin) for pin in net.connections if refs is None or pin.component in refs]


def build_flows(circuit: CircuitIR, catalog, groupings: list[ComponentGrouping]) -> list[Flow]:
    """Build the named stories a user can ask for, each read off the netlist.

    A flow is emitted only when the topology it describes is actually present.
    Nothing here invents a path: every stage names nets and pins that exist.
    """
    by_ref = {g.component_ref: g for g in groupings}
    flows: list[Flow] = []

    source_net = next((n for n in circuit.nets if n.external_source is not None), None)
    ground = next((n for n in circuit.nets if n.kind is NetKind.GROUND), None)
    regulator = next(
        (i.ref for i in circuit.components
         if _category(circuit, catalog, i.ref) in
         {ComponentCategory.REGULATOR_LINEAR, ComponentCategory.REGULATOR_SWITCHING}),
        None,
    )

    if source_net is not None and regulator is not None:
        spec = catalog.require(circuit.component(regulator).part_id)
        out_pins = [p.number for p in spec.pins if p.electrical_type.value == "power_out"]
        out_net = next(
            (n for n in circuit.nets
             if n.kind is NetKind.POWER and any(
                 ref.component == regulator and ref.pin in out_pins for ref in n.connections)),
            None,
        )
        if out_net is not None:
            consumers = sorted(out_net.components() - {regulator})
            major = [ref for ref in consumers
                     if _category(circuit, catalog, ref) in _ANCHOR_CATEGORIES] or consumers
            supply = net_term(circuit, catalog, source_net.name)
            rail = net_term(circuit, catalog, out_net.name)
            regulator_name = component_term(circuit, catalog, regulator)
            connector = humanise_refs(circuit, catalog, [
                ref for ref in sorted(source_net.components())
                if _category(circuit, catalog, ref) is ComponentCategory.CONNECTOR
            ])
            stages = [
                FlowStage(
                    title="Power arrives",
                    detail=(
                        f"The {connector} brings {phrase(supply)} into the board."
                    ),
                    net_names=[source_net.name],
                    component_refs=sorted(source_net.components()),
                    pin_labels=_pin_labels(circuit, source_net.name),
                ),
                FlowStage(
                    title="The regulator steps it down",
                    detail=(
                        f"The {phrase(regulator_name)} takes that in and produces a steadier, "
                        f"lower {phrase(rail)}. Turning one voltage into another is the whole "
                        "job of a voltage regulator."
                    ),
                    net_names=[source_net.name, out_net.name],
                    component_refs=[regulator],
                    pin_labels=_pin_labels(circuit, out_net.name, {regulator}),
                ),
                FlowStage(
                    title="Everything else runs from it",
                    detail=(
                        f"The {humanise_refs(circuit, catalog, major)} all take their "
                        f"supply from that {phrase(rail)}."
                    ),
                    net_names=[out_net.name],
                    component_refs=consumers,
                    pin_labels=_pin_labels(circuit, out_net.name),
                ),
            ]
            flows.append(Flow(
                flow_id="power", label="Power", question="Where does the electricity go?",
                summary=(
                    f"{supply.human} comes in from the connector, the "
                    f"{phrase(regulator_name)} converts it, and {phrase(rail)} feeds the rest "
                    "of the board."
                ),
                stages=stages, net_names=[source_net.name, out_net.name],
                component_refs=sorted({*source_net.components(), regulator, *consumers}),
                basis="declared external source, regulator power-out pins, and net membership",
            ))

    # I2C: derived from the peripheral side, matching the verifier's own rule.
    peripherals = [
        i.ref for i in circuit.components
        if _category(circuit, catalog, i.ref) in {ComponentCategory.SENSOR, ComponentCategory.MEMORY}
    ]
    bus_nets: list[str] = []
    for ref in peripherals:
        spec = catalog.require(circuit.component(ref).part_id)
        bus_pins = {p.number for p in spec.pins if p.name.upper() in {"SDA", "SDI", "SCK", "SCL"}}
        for net in circuit.nets:
            if net.kind is NetKind.SIGNAL and any(
                c.component == ref and c.pin in bus_pins for c in net.connections
            ):
                bus_nets.append(net.name)
    bus_nets = sorted(set(bus_nets))
    if peripherals and bus_nets:
        controllers = sorted({
            c.component for name in bus_nets for c in circuit.net(name).connections
            if by_ref.get(c.component) and by_ref[c.component].system is SystemId.COMPUTE
        })
        pullups = sorted({
            c.component for name in bus_nets for c in circuit.net(name).connections
            if _category(circuit, catalog, c.component) is ComponentCategory.RESISTOR
        })
        stages = [
            FlowStage(
                title="The sensor measures",
                detail=f"The {humanise_refs(circuit, catalog, peripherals)} does the "
                       "physical measurement.",
                component_refs=peripherals,
            ),
            FlowStage(
                title="Two wires carry the reading",
                detail=(
                    "Two wires run between them: one carries the data, the other a clock so "
                    "both ends agree when each bit is valid."
                ),
                net_names=bus_nets,
                component_refs=sorted({c.component for n in bus_nets for c in circuit.net(n).connections}),
                pin_labels=[label for name in bus_nets for label in _pin_labels(circuit, name)],
            ),
            FlowStage(
                title="Resistors hold the wires high",
                detail=(
                    f"{'A resistor on each wire holds' if len(pullups) > 1 else 'A resistor holds'}"
                    " them up when nothing is driving them. Without that they would float at an "
                    "undefined level and the reading would be unreliable."
                ) if pullups else "No pull-up resistors were found on this bus.",
                net_names=bus_nets, component_refs=pullups,
            ),
            FlowStage(
                title="The processor reads it",
                detail=(f"The {humanise_refs(circuit, catalog, controllers)} receives the "
                        "measurement.") if controllers
                       else "No processor pin was found on this bus.",
                net_names=bus_nets, component_refs=controllers,
            ),
        ]
        flows.append(Flow(
            flow_id="sensor_data", label="Sensor data",
            question="How does a measurement reach the processor?",
            summary=(f"The {humanise_refs(circuit, catalog, peripherals)} talks to the "
                     f"{humanise_refs(circuit, catalog, controllers)} over two shared wires."),
            stages=stages, net_names=bus_nets,
            component_refs=sorted({*peripherals, *controllers, *pullups}),
            basis="peripheral-side bus pin names, then net membership",
        ))

    leds = [i.ref for i in circuit.components
            if _category(circuit, catalog, i.ref) is ComponentCategory.LED]
    if leds:
        led = leds[0]
        led_nets = sorted({n.name for n in circuit.nets
                           if led in n.components() and n.kind is not NetKind.GROUND})
        chain = sorted({c.component for name in led_nets for c in circuit.net(name).connections})
        series = [ref for ref in chain
                  if _category(circuit, catalog, ref) is ComponentCategory.RESISTOR]
        extended = sorted(set(chain) | {
            c.component
            for ref in series
            for n in circuit.nets if ref in n.components() and n.kind is not NetKind.GROUND
            for c in n.connections
        })
        # The driving net is the one a series element shares with something that
        # is neither the LED nor another series element.
        driver_nets = sorted({
            n.name for ref in series for n in circuit.nets
            if ref in n.components() and n.kind is not NetKind.GROUND
            and n.components() - set(series) - {led}
        })
        drivers = sorted({c.component for name in driver_nets
                          for c in circuit.net(name).connections
                          if c.component not in series and c.component != led})
        flows.append(Flow(
            flow_id="status_led", label="Status light",
            question="How does the board show me something?",
            summary=(f"A single processor pin switches the "
                     f"{humanise_refs(circuit, catalog, [led])} on and off through the "
                     f"{humanise_refs(circuit, catalog, series) if series else 'board'}."),
            stages=[
                FlowStage(
                    title="The processor switches a pin",
                    detail=(f"The {humanise_refs(circuit, catalog, drivers)} turns the "
                            "indicator on and off with one output pin."),
                    net_names=driver_nets, component_refs=drivers,
                ),
                FlowStage(
                    title="A resistor limits the current",
                    detail=(
                        f"The {humanise_refs(circuit, catalog, series)} sits in line with the "
                        "light. An LED with no resistor in front of it draws whatever current "
                        "it can and destroys itself."
                    ) if series else "No series resistor was found for this LED.",
                    net_names=sorted(set(driver_nets) | set(led_nets)), component_refs=series,
                ),
                FlowStage(
                    title="The LED lights",
                    detail="Current flows through the light to ground, and it glows.",
                    net_names=led_nets, component_refs=[led],
                    pin_labels=[label for name in led_nets for label in _pin_labels(circuit, name, {led})],
                ),
            ],
            net_names=sorted(set(led_nets) | set(driver_nets)),
            component_refs=extended, basis="LED part category and series net topology",
        ))

    headers = [i.ref for i in circuit.components
               if _category(circuit, catalog, i.ref) is ComponentCategory.HEADER]
    if headers:
        header = headers[0]
        header_nets = sorted({n.name for n in circuit.nets if header in n.components()})
        flows.append(Flow(
            flow_id="programming", label="Programming",
            question="How do I put my code on it?",
            summary=(f"The {humanise_refs(circuit, catalog, [header])} brings "
                     f"{len(header_nets)} connections out so you can load your program."),
            stages=[FlowStage(
                title="The header exposes the processor",
                detail=(
                    "These are pins you can clip a programmer onto. Ohmni cannot settle which "
                    "way round the header should face from the wiring alone, so it says so "
                    "rather than guessing."
                ),
                net_names=header_nets, component_refs=[header],
                pin_labels=[label for name in header_nets for label in _pin_labels(circuit, name, {header})],
            )],
            net_names=header_nets,
            component_refs=sorted({c.component for n in header_nets for c in circuit.net(n).connections}),
            basis="header part category and net membership",
        ))

    if ground is not None:
        flows.append(Flow(
            flow_id="ground", label="Ground",
            question="What is ground?",
            summary="Every part on the board shares one common return path.",
            stages=[FlowStage(
                title="Everything shares one return",
                detail=(
                    "Current has to get back to where it came from. Every part on this board "
                    f"connects to ground through {len(ground.connections)} pins, and it is the "
                    "reference every voltage on the board is measured against."
                ),
                net_names=[ground.name], component_refs=sorted(ground.components()),
                pin_labels=_pin_labels(circuit, ground.name),
            )],
            net_names=[ground.name], component_refs=sorted(ground.components()),
            basis="the net declared as the ground net",
        ))
    return flows
