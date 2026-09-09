"""LED current limiting.

Detecting a series resistor is a topology question, not a pattern match. The
signature of a series element is a *private node*: a net touching exactly two
pins, one of them the LED. A resistor that happens to sit somewhere else on the
LED's net is not in series with it and limits nothing.

The current is then computed the way it should be -- worst case, using the
minimum forward voltage, because that is what produces the highest current.
"""

from __future__ import annotations

from ...domain.component import ComponentCategory, PinRole
from ...domain.evidence import calculated_evidence
from ...domain.units import Quantity, Unit
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule

#: Above this, a chip resistor's power rating starts to matter. An 0603 is
#: typically 100 mW and an 0805 125 mW, but the catalog does not carry ratings
#: yet, so this only raises a flag for a human rather than deciding anything.
RESISTOR_POWER_ATTENTION = Quantity.watts(0.05)


@rule(
    "PB-LED-001",
    "Every LED has a current-limiting resistor in series",
    RuleCategory.ELECTRICAL,
    "Also computes the worst-case current and checks it against the LED's rating.",
)
def led_current_limiting(ctx: VerificationContext, out: ResultBuilder) -> None:
    leds = ctx.instances_of_category(ComponentCategory.LED)
    if not leds:
        out.not_applicable("circuit has no LEDs")
        return

    for instance in leds:
        spec = ctx.spec_of(instance.ref)
        assert spec is not None
        out.examined(f"{instance.ref} ({spec.display_name})")

        anode = _pin_net(ctx, instance.ref, spec, PinRole.ANODE)
        cathode = _pin_net(ctx, instance.ref, spec, PinRole.CATHODE)
        if anode is None or cathode is None:
            out.finding(
                severity=Severity.ERROR,
                title=f"{instance.ref} is not fully connected",
                description=(
                    f"{instance.ref} needs both its anode and cathode on nets; "
                    f"anode={anode or 'unconnected'}, cathode={cathode or 'unconnected'}."
                ),
                components=[instance.ref],
                lesson_topic="led-current-limiting",
            )
            continue

        series = _series_resistor(ctx, instance.ref, anode) or _series_resistor(
            ctx, instance.ref, cathode
        )

        if series is None:
            out.finding(
                severity=Severity.CRITICAL,
                title=f"{instance.ref} has no series current-limiting resistor",
                description=(
                    f"Neither {anode!r} nor {cathode!r} is a private node between "
                    f"{instance.ref} and a resistor, so nothing limits the LED current. An "
                    "LED is a diode: above its forward voltage the current is set only by "
                    "whatever impedance is in the loop. Connected straight across a rail it "
                    "draws until something fails, usually the LED, sometimes the driving pin."
                ),
                components=[instance.ref],
                nets=[anode, cathode],
                auto_fixable=True,
                suggested_fix=(
                    "Add a resistor in series with the LED, sized for the rail voltage and "
                    "the current you want."
                ),
                lesson_topic="led-current-limiting",
            )
            continue

        bridge, led_net = series
        out.examined(f"{instance.ref} series resistor {bridge.ref}")

        if bridge.value is None:
            out.missing(f"{bridge.ref} is in series with {instance.ref} but has no value")
            continue

        source_net = ctx.opposite_net(bridge, led_net)
        drive = _drive_voltage(ctx, source_net, cathode)
        if drive is None:
            out.missing(
                f"{instance.ref}: could not determine the voltage driving {source_net!r}, so "
                "the LED current was not computed"
            )
            continue

        drive_voltage, drive_description = drive
        led_spec = spec.led
        if led_spec is None:
            out.missing(f"{spec.display_name} has no forward-voltage data in the catalog")
            continue

        # Worst case for current is the lowest forward voltage against the
        # highest drive: the LED drops less, so the resistor sees more.
        vf_low = led_spec.forward_voltage.worst_case_low
        assert vf_low is not None
        current = Quantity(
            value=max(0.0, (drive_voltage.value - vf_low.value) / bridge.value.value),
            unit=Unit.AMPERE,
        )
        power = Quantity(
            value=current.value * current.value * bridge.value.value, unit=Unit.WATT
        )

        working = (
            f"I = (V_drive - Vf(min)) / R = ({drive_voltage.engineering()} - "
            f"{vf_low.engineering()}) / {bridge.value.engineering()} = "
            f"{current.engineering()}, driven by {drive_description}"
        )
        current_evidence = calculated_evidence(
            f"{instance.ref} worst-case forward current",
            detail=working,
            quantity=current,
        )
        power_evidence = calculated_evidence(
            f"{bridge.ref} power dissipation",
            detail=(
                f"P = I^2 * R = ({current.engineering()})^2 * {bridge.value.engineering()} "
                f"= {power.engineering()}"
            ),
            quantity=power,
        )
        out.note(f"{instance.ref}: {working}")

        if current > led_spec.max_forward_current:
            out.finding(
                severity=Severity.ERROR,
                title=f"{instance.ref} is driven above its maximum forward current",
                description=(
                    f"{working}, which exceeds the "
                    f"{led_spec.max_forward_current.engineering()} maximum for "
                    f"{spec.display_name}. Running an LED over its rating shortens its life "
                    "and can exceed the driving pin's rating too."
                ),
                components=[instance.ref, bridge.ref],
                nets=[led_net, source_net],
                evidence=[current_evidence, *led_spec.evidence],
                auto_fixable=True,
                suggested_fix=(
                    f"Increase {bridge.ref} to at least "
                    f"{Quantity.ohms((drive_voltage.value - vf_low.value) / led_spec.max_forward_current.value).engineering()}."
                ),
                lesson_topic="led-current-limiting",
            )
        elif power > RESISTOR_POWER_ATTENTION:
            out.finding(
                severity=Severity.WARNING,
                title=f"{bridge.ref} dissipates {power.engineering()}",
                description=(
                    f"{power_evidence.detail}. Check this against the resistor's package "
                    "rating: a 0603 is typically 100 mW and an 0805 125 mW. The catalog does "
                    "not record power ratings, so this could not be decided automatically."
                ),
                components=[bridge.ref],
                evidence=[power_evidence],
                lesson_topic="resistor-power",
            )

    out.limitation(
        "The driving pin's own current rating is not checked: the catalog does not record "
        "per-pin source and sink limits, so an LED within its own rating could still exceed "
        "what the GPIO driving it can supply."
    )


