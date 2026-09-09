"""Typed physical quantities.

No electrical value anywhere in Ohmni is a bare string or a bare float.
Every quantity carries its unit, and every quantity is stored in the canonical
SI base unit for that dimension (volts, amperes, ohms, farads, ...). Engineering
notation is a *presentation* and *parsing* concern only.

Rationale (see PRE_IMPLEMENTATION_REVIEW.md 3.2): the specification's
``Evidence.value: str | float | None`` cannot distinguish "3.3V", "3V3", "3.3"
and 3.3, which is precisely the ambiguity that produces destroyed hardware.
"""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

# Relative tolerance used for boundary comparisons. Datasheet limits are decimal
# values that do not round-trip exactly in binary floating point; comparing
# 3.3 * 1.1 against 3.63 must not fail on representation noise alone.
REL_TOL = 1e-9


class UnitMismatchError(ValueError):
    """Raised when two quantities of different dimensions are combined."""


class QuantityParseError(ValueError):
    """Raised when a string cannot be parsed into an unambiguous quantity."""


class Unit(StrEnum):
    """Canonical SI base units. The stored value is always in these units."""

    VOLT = "V"
    AMPERE = "A"
    OHM = "ohm"
    FARAD = "F"
    HENRY = "H"
    WATT = "W"
    SECOND = "s"
    HERTZ = "Hz"
    CELSIUS = "degC"
    METRE = "m"
    # Dimensionless. Used for counts and ratios so they are still explicit.
    COUNT = "count"
    RATIO = "ratio"


# Unit symbols accepted when parsing, longest first so "degC" wins over "C"
# and "ohm" is not mistaken for a prefix + "m".
_UNIT_SYMBOLS: tuple[tuple[str, Unit], ...] = (
    ("degC", Unit.CELSIUS),
    ("ohm", Unit.OHM),
    ("Hz", Unit.HERTZ),
    ("V", Unit.VOLT),
    ("A", Unit.AMPERE),
    ("F", Unit.FARAD),
    ("H", Unit.HENRY),
    ("W", Unit.WATT),
    ("s", Unit.SECOND),
    ("m", Unit.METRE),
)

_PREFIXES: dict[str, float] = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "": 1.0,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}

# Display prefixes, ordered for engineering notation output. ASCII only: "u"
# rather than the micro sign, because these strings end up in reports, in
# generated files and on Windows consoles whose encoding we do not control.
_DISPLAY_PREFIXES: tuple[tuple[float, str], ...] = (
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "u"),
    (1e-9, "n"),
    (1e-12, "p"),
)

# Infix engineering notation: "4k7" = 4.7k, "3V3" = 3.3 V, "4R7" = 4.7 ohm.
# "R" is the traditional resistor marking for the unity multiplier.
_INFIX_UNIT_LETTERS: dict[str, Unit] = {
    "R": Unit.OHM,
    "V": Unit.VOLT,
    "A": Unit.AMPERE,
    "F": Unit.FARAD,
    "H": Unit.HENRY,
    "W": Unit.WATT,
}

_NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_PLAIN_RE = re.compile(rf"^(?P<num>{_NUMBER})\s*(?P<rest>[a-zA-Z]*)$")
_INFIX_RE = re.compile(r"^(?P<whole>\d+)(?P<mid>[a-zA-Z])(?P<frac>\d+)$")


def _normalise(text: str) -> str:
    """Fold the many ways datasheets write the same unit into one spelling."""
    out = text.strip()
    for src, dst in (
        ("µ", "u"),  # MICRO SIGN
        ("μ", "u"),  # GREEK SMALL LETTER MU
        ("Ω", "ohm"),  # OHM SIGN
        ("Ω", "ohm"),  # GREEK CAPITAL LETTER OMEGA
        ("℃", "degC"),  # DEGREE CELSIUS
        ("°C", "degC"),
        ("Ohms", "ohm"),
        ("Ohm", "ohm"),
        ("ohms", "ohm"),
    ):
        out = out.replace(src, dst)
    return out


def _split_unit(rest: str) -> tuple[str, Unit | None]:
    """Split a trailing symbol group into (prefix, unit)."""
    for symbol, unit in _UNIT_SYMBOLS:
        if rest == symbol:
            return "", unit
        if rest.endswith(symbol):
            prefix = rest[: -len(symbol)]
            if prefix in _PREFIXES:
                return prefix, unit
    if rest in _PREFIXES:
        return rest, None
    raise QuantityParseError(f"unrecognised unit or prefix: {rest!r}")


