"""Typed contracts for dynamic multimodal component synthesis.

This module is the trust boundary of COMPONENT_SYNTHESIS_PLAN.md expressed as
data. Three distinctions are load-bearing and are enforced here rather than left
to reviewer discipline:

* **A proposal is not evidence.** Everything a provider may return lives under
  :class:`ExtractionProposal` and its candidate types. None of them can carry a
  verdict, an :class:`~ohmni.domain.evidence.Evidence` object, a verification
  status, a catalog identifier, a file path, or S-expression text -- the schemas
  forbid the fields outright, and :func:`assert_proposal_schema_is_untrusted`
  checks that mechanically for every proposal type.
* **A receipt is not a proposal.** :class:`VerificationReceipt` records what a
  deterministic check actually measured. Its constructor requires a checker
  identifier and version, and nothing in this module produces one from a
  candidate; only :mod:`ohmni.datasheet.constraint_verifier` does.
* **A number is not a dimension.** A drawn value has a unit, a limit column
  (min/nom/max), a dimension symbol, and a feature it belongs to. Values are
  parsed from their exact printed decimal text and held on an integer nanometre
  grid, so 0.95 mm is not 0.95 inch and never becomes 0.9499999999999999.

Nothing here imports infrastructure; ``tests/test_architecture.py`` enforces it.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

#: The internal length grid. Every extracted dimension is converted once, at the
#: parsing boundary, into whole nanometres. Existing Ohmni physical APIs are
#: float millimetres; that conversion happens at one tested boundary
#: (:meth:`LengthValue.millimetres`) instead of being re-rounded per stage.
NANOMETRES_PER_MM = 1_000_000
#: Exact by definition (international inch, 1959).
NANOMETRES_PER_INCH = 25_400_000
NANOMETRES_PER_MIL = 25_400

#: Quantisation tolerance of the grid itself, in nanometres. This is *not* a
#: manufacturing tolerance and is never added to one; it exists so a check can
#: state the numerical slack it allowed.
GRID_EPSILON_NM = 1

ShortText = Annotated[str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)]
Quote = Annotated[str, StringConstraints(min_length=1, max_length=400)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.\-/+()]{0,79}$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

#: Field names a provider may never supply, anywhere in a proposal schema. The
#: point is not that a model would be believed if it said ``status="verified"``;
#: it is that the field must not exist for it to fill in, so a later refactor
#: cannot quietly start reading one.
FORBIDDEN_PROPOSAL_FIELDS = frozenset({
    "evidence", "status", "verified", "snippet_verified", "claim_status",
    "outcome", "verdict", "confidence_verified", "receipt", "receipts",
    "approved", "admitted", "catalog_id", "part_id", "revision_id",
    "path", "file_path", "sexpr", "s_expression", "kicad", "code",
    "provenance_machine_verified", "capability", "capabilities",
})


class SourceUnit(StrEnum):
    """Units a mechanical drawing may print. Never inferred from magnitude."""

    MILLIMETRE = "mm"
    INCH = "inch"
    MIL = "mil"


_UNIT_FACTORS = {
    SourceUnit.MILLIMETRE: NANOMETRES_PER_MM,
    SourceUnit.INCH: NANOMETRES_PER_INCH,
    SourceUnit.MIL: NANOMETRES_PER_MIL,
}

_DECIMAL_TEXT = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")


class LengthValue(BaseModel):
    """One printed length: its exact source text, its unit, and its grid value.

    ``source_text`` is the characters as printed, so a check can say which
    glyphs it read. ``nanometres`` is derived from that text by exact decimal
    arithmetic; the pair is validated to agree, which makes a transcription
    error in either half a construction failure rather than a silent drift.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_text: Annotated[str, StringConstraints(min_length=1, max_length=24)]
    unit: SourceUnit
    nanometres: int

    @model_validator(mode="after")
    def _exact(self) -> LengthValue:
        expected = _to_nanometres(self.source_text, self.unit)
        if expected != self.nanometres:
            raise ValueError(
                f"{self.source_text!r} {self.unit.value} is {expected} nm, not {self.nanometres} nm"
            )
        return self

    @classmethod
    def parse(cls, source_text: str, unit: SourceUnit) -> LengthValue:
        return cls(
            source_text=source_text,
            unit=unit,
            nanometres=_to_nanometres(source_text, unit),
        )

    def millimetres(self) -> float:
        """The single conversion boundary to Ohmni's float-millimetre physics."""
        return self.nanometres / NANOMETRES_PER_MM


