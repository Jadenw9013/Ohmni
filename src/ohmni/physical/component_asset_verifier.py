"""Pure checks of measured asset geometry against verified source constraints.

Two inputs, and neither of them is the generator: the measurements come from
parsing the bytes that were actually written, and the requirements come from the
:class:`~ohmni.domain.component_synthesis.VerifiedConstraintSet` that
deterministic source checking produced. If those two disagree, the asset fails.

That ordering is the whole point of COMPONENT_SYNTHESIS_PLAN.md section 6.
Comparing a footprint against the model's own JSON would prove the footprint
matches the JSON. These checks compare it against dimensions that were relocated
in the document, bound to their row, symbol, column and units, and cross-checked
against the arithmetic the drawing prints about itself.

What a pass here means is stated in every finding: *datasheet and land-pattern
geometric conformance within the implemented subset*. Not IPC-7351 or IPC-7352
compliance, not solderability, not thermal adequacy, not a working board.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from ..domain.component_synthesis import DimensionKind, VerifiedConstraintSet
from .asset_measurements import MeasuredFootprint, MeasuredSymbol
from .land_patterns import COURTYARD_MARGIN_NM, LandPatternDefinition, SymbolDefinition

#: Bump when a check changes. Findings carry it.
CHECKER_VERSION = "1.0.0"

#: Numerical slack, in nanometres. The emitted format carries exact nanometres
#: and the parser refuses anything finer, so this is the quantisation tolerance
#: of the grid itself. It is NOT a manufacturing tolerance and is never added to
#: one.
GRID_TOLERANCE_NM = 1

#: Minimum copper-to-copper separation the geometry checks require between two
#: lands, in nanometres. It is a geometric sanity bound, not a fabrication rule:
#: the manufacturing profile owns the real clearance requirement.
MIN_LAND_SEPARATION_NM = 100_000

LIMITATIONS = (
    "Datasheet and land-pattern geometric conformance within the implemented subset only.",
    "IPC-7351 and IPC-7352 compliance are NOT established by these checks.",
    ("Solder joint reliability, paste volume, stencil design, thermal performance and "
     "bench operation are NOT established."),
    "Pin electrical types are 'unspecified'; no electrical behaviour is established.",
)


class AssetCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass(frozen=True)
class AssetFinding:
    check_id: str
    status: AssetCheckStatus
    description: str
    measured: str | None = None
    expected: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is AssetCheckStatus.PASS


@dataclass(frozen=True)
class AssetVerificationReport:
    findings: tuple[AssetFinding, ...]
    checker_version: str = CHECKER_VERSION
    limitations: tuple[str, ...] = LIMITATIONS

    @property
    def passed(self) -> bool:
        """An empty report is never a pass; neither is one with any non-pass."""
        return bool(self.findings) and all(finding.ok for finding in self.findings)

    def failures(self) -> tuple[AssetFinding, ...]:
        return tuple(finding for finding in self.findings if not finding.ok)


def _finding(
    check_id: str, ok: bool, description: str, *, measured=None, expected=None
) -> AssetFinding:
    return AssetFinding(
        check_id=check_id,
        status=AssetCheckStatus.PASS if ok else AssetCheckStatus.FAIL,
        description=description,
        measured=None if measured is None else str(measured),
        expected=None if expected is None else str(expected),
    )


def verify_assets(
    verified: VerifiedConstraintSet,
    footprint: MeasuredFootprint,
    symbol: MeasuredSymbol,
    *,
    land_pattern: LandPatternDefinition,
    symbol_definition: SymbolDefinition,
    footprint_digest: str,
    symbol_digest: str,
    recorded_footprint_digest: str,
    recorded_symbol_digest: str,
) -> AssetVerificationReport:
    """Run every implemented CS-* asset check over the measured bytes."""
    findings: list[AssetFinding] = []
    findings.extend(_source(verified))
    findings.extend(_pin(verified, footprint, symbol))
    findings.extend(_dimension(verified, footprint))
    findings.extend(_orientation(verified, footprint, symbol))
    findings.extend(_geometry(footprint, land_pattern))
    findings.extend(_lineage(
        verified, footprint, symbol, land_pattern, symbol_definition,
        footprint_digest, symbol_digest, recorded_footprint_digest, recorded_symbol_digest,
    ))
    return AssetVerificationReport(findings=tuple(findings))


def _source(verified: VerifiedConstraintSet) -> list[AssetFinding]:
    """CS-SOURCE: every verified value still matches the receipt attached to it.

    The binding is recomputed here rather than inherited. A checker that trusts
    the object it was handed is trusting whoever built it, and the object can
    reach this point through serialisation -- which is how a 1.10 mm pad length
    became 0.60 mm with every original receipt still reading "supported".
    """
    broken = verified.revalidate()
    findings = [_finding(
        "CS-SOURCE-000", not broken,
        "every accepted value still hashes to the claim its receipt recorded",
        measured=broken[0] if broken else "all bindings hold",
        expected="all bindings hold",
    )]
    unsupported = [receipt.receipt_id for receipt in verified.receipts if not receipt.supported]
    findings.append(_finding(
        "CS-SOURCE-001", not unsupported,
        "every receipt backing the verified constraints is supported",
        measured=f"{len(verified.receipts)} receipts, {len(unsupported)} unsupported",
        expected="0 unsupported",
    ))
    required = {
        DimensionKind.LAND_PAD_WIDTH, DimensionKind.LAND_PAD_LENGTH,
        DimensionKind.LAND_CONTACT_PITCH, DimensionKind.LAND_ROW_SPACING,
    }
    missing = sorted(kind.value for kind in required if verified.dimension(kind) is None)
    findings.append(_finding(
        "CS-SOURCE-002", not missing,
        "the required recommended-land dimensions are all present",
        measured=", ".join(missing) or "none missing", expected="none missing",
    ))
    relations = [
        receipt for receipt in verified.receipts
        if receipt.checker == "CS-SOURCE-CONSISTENCY"
    ]
    findings.append(_finding(
        "CS-SOURCE-003", len(relations) >= 1 and all(item.supported for item in relations),
        "the printed dimensions agree with the arithmetic the drawing states about itself",
        measured=f"{len(relations)} relation(s) checked",
        expected="at least one, all supported",
    ))
    return findings


def _pin(
    verified: VerifiedConstraintSet, footprint: MeasuredFootprint, symbol: MeasuredSymbol
) -> list[AssetFinding]:
    """CS-PIN: complete, exact mapping between terminals, lands and symbol pins."""
    expected = {terminal.pin_number for terminal in verified.terminals}
    pads = {pad.number for pad in footprint.pads}
    pins = {pin.number for pin in symbol.pins}
    findings = [
        _finding("CS-PIN-001", pads == expected,
                 "every verified terminal has exactly one land and no land is invented",
                 measured=sorted(pads), expected=sorted(expected)),
        _finding("CS-PIN-002", pins == expected,
                 "every verified terminal has exactly one symbol pin",
                 measured=sorted(pins), expected=sorted(expected)),
    ]
    names_ok = True
    detail = []
    for terminal in verified.terminals:
        pin = symbol.pin(terminal.pin_number)
        if pin is None or pin.name != terminal.symbol:
            names_ok = False
            detail.append(f"{terminal.pin_number}:{pin.name if pin else 'absent'}")
    findings.append(_finding(
        "CS-PIN-003", names_ok, "symbol pin names match the source-checked pin symbols",
        measured=", ".join(detail) or "all match",
        expected=", ".join(f"{t.pin_number}:{t.symbol}" for t in verified.terminals),
    ))
    unspecified = [pin.number for pin in symbol.pins if pin.electrical_type != "unspecified"]
    findings.append(_finding(
        "CS-PIN-004", not unspecified,
        "no pin claims an electrical type the source checks did not establish",
        measured=", ".join(unspecified) or "all unspecified", expected="all unspecified",
    ))
    return findings


def _dimension(
    verified: VerifiedConstraintSet, footprint: MeasuredFootprint
) -> list[AssetFinding]:
    """CS-DIMENSION: measured copper satisfies the verified table, independently."""
    width = verified.require(DimensionKind.LAND_PAD_WIDTH).value.nanometres
    length = verified.require(DimensionKind.LAND_PAD_LENGTH).value.nanometres
    pitch = verified.require(DimensionKind.LAND_CONTACT_PITCH).value.nanometres
    spacing = verified.require(DimensionKind.LAND_ROW_SPACING).value.nanometres

    wrong_size = [
        pad.number for pad in footprint.pads
        if abs(pad.width_nm - width) > GRID_TOLERANCE_NM
        or abs(pad.height_nm - length) > GRID_TOLERANCE_NM
    ]
    findings = [_finding(
        "CS-DIMENSION-001", not wrong_size,
        "every land measures the verified contact pad width and length",
        measured=f"off-size lands: {wrong_size or 'none'}",
        expected=f"{width} x {length} nm",
    )]

    rows: dict[int, list] = {}
    for pad in footprint.pads:
        rows.setdefault(pad.centre_y_nm, []).append(pad)
    findings.append(_finding(
        "CS-DIMENSION-002", len(rows) == 2,
        "the lands form exactly two rows",
        measured=f"{len(rows)} row(s)", expected="2 rows",
    ))
    if len(rows) == 2:
        first, second = sorted(rows)
        measured_spacing = second - first
        findings.append(_finding(
            "CS-DIMENSION-003", abs(measured_spacing - spacing) <= GRID_TOLERANCE_NM,
            "measured row centre separation equals the verified contact pad spacing",
            measured=f"{measured_spacing} nm", expected=f"{spacing} nm",
        ))
    # Adjacent centre separation is compared pair by pair, not as a row span:
    # a row whose span happens to be right can still have one land misplaced.
    bad_pitch: list[str] = []
    for centre in sorted(rows):
        ordered = sorted(rows[centre], key=lambda pad: pad.centre_x_nm)
        for left, right in pairwise(ordered):
            gap = right.centre_x_nm - left.centre_x_nm
            if gap % pitch or abs(gap - pitch * round(gap / pitch)) > GRID_TOLERANCE_NM:
                bad_pitch.append(f"{left.number}->{right.number}={gap}")
    findings.append(_finding(
        "CS-DIMENSION-004", not bad_pitch,
        "every adjacent land separation is a whole multiple of the verified contact pitch",
        measured=", ".join(bad_pitch) or "all on pitch", expected=f"multiple of {pitch} nm",
    ))
    overall = verified.dimension(DimensionKind.LAND_OVERALL_WIDTH)
    if overall is not None:
        measured = (max(pad.y1_nm for pad in footprint.pads)
                    - min(pad.y0_nm for pad in footprint.pads))
        findings.append(_finding(
            "CS-DIMENSION-005",
            abs(measured - overall.value.nanometres) <= GRID_TOLERANCE_NM,
            "measured land extent across the rows equals the verified overall width",
            measured=f"{measured} nm", expected=f"{overall.value.nanometres} nm",
        ))
    gap = verified.dimension(DimensionKind.LAND_ADJACENT_GAP)
    if gap is not None and len(rows) == 2:
        # Only lands exactly one pitch apart are adjacent. Two lands separated by
        # an empty pitch-grid column -- as in a five-land SOT-23, whose short row
        # skips the middle slot -- are two pitches apart and the printed
        # distance-between-pads figure does not describe them.
        edges: list[int] = []
        for centre in sorted(rows):
            ordered = sorted(rows[centre], key=lambda pad: pad.centre_x_nm)
            for left, right in pairwise(ordered):
                if abs((right.centre_x_nm - left.centre_x_nm) - pitch) <= GRID_TOLERANCE_NM:
                    edges.append(right.x0_nm - left.x1_nm)
        ok = bool(edges) and all(
            abs(edge - gap.value.nanometres) <= GRID_TOLERANCE_NM for edge in edges
        )
        findings.append(_finding(
            "CS-DIMENSION-006", ok,
            "measured edge gap between lands one pitch apart equals the verified "
            "distance between pads",
            measured=f"{sorted(set(edges))} nm over {len(edges)} pair(s)",
            expected=f"{gap.value.nanometres} nm",
        ))
    row_gap = verified.dimension(DimensionKind.LAND_ROW_GAP)
    if row_gap is not None and len(rows) == 2:
        first, second = sorted(rows)
        measured = (min(pad.y0_nm for pad in rows[second])
                    - max(pad.y1_nm for pad in rows[first]))
        findings.append(_finding(
            "CS-DIMENSION-007",
            abs(measured - row_gap.value.nanometres) <= GRID_TOLERANCE_NM,
            "measured copper gap between the two land rows equals the verified "
            "distance between pads",
            measured=f"{measured} nm", expected=f"{row_gap.value.nanometres} nm",
        ))
    return findings


def _orientation(
    verified: VerifiedConstraintSet, footprint: MeasuredFootprint, symbol: MeasuredSymbol
) -> list[AssetFinding]:
    """CS-ORIENTATION: numbering runs the way the drawing's labels say it does.

    A mirrored sequence has identical pitch, identical pad sizes and an identical
    row span, so a pitch-only test passes it. These checks compare the emitted
    row and column of every pin against the verified slots.
    """
    ordering = verified.pad_ordering
    rows = sorted({pad.centre_y_nm for pad in footprint.pads})
    findings = [_finding(
        "CS-ORIENTATION-001", len(rows) == ordering.row_count,
        "the emitted land rows match the verified pad ordering",
        measured=len(rows), expected=ordering.row_count,
    )]
    if len(rows) != ordering.row_count:
        return findings
    columns = sorted({pad.centre_x_nm for pad in footprint.pads})
    findings.append(_finding(
        "CS-ORIENTATION-002", len(columns) == ordering.column_count,
        "the emitted pitch-grid columns match the verified pad ordering",
        measured=len(columns), expected=ordering.column_count,
    ))
    if len(columns) != ordering.column_count:
        return findings
    # Verified row 0 is the row carrying the printed pin-1 label, not the row
    # with the smaller coordinate: which way the emitter points +Y is a format
    # convention, and this check is about numbering, not about that convention.
    pin_one = footprint.pad("1")
    misplaced = []
    if pin_one is None:
        misplaced.append("1:absent")
    else:
        pin_one_row = rows.index(pin_one.centre_y_nm)
        for slot in ordering.slots:
            pad = footprint.pad(slot.pin_number)
            if pad is None:
                misplaced.append(f"{slot.pin_number}:absent")
                continue
            measured_row = 0 if rows.index(pad.centre_y_nm) == pin_one_row else 1
            measured_column = columns.index(pad.centre_x_nm)
            if (measured_row, measured_column) != (slot.row, slot.column):
                misplaced.append(
                    f"{slot.pin_number}:({measured_row},{measured_column})"
                    f"!=({slot.row},{slot.column})"
                )
    findings.append(_finding(
        "CS-ORIENTATION-003", not misplaced,
        "every land sits in the row and pitch-grid column the source-checked ordering requires",
        measured=", ".join(misplaced) or "all in place",
        expected="every pin in its verified slot",
    ))
    pin_one = footprint.pad("1")
    markers = [
        graphic for graphic in footprint.layer_graphics("F.SilkS")
        if graphic.primitive == "fp_circle"
    ]
    findings.append(_finding(
        "CS-ORIENTATION-004",
        len(markers) == 1 and pin_one is not None
        and markers[0].points_nm[0][0] < pin_one.x0_nm,
        "exactly one pin-1 marker is drawn, outside pin 1 rather than over any land",
        measured=f"{len(markers)} marker(s)", expected="1 marker beside pin 1",
    ))
    left_pins = {
        pin.number for pin in symbol.pins if pin.orientation_deg == 0
    }
    expected_left = set(ordering.row_occupancy()[0])
    findings.append(_finding(
        "CS-ORIENTATION-005", left_pins == expected_left,
        "the symbol places the pin-1 land row on one side, matching the verified ordering",
        measured=sorted(left_pins), expected=sorted(expected_left),
    ))
    # A mirrored footprint has identical pitch, identical land sizes, an
    # identical row span and identical row/column membership. What it does not
    # have is the same handedness, so the signed area of the numbering polygon
    # is the check that catches it. KiCad footprint Y grows downward, so a
    # counter-clockwise top-view sequence has a negative signed area here.
    signed = 0
    ordered_pads = [footprint.pad(slot.pin_number) for slot in
                    sorted(ordering.slots, key=lambda item: int(item.pin_number))]
    if all(pad is not None for pad in ordered_pads) and len(ordered_pads) >= 3:
        for current, following in zip(ordered_pads, ordered_pads[1:] + ordered_pads[:1],
                                      strict=False):
            signed += (current.centre_x_nm * following.centre_y_nm
                       - following.centre_x_nm * current.centre_y_nm)
    expected_sign = -1 if ordering.traversal == "counter_clockwise_from_pin_1" else 1
    findings.append(_finding(
        "CS-ORIENTATION-006",
        signed != 0 and (signed < 0) == (expected_sign < 0),
        "the emitted numbering runs the way the source-checked traversal says, "
        "so a mirrored footprint cannot pass a pitch-only test",
        measured=f"signed area {signed}", expected=f"sign {expected_sign}",
    ))
    return findings


def _geometry(
    footprint: MeasuredFootprint, land_pattern: LandPatternDefinition
) -> list[AssetFinding]:
    """CS-GEOMETRY: lands do not touch, artwork stays off copper, bounds are sane."""
    findings: list[AssetFinding] = []
    overlaps: list[str] = []
    separations: list[str] = []
    pads = sorted(footprint.pads, key=lambda pad: (pad.centre_y_nm, pad.centre_x_nm))
    for index, left in enumerate(pads):
        for right in pads[index + 1:]:
            dx = max(left.x0_nm, right.x0_nm) - min(left.x1_nm, right.x1_nm)
            dy = max(left.y0_nm, right.y0_nm) - min(left.y1_nm, right.y1_nm)
            if dx < 0 and dy < 0:
                overlaps.append(f"{left.number}/{right.number}")
            elif max(dx, dy) < MIN_LAND_SEPARATION_NM:
                separations.append(f"{left.number}/{right.number}={max(dx, dy)}")
    findings.append(_finding(
        "CS-GEOMETRY-001", not overlaps, "no two lands overlap",
        measured=", ".join(overlaps) or "none", expected="none",
    ))
    findings.append(_finding(
        "CS-GEOMETRY-002", not separations,
        "every land pair is separated by at least the geometric sanity bound",
        measured=", ".join(separations) or "all separated",
        expected=f">= {MIN_LAND_SEPARATION_NM} nm",
    ))
    courtyards = footprint.layer_graphics("F.CrtYd")
    ok = len(courtyards) == 1 and courtyards[0].primitive == "fp_rect"
    if ok:
        (x0, y0), (x1, y1) = courtyards[0].points_nm[:2]
        contains = all(
            x0 <= pad.x0_nm and pad.x1_nm <= x1 and y0 <= pad.y0_nm and pad.y1_nm <= y1
            for pad in footprint.pads
        )
        margin_ok = (
            min(pad.x0_nm for pad in footprint.pads) - x0 >= COURTYARD_MARGIN_NM
            and y1 - max(pad.y1_nm for pad in footprint.pads) >= COURTYARD_MARGIN_NM
        )
        ok = contains and margin_ok
    findings.append(_finding(
        "CS-GEOMETRY-003", ok,
        "exactly one courtyard rectangle contains every land with the declared policy margin",
        measured=f"{len(courtyards)} courtyard graphic(s)",
        expected=f"1 rectangle, margin >= {COURTYARD_MARGIN_NM} nm",
    ))
    silk = footprint.layer_graphics("F.SilkS")
    on_copper: list[str] = []
    for graphic in silk:
        for x, y in graphic.points_nm:
            for pad in footprint.pads:
                if pad.x0_nm <= x <= pad.x1_nm and pad.y0_nm <= y <= pad.y1_nm:
                    on_copper.append(f"{graphic.primitive}@{pad.number}")
    findings.append(_finding(
        "CS-GEOMETRY-004", not on_copper,
        "no silkscreen artwork is drawn over a solderable land",
        measured=", ".join(on_copper) or "clear of copper", expected="clear of copper",
    ))
    layers_ok = all(
        set(pad.layers) == {"F.Cu", "F.Mask", "F.Paste"} for pad in footprint.pads
    )
    findings.append(_finding(
        "CS-GEOMETRY-005", layers_ok,
        "every land carries copper, mask and paste openings explicitly",
        measured=sorted({tuple(pad.layers) for pad in footprint.pads}),
        expected="F.Cu, F.Mask, F.Paste",
    ))
    copper_graphics = [
        f"{item.primitive}@{item.layer}"
        for item in footprint.graphics
        if item.layer.endswith(".Cu") or item.layer == "*.Cu"
    ]
    findings.append(_finding(
        "CS-GEOMETRY-007", not copper_graphics,
        "no copper is drawn outside the lands themselves",
        measured=", ".join(copper_graphics) or "none", expected="none",
    ))
    rotated = [
        pad.number for pad in footprint.pads if pad.rotation_deg % 360 != 0
    ]
    findings.append(_finding(
        "CS-GEOMETRY-008", not rotated,
        "every land is axis-aligned, so the measured envelopes are the real ones",
        measured=", ".join(rotated) or "all unrotated", expected="all unrotated",
    ))
    stated = set(land_pattern.limitations)
    findings.append(_finding(
        "CS-GEOMETRY-006",
        any("IPC" in item for item in stated) and any("body" in item for item in stated),
        "the artifact states that IPC compliance and a package body are not established",
        measured=f"{len(stated)} limitation(s)", expected="IPC and body limitations present",
    ))
    return findings


def _lineage(
    verified: VerifiedConstraintSet,
    footprint: MeasuredFootprint,
    symbol: MeasuredSymbol,
    land_pattern: LandPatternDefinition,
    symbol_definition: SymbolDefinition,
    footprint_digest: str,
    symbol_digest: str,
    recorded_footprint_digest: str,
    recorded_symbol_digest: str,
) -> list[AssetFinding]:
    """CS-LINEAGE: these exact bytes came from these exact constraints."""
    constraint_hash = verified.content_hash
    return [
        _finding(
            "CS-LINEAGE-001", footprint_digest == recorded_footprint_digest,
            "the measured footprint bytes are the bytes the manifest records",
            measured=footprint_digest[:16], expected=recorded_footprint_digest[:16],
        ),
        _finding(
            "CS-LINEAGE-002", symbol_digest == recorded_symbol_digest,
            "the measured symbol bytes are the bytes the manifest records",
            measured=symbol_digest[:16], expected=recorded_symbol_digest[:16],
        ),
        _finding(
            "CS-LINEAGE-003",
            footprint.properties.get("ohmni_constraint_hash") == constraint_hash,
            "the footprint names the verified constraint set it was built from",
            measured=str(footprint.properties.get("ohmni_constraint_hash"))[:16],
            expected=constraint_hash[:16],
        ),
        _finding(
            "CS-LINEAGE-004",
            symbol.properties.get("ohmni_constraint_hash") == constraint_hash,
            "the symbol names the verified constraint set it was built from",
            measured=str(symbol.properties.get("ohmni_constraint_hash"))[:16],
            expected=constraint_hash[:16],
        ),
        _finding(
            "CS-LINEAGE-005",
            land_pattern.constraint_hash == constraint_hash
            and symbol_definition.constraint_hash == constraint_hash,
            "the land pattern and symbol definitions share one constraint set",
            measured=f"{land_pattern.constraint_hash[:16]}/"
                     f"{symbol_definition.constraint_hash[:16]}",
            expected=constraint_hash[:16],
        ),
        _finding(
            "CS-LINEAGE-006",
            footprint.name == land_pattern.name and symbol.name == symbol_definition.name,
            "the emitted asset names match the definitions they were built from",
            measured=f"{footprint.name}/{symbol.name}",
            expected=f"{land_pattern.name}/{symbol_definition.name}",
        ),
        _finding(
            "CS-LINEAGE-007",
            footprint.properties.get("ohmni_land_pattern_method") == land_pattern.method.value,
            "the footprint names the land-pattern method that produced it",
            measured=str(footprint.properties.get("ohmni_land_pattern_method")),
            expected=land_pattern.method.value,
        ),
    ]


__all__ = [
    "CHECKER_VERSION",
    "GRID_TOLERANCE_NM",
    "LIMITATIONS",
    "MIN_LAND_SEPARATION_NM",
    "AssetCheckStatus",
    "AssetFinding",
    "AssetVerificationReport",
    "verify_assets",
]