def parse_quantity(text: str, unit: Unit | None = None) -> Quantity:
    """Parse engineering notation into a canonical :class:`Quantity`.

    Accepts ``"3.3V"``, ``"3V3"``, ``"100nF"``, ``"4k7"`` (with ``unit`` given),
    ``"4R7"``, ``"250 mA"``, ``"1.8"`` (with ``unit`` given).

    ``unit`` supplies the dimension when the text does not carry one. If the
    text carries a unit and ``unit`` is also given, they must agree; a
    disagreement is a bug worth surfacing loudly rather than silently coercing.
    """
    raw = _normalise(text)
    if not raw:
        raise QuantityParseError("empty quantity string")

    scale = 1.0
    parsed_unit: Unit | None = None

    if match := _PLAIN_RE.match(raw):
        value = float(match.group("num"))
        rest = match.group("rest")
        if rest:
            prefix, parsed_unit = _split_unit(rest)
            scale = _PREFIXES[prefix]
    elif match := _INFIX_RE.match(raw):
        mid = match.group("mid")
        value = float(f"{match.group('whole')}.{match.group('frac')}")
        if mid in _INFIX_UNIT_LETTERS:
            parsed_unit = _INFIX_UNIT_LETTERS[mid]
        elif mid in _PREFIXES:
            scale = _PREFIXES[mid]
        else:
            raise QuantityParseError(f"unrecognised infix multiplier {mid!r} in {text!r}")
    else:
        raise QuantityParseError(f"cannot parse quantity from {text!r}")

    resolved = parsed_unit or unit
    if resolved is None:
        raise QuantityParseError(
            f"{text!r} carries no unit and no unit was supplied; refusing to guess"
        )
    if parsed_unit is not None and unit is not None and parsed_unit != unit:
        raise UnitMismatchError(f"{text!r} is in {parsed_unit} but {unit} was expected")

    return Quantity(value=value * scale, unit=resolved)


class Quantity(BaseModel):
    """An immutable physical value in a canonical SI base unit.

    Equality is **exact and structural**, because this is a frozen, hashable
    value object and tolerant equality would break hashing. Engineering
    comparison goes through :meth:`is_close`, :meth:`at_most` and
    :meth:`at_least`, which opt into tolerance explicitly.

    That distinction is load-bearing: ``parse_quantity("100nF")`` computes
    ``100 * 1e-9``, which differs from the literal ``1e-7`` in the last bit.
    Any rule comparing a measured or computed value against a limit must use
    the tolerant methods.
    """

    model_config = ConfigDict(frozen=True)

    value: float
    unit: Unit

    @model_validator(mode="before")
    @classmethod
    def _accept_shorthand(cls, data: Any) -> Any:
        """Allow ``"100nF"`` wherever a Quantity is expected, for readable fixtures."""
        if isinstance(data, str):
            parsed = parse_quantity(data)
            return {"value": parsed.value, "unit": parsed.unit}
        return data

    # -- constructors ----------------------------------------------------

    @classmethod
    def volts(cls, value: float) -> Self:
        return cls(value=value, unit=Unit.VOLT)

    @classmethod
    def amps(cls, value: float) -> Self:
        return cls(value=value, unit=Unit.AMPERE)

    @classmethod
    def ohms(cls, value: float) -> Self:
        return cls(value=value, unit=Unit.OHM)

    @classmethod
    def farads(cls, value: float) -> Self:
        return cls(value=value, unit=Unit.FARAD)

    @classmethod
    def watts(cls, value: float) -> Self:
        return cls(value=value, unit=Unit.WATT)

    # -- arithmetic ------------------------------------------------------

    def _require_same_unit(self, other: Quantity) -> None:
        if self.unit != other.unit:
            raise UnitMismatchError(f"cannot combine {self.unit} with {other.unit}")

    def __add__(self, other: Quantity) -> Quantity:
        self._require_same_unit(other)
        return Quantity(value=self.value + other.value, unit=self.unit)

    def __sub__(self, other: Quantity) -> Quantity:
        self._require_same_unit(other)
        return Quantity(value=self.value - other.value, unit=self.unit)

    def scaled(self, factor: float) -> Quantity:
        return Quantity(value=self.value * factor, unit=self.unit)

    # -- comparison ------------------------------------------------------
    #
    # Comparisons are unit-checked. They deliberately do NOT apply tolerance:
    # a rule that needs boundary tolerance must ask for it explicitly via
    # is_close / at_most / at_least, so that the choice is visible in the rule.

    def __lt__(self, other: Quantity) -> bool:
        self._require_same_unit(other)
        return self.value < other.value

    def __le__(self, other: Quantity) -> bool:
        self._require_same_unit(other)
        return self.value <= other.value

    def __gt__(self, other: Quantity) -> bool:
        self._require_same_unit(other)
        return self.value > other.value

    def __ge__(self, other: Quantity) -> bool:
        self._require_same_unit(other)
        return self.value >= other.value

    def is_close(self, other: Quantity, rel_tol: float = REL_TOL) -> bool:
        self._require_same_unit(other)
        return math.isclose(self.value, other.value, rel_tol=rel_tol, abs_tol=0.0)

    def at_most(self, limit: Quantity, rel_tol: float = REL_TOL) -> bool:
        """True if this value is within ``limit``, treating the boundary as inside."""
        self._require_same_unit(limit)
        return self.value <= limit.value or self.is_close(limit, rel_tol)

    def at_least(self, limit: Quantity, rel_tol: float = REL_TOL) -> bool:
        """True if this value reaches ``limit``, treating the boundary as inside."""
        self._require_same_unit(limit)
        return self.value >= limit.value or self.is_close(limit, rel_tol)

    # -- presentation ----------------------------------------------------

    def engineering(self, significant: int = 3) -> str:
        """Format with an engineering prefix, e.g. ``4.7 kohm``, ``100 nF``."""
        if self.unit in (Unit.COUNT, Unit.RATIO):
            return f"{self.value:g}"
        if self.value == 0:
            return f"0 {self.unit.value}"
        magnitude = abs(self.value)
        for factor, prefix in _DISPLAY_PREFIXES:
            if magnitude >= factor:
                scaled = self.value / factor
                text = f"{scaled:.{significant}g}"
                return f"{text} {prefix}{self.unit.value}"
        scaled = self.value / 1e-12
        return f"{scaled:.{significant}g} p{self.unit.value}"

    def __str__(self) -> str:
        return self.engineering()


