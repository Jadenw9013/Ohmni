"""Deterministic land patterns and symbols from verified source constraints.

Pure geometry on the integer nanometre grid. The only input is a
:class:`~ohmni.domain.component_synthesis.VerifiedConstraintSet`, which by
construction contains nothing a provider proposed and nothing a deterministic
checker refused. There is no path from a candidate to a pad here.

What this module deliberately does not do is as important as what it does:

* **It does not derive lands from package terminals.** The only implemented
  method is ``manufacturer_recommended_table``. Deriving a land from a lead size
  needs a separately validated policy and all its tolerance inputs; without
  them, the method returns unsupported rather than guessing.
* **It does not invent a body.** This slice reads the recommended land table.
  Package body and lead dimensions were not read, so no silkscreen body outline
  and no fabrication body rectangle is emitted, and the limitation says so. A
  convenient rectangle drawn where the body probably is would be geometry the
  document never stated.
* **It does not claim IPC anything.** The courtyard here is the verified land
  extent plus one declared, policy-versioned margin. That is not an IPC-7351 or
  IPC-7352 courtyard excess, and :attr:`LandPatternDefinition.limitations` says
  so in the artifact itself.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ..domain.component_synthesis import (
    NANOMETRES_PER_MM,
    Capability,
    CapabilityMatrix,
    CapabilityResult,
    CapabilityState,
    DimensionKind,
    VerifiedConstraintSet,
)

#: Bump on any change to the geometry these functions produce. Manifests carry
#: it, so a regenerated asset is never confused with one built by older rules.
POLICY_VERSION = "1.0.0"

#: The dimensions a manufacturer-recommended land pattern cannot be built
#: without. A missing one blocks the footprint capability; it is never defaulted.
REQUIRED_LAND_DIMENSIONS = frozenset({
    DimensionKind.LAND_PAD_WIDTH,
    DimensionKind.LAND_PAD_LENGTH,
    DimensionKind.LAND_CONTACT_PITCH,
    DimensionKind.LAND_ROW_SPACING,
})

#: Declared policy margin between the verified land extent and the courtyard.
#: Not an IPC courtyard excess: this slice has no verified package body, so the
#: only honest courtyard is "the copper we know about, plus a stated margin".
COURTYARD_MARGIN_NM = 250_000
#: Silkscreen pin-1 dot: radius, and clearance from the nearest solderable edge.
PIN1_MARKER_RADIUS_NM = 125_000
PIN1_MARKER_CLEARANCE_NM = 250_000
#: Symbol geometry, on KiCad's 1.27 mm grid in nanometres.
SYMBOL_PIN_PITCH_NM = 2_540_000
SYMBOL_PIN_LENGTH_NM = 2_540_000
SYMBOL_HALF_WIDTH_NM = 7_620_000


class LandPatternMethod(StrEnum):
    """How a land pattern was derived. Only one method is implemented."""

    MANUFACTURER_RECOMMENDED_TABLE = "manufacturer_recommended_table"
    #: Reserved and unimplemented. Returned as unsupported, never silently used.
    STANDARDS_DERIVED = "standards_derived"


class LandPatternError(ValueError):
    """The verified constraints do not support a land pattern under this policy."""


class LandPad(BaseModel):
    """One copper land, on the integer nanometre grid."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: Annotated[str, StringConstraints(pattern=r"^[A-Z]?\d{1,4}$")]
    centre_x_nm: int
    centre_y_nm: int
    width_nm: int = Field(gt=0)
    height_nm: int = Field(gt=0)
    shape: Literal["rect", "roundrect"] = "roundrect"
    roundrect_ratio: float = Field(default=0.25, ge=0, le=0.5)

    @property
    def x0_nm(self) -> int:
        return self.centre_x_nm - self.width_nm // 2

    @property
    def x1_nm(self) -> int:
        return self.centre_x_nm + self.width_nm // 2

    @property
    def y0_nm(self) -> int:
        return self.centre_y_nm - self.height_nm // 2

    @property
    def y1_nm(self) -> int:
        return self.centre_y_nm + self.height_nm // 2