def _to_nanometres(source_text: str, unit: SourceUnit) -> int:
    text = source_text.strip()
    if not _DECIMAL_TEXT.match(text):
        raise ValueError(f"{source_text!r} is not an exact printed decimal length")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
        raise ValueError(f"{source_text!r} is not a decimal") from exc
    scaled = value * _UNIT_FACTORS[unit]
    if scaled != scaled.to_integral_value():
        raise ValueError(
            f"{source_text!r} {unit.value} is finer than the {GRID_EPSILON_NM} nm length grid"
        )
    return int(scaled)


class LimitColumn(StrEnum):
    """Which column of a dimension table a value was printed in.

    ``BASIC`` is not a fourth column. It is the honest reading of a value
    printed *across* the limit columns, which is what a drawing does for a basic
    dimension: theoretically exact, with no minimum or maximum. Recording such a
    value as ``NOM`` because its centre happens to land nearest the nominal
    column would be an interpretation the document did not make.
    """

    MIN = "min"
    NOM = "nom"
    MAX = "max"
    BASIC = "basic"


class DimensionKind(StrEnum):
    """The mechanical feature a dimension describes.

    Recommended land dimensions and package terminal dimensions are separate
    members on purpose: COMPONENT_SYNTHESIS_PLAN.md requires manufacturer land
    data for the first CAD proof, and a lead width must never be silently used
    as a pad width.
    """

    LAND_PAD_WIDTH = "land_pad_width"
    LAND_PAD_LENGTH = "land_pad_length"
    LAND_CONTACT_PITCH = "land_contact_pitch"
    LAND_ROW_SPACING = "land_row_spacing"
    LAND_ROW_GAP = "land_row_gap"
    LAND_ADJACENT_GAP = "land_adjacent_gap"
    LAND_OVERALL_WIDTH = "land_overall_width"
    PACKAGE_BODY_WIDTH = "package_body_width"
    PACKAGE_BODY_LENGTH = "package_body_length"
    PACKAGE_TERMINAL_WIDTH = "package_terminal_width"
    PACKAGE_TERMINAL_LENGTH = "package_terminal_length"


#: Which dimension kinds describe a manufacturer-recommended PCB land, as
#: opposed to the metal of the part. Only these may feed a land pattern built
#: with the ``manufacturer_recommended_table`` policy.
LAND_DIMENSION_KINDS = frozenset({
    DimensionKind.LAND_PAD_WIDTH,
    DimensionKind.LAND_PAD_LENGTH,
    DimensionKind.LAND_CONTACT_PITCH,
    DimensionKind.LAND_ROW_SPACING,
    DimensionKind.LAND_ROW_GAP,
    DimensionKind.LAND_ADJACENT_GAP,
    DimensionKind.LAND_OVERALL_WIDTH,
})


class SourceRegion(BaseModel):
    """A rectangle in PDF user-space points on one page.

    Candidate locators use this to say *where* they read something. A region a
    provider supplies is a claim about the document, checked against actual
    token geometry before it means anything.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    x0: float = Field(ge=0, le=20000)
    y0: float = Field(ge=0, le=20000)
    x1: float = Field(ge=0, le=20000)
    y1: float = Field(ge=0, le=20000)

    @model_validator(mode="after")
    def _ordered(self) -> SourceRegion:
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("source region must have positive width and height")
        return self

    def contains(self, other: SourceRegion, *, tolerance: float = 0.0) -> bool:
        return (
            other.x0 >= self.x0 - tolerance
            and other.y0 >= self.y0 - tolerance
            and other.x1 <= self.x1 + tolerance
            and other.y1 <= self.y1 + tolerance
        )


class SourceLocator(BaseModel):
    """Where a candidate claims to have read something. Candidate until checked."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: Sha256
    page: int = Field(ge=1, le=2000)
    region: SourceRegion
    quote: Quote
    token_ids: tuple[Annotated[str, StringConstraints(pattern=r"^p\d+t\d+$")], ...] = Field(
        default=(), max_length=64
    )
    table_label: ShortText | None = None
    drawing_label: ShortText | None = None


