"""Layer 2: connectivity. The unglamorous checks that catch most real mistakes."""

from __future__ import annotations

from ...domain.component import Interface, PinElectricalType, PinRole
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule


@rule(
    "PB-CONN-001",
    "The board has exactly one ground net",
    RuleCategory.CONNECTIVITY,
    "Two grounds that are never joined is a board that does not work.",
)
def single_ground(ctx: VerificationContext, out: ResultBuilder) -> None:
    grounds = ctx.circuit.ground_nets
    out.examined(*(f"ground net {n.name}" for n in grounds))

    if not grounds:
        out.finding(
            severity=Severity.CRITICAL,
            title="No ground net",
            description=(
                "No net is marked as ground. Every return path, every decoupling capacitor "
                "and every voltage reference in this design is undefined without one."
            ),
            lesson_topic="grounding",
        )
        return

    if len(grounds) > 1:
        names = sorted(n.name for n in grounds)
        out.finding(
            severity=Severity.ERROR,
            title=f"{len(grounds)} separate ground nets",
            description=(
                f"The design declares more than one ground net ({', '.join(names)}) with no "
                "explicit connection between them. Split grounds are occasionally deliberate "
                "in mixed-signal designs, but they are out of MVP scope and are far more "
                "often a wiring mistake."
            ),
            nets=names,
            lesson_topic="grounding",
        )


@rule(
    "PB-CONN-002",
    "Every ground pin reaches ground",
    RuleCategory.CONNECTIVITY,
    "Includes exposed pads, which are easy to leave off a netlist.",
)
def ground_pins_connected(ctx: VerificationContext, out: ResultBuilder) -> None:
    found_any = False
    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None:
            continue
        for pin in spec.pins_with_role(PinRole.GROUND):
            found_any = True
            out.examined(f"{component.ref}.{pin.number} ({pin.name})")
            net = ctx.circuit.net_of(component.ref, pin.number)
            if net is None:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{component.ref}.{pin.number} ({pin.name}) is not connected",
                    description=(
                        f"{spec.display_name} pin {pin.number} is a ground pin and is on no "
                        "net at all."
                    ),
                    components=[component.ref],
                    auto_fixable=True,
                    suggested_fix="Connect it to the ground net.",
                    lesson_topic="grounding",
                )
            elif not ctx.is_ground(net.name):
                out.finding(
                    severity=Severity.CRITICAL,
                    title=f"{component.ref}.{pin.number} ({pin.name}) is not on ground",
                    description=(
                        f"{spec.display_name} pin {pin.number} is a ground pin but is wired to "
                        f"net {net.name!r}, which is not a ground net. Depending on what drives "
                        f"{net.name!r}, this can destroy the part."
                    ),
                    components=[component.ref],
                    nets=[net.name],
                    lesson_topic="grounding",
                )

    if not found_any:
        out.not_applicable("no resolved component declares a ground pin")


@rule(
    "PB-CONN-003",
    "Every supply pin is fed by something that produces a voltage",
    RuleCategory.CONNECTIVITY,
    "A power input on an undriven net is a part that never turns on.",
)
def power_pins_supplied(ctx: VerificationContext, out: ResultBuilder) -> None:
    found_any = False
    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None:
            continue
        for pin in spec.pins:
            is_supply_input = (
                pin.has_role(PinRole.POWER)
                and pin.electrical_type is PinElectricalType.POWER_IN
            )
            if not is_supply_input:
                continue
            found_any = True
            out.examined(f"{component.ref}.{pin.number} ({pin.name})")

            net = ctx.circuit.net_of(component.ref, pin.number)
            if net is None:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{component.ref}.{pin.number} ({pin.name}) is not connected",
                    description=(
                        f"{spec.display_name} needs {pin.name} supplied, but the pin is on no "
                        "net. The part will not power up."
                    ),
                    components=[component.ref],
                    lesson_topic="power-distribution",
                )
                continue

            voltage = ctx.net_voltage(net.name)
            if not voltage.is_known:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{component.ref}.{pin.number} sits on an undriven net",
                    description=(
                        f"{pin.name} of {spec.display_name} is wired to net {net.name!r}, but "
                        "nothing on that net produces a voltage: it has no declared external "
                        "source and no regulator output. Either the supply is missing, or the "
                        "net is fed by a part whose output the catalog does not describe."
                    ),
                    components=[component.ref],
                    nets=[net.name],
                    lesson_topic="power-distribution",
                )

    if not found_any:
        out.not_applicable("no resolved component declares a supply input pin")