class Rectangle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    x0_nm: int
    y0_nm: int
    x1_nm: int
    y1_nm: int

    @model_validator(mode="after")
    def _ordered(self) -> Rectangle:
        if self.x1_nm <= self.x0_nm or self.y1_nm <= self.y0_nm:
            raise ValueError("rectangle must have positive extent")
        return self


class Circle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    centre_x_nm: int
    centre_y_nm: int
    radius_nm: int = Field(gt=0)


class LandPatternDefinition(BaseModel):
    """A complete footprint in Ohmni's own terms, before any file format."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    method: LandPatternMethod
    policy_version: str
    constraint_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    description: Annotated[str, StringConstraints(max_length=400)]
    pads: tuple[LandPad, ...] = Field(min_length=1, max_length=256)
    courtyard: Rectangle
    pin1_marker: Circle
    limitations: tuple[str, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def _distinct_pads(self) -> LandPatternDefinition:
        numbers = [pad.number for pad in self.pads]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate land number")
        return self

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def extent(self) -> Rectangle:
        return Rectangle(
            x0_nm=min(pad.x0_nm for pad in self.pads),
            y0_nm=min(pad.y0_nm for pad in self.pads),
            x1_nm=max(pad.x1_nm for pad in self.pads),
            y1_nm=max(pad.y1_nm for pad in self.pads),
        )


class SymbolPin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    number: Annotated[str, StringConstraints(pattern=r"^[A-Z]?\d{1,4}$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    #: KiCad's own vocabulary. ``unspecified`` is the honest value until the
    #: electrical profile gate runs; see :func:`build_symbol`.
    electrical_type: Literal["unspecified"] = "unspecified"
    x_nm: int
    y_nm: int
    orientation_deg: Literal[0, 180] = 0
    length_nm: int = Field(gt=0)


class SymbolDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    reference_prefix: Annotated[str, StringConstraints(min_length=1, max_length=4)]
    value: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    description: Annotated[str, StringConstraints(max_length=400)]
    datasheet_note: Annotated[str, StringConstraints(max_length=200)]
    body: Rectangle
    pins: tuple[SymbolPin, ...] = Field(min_length=1, max_length=256)
    policy_version: str
    constraint_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    limitations: tuple[str, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def _distinct_pins(self) -> SymbolDefinition:
        numbers = [pin.number for pin in self.pins]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate symbol pin number")
        return self

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def asset_base_name(verified: VerifiedConstraintSet) -> str:
    """A stable, path-safe identity for the generated pair."""
    identity = verified.identity
    safe = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in f"{identity.base_device}_{identity.package_code}"
    )
    return f"Ohmni_{safe}"


def build_land_pattern(
    verified: VerifiedConstraintSet,
    *,
    method: LandPatternMethod = LandPatternMethod.MANUFACTURER_RECOMMENDED_TABLE,
) -> LandPatternDefinition:
    """Compile verified recommended-land dimensions into exact copper geometry.

    Every coordinate is integer nanometres derived from the printed decimals. A
    position that would not land exactly on the grid raises rather than rounding:
    a half-nanometre of silent rounding in a pitch is a real defect at the
    hundredth pad, and there is no reason to accept one here.
    """
    if method is not LandPatternMethod.MANUFACTURER_RECOMMENDED_TABLE:
        raise LandPatternError(
            f"{method.value} is not implemented; it needs its own validated policy, "
            "authorised standard access and tolerance inputs"
        )
    missing = sorted(
        kind.value for kind in REQUIRED_LAND_DIMENSIONS if verified.dimension(kind) is None
    )
    if missing:
        raise LandPatternError(f"verified constraints are missing: {', '.join(missing)}")

    pitch = verified.require(DimensionKind.LAND_CONTACT_PITCH).value.nanometres
    spacing = verified.require(DimensionKind.LAND_ROW_SPACING).value.nanometres
    width = verified.require(DimensionKind.LAND_PAD_WIDTH).value.nanometres
    length = verified.require(DimensionKind.LAND_PAD_LENGTH).value.nanometres

    ordering = verified.pad_ordering
    if ordering.row_count != 2:
        raise LandPatternError(
            f"{ordering.row_count} land rows; this policy implements two-row packages only"
        )
    if spacing % 2:
        raise LandPatternError("row spacing is not an exact whole number of half-nanometres")
    columns = ordering.column_count
    pads: list[LandPad] = []
    for slot in sorted(ordering.slots, key=lambda item: int(item.pin_number)):
        half_steps = 2 * slot.column - (columns - 1)
        product = half_steps * pitch
        if product % 2:
            raise LandPatternError(
                "the pitch does not place an even column count on the nanometre grid"
            )
        # Row 0 is the row carrying the printed pin-1 label. KiCad footprint Y
        # grows downward, matching the drawing's own orientation, so row 0 sits
        # at +spacing/2 and the opposite row at -spacing/2.
        pads.append(LandPad(
            number=slot.pin_number,
            centre_x_nm=product // 2,
            centre_y_nm=(spacing // 2) if slot.row == 0 else -(spacing // 2),
            width_nm=width,
            height_nm=length,
        ))

    x0 = min(pad.x0_nm for pad in pads) - COURTYARD_MARGIN_NM
    y0 = min(pad.y0_nm for pad in pads) - COURTYARD_MARGIN_NM
    x1 = max(pad.x1_nm for pad in pads) + COURTYARD_MARGIN_NM
    y1 = max(pad.y1_nm for pad in pads) + COURTYARD_MARGIN_NM
    pin_one = next(pad for pad in pads if pad.number == "1")
    marker = Circle(
        centre_x_nm=pin_one.centre_x_nm
        - (pin_one.width_nm // 2 + PIN1_MARKER_CLEARANCE_NM + PIN1_MARKER_RADIUS_NM),
        centre_y_nm=pin_one.centre_y_nm,
        radius_nm=PIN1_MARKER_RADIUS_NM,
    )
    courtyard = Rectangle(
        x0_nm=min(x0, marker.centre_x_nm - marker.radius_nm - COURTYARD_MARGIN_NM),
        y0_nm=y0, x1_nm=x1, y1_nm=y1,
    )
    identity = verified.identity
    return LandPatternDefinition(
        name=f"{asset_base_name(verified)}_{len(pads)}",
        method=method,
        policy_version=POLICY_VERSION,
        constraint_hash=verified.content_hash,
        description=(
            f"{identity.manufacturer} {identity.base_device} {identity.package_description}; "
            f"recommended land pattern from drawing {identity.drawing_number}"
        )[:400],
        pads=tuple(pads),
        courtyard=courtyard,
        pin1_marker=marker,
        limitations=(
            ("Geometry conforms to the manufacturer recommended land table only. "
             "IPC-7351/IPC-7352 compliance is NOT established."),
            ("Solder joint reliability, paste volume, stencil design and thermal "
             "performance are NOT established."),
            ("No package body or silkscreen outline is emitted: this import read the "
             "recommended land table, and body dimensions were not read."),
            (f"The courtyard is the verified land extent plus a declared "
             f"{COURTYARD_MARGIN_NM / NANOMETRES_PER_MM:.2f} mm policy margin, not a "
             "standards-derived courtyard excess."),
        ),
    )


def build_symbol(verified: VerifiedConstraintSet) -> SymbolDefinition:
    """Compile verified terminals into a schematic symbol.

    Every pin is emitted as ``unspecified``. The source checks established the
    printed pin name and function text; they established no electrical
    behaviour, and COMPONENT_SYNTHESIS_PLAN.md forbids a passive or power
    fallback chosen to make ERC quieter. The electrical type becomes real only
    at the CS-T07 electrical-profile gate, and the limitation says so.
    """
    ordering = verified.pad_ordering
    rows = ordering.row_occupancy()
    if len(rows) != 2:
        raise LandPatternError("this symbol policy implements two-row packages only")
    by_number = {terminal.pin_number: terminal for terminal in verified.terminals}
    left, right = rows[0], tuple(reversed(rows[1]))
    height_steps = max(len(left), len(right))
    # A whole number of pitches, so every pin lands on KiCad's 2.54 mm pin grid.
    # Centring an even pin count would put every pin on a half pitch, which
    # schematic ERC reports as an off-grid endpoint.
    top = ((height_steps - 1) // 2) * SYMBOL_PIN_PITCH_NM
    pins: list[SymbolPin] = []
    for index, number in enumerate(left):
        pins.append(SymbolPin(
            number=number, name=by_number[number].symbol,
            x_nm=-SYMBOL_HALF_WIDTH_NM, y_nm=top - index * SYMBOL_PIN_PITCH_NM,
            orientation_deg=0, length_nm=SYMBOL_PIN_LENGTH_NM,
        ))
    for index, number in enumerate(right):
        pins.append(SymbolPin(
            number=number, name=by_number[number].symbol,
            x_nm=SYMBOL_HALF_WIDTH_NM, y_nm=top - index * SYMBOL_PIN_PITCH_NM,
            orientation_deg=180, length_nm=SYMBOL_PIN_LENGTH_NM,
        ))
    body_half_height = top + SYMBOL_PIN_PITCH_NM
    identity = verified.identity
    return SymbolDefinition(
        name=asset_base_name(verified),
        reference_prefix="U",
        value=identity.base_device,
        description=(
            f"{identity.manufacturer} {identity.base_device}, "
            f"{identity.package_description}. Pin names and functions are source-checked; "
            "electrical types are not yet established."
        )[:400],
        datasheet_note=f"{identity.manufacturer} document revision {identity.document_revision}",
        body=Rectangle(
            x0_nm=-(SYMBOL_HALF_WIDTH_NM - SYMBOL_PIN_LENGTH_NM),
            y0_nm=-body_half_height,
            x1_nm=SYMBOL_HALF_WIDTH_NM - SYMBOL_PIN_LENGTH_NM,
            y1_nm=body_half_height,
        ),
        pins=tuple(sorted(pins, key=lambda pin: int(pin.number))),
        policy_version=POLICY_VERSION,
        constraint_hash=verified.content_hash,
        limitations=(
            ("Every pin is emitted with electrical type 'unspecified'. The source checks "
             "established printed names and functions, not electrical behaviour."),
            ("This symbol establishes no operating limit, absolute maximum rating or "
             "internal connection, and no simulation model."),
        ),
    )


def cad_capabilities(
    verified: VerifiedConstraintSet,
    *,
    land_pattern_built: bool,
    symbol_built: bool,
) -> CapabilityMatrix:
    """What this import supports so far. Absence of a result is never support."""
    results = [
        CapabilityResult(
            capability=Capability.IDENTITY,
            state=CapabilityState.SUPPORTED,
            reasons=(f"exact orderable part {verified.identity.orderable_part_number}",),
        ),
        CapabilityResult(
            capability=Capability.FOOTPRINT,
            state=CapabilityState.SUPPORTED if land_pattern_built else CapabilityState.UNSUPPORTED,
            limitations=("Datasheet land conformance only; not IPC compliance.",),
        ),
        CapabilityResult(
            capability=Capability.SYMBOL,
            state=CapabilityState.SUPPORTED if symbol_built else CapabilityState.UNSUPPORTED,
            limitations=("Pin electrical types are unspecified until the electrical gate.",),
        ),
        CapabilityResult(
            capability=Capability.ELECTRICAL_PROFILE,
            state=CapabilityState.NOT_EVALUATED,
            reasons=("the electrical profile gate is CS-T07 and has not run",),
        ),
        CapabilityResult(
            capability=Capability.ROUTING,
            state=CapabilityState.NOT_EVALUATED,
            reasons=("board integration is CS-T08 and has not run",),
        ),
        CapabilityResult(
            capability=Capability.SIMULATION,
            state=CapabilityState.UNSUPPORTED,
            reasons=("no model was ingested; the SPICE boundary is CS-T09",),
        ),
    ]
    return CapabilityMatrix(results=tuple(results))


__all__ = [
    "COURTYARD_MARGIN_NM",
    "POLICY_VERSION",
    "REQUIRED_LAND_DIMENSIONS",
    "SYMBOL_HALF_WIDTH_NM",
    "SYMBOL_PIN_LENGTH_NM",
    "SYMBOL_PIN_PITCH_NM",
    "Circle",
    "LandPad",
    "LandPatternDefinition",
    "LandPatternError",
    "LandPatternMethod",
    "Rectangle",
    "SymbolDefinition",
    "SymbolPin",
    "asset_base_name",
    "build_land_pattern",
    "build_symbol",
    "cad_capabilities",
]
