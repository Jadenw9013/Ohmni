"""Functional grouping and signal flows derived from authoritative topology.

Nothing here decides electrical truth. Every grouping is a *presentation*
derived from facts the circuit already states -- net membership, part category,
declared external sources, and the placement Ohmni generated. Each result
carries the ``basis`` it was derived from so the interface can say why a
component is shown where it is, and so a reviewer can check the derivation
instead of trusting it.

For generated projects, fingerprint-bound functional groups recorded during
compilation own the association. Shared supply nets and physical distance do
not replace that declared capacitor ownership. For legacy reports without this
intent, two presentation rules provide an explicitly topology-derived fallback:

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
from ..domain.component import ComponentCategory, Interface, PinRole
from ..physical.models import PlacementRequest
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
        "The processor runs a program to coordinate connected devices.",
    ),
    SystemId.SENSE: (
        "Sensing",
        ("The measurement hardware and the small parts that let it talk to the "
         "processor reliably."),
    ),
    SystemId.IO: (
        "User controls and connections",
        "The interface components and their supporting parts.",
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
    category: ComponentCategory | None = None


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
    circuit: CircuitIR, catalog, placements: dict[str, tuple[float, float]],
    placement_request: PlacementRequest | None = None,
) -> list[ComponentGrouping]:
    """Assign every component to one functional system, deterministically."""
    if placement_request is not None:
        request = PlacementRequest.model_validate(placement_request.model_dump())
        if request.circuit_content_hash != circuit.content_hash:
            raise ValueError("Functional placement groups belong to another circuit")
        grouped = {ref for group in request.groups for ref in group.member_refs}
        if grouped != {part.ref for part in circuit.components}:
            raise ValueError("Functional placement groups do not cover this circuit")
        result = []
        for group in request.groups:
            system = _anchor_system(circuit, catalog, group.anchor_ref)
            if system is None:
                raise ValueError("Functional placement block has no supported anchor")
            for ref in group.member_refs:
                instance = circuit.component(ref)
                result.append(ComponentGrouping(
                    component_ref=ref, part_id=instance.part_id, system=system,
                    anchor=ref == group.anchor_ref,
                    attached_to=None if ref == group.anchor_ref else group.anchor_ref,
                    category=_category(circuit, catalog, ref),
                    basis=f"Compiler-declared functional block: {group.reason}",
                ))
        return sorted(result, key=lambda item: item.component_ref)
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
                anchor=True, category=_category(circuit, catalog, ref),
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
                basis="shares no net with a system anchor", category=_category(circuit, catalog, ref),
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
            anchor=False, attached_to=anchor_ref, basis=basis, category=_category(circuit, catalog, ref),
        ))
    return groupings


def build_systems(groupings: list[ComponentGrouping]) -> list[FunctionalSystem]:
    systems: list[FunctionalSystem] = []
    categories = {item.category for item in groupings if item.anchor}
    for system in SystemId:
        members = [g for g in groupings if g.system is system]
        if not members:
            continue
        label, summary = SYSTEM_LABELS[system]
        if system is SystemId.COMPUTE:
            tasks = []
            if ComponentCategory.SENSOR in categories:
                tasks.append("request sensor readings")
            if ComponentCategory.LED in categories:
                tasks.append("control the indicator light")
            if ComponentCategory.SWITCH in categories:
                tasks.append("read button inputs")
            if ComponentCategory.MEMORY in categories:
                tasks.append("read and write memory")
            if tasks:
                summary = "A program on the processor can " + ", ".join(tasks) + ". Firmware is still required."
        elif system is SystemId.SENSE:
            member_categories = {item.category for item in members if item.anchor}
            if ComponentCategory.MEMORY in member_categories:
                if ComponentCategory.SENSOR in member_categories:
                    label, summary = "Sensing and storage", "Sensors take measurements; memory stores data. A program coordinates their separate buses."
                else:
                    label, summary = "Storage", "Memory chips exchange data with the processor, with nearby supply capacitors and control pull-ups."
        elif system is SystemId.IO:
            member_categories = {item.category for item in members if item.anchor}
            interfaces = [name for category, name in (
                (ComponentCategory.LED, "indicator light"),
                (ComponentCategory.HEADER, "connector header"),
                (ComponentCategory.SWITCH, "switch"),
                (ComponentCategory.CONNECTOR, "external connector"),
            ) if category in member_categories]
            if interfaces:
                names = ", ".join(interfaces[:-1]) + " and " + interfaces[-1] if len(interfaces) > 1 else interfaces[0]
                summary = f"The {names}, with supporting parts."
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


def _role_nets(circuit, spec, ref, roles):
    result = {}
    for role in roles:
        pins = {pin.number for pin in spec.pins if role in pin.roles}
        names = {net.name for net in circuit.nets if any(net.has(ref, pin) for pin in pins)}
        if len(names) != 1:
            return None
        result[role] = next(iter(names))
    return result


def _spi_flows(circuit, catalog):
    """Describe selected SPI wiring, without treating a clock pin as I2C."""
    roles = (PinRole.SPI_SCK, PinRole.SPI_MOSI, PinRole.SPI_MISO, PinRole.SPI_CS)
    devices = []
    for part in circuit.components:
        spec = catalog.get(part.part_id)
        if spec is None or spec.category in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}:
            continue
        if Interface.SPI not in part.selected_interfaces:
            continue
        nets = _role_nets(circuit, spec, part.ref, roles)
        if nets and len(set(nets.values())) == len(roles):
            devices.append((part.ref, nets))
    if not devices:
        return []
    clock = sorted({nets[PinRole.SPI_SCK] for _, nets in devices})
    outgoing = sorted({nets[PinRole.SPI_MOSI] for _, nets in devices})
    incoming = sorted({nets[PinRole.SPI_MISO] for _, nets in devices})
    selects = sorted({nets[PinRole.SPI_CS] for _, nets in devices})
    select_pullups = {
        name: [ref for ref in circuit.net(name).components()
               if _category(circuit, catalog, ref) is ComponentCategory.RESISTOR
               and any(net.kind is NetKind.POWER and ref in net.components() for net in circuit.nets)]
        for name in selects
    }
    data_nets = sorted(set(clock + outgoing + incoming))
    net_names = sorted(set(data_nets + selects))
    refs = sorted({pin.component for name in net_names for pin in circuit.net(name).connections})
    peripherals = [ref for ref, _ in devices]
    controllers = [ref for ref in refs if _category(circuit, catalog, ref) in
                   {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}]
    memories_only = all(_category(circuit, catalog, ref) is ComponentCategory.MEMORY for ref in peripherals)
    return [Flow(
        flow_id="spi_data", label="Memory communication" if memories_only else "SPI communication",
        question="How does the processor store and retrieve data?" if memories_only else "How do these devices communicate?",
        summary="SPI uses a clock and separate send/receive lines. A chip-select line addresses each included device; firmware manages the conversation.",
        stages=[
            FlowStage(title="Select a device",
                      detail=("Each wired chip-select identifies a peripheral. The included resistors bias every select line toward its supply; firmware must select devices correctly."
                              if all(select_pullups.values()) else
                              "Each wired chip-select identifies a peripheral. Supply pull-ups were not found on every select line; inspect the control wiring and device requirements."),
                      net_names=selects, component_refs=refs,
                      pin_labels=[label for name in selects for label in _pin_labels(circuit, name)]),
            FlowStage(title="Send a command with a clock",
                      detail="The processor can send commands and data on the outgoing line while its clock marks the bits. Pin setup, timing and commands require firmware.",
                      net_names=sorted(set(clock + outgoing)), component_refs=controllers + peripherals),
            FlowStage(title="Read the response",
                      detail="The selected device can return data on a separate incoming line. These are physical connections, not a simulated memory transaction.",
                      net_names=incoming, component_refs=peripherals,
                      pin_labels=[label for name in incoming for label in _pin_labels(circuit, name)]),
        ], net_names=net_names, component_refs=refs,
        basis="selected SPI interfaces, documented peripheral pin roles and actual net membership",
    )]


def _button_flows(circuit, catalog):
    buttons = [part.ref for part in circuit.components if _category(circuit, catalog, part.ref) is ComponentCategory.SWITCH]
    signal_names = sorted({net.name for net in circuit.nets if net.kind is NetKind.SIGNAL and net.components() & set(buttons)})
    if not buttons or not signal_names:
        return []
    connected = sorted({pin.component for name in signal_names for pin in circuit.net(name).connections})
    pullups = [ref for ref in connected if _category(circuit, catalog, ref) is ComponentCategory.RESISTOR
               and any(net.kind is NetKind.POWER and ref in net.components() for net in circuit.nets)]
    grounded = [ref for ref in buttons if any(net.kind is NetKind.GROUND and ref in net.components() for net in circuit.nets)]
    return [Flow(
        flow_id="buttons", label="Button inputs", question="How does a press become an input?",
        summary="A button changes an electrical connection. A program reads its input pin and decides what should happen; no button behavior is simulated here.",
        stages=[
            FlowStage(title="Give the idle input a level",
                      detail="The included pull-up resistors bias the inputs toward their supply when the buttons are open." if pullups else "No supply pull-up was found on these input nets.",
                      net_names=signal_names, component_refs=pullups),
            FlowStage(title="Close the button contacts",
                      detail="These buttons connect their signal to ground when their contacts close." if len(grounded) == len(buttons) else "Follow the button terminals to see which connection changes when its contacts close.",
                      net_names=signal_names, component_refs=buttons,
                      pin_labels=[label for name in signal_names for label in _pin_labels(circuit, name, set(buttons))]),
            FlowStage(title="Let the program interpret the press",
                      detail="Firmware must configure and read the input, filter contact bounce, and choose a response. Wiring a button does not supply that program.",
                      net_names=signal_names, component_refs=[ref for ref in connected if _category(circuit, catalog, ref) in
                                                             {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}]),
        ], net_names=signal_names, component_refs=connected,
        basis="switch categories, connected signal/ground nets and observed supply pull-ups",
    )]


def build_flows(circuit: CircuitIR, catalog, groupings: list[ComponentGrouping]) -> list[Flow]:
    """Build the named stories a user can ask for, each read off the netlist.

    A flow is emitted only when the topology it describes is actually present.
    Nothing here invents a path: every stage names nets and pins that exist.
    """
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
        and Interface.I2C in i.selected_interfaces
        and (role_nets := _role_nets(circuit, catalog.require(i.part_id), i.ref, (PinRole.I2C_SDA, PinRole.I2C_SCL)))
        and len(set(role_nets.values())) == 2
    ]
    bus_nets: list[str] = []
    for ref in peripherals:
        spec = catalog.require(circuit.component(ref).part_id)
        bus_pins = {p.number for p in spec.pins if {PinRole.I2C_SDA, PinRole.I2C_SCL} & set(p.roles)}
        for net in circuit.nets:
            if net.kind is NetKind.SIGNAL and any(
                c.component == ref and c.pin in bus_pins for c in net.connections
            ):
                bus_nets.append(net.name)
    bus_nets = sorted(set(bus_nets))
    if peripherals and bus_nets:
        measurement = all(_category(circuit, catalog, ref) is ComponentCategory.SENSOR for ref in peripherals)
        controllers = sorted({
            c.component for name in bus_nets for c in circuit.net(name).connections
            # A compute group also owns passives. Only catalog-identified
            # processors connected to this bus can receive its readings.
            if _category(circuit, catalog, c.component)
            in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}
        })
        pullups = sorted({
            c.component for name in bus_nets for c in circuit.net(name).connections
            if _category(circuit, catalog, c.component) is ComponentCategory.RESISTOR
        })
        stages = [
            FlowStage(
                title="The sensors measure" if measurement else "The devices provide data",
                detail=("The included sensors provide measurements that a program can request."
                        if measurement else "The selected I2C peripherals can exchange data with a suitable program."),
                component_refs=peripherals,
            ),
            FlowStage(
                title="Two wires carry data",
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
            flow_id="sensor_data", label="Sensor data" if measurement else "I2C device data",
            question="How does a measurement reach the processor?" if measurement else "How does data reach the processor?",
            summary=(f"The {humanise_refs(circuit, catalog, peripherals)} talks to the "
                     f"{humanise_refs(circuit, catalog, controllers)} over two shared wires."),
            stages=stages, net_names=bus_nets,
            component_refs=sorted({*peripherals, *controllers, *pullups}),
            basis="peripheral-side bus pin names, then net membership",
        ))

    flows.extend(_spi_flows(circuit, catalog))
    flows.extend(_button_flows(circuit, catalog))

    leds = [i.ref for i in circuit.components
            if _category(circuit, catalog, i.ref) is ComponentCategory.LED]
    for index, led in enumerate(leds):
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
            flow_id="status_led" if len(leds) == 1 else f"led_{led}",
            label="Status light" if len(leds) == 1 else f"Light {index + 1}",
            question="How does the board show me something?",
            summary=(f"A program can use one processor pin to switch the "
                     f"{humanise_refs(circuit, catalog, [led])} on and off through the "
                     f"{humanise_refs(circuit, catalog, series) if series else 'board'}."),
            stages=[
                FlowStage(
                    title="The processor switches a pin",
                    detail=(f"The {humanise_refs(circuit, catalog, drivers)} turns the "
                            "indicator on and off with one output pin when firmware drives it."),
                    net_names=driver_nets, component_refs=drivers,
                ),
                FlowStage(
                    title="A resistor limits the current",
                    detail=(
                        f"The {humanise_refs(circuit, catalog, series)} sits in line with the "
                        "light. It limits current; excessive current can damage an LED."
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
            summary="The connected ground pins share a common return and voltage reference.",
            stages=[FlowStage(
                title="Everything shares one return",
                detail=(
                    f"This net connects {len(ground.connections)} declared ground contacts. "
                    "It provides the return path and the reference for voltage measurements; "
                    "other parts can reach it through components rather than a direct connection."
                ),
                net_names=[ground.name], component_refs=sorted(ground.components()),
                pin_labels=_pin_labels(circuit, ground.name),
            )],
            net_names=[ground.name], component_refs=sorted(ground.components()),
            basis="the net declared as the ground net",
        ))
    return flows