class IdentityCandidate(BaseModel):
    """Proposed manufacturer, device and package. Unknown stays unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manufacturer: ShortText | None = None
    base_device: ShortText | None = None
    orderable_part_number: ShortText | None = None
    package_code: ShortText | None = None
    package_description: ShortText | None = None
    pin_count: int | None = Field(default=None, ge=1, le=2000)
    document_revision: ShortText | None = None
    drawing_number: ShortText | None = None
    locators: tuple[SourceLocator, ...] = Field(default=(), max_length=16)
    unresolved: tuple[ShortText, ...] = Field(default=(), max_length=16)


class PhysicalConstraintCandidate(BaseModel):
    """A proposed mechanical dimension, bound to a symbol, column and feature."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: Identifier
    kind: DimensionKind
    dimension_symbol: Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9]{0,7}$")]
    row_label: ShortText
    limit: LimitColumn
    value: LengthValue
    basic_dimension: bool = False
    applies_to_terminals: int | None = Field(default=None, ge=1, le=2000)
    locator: SourceLocator
    notes: tuple[ShortText, ...] = Field(default=(), max_length=8)


class TerminalKind(StrEnum):
    ELECTRICAL = "electrical"
    NO_CONNECT = "no_connect"
    EXPOSED_PAD = "exposed_pad"
    MECHANICAL = "mechanical"


class PinCandidate(BaseModel):
    """A proposed row of a pin function table, for one named package column."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: Identifier
    package_column: ShortText
    pin_number: Annotated[str, StringConstraints(pattern=r"^[A-Z]?\d{1,4}$")]
    symbol: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_+\-/]{1,16}$")]
    function: ShortText
    kind: TerminalKind = TerminalKind.ELECTRICAL
    locator: SourceLocator
    notes: tuple[ShortText, ...] = Field(default=(), max_length=8)


class PadOrderingCandidate(BaseModel):
    """Proposed pad ordering read off a land-pattern or outline drawing.

    Ordering is topology, not dimension. A drawing may be explicitly not to
    scale, so this carries the traversal and the pin numbers whose printed
    labels anchor it, never distances.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: Identifier
    traversal: Literal["counter_clockwise_from_pin_1", "clockwise_from_pin_1"]
    first_pin_corner: Literal["bottom_left", "top_left", "bottom_right", "top_right"]
    labelled_pins: tuple[Annotated[str, StringConstraints(pattern=r"^\d{1,4}$")], ...] = Field(
        min_length=1, max_length=64
    )
    locator: SourceLocator


