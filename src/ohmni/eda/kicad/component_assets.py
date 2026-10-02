"""Deterministic KiCad 10 footprint and symbol serialization.

Byte-exact output: stable ordering, LF newlines, UTF-8, and a fixed numeric
format. The same verified constraints always produce the same bytes, which is
what lets a manifest bind a component revision to a SHA-256 rather than to
"a footprint that looked right".

Numbers use their own precision policy. The shared :func:`ohmni.eda.kicad.sexpr.number`
formats three decimals, which is right for the existing boards and wrong here:
a land at 1.1375 mm is a real coordinate in KiCad's own libraries, and rounding
it would change the copper. :func:`millimetres` formats from the integer
nanometre grid at six decimals with trailing zeros stripped, and refuses a value
it cannot represent exactly, rather than silently emitting a different pad.

Nothing in this module interprets a datasheet. It receives geometry that has
already been checked and writes it out.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ...domain.component_synthesis import NANOMETRES_PER_MM
from ...physical.land_patterns import (
    Circle,
    LandPatternDefinition,
    Rectangle,
    SymbolDefinition,
)
from .sexpr import quote

#: Emitted format tokens, pinned. A manifest records these beside the tool
#: version that was actually run against the output.
FOOTPRINT_FORMAT_VERSION = "20260206"
SYMBOL_LIB_FORMAT_VERSION = "20251024"
GENERATOR = "ohmni-component-synthesis"
GENERATOR_VERSION = "1.0.0"

#: Line widths, in nanometres, matching KiCad's own library conventions.
SILKSCREEN_WIDTH_NM = 120_000
COURTYARD_WIDTH_NM = 50_000
SYMBOL_BODY_WIDTH_NM = 254_00
TEXT_SIZE_MM = 1.0
TEXT_THICKNESS_MM = 0.15


class AssetSerializationError(ValueError):
    """A value cannot be represented exactly in the emitted format."""


def millimetres(nanometres: int) -> str:
    """Format an exact nanometre value as millimetres, or refuse.

    Six decimals is exactly one nanometre, so every grid value is representable
    and nothing is ever rounded. A non-integer input is a programming error in
    the caller, not something to round away.
    """
    if not isinstance(nanometres, int) or isinstance(nanometres, bool):
        raise AssetSerializationError(f"{nanometres!r} is not an exact nanometre value")
    sign = "-" if nanometres < 0 else ""
    magnitude = abs(nanometres)
    whole, fraction = divmod(magnitude, NANOMETRES_PER_MM)
    if fraction == 0:
        return f"{sign}{whole}"
    text = f"{sign}{whole}.{fraction:06d}".rstrip("0")
    return text


def _effects(indent: str) -> list[str]:
    return [
        f"{indent}(effects",
        f"{indent}\t(font",
        f"{indent}\t\t(size {TEXT_SIZE_MM} {TEXT_SIZE_MM})",
        f"{indent}\t\t(thickness {TEXT_THICKNESS_MM})",
        f"{indent}\t)",
        f"{indent})",
    ]


def render_footprint(definition: LandPatternDefinition) -> str:
    """Serialize a land pattern as a KiCad 10 ``.kicad_mod`` payload."""
    extent = definition.extent()
    lines = [
        f"(footprint {quote(definition.name)}",
        f"\t(version {FOOTPRINT_FORMAT_VERSION})",
        f"\t(generator {quote(GENERATOR)})",
        f"\t(generator_version {quote(GENERATOR_VERSION)})",
        '\t(layer "F.Cu")',
        f"\t(descr {quote(definition.description)})",
        f"\t(tags {quote('ohmni component-synthesis ' + definition.method.value)})",
    ]
    lines += _property("Reference", "REF**", "F.SilkS",
                       0, definition.courtyard.y0_nm - 1_000_000)
    lines += _property("Value", definition.name, "F.Fab",
                       0, definition.courtyard.y1_nm + 1_000_000)
    lines += _property("ohmni_constraint_hash", definition.constraint_hash, "F.Fab", 0, 0,
                       hide=True)
    lines += _property("ohmni_land_pattern_method", definition.method.value, "F.Fab", 0, 0,
                       hide=True)
    lines += _property("ohmni_policy_version", definition.policy_version, "F.Fab", 0, 0, hide=True)
    for index, limitation in enumerate(definition.limitations):
        lines += _property(f"ohmni_limitation_{index + 1}", limitation, "F.Fab", 0, 0, hide=True)
    lines.append("\t(attr smd)")
    lines += _circle(definition.pin1_marker, "F.SilkS", SILKSCREEN_WIDTH_NM)
    lines += _rectangle(definition.courtyard, "F.CrtYd", COURTYARD_WIDTH_NM)
    for pad in definition.pads:
        lines += [
            f"\t(pad {quote(pad.number)} smd {pad.shape}",
            f"\t\t(at {millimetres(pad.centre_x_nm)} {millimetres(pad.centre_y_nm)})",
            f"\t\t(size {millimetres(pad.width_nm)} {millimetres(pad.height_nm)})",
            '\t\t(layers "F.Cu" "F.Mask" "F.Paste")',
            f"\t\t(roundrect_rratio {pad.roundrect_ratio})",
            "\t)",
        ]
    lines.append(")")
    lines.append("")
    _ = extent
    return "\n".join(lines)


def _property(
    name: str, value: str, layer: str, x_nm: int, y_nm: int, *, hide: bool = False
) -> list[str]:
    lines = [
        f"\t(property {quote(name)} {quote(value)}",
        f"\t\t(at {millimetres(x_nm)} {millimetres(y_nm)} 0)",
        f"\t\t(layer {quote(layer)})",
    ]
    if hide:
        lines.append("\t\t(hide yes)")
    lines += _effects("\t\t")
    lines.append("\t)")
    return lines


def _rectangle(rectangle: Rectangle, layer: str, width_nm: int) -> list[str]:
    return [
        "\t(fp_rect",
        f"\t\t(start {millimetres(rectangle.x0_nm)} {millimetres(rectangle.y0_nm)})",
        f"\t\t(end {millimetres(rectangle.x1_nm)} {millimetres(rectangle.y1_nm)})",
        "\t\t(stroke",
        f"\t\t\t(width {millimetres(width_nm)})",
        "\t\t\t(type solid)",
        "\t\t)",
        "\t\t(fill no)",
        f"\t\t(layer {quote(layer)})",
        "\t)",
    ]


def _circle(circle: Circle, layer: str, width_nm: int) -> list[str]:
    return [
        "\t(fp_circle",
        f"\t\t(center {millimetres(circle.centre_x_nm)} {millimetres(circle.centre_y_nm)})",
        (f"\t\t(end {millimetres(circle.centre_x_nm + circle.radius_nm)} "
         f"{millimetres(circle.centre_y_nm)})"),
        "\t\t(stroke",
        f"\t\t\t(width {millimetres(width_nm)})",
        "\t\t\t(type solid)",
        "\t\t)",
        "\t\t(fill yes)",
        f"\t\t(layer {quote(layer)})",
        "\t)",
    ]


def render_symbol_library(definition: SymbolDefinition) -> str:
    """Serialize one symbol as a standalone KiCad 10 ``.kicad_sym`` payload."""
    body = definition.body
    lines = [
        "(kicad_symbol_lib",
        f"\t(version {SYMBOL_LIB_FORMAT_VERSION})",
        f"\t(generator {quote(GENERATOR)})",
        f"\t(generator_version {quote(GENERATOR_VERSION)})",
        f"\t(symbol {quote(definition.name)}",
        "\t\t(pin_names",
        "\t\t\t(offset 0.254)",
        "\t\t)",
        "\t\t(exclude_from_sim yes)",
        "\t\t(in_bom yes)",
        "\t\t(on_board yes)",
    ]
    top = body.y1_nm + 2_540_000
    lines += _symbol_property("Reference", definition.reference_prefix, 0, top)
    lines += _symbol_property("Value", definition.value, 0, body.y0_nm - 2_540_000)
    lines += _symbol_property("Footprint", "", 0, 0, hide=True)
    lines += _symbol_property("Datasheet", definition.datasheet_note, 0, 0, hide=True)
    lines += _symbol_property("Description", definition.description, 0, 0, hide=True)
    lines += _symbol_property("ohmni_constraint_hash", definition.constraint_hash, 0, 0, hide=True)
    lines += _symbol_property("ohmni_policy_version", definition.policy_version, 0, 0, hide=True)
    for index, limitation in enumerate(definition.limitations):
        lines += _symbol_property(f"ohmni_limitation_{index + 1}", limitation, 0, 0, hide=True)
    lines += [
        f"\t\t(symbol {quote(definition.name + '_0_1')}",
        "\t\t\t(rectangle",
        f"\t\t\t\t(start {millimetres(body.x0_nm)} {millimetres(body.y0_nm)})",
        f"\t\t\t\t(end {millimetres(body.x1_nm)} {millimetres(body.y1_nm)})",
        "\t\t\t\t(stroke",
        f"\t\t\t\t\t(width {millimetres(SYMBOL_BODY_WIDTH_NM)})",
        "\t\t\t\t\t(type default)",
        "\t\t\t\t)",
        "\t\t\t\t(fill",
        "\t\t\t\t\t(type background)",
        "\t\t\t\t)",
        "\t\t\t)",
        "\t\t)",
        f"\t\t(symbol {quote(definition.name + '_1_1')}",
    ]
    for pin in definition.pins:
        lines += [
            f"\t\t\t(pin {pin.electrical_type} line",
            f"\t\t\t\t(at {millimetres(pin.x_nm)} {millimetres(pin.y_nm)} {pin.orientation_deg})",
            f"\t\t\t\t(length {millimetres(pin.length_nm)})",
            f"\t\t\t\t(name {quote(pin.name)}",
            "\t\t\t\t\t(effects",
            "\t\t\t\t\t\t(font",
            "\t\t\t\t\t\t\t(size 1.27 1.27)",
            "\t\t\t\t\t\t)",
            "\t\t\t\t\t)",
            "\t\t\t\t)",
            f"\t\t\t\t(number {quote(pin.number)}",
            "\t\t\t\t\t(effects",
            "\t\t\t\t\t\t(font",
            "\t\t\t\t\t\t\t(size 1.27 1.27)",
            "\t\t\t\t\t\t)",
            "\t\t\t\t\t)",
            "\t\t\t\t)",
            "\t\t\t)",
        ]
    lines += ["\t\t)", "\t)", ")", ""]
    return "\n".join(lines)


def _symbol_property(
    name: str, value: str, x_nm: int, y_nm: int, *, hide: bool = False
) -> list[str]:
    lines = [
        f"\t\t(property {quote(name)} {quote(value)}",
        f"\t\t\t(at {millimetres(x_nm)} {millimetres(y_nm)} 0)",
    ]
    if hide:
        lines.append("\t\t\t(hide yes)")
    lines += [
        "\t\t\t(effects",
        "\t\t\t\t(font",
        "\t\t\t\t\t(size 1.27 1.27)",
        "\t\t\t\t)",
        "\t\t\t)",
        "\t\t)",
    ]
    return lines


def write_asset(payload: str, destination: Path) -> str:
    """Write UTF-8 with LF newlines and return the SHA-256 of the exact bytes."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8")
    destination.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


__all__ = [
    "COURTYARD_WIDTH_NM",
    "FOOTPRINT_FORMAT_VERSION",
    "GENERATOR",
    "GENERATOR_VERSION",
    "SILKSCREEN_WIDTH_NM",
    "SYMBOL_LIB_FORMAT_VERSION",
    "AssetSerializationError",
    "millimetres",
    "render_footprint",
    "render_symbol_library",
    "write_asset",
]
