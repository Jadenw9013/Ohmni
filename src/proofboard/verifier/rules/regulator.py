"""Regulator sizing and headroom.

The current-capacity rule is careful about what it does not know. A load sum
built from only the parts that publish a figure is a *lower bound*, so:

* lower bound already over capacity  -> FAIL. Definitive: adding the unknown
  parts can only make it worse.
* lower bound under capacity, but some parts publish nothing -> INSUFFICIENT_DATA.

Silently summing the known parts and reporting a pass would understate the load,
which is exactly how an undersized regulator reaches a real board.
"""

from __future__ import annotations

from ...domain.component import ComponentCategory, PinElectricalType, PinRole
from ...domain.evidence import calculated_evidence
from ...domain.units import Quantity, Unit
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule

#: Warn when a regulator is loaded to within this fraction of its rating.
MIN_HEADROOM = 0.10

REGULATOR_CATEGORIES = (
    ComponentCategory.REGULATOR_LINEAR,
    ComponentCategory.REGULATOR_SWITCHING,
)


def _output_net(ctx: VerificationContext, ref: str) -> str | None:
    spec = ctx.spec_of(ref)
    if spec is None:
        return None
    for pin in spec.pins:
        if (
            pin.has_role(PinRole.POWER)
            and pin.electrical_type is PinElectricalType.POWER_OUT
        ):
            net = ctx.circuit.net_of(ref, pin.number)
            if net is not None:
                return net.name
    return None


def _input_net(ctx: VerificationContext, ref: str) -> str | None:
    spec = ctx.spec_of(ref)
    if spec is None:
        return None
    for pin in spec.pins:
        if (
            pin.has_role(PinRole.POWER)
            and pin.electrical_type is PinElectricalType.POWER_IN
        ):
            net = ctx.circuit.net_of(ref, pin.number)
            if net is not None:
                return net.name
    return None


@rule(
    "PB-REG-001",
    "Regulator input voltage is in range and leaves dropout headroom",
    RuleCategory.ELECTRICAL,
    "An LDO below its dropout does not regulate; it just follows its input down.",
)
def regulator_input_and_dropout(ctx: VerificationContext, out: ResultBuilder) -> None:
    regulators = ctx.instances_of_category(*REGULATOR_CATEGORIES)
    if not regulators:
        out.not_applicable("circuit has no regulators")
        return

    for instance in regulators:
        spec = ctx.spec_of(instance.ref)
        assert spec is not None
        reg = spec.regulator
        if reg is None:
            out.missing(f"{instance.ref}: catalog has no regulator characteristics")
            continue

        in_net = _input_net(ctx, instance.ref)
        if in_net is None:
            out.missing(f"{instance.ref}: input pin is not connected")
            continue

        vin = ctx.net_voltage(in_net)
        out.examined(f"{instance.ref} input on {in_net}")
        if not vin.is_known:
            out.missing(f"{instance.ref}: input net {in_net!r} has no identifiable driver")
            continue

        vin_low = vin.worst_case_low
        vin_high = vin.worst_case_high
        assert vin_low is not None and vin_high is not None

        if not reg.input_voltage.contains(vin_high) or not reg.input_voltage.contains(vin_low):
            out.finding(
                severity=Severity.ERROR,
                title=f"{instance.ref} input voltage is outside its specified range",
                description=(
                    f"Net {in_net!r} is {vin.voltage}, and {spec.display_name} specifies an "
                    f"input range of {reg.input_voltage}."
                ),
                components=[instance.ref],
                nets=[in_net],
                evidence=[*vin.evidence, *reg.evidence],
                lesson_topic="regulator-selection",
            )
            continue

        vout = reg.output_voltage.worst_case_high or reg.output_voltage.nominal
        if reg.dropout_at_max_current is None or vout is None:
            out.missing(f"{instance.ref}: no dropout voltage recorded, headroom not checked")
            continue

        headroom = Quantity(value=vin_low.value - vout.value, unit=Unit.VOLT)
        detail = (
            f"Vin(min) {vin_low.engineering()} - Vout(max) {vout.engineering()} "
            f"= {headroom.engineering()}; dropout at full load is "
            f"{reg.dropout_at_max_current.engineering()}"
        )
        evidence = [
            calculated_evidence(
                f"{instance.ref} dropout headroom", detail=detail, quantity=headroom
            ),
            *reg.evidence,
        ]

        if headroom < reg.dropout_at_max_current:
            out.finding(
                severity=Severity.ERROR,
                title=f"{instance.ref} does not have enough dropout headroom",
                description=(
                    f"At the low end of its input tolerance the regulator has only "
                    f"{headroom.engineering()} across it, but it needs "
                    f"{reg.dropout_at_max_current.engineering()} to regulate at full load. "
                    "Below dropout the output simply follows the input down, so the rail "
                    "sags exactly when the load is heaviest. " + detail
                ),
                components=[instance.ref],
                nets=[in_net],
                evidence=evidence,
                lesson_topic="ldo-dropout",
            )
        else:
            out.note(f"{instance.ref}: {detail}")