class ExtractionProposal(BaseModel):
    """Everything one provider call may return. Bounded, and evidence-free.

    Bounds are cost and blast-radius controls, not style: an unbounded list is
    how a malformed or adversarial response turns into unbounded downstream
    work.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity: IdentityCandidate
    dimensions: tuple[PhysicalConstraintCandidate, ...] = Field(default=(), max_length=64)
    pins: tuple[PinCandidate, ...] = Field(default=(), max_length=256)
    pad_ordering: PadOrderingCandidate | None = None
    unresolved: tuple[ShortText, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def _unique_candidate_ids(self) -> ExtractionProposal:
        ids = [c.candidate_id for c in self.dimensions] + [c.candidate_id for c in self.pins]
        if self.pad_ordering is not None:
            ids.append(self.pad_ordering.candidate_id)
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique within one proposal")
        return self


PROPOSAL_SCHEMAS: tuple[type[BaseModel], ...] = (
    SourceRegion,
    SourceLocator,
    IdentityCandidate,
    PhysicalConstraintCandidate,
    PinCandidate,
    PadOrderingCandidate,
    ExtractionProposal,
)


def assert_proposal_schema_is_untrusted(schema: type[BaseModel]) -> None:
    """Raise if a provider-facing schema could carry a verdict or a path.

    Called by the architecture tests over every member of
    :data:`PROPOSAL_SCHEMAS`, so adding a field named ``status`` to a candidate
    is a test failure the moment it is written.
    """
    for name in schema.model_fields:
        if name.casefold() in FORBIDDEN_PROPOSAL_FIELDS:
            raise ValueError(
                f"{schema.__name__}.{name} is a verdict/identity field a provider must never supply"
            )
    if schema.model_config.get("extra") != "forbid":
        raise ValueError(f"{schema.__name__} must forbid extra fields")


# ---------------------------------------------------------------------------
# Deterministic verification receipts
# ---------------------------------------------------------------------------


class ReceiptOutcome(StrEnum):
    """Outcome of one deterministic check. There are four, and three fail closed."""

    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    NOT_LOCATED = "not_located"
    UNSUPPORTED_SOURCE = "unsupported_source"


class VerificationReceipt(BaseModel):
    """What a deterministic checker measured, and against which exact bytes.

    Constructed only by deterministic checking code. It records the checker and
    its version so that a later rule change makes old receipts visibly historical
    instead of silently current.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    receipt_id: Identifier
    checker: Annotated[str, StringConstraints(pattern=r"^CS-[A-Z]+(-[A-Z0-9]+)?$")]
    checker_version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
    outcome: ReceiptOutcome
    candidate_id: Identifier | None = None
    claim_hash: Sha256
    document_digest: Sha256
    observation_digest: Sha256
    page: int | None = Field(default=None, ge=1, le=2000)
    located_region: SourceRegion | None = None
    measured: ShortText | None = None
    expected: ShortText | None = None
    reasons: tuple[ShortText, ...] = Field(default=(), max_length=16)
    limitations: tuple[ShortText, ...] = Field(default=(), max_length=16)
    #: For a receipt that relates several checked claims -- an arithmetic
    #: cross-check -- the claim hashes of every operand. A relation that did not
    #: name what it related would survive a change to any of them.
    bound_claims: dict[str, Sha256] | None = None

    @property
    def supported(self) -> bool:
        return self.outcome is ReceiptOutcome.SUPPORTED


def claim_hash(payload: Any) -> str:
    """Stable digest of exactly what was checked.

    Any JSON-serialisable claim hashes the same way, so a receipt cannot be
    reattached to a claim that differs by one digit.
    """
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


#: Version of the checked-claim payload shapes below, and of the deterministic
#: rules allowed to produce receipts against them. Every receipt carries it and
#: :class:`VerifiedConstraintSet` refuses any receipt that does not match, so a
#: rule change makes old receipts visibly historical instead of silently
#: current. The checker asserts its own version equals this at import time.
CHECKER_CONTRACT_VERSION = "2.0.0"


# ---------------------------------------------------------------------------
# Canonical checked-claim payloads
# ---------------------------------------------------------------------------
#
# These exist because a receipt that merely *exists* proves nothing. Each
# payload is built from exactly the semantic facts that survive into the
# verified constraint set, so the set can recompute the hash and refuse a value
# that was edited after it was checked. The deterministic checker builds the
# same payloads when it issues the receipt; there is one definition, here, and
# both sides use it.


def dimension_claim(
    *,
    kind: DimensionKind,
    dimension_symbol: str,
    limit: LimitColumn,
    value: LengthValue,
    basic_dimension: bool,
    applies_to_terminals: int | None,
) -> dict:
    return {
        "claim": "dimension",
        "kind": kind.value,
        "dimension_symbol": dimension_symbol,
        "limit": limit.value,
        "nanometres": value.nanometres,
        "source_text": value.source_text,
        "unit": value.unit.value,
        "basic_dimension": basic_dimension,
        "applies_to_terminals": applies_to_terminals,
    }


def terminal_claim(
    *,
    package_column: str,
    pin_number: str,
    symbol: str,
    function: str,
    kind: TerminalKind,
) -> dict:
    return {
        "claim": "terminal",
        "package_column": package_column,
        "pin_number": pin_number,
        "symbol": symbol,
        "function": function,
        "kind": kind.value,
    }


def identity_claim(
    *,
    manufacturer: str,
    base_device: str,
    orderable_part_number: str,
    package_code: str,
    package_description: str,
    pin_count: int,
    document_revision: str,
    drawing_number: str,
) -> dict:
    return {
        "claim": "identity",
        "manufacturer": manufacturer,
        "base_device": base_device,
        "orderable_part_number": orderable_part_number,
        "package_code": package_code,
        "package_description": package_description,
        "pin_count": pin_count,
        "document_revision": document_revision,
        "drawing_number": drawing_number,
    }


