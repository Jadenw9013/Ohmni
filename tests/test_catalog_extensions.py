"""Catalog expansion keeps electrical facts, assumptions and pad lineage explicit."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from ohmni.adapters.tools import find_kicad_cli
from ohmni.catalog.loader import default_catalog
from ohmni.domain import (
    CircuitComponent,
    CircuitIR,
    ClaimStatus,
    Interface,
    Net,
    PinElectricalType,
    PinRef,
    PinRole,
)
from ohmni.eda.kicad import KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.physical.footprints import footprint
from ohmni.physical.models import BoardConstraints, BoardOutline, ComponentPlacement

CATALOG_PACKAGES = [
    (spec.part_id, package.name)
    for spec in default_catalog().all_parts() for package in spec.packages
]
NEW_FOOTPRINTS = [
    "Package_TO_SOT_SMD:SOT-23", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "Package_TO_SOT_SMD:SOT-563", "Button_Switch_THT:SW_PUSH_6mm",
    "LED_SMD:LED_0603_1608Metric",
] + [
    f"{family}_SMD:{letter}_{package}"
    for family, letter in (("Resistor", "R"), ("Capacitor", "C"))
    for package in ("0402_1005Metric", "0603_1608Metric", "1206_3216Metric")
]


def test_seed_authoring_preserves_package_mapping_and_accepted_bme_pin_mode(catalog):
    from scripts.author_catalog import (
        bme280,
        generic_capacitor,
        generic_led_green,
        generic_resistor,
    )

    for builder in (generic_capacitor, generic_resistor, generic_led_green, bme280):
        authored = builder()
        assert [(p.name, p.kicad_footprint) for p in authored.packages] == [
            (p.name, p.kicad_footprint) for p in catalog.require(authored.part_id).packages
        ]
    assert bme280().pin("5") == catalog.require("BME280").pin("5")


def test_eeprom_roles_support_voltage_and_shared_bus_checks(catalog):
    part = catalog.require("25LC256-I/SN")
    assert part.interfaces == [Interface.SPI]
    assert [(p.number, p.name) for p in part.pins] == [
        ("1", "CS"), ("2", "SO"), ("3", "WP"), ("4", "VSS"),
        ("5", "SI"), ("6", "SCK"), ("7", "HOLD"), ("8", "VCC"),
    ]
    assert part.pin("2").electrical_type is PinElectricalType.TRI_STATE
    for number, role in (("1", PinRole.SPI_CS), ("2", PinRole.SPI_MISO),
                         ("5", PinRole.SPI_MOSI), ("6", PinRole.SPI_SCK)):
        assert role in part.pin(number).roles
        assert part.pin(number).supply_rail == "VCC"
    assert all(part.pin(n).must_not_float for n in ("1", "3", "7"))
    assert part.pin("8").roles == [PinRole.POWER]
    assert part.pin("8").electrical_type is PinElectricalType.POWER_IN
    assert part.supply_rails[0].operating.minimum.value == 2.5
    assert part.supply_rails[0].operating.maximum.value == 5.5
    assert part.decoupling_rules[0].per_pin_capacitance.value == pytest.approx(100e-9)


def test_tmp102_pinout_limits_and_address_options(catalog):
    part = catalog.require("TMP102AIDRLR")
    assert [(p.number, p.name) for p in part.pins] == [
        ("1", "SCL"), ("2", "GND"), ("3", "ALERT"),
        ("4", "ADD0"), ("5", "V+"), ("6", "SDA"),
    ]
    assert part.pin("6").electrical_type is PinElectricalType.OPEN_COLLECTOR
    assert part.pin("4").must_not_float
    assert part.supply_rails[0].operating.maximum.value == 3.6
    assert part.pin("3").absolute_max_above_supply.value == .3
    assert part.decoupling_rules[0].per_pin_capacitance.value == pytest.approx(10e-9)
    assert [(a.address, a.strap_level) for a in part.i2c_addresses] == [
        (0x48, "low"), (0x49, "high"), (0x4A, None), (0x4B, None),
    ]
    address_rule = next(rule for rule in part.design_rules if rule.rule_id == "tmp102.address")
    assert address_rule.evidence[0].page == 11


@pytest.mark.parametrize("part_id", ["25LC256-I/SN", "TMP102AIDRLR"])
def test_current_allowances_are_assumptions_not_peak_specifications(catalog, part_id):
    rail = catalog.require(part_id).supply_rails[0]
    current_evidence = [e for e in rail.evidence if e.quantity == rail.current_max]
    assert current_evidence
    assert all(e.status is ClaimStatus.ASSUMED for e in current_evidence)
    assert all("not a" in e.detail for e in current_evidence)


def test_generic_button_has_two_contacts_and_no_invented_part_rating(catalog):
    part = catalog.require("GENERIC_MOMENTARY_BUTTON")
    assert part.is_generic and part.mpn is None and part.datasheet is None
    assert len(part.pins) == 2
    assert all(p.roles == [PinRole.TERMINAL] for p in part.pins)
    assert all(p.electrical_type is PinElectricalType.PASSIVE for p in part.pins)
    assert all(e.status is ClaimStatus.ASSUMED for e in part.evidence)
    fp = footprint(part.packages[0].kicad_footprint)
    assert [p.number for p in fp.pads] == ["1", "1", "2", "2"]
    assert "translated by (-3.25, -2.25)" in fp.source.derivation
    assert all(min(p.width_mm, p.height_mm) * .55 == 1.1 for p in fp.pads)


@pytest.mark.parametrize("part_id,package_name", CATALOG_PACKAGES)
def test_every_offered_package_compiles_with_complete_pin_binding(
    catalog, tmp_path, part_id, package_name,
):
    spec = catalog.require(part_id)
    package = spec.package(package_name)
    assert package.kicad_footprint, f"{part_id}/{package_name} offers no footprint"
    definition = footprint(package.kicad_footprint)
    assert definition is not None
    circuit = CircuitIR(
        ir_id="package-coverage", name="Package compilation coverage",
        components=[CircuitComponent(ref="U1", part_id=part_id, package=package_name)],
        nets=[Net(name=f"PIN_{p.number}", connections=[PinRef(component="U1", pin=p.number)])
              for p in spec.pins],
    )
    schematic = KiCadSchematicCompiler(catalog).compile(circuit, tmp_path / "part.kicad_sch")
    constraints = BoardConstraints(
        outline=BoardOutline(width_mm=80, height_mm=80),
        placements=[ComponentPlacement(component_ref="U1", x_mm=40, y_mm=40,
                                       reason="Isolated package compilation test")],
    )
    pcb = KiCadPcbCompiler(catalog).compile(
        circuit, schematic, constraints, tmp_path / "part.kicad_pcb",
    )
    assert pcb.is_current
    assert pcb.compilation.physical_verification.passed
    assert {b.pin_number for b in pcb.compilation.pad_bindings} == {p.number for p in spec.pins}
    assert len(re.findall(r'\(pad "', pcb.path.read_text())) == len(definition.pads)
    for binding in pcb.compilation.pad_bindings:
        assert binding.net_name == f"PIN_{binding.pin_number}"


@pytest.mark.parametrize("footprint_id", NEW_FOOTPRINTS)
def test_new_placement_envelopes_contain_all_copper_lands(footprint_id):
    fp = footprint(footprint_id)
    for pad in fp.pads:
        assert abs(pad.x_mm) + pad.width_mm / 2 <= fp.width_mm / 2
        assert abs(pad.y_mm) + pad.height_mm / 2 <= fp.height_mm / 2


@pytest.mark.integration
@pytest.mark.parametrize("footprint_id", NEW_FOOTPRINTS)
def test_new_geometry_matches_pinned_kicad_source(footprint_id):
    executable = find_kicad_cli()
    if executable is None:
        pytest.skip("KiCad not installed")
    libraries = Path(executable).resolve().parent.parent / "share/kicad/footprints"
    library, name = footprint_id.split(":")
    source = libraries / f"{library}.pretty" / f"{name}.kicad_mod"
    if not source.is_file():
        pytest.skip("KiCad footprint library not installed beside CLI")
    raw = source.read_bytes()
    fp = footprint(footprint_id)
    if hashlib.sha256(raw).hexdigest() != fp.source.upstream_file_sha256:
        pytest.skip("Installed library revision differs from the pinned source")
    source_pads = re.findall(
        r'\(pad "([^"]+)" (smd|thru_hole) (\S+)\s*\(at ([^)]*)\)\s*\(size ([^)]*)\)',
        raw.decode(),
    )
    assert len(source_pads) == len(fp.pads)
    for (number, kind, shape, at, size), actual in zip(source_pads, fp.pads, strict=True):
        xy = [float(v) for v in at.split()]
        wh = [float(v) for v in size.split()]
        if footprint_id == "Button_Switch_THT:SW_PUSH_6mm":
            xy[0] -= 3.25
            xy[1] -= 2.25
        assert (number, kind, shape) == (actual.number, actual.kind, actual.shape)
        assert [actual.x_mm, actual.y_mm, actual.width_mm, actual.height_mm] == pytest.approx(
            [*xy[:2], *wh],
        )
