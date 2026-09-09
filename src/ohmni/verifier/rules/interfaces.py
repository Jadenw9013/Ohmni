"""Layer 4: interface rules. I2C, UART and USB-C sink termination."""

from __future__ import annotations

from ...domain.component import ComponentCategory, PinElectricalType, PinRole
from ...domain.evidence import assumed_evidence, calculated_evidence
from ...domain.units import Quantity
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule

#: Practical bounds for an I2C pull-up on a hobbyist board. Below this the bus
#: exceeds its sink-current limit; above it the rise time gets too slow for
#: standard mode at any realistic bus capacitance.
PULLUP_MIN = Quantity.ohms(1_000)
PULLUP_MAX = Quantity.ohms(10_000)

#: USB Type-C sink termination: Rd = 5.1 kohm on each CC pin, +/-20%.
RD_NOMINAL = Quantity.ohms(5_100)
RD_TOLERANCE = 0.20


@rule(
    "PB-I2C-001",
    "Every I2C bus has pull-up resistors on both lines",
    RuleCategory.INTERFACE,
    "I2C is open-drain: with no pull-up nothing ever drives the line high.",
)
def i2c_pullups_present(ctx: VerificationContext, out: ResultBuilder) -> None:
    buses = ctx.i2c_buses
    if not buses:
        out.not_applicable("no I2C bus found (no part declares an SDA pin)")
        return

    for bus in buses:
        out.examined(str(bus))
        lines: list[tuple[str, str | None]] = [("SDA", bus.sda_net), ("SCL", bus.scl_net)]

        if bus.scl_net is None:
            out.finding(
                severity=Severity.ERROR,
                title=f"I2C bus on {bus.sda_net!r} has no clock line",
                description=(
                    f"An SDA line was found on net {bus.sda_net!r}, but no net carries the "
                    f"matching SCL pin of {', '.join(bus.devices)}. A data line with no clock "
                    "is not a bus."
                ),
                nets=[bus.sda_net],
                components=bus.devices,
                lesson_topic="i2c-basics",
            )

        for label, net_name in lines:
            if net_name is None:
                continue
            pulls = ctx.pull_ups_on(net_name)
            if not pulls:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"I2C {label} line {net_name!r} has no pull-up",
                    description=(
                        f"Net {net_name!r} carries I2C {label} for {', '.join(bus.devices)}, "
                        "and no resistor connects it to a supply. I2C devices only ever pull "
                        "the line low; the pull-up is what makes a high. Without it the bus "
                        "sits low and every transaction fails, usually looking like a dead "
                        "or missing sensor."
                    ),
                    nets=[net_name],
                    components=bus.devices,
                    auto_fixable=True,
                    suggested_fix=(
                        f"Add a 4.7 kohm resistor from {net_name} to the bus supply rail."
                    ),
                    lesson_topic="i2c-pullups",
                )