def pad_ordering_claim(
    *,
    traversal: str,
    first_pin_corner: str,
    slots: tuple[PadSlot, ...],
) -> dict:
    return {
        "claim": "pad_ordering",
        "traversal": traversal,
        "first_pin_corner": first_pin_corner,
        "slots": [
            [slot.pin_number, slot.row, slot.column]
            for slot in sorted(slots, key=lambda item: int(item.pin_number))
        ],
    }


def relation_claim(
    *, relation: str, result_claim: str, left_claim: str, right_claim: str, expected_nm: int
) -> dict:
    """An arithmetic relation binds the claim hashes of all three operands.

    Without the operand hashes a relation receipt would survive a change to any
    of the values it related, which is the same defect one layer up.
    """
    return {
        "claim": "relation",
        "relation": relation,
        "result_claim": result_claim,
        "left_claim": left_claim,
        "right_claim": right_claim,
        "expected_nm": expected_nm,
    }


# ---------------------------------------------------------------------------
# Verified constraints: the only thing CAD generation is allowed to read
# ---------------------------------------------------------------------------


class VerifiedDimension(BaseModel):
    """A dimension that passed deterministic source checking, with its receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: DimensionKind
    dimension_symbol: str
    limit: LimitColumn
    value: LengthValue
    basic_dimension: bool
    applies_to_terminals: int | None = Field(default=None, ge=1, le=2000)
    receipt_id: Identifier

    def claim(self) -> dict:
        return dimension_claim(
            kind=self.kind, dimension_symbol=self.dimension_symbol, limit=self.limit,
            value=self.value, basic_dimension=self.basic_dimension,
            applies_to_terminals=self.applies_to_terminals,
        )


class VerifiedTerminal(BaseModel):
    """One checked electrical terminal of the selected package."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_column: ShortText
    pin_number: str
    symbol: str
    function: ShortText
    kind: TerminalKind
    receipt_id: Identifier

    def claim(self) -> dict:
        return terminal_claim(
            package_column=self.package_column, pin_number=self.pin_number,
            symbol=self.symbol, function=self.function, kind=self.kind,
        )


