"""Layer 3: electrical constraints on supply rails and voltage domains.

The rule that matters most in the whole system is :func:`supply_within_limits`.
It is also where the distinction between *recommended operating conditions* and
*absolute maximum ratings* is enforced, which VERIFICATION.md calls out and
which most generated designs get wrong.

Severity ladder, in order of precedence:

* above the absolute maximum      -> CRITICAL (the part may be destroyed)
* outside recommended operating   -> ERROR    (the part is not specified to work)
* nominal fine, tolerance is not  -> WARNING  (works today, marginal by design)

Note the third case is only reachable when the supply's tolerance is known. And
note what is *not* here: if the applied voltage is inside the recommended
operating range, an unknown absolute maximum is not missing data. Recommended
operating conditions are by construction inside the absolute maximum, so there
is nothing left to check -- which is why the golden fixture does not need a
figure I could not source.
"""

from __future__ import annotations

from ...domain.component import ComponentCategory, PinElectricalType
from ...domain.evidence import calculated_evidence
from ...domain.units import Quantity
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule

#: Two supplies are treated as the same domain if their nominals agree to
#: within 5%. Wider than float noise, narrower than the gap between any two
#: standard logic rails (1.8 / 2.5 / 3.3 / 5.0).
DOMAIN_TOLERANCE = 0.05


@rule(
    "PB-PWR-001",
    "Every supply rail is inside its recommended operating range",
    RuleCategory.ELECTRICAL,
    "Distinguishes operating limits from absolute maximum ratings.",
)
def supply_within_limits(ctx: VerificationContext, out: ResultBuilder) -> None:
    checked = 0
    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None or not spec.supply_rails:
            continue

        for rail in spec.supply_rails:
            label = f"{component.ref} rail {rail.name}"
            nets = ctx.rail_nets(component.ref, rail.name)
            if not nets:
                if ctx.power_pins_of_rail(component.ref, rail.name):
                    out.missing(f"{label}: supply pin is not connected to any net")
                else:
                    out.missing(f"{label}: the catalog records no supply pin for this rail")
                continue

            if len(nets) > 1:
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{label} is wired to more than one net",
                    description=(
                        f"The pins of {spec.display_name} rail {rail.name} are split across "
                        f"nets {', '.join(sorted(n.name for n in nets))}. A single supply "
                        "domain must sit on one net."
                    ),
                    components=[component.ref],
                    nets=sorted(n.name for n in nets),
                    lesson_topic="power-distribution",
                )
                continue

            net = nets[0]
            voltage = ctx.net_voltage(net.name)
            out.examined(f"{label} on {net.name}")

            if not voltage.is_known:
                out.missing(
                    f"{label}: net {net.name!r} has no identifiable driver, so its voltage "
                    "is unknown"
                )
                continue

            checked += 1
            applied_high = voltage.worst_case_high
            applied_nominal = voltage.nominal
            assert applied_high is not None and applied_nominal is not None

            supporting = [
                *voltage.evidence,
                *rail.evidence,
                calculated_evidence(
                    f"Voltage applied to {label}",
                    detail=(
                        f"derived from net {net.name!r}, driven by "
                        f"{', '.join(voltage.driver_descriptions) or 'unknown'}"
                    ),
                    quantity=applied_nominal,
                ),
            ]

            # 1. Absolute maximum. Only reachable when the applied voltage has
            #    already left the recommended range, since operating is inside
            #    absolute max by construction.
            if rail.absolute_max is not None and not applied_high.at_most(rail.absolute_max):
                out.finding(
                    severity=Severity.CRITICAL,
                    title=f"{label} exceeds the absolute maximum rating",
                    description=(
                        f"Net {net.name!r} can reach {applied_high.engineering()}, above the "
                        f"absolute maximum of {rail.absolute_max.engineering()} for "
                        f"{spec.display_name} rail {rail.name}. This is not an out-of-spec "
                        "operating point; it is the voltage at which the part may be "
                        "permanently damaged. The recommended operating range is "
                        f"{rail.operating}."
                    ),
                    components=[component.ref],
                    nets=[net.name],
                    evidence=supporting,
                    auto_fixable=True,
                    suggested_fix=(
                        f"Move {component.ref} rail {rail.name} to a rail within "
                        f"{rail.operating}."
                    ),
                    lesson_topic="absolute-maximum-vs-operating",
                )
                continue

            # 2. Recommended operating conditions, at the nominal supply voltage.
            if not rail.operating.contains(applied_nominal):
                description = (
                    f"Net {net.name!r} sits at {applied_nominal.engineering()}, outside the "
                    f"recommended operating range {rail.operating} for {spec.display_name} "
                    f"rail {rail.name}. The part is not specified to work here."
                )
                if rail.absolute_max is None:
                    description += (
                        " The catalog has no absolute maximum for this rail, so whether this "
                        "also risks damage could not be determined."
                    )
                    out.missing(
                        f"{label}: no absolute maximum recorded, so damage risk is unassessed"
                    )
                out.finding(
                    severity=Severity.ERROR,
                    title=f"{label} is outside its recommended operating range",
                    description=description,
                    components=[component.ref],
                    nets=[net.name],
                    evidence=supporting,
                    auto_fixable=True,
                    suggested_fix=f"Supply {component.ref} from a rail within {rail.operating}.",
                    lesson_topic="absolute-maximum-vs-operating",
                )
                continue

            # 3. Nominal is fine but the supply's own tolerance leaves the range.
            applied_low = voltage.worst_case_low
            assert applied_low is not None
            excursions = [
                q for q in (applied_low, applied_high) if not rail.operating.contains(q)
            ]
            if excursions:
                out.finding(
                    severity=Severity.WARNING,
                    title=f"{label} leaves its operating range over the supply's tolerance",
                    description=(
                        f"At its nominal {applied_nominal.engineering()} the rail is fine, but "
                        f"net {net.name!r} is specified as {voltage.voltage} and the recommended "
                        f"range for {spec.display_name} rail {rail.name} is {rail.operating}. "
                        "The design is marginal at the ends of the supply tolerance."
                    ),
                    components=[component.ref],
                    nets=[net.name],
                    evidence=supporting,
                    lesson_topic="tolerance-stackup",
                )

    if checked == 0 and not out.missing_items:
        out.not_applicable("no resolved component declares a supply rail")


