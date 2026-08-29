"""Quantities, parsing and tolerance-aware comparison."""

from __future__ import annotations

import pytest

from ohmni.domain import (
    Quantity,
    QuantityParseError,
    Unit,
    UnitMismatchError,
    ValueRange,
    parse_quantity,
)


class TestParsing:
    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_unit"),
        [
            ("3.3V", 3.3, Unit.VOLT),
            ("3V3", 3.3, Unit.VOLT),
            ("1.8 V", 1.8, Unit.VOLT),
            ("100nF", 100e-9, Unit.FARAD),
            ("22uF", 22e-6, Unit.FARAD),
            ("250mA", 0.25, Unit.AMPERE),
            ("600 mA", 0.6, Unit.AMPERE),
            ("4R7", 4.7, Unit.OHM),
            ("4k7", 4700.0, Unit.OHM),
            ("10kohm", 10_000.0, Unit.OHM),
            ("1.5 Mohm", 1.5e6, Unit.OHM),
            ("100 kHz", 100e3, Unit.HERTZ),
            ("125mW", 0.125, Unit.WATT),
        ],
    )
    def test_engineering_notation(self, text, expected_value, expected_unit):
        # "4k7" has no unit letter, so ohms must be supplied for that case.
        unit = Unit.OHM if text == "4k7" else None
        q = parse_quantity(text, unit)
        assert q.unit is expected_unit
        assert q.value == pytest.approx(expected_value)

    def test_micro_sign_variants_normalise(self):
        assert parse_quantity("22µF").value == pytest.approx(22e-6)  # MICRO SIGN
        assert parse_quantity("22μF").value == pytest.approx(22e-6)  # GREEK MU

    def test_ohm_sign_normalises(self):
        assert parse_quantity("4.7 kΩ").unit is Unit.OHM

    def test_bare_number_without_unit_is_refused(self):
        # The whole point of the type: refuse to guess a dimension.
        with pytest.raises(QuantityParseError, match="refusing to guess"):
            parse_quantity("3.3")

    def test_bare_number_with_supplied_unit_is_fine(self):
        assert parse_quantity("3.3", Unit.VOLT) == Quantity.volts(3.3)

    def test_conflicting_unit_is_an_error_not_a_coercion(self):
        with pytest.raises(UnitMismatchError):
            parse_quantity("3.3V", Unit.AMPERE)

    def test_nonsense_is_refused(self):
        with pytest.raises(QuantityParseError):
            parse_quantity("banana")

    def test_shorthand_accepted_wherever_a_quantity_is_expected(self):
        # Fixtures and catalog JSON can say "100nF" instead of a dict.
        parsed = Quantity.model_validate("100nF")
        assert parsed.unit is Unit.FARAD
        # 100 * 1e-9 and the literal 1e-7 differ in the last bit, which is
        # exactly why `==` is exact and engineering comparison goes through
        # is_close. See TestEqualityIsExact below.
        assert parsed.is_close(Quantity.farads(100e-9))


class TestComparison:
    def test_units_are_checked(self):
        with pytest.raises(UnitMismatchError):
            _ = Quantity.volts(3.3) < Quantity.amps(3.3)
        with pytest.raises(UnitMismatchError):
            _ = Quantity.volts(1.0) + Quantity.ohms(1.0)

    def test_boundary_is_inclusive_under_float_noise(self):
        # 0.1 + 0.2 is 0.30000000000000004 in binary floating point. A limit
        # reached by arithmetic must not be reported as exceeded because of
        # representation error alone.
        computed = Quantity.volts(0.1) + Quantity.volts(0.2)
        assert computed.value > 0.3
        assert computed.at_most(Quantity.volts(0.3))
        assert computed.at_least(Quantity.volts(0.3))

    def test_strict_comparison_does_not_silently_apply_tolerance(self):
        # at_most/at_least opt into tolerance; < and > do not. Keeping them
        # apart means a rule author has to choose, visibly, in the rule.
        computed = Quantity.volts(0.1) + Quantity.volts(0.2)
        assert computed > Quantity.volts(0.3)
        assert not computed.at_most(Quantity.volts(0.3), rel_tol=0.0)

    def test_engineering_formatting_is_ascii(self):
        text = Quantity.farads(22e-6).engineering()
        assert text == "22 uF"
        assert text.isascii()
        assert Quantity.ohms(4700).engineering() == "4.7 kohm"
        assert Quantity.volts(0).engineering() == "0 V"