class PadSlot(BaseModel):
    """Which row and pitch-grid column one pin occupies.

    Slots are *topology*: which lands exist and how they line up with each
    other. Every distance comes from the dimension table. A drawing may be
    explicitly not to scale, so nothing here is measured off it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pin_number: str
    row: int = Field(ge=0, le=15)
    column: int = Field(ge=0, le=255)


class VerifiedPadOrdering(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    traversal: Literal["counter_clockwise_from_pin_1", "clockwise_from_pin_1"]
    first_pin_corner: Literal["bottom_left", "top_left", "bottom_right", "top_right"]
    slots: tuple[PadSlot, ...] = Field(min_length=1, max_length=256)
    receipt_id: Identifier

    @model_validator(mode="after")
    def _slots_are_distinct(self) -> VerifiedPadOrdering:
        pins = [slot.pin_number for slot in self.slots]
        if len(pins) != len(set(pins)):
            raise ValueError("duplicate pin in pad ordering")
        positions = [(slot.row, slot.column) for slot in self.slots]
        if len(positions) != len(set(positions)):
            raise ValueError("two pins occupy one pad slot")
        return self

    def claim(self) -> dict:
        return pad_ordering_claim(
            traversal=self.traversal, first_pin_corner=self.first_pin_corner, slots=self.slots,
        )

    @property
    def row_count(self) -> int:
        return max(slot.row for slot in self.slots) + 1

    @property
    def column_count(self) -> int:
        return max(slot.column for slot in self.slots) + 1

    def row_occupancy(self) -> tuple[tuple[str, ...], ...]:
        """Pin numbers per row, ordered by column. Row 0 holds pin 1."""
        return tuple(
            tuple(
                slot.pin_number
                for slot in sorted(self.slots, key=lambda item: item.column)
                if slot.row == row
            )
            for row in range(self.row_count)
        )


class VerifiedIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manufacturer: ShortText
    base_device: ShortText
    orderable_part_number: ShortText
    package_code: ShortText
    package_description: ShortText
    pin_count: int = Field(ge=1, le=2000)
    document_revision: ShortText
    drawing_number: ShortText
    receipt_id: Identifier

    def claim(self) -> dict:
        return identity_claim(
            manufacturer=self.manufacturer, base_device=self.base_device,
            orderable_part_number=self.orderable_part_number,
            package_code=self.package_code, package_description=self.package_description,
            pin_count=self.pin_count, document_revision=self.document_revision,
            drawing_number=self.drawing_number,
        )


class VerifiedConstraintSet(BaseModel):
    """The complete, checked input to deterministic CAD generation.

    Construction requires that every part of it names a supporting receipt and
    that every named receipt is ``SUPPORTED``. That is the mechanical form of
    "matching a footprint to model-produced JSON proves consistency with that
    JSON": CAD never sees a candidate, only this.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_digest: Sha256
    observation_digest: Sha256
    identity: VerifiedIdentity
    dimensions: tuple[VerifiedDimension, ...] = Field(min_length=1, max_length=64)
    terminals: tuple[VerifiedTerminal, ...] = Field(min_length=1, max_length=256)
    pad_ordering: VerifiedPadOrdering
    receipts: tuple[VerificationReceipt, ...] = Field(min_length=1, max_length=512)
    limitations: tuple[ShortText, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def _every_claim_has_a_supporting_receipt(self) -> VerifiedConstraintSet:
        by_id = {receipt.receipt_id: receipt for receipt in self.receipts}
        if len(by_id) != len(self.receipts):
            raise ValueError("duplicate receipt IDs")
        # Each accepted value recomputes its own canonical claim payload and must
        # match the hash its receipt recorded. Without this, a set can be
        # serialised, edited, and revalidated with the original receipts still
        # attached -- which is exactly how a 1.10 mm pad length became 0.60 mm
        # while every receipt still said "supported".
        bound: list[tuple[str, dict]] = [
            (self.identity.receipt_id, self.identity.claim()),
            (self.pad_ordering.receipt_id, self.pad_ordering.claim()),
        ]
        bound += [(item.receipt_id, item.claim()) for item in self.dimensions]
        bound += [(item.receipt_id, item.claim()) for item in self.terminals]
        for receipt_id, payload in bound:
            receipt = by_id.get(receipt_id)
            if receipt is None:
                raise ValueError(f"verified constraint references unknown receipt {receipt_id!r}")
            if not receipt.supported:
                raise ValueError(
                    f"receipt {receipt_id!r} is {receipt.outcome.value}; "
                    "an unsupported claim cannot enter a verified constraint set"
                )
            if receipt.document_digest != self.document_digest:
                raise ValueError(f"receipt {receipt_id!r} checked a different document")
            if receipt.observation_digest != self.observation_digest:
                raise ValueError(f"receipt {receipt_id!r} checked different observations")
            expected = claim_hash(payload)
            if receipt.claim_hash != expected:
                raise ValueError(
                    f"receipt {receipt_id!r} does not describe the value it is attached to: "
                    f"it recorded claim {receipt.claim_hash[:16]}, this value hashes "
                    f"{expected[:16]}"
                )
        for receipt in self.receipts:
            if receipt.checker_version != CHECKER_CONTRACT_VERSION:
                raise ValueError(
                    f"receipt {receipt.receipt_id!r} was produced by checker version "
                    f"{receipt.checker_version}, not the current "
                    f"{CHECKER_CONTRACT_VERSION}; it is historical, not current"
                )
            if receipt.document_digest != self.document_digest:
                raise ValueError(f"receipt {receipt.receipt_id!r} checked a different document")
            if receipt.observation_digest != self.observation_digest:
                raise ValueError(
                    f"receipt {receipt.receipt_id!r} checked different observations"
                )
        # Arithmetic receipts bind their operands' claim hashes, so a relation
        # cannot survive a change to any value it related.
        known_claims = {claim_hash(payload) for _, payload in bound}
        for receipt in self.receipts:
            if receipt.checker != "CS-SOURCE-CONSISTENCY":
                continue
            for field in ("result_claim", "left_claim", "right_claim"):
                referenced_claim = (receipt.bound_claims or {}).get(field)
                if referenced_claim is None:
                    raise ValueError(
                        f"relation receipt {receipt.receipt_id!r} does not name its {field}"
                    )
                if referenced_claim not in known_claims:
                    raise ValueError(
                        f"relation receipt {receipt.receipt_id!r} relates a value that is not "
                        "in this verified constraint set"
                    )
        numbers = [terminal.pin_number for terminal in self.terminals]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate terminal pin numbers")
        ordered = [slot.pin_number for slot in self.pad_ordering.slots]
        if sorted(ordered) != sorted(numbers):
            raise ValueError("pad ordering and verified terminals describe different pins")
        symbols = {(d.kind, d.dimension_symbol, d.limit) for d in self.dimensions}
        if len(symbols) != len(self.dimensions):
            raise ValueError("duplicate verified dimension")
        return self

    def revalidate(self) -> tuple[str, ...]:
        """Recompute every receipt binding and report what no longer holds.

        Construction already enforces this, but a checker that *trusts* a model
        it was handed is trusting whoever built it. Callers at a use boundary
        run this so the binding is re-established at the point of use, not
        inherited from a constructor that ran somewhere else.
        """
        try:
            VerifiedConstraintSet.model_validate(self.model_dump(mode="json"))
        except ValueError as exc:
            return (str(exc)[:400],)
        return ()

    def dimension(self, kind: DimensionKind) -> VerifiedDimension | None:
        return next((item for item in self.dimensions if item.kind is kind), None)

    def require(self, kind: DimensionKind) -> VerifiedDimension:
        found = self.dimension(kind)
        if found is None:
            raise KeyError(f"no verified {kind.value}; a missing dimension stays missing")
        return found

    @property
    def content_hash(self) -> str:
        return claim_hash(self)


# ---------------------------------------------------------------------------
# Capability matrix and import lifecycle
# ---------------------------------------------------------------------------


class CapabilityState(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"
    NOT_EVALUATED = "not_evaluated"


class Capability(StrEnum):
    IDENTITY = "identity_supported"
    SYMBOL = "symbol_supported"
    FOOTPRINT = "footprint_supported"
    ELECTRICAL_PROFILE = "electrical_profile_supported"
    ROUTING = "routing_supported"
    SIMULATION = "simulation_supported"


class CapabilityResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: Capability
    state: CapabilityState
    reasons: tuple[ShortText, ...] = Field(default=(), max_length=16)
    limitations: tuple[ShortText, ...] = Field(default=(), max_length=16)


class CapabilityMatrix(BaseModel):
    """Per-capability support. Absence of a result is never support.

    Separating capability from lifecycle is the point: a part whose footprint is
    proved and whose behaviour is unknown has one supported capability and
    several unsupported ones, not a single ``verified`` flag.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    results: tuple[CapabilityResult, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def _one_result_per_capability(self) -> CapabilityMatrix:
        seen = [result.capability for result in self.results]
        if len(seen) != len(set(seen)):
            raise ValueError("duplicate capability result")
        return self

    def state(self, capability: Capability) -> CapabilityState:
        for result in self.results:
            if result.capability is capability:
                return result.state
        return CapabilityState.NOT_EVALUATED

    def supports(self, capability: Capability) -> bool:
        return self.state(capability) is CapabilityState.SUPPORTED


class ImportState(StrEnum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    CANDIDATES_READY = "candidates_ready"
    VERIFYING_SOURCE = "verifying_source"
    NEEDS_REVIEW = "needs_review"
    GENERATING_ASSETS = "generating_assets"
    VERIFYING_ASSETS = "verifying_assets"
    ADMITTED = "admitted"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


#: Allowed transitions of the import state machine. Admission is reachable only
#: through asset verification, so no path skips a gate.
IMPORT_TRANSITIONS: dict[ImportState, frozenset[ImportState]] = {
    ImportState.RECEIVED: frozenset({ImportState.EXTRACTING, ImportState.FAILED,
                                     ImportState.CANCELLED}),
    ImportState.EXTRACTING: frozenset({ImportState.CANDIDATES_READY, ImportState.FAILED,
                                       ImportState.CANCELLED}),
    ImportState.CANDIDATES_READY: frozenset({ImportState.VERIFYING_SOURCE, ImportState.FAILED,
                                             ImportState.CANCELLED}),
    ImportState.VERIFYING_SOURCE: frozenset({ImportState.GENERATING_ASSETS,
                                             ImportState.NEEDS_REVIEW, ImportState.REJECTED,
                                             ImportState.FAILED, ImportState.CANCELLED}),
    ImportState.NEEDS_REVIEW: frozenset({ImportState.VERIFYING_SOURCE, ImportState.REJECTED,
                                         ImportState.CANCELLED}),
    ImportState.GENERATING_ASSETS: frozenset({ImportState.VERIFYING_ASSETS, ImportState.FAILED,
                                              ImportState.CANCELLED}),
    ImportState.VERIFYING_ASSETS: frozenset({ImportState.ADMITTED, ImportState.REJECTED,
                                             ImportState.FAILED, ImportState.CANCELLED}),
    ImportState.ADMITTED: frozenset(),
    ImportState.REJECTED: frozenset(),
    ImportState.FAILED: frozenset(),
    ImportState.CANCELLED: frozenset(),
}


def can_transition(current: ImportState, target: ImportState) -> bool:
    return target in IMPORT_TRANSITIONS[current]


class SourceOriginKind(StrEnum):
    """How the exact source bytes reached the workspace.

    ``MANUFACTURER_HTTPS`` records an observed manufacturer distribution source.
    It is not a cryptographic guarantee of silicon identity, and the field name
    is the honest one on purpose.
    """

    MANUFACTURER_HTTPS = "manufacturer_https"
    SUPPLIED_UNVERIFIED = "supplied_unverified"


class SourceOrigin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: SourceOriginKind
    acquisition_url: Annotated[str, StringConstraints(max_length=1000)] | None = None
    redirect_chain: tuple[Annotated[str, StringConstraints(max_length=1000)], ...] = Field(
        default=(), max_length=16
    )
    acquired_at: ShortText | None = None
    note: ShortText | None = None

    @model_validator(mode="after")
    def _https_origin_names_its_url(self) -> SourceOrigin:
        if self.kind is SourceOriginKind.MANUFACTURER_HTTPS:
            if not self.acquisition_url or not self.acquisition_url.startswith("https://"):
                raise ValueError("a manufacturer HTTPS origin must record its https:// URL")
            for target in self.redirect_chain:
                if not target.startswith("https://"):
                    raise ValueError("redirect destinations must stay on HTTPS")
        return self


class ComponentImportRequest(BaseModel):
    """One import: one exact package of one device from named documents."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    import_id: Identifier
    workspace: Identifier
    requested_identity: IdentityCandidate
    document_digests: tuple[Sha256, ...] = Field(min_length=1, max_length=8)
    requested_capabilities: tuple[Capability, ...] = Field(min_length=1, max_length=8)
    origin: SourceOrigin
    max_pages: int = Field(default=64, ge=1, le=500)
    max_provider_attempts: int = Field(default=2, ge=1, le=5)


__all__ = [
    "CHECKER_CONTRACT_VERSION",
    "FORBIDDEN_PROPOSAL_FIELDS",
    "GRID_EPSILON_NM",
    "IMPORT_TRANSITIONS",
    "LAND_DIMENSION_KINDS",
    "NANOMETRES_PER_INCH",
    "NANOMETRES_PER_MIL",
    "NANOMETRES_PER_MM",
    "PROPOSAL_SCHEMAS",
    "Capability",
    "CapabilityMatrix",
    "CapabilityResult",
    "CapabilityState",
    "ComponentImportRequest",
    "DimensionKind",
    "ExtractionProposal",
    "IdentityCandidate",
    "ImportState",
    "LengthValue",
    "LimitColumn",
    "PadOrderingCandidate",
    "PadSlot",
    "PhysicalConstraintCandidate",
    "PinCandidate",
    "ReceiptOutcome",
    "SourceLocator",
    "SourceOrigin",
    "SourceOriginKind",
    "SourceRegion",
    "SourceUnit",
    "TerminalKind",
    "VerificationReceipt",
    "VerifiedConstraintSet",
    "VerifiedDimension",
    "VerifiedIdentity",
    "VerifiedPadOrdering",
    "VerifiedTerminal",
    "assert_proposal_schema_is_untrusted",
    "can_transition",
    "claim_hash",
    "dimension_claim",
    "identity_claim",
    "pad_ordering_claim",
    "relation_claim",
    "terminal_claim",
]
