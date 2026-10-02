"""What an emitted component asset was measured to contain.

Pure geometry, on the integer nanometre grid, with no knowledge of any file
format. The KiCad asset parser produces these by reading actual bytes; the asset
verifier consumes them. Keeping the contract here is what lets the checks stay
in :mod:`ohmni.physical` without that package learning about KiCad -- the
dependency runs ``eda -> physical``, as it does for board geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MeasuredPad:
    """One land as it was found in the emitted file."""

    number: str
    kind: str
    shape: str
    centre_x_nm: int
    centre_y_nm: int
    width_nm: int
    height_nm: int
    rotation_deg: float
    layers: tuple[str, ...]

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


@dataclass(frozen=True)
class MeasuredGraphic:
    """One non-copper primitive: its layer, its points and its stroke."""

    primitive: str
    layer: str
    points_nm: tuple[tuple[int, int], ...]
    width_nm: int
    filled: bool


@dataclass(frozen=True)
class MeasuredFootprint:
    name: str
    format_version: str
    generator: str
    generator_version: str
    attributes: tuple[str, ...]
    properties: dict[str, str]
    pads: tuple[MeasuredPad, ...]
    graphics: tuple[MeasuredGraphic, ...] = field(default=())

    def pad(self, number: str) -> MeasuredPad | None:
        found = [item for item in self.pads if item.number == number]
        return found[0] if len(found) == 1 else None

    def layer_graphics(self, layer: str) -> tuple[MeasuredGraphic, ...]:
        return tuple(item for item in self.graphics if item.layer == layer)


@dataclass(frozen=True)
class MeasuredSymbolPin:
    number: str
    name: str
    electrical_type: str
    graphic_style: str
    x_nm: int
    y_nm: int
    orientation_deg: float
    length_nm: int


@dataclass(frozen=True)
class MeasuredSymbol:
    name: str
    format_version: str
    generator: str
    generator_version: str
    properties: dict[str, str]
    pins: tuple[MeasuredSymbolPin, ...]
    body_points_nm: tuple[tuple[int, int], ...]

    def pin(self, number: str) -> MeasuredSymbolPin | None:
        found = [item for item in self.pins if item.number == number]
        return found[0] if len(found) == 1 else None


__all__ = [
    "MeasuredFootprint",
    "MeasuredGraphic",
    "MeasuredPad",
    "MeasuredSymbol",
    "MeasuredSymbolPin",
]