@rule(
    "PB-REG-002",
    "Regulator can supply the load on its output",
    RuleCategory.ELECTRICAL,
    "Sums only published figures, and says so when parts publish nothing.",
)
def regulator_current_capacity(ctx: VerificationContext, out: ResultBuilder) -> None:
    regulators = ctx.instances_of_category(*REGULATOR_CATEGORIES)
    if not regulators:
        out.not_applicable("circuit has no regulators")
        return

    for instance in regulators:
        spec = ctx.spec_of(instance.ref)
        assert spec is not None
        reg = spec.regulator
        if reg is None:
            out.missing(f"{instance.ref}: catalog has no regulator characteristics")
            continue

        out_net = _output_net(ctx, instance.ref)
        if out_net is None:
            out.missing(f"{instance.ref}: output pin is not connected")
            continue

        out.examined(f"{instance.ref} output on {out_net}")
        known, contributors, unknown = ctx.total_known_load(out_net)
        capacity = reg.output_current_max

        evidence = [
            ctx.load_evidence(out_net, contributors, known) if contributors else
            calculated_evidence(
                f"Total known current draw on {out_net}",
                detail="no part on this rail publishes a current figure",
                quantity=known,
            ),
            *reg.evidence,
        ]

        if known > capacity:
            out.finding(
                severity=Severity.ERROR,
                title=f"{instance.ref} cannot supply the load on {out_net}",
                description=(
                    f"Parts on {out_net!r} draw at least {known.engineering()}, but "
                    f"{spec.display_name} is rated for {capacity.engineering()}. "
                    + ("Unknown loads would only add to this. " if unknown else "")
                    + "Contributors: "
                    + "; ".join(contributors)
                    + ". An overloaded LDO drops out, goes into thermal shutdown, or both, "
                    "and the symptom is a board that browns out only under load."
                ),
                components=[instance.ref, *sorted({c.split()[0] for c in contributors})],
                nets=[out_net],
                evidence=evidence,
                auto_fixable=True,
                suggested_fix=(
                    f"Choose a regulator rated above {known.engineering()}, with margin."
                ),
                lesson_topic="regulator-sizing",
            )
            continue

        if unknown:
            out.missing(
                f"{instance.ref}: current draw is not recorded for "
                + ", ".join(sorted(unknown))
                + f"; known load is {known.engineering()} against a "
                f"{capacity.engineering()} rating"
            )
            continue

        headroom_fraction = (capacity.value - known.value) / capacity.value
        out.note(
            f"{instance.ref}: known load {known.engineering()} of {capacity.engineering()} "
            f"({headroom_fraction:.0%} headroom)"
        )
        if headroom_fraction < MIN_HEADROOM:
            out.finding(
                severity=Severity.WARNING,
                title=f"{instance.ref} has little current headroom",
                description=(
                    f"The load on {out_net!r} is {known.engineering()} against a "
                    f"{capacity.engineering()} rating, leaving {headroom_fraction:.0%} margin. "
                    "That is inside the rating but leaves nothing for tolerance, temperature "
                    "or a part added later."
                ),
                components=[instance.ref],
                nets=[out_net],
                evidence=evidence,
                lesson_topic="regulator-sizing",
            )

    out.limitation(
        "Load is summed from published maxima, which are worst-case figures that rarely occur "
        "simultaneously. This is deliberately conservative and is not a thermal analysis: "
        "package power dissipation and rise above ambient are NOT_VERIFIED."
    )