class TestEqualityIsExact:
    """`==` is structural; engineering comparison is `is_close`.

    Quantity is a frozen, hashable value object, so equality has to stay exact
    to keep hashing consistent. Anything comparing measured or computed values
    must use is_close / at_most / at_least.
    """

    def test_equal_values_compare_equal(self):
        assert Quantity.volts(3.3) == Quantity.volts(3.3)

    def test_last_bit_differences_are_not_equal_but_are_close(self):
        parsed = parse_quantity("100nF")
        literal = Quantity.farads(100e-9)
        assert parsed != literal
        assert parsed.is_close(literal)

    def test_quantities_are_hashable(self):
        assert len({Quantity.volts(3.3), Quantity.volts(3.3)}) == 1

class TestValueRange:
    def test_requires_at_least_one_bound(self):
        with pytest.raises(ValueError, match="at least one"):
            ValueRange()

    def test_rejects_mixed_units(self):
        # Raised as UnitMismatchError inside the validator; pydantic wraps any
        # ValueError from a validator into a ValidationError.
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="mixes units"):
            ValueRange(minimum=Quantity.volts(1.0), maximum=Quantity.amps(2.0))

    def test_rejects_inverted_bounds(self):
        with pytest.raises(ValueError, match="minimum exceeds maximum"):
            ValueRange(minimum=Quantity.volts(3.6), maximum=Quantity.volts(1.7))

    def test_rejects_typical_outside_the_limits(self):
        with pytest.raises(ValueError, match="typical is above maximum"):
            ValueRange(
                minimum=Quantity.volts(1.7),
                typical=Quantity.volts(5.0),
                maximum=Quantity.volts(3.6),
            )

    def test_containment_is_boundary_inclusive(self):
        operating = ValueRange(minimum=Quantity.volts(1.71), maximum=Quantity.volts(3.6))
        assert operating.contains(Quantity.volts(3.3))
        assert operating.contains(Quantity.volts(3.6))
        assert operating.contains(Quantity.volts(1.71))
        assert not operating.contains(Quantity.volts(5.0))

    def test_unbounded_side_never_excludes(self):
        at_least_2v5 = ValueRange(minimum=Quantity.volts(2.5))
        assert at_least_2v5.contains(Quantity.volts(48.0))
        assert not at_least_2v5.contains(Quantity.volts(1.0))

    def test_worst_case_accessors(self):
        r = ValueRange(
            minimum=Quantity.volts(4.75),
            typical=Quantity.volts(5.0),
            maximum=Quantity.volts(5.25),
        )
        assert r.worst_case_high == Quantity.volts(5.25)
        assert r.worst_case_low == Quantity.volts(4.75)
        assert r.nominal == Quantity.volts(5.0)

    def test_nominal_falls_back_to_midpoint(self):
        r = ValueRange(minimum=Quantity.volts(3.0), maximum=Quantity.volts(3.6))
        assert r.nominal is not None
        assert r.nominal.value == pytest.approx(3.3)

    def test_accessors_are_properties_on_both_range_and_netvoltage(self):
        # These two types expose the same names. When one was a method and the
        # other a property, two rules silently compared a bound method against
        # a float. Keep them symmetric.
        from ohmni.verifier.context import NetVoltage

        r = ValueRange(minimum=Quantity.volts(1.0), maximum=Quantity.volts(2.0))
        nv = NetVoltage(net_name="X", voltage=r)
        for name in ("nominal", "worst_case_high", "worst_case_low"):
            assert not callable(getattr(r, name))
            assert not callable(getattr(nv, name))