def _pin_net(ctx: VerificationContext, ref: str, spec, role: PinRole) -> str | None:
    for pin in spec.pins_with_role(role):
        net = ctx.circuit.net_of(ref, pin.number)
        if net is not None:
            return net.name
    return None


def _series_resistor(ctx: VerificationContext, led_ref: str, net_name: str):
    """Find a resistor forming a private two-pin node with this LED.

    Exactly two connections on the net, one of them the LED and the other a
    resistor, is the unambiguous signature of a series element.
    """
    net = ctx.circuit.net(net_name)
    if net is None or len(net.connections) != 2:
        return None
    refs = {c.component for c in net.connections}
    if led_ref not in refs or len(refs) != 2:
        return None
    (other_ref,) = refs - {led_ref}
    other_spec = ctx.spec_of(other_ref)
    if other_spec is None or other_spec.category is not ComponentCategory.RESISTOR:
        return None
    for bridge in ctx.two_terminal_bridges:
        if bridge.ref == other_ref and net_name in (bridge.net_a, bridge.net_b):
            return bridge, net_name
    return None


def _drive_voltage(
    ctx: VerificationContext, source_net: str, return_net: str
) -> tuple[Quantity, str] | None:
    """Voltage across the LED branch, worst case high.

    Either the source net has a supply of its own, or it is a logic pin, in
    which case its high level is set by the rail that references it.
    """
    supply = ctx.net_voltage(source_net)
    return_voltage = ctx.net_voltage(return_net)
    return_value = return_voltage.worst_case_low.value if return_voltage.is_known else None

    if supply.is_known and supply.worst_case_high is not None and return_value is not None:
        across = supply.worst_case_high.value - return_value
        return (
            Quantity(value=across, unit=Unit.VOLT),
            f"net {source_net!r} at {supply.worst_case_high.engineering()}",
        )

    if return_value is None:
        return None

    for resolved in ctx.pins_on(ctx.circuit.net(source_net)) if ctx.circuit.net(source_net) else []:
        domain = ctx.logic_domain(resolved)
        if domain is not None and domain.worst_case_high is not None:
            across = domain.worst_case_high.value - return_value
            return (
                Quantity(value=across, unit=Unit.VOLT),
                f"{resolved} driving high from its {domain.worst_case_high.engineering()} rail",
            )
    return None