@rule(
    "PB-I2C-002",
    "I2C pull-ups go to the right rail and are a sane value",
    RuleCategory.INTERFACE,
    "A pull-up to the wrong rail exceeds the input rating of every device on the bus.",
)
def i2c_pullup_quality(ctx: VerificationContext, out: ResultBuilder) -> None:
    buses = ctx.i2c_buses
    if not buses:
        out.not_applicable("no I2C bus found")
        return

    checked = 0
    for bus in buses:
        for label, net_name, pins in (
            ("SDA", bus.sda_net, bus.sda_pins),
            ("SCL", bus.scl_net, bus.scl_pins),
        ):
            if net_name is None:
                continue
            pulls = ctx.pull_ups_on(net_name)
            if not pulls:
                continue  # PB-I2C-001 owns the missing case.

            # Which supply should the bus be pulled to? The interface rail of
            # the devices on it -- derived from their own power pins, not from
            # a label on the net.
            expected: dict[str, Quantity] = {}
            for resolved in pins:
                domain = ctx.logic_domain(resolved)
                if domain is not None and domain.nominal is not None:
                    expected[str(resolved)] = domain.nominal
            if not expected:
                out.missing(
                    f"{label} on {net_name!r}: could not determine the interface supply of "
                    "any device on the bus"
                )
                continue

            checked += 1
            target = max(expected.values(), key=lambda q: q.value)

            for bridge, pull_voltage in pulls:
                out.examined(f"{bridge.ref} pulls {net_name} to {pull_voltage.net_name}")
                nominal = pull_voltage.nominal
                assert nominal is not None

                if not nominal.is_close(target, rel_tol=0.05):
                    out.finding(
                        severity=Severity.ERROR,
                        title=f"I2C {label} is pulled up to the wrong rail",
                        description=(
                            f"{bridge.ref} pulls {net_name!r} up to "
                            f"{pull_voltage.net_name!r} at {nominal.engineering()}, but the "
                            f"devices on this bus run their interface at "
                            f"{target.engineering()} ("
                            + "; ".join(f"{k} at {v.engineering()}" for k, v in sorted(expected.items()))
                            + "). The pull-up sets the bus high level, so this drives every "
                            "device's input above its supply."
                        ),
                        nets=[net_name, pull_voltage.net_name],
                        components=[bridge.ref, *bus.devices],
                        evidence=pull_voltage.evidence,
                        auto_fixable=True,
                        suggested_fix=f"Move {bridge.ref} to the {target.engineering()} rail.",
                        lesson_topic="i2c-pullups",
                    )

                if bridge.value is None:
                    out.missing(f"{bridge.ref} has no resistance value")
                    continue

                if bridge.value < PULLUP_MIN or bridge.value > PULLUP_MAX:
                    out.finding(
                        severity=Severity.WARNING,
                        title=f"I2C pull-up {bridge.ref} is {bridge.value.engineering()}",
                        description=(
                            f"{bridge.ref} is outside the usual "
                            f"{PULLUP_MIN.engineering()} to {PULLUP_MAX.engineering()} range "
                            "for an I2C pull-up. Too small and a device cannot pull the line "
                            "low within its sink-current rating; too large and the line rises "
                            "too slowly for the clock. 4.7 kohm is the standard starting point."
                        ),
                        nets=[net_name],
                        components=[bridge.ref],
                        evidence=[
                            assumed_evidence(
                                "I2C pull-up range",
                                detail=(
                                    "Bounds are practice-based, not computed from the actual "
                                    "bus capacitance, which depends on trace length and is "
                                    "unknown before layout."
                                ),
                                quantity=bridge.value,
                            )
                        ],
                        lesson_topic="i2c-pullups",
                    )

    if checked == 0:
        out.not_applicable("no I2C bus has both pull-ups and a resolvable interface supply")
        return

    out.limitation(
        "Pull-up resistance is range-checked against common practice, not calculated from bus "
        "capacitance and rise time. Actual rise time stays NOT_VERIFIED until layout is known."
    )


@rule(
    "PB-I2C-003",
    "No two devices share an I2C address, and straps match the declared address",
    RuleCategory.INTERFACE,
    "Also checks the declared address against how the strap pin is actually wired.",
)
def i2c_addresses(ctx: VerificationContext, out: ResultBuilder) -> None:
    buses = ctx.i2c_buses
    if not buses:
        out.not_applicable("no I2C bus found")
        return

    for bus in buses:
        assigned: dict[int, list[str]] = {}

        for ref in bus.devices:
            spec = ctx.spec_of(ref)
            instance = ctx.instance(ref)
            if spec is None or instance is None or not spec.i2c_addresses:
                continue
            out.examined(f"{ref} I2C address")

            declared = instance.selected_i2c_address
            if declared is None:
                if len(spec.i2c_addresses) == 1:
                    declared = spec.i2c_addresses[0].address
                else:
                    out.missing(
                        f"{ref} ({spec.display_name}) can sit at "
                        + ", ".join(str(o) for o in spec.i2c_addresses)
                        + " and the design does not say which"
                    )
                    continue

            assigned.setdefault(declared, []).append(ref)

            # Derive the address from the strap wiring and compare. A declared
            # address is an assertion; the strap is the board.
            strapped = _address_from_strap(ctx, ref, spec)
            if strapped is not None and strapped != declared:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{ref} is strapped to a different address than declared",
                    description=(
                        f"The design says {ref} sits at 0x{declared:02X}, but its address "
                        f"select pin is wired for 0x{strapped:02X}. Firmware written against "
                        "the declared address will not find the device."
                    ),
                    components=[ref],
                    auto_fixable=True,
                    suggested_fix=(
                        f"Either change the declared address to 0x{strapped:02X} or rewire "
                        "the address strap."
                    ),
                    lesson_topic="i2c-addressing",
                )

        for address, refs in sorted(assigned.items()):
            if len(refs) > 1:
                alternatives: list[str] = []
                for ref in refs:
                    spec = ctx.spec_of(ref)
                    if spec is None:
                        continue
                    others = [o for o in spec.i2c_addresses if o.address != address]
                    if others:
                        alternatives.append(
                            f"{ref} can move to "
                            + " or ".join(f"{o} ({o.selected_by})" for o in others)
                        )
                out.finding(
                    severity=Severity.ERROR,
                    title=f"Address 0x{address:02X} is used by {len(refs)} devices on one bus",
                    description=(
                        f"{', '.join(sorted(refs))} all sit at 0x{address:02X} on the bus at "
                        f"{bus.sda_net!r}. Two devices answering the same address collide, and "
                        "the bus returns corrupt data rather than an obvious error. "
                        + (" ".join(alternatives) if alternatives else "")
                    ).strip(),
                    components=sorted(refs),
                    nets=[bus.sda_net],
                    auto_fixable=bool(alternatives),
                    suggested_fix=(
                        "Re-strap one device to its alternate address, or put it on a second "
                        "bus."
                    ),
                    lesson_topic="i2c-addressing",
                )


