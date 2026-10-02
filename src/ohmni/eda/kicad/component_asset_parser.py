"""Independent structural parsing and measurement of emitted asset bytes.

This module exists to be a *second* opinion. It reads the bytes that were
actually written and reports what it finds there; it never imports the land
pattern or symbol definitions, and the architecture tests enforce that. Sharing
a tokenizer with a generator is fine. Sharing the generator's geometry as the
only oracle is how a footprint comes to agree with itself and with nothing else.

Everything is bounded and fails closed: unbalanced parentheses, excess nesting,
duplicated critical fields, unknown pad shapes, non-finite numbers and unexpected
primitives are errors, not values to work around.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ...physical.asset_measurements import (
    MeasuredFootprint,
    MeasuredGraphic,
    MeasuredPad,
    MeasuredSymbol,
    MeasuredSymbolPin,
)

#: Bounds on what a component asset may contain. Generous against real
#: libraries, finite against a malformed or hostile file.
MAX_ASSET_BYTES = 4 * 1024 * 1024
MAX_NESTING_DEPTH = 32
MAX_NODES = 100_000
#: Nanometres per millimetre, repeated here rather than imported: this parser is
#: deliberately independent of the domain module the generator uses.
NM_PER_MM = 1_000_000

_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')
_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")


class AssetParseError(ValueError):
    """The emitted bytes are not a readable asset. Never a partial result."""


@dataclass(frozen=True)
class Node:
    """One S-expression list: a head symbol and its arguments."""

    head: str
    items: tuple[object, ...]

    def children(self, head: str) -> list[Node]:
        return [item for item in self.items if isinstance(item, Node) and item.head == head]

    def child(self, head: str) -> Node:
        found = self.children(head)
        if len(found) != 1:
            raise AssetParseError(f"expected exactly one ({head} ...), found {len(found)}")
        return found[0]

    def optional(self, head: str) -> Node | None:
        found = self.children(head)
        if len(found) > 1:
            raise AssetParseError(f"duplicated ({head} ...)")
        return found[0] if found else None

    def atoms(self) -> list[str]:
        return [item for item in self.items if isinstance(item, str)]


def parse(payload: str) -> Node:
    """Parse one top-level S-expression from text. Bounded and fail-closed."""
    if len(payload.encode("utf-8")) > MAX_ASSET_BYTES:
        raise AssetParseError("asset exceeds the parser size bound")
    tokens = _TOKEN.findall(payload)
    position = 0
    nodes = 0

    def build(depth: int) -> Node:
        nonlocal position, nodes
        if depth > MAX_NESTING_DEPTH:
            raise AssetParseError("asset nesting exceeds the parser bound")
        nodes += 1
        if nodes > MAX_NODES:
            raise AssetParseError("asset node count exceeds the parser bound")
        if position >= len(tokens) or tokens[position] != "(":
            raise AssetParseError("expected an opening parenthesis")
        position += 1
        if position >= len(tokens):
            raise AssetParseError("unterminated list")
        head = tokens[position]
        if head in "()" or head.startswith('"'):
            raise AssetParseError("a list must start with a symbol")
        position += 1
        items: list[object] = []
        while position < len(tokens) and tokens[position] != ")":
            token = tokens[position]
            if token == "(":
                items.append(build(depth + 1))
            else:
                items.append(_unquote(token))
                position += 1
        if position >= len(tokens):
            raise AssetParseError("unbalanced parentheses")
        position += 1
        return Node(head=head, items=tuple(items))

    while position < len(tokens) and tokens[position] != "(":
        position += 1
    root = build(0)
    while position < len(tokens):
        if tokens[position].strip():
            raise AssetParseError("trailing content after the top-level list")
        position += 1
    return root


def _unquote(token: str) -> str:
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        return token[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return token


def nanometres(text: str) -> int:
    """Read a millimetre literal as exact nanometres, or refuse it."""
    if not _NUMBER.match(text):
        raise AssetParseError(f"{text!r} is not a finite decimal")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
        raise AssetParseError(f"{text!r} is not a decimal") from exc
    if not value.is_finite() or math.isinf(float(value)):
        raise AssetParseError(f"{text!r} is not finite")
    scaled = value * NM_PER_MM
    if scaled != scaled.to_integral_value():
        raise AssetParseError(f"{text!r} mm is finer than the one nanometre grid")
    return int(scaled)


_SUPPORTED_PAD_KINDS = {"smd", "thru_hole", "np_thru_hole"}
_SUPPORTED_PAD_SHAPES = {"rect", "roundrect", "circle", "oval"}

#: The exact syntax this slice understands. Anything outside it is refused.
#:
#: The audit's third finding was that silently ignoring what we do not read is
#: indistinguishable from reading it and finding nothing wrong. A
#: ``solder_mask_margin -0.4`` that the parser drops still changes the board,
#: while the report goes on saying mask openings are explicit. So the rule here
#: is an allowlist: if the parser does not model a construct, the file is
#: rejected rather than measured as if the construct were absent.
_FOOTPRINT_CHILDREN = frozenset({
    "version", "generator", "generator_version", "layer", "descr", "tags",
    "property", "attr", "pad", "fp_rect", "fp_circle", "fp_line", "fp_poly",
})
_PAD_CHILDREN = frozenset({"at", "size", "layers", "roundrect_rratio"})
_GRAPHIC_CHILDREN = frozenset({"start", "end", "center", "mid", "pts", "stroke", "fill", "layer"})
_PROPERTY_CHILDREN = frozenset({"at", "layer", "hide", "effects", "uuid", "unlocked"})
_SYMBOL_LIB_CHILDREN = frozenset({"version", "generator", "generator_version", "symbol"})
_SYMBOL_CHILDREN = frozenset({
    "pin_names", "pin_numbers", "exclude_from_sim", "in_bom", "on_board", "property",
    "symbol",
})
_SYMBOL_UNIT_CHILDREN = frozenset({"rectangle", "pin", "polyline", "circle", "arc", "text"})
_SYMBOL_PIN_CHILDREN = frozenset({"at", "length", "name", "number", "hide"})

#: Copper layers. A graphic on one of these is copper the geometry checks do not
#: model, so it is refused rather than parsed and forgotten.
_COPPER_LAYERS = frozenset({"F.Cu", "B.Cu", "*.Cu"})

#: The only pad rotation this slice supports. Every dimension and clearance
#: check works on axis-aligned envelopes, so a rotated pad would be measured as
#: something it is not: rotating a 0.60 by 1.10 mm land 90 degrees puts 1.10 mm
#: of copper across a 0.95 mm pitch, and the unrotated check never sees it.
SUPPORTED_PAD_ROTATION_DEG = 0.0


def _reject_unknown(node: Node, allowed: frozenset[str], what: str) -> None:
    for item in node.items:
        if isinstance(item, Node) and item.head not in allowed:
            raise AssetParseError(
                f"{what} carries unsupported construct ({item.head} ...); this slice "
                "refuses what it does not model rather than measuring around it"
            )


def measure_footprint(payload: str) -> MeasuredFootprint:
    """Measure a ``.kicad_mod`` payload from its own bytes."""
    root = parse(payload)
    if root.head != "footprint":
        raise AssetParseError(f"expected a footprint, found ({root.head} ...)")
    _reject_unknown(root, _FOOTPRINT_CHILDREN, "footprint")
    atoms = root.atoms()
    if not atoms:
        raise AssetParseError("footprint has no name")
    name = atoms[0]
    version = root.child("version").atoms()
    generator = root.child("generator").atoms()
    generator_version = root.child("generator_version").atoms()
    if not version or not generator or not generator_version:
        raise AssetParseError("footprint is missing its format or generator identity")

    properties: dict[str, str] = {}
    for node in root.children("property"):
        _reject_unknown(node, _PROPERTY_CHILDREN, "a footprint property")
        entries = node.atoms()
        if len(entries) < 2:
            raise AssetParseError("a property must carry a name and a value")
        if entries[0] in properties:
            raise AssetParseError(f"duplicated property {entries[0]!r}")
        properties[entries[0]] = entries[1]

    pads: list[MeasuredPad] = []
    for node in root.children("pad"):
        _reject_unknown(node, _PAD_CHILDREN, "a pad")
        entries = node.atoms()
        if len(entries) < 3:
            raise AssetParseError("a pad must carry a number, a kind and a shape")
        number, kind, shape = entries[0], entries[1], entries[2]
        if kind not in _SUPPORTED_PAD_KINDS:
            raise AssetParseError(f"unsupported pad kind {kind!r}")
        if shape not in _SUPPORTED_PAD_SHAPES:
            raise AssetParseError(f"unsupported pad shape {shape!r}")
        at = node.child("at").atoms()
        if len(at) not in (2, 3):
            raise AssetParseError("a pad position needs x, y and an optional rotation")
        size = node.child("size").atoms()
        if len(size) != 2:
            raise AssetParseError("a pad size needs exactly two dimensions")
        layers = tuple(node.child("layers").atoms())
        if not layers:
            raise AssetParseError("a pad must name at least one layer")
        rotation = float(at[2]) if len(at) == 3 else 0.0
        if not math.isfinite(rotation) or rotation != SUPPORTED_PAD_ROTATION_DEG:
            raise AssetParseError(
                f"pad {number!r} carries rotation {at[2] if len(at) == 3 else rotation}; this "
                "slice supports only unrotated pads, because every dimension and clearance "
                "check measures an axis-aligned envelope"
            )
        pads.append(MeasuredPad(
            number=number, kind=kind, shape=shape,
            centre_x_nm=nanometres(at[0]), centre_y_nm=nanometres(at[1]),
            width_nm=nanometres(size[0]), height_nm=nanometres(size[1]),
            rotation_deg=rotation,
            layers=layers,
        ))
    numbered = [pad.number for pad in pads]
    if len(numbered) != len(set(numbered)):
        raise AssetParseError("the footprint has duplicate pad numbers")

    graphics: list[MeasuredGraphic] = []
    for node in root.items:
        if not isinstance(node, Node) or node.head not in {"fp_rect", "fp_circle", "fp_line",
                                                           "fp_poly"}:
            continue
        graphics.append(_graphic(node))
    return MeasuredFootprint(
        name=name, format_version=version[0], generator=generator[0],
        generator_version=generator_version[0],
        attributes=tuple(atom for node in root.children("attr") for atom in node.atoms()),
        properties=properties, pads=tuple(pads), graphics=tuple(graphics),
    )


def _graphic(node: Node) -> MeasuredGraphic:
    _reject_unknown(node, _GRAPHIC_CHILDREN, f"a {node.head}")
    layer = node.child("layer").atoms()
    if not layer:
        raise AssetParseError(f"({node.head} ...) names no layer")
    if layer[0] in _COPPER_LAYERS:
        raise AssetParseError(
            f"({node.head} ...) draws on copper layer {layer[0]!r}; copper outside pads is "
            "not modelled by the geometry checks, so it is refused rather than ignored"
        )
    stroke = node.optional("stroke")
    width = 0
    if stroke is not None:
        width_atoms = stroke.child("width").atoms()
        if not width_atoms:
            raise AssetParseError("a stroke must carry a width")
        width = nanometres(width_atoms[0])
    fill = node.optional("fill")
    filled = bool(fill and fill.atoms() and fill.atoms()[0] in {"yes", "solid", "true"})
    points: list[tuple[int, int]] = []
    for key in ("start", "end", "center", "mid"):
        for child in node.children(key):
            pair = child.atoms()
            if len(pair) < 2:
                raise AssetParseError(f"({key} ...) needs two coordinates")
            points.append((nanometres(pair[0]), nanometres(pair[1])))
    for child in node.children("pts"):
        for point in child.children("xy"):
            pair = point.atoms()
            if len(pair) < 2:
                raise AssetParseError("(xy ...) needs two coordinates")
            points.append((nanometres(pair[0]), nanometres(pair[1])))
    return MeasuredGraphic(
        primitive=node.head, layer=layer[0], points_nm=tuple(points),
        width_nm=width, filled=filled,
    )


_SUPPORTED_PIN_TYPES = {
    "input", "output", "bidirectional", "tri_state", "passive", "free", "unspecified",
    "power_in", "power_out", "open_collector", "open_emitter", "no_connect",
}


def measure_symbol_library(payload: str) -> MeasuredSymbol:
    """Measure a single-symbol ``.kicad_sym`` payload from its own bytes."""
    root = parse(payload)
    if root.head != "kicad_symbol_lib":
        raise AssetParseError(f"expected a symbol library, found ({root.head} ...)")
    _reject_unknown(root, _SYMBOL_LIB_CHILDREN, "a symbol library")
    version = root.child("version").atoms()
    generator = root.child("generator").atoms()
    generator_version = root.child("generator_version").atoms()
    symbols = root.children("symbol")
    if len(symbols) != 1:
        raise AssetParseError(f"expected exactly one symbol, found {len(symbols)}")
    symbol = symbols[0]
    _reject_unknown(symbol, _SYMBOL_CHILDREN, "a symbol")
    atoms = symbol.atoms()
    if not atoms:
        raise AssetParseError("symbol has no name")

    properties: dict[str, str] = {}
    for node in symbol.children("property"):
        entries = node.atoms()
        if len(entries) < 2:
            raise AssetParseError("a property must carry a name and a value")
        if entries[0] in properties:
            raise AssetParseError(f"duplicated property {entries[0]!r}")
        properties[entries[0]] = entries[1]

    pins: list[MeasuredSymbolPin] = []
    body: list[tuple[int, int]] = []
    for unit in symbol.children("symbol"):
        _reject_unknown(unit, _SYMBOL_UNIT_CHILDREN, "a symbol unit")
        for rectangle in unit.children("rectangle"):
            for key in ("start", "end"):
                pair = rectangle.child(key).atoms()
                body.append((nanometres(pair[0]), nanometres(pair[1])))
        for node in unit.children("pin"):
            _reject_unknown(node, _SYMBOL_PIN_CHILDREN, "a symbol pin")
            entries = node.atoms()
            if len(entries) < 2:
                raise AssetParseError("a pin must carry an electrical type and a style")
            electrical, style = entries[0], entries[1]
            if electrical not in _SUPPORTED_PIN_TYPES:
                raise AssetParseError(f"unsupported pin electrical type {electrical!r}")
            at = node.child("at").atoms()
            if len(at) != 3:
                raise AssetParseError("a pin position needs x, y and an orientation")
            length = node.child("length").atoms()
            name = node.child("name").atoms()
            number = node.child("number").atoms()
            if not name or not number or not length:
                raise AssetParseError("a pin must carry a name, a number and a length")
            pins.append(MeasuredSymbolPin(
                number=number[0], name=name[0], electrical_type=electrical,
                graphic_style=style, x_nm=nanometres(at[0]), y_nm=nanometres(at[1]),
                orientation_deg=float(at[2]), length_nm=nanometres(length[0]),
            ))
    numbers = [pin.number for pin in pins]
    if len(numbers) != len(set(numbers)):
        raise AssetParseError("the symbol has duplicate pin numbers")
    if not version or not generator or not generator_version:
        raise AssetParseError("symbol library is missing its format or generator identity")
    return MeasuredSymbol(
        name=atoms[0], format_version=version[0], generator=generator[0],
        generator_version=generator_version[0], properties=properties,
        pins=tuple(pins), body_points_nm=tuple(body),
    )


__all__ = [
    "MAX_ASSET_BYTES",
    "MAX_NESTING_DEPTH",
    "MAX_NODES",
    "SUPPORTED_PAD_ROTATION_DEG",
    "AssetParseError",
    "MeasuredFootprint",
    "MeasuredGraphic",
    "MeasuredPad",
    "MeasuredSymbol",
    "MeasuredSymbolPin",
    "Node",
    "measure_footprint",
    "measure_symbol_library",
    "nanometres",
    "parse",
]
