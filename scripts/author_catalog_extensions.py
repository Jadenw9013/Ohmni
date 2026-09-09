"""Author bounded A2/A3 catalog additions from inspected manufacturer sources.

Run separately from author_catalog.py. Only these three records are written.
All transcribed manufacturer facts stay CATALOG_REPORTED. Operating allowances
and the generic switch's behavior stay ASSUMED; no PDF-ingestion claim is made.
"""

from __future__ import annotations

import json
from pathlib import Path

from ohmni.domain import (
    ComponentCategory,
    ComponentSpec,
    DecouplingRule,
    DesignRule,
    DocumentRef,
    I2CAddressOption,
    Interface,
    Lifecycle,
    PackageOption,
    PinElectricalType,
    PinRole,
    PinSpec,
    Quantity,
    SupplyRail,
    ValueRange,
    assumed_evidence,
    catalog_evidence,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "src/ohmni/catalog/data/parts"
EEPROM_DOC = DocumentRef(
    document_id="microchip-25lc256-ds20001822h", title="25AA256/25LC256 Data Sheet",
    manufacturer="Microchip Technology", part_number="25LC256", revision="DS20001822H (2019)",
    url="https://ww1.microchip.com/downloads/en/DeviceDoc/25AA256-25LC256-256K-SPI-Bus-Serial-EEPROM-20001822H.pdf",
)
EEPROM_USAGE = DocumentRef(
    document_id="microchip-an1040", title="Recommended Usage of Microchip SPI Serial EEPROM Devices",
    manufacturer="Microchip Technology", revision="DS01040A (2006)",
    url="https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ApplicationNotes/ApplicationNotes/01040A.pdf",
)
TMP102_DOC = DocumentRef(
    document_id="ti-tmp102-sbos397i", title="TMP102 Low-Power Digital Temperature Sensor",
    manufacturer="Texas Instruments", part_number="TMP102", revision="SBOS397I (June 2024)",
    url="https://www.ti.com/lit/ds/symlink/tmp102.pdf",
)
V = Quantity.volts
A = Quantity.amps


def spi_eeprom() -> ComponentSpec:
    pinout = (
        ("1", "CS", PinRole.SPI_CS, PinElectricalType.INPUT),
        ("2", "SO", PinRole.SPI_MISO, PinElectricalType.TRI_STATE),
        ("3", "WP", PinRole.OTHER, PinElectricalType.INPUT),
        ("4", "VSS", PinRole.GROUND, PinElectricalType.POWER_IN),
        ("5", "SI", PinRole.SPI_MOSI, PinElectricalType.INPUT),
        ("6", "SCK", PinRole.SPI_SCK, PinElectricalType.INPUT),
        ("7", "HOLD", PinRole.OTHER, PinElectricalType.INPUT),
        ("8", "VCC", PinRole.POWER, PinElectricalType.POWER_IN),
    )
    pins = []
    for number, name, role, electrical_type in pinout:
        pins.append(PinSpec(
            number=number, name=name, roles=[role], electrical_type=electrical_type,
            supply_rail=None if role is PinRole.GROUND else "VCC",
            absolute_max_above_supply=V(1) if number not in {"4", "8"} else None,
            must_not_float=True if number in {"1", "3", "7"} else None,
            notes=("Active-low control; provide a defined idle level."
                   if number in {"1", "3", "7"} else
                   "SO is high impedance while CS is high; firmware must deselect other bus devices."
                   if number == "2" else None),
            evidence=[catalog_evidence(f"25LC256 pin {number} ({name})", document=EEPROM_DOC,
                                       page=1, text_value=f"SOIC pin {number}: {name}")]
                     + ([catalog_evidence("SO deselected high-impedance behavior",
                                          document=EEPROM_DOC, page=13)] if number == "2" else [])
                     + ([catalog_evidence("25LC256 I/O absolute limit relative to VCC",
                                          document=EEPROM_DOC, page=2,
                                          text_value="All inputs and outputs: -0.6 V to VCC + 1.0 V")]
                        if number not in {"4", "8"} else []),
        ))
    return ComponentSpec(
        part_id="25LC256-I/SN", mpn="25LC256-I/SN", manufacturer="Microchip Technology",
        category=ComponentCategory.MEMORY, lifecycle=Lifecycle.ACTIVE, datasheet=EEPROM_DOC,
        description="256-kbit SPI EEPROM, 32 KiB, in the industrial-temperature SOIC-8 package.",
        interfaces=[Interface.SPI], packages=[PackageOption(
            name="SOIC-8", pin_count=8, hand_solderable=True,
            kicad_footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            notes="SN narrow SOIC package; order-code mapping is in DS20001822H page 29.",
        )], pins=pins,
        supply_rails=[SupplyRail(
            name="VCC", operating=ValueRange(minimum=V(2.5), maximum=V(5.5)),
            absolute_max=V(6.5), current_max=A(0.006),
            evidence=[
                catalog_evidence("25LC256 operating supply", document=EEPROM_DOC, page=1,
                                 text_value="VCC operating range: 2.5 to 5.5 V"),
                catalog_evidence("25LC256 absolute supply limit", document=EEPROM_DOC, page=2,
                                 quantity=V(6.5)),
                assumed_evidence("EEPROM current allowance for the 3.3 V archetype", quantity=A(0.006),
                                 detail="The 6 mA read maximum is specified at 5.5 V and 10 MHz in DS20001822H page 2. "
                                        "Using it as an allowance at 3.3 V is an explicit design assumption, not a measured "
                                        "or manufacturer-guaranteed 3.3 V peak. Output-load current is separate."),
            ],
        )],
        decoupling_rules=[DecouplingRule(
            rail="VCC", per_pin_capacitance=Quantity.farads(100e-9),
            note="Manufacturer application-note recommendation; no numeric placement distance is specified.",
            evidence=[catalog_evidence("SPI EEPROM bypass recommendation", document=EEPROM_USAGE,
                                       page=1, quantity=Quantity.farads(100e-9))],
        )],
        design_rules=[
            DesignRule(rule_id="25lc256.control_idle", category="other",
                       description="Provide a CS pull-up for startup and hold unused active-low HOLD/WP controls high.",
                       evidence=[catalog_evidence("SPI EEPROM control-pin guidance", document=EEPROM_USAGE, page=2)]),
            DesignRule(rule_id="25lc256.firmware", category="firmware",
                       description="At 3.3 V use an SPI clock no greater than 5 MHz; issue write-enable and poll write-in-progress. "
                                   "A page write is limited to 64 bytes. Static wiring checks do not execute these operations.",
                       evidence=[catalog_evidence("SPI clock ceiling at 2.5 to below 4.5 V", document=EEPROM_DOC, page=3),
                                 catalog_evidence("EEPROM page-write protocol", document=EEPROM_DOC, page=6)]),
        ],
        evidence=[catalog_evidence("Industrial SN order-code selection", document=EEPROM_DOC, page=29,
                                   text_value="25LC256-I/SN: industrial temperature, narrow SOIC-8")],
    )


def temperature_sensor() -> ComponentSpec:
    pinout = (
        ("1", "SCL", PinRole.I2C_SCL, PinElectricalType.INPUT),
        ("2", "GND", PinRole.GROUND, PinElectricalType.POWER_IN),
        ("3", "ALERT", PinRole.OTHER, PinElectricalType.OPEN_COLLECTOR),
        ("4", "ADD0", PinRole.I2C_ADDRESS_SELECT, PinElectricalType.INPUT),
        ("5", "V+", PinRole.POWER, PinElectricalType.POWER_IN),
        ("6", "SDA", PinRole.I2C_SDA, PinElectricalType.OPEN_COLLECTOR),
    )
    pins = [PinSpec(
        number=number, name=name, roles=[role], electrical_type=electrical_type,
        supply_rail=None if role is PinRole.GROUND else "V+",
        absolute_max=V(4) if number in {"1", "4", "6"} else None,
        absolute_max_above_supply=V(0.3) if number == "3" else None,
        must_not_float=True if number == "4" else None,
        notes="Open-drain output; requires an external pull-up when used." if number in {"3", "6"} else None,
        evidence=[catalog_evidence(f"TMP102 pin {number} ({name})", document=TMP102_DOC, page=3)]
                 + ([catalog_evidence("TMP102 signal absolute limits", document=TMP102_DOC,
                                      page=4, text_value="SCL/SDA/ADD0: 4 V; ALERT: V+ + 0.3 V, at most 4 V")]
                    if number in {"1", "3", "4", "6"} else []),
    ) for number, name, role, electrical_type in pinout]
    return ComponentSpec(
        part_id="TMP102AIDRLR", mpn="TMP102AIDRLR", manufacturer="Texas Instruments",
        category=ComponentCategory.SENSOR, lifecycle=Lifecycle.ACTIVE, datasheet=TMP102_DOC,
        description="Low-power I2C temperature sensor in the six-pin SOT-563 DRL package.",
        interfaces=[Interface.I2C], packages=[PackageOption(
            name="SOT-563", pin_count=6, hand_solderable=False,
            kicad_footprint="Package_TO_SOT_SMD:SOT-563",
            notes="Fine-pitch package: assembly guidance requires surface-mount equipment and review.",
        )], pins=pins,
        supply_rails=[SupplyRail(
            name="V+", operating=ValueRange(minimum=V(1.4), typical=V(3.3), maximum=V(3.6)),
            absolute_max=V(4), current_max=A(100e-6),
            evidence=[
                catalog_evidence("TMP102 operating and absolute supply ratings", document=TMP102_DOC, page=4,
                                 text_value="Operating 1.4 to 3.6 V; absolute maximum 4 V"),
                assumed_evidence("TMP102 supply-current allowance", quantity=A(100e-6),
                                 detail="100 uA is an authored allowance, not a manufacturer peak-current specification. "
                                        "SBOS397I page 5 gives mode-dependent average currents: 7.5 uA maximum with an "
                                        "inactive bus at the default rate, and 40 uA typical at a 2.85 MHz active bus. "
                                        "Output pull-up currents and transient peaks need separate review."),
            ],
        )],
        i2c_addresses=[
            I2CAddressOption(address=0x48, selected_by="ADD0 connected to GND", strap_pin="4", strap_level="low", is_default=True),
            I2CAddressOption(address=0x49, selected_by="ADD0 connected to V+", strap_pin="4", strap_level="high"),
            I2CAddressOption(address=0x4A, selected_by="ADD0 connected to SDA; not supported by the low/high strap compiler", strap_pin="4"),
            I2CAddressOption(address=0x4B, selected_by="ADD0 connected to SCL; not supported by the low/high strap compiler", strap_pin="4"),
        ],
        decoupling_rules=[DecouplingRule(
            rail="V+", per_pin_capacitance=Quantity.farads(10e-9),
            note="Place near the supply/ground pins; manufacturer gives no numeric maximum distance.",
            evidence=[catalog_evidence("TMP102 supply bypass recommendation", document=TMP102_DOC, page=21,
                                       quantity=Quantity.farads(10e-9))],
        )],
        design_rules=[
            DesignRule(rule_id="tmp102.address", category="other",
                       description="ADD0 selects one of four addresses. The current strap compiler can represent only GND and V+ choices.",
                       evidence=[catalog_evidence("TMP102 address selection", document=TMP102_DOC, page=11)]),
            DesignRule(rule_id="tmp102.pullups", category="other",
                       description="Used SDA/ALERT open-drain outputs need pull-ups. Review bus capacitance and timing; keep pull-up sink current within 3 mA.",
                       evidence=[catalog_evidence("TMP102 pull-up guidance", document=TMP102_DOC, page=20)]),
            DesignRule(rule_id="tmp102.thermal", category="layout",
                       description="Measured temperature depends on package/board thermal coupling. Position away from unwanted heat sources for ambient measurements.",
                       evidence=[catalog_evidence("TMP102 thermal and layout guidance", document=TMP102_DOC, page=22)]),
        ],
    )


def momentary_button() -> ComponentSpec:
    return ComponentSpec(
        part_id="GENERIC_MOMENTARY_BUTTON", category=ComponentCategory.SWITCH, is_generic=True,
        description="Generic normally-open momentary pushbutton with two electrical terminals.",
        packages=[PackageOption(
            name="6mm-THT", pin_count=2, hand_solderable=True,
            kicad_footprint="Button_Switch_THT:SW_PUSH_6mm",
            notes="Four physical legs form two permanently joined pairs. Confirm the chosen switch matches this land pattern.",
        )],
        pins=[PinSpec(number=str(number), name=f"T{number}", roles=[PinRole.TERMINAL],
                      electrical_type=PinElectricalType.PASSIVE) for number in (1, 2)],
        evidence=[assumed_evidence("Generic momentary contact behavior",
                                   detail="The chosen switch is assumed normally open and closed only while pressed. "
                                          "There is no selected manufacturer part, contact rating, debounce model, or life rating.")],
        design_rules=[DesignRule(rule_id="button.debounce", category="firmware",
                                 description="Mechanical contacts can bounce. Firmware must debounce the input; static checks do not simulate button presses.")],
    )


BUILDERS = (spi_eeprom, temperature_sensor, momentary_button)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for builder in BUILDERS:
        spec = builder()
        # Slash is an order-code delimiter, not a catalog directory separator.
        filename = spec.part_id.replace("/", "_") + ".json"
        payload = spec.model_dump(mode="json", exclude_none=True)
        (OUT_DIR / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {filename}")


if __name__ == "__main__":
    main()