@rule(
    "PB-PWR-002",
    "No net is driven by two different supplies",
    RuleCategory.ELECTRICAL,
    "Shorting two rails together destroys whichever one loses.",
)
def no_supply_conflict(ctx: VerificationContext, out: ResultBuilder) -> None:
    conflicts = 0
    for net in ctx.circuit.nets:
        voltage = ctx.net_voltage(net.name)
        if not voltage.is_known:
            continue
        out.examined(f"{net.name} driven by {', '.join(voltage.driver_descriptions)}")
        if voltage.has_conflict:
            conflicts += 1
            out.finding(
                severity=Severity.CRITICAL,
                title=f"Net {net.name!r} is driven by two different supplies",
                description=(
                    f"Net {net.name!r} is driven by {', '.join(voltage.conflicting_drivers)}, "
                    "which do not produce the same voltage. Connecting two supplies together "
                    "forces current backwards into one of them."
                ),
                nets=[net.name],
                evidence=voltage.evidence,
                lesson_topic="power-distribution",
            )
    if conflicts == 0 and not any(
        ctx.net_voltage(n.name).is_known for n in ctx.circuit.nets
    ):
        out.not_applicable("no net has an identifiable supply")


@rule(
    "PB-PWR-003",
    "Signals do not cross voltage domains without translation",
    RuleCategory.ELECTRICAL,
    "A 5 V output into a 3.3 V input is the classic hobbyist board-killer.",
)
def voltage_domain_compatibility(ctx: VerificationContext, out: ResultBuilder) -> None:
    checked = 0
    for net in ctx.circuit.nets:
        if ctx.is_ground(net.name):
            continue
        if ctx.net_voltage(net.name).is_known and net.kind.value == "power":
            continue

        domains: dict[str, tuple[Quantity, str]] = {}
        for resolved in ctx.pins_on(net):
            if resolved.pin is None or resolved.spec is None:
                continue
            if resolved.pin.electrical_type in (
                PinElectricalType.PASSIVE,
                PinElectricalType.NO_CONNECT,
                PinElectricalType.FREE,
            ):
                continue
            domain = ctx.logic_domain(resolved)
            if domain is None or domain.nominal is None:
                if resolved.pin.supply_rail is not None:
                    out.missing(
                        f"{resolved} on {net.name}: could not determine the voltage of its "
                        f"reference rail {resolved.pin.supply_rail!r}"
                    )
                continue
            domains[str(resolved)] = (domain.nominal, domain.net_name)

        if len(domains) < 2:
            continue

        checked += 1
        out.examined(f"{net.name}: {len(domains)} referenced pins")

        values = [v for v, _ in domains.values()]
        highest = max(values, key=lambda q: q.value)
        lowest = min(values, key=lambda q: q.value)
        if highest.is_close(lowest, rel_tol=DOMAIN_TOLERANCE):
            continue

        detail = "; ".join(
            f"{pin} referenced to {v.engineering()} ({net_name})"
            for pin, (v, net_name) in sorted(domains.items())
        )
        out.finding(
            severity=Severity.ERROR,
            title=f"Net {net.name!r} joins pins in different voltage domains",
            description=(
                f"Pins on {net.name!r} are referenced to supplies between "
                f"{lowest.engineering()} and {highest.engineering()}: {detail}. Driving a "
                "lower-voltage input from a higher-voltage output exceeds its input rating "
                "and can damage it. This needs a level shifter, or both ends on one rail."
            ),
            nets=[net.name],
            components=sorted({p.split(".")[0] for p in domains}),
            lesson_topic="logic-levels",
        )

    if checked == 0:
        out.not_applicable("no signal net joins two pins with resolvable reference rails")


