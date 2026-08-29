"""Layer 1: identity. Does every part and pin in this design actually exist?

These run first because every later rule depends on them. A voltage rule that
silently skips an unresolvable part reports a pass it did not earn.
"""

from __future__ import annotations

from ...domain.component import PASSIVE_CATEGORIES, ComponentCategory
from ...domain.evidence import assumed_evidence
from ...domain.verification import RuleCategory, Severity
from ..context import VerificationContext
from ..registry import ResultBuilder, rule

_VALUE_UNIT_BY_CATEGORY = {
    ComponentCategory.RESISTOR: "ohm",
    ComponentCategory.CAPACITOR: "F",
    ComponentCategory.INDUCTOR: "H",
}


@rule(
    "PB-ID-001",
    "Every part resolves to a catalog entry",
    RuleCategory.IDENTITY,
    "A component referencing an unknown part cannot be verified at all.",
)
def parts_resolve(ctx: VerificationContext, out: ResultBuilder) -> None:
    for component in ctx.circuit.components:
        out.examined(f"{component.ref} -> {component.part_id}")

    for ref, part_id in sorted(ctx.unresolved_parts.items()):
        out.finding(
            severity=Severity.CRITICAL,
            title=f"{ref} references an unknown part",
            description=(
                f"{ref} is declared as part {part_id!r}, which is not in the catalog. "
                "Nothing about this component can be checked: not its pinout, not its "
                "voltage limits, not its current draw. Every other rule will skip it."
            ),
            components=[ref],
            suggested_fix=(
                f"Add {part_id!r} to the catalog with datasheet-backed facts, or replace it "
                "with a part that is already known."
            ),
            lesson_topic="component-identity",
        )

    for component in ctx.circuit.components:
        if component.placeholder:
            out.finding(
                severity=Severity.WARNING,
                title=f"{component.ref} is still a placeholder",
                description=(
                    f"{component.ref} has not been resolved to a real, orderable part. "
                    "The design cannot be built or costed until it is."
                ),
                components=[component.ref],
                lesson_topic="component-identity",
            )


@rule(
    "PB-ID-002",
    "Every connection names a pin the part actually has",
    RuleCategory.IDENTITY,
    "Catches invented pin numbers, the classic hallucination in generated netlists.",
)
def pins_exist(ctx: VerificationContext, out: ResultBuilder) -> None:
    for net in ctx.circuit.nets:
        for pin_ref in net.connections:
            spec = ctx.spec_of(pin_ref.component)
            if spec is None:
                # PB-ID-001 already reported this; do not double-count it.
                continue
            out.examined(f"{pin_ref} on {net.name}")
            if spec.pin(pin_ref.pin) is None:
                available = ", ".join(p.number for p in spec.pins[:12])
                out.finding(
                    severity=Severity.CRITICAL,
                    title=f"{pin_ref} does not exist on {spec.display_name}",
                    description=(
                        f"Net {net.name!r} connects to pin {pin_ref.pin!r} of "
                        f"{pin_ref.component} ({spec.display_name}), but that part has no such "
                        f"pin. Known pins include: {available}"
                        f"{'...' if len(spec.pins) > 12 else ''}."
                    ),
                    components=[pin_ref.component],
                    nets=[net.name],
                    lesson_topic="component-identity",
                )