@rule(
    "PB-CONN-004",
    "No net connects to only one pin",
    RuleCategory.CONNECTIVITY,
    "A one-pin net is a wire that goes nowhere.",
)
def no_dangling_nets(ctx: VerificationContext, out: ResultBuilder) -> None:
    if not ctx.circuit.nets:
        out.not_applicable("circuit has no nets")
        return

    for net in ctx.circuit.nets:
        out.examined(f"{net.name} ({len(net.connections)} connections)")
        if len(net.connections) == 0:
            out.finding(
                severity=Severity.WARNING,
                title=f"Net {net.name!r} has no connections",
                description=f"Net {net.name!r} is declared but nothing is wired to it.",
                nets=[net.name],
                lesson_topic="netlist-hygiene",
            )
        elif len(net.connections) == 1:
            # An externally-fed net legitimately has one pin at this stage only
            # if it is a test point; otherwise it is a break in the circuit.
            only = net.connections[0]
            out.finding(
                severity=Severity.ERROR,
                title=f"Net {net.name!r} connects to only {only}",
                description=(
                    f"Net {net.name!r} touches a single pin, so it connects nothing to "
                    "anything. Either a connection is missing or the net is left over from "
                    "an earlier revision."
                ),
                nets=[net.name],
                components=[only.component],
                lesson_topic="netlist-hygiene",
            )


@rule(
    "PB-CONN-005",
    "Unconnected pins are accounted for",
    RuleCategory.CONNECTIVITY,
    "Unused GPIO is fine; an unconnected interface pin usually is not.",
)
def unconnected_pins(ctx: VerificationContext, out: ResultBuilder) -> None:
    unconnected = ctx.unconnected_pins
    if not unconnected:
        out.not_applicable("every pin of every resolved part is connected")
        return

    benign_roles = {PinRole.GPIO, PinRole.NOT_CONNECTED, PinRole.ANALOG_IN, PinRole.OTHER}

    # A USB-C receptacle used only for power legitimately leaves D+/D-
    # unconnected. Whether that is expected is decided by what the user asked
    # for, not by hard-coding an exception for connectors.
    wants_usb_data = ctx.requirements is not None and Interface.USB_DEVICE in (
        ctx.requirements.interfaces
    )
    if not wants_usb_data:
        benign_roles |= {PinRole.USB_DP, PinRole.USB_DM, PinRole.USB_SHIELD}

    noteworthy: list[str] = []

    for resolved in unconnected:
        pin = resolved.pin
        assert pin is not None
        out.examined(str(resolved))
        if pin.electrical_type is PinElectricalType.NO_CONNECT:
            continue
        if pin.requires_defined_level:
            # PB-PIN-002 owns floating control pins and reports them properly.
            continue
        if set(pin.roles) <= benign_roles:
            noteworthy.append(str(resolved))
            continue
        out.finding(
            severity=Severity.WARNING,
            title=f"{resolved} is not connected",
            description=(
                f"Pin {pin.name} of {resolved.instance.ref} has role "
                f"{', '.join(r.value for r in pin.roles)} and is on no net. That is rarely "
                "intentional for a pin of this kind."
            ),
            components=[resolved.instance.ref],
            lesson_topic="netlist-hygiene",
        )

    if not wants_usb_data:
        out.note(
            "USB data pins are treated as expected-unconnected because the requirements ask "
            "for USB power only. Add Interface.USB_DEVICE to the requirements if this board "
            "is meant to enumerate over USB."
        )

    if noteworthy:
        out.note(
            f"{len(noteworthy)} unused general-purpose pins left unconnected, which is normal: "
            + ", ".join(noteworthy[:8])
            + ("..." if len(noteworthy) > 8 else "")
        )