class ValueRange(BaseModel):
    """A datasheet min / typical / max triple.

    This is the shape real datasheets publish. Keeping typical distinct from the
    limits is what lets the verifier refuse to treat a typical value as a
    guarantee, and lets it keep recommended operating conditions separate from
    absolute maximum ratings.
    """

    model_config = ConfigDict(frozen=True)

    minimum: Quantity | None = None
    typical: Quantity | None = None
    maximum: Quantity | None = None

    @model_validator(mode="after")
    def _check(self) -> ValueRange:
        present = [q for q in (self.minimum, self.typical, self.maximum) if q is not None]
        if not present:
            raise ValueError("ValueRange requires at least one of minimum/typical/maximum")
        units = {q.unit for q in present}
        if len(units) > 1:
            raise UnitMismatchError(f"ValueRange mixes units: {sorted(u.value for u in units)}")
        if self.minimum and self.maximum and self.minimum > self.maximum:
            raise ValueError("ValueRange minimum exceeds maximum")
        if self.minimum and self.typical and self.typical < self.minimum:
            raise ValueError("ValueRange typical is below minimum")
        if self.maximum and self.typical and self.typical > self.maximum:
            raise ValueError("ValueRange typical is above maximum")
        return self

    @property
    def unit(self) -> Unit:
        for q in (self.minimum, self.typical, self.maximum):
            if q is not None:
                return q.unit
        raise AssertionError("unreachable: validated to have at least one bound")

    @classmethod
    def exact(cls, quantity: Quantity) -> ValueRange:
        return cls(minimum=quantity, typical=quantity, maximum=quantity)

    def contains(self, quantity: Quantity, rel_tol: float = REL_TOL) -> bool:
        """Boundary-inclusive containment. An unbounded side never excludes."""
        if quantity.unit != self.unit:
            raise UnitMismatchError(f"cannot test {quantity.unit} against {self.unit} range")
        if self.minimum is not None and not quantity.at_least(self.minimum, rel_tol):
            return False
        return self.maximum is None or quantity.at_most(self.maximum, rel_tol)

    @property
    def worst_case_high(self) -> Quantity | None:
        """Highest value this range can take: maximum, else typical, else minimum."""
        return self.maximum or self.typical or self.minimum

    @property
    def worst_case_low(self) -> Quantity | None:
        """Lowest value this range can take: minimum, else typical, else maximum."""
        return self.minimum or self.typical or self.maximum

    @property
    def nominal(self) -> Quantity | None:
        """Best single representative value: typical, else the midpoint, else a bound."""
        if self.typical is not None:
            return self.typical
        if self.minimum is not None and self.maximum is not None:
            return Quantity(
                value=(self.minimum.value + self.maximum.value) / 2.0, unit=self.unit
            )
        return self.minimum or self.maximum

    def __str__(self) -> str:
        if self.minimum and self.maximum and self.minimum.is_close(self.maximum):
            return str(self.minimum)
        low = self.minimum.engineering() if self.minimum else "?"
        high = self.maximum.engineering() if self.maximum else "?"
        if self.typical is not None:
            return f"{low} .. {self.typical.engineering()} (typ) .. {high}"
        return f"{low} .. {high}"