@rule(
    "PB-ID-003",
    "Chosen package is one the part is offered in",
    RuleCategory.IDENTITY,
    "Package suffixes change footprints and sometimes electrical characteristics.",
)
def package_consistency(ctx: VerificationContext, out: ResultBuilder) -> None:
    checked = 0
    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None:
            continue
        if component.package is None:
            out.missing(f"{component.ref} does not state a package")
            continue
        checked += 1
        out.examined(f"{component.ref} package {component.package}")
        option = spec.package(component.package)
        if option is None:
            offered = ", ".join(p.name for p in spec.packages) or "none recorded"
            out.finding(
                severity=Severity.ERROR,
                title=f"{component.ref} asks for a package {spec.display_name} is not made in",
                description=(
                    f"{component.ref} specifies package {component.package!r}, but "
                    f"{spec.display_name} is offered in: {offered}. A footprint that does not "
                    "match the real package produces a board the part cannot be soldered to."
                ),
                components=[component.ref],
                auto_fixable=bool(spec.packages),
                suggested_fix=(
                    f"Use one of: {offered}." if spec.packages else "Record the part's packages."
                ),
                lesson_topic="packages-and-footprints",
            )
            continue
        if option.pin_count is not None and option.pin_count != len(spec.pins):
            out.finding(
                severity=Severity.WARNING,
                title=f"{spec.display_name} pin count disagrees with its {option.name} package",
                description=(
                    f"The catalog records {len(spec.pins)} pins for {spec.display_name} but the "
                    f"{option.name} package declares {option.pin_count}. One of the two is wrong, "
                    "and a footprint generated from either could be incorrect."
                ),
                components=[component.ref],
                lesson_topic="packages-and-footprints",
            )

    if checked == 0 and not ctx.circuit.components:
        out.not_applicable("circuit has no components")


@rule(
    "PB-ID-004",
    "Passive components carry a value in the right unit",
    RuleCategory.IDENTITY,
    "A resistor with no resistance cannot be checked, costed or bought.",
)
def passive_values(ctx: VerificationContext, out: ResultBuilder) -> None:
    passives = ctx.instances_of_category(*PASSIVE_CATEGORIES)
    if not passives:
        out.not_applicable("circuit has no passive components")
        return

    for component in passives:
        spec = ctx.spec_of(component.ref)
        assert spec is not None
        expected = _VALUE_UNIT_BY_CATEGORY.get(spec.category)
        out.examined(f"{component.ref} value")
        if component.value is None:
            out.finding(
                severity=Severity.ERROR,
                title=f"{component.ref} has no value",
                description=(
                    f"{component.ref} is a {spec.category.value} with no value set. Current "
                    "limiting, pull-up strength and decoupling all depend on it, so those "
                    "checks cannot run against this part."
                ),
                components=[component.ref],
                lesson_topic="passive-values",
            )
        elif expected is not None and component.value.unit.value != expected:
            out.finding(
                severity=Severity.ERROR,
                title=f"{component.ref} value is in the wrong unit",
                description=(
                    f"{component.ref} is a {spec.category.value} but its value is "
                    f"{component.value.engineering()}, which is not a "
                    f"{expected} quantity."
                ),
                components=[component.ref],
                lesson_topic="passive-values",
            )


@rule(
    "PB-ID-005",
    "Packages match the user's hand-soldering requirement",
    RuleCategory.IDENTITY,
    "A hobbyist with an iron cannot assemble a bottom-terminated package.",
)
def hand_solderable(ctx: VerificationContext, out: ResultBuilder) -> None:
    if ctx.requirements is None:
        out.not_applicable("no requirements supplied")
        return
    if not ctx.requirements.hand_solderable:
        out.not_applicable("hand soldering was not requested")
        return

    for component in ctx.circuit.components:
        spec = ctx.spec_of(component.ref)
        if spec is None or component.package is None:
            continue
        option = spec.package(component.package)
        if option is None:
            continue
        out.examined(f"{component.ref} {option.name}")
        if not option.hand_solderable:
            out.finding(
                severity=Severity.WARNING,
                title=f"{component.ref} in {option.name} is not hand-solderable",
                description=(
                    f"The project asks for hand-solderable parts, but {component.ref} "
                    f"({spec.display_name}) is in a {option.name} package. "
                    f"{option.notes or 'This package needs hot air or reflow.'} "
                    "The design is electrically fine; this is an assembly constraint."
                ),
                components=[component.ref],
                evidence=[
                    assumed_evidence(
                        f"{option.name} hand-solderability",
                        detail=(
                            "Hand-solderability is recorded per package in the catalog and "
                            "reflects a typical hobbyist with a soldering iron, not a hard "
                            "manufacturing limit."
                        ),
                    )
                ],
                suggested_fix=(
                    "Use a breakout module carrying this part, or accept that assembly needs "
                    "hot air or a reflow plate."
                ),
                lesson_topic="hand-assembly",
            )