def _address_from_strap(ctx: VerificationContext, ref: str, spec) -> int | None:
    """Work out the I2C address from how the address-select pin is wired."""
    for pin in spec.pins_with_role(PinRole.I2C_ADDRESS_SELECT):
        net = ctx.circuit.net_of(ref, pin.number)
        if net is None:
            return None
        if ctx.is_ground(net.name):
            level = "low"
        else:
            voltage = ctx.net_voltage(net.name)
            nominal = voltage.nominal
            if not voltage.is_known or nominal is None or nominal.value <= 0:
                return None
            level = "high"
        for option in spec.i2c_addresses:
            if option.strap_pin == pin.number and option.strap_level == level:
                return option.address
    return None


@rule(
    "PB-UART-001",
    "UART lines are not transmitter-to-transmitter",
    RuleCategory.INTERFACE,
    "Header labelling is genuinely ambiguous, so that case asks for confirmation.",
)
def uart_orientation(ctx: VerificationContext, out: ResultBuilder) -> None:
    found = False
    for net in ctx.circuit.nets:
        transmitters: list[str] = []
        receivers: list[str] = []
        passives: list[str] = []

        for resolved in ctx.pins_on(net):
            if resolved.pin is None:
                continue
            if resolved.pin.has_role(PinRole.UART_TX):
                transmitters.append(str(resolved))
            elif resolved.pin.has_role(PinRole.UART_RX):
                receivers.append(str(resolved))
            elif resolved.pin.electrical_type is PinElectricalType.PASSIVE:
                passives.append(str(resolved))

        if not transmitters and not receivers:
            continue
        found = True
        out.examined(f"{net.name}: {len(transmitters)} TX, {len(receivers)} RX")

        if len(transmitters) > 1:
            out.finding(
                severity=Severity.ERROR,
                title=f"Two transmitters share net {net.name!r}",
                description=(
                    f"{', '.join(sorted(transmitters))} are both UART transmit pins on the "
                    "same net. Two push-pull drivers fight whenever they disagree, and "
                    "neither device receives anything."
                ),
                nets=[net.name],
                components=sorted({t.split(".")[0] for t in transmitters}),
                lesson_topic="uart-basics",
            )
        elif transmitters and not receivers and passives:
            out.finding(
                severity=Severity.INFO,
                title=f"UART pin orientation on {net.name!r} needs human confirmation",
                description=(
                    f"{transmitters[0]} goes to a connector pin ({', '.join(sorted(passives))}) "
                    "rather than to another UART device, so the correct wiring depends on how "
                    "that header is labelled. Both conventions exist in shipping products: a "
                    "header labelled from the board's point of view wants TX on the pin marked "
                    "TX, one labelled from the programmer's point of view wants the opposite. "
                    "This cannot be settled from the netlist. Confirm against the programmer "
                    "you intend to use."
                ),
                nets=[net.name],
                components=sorted({t.split(".")[0] for t in transmitters} | {p.split(".")[0] for p in passives}),
                lesson_topic="uart-header-conventions",
            )

    if not found:
        out.not_applicable("no UART pins in this circuit")
        return

    out.limitation(
        "Orientation against an external programmer cannot be verified from connectivity. "
        "Where a UART reaches a bare header, the wiring stays HUMAN_CONFIRMED at best."
    )


