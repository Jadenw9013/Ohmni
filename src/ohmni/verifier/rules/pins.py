"""Layer 2: pin semantics. Contention and floating control pins."""

from __future__ import annotations

from ...domain.component import (
    DRIVING_TYPES,
    PUSH_PULL_DRIVERS,
    ComponentCategory,
    PinRole,
)
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule


@rule(
    "PB-PIN-001",
    "No two devices drive the same net push-pull",
    RuleCategory.PIN_SEMANTICS,
    "Uses KiCad's pin-type vocabulary, so this and KiCad ERC agree by construction.",
)
def output_contention(ctx: VerificationContext, out: ResultBuilder) -> None:
    any_drivers = False

    for net in ctx.circuit.nets:
        # Group by component, not by pin: a part with several paralleled output
        # pins on one net is one driver, not a short.
        drivers: dict[str, list[str]] = {}
        for resolved in ctx.pins_on(net):
            if resolved.pin is None:
                continue
            if resolved.pin.electrical_type in PUSH_PULL_DRIVERS:
                drivers.setdefault(resolved.ref.component, []).append(str(resolved))

        if drivers:
            any_drivers = True
            out.examined(f"{net.name}: {len(drivers)} driving components")

        if len(drivers) > 1:
            described = "; ".join(
                f"{ref} ({', '.join(sorted(pins))})" for ref, pins in sorted(drivers.items())
            )
            out.finding(
                severity=Severity.CRITICAL,
                title=f"{len(drivers)} devices drive net {net.name!r} push-pull",
                description=(
                    f"{described} all drive {net.name!r} with push-pull outputs. When one "
                    "drives high and another drives low, the only thing limiting the current "
                    "is the on-resistance of the two drivers, and one of them loses. "
                    "Open-drain outputs with a pull-up would be fine here; these are not."
                ),
                nets=[net.name],
                components=sorted(drivers),
                lesson_topic="output-contention",
            )

    if not any_drivers:
        out.not_applicable("no push-pull output pins in this circuit")


@rule(
    "PB-PIN-002",
    "Control pins that must not float are tied or driven",
    RuleCategory.PIN_SEMANTICS,
    "Enable, reset, boot-strap and address-select pins.",
)
def no_floating_control_pins(ctx: VerificationContext, out: ResultBuilder) -> None:
    resistor_only = frozenset({ComponentCategory.RESISTOR})
    found_any = False
    # Boot-strap pins left on their documented internal defaults, collected per
    # component so a 38-pin module produces one note rather than five.
    strapping: dict[str, list[str]] = {}

    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None:
            continue

        for pin in spec.pins:
            if not pin.requires_defined_level:
                continue
            found_any = True
            label = f"{component.ref}.{pin.number} ({pin.name})"
            out.examined(label)

            net = ctx.circuit.net_of(component.ref, pin.number)
            if net is None:
                if pin.internal_pull in ("up", "down") and pin.has_role(PinRole.BOOT_STRAP):
                    strapping.setdefault(component.ref, []).append(
                        f"{pin.name} (internal pull-{pin.internal_pull}, unconnected)"
                    )
                    continue
                _report_floating(
                    out,
                    component.ref,
                    spec.display_name,
                    pin,
                    None,
                    "the pin is on no net at all",
                )
                continue

            # Tied straight to ground or to a rail with a known voltage.
            if ctx.is_ground(net.name):
                continue
            if ctx.net_voltage(net.name).is_known:
                continue

            # Held by a resistor to a rail or to ground.
            if ctx.pull_ups_on(net.name) or ctx.bridges_to_ground(
                net.name, categories=resistor_only
            ):
                continue

            # Actively driven by something else on the net.
            actively_driven = any(
                other.pin is not None
                and other.ref.component != component.ref
                and other.pin.electrical_type in DRIVING_TYPES
                for other in ctx.pins_on(net)
            )
            if actively_driven:
                continue

            # A pin with a documented internal pull does have a defined level.
            # Whether relying on it is acceptable depends on the pin: a boot
            # strap using its documented default is an ordinary design choice,
            # an enable pin leaning on a weak internal pull is fragile.
            if pin.internal_pull in ("up", "down"):
                if pin.has_role(PinRole.BOOT_STRAP):
                    strapping.setdefault(component.ref, []).append(
                        f"{pin.name} (internal pull-{pin.internal_pull}"
                        + (f", on net {net.name!r}" if net is not None else ", unconnected")
                        + ")"
                    )
                else:
                    out.finding(
                        severity=Severity.WARNING,
                        title=f"{label} relies on an internal pull-{pin.internal_pull}",
                        description=(
                            f"{spec.display_name} pin {pin.name} has nothing external holding "
                            f"it and depends on an internal pull-{pin.internal_pull}. Internal "
                            "pulls are weak, are often disabled during reset, and vary with "
                            "temperature. For a pin that must have a defined level at power-up "
                            "that is fragile."
                        ),
                        components=[component.ref],
                        nets=[net.name],
                        lesson_topic="floating-pins",
                    )
                continue

            _report_floating(
                out,
                component.ref,
                spec.display_name,
                pin,
                net.name,
                f"net {net.name!r} has no supply, no pull resistor and no driver",
            )

    for ref, pins_used in sorted(strapping.items()):
        spec = ctx.spec_of(ref)
        out.finding(
            severity=Severity.INFO,
            title=f"{ref} leaves {len(pins_used)} strapping pins on their internal defaults",
            description=(
                f"{spec.display_name if spec else ref} boot configuration is set by "
                + ", ".join(sorted(pins_used))
                + ". Relying on the internal pulls is normal and gives the documented default "
                "boot mode, but it is worth knowing which pins these are: anything you attach "
                "to one of them -- an LED, a bus, a header -- is also pulling on it while the "
                "part boots. Add an external resistor wherever you need a level the internal "
                "pull does not give you."
            ),
            components=[ref],
            lesson_topic="strapping-pins",
        )

    if not found_any:
        out.not_applicable("no resolved part declares a pin that must not float")


def _report_floating(  # noqa: ANN001, PLR0913
    out: ResultBuilder,
    ref: str,
    part_name: str,
    pin,
    net_name: str | None,
    reason: str,
) -> None:
    roles = ", ".join(r.value for r in pin.roles)
    out.finding(
        severity=Severity.ERROR,
        title=f"{ref}.{pin.number} ({pin.name}) is floating",
        description=(
            f"{part_name} pin {pin.name} has role {roles} and must sit at a defined level, "
            f"but {reason}. A floating CMOS input drifts with leakage and coupling, so the "
            "part may work on the bench, fail when a hand comes near it, and behave "
            "differently on every board. "
            + (pin.notes or "")
        ).strip(),
        components=[ref],
        nets=[net_name] if net_name else [],
        auto_fixable=True,
        suggested_fix=(
            f"Tie {pin.name} to the appropriate rail or to ground, through a pull resistor "
            "if it also needs to be driven."
        ),
        lesson_topic="floating-pins",
    )
