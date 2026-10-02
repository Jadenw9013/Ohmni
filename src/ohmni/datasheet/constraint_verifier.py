"""Independent deterministic source verification for component synthesis.

This module is the only place that may decide a proposed claim is supported by
the document. It is a pure function of immutable observations: no provider, no
filesystem, no clock, no network, and it never reads a generated artifact.
``tests/test_architecture.py`` enforces that.

The rule it exists to implement is the one COMPONENT_SYNTHESIS_PLAN.md states
twice: *finding the same number elsewhere fails.* A value is supported only when
it is printed in the claimed row, under the claimed dimension symbol, in the
claimed MIN/NOM/MAX column, under the units the table declares, on a page that
is the recommended land pattern for the selected package. A pin is supported
only when it is printed in the claimed package's own column -- a number read
from the neighbouring DFN column is a different package's pin, and an em dash
means that package has no such pin at all.

Layout grammars are bounded and named. ``microchip_land_pattern_v1`` and
``microchip_pin_function_v1`` describe the two table shapes this slice supports.
A page that does not match returns ``UNSUPPORTED_SOURCE`` and quarantines the
import; it never degrades to a fuzzy text search, because a fuzzy match over a
datasheet is exactly how a number from the wrong row becomes evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from ..domain.component_synthesis import (
    CHECKER_CONTRACT_VERSION,
    LAND_DIMENSION_KINDS,
    DimensionKind,
    ExtractionProposal,
    IdentityCandidate,
    LimitColumn,
    PadOrderingCandidate,
    PadSlot,
    PhysicalConstraintCandidate,
    PinCandidate,
    ReceiptOutcome,
    SourceRegion,
    SourceUnit,
    TerminalKind,
    VerificationReceipt,
    VerifiedConstraintSet,
    VerifiedDimension,
    VerifiedIdentity,
    VerifiedPadOrdering,
    VerifiedTerminal,
    claim_hash,
    dimension_claim,
    identity_claim,
    pad_ordering_claim,
    relation_claim,
    terminal_claim,
)
from .observations import DocumentObservationBundle, PageObservation, TextToken, VectorRectangle

#: Bump this whenever a grammar or a rule changes. Receipts carry it, so old
#: receipts become visibly historical instead of silently current. It is the
#: same value the domain contract enforces, asserted here so the two cannot
#: drift apart silently: a receipt produced under other rules must not validate.
CHECKER_VERSION = CHECKER_CONTRACT_VERSION

SUPPORTED_GRAMMARS = ("microchip_land_pattern_v1", "microchip_pin_function_v1")

#: Two printed rules closer than this are the same border. Table borders in the
#: supported layouts are under 0.5 pt thick and no two distinct columns are
#: within 25 pt, so this separates a doubled rule from a real column.
RULE_MERGE_PT = 1.0
#: A band shorter than this is a sliver between doubled rules, not a row.
MIN_BAND_HEIGHT_PT = 3.0
#: Largest gap between consecutive horizontal rules still considered one table.
MAX_BAND_HEIGHT_PT = 60.0
#: Vertical tolerance for deciding two tokens share a text row.
ROW_TOLERANCE_PT = 2.5
#: How far a pad-number label may sit from its land, as a multiple of the
#: largest land dimension. Labels sit outside the pad on leader lines.
LABEL_SEARCH_FACTOR = 1.5
#: Congruence tolerance when grouping drawn lands, in PDF points.
PAD_CONGRUENCE_PT = 0.75

#: What each printed row of the supported land-pattern grammar *means*, keyed by
#: its normalised row label and dimension symbol.
#:
#: This table is the answer to the audit's first finding. Checking that a value
#: is printed in the claimed row proves the number was read correctly; it says
#: nothing about whether that row denotes the feature the proposal called it. A
#: candidate can cite the genuine "Contact Pad Width (X5) / X / 0.60" row, label
#: it ``land_pad_length``, and every value check still passes -- producing 0.60
#: by 0.60 mm lands from a document that prints 1.10 mm for the length. The
#: engineering meaning has to come from the grammar, not from the proposal.
#:
#: A row that is not in this table has no established meaning and returns
#: UNSUPPORTED_SOURCE. Adding a package family means adding its rows here, with
#: a source case, rather than trusting whatever the model called them.
LAND_ROW_MEANINGS: dict[tuple[str, str], DimensionKind] = {
    ("contact pitch", "E"): DimensionKind.LAND_CONTACT_PITCH,
    ("contact pad spacing", "C"): DimensionKind.LAND_ROW_SPACING,
    ("contact pad width", "X"): DimensionKind.LAND_PAD_WIDTH,
    ("contact pad length", "Y"): DimensionKind.LAND_PAD_LENGTH,
    ("distance between pads", "G"): DimensionKind.LAND_ROW_GAP,
    ("distance between pads", "GX"): DimensionKind.LAND_ADJACENT_GAP,
    ("overall width", "Z"): DimensionKind.LAND_OVERALL_WIDTH,
    ("overall length", "ZL"): DimensionKind.LAND_OVERALL_WIDTH,
}

#: A row label may carry a terminal-count multiplier, as in "Contact Pad Width
#: (X5)". The count is checked separately; it is not part of the row's identity.
_MULTIPLIER = re.compile(r"\s*\(x\s*(\d{1,4})\)\s*$", re.IGNORECASE)

#: What a printed pin row means, derived from its own symbol and function text.
#: Same principle: a proposal cannot relabel a real electrical row as an exposed
#: pad or a no-connect.
_NO_CONNECT_SYMBOLS = {"NC", "DNC", "N/C"}
_EXPOSED_PAD_SYMBOLS = {"EP", "PAD", "TAB"}

_UNIT_WORDS = {
    "MILLIMETERS": SourceUnit.MILLIMETRE,
    "MILLIMETRES": SourceUnit.MILLIMETRE,
    "INCHES": SourceUnit.INCH,
}
_LIMIT_WORDS = {"MIN": LimitColumn.MIN, "NOM": LimitColumn.NOM, "MAX": LimitColumn.MAX}
_DASHES = {"—", "–", "−", "-"}
_NUMBER = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")
_INTEGER = re.compile(r"^\d{1,4}$")
_LEAD_COUNT = re.compile(r"^(\d{1,4})-Lead$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Pure layout reconstruction from printed rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridCell:
    """One cell of a ruled table: the leaf columns it spans and its tokens."""

    x0: float
    x1: float
    first_column: int
    last_column: int
    tokens: tuple[TextToken, ...]

    @property
    def text(self) -> str:
        return " ".join(token.text for token in sorted(self.tokens, key=lambda t: t.region.x0))

    @property
    def single_column(self) -> bool:
        return self.first_column == self.last_column

    @property
    def region(self) -> SourceRegion | None:
        if not self.tokens:
            return None
        return SourceRegion(
            x0=min(t.region.x0 for t in self.tokens), y0=min(t.region.y0 for t in self.tokens),
            x1=max(t.region.x1 for t in self.tokens), y1=max(t.region.y1 for t in self.tokens),
        )


@dataclass(frozen=True)
class GridBand:
    """One ruled row of a table."""

    y0: float
    y1: float
    cells: tuple[GridCell, ...]

    def cell_at(self, column: int) -> GridCell | None:
        return next(
            (cell for cell in self.cells if cell.first_column <= column <= cell.last_column), None
        )

    @property
    def text(self) -> str:
        return " | ".join(cell.text for cell in self.cells)


@dataclass(frozen=True)
class TableGrid:
    """A table reconstructed from its own printed borders.

    Columns are the partition induced by every vertical rule inside the table.
    A band whose vertical rule is absent has a cell spanning several columns --
    which is exactly what a merged cell means, and is how a basic dimension
    printed across MIN/NOM/MAX is read as spanning them rather than as sitting
    in whichever one its centre happens to fall nearest.
    """

    page: int
    x_edges: tuple[float, ...]
    bands: tuple[GridBand, ...]

    @property
    def column_count(self) -> int:
        return len(self.x_edges) - 1

    @property
    def region(self) -> SourceRegion:
        return SourceRegion(
            x0=self.x_edges[0], y0=self.bands[0].y0,
            x1=self.x_edges[-1], y1=self.bands[-1].y1,
        )

    def column_named(self, name: str, *, above_band: int) -> int | None:
        """The leaf column whose own header cell holds exactly ``name``.

        Searched bottom-up through the header bands, so a sub-header wins over
        the spanning header above it.
        """
        for band in reversed(self.bands[:above_band]):
            for cell in band.cells:
                if cell.single_column and cell.text == name:
                    return cell.first_column
        return None


class UnsupportedSource(ValueError):
    """The page does not match any supported layout grammar. Never a pass."""


def build_grid(page: PageObservation, anchors: list[TextToken]) -> TableGrid:
    """Reconstruct the ruled table containing ``anchors``.

    Discovery is two-step. The *spine* is the stack of horizontal rules that run
    under the anchor, which fixes the table's extent. Any further horizontal
    rule inside that extent is then added as a band boundary, so a sub-header
    divider that covers only part of the width still splits the row it divides.
    """
    if not anchors:
        raise UnsupportedSource("no anchor token for table discovery")
    anchor_x = sum(token.x_centre for token in anchors) / len(anchors)
    anchor_y = sum(token.y_centre for token in anchors) / len(anchors)
    horizontal = sorted(
        (rule for rule in page.rules
         if rule.orientation == "horizontal" and rule.covers_position(anchor_x)),
        key=lambda rule: rule.position,
    )
    if len(horizontal) < 2:
        raise UnsupportedSource("the anchor is not inside a ruled table")
    above = [rule for rule in horizontal if rule.position <= anchor_y]
    below = [rule for rule in horizontal if rule.position > anchor_y]
    if not above or not below:
        raise UnsupportedSource("the anchor has no ruled row above and below it")
    spine = [above[-1], below[0]]
    for rule in reversed(above[:-1]):
        if spine[0].position - rule.position > MAX_BAND_HEIGHT_PT:
            break
        spine.insert(0, rule)
    for rule in below[1:]:
        if rule.position - spine[-1].position > MAX_BAND_HEIGHT_PT:
            break
        spine.append(rule)
    x_left = min(rule.start for rule in spine)
    x_right = max(rule.end for rule in spine)
    y_top, y_bottom = spine[0].position, spine[-1].position

    boundaries = {rule.position for rule in spine}
    for rule in page.rules:
        if rule.orientation != "horizontal":
            continue
        if not y_top - RULE_MERGE_PT <= rule.position <= y_bottom + RULE_MERGE_PT:
            continue
        if rule.end < x_left or rule.start > x_right:
            continue
        boundaries.add(rule.position)
    y_edges = _merge_positions(sorted(boundaries))

    verticals = [
        rule for rule in page.rules
        if rule.orientation == "vertical"
        and x_left - RULE_MERGE_PT <= rule.position <= x_right + RULE_MERGE_PT
        and rule.end > y_top and rule.start < y_bottom
    ]
    x_edges = _merge_positions(sorted({x_left, x_right, *(rule.position for rule in verticals)}))
    if len(x_edges) < 2:
        raise UnsupportedSource("the table has no printed column boundaries")

    bands: list[GridBand] = []
    for top, bottom in pairwise(y_edges):
        if bottom - top < MIN_BAND_HEIGHT_PT:
            continue
        present = [0, len(x_edges) - 1]
        for index, edge in enumerate(x_edges[1:-1], start=1):
            if any(
                abs(rule.position - edge) <= RULE_MERGE_PT
                and rule.spans(top, bottom, tolerance=RULE_MERGE_PT)
                for rule in verticals
            ):
                present.append(index)
        present = sorted(set(present))
        cells: list[GridCell] = []
        for first, last in pairwise(present):
            x0, x1 = x_edges[first], x_edges[last]
            tokens = tuple(
                token for token in page.tokens
                if top < token.y_centre < bottom and x0 <= token.x_centre <= x1
            )
            cells.append(GridCell(
                x0=x0, x1=x1, first_column=first, last_column=last - 1,
                tokens=tuple(sorted(tokens, key=lambda t: t.region.x0)),
            ))
        if any(cell.tokens for cell in cells):
            bands.append(GridBand(y0=top, y1=bottom, cells=tuple(cells)))
    if not bands:
        raise UnsupportedSource("the ruled table contains no populated row")
    return TableGrid(page=page.number, x_edges=tuple(x_edges), bands=tuple(bands))


def _merge_positions(positions: list[float]) -> list[float]:
    """Collapse rule positions that differ by less than the merge tolerance."""
    merged: list[float] = []
    for value in positions:
        if merged and value - merged[-1] <= RULE_MERGE_PT:
            merged[-1] = (merged[-1] + value) / 2
        else:
            merged.append(value)
    return merged


def text_rows(page: PageObservation) -> list[list[TextToken]]:
    """Group tokens into printed rows by baseline, preserving left-to-right order.

    Used for locating headings and legends in running text, never for deciding
    which table column a value sits in.
    """
    rows: list[list[TextToken]] = []
    for token in sorted(page.tokens, key=lambda t: (t.region.y1, t.region.x0)):
        # Anchored on the row's first token, not its last: comparing against the
        # last one lets a long row drift a tolerance at a time until it swallows
        # the row below it.
        if rows and abs(rows[-1][0].region.y1 - token.region.y1) <= ROW_TOLERANCE_PT:
            rows[-1].append(token)
        else:
            rows.append([token])
    return [sorted(row, key=lambda t: t.region.x0) for row in rows]


def _run(row: list[TextToken], start: int, count: int) -> list[TextToken] | None:
    """A contiguous run of ``count`` tokens starting at ``start``, or None."""
    if start + count > len(row):
        return None
    return row[start:start + count]


# ---------------------------------------------------------------------------
# Supported table grammars
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionRow:
    label: str
    symbol: str
    limit: LimitColumn
    value_text: str
    basic: bool
    cell: GridCell
    band: GridBand


@dataclass(frozen=True)
class LandPatternTable:
    grammar: str
    page: int
    units: SourceUnit
    rows: tuple[DimensionRow, ...]
    package_heading: str
    drawing_number: str | None
    region: SourceRegion

    def row(self, label: str, symbol: str) -> DimensionRow | None:
        found = [
            item for item in self.rows
            if item.label.casefold() == label.casefold() and item.symbol == symbol
        ]
        return found[0] if len(found) == 1 else None


def parse_land_pattern_table(page: PageObservation) -> LandPatternTable:
    """Reconstruct a Microchip-style RECOMMENDED LAND PATTERN table.

    Fails closed at every ambiguity: a missing title or package heading, a units
    word that is not an exact known unit, a data row that is not label / symbol
    / one value, or a value cell that spans several limit columns without the
    BSC marking that makes a basic dimension legitimately span them.
    """
    rows = text_rows(page)
    if _land_pattern_heading(rows) is None:
        raise UnsupportedSource("page carries no RECOMMENDED LAND PATTERN title")
    package_heading = _package_heading(rows)
    if package_heading is None:
        raise UnsupportedSource("page carries no '<n>-Lead ...' package heading")

    anchors = [token for token in page.tokens if token.text.upper() in _LIMIT_WORDS]
    if len(anchors) != 3:
        raise UnsupportedSource(
            f"page carries {len(anchors)} MIN/NOM/MAX tokens; the grammar requires exactly three"
        )
    grid = build_grid(page, anchors)

    header_index = None
    limit_columns: dict[LimitColumn, int] = {}
    for index, band in enumerate(grid.bands):
        found = {
            _LIMIT_WORDS[cell.text.upper()]: cell.first_column
            for cell in band.cells
            if cell.single_column and cell.text.upper() in _LIMIT_WORDS
        }
        if len(found) == 3:
            header_index, limit_columns = index, found
            break
    if header_index is None:
        raise UnsupportedSource("no band holds MIN, NOM and MAX in three separate columns")

    units = None
    for band in reversed(grid.bands[:header_index]):
        texts = [cell.text for cell in band.cells if cell.tokens]
        if texts and texts[0].casefold() == "units":
            known = [_UNIT_WORDS[text.upper()] for text in texts[1:] if text.upper() in _UNIT_WORDS]
            if len(known) != 1:
                raise UnsupportedSource(f"units row is not exactly one known unit: {texts[1:]}")
            units = known[0]
            break
    if units is None:
        raise UnsupportedSource("no 'Units' row above the dimension-limit header")

    first_limit = min(limit_columns.values())
    by_column = {column: limit for limit, column in limit_columns.items()}
    parsed: list[DimensionRow] = []
    for band in grid.bands[header_index + 1:]:
        populated = [cell for cell in band.cells if cell.tokens]
        if len(populated) != 3:
            break
        label_cell, symbol_cell, value_cell = populated
        if label_cell.last_column >= first_limit or symbol_cell.last_column >= first_limit:
            break
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,7}", symbol_cell.text):
            break
        if value_cell.first_column < first_limit:
            raise UnsupportedSource(
                f"value {value_cell.text!r} starts left of the first limit column"
            )
        words = value_cell.text.split()
        basic = len(words) == 2 and words[1].upper() == "BSC"
        number = words[0]
        if not _NUMBER.match(number) or (len(words) > 1 and not basic):
            raise UnsupportedSource(f"value cell {value_cell.text!r} is not a printed number")
        if value_cell.single_column:
            limit = by_column.get(value_cell.first_column)
            if limit is None:
                raise UnsupportedSource(f"value {value_cell.text!r} is under no limit column")
        else:
            spanned = {
                by_column[column] for column in range(value_cell.first_column,
                                                      value_cell.last_column + 1)
                if column in by_column
            }
            if spanned != set(LimitColumn) - {LimitColumn.BASIC} or not basic:
                raise UnsupportedSource(
                    f"value {value_cell.text!r} spans limit columns without a BSC marking"
                )
            limit = LimitColumn.BASIC
        parsed.append(DimensionRow(
            label=label_cell.text, symbol=symbol_cell.text, limit=limit,
            value_text=number, basic=basic, cell=value_cell, band=band,
        ))
    if not parsed:
        raise UnsupportedSource("dimension-limit header is followed by no readable data row")
    return LandPatternTable(
        grammar="microchip_land_pattern_v1", page=page.number, units=units,
        rows=tuple(parsed), package_heading=package_heading,
        drawing_number=_drawing_number(rows), region=grid.region,
    )


def _land_pattern_heading(rows: list[list[TextToken]]) -> str | None:
    for row in rows:
        words = [token.text.upper() for token in row]
        for start in range(len(words) - 2):
            if words[start:start + 3] == ["RECOMMENDED", "LAND", "PATTERN"]:
                return "RECOMMENDED LAND PATTERN"
    return None


def _package_heading(rows: list[list[TextToken]]) -> str | None:
    for row in rows:
        if row and _LEAD_COUNT.match(row[0].text):
            return " ".join(token.text for token in row)
    return None


def _drawing_number(rows: list[list[TextToken]]) -> str | None:
    for row in rows:
        words = [token.text for token in row]
        for index, word in enumerate(words):
            if word == "Drawing" and words[index + 1:index + 2] == ["No."]:
                tail = words[index + 2:index + 5]
                if len(tail) == 3 and tail[1] == "Rev":
                    return " ".join(tail)
    return None


@dataclass(frozen=True)
class PinRow:
    pin_numbers: dict[str, str]
    symbol: str
    function: str
    band: GridBand

    @property
    def region(self) -> SourceRegion:
        regions = [cell.region for cell in self.band.cells if cell.region is not None]
        return SourceRegion(
            x0=min(r.x0 for r in regions), y0=min(r.y0 for r in regions),
            x1=max(r.x1 for r in regions), y1=max(r.y1 for r in regions),
        )


@dataclass(frozen=True)
class PinFunctionTable:
    grammar: str
    page: int
    package_columns: tuple[str, ...]
    rows: tuple[PinRow, ...]

    def row_for(self, package_column: str, pin_number: str) -> PinRow | None:
        found = [row for row in self.rows if row.pin_numbers.get(package_column) == pin_number]
        return found[0] if len(found) == 1 else None


def parse_pin_function_table(page: PageObservation) -> PinFunctionTable:
    """Reconstruct a Microchip-style multi-package PIN FUNCTION table.

    Package columns come from the table's own printed sub-header. A cell holding
    an em dash means that package has no pin on this row; it is recorded as
    absent, never filled in from a neighbouring column.
    """
    anchors = [token for token in page.tokens if token.text in {"Symbol", "Function"}]
    if len(anchors) < 2:
        raise UnsupportedSource("page carries no Symbol/Function pin-table header")
    grid = build_grid(page, anchors)

    first_data = None
    for index, band in enumerate(grid.bands):
        first = next((cell for cell in band.cells if cell.tokens), None)
        if first is not None and first.single_column and _INTEGER.match(first.text):
            first_data = index
            break
    if first_data is None or first_data == 0:
        raise UnsupportedSource("the pin table has no header band above its first numbered row")

    symbol_column = grid.column_named("Symbol", above_band=first_data)
    function_column = grid.column_named("Function", above_band=first_data)
    if symbol_column is None or function_column is None:
        raise UnsupportedSource("no single column is headed Symbol and another headed Function")
    package_columns: list[tuple[int, str]] = []
    for column in range(min(symbol_column, function_column)):
        name = None
        for band in reversed(grid.bands[:first_data]):
            cell = band.cell_at(column)
            if cell is not None and cell.single_column and cell.tokens:
                name = cell.text
                break
        if name:
            package_columns.append((column, name))
    if not package_columns:
        raise UnsupportedSource("the pin table names no package column")
    names = [name for _, name in package_columns]
    if len(names) != len(set(names)):
        raise UnsupportedSource("pin-table package columns are not distinct")

    parsed: list[PinRow] = []
    for band in grid.bands[first_data:]:
        numbers: dict[str, str] = {}
        ok = True
        for column, name in package_columns:
            cell = band.cell_at(column)
            if cell is None or not cell.single_column:
                ok = False
                break
            if not cell.tokens or cell.text in _DASHES:
                continue
            if not _INTEGER.match(cell.text):
                ok = False
                break
            numbers[name] = cell.text
        symbol_cell = band.cell_at(symbol_column)
        function_cell = band.cell_at(function_column)
        if not ok or symbol_cell is None or function_cell is None:
            break
        if not symbol_cell.tokens or not function_cell.tokens:
            break
        parsed.append(PinRow(
            pin_numbers=numbers, symbol=symbol_cell.text, function=function_cell.text, band=band,
        ))
    if not parsed:
        raise UnsupportedSource("pin-table header is followed by no readable data row")
    return PinFunctionTable(
        grammar="microchip_pin_function_v1", page=page.number,
        package_columns=tuple(names), rows=tuple(parsed),
    )


# ---------------------------------------------------------------------------
# Drawn land topology
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DrawnLands:
    rectangles: tuple[VectorRectangle, ...]
    rows: tuple[tuple[VectorRectangle, ...], ...]
    columns: tuple[float, ...]


def drawn_lands(page: PageObservation, pin_count: int) -> DrawnLands:
    """Find the congruent drawn lands and their row/column topology.

    Distances are never taken from here. What the drawing establishes is which
    lands exist, which row each is in, and which lands line up in a column --
    facts a not-to-scale drawing still states correctly.
    """
    candidates = [rect for rect in page.rectangles if rect.stroked or rect.filled]
    groups: dict[tuple[float, float], list[VectorRectangle]] = {}
    for rect in candidates:
        width = rect.region.x1 - rect.region.x0
        height = rect.region.y1 - rect.region.y0
        key = (round(width / PAD_CONGRUENCE_PT), round(height / PAD_CONGRUENCE_PT))
        groups.setdefault(key, []).append(rect)
    matching = [group for group in groups.values() if len(group) == pin_count]
    if len(matching) != 1:
        raise UnsupportedSource(
            f"{len(matching)} congruent groups of {pin_count} drawn lands; expected exactly one"
        )
    lands = matching[0]
    heights = [rect.region.y1 - rect.region.y0 for rect in lands]
    widths = [rect.region.x1 - rect.region.x0 for rect in lands]
    row_tolerance = max(heights) / 2
    column_tolerance = max(widths) / 2
    rows: list[list[VectorRectangle]] = []
    for rect in sorted(lands, key=lambda r: (r.region.y0 + r.region.y1) / 2):
        centre = (rect.region.y0 + rect.region.y1) / 2
        # Anchored on the row's first land, for the same reason text rows are.
        if rows and abs(_centre_y(rows[-1][0]) - centre) <= row_tolerance:
            rows[-1].append(rect)
        else:
            rows.append([rect])
    columns: list[float] = []
    for rect in sorted(lands, key=_centre_x):
        centre = _centre_x(rect)
        if not columns or abs(columns[-1] - centre) > column_tolerance:
            columns.append(centre)
    return DrawnLands(
        rectangles=tuple(lands),
        rows=tuple(tuple(sorted(row, key=_centre_x)) for row in rows),
        columns=tuple(columns),
    )


def _centre_x(rect: VectorRectangle) -> float:
    return (rect.region.x0 + rect.region.x1) / 2


def _centre_y(rect: VectorRectangle) -> float:
    return (rect.region.y0 + rect.region.y1) / 2


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


def _receipt(
    bundle: DocumentObservationBundle,
    receipt_id: str,
    checker: str,
    outcome: ReceiptOutcome,
    *,
    claim,
    candidate_id: str | None = None,
    page: int | None = None,
    region: SourceRegion | None = None,
    measured: str | None = None,
    expected: str | None = None,
    reasons: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    bound_claims: dict[str, str] | None = None,
) -> VerificationReceipt:
    return VerificationReceipt(
        receipt_id=receipt_id,
        checker=checker,
        checker_version=CHECKER_VERSION,
        outcome=outcome,
        candidate_id=candidate_id,
        claim_hash=claim_hash(claim),
        document_digest=bundle.document_digest,
        observation_digest=bundle.observation_digest,
        page=page,
        located_region=region,
        measured=measured,
        expected=expected,
        reasons=reasons,
        limitations=limitations,
        bound_claims=bound_claims,
    )


def row_meaning(label: str, symbol: str) -> tuple[DimensionKind | None, int | None]:
    """What a printed land-table row denotes, and how many terminals it covers.

    Returns ``(None, None)`` when the supported grammar establishes no meaning
    for the row. That is the honest answer, and it quarantines the import rather
    than letting the proposal supply the meaning itself.
    """
    multiplier = _MULTIPLIER.search(label)
    terminals = int(multiplier.group(1)) if multiplier else None
    normalised = _MULTIPLIER.sub("", label).strip().casefold()
    return LAND_ROW_MEANINGS.get((normalised, symbol)), terminals


def terminal_meaning(symbol: str, function: str) -> TerminalKind:
    """What a printed pin row denotes, from its own symbol and function text."""
    folded = function.casefold()
    if symbol.upper() in _EXPOSED_PAD_SYMBOLS or "exposed thermal pad" in folded:
        return TerminalKind.EXPOSED_PAD
    if symbol.upper() in _NO_CONNECT_SYMBOLS or "no connection" in folded:
        return TerminalKind.NO_CONNECT
    return TerminalKind.ELECTRICAL


def verify_dimension(
    bundle: DocumentObservationBundle,
    candidate: PhysicalConstraintCandidate,
    *,
    expected_package_heading: str | None = None,
) -> VerificationReceipt:
    """Check one dimension against the row, symbol, column and units it claims."""
    receipt_id = f"CS-DIM-{candidate.candidate_id}"
    page = bundle.page(candidate.locator.page)
    if page is None:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.NOT_LOCATED,
                        claim=candidate, candidate_id=candidate.candidate_id,
                        reasons=(f"page {candidate.locator.page} was not observed",))
    try:
        table = parse_land_pattern_table(page)
    except UnsupportedSource as exc:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id,
                        page=page.number, reasons=(str(exc)[:200],))
    if candidate.kind not in LAND_DIMENSION_KINDS:
        # parse_land_pattern_table already required the RECOMMENDED LAND PATTERN
        # title, which is what makes this a land table rather than a package
        # outline table. A package terminal dimension read off it would be the
        # wrong feature, so this slice refuses rather than guessing.
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        reasons=(f"{candidate.kind.value} is not a recommended-land dimension",))
    if expected_package_heading and table.package_heading != expected_package_heading:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.NOT_SUPPORTED,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        measured=table.package_heading[:200], expected=expected_package_heading[:200],
                        reasons=("the table on this page is for a different package",))
    row = table.row(candidate.row_label, candidate.dimension_symbol)
    if row is None:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.NOT_SUPPORTED,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        region=table.region,
                        expected=f"{candidate.row_label} / {candidate.dimension_symbol}",
                        reasons=("no single table row carries that label and dimension symbol",))
    # What the row MEANS comes from the grammar, never from the proposal. A row
    # the grammar does not map has no established meaning at all.
    meaning, terminals = row_meaning(row.label, row.symbol)
    if meaning is None:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        region=row.cell.region, measured=f"{row.label} / {row.symbol}",
                        reasons=("the supported grammar does not establish what this row denotes",))
    reasons: list[str] = []
    if meaning is not candidate.kind:
        reasons.append(
            f"this row denotes {meaning.value}; the claim calls it {candidate.kind.value}"
        )
    if terminals is not None and candidate.applies_to_terminals not in (None, terminals):
        reasons.append(
            f"the row applies to {terminals} terminals, the claim states "
            f"{candidate.applies_to_terminals}"
        )
    if row.limit is not candidate.limit:
        reasons.append(
            f"value is printed in the {row.limit.value.upper()} column, "
            f"not {candidate.limit.value.upper()}"
        )
    if table.units is not candidate.value.unit:
        reasons.append(
            f"table declares {table.units.value}, the claim declares {candidate.value.unit.value}"
        )
    if Decimal(row.value_text) != Decimal(candidate.value.source_text):
        reasons.append(f"row prints {row.value_text}, the claim states {candidate.value.source_text}")
    if row.basic != candidate.basic_dimension:
        reasons.append(
            "BSC marking disagrees: the row is "
            f"{'basic' if row.basic else 'not basic'}"
        )
    outcome = ReceiptOutcome.NOT_SUPPORTED if reasons else ReceiptOutcome.SUPPORTED
    return _receipt(
        bundle, receipt_id, "CS-SOURCE", outcome,
        claim=dimension_claim(
            kind=meaning, dimension_symbol=row.symbol, limit=row.limit,
            value=candidate.value, basic_dimension=row.basic,
            applies_to_terminals=terminals,
        ),
        candidate_id=candidate.candidate_id, page=page.number, region=row.cell.region,
        measured=f"{row.label} / {row.symbol} / {row.limit.value} / {row.value_text} "
                 f"{table.units.value}",
        expected=f"{candidate.row_label} / {candidate.dimension_symbol} / "
                 f"{candidate.limit.value} / {candidate.value.source_text} "
                 f"{candidate.value.unit.value}",
        reasons=tuple(reasons[:8]),
        limitations=(
            ("Datasheet land conformance only; not IPC-7351/7352 compliance, solder joint "
             "reliability, paste volume or thermal adequacy."),
        ),
    )


def verify_pin(
    bundle: DocumentObservationBundle, candidate: PinCandidate
) -> VerificationReceipt:
    """Check one pin row inside the package column it claims, and no other."""
    receipt_id = f"CS-PINROW-{candidate.candidate_id}"
    page = bundle.page(candidate.locator.page)
    if page is None:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.NOT_LOCATED,
                        claim=candidate, candidate_id=candidate.candidate_id,
                        reasons=(f"page {candidate.locator.page} was not observed",))
    try:
        table = parse_pin_function_table(page)
    except UnsupportedSource as exc:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id,
                        page=page.number, reasons=(str(exc)[:200],))
    if candidate.package_column not in table.package_columns:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.NOT_SUPPORTED,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        measured=", ".join(table.package_columns),
                        expected=candidate.package_column,
                        reasons=("the table has no such package column",))
    row = table.row_for(candidate.package_column, candidate.pin_number)
    if row is None:
        return _receipt(bundle, receipt_id, "CS-SOURCE", ReceiptOutcome.NOT_SUPPORTED,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        expected=f"{candidate.package_column} pin {candidate.pin_number}",
                        reasons=("no single row carries that pin number in that package column",))
    reasons: list[str] = []
    if row.symbol != candidate.symbol:
        reasons.append(f"row symbol is {row.symbol!r}, the claim states {candidate.symbol!r}")
    if row.function.casefold() != candidate.function.casefold():
        reasons.append("row function text does not match the claim")
    # As with a dimension row, the terminal's kind is derived from what the row
    # prints, so a real electrical pin cannot be relabelled an exposed pad.
    meaning = terminal_meaning(row.symbol, row.function)
    if meaning is not candidate.kind:
        reasons.append(
            f"this row denotes a {meaning.value} terminal; the claim calls it "
            f"{candidate.kind.value}"
        )
    outcome = ReceiptOutcome.NOT_SUPPORTED if reasons else ReceiptOutcome.SUPPORTED
    return _receipt(
        bundle, receipt_id, "CS-SOURCE", outcome,
        claim=terminal_claim(
            package_column=candidate.package_column, pin_number=candidate.pin_number,
            symbol=row.symbol, function=row.function, kind=meaning,
        ),
        candidate_id=candidate.candidate_id, page=page.number, region=row.region,
        measured=f"{candidate.package_column} {candidate.pin_number} / {row.symbol} / {row.function}",
        expected=f"{candidate.package_column} {candidate.pin_number} / {candidate.symbol} / "
                 f"{candidate.function}",
        reasons=tuple(reasons[:8]),
        limitations=(
            ("A checked pin table row establishes the printed name and function only; it "
             "establishes no electrical limit, behaviour or internal connection."),
        ),
    )


def verify_pad_ordering(
    bundle: DocumentObservationBundle, candidate: PadOrderingCandidate, *, pin_count: int
) -> tuple[VerificationReceipt, VerifiedPadOrdering | None]:
    """Derive pad topology from the drawing and check the printed pin labels.

    At least two printed labels are required. One label cannot distinguish a
    clockwise sequence from a counter-clockwise one, and a footprint whose
    numbering runs the wrong way around passes every pitch-only test.
    """
    receipt_id = f"CS-ORDER-{candidate.candidate_id}"
    page = bundle.page(candidate.locator.page)
    if page is None:
        return _receipt(bundle, receipt_id, "CS-ORIENTATION", ReceiptOutcome.NOT_LOCATED,
                        claim=candidate, candidate_id=candidate.candidate_id,
                        reasons=(f"page {candidate.locator.page} was not observed",)), None
    try:
        lands = drawn_lands(page, pin_count)
    except UnsupportedSource as exc:
        return _receipt(bundle, receipt_id, "CS-ORIENTATION", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        reasons=(str(exc)[:200],)), None
    if len(lands.rows) != 2:
        return _receipt(bundle, receipt_id, "CS-ORIENTATION", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        reasons=(f"{len(lands.rows)} drawn land rows; this slice supports two",)), None
    if candidate.first_pin_corner != "bottom_left":
        return _receipt(bundle, receipt_id, "CS-ORIENTATION", ReceiptOutcome.UNSUPPORTED_SOURCE,
                        claim=candidate, candidate_id=candidate.candidate_id, page=page.number,
                        reasons=(f"first pin corner {candidate.first_pin_corner!r} is not supported",
                                 )), None
    # PDF y grows downward, so the visually lower row is the one with larger y.
    upper, lower = lands.rows[0], lands.rows[1]
    if candidate.traversal == "counter_clockwise_from_pin_1":
        sequence = list(lower) + list(reversed(upper))
    else:
        sequence = list(upper) + list(reversed(lower))
    assignment = {str(index + 1): rect for index, rect in enumerate(sequence)}

    labels = _pad_number_labels(page, lands, pin_count)
    confirmed: list[str] = []
    reasons: list[str] = []
    for pin in candidate.labelled_pins:
        token = labels.get(pin)
        if token is None:
            reasons.append(f"no printed label {pin!r} was found beside the drawn lands")
            continue
        nearest = min(lands.rectangles, key=lambda rect: _distance(rect, token))
        if nearest is not assignment[pin]:
            reasons.append(f"printed label {pin!r} sits beside a different land than the traversal")
            continue
        confirmed.append(pin)
    if len(confirmed) < 2:
        reasons.append("fewer than two printed pin labels confirmed the traversal direction")
    outcome = ReceiptOutcome.NOT_SUPPORTED if reasons else ReceiptOutcome.SUPPORTED
    # The slots are derived before the receipt so the receipt can bind to them.
    # A receipt that recorded only "the traversal looked right" would survive a
    # later edit to the slots it was supposed to establish.
    slots: list[PadSlot] = []
    for pin, rect in assignment.items():
        row_index = 0 if rect in lower else 1
        column = min(
            range(len(lands.columns)),
            key=lambda index: abs(lands.columns[index] - _centre_x(rect)),
        )
        slots.append(PadSlot(pin_number=pin, row=row_index, column=column))
    ordered_slots = tuple(sorted(slots, key=lambda slot: int(slot.pin_number)))
    receipt = _receipt(
        bundle, receipt_id, "CS-ORIENTATION", outcome,
        claim=pad_ordering_claim(
            traversal=candidate.traversal, first_pin_corner=candidate.first_pin_corner,
            slots=ordered_slots,
        ),
        candidate_id=candidate.candidate_id, page=page.number,
        region=SourceRegion(
            x0=min(r.region.x0 for r in lands.rectangles),
            y0=min(r.region.y0 for r in lands.rectangles),
            x1=max(r.region.x1 for r in lands.rectangles),
            y1=max(r.region.y1 for r in lands.rectangles),
        ),
        measured=f"{len(lands.rows)} rows, {len(lands.columns)} columns, "
                 f"labels confirmed: {','.join(confirmed) or 'none'}",
        expected=f"{candidate.traversal} from {candidate.first_pin_corner}",
        reasons=tuple(reasons[:8]),
        limitations=(
            ("Drawing topology only: which lands exist and how they line up. Every distance "
             "comes from the dimension table, because a drawing may not be to scale."),
        ),
    )
    if outcome is not ReceiptOutcome.SUPPORTED:
        return receipt, None
    return receipt, VerifiedPadOrdering(
        traversal=candidate.traversal, first_pin_corner=candidate.first_pin_corner,
        slots=ordered_slots, receipt_id=receipt_id,
    )


def _pad_number_labels(
    page: PageObservation, lands: DrawnLands, pin_count: int
) -> dict[str, TextToken]:
    span = max(
        max(rect.region.x1 - rect.region.x0 for rect in lands.rectangles),
        max(rect.region.y1 - rect.region.y0 for rect in lands.rectangles),
    ) * LABEL_SEARCH_FACTOR
    area = SourceRegion(
        x0=max(0.0, min(r.region.x0 for r in lands.rectangles) - span),
        y0=max(0.0, min(r.region.y0 for r in lands.rectangles) - span),
        x1=max(r.region.x1 for r in lands.rectangles) + span,
        y1=max(r.region.y1 for r in lands.rectangles) + span,
    )
    found: dict[str, list[TextToken]] = {}
    for token in page.tokens:
        if not _INTEGER.match(token.text) or not 1 <= int(token.text) <= pin_count:
            continue
        if area.contains(token.region):
            found.setdefault(str(int(token.text)), []).append(token)
    # A duplicated label cannot anchor a sequence; drop it rather than pick one.
    return {pin: tokens[0] for pin, tokens in found.items() if len(tokens) == 1}


def _distance(rect: VectorRectangle, token: TextToken) -> float:
    dx = _centre_x(rect) - token.x_centre
    dy = _centre_y(rect) - token.y_centre
    return (dx * dx + dy * dy) ** 0.5


#: Printed redundancy inside a supported land table. A single misread digit
#: breaks at least one of these, so they are checked as their own receipts.
CONSISTENCY_RELATIONS: tuple[tuple[str, DimensionKind, DimensionKind, DimensionKind], ...] = (
    ("overall_width_is_row_spacing_plus_pad_length", DimensionKind.LAND_OVERALL_WIDTH,
     DimensionKind.LAND_ROW_SPACING, DimensionKind.LAND_PAD_LENGTH),
    ("row_gap_is_row_spacing_minus_pad_length", DimensionKind.LAND_ROW_GAP,
     DimensionKind.LAND_ROW_SPACING, DimensionKind.LAND_PAD_LENGTH),
    ("adjacent_gap_is_pitch_minus_pad_width", DimensionKind.LAND_ADJACENT_GAP,
     DimensionKind.LAND_CONTACT_PITCH, DimensionKind.LAND_PAD_WIDTH),
)


def verify_consistency(
    bundle: DocumentObservationBundle, verified: dict[DimensionKind, VerifiedDimension]
) -> list[VerificationReceipt]:
    """Check the arithmetic the drawing prints about itself.

    Each relation binds the claim hashes of all three operands, so it cannot
    survive a later change to any value it related. A relation whose inputs are
    not all present is not checked and produces no receipt; the caller records
    that as a limitation. Absence of a check is never recorded as a pass.
    """
    receipts: list[VerificationReceipt] = []
    for name, result_kind, left_kind, right_kind in CONSISTENCY_RELATIONS:
        result, left, right = (verified.get(result_kind), verified.get(left_kind),
                               verified.get(right_kind))
        if result is None or left is None or right is None:
            continue
        sign = 1 if name.endswith("plus_pad_length") else -1
        expected = left.value.nanometres + sign * right.value.nanometres
        supported = expected == result.value.nanometres
        hashes = {
            "result_claim": claim_hash(result.claim()),
            "left_claim": claim_hash(left.claim()),
            "right_claim": claim_hash(right.claim()),
        }
        receipts.append(_receipt(
            bundle, f"CS-CONSIST-{name}", "CS-SOURCE-CONSISTENCY",
            ReceiptOutcome.SUPPORTED if supported else ReceiptOutcome.NOT_SUPPORTED,
            claim=relation_claim(relation=name, expected_nm=expected, **hashes),
            measured=f"{result.value.nanometres} nm",
            expected=f"{expected} nm",
            reasons=() if supported else ("printed dimensions contradict each other",),
            bound_claims=hashes,
        ))
    return receipts


def verify_identity(
    bundle: DocumentObservationBundle, candidate: IdentityCandidate
) -> tuple[list[VerificationReceipt], VerifiedIdentity | None]:
    """Locate each identity field exactly, or leave it unsupported.

    The orderable part number is bound to a package by the document's own
    package-code legend, not by the suffix looking plausible: ``/OT`` means
    SOT23 because the datasheet says ``OT = ... (SOT23), 5-Lead``.
    """
    receipts: list[VerificationReceipt] = []
    fields = {
        "manufacturer": candidate.manufacturer,
        "base_device": candidate.base_device,
        "orderable_part_number": candidate.orderable_part_number,
        "package_code": candidate.package_code,
        "package_description": candidate.package_description,
        "document_revision": candidate.document_revision,
        "drawing_number": candidate.drawing_number,
    }
    missing = [name for name, value in fields.items() if not value]
    if missing or candidate.pin_count is None:
        for name in missing + ([] if candidate.pin_count is not None else ["pin_count"]):
            receipts.append(_receipt(
                bundle, f"CS-IDENT-{name.upper()}", "CS-SOURCE", ReceiptOutcome.NOT_SUPPORTED,
                claim={"field": name}, reasons=("the candidate left this identity field unknown",),
            ))
        return receipts, None

    checks = [
        ("MANUFACTURER", "manufacturer", _find_phrase(bundle, candidate.manufacturer)),
        ("DEVICE", "base_device", _find_device(bundle, candidate.base_device)),
        ("MPN", "orderable_part_number",
         _find_phrase(bundle, candidate.orderable_part_number, allow_trailing_colon=True)),
        ("REVISION", "document_revision", _find_revision(bundle, candidate.document_revision)),
        ("DRAWING", "drawing_number", _find_drawing(bundle, candidate.drawing_number)),
        ("PACKAGE", "package_description", _find_package(bundle, candidate)),
    ]
    for name, field, found in checks:
        page_number, region, reason = found
        claim = {"field": field, "value": fields[field]}
        if name == "PACKAGE":
            claim = {
                "field": field, "value": fields[field],
                "package_code": candidate.package_code,
                "pin_count": candidate.pin_count,
                "orderable_part_number": candidate.orderable_part_number,
            }
        receipts.append(_receipt(
            bundle, f"CS-IDENT-{name}", "CS-SOURCE",
            ReceiptOutcome.SUPPORTED if reason is None else ReceiptOutcome.NOT_SUPPORTED,
            claim=claim, page=page_number, region=region,
            reasons=() if reason is None else (reason,),
        ))
    if any(not receipt.supported for receipt in receipts):
        return receipts, None
    # One binding receipt covers the identity as a whole. The six field receipts
    # each establish one located fact; this one establishes that *this exact
    # combination* is what was checked, so no field can be edited afterwards
    # while the field receipts still read "supported".
    payload = identity_claim(
        manufacturer=candidate.manufacturer,
        base_device=candidate.base_device,
        orderable_part_number=candidate.orderable_part_number,
        package_code=candidate.package_code,
        package_description=candidate.package_description,
        pin_count=candidate.pin_count,
        document_revision=candidate.document_revision,
        drawing_number=candidate.drawing_number,
    )
    receipts.append(_receipt(
        bundle, "CS-IDENT-BINDING", "CS-SOURCE", ReceiptOutcome.SUPPORTED, claim=payload,
        measured=f"{candidate.orderable_part_number} / {candidate.package_description}",
        limitations=(
            ("Identity as printed in this document. It establishes no silicon identity and "
             "no supplier, lifecycle or availability fact."),
        ),
    ))
    identity = VerifiedIdentity(
        manufacturer=candidate.manufacturer,
        base_device=candidate.base_device,
        orderable_part_number=candidate.orderable_part_number,
        package_code=candidate.package_code,
        package_description=candidate.package_description,
        pin_count=candidate.pin_count,
        document_revision=candidate.document_revision,
        drawing_number=candidate.drawing_number,
        receipt_id="CS-IDENT-BINDING",
    )
    return receipts, identity


def _find_phrase(
    bundle: DocumentObservationBundle, phrase: str, *, allow_trailing_colon: bool = False
) -> tuple[int | None, SourceRegion | None, str | None]:
    words = phrase.split()
    for page in bundle.pages:
        for row in text_rows(page):
            texts = [token.text for token in row]
            for start in range(len(texts)):
                run = _run(row, start, len(words))
                if run is None:
                    continue
                actual = [token.text for token in run]
                if allow_trailing_colon and actual:
                    actual = actual[:-1] + [actual[-1].rstrip(":")]
                if actual == words:
                    return page.number, _span(run), None
    return None, None, f"{phrase!r} is not printed as a contiguous run on any observed page"


def _find_device(
    bundle: DocumentObservationBundle, device: str
) -> tuple[int | None, SourceRegion | None, str | None]:
    """A family header such as ``MCP73831/2`` names ``MCP73831``."""
    for page in bundle.pages:
        for token in page.tokens:
            if token.text == device or token.text.split("/")[0] == device:
                return page.number, token.region, None
    return None, None, f"{device!r} is not printed on any observed page"


def _find_revision(
    bundle: DocumentObservationBundle, revision: str
) -> tuple[int | None, SourceRegion | None, str | None]:
    pattern = re.compile(rf"^DS\d+{re.escape(revision)}-page$")
    for page in bundle.pages:
        for token in page.tokens:
            if pattern.match(token.text):
                return page.number, token.region, None
    return None, None, (
        f"no page footer names document revision {revision!r}"
    )


def _find_drawing(
    bundle: DocumentObservationBundle, drawing: str
) -> tuple[int | None, SourceRegion | None, str | None]:
    for page in bundle.pages:
        rows = text_rows(page)
        if _drawing_number(rows) == drawing:
            for row in rows:
                if drawing.split()[0] in [token.text for token in row]:
                    return page.number, _span(row), None
    return None, None, f"no page carries drawing number {drawing!r}"


def _find_package(
    bundle: DocumentObservationBundle, candidate: IdentityCandidate
) -> tuple[int | None, SourceRegion | None, str | None]:
    """Bind code, pin count and package description through the printed legend."""
    legend = None
    for page in bundle.pages:
        for row in text_rows(page):
            texts = [token.text for token in row]
            for start, text in enumerate(texts):
                if text != candidate.package_code or texts[start + 1:start + 2] != ["="]:
                    continue
                tail = texts[start + 2:]
                lead = next((word for word in tail if _LEAD_COUNT.match(word)), None)
                bracket = next(
                    (word for word in tail if word.startswith("(") and word.rstrip(",").endswith(")")),
                    None,
                )
                if lead is None or bracket is None:
                    continue
                legend = (page.number, _span(row[start:start + 2 + len(tail)]), lead, bracket)
                break
            if legend:
                break
        if legend:
            break
    if legend is None:
        return None, None, (
            f"no package-code legend binds {candidate.package_code!r} to a package and pin count"
        )
    page_number, region, lead, bracket = legend
    lead_count = int(_LEAD_COUNT.match(lead).group(1))
    if lead_count != candidate.pin_count:
        return page_number, region, (
            f"legend says {lead_count} leads, the claim says {candidate.pin_count}"
        )
    family = bracket.strip("(),")
    if family.upper() not in candidate.package_description.upper():
        return page_number, region, (
            f"legend package family {family!r} is absent from the claimed package description"
        )
    if not candidate.orderable_part_number.upper().endswith("/" + candidate.package_code.upper()):
        return page_number, region, (
            "the orderable part number does not carry this package code as its suffix"
        )
    for page in bundle.pages:
        for row in text_rows(page):
            if " ".join(token.text for token in row) == candidate.package_description:
                return page.number, _span(row), None
    return page_number, region, (
        "the claimed package description is not printed as a heading on any observed page"
    )


def _span(tokens) -> SourceRegion:
    return SourceRegion(
        x0=min(token.region.x0 for token in tokens),
        y0=min(token.region.y0 for token in tokens),
        x1=max(token.region.x1 for token in tokens),
        y1=max(token.region.y1 for token in tokens),
    )


@dataclass(frozen=True)
class SourceVerificationReport:
    """Every receipt, plus the verified set only when all requirements are met."""

    receipts: tuple[VerificationReceipt, ...]
    verified: VerifiedConstraintSet | None
    missing: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def quarantined(self) -> bool:
        return self.verified is None

    def unsupported(self) -> tuple[VerificationReceipt, ...]:
        return tuple(receipt for receipt in self.receipts if not receipt.supported)


def verify_extraction(
    bundle: DocumentObservationBundle,
    proposal: ExtractionProposal,
    *,
    required_dimensions: frozenset[DimensionKind],
    package_column: str,
) -> SourceVerificationReport:
    """Verify a whole proposal and build the verified set only if nothing is missing.

    "Nothing is missing" is checked against the required-dimension matrix and
    the declared pin count, not against the proposal being non-empty. An
    all-pass report over two claims does not verify a five-pin package.
    """
    receipts: list[VerificationReceipt] = []
    limitations: list[str] = []
    missing: list[str] = []

    identity_receipts, identity = verify_identity(bundle, proposal.identity)
    receipts.extend(identity_receipts)

    heading = identity.package_description if identity else None
    dimensions: list[VerifiedDimension] = []
    values: dict[DimensionKind, VerifiedDimension] = {}
    for candidate in proposal.dimensions:
        receipt = verify_dimension(bundle, candidate, expected_package_heading=heading)
        receipts.append(receipt)
        if not receipt.supported:
            continue
        # Every field of the accepted dimension comes from the checked row, not
        # from the candidate: the candidate only said where to look.
        meaning, terminals = row_meaning(candidate.row_label, candidate.dimension_symbol)
        if meaning is None:
            continue
        verified_dimension = VerifiedDimension(
            kind=meaning, dimension_symbol=candidate.dimension_symbol,
            limit=candidate.limit, value=candidate.value,
            basic_dimension=candidate.basic_dimension,
            applies_to_terminals=terminals, receipt_id=receipt.receipt_id,
        )
        dimensions.append(verified_dimension)
        values[meaning] = verified_dimension

    consistency = verify_consistency(bundle, values)
    receipts.extend(consistency)
    checked = {receipt.receipt_id for receipt in consistency}
    for name, *_ in CONSISTENCY_RELATIONS:
        if f"CS-CONSIST-{name}" not in checked:
            limitations.append(f"printed relation {name} was not checkable: an input is absent")

    terminals: list[VerifiedTerminal] = []
    for candidate in proposal.pins:
        if candidate.package_column != package_column:
            continue
        receipt = verify_pin(bundle, candidate)
        receipts.append(receipt)
        if receipt.supported:
            terminals.append(VerifiedTerminal(
                package_column=candidate.package_column,
                pin_number=candidate.pin_number, symbol=candidate.symbol,
                function=candidate.function,
                kind=terminal_meaning(candidate.symbol, candidate.function),
                receipt_id=receipt.receipt_id,
            ))

    ordering = None
    if proposal.pad_ordering is None:
        missing.append("pad ordering candidate")
    elif identity is not None:
        receipt, ordering = verify_pad_ordering(
            bundle, proposal.pad_ordering, pin_count=identity.pin_count
        )
        receipts.append(receipt)

    for kind in sorted(required_dimensions, key=lambda item: item.value):
        if kind not in values:
            missing.append(f"required dimension {kind.value}")
    if identity is None:
        missing.append("verified identity")
    elif len(terminals) != identity.pin_count:
        missing.append(
            f"{identity.pin_count} verified terminals for {package_column}; got {len(terminals)}"
        )
    if ordering is None:
        missing.append("verified pad ordering")
    if any(not receipt.supported for receipt in receipts):
        missing.append("one or more claims are unsupported")

    limitations.append(
        "Source support establishes what the document prints. It establishes no electrical "
        "behaviour, no IPC compliance, and no catalog eligibility."
    )
    if missing or identity is None or ordering is None:
        return SourceVerificationReport(
            receipts=tuple(receipts), verified=None,
            missing=tuple(dict.fromkeys(missing)), limitations=tuple(limitations),
        )
    verified = VerifiedConstraintSet(
        document_digest=bundle.document_digest,
        observation_digest=bundle.observation_digest,
        identity=identity,
        dimensions=tuple(dimensions),
        terminals=tuple(sorted(terminals, key=lambda item: int(item.pin_number))),
        pad_ordering=ordering,
        receipts=tuple(receipts),
        limitations=tuple(limitations),
    )
    return SourceVerificationReport(
        receipts=tuple(receipts), verified=verified, missing=(), limitations=tuple(limitations),
    )


__all__ = [
    "CHECKER_VERSION",
    "CONSISTENCY_RELATIONS",
    "LAND_ROW_MEANINGS",
    "SUPPORTED_GRAMMARS",
    "DimensionRow",
    "DrawnLands",
    "GridBand",
    "GridCell",
    "LandPatternTable",
    "PinFunctionTable",
    "PinRow",
    "SourceVerificationReport",
    "TableGrid",
    "UnsupportedSource",
    "build_grid",
    "drawn_lands",
    "parse_land_pattern_table",
    "parse_pin_function_table",
    "row_meaning",
    "terminal_meaning",
    "text_rows",
    "verify_consistency",
    "verify_dimension",
    "verify_extraction",
    "verify_identity",
    "verify_pad_ordering",
    "verify_pin",
]