@rule(
    "PB-PWR-004",
    "Supply pins have the decoupling their datasheet asks for",
    RuleCategory.ELECTRICAL,
    "Connectivity-level only: presence is checked, placement is not.",
)
def decoupling_present(ctx: VerificationContext, out: ResultBuilder) -> None:
    any_rules = False

    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None or not spec.decoupling_rules:
            continue

        for dec in spec.decoupling_rules:
            any_rules = True
            label = f"{component.ref} rail {dec.rail}"
            nets = ctx.rail_nets(component.ref, dec.rail)
            if not nets:
                out.missing(f"{label}: rail is not connected, so decoupling cannot be checked")
                continue
            net = nets[0]
            out.examined(f"{label} on {net.name}")

            caps = ctx.bridges_to_ground(
                net.name, categories=frozenset({ComponentCategory.CAPACITOR})
            )
            valued = [c for c in caps if c.value is not None]

            if dec.per_pin_capacitance is not None:
                target = dec.per_pin_capacitance
                # Accept anything within half to double the recommended value:
                # 100 nF and 220 nF are both legitimate local decoupling, 10 uF
                # is not a substitute for it.
                matching = [
                    c
                    for c in valued
                    if c.value is not None
                    and target.value * 0.5 <= c.value.value <= target.value * 2.0
                ]
                if not matching:
                    out.finding(
                        severity=Severity.ERROR,
                        title=f"{label} has no local decoupling capacitor",
                        description=(
                            f"{spec.display_name} asks for {target.engineering()} of local "
                            f"decoupling on {dec.rail}, and no capacitor of about that value "
                            f"connects net {net.name!r} to ground. "
                            f"{dec.note or ''} Without it the supply sags on every switching "
                            "edge, which shows up as unexplained resets and corrupted bus "
                            "traffic rather than as an obvious failure."
                        ).strip(),
                        components=[component.ref],
                        nets=[net.name],
                        evidence=list(dec.evidence),
                        auto_fixable=True,
                        suggested_fix=(
                            f"Add a {target.engineering()} capacitor from {net.name} to ground, "
                            f"placed next to {component.ref}."
                        ),
                        lesson_topic="decoupling",
                    )

            if dec.bulk_capacitance is not None:
                target = dec.bulk_capacitance
                bulk = [
                    c
                    for c in valued
                    if c.value is not None and c.value.value >= target.value * 0.5
                ]
                if not bulk:
                    out.finding(
                        severity=Severity.WARNING,
                        title=f"{label} has no bulk capacitor",
                        description=(
                            f"{spec.display_name} asks for about {target.engineering()} of bulk "
                            f"capacitance on {dec.rail}. The largest capacitor on net "
                            f"{net.name!r} is "
                            + (
                                max(
                                    (c.value.engineering() for c in valued if c.value), default=""
                                )
                                or "none"
                            )
                            + ". Bulk capacitance supplies the current bursts a regulator "
                            "cannot respond to quickly enough -- on this module, the RF "
                            "transmit bursts."
                        ),
                        components=[component.ref],
                        nets=[net.name],
                        evidence=list(dec.evidence),
                        auto_fixable=True,
                        suggested_fix=f"Add a {target.engineering()} capacitor from {net.name} to ground.",
                        lesson_topic="decoupling",
                    )

            unvalued = [c.ref for c in caps if c.value is None]
            if unvalued:
                out.missing(
                    f"{label}: capacitors {', '.join(sorted(unvalued))} have no value, so they "
                    "could not be counted"
                )

    if not any_rules:
        out.not_applicable("no resolved part states a decoupling requirement")
        return

    out.limitation(
        "Presence only. A netlist cannot show that a capacitor is physically close to the pin "
        "it decouples, and placement is what makes decoupling work. Capacitor placement stays "
        "NOT_VERIFIED until board layout is reviewed."
    )
    out.limitation(
        "Capacitors are counted per rail net, not attributed to individual supply pins. A part "
        "with several supply pins on one net may pass here while still lacking a capacitor at "
        "each pin."
    )
