"""The seed catalog, and the honesty rules its entries have to obey."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ohmni.adapters import PartNotFoundError
from ohmni.domain import (
    ClaimStatus,
    ComponentCategory,
    ComponentSpec,
    EvidenceKind,
    PackageOption,
    PinElectricalType,
    PinRole,
    PinSpec,
    Quantity,
    SupplyRail,
    Unit,
    ValueRange,
)

V = Quantity.volts


class TestCatalogLoads:
    def test_catalog_is_not_empty(self, catalog):
        assert len(catalog) >= 9

    def test_unknown_part_raises_rather_than_returning_an_empty_spec(self, catalog):
        # A silently-empty spec would make every rule report INSUFFICIENT_DATA
        # and look like a data problem rather than the lookup bug it is.
        assert catalog.get("NOT_A_PART") is None
        with pytest.raises(PartNotFoundError):
            catalog.require("NOT_A_PART")

    def test_every_part_validates(self, catalog):
        for spec in catalog.all_parts():
            assert isinstance(spec, ComponentSpec)


class TestNoInventedMpns:
    """Hard target from EVALS.md: invented MPNs, zero."""

    def test_every_non_generic_part_has_a_real_mpn(self, catalog):
        for spec in catalog.all_parts():
            if not spec.is_generic:
                assert spec.mpn, f"{spec.part_id} claims to be a real part with no MPN"
                assert spec.manufacturer, f"{spec.mpn} has no manufacturer"

    def test_generic_parts_claim_no_mpn(self, catalog):
        # A generic 4.7 kohm resistor has no meaningful part number, and making
        # one up would be exactly the failure the target forbids.
        for spec in catalog.all_parts():
            if spec.is_generic:
                assert spec.mpn is None, f"{spec.part_id} is generic but claims MPN {spec.mpn}"

    def test_a_non_generic_part_without_an_mpn_is_rejected(self):
        with pytest.raises(ValidationError, match="must carry a real MPN"):
            ComponentSpec(part_id="X", category=ComponentCategory.SENSOR, description="d")


class TestProvenanceHonesty:
    def test_hand_entered_facts_are_catalog_not_datasheet(self, catalog):
        """Nothing in the seed catalog claims a machine-verified citation.

        These values were typed in by a human from a datasheet. Labelling them
        DATASHEET_SUPPORTED would require a verbatim snippet confirmed against
        the real PDF, and writing one from memory is a fabricated citation.
        """
        for spec in catalog.all_parts():
            for evidence in _all_evidence(spec):
                assert evidence.kind is not EvidenceKind.DATASHEET, (
                    f"{spec.part_id} claims datasheet support for {evidence.label!r} "
                    "without a machine-verified snippet"
                )
                assert not evidence.provenance_machine_verified

    def test_catalog_facts_cite_a_document(self, catalog):
        for spec in catalog.all_parts():
            for evidence in _all_evidence(spec):
                if evidence.kind is EvidenceKind.CATALOG:
                    assert evidence.document is not None, evidence.label
                    assert evidence.status is ClaimStatus.CATALOG_REPORTED

    def test_estimates_are_marked_assumed(self, catalog):
        """Conservative figures entered by hand must not read as manufacturer data."""
        bme = catalog.require("BME280")
        current_evidence = [
            e
            for rail in bme.supply_rails
            for e in rail.evidence
            if e.quantity is not None and e.quantity.unit is Unit.AMPERE
        ]
        assert current_evidence
        assert all(e.status is ClaimStatus.ASSUMED for e in current_evidence)

    def test_values_that_could_not_be_sourced_are_absent_not_guessed(self, catalog):
        # The AP2112's absolute maximum input was not recorded, because it
        # could not be stated with confidence. Absent is the honest answer.
        ap2112 = catalog.require("AP2112K-3.3TRG1")
        assert ap2112.rail("VIN") is not None
        assert ap2112.rail("VIN").absolute_max is None


class TestSpecInvariants:
    def test_operating_range_cannot_exceed_absolute_maximum(self):
        with pytest.raises(ValidationError, match="exceeds absolute maximum"):
            SupplyRail(
                name="VDD",
                operating=ValueRange(minimum=V(1.71), maximum=V(5.0)),
                absolute_max=V(4.3),
            )

    def test_pins_referencing_an_unknown_rail_are_rejected(self):
        with pytest.raises(ValidationError, match="unknown supply rail"):
            ComponentSpec(
                part_id="X",
                mpn="X-1",
                manufacturer="Acme",
                category=ComponentCategory.SENSOR,
                description="d",
                pins=[
                    PinSpec(
                        number="1",
                        name="VDD",
                        roles=[PinRole.POWER],
                        electrical_type=PinElectricalType.POWER_IN,
                        supply_rail="NOPE",
                    )
                ],
            )

    def test_duplicate_pin_numbers_are_rejected(self):
        with pytest.raises(ValidationError, match="duplicate pin numbers"):
            ComponentSpec(
                part_id="X",
                mpn="X-1",
                manufacturer="Acme",
                category=ComponentCategory.SENSOR,
                description="d",
                pins=[
                    PinSpec(number="1", name="A"),
                    PinSpec(number="1", name="B"),
                ],
            )

    def test_a_regulator_spec_on_a_non_regulator_is_rejected(self):
        from ohmni.domain import RegulatorSpec

        with pytest.raises(ValidationError, match="not a regulator"):
            ComponentSpec(
                part_id="X",
                mpn="X-1",
                manufacturer="Acme",
                category=ComponentCategory.SENSOR,
                description="d",
                regulator=RegulatorSpec(
                    output_voltage=ValueRange.exact(V(3.3)),
                    output_current_max=Quantity.amps(0.6),
                    input_voltage=ValueRange(minimum=V(2.5), maximum=V(6.0)),
                ),
            )

    def test_duplicate_i2c_addresses_on_one_part_are_rejected(self):
        from ohmni.domain import I2CAddressOption

        with pytest.raises(ValidationError, match="same I2C address twice"):
            ComponentSpec(
                part_id="X",
                mpn="X-1",
                manufacturer="Acme",
                category=ComponentCategory.SENSOR,
                description="d",
                i2c_addresses=[
                    I2CAddressOption(address=0x76),
                    I2CAddressOption(address=0x76),
                ],
            )


class TestGoldenFixtureParts:
    """The specific facts the golden circuit's verdicts depend on."""

    def test_bme280_has_two_independent_supply_domains(self, catalog):
        # The case the specification's flat supply fields could not represent.
        bme = catalog.require("BME280")
        assert {r.name for r in bme.supply_rails} == {"VDD", "VDDIO"}
        assert bme.rail("VDD").operating.minimum == V(1.71)
        assert bme.rail("VDDIO").operating.minimum == V(1.2)

    def test_bme280_separates_operating_from_absolute_max(self, catalog):
        vdd = catalog.require("BME280").rail("VDD")
        assert vdd.operating.maximum == V(3.6)
        assert vdd.absolute_max == V(4.3)
        assert vdd.absolute_max > vdd.operating.maximum

    def test_bme280_has_two_address_options_with_straps(self, catalog):
        options = catalog.require("BME280").i2c_addresses
        assert {o.address for o in options} == {0x76, 0x77}
        assert all(o.strap_pin == "5" for o in options)
        assert {o.strap_level for o in options} == {"low", "high"}

    def test_esp32_peak_current_makes_regulator_sizing_real(self, catalog):
        rail = catalog.require("ESP32-WROOM-32E").rail("VDD")
        assert rail.current_max == Quantity.amps(0.5)

    def test_the_two_regulators_differ_in_the_way_that_matters(self, catalog):
        good = catalog.require("AP2112K-3.3TRG1").regulator
        undersized = catalog.require("MCP1700T-3302E-TT").regulator
        assert good.output_current_max > Quantity.amps(0.5)
        assert undersized.output_current_max < Quantity.amps(0.5)

    def test_esp32_enable_has_no_internal_pull(self, catalog):
        en = next(p for p in catalog.require("ESP32-WROOM-32E").pins if p.name == "EN")
        assert en.must_not_float is True
        assert en.internal_pull is None

    def test_strapping_pins_record_their_internal_pulls(self, catalog):
        esp = catalog.require("ESP32-WROOM-32E")
        strapping = [p for p in esp.pins if p.has_role(PinRole.BOOT_STRAP)]
        assert len(strapping) == 5
        assert all(p.internal_pull in ("up", "down") for p in strapping)

    def test_usb_c_pin_count_matches_its_package(self, catalog):
        usb = catalog.require("USB_C_RECEPTACLE_16P")
        package: PackageOption = usb.packages[0]
        assert package.pin_count == len(usb.pins) == 16

    def test_usb_c_vbus_pins_are_passive_not_power_outputs(self, catalog):
        # A receptacle does not generate VBUS. Four paralleled power outputs on
        # one net would read as driver contention.
        usb = catalog.require("USB_C_RECEPTACLE_16P")
        for pin in usb.pins_with_role(PinRole.USB_VBUS):
            assert pin.electrical_type is PinElectricalType.PASSIVE

    def test_lga_package_is_marked_not_hand_solderable(self, catalog):
        assert catalog.require("BME280").package("LGA-8").hand_solderable is False


def _all_evidence(spec: ComponentSpec):
    yield from spec.evidence
    for rail in spec.supply_rails:
        yield from rail.evidence
    for pin in spec.pins:
        yield from pin.evidence
    for dec in spec.decoupling_rules:
        yield from dec.evidence
    for design_rule in spec.design_rules:
        yield from design_rule.evidence
    if spec.regulator:
        yield from spec.regulator.evidence
    if spec.led:
        yield from spec.led.evidence