@rule(
    "PB-USB-001",
    "A USB-C sink presents Rd on both CC pins",
    RuleCategory.INTERFACE,
    "Without Rd, a Type-C source never turns VBUS on. The board looks dead.",
)
def usb_c_cc_termination(ctx: VerificationContext, out: ResultBuilder) -> None:
    cc_pins: list[tuple[str, str, str]] = []  # (ref, pin number, net name)
    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None:
            continue
        for pin in spec.pins_with_role(PinRole.USB_CC):
            net = ctx.circuit.net_of(component.ref, pin.number)
            cc_pins.append((component.ref, pin.name, net.name if net else ""))

    if not cc_pins:
        out.not_applicable("no USB-C CC pins in this circuit")
        return

    resistor_only = frozenset({ComponentCategory.RESISTOR})
    used_resistors: dict[str, list[str]] = {}

    for ref, pin_name, net_name in cc_pins:
        out.examined(f"{ref}.{pin_name} on {net_name or 'nothing'}")
        if not net_name:
            out.finding(
                severity=Severity.ERROR,
                title=f"{ref} {pin_name} is not connected",
                description=(
                    f"{pin_name} carries the Type-C sink termination and is on no net. A "
                    "Type-C source detects a sink by seeing Rd on CC; with the pin floating "
                    "it never enables VBUS, and the board appears completely dead on a "
                    "C-to-C cable while working on a legacy A-to-C cable."
                ),
                components=[ref],
                auto_fixable=True,
                suggested_fix=f"Add a {RD_NOMINAL.engineering()} resistor from {pin_name} to ground.",
                lesson_topic="usb-c-sink",
            )
            continue

        pulldowns = ctx.bridges_to_ground(net_name, categories=resistor_only)
        if not pulldowns:
            out.finding(
                severity=Severity.ERROR,
                title=f"{ref} {pin_name} has no Rd pull-down",
                description=(
                    f"Net {net_name!r} carries {pin_name} but no resistor connects it to "
                    f"ground. A Type-C sink must present Rd = {RD_NOMINAL.engineering()} on "
                    "each CC pin or the source will not enable VBUS."
                ),
                components=[ref],
                nets=[net_name],
                auto_fixable=True,
                suggested_fix=f"Add a {RD_NOMINAL.engineering()} resistor from {net_name} to ground.",
                lesson_topic="usb-c-sink",
            )
            continue

        for bridge in pulldowns:
            used_resistors.setdefault(bridge.ref, []).append(pin_name)
            if bridge.value is None:
                out.missing(f"{bridge.ref} has no resistance value")
                continue
            low = RD_NOMINAL.scaled(1 - RD_TOLERANCE)
            high = RD_NOMINAL.scaled(1 + RD_TOLERANCE)
            if bridge.value < low or bridge.value > high:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{bridge.ref} is {bridge.value.engineering()}, not Rd",
                    description=(
                        f"{bridge.ref} terminates {pin_name} but is "
                        f"{bridge.value.engineering()}. Type-C requires "
                        f"{RD_NOMINAL.engineering()} +/-{RD_TOLERANCE:.0%} "
                        f"({low.engineering()} to {high.engineering()}) for a sink. Other "
                        "values advertise a different role and can leave VBUS off."
                    ),
                    components=[bridge.ref, ref],
                    nets=[net_name],
                    evidence=[
                        calculated_evidence(
                            "Rd tolerance band",
                            detail=(
                                f"{RD_NOMINAL.engineering()} +/-{RD_TOLERANCE:.0%} = "
                                f"{low.engineering()} to {high.engineering()}"
                            ),
                            quantity=bridge.value,
                        )
                    ],
                    auto_fixable=True,
                    suggested_fix=f"Change {bridge.ref} to {RD_NOMINAL.engineering()}.",
                    lesson_topic="usb-c-sink",
                )

    shared = {ref: pins for ref, pins in used_resistors.items() if len(set(pins)) > 1}
    for resistor_ref, pins in sorted(shared.items()):
        out.finding(
            severity=Severity.ERROR,
            title=f"{resistor_ref} is shared between {' and '.join(sorted(set(pins)))}",
            description=(
                "CC1 and CC2 each need their own Rd. One resistor shared between them ties "
                "the two CC pins together, which breaks cable-orientation detection and can "
                "confuse the source into seeing the wrong role."
            ),
            components=[resistor_ref],
            auto_fixable=True,
            suggested_fix="Give each CC pin a separate 5.1 kohm resistor to ground.",
            lesson_topic="usb-c-sink",
        )
