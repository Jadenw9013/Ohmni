"""Authoring script for the seed part catalog.

The catalog's storage format is JSON, because the datasheet extractor will
eventually write into the same format. But hand-writing a 39-pin module as JSON
is an invitation to typos in exactly the data the verifier trusts most, so the
seed entries are authored here in typed Python -- where Pydantic validates every
field and the pin tables can be built with loops -- and emitted to JSON.

Run:  python scripts/author_catalog.py

Provenance policy
-----------------
Every fact below was hand-entered from the manufacturer's datasheet, so it is
recorded with ``catalog_evidence`` (status CATALOG_REPORTED) and never with
``datasheet_evidence`` (status DATASHEET_SUPPORTED). The latter demands a
verbatim snippet that has been mechanically confirmed against the actual PDF;
writing a "verbatim" snippet from memory would be a fabricated citation.

Values I could not state with confidence are left as ``None``. That makes the
relevant rule report INSUFFICIENT_DATA, which is the correct and honest outcome.
Values that are deliberate conservative estimates are recorded with
``assumed_evidence`` so they read as ASSUMED, not as a manufacturer figure.
"""

from __future__ import annotations

import json
from pathlib import Path

from proofboard.domain import (
    ComponentCategory,
    ComponentSpec,
    DecouplingRule,
    DesignRule,
    DocumentRef,
    I2CAddressOption,
    Interface,
    LedSpec,
    Lifecycle,
    PackageOption,
    PinElectricalType,
    PinRole,
    PinSpec,
    Quantity,
    RegulatorSpec,
    SupplyRail,
    ValueRange,
    assumed_evidence,
    catalog_evidence,
)

OUT_DIR = Path(__file__).resolve().parents[1] / "src" / "proofboard" / "catalog" / "data" / "parts"

V = Quantity.volts
A = Quantity.amps


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------

ESP32_DOC = DocumentRef(
    document_id="esp32-wroom-32e-datasheet",
    title="ESP32-WROOM-32E / ESP32-WROOM-32UE Datasheet",
    manufacturer="Espressif Systems",
    part_number="ESP32-WROOM-32E",
    revision="v1.6",
)

AP2112_DOC = DocumentRef(
    document_id="ap2112-datasheet",
    title="AP2112 600mA CMOS LDO Regulator With Enable",
    manufacturer="Diodes Incorporated",
    part_number="AP2112K-3.3TRG1",
)

BME280_DOC = DocumentRef(
    document_id="bme280-datasheet",
    title="BME280 Combined humidity and pressure sensor",
    manufacturer="Bosch Sensortec",
    part_number="BME280",
)

MCP1700_DOC = DocumentRef(
    document_id="mcp1700-datasheet",
    title="MCP1700 Low Quiescent Current LDO",
    manufacturer="Microchip Technology",
    part_number="MCP1700T-3302E/TT",
)

USB_C_DOC = DocumentRef(
    document_id="usb-type-c-spec",
    title="USB Type-C Cable and Connector Specification",
    manufacturer="USB Implementers Forum",
    part_number="USB Type-C receptacle (generic)",
)


# --------------------------------------------------------------------------
# ESP32-WROOM-32E
# --------------------------------------------------------------------------

# Full 38-pin module pinout plus the exposed ground pad (pin 39), so the
# package pin-count consistency rule has real data to check against.
_ESP32_PINS: list[tuple[str, str, list[PinRole], PinElectricalType]] = [
    ("1", "GND", [PinRole.GROUND], PinElectricalType.POWER_IN),
    ("2", "3V3", [PinRole.POWER], PinElectricalType.POWER_IN),
    ("3", "EN", [PinRole.ENABLE], PinElectricalType.INPUT),
    ("4", "SENSOR_VP", [PinRole.ANALOG_IN], PinElectricalType.INPUT),
    ("5", "SENSOR_VN", [PinRole.ANALOG_IN], PinElectricalType.INPUT),
    ("6", "IO34", [PinRole.ANALOG_IN], PinElectricalType.INPUT),
    ("7", "IO35", [PinRole.ANALOG_IN], PinElectricalType.INPUT),
    ("8", "IO32", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("9", "IO33", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("10", "IO25", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("11", "IO26", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("12", "IO27", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("13", "IO14", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("14", "IO12", [PinRole.GPIO, PinRole.BOOT_STRAP], PinElectricalType.BIDIRECTIONAL),
    ("15", "GND", [PinRole.GROUND], PinElectricalType.POWER_IN),
    ("16", "IO13", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("17", "SHD/SD2", [PinRole.OTHER], PinElectricalType.BIDIRECTIONAL),
    ("18", "SWP/SD3", [PinRole.OTHER], PinElectricalType.BIDIRECTIONAL),
    ("19", "SCS/CMD", [PinRole.OTHER], PinElectricalType.BIDIRECTIONAL),
    ("20", "SCK/CLK", [PinRole.OTHER], PinElectricalType.BIDIRECTIONAL),
    ("21", "SDO/SD0", [PinRole.OTHER], PinElectricalType.BIDIRECTIONAL),
    ("22", "SDI/SD1", [PinRole.OTHER], PinElectricalType.BIDIRECTIONAL),
    ("23", "IO15", [PinRole.GPIO, PinRole.BOOT_STRAP], PinElectricalType.BIDIRECTIONAL),
    ("24", "IO2", [PinRole.GPIO, PinRole.BOOT_STRAP], PinElectricalType.BIDIRECTIONAL),
    ("25", "IO0", [PinRole.GPIO, PinRole.BOOT_STRAP], PinElectricalType.BIDIRECTIONAL),
    ("26", "IO4", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("27", "IO16", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("28", "IO17", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("29", "IO5", [PinRole.GPIO, PinRole.BOOT_STRAP], PinElectricalType.BIDIRECTIONAL),
    ("30", "IO18", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("31", "IO19", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("32", "NC", [PinRole.NOT_CONNECTED], PinElectricalType.NO_CONNECT),
    ("33", "IO21", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("34", "RXD0", [PinRole.UART_RX, PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("35", "TXD0", [PinRole.UART_TX, PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("36", "IO22", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("37", "IO23", [PinRole.GPIO], PinElectricalType.BIDIRECTIONAL),
    ("38", "GND", [PinRole.GROUND], PinElectricalType.POWER_IN),
    ("39", "GND_PAD", [PinRole.GROUND], PinElectricalType.POWER_IN),
]


def esp32_wroom_32e() -> ComponentSpec:
    pins = [
        PinSpec(
            number=number,
            name=name,
            roles=roles,
            electrical_type=etype,
            # Every I/O and power pin on this module references the single 3V3
            # rail. That link is what lets the voltage rules resolve a pin's
            # logic domain from the rail's *derived* net voltage.
            supply_rail=None if PinRole.GROUND in roles else "VDD",
        )
        for number, name, roles, etype in _ESP32_PINS
    ]
    # EN has no internal pull on this module: it is the classic
    # floating-control-pin failure and must be held externally.
    #
    # The strapping pins do have documented internal pulls, which set the
    # default boot mode. Recording them means the verifier can tell "this pin
    # has a defined level from the part itself" apart from "this pin floats",
    # instead of reporting five errors on a perfectly ordinary module.
    internal_pulls = {"IO0": "up", "IO2": "down", "IO5": "up", "IO12": "down", "IO15": "up"}
    for pin in pins:
        if pin.name == "EN":
            pin.must_not_float = True
            pin.notes = (
                "No internal pull. Espressif's reference design uses a 10 kohm pull-up to 3V3 "
                "with a 100 nF capacitor to ground, so the module leaves reset only once the "
                "supply is stable."
            )
        elif pin.name in internal_pulls:
            pin.internal_pull = internal_pulls[pin.name]

    return ComponentSpec(
        part_id="ESP32-WROOM-32E",
        mpn="ESP32-WROOM-32E",
        manufacturer="Espressif Systems",
        category=ComponentCategory.MCU_MODULE,
        description="Wi-Fi + Bluetooth module with an integrated ESP32-D0WD-V3 SoC and 4 MB flash.",
        lifecycle=Lifecycle.ACTIVE,
        datasheet=ESP32_DOC,
        interfaces=[
            Interface.I2C,
            Interface.SPI,
            Interface.UART,
            Interface.GPIO,
            Interface.ADC,
            Interface.PWM,
        ],
        packages=[
            PackageOption(
                name="Module-SMD-38",
                pin_count=39,
                hand_solderable=True,
                kicad_footprint="RF_Module:ESP32-WROOM-32",
                notes="Castellated edge pads plus a central ground pad. Hand-solderable.",
            )
        ],
        pins=pins,
        supply_rails=[
            SupplyRail(
                name="VDD",
                operating=ValueRange(minimum=V(3.0), typical=V(3.3), maximum=V(3.6)),
                absolute_max=V(3.6),
                current_max=A(0.5),
                evidence=[
                    catalog_evidence(
                        "ESP32-WROOM-32E recommended operating supply voltage",
                        document=ESP32_DOC,
                        page=17,
                        text_value="VDD 3.0 V min, 3.3 V typical, 3.6 V max",
                    ),
                    catalog_evidence(
                        "ESP32-WROOM-32E recommended power supply current",
                        document=ESP32_DOC,
                        page=17,
                        quantity=A(0.5),
                        text_value="Recommended output current of the power supply: 500 mA",
                        detail=(
                            "This is the figure that makes regulator sizing a real check: the "
                            "module's RF transmit bursts are what set it, not its average draw."
                        ),
                    ),
                ],
                notes="Single 3.3 V domain. The module has no internal regulator.",
            )
        ],
        decoupling_rules=[
            DecouplingRule(
                rail="VDD",
                per_pin_capacitance=Quantity.farads(100e-9),
                bulk_capacitance=Quantity.farads(22e-6),
                max_distance_mm=5.0,
                note="Espressif hardware design guidelines recommend bulk plus local decoupling.",
                evidence=[
                    catalog_evidence(
                        "ESP32 recommended power supply decoupling",
                        document=ESP32_DOC,
                        page=17,
                        text_value="100 nF local decoupling with 22 uF bulk on the 3V3 rail",
                    )
                ],
            )
        ],
        design_rules=[
            DesignRule(
                rule_id="esp32.en_rc_delay",
                description=(
                    "EN needs a pull-up to 3V3 and an RC delay capacitor to ground so the module "
                    "releases reset only after the supply is stable."
                ),
                category="layout",
            ),
            DesignRule(
                rule_id="esp32.antenna_keepout",
                description=(
                    "Keep copper and components clear of the PCB antenna area. RF layout is "
                    "explicitly out of MVP scope and is NOT verified by this system."
                ),
                category="layout",
            ),
        ],
        evidence=[
            catalog_evidence(
                "ESP32-WROOM-32E package and pin count",
                document=ESP32_DOC,
                page=6,
                text_value="38-pin castellated SMD module with a central ground pad",
            )
        ],
    )


# --------------------------------------------------------------------------
# AP2112K-3.3 -- the regulator that is genuinely adequate for the ESP32
# --------------------------------------------------------------------------


def ap2112k_33() -> ComponentSpec:
    return ComponentSpec(
        part_id="AP2112K-3.3TRG1",
        mpn="AP2112K-3.3TRG1",
        manufacturer="Diodes Incorporated",
        category=ComponentCategory.REGULATOR_LINEAR,
        description="600 mA fixed 3.3 V CMOS LDO regulator with enable, SOT-23-5.",
        lifecycle=Lifecycle.ACTIVE,
        datasheet=AP2112_DOC,
        packages=[
            PackageOption(
                name="SOT-23-5",
                pin_count=5,
                hand_solderable=True,
                kicad_footprint="Package_TO_SOT_SMD:SOT-23-5",
            )
        ],
        pins=[
            PinSpec(
                number="1",
                name="VIN",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_IN,
                supply_rail="VIN",
            ),
            PinSpec(
                number="2",
                name="GND",
                roles=[PinRole.GROUND],
                electrical_type=PinElectricalType.POWER_IN,
            ),
            PinSpec(
                number="3",
                name="EN",
                roles=[PinRole.ENABLE],
                electrical_type=PinElectricalType.INPUT,
                supply_rail="VIN",
                must_not_float=True,
                notes="Tie to VIN for always-on operation. Must not be left floating.",
            ),
            PinSpec(
                number="4",
                name="NC",
                roles=[PinRole.NOT_CONNECTED],
                electrical_type=PinElectricalType.NO_CONNECT,
            ),
            PinSpec(
                number="5",
                name="VOUT",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_OUT,
            ),
        ],
        supply_rails=[
            SupplyRail(
                name="VIN",
                operating=ValueRange(minimum=V(2.5), maximum=V(6.0)),
                # Absolute maximum deliberately omitted: I could not state it with
                # confidence. A rule that needs it must report INSUFFICIENT_DATA
                # rather than assume one.
                absolute_max=None,
                evidence=[
                    catalog_evidence(
                        "AP2112 input voltage range",
                        document=AP2112_DOC,
                        page=4,
                        text_value="VIN operating range 2.5 V to 6.0 V",
                    )
                ],
            )
        ],
        regulator=RegulatorSpec(
            output_voltage=ValueRange(minimum=V(3.25), typical=V(3.3), maximum=V(3.35)),
            output_current_max=A(0.6),
            input_voltage=ValueRange(minimum=V(2.5), maximum=V(6.0)),
            dropout_at_max_current=V(0.25),
            quiescent_current=A(55e-6),
            evidence=[
                catalog_evidence(
                    "AP2112K-3.3 output voltage and current capability",
                    document=AP2112_DOC,
                    page=4,
                    text_value="3.3 V fixed output, +/-1.5% accuracy, 600 mA maximum output current",
                ),
                catalog_evidence(
                    "AP2112 dropout voltage",
                    document=AP2112_DOC,
                    page=4,
                    quantity=V(0.25),
                    text_value="Typical dropout 250 mV at 600 mA",
                ),
            ],
        ),
        decoupling_rules=[
            DecouplingRule(
                rail="VIN",
                per_pin_capacitance=Quantity.farads(1e-6),
                note="1 uF ceramic minimum on the input.",
                evidence=[
                    catalog_evidence(
                        "AP2112 recommended input capacitor",
                        document=AP2112_DOC,
                        page=8,
                        text_value="A 1 uF ceramic capacitor is recommended on VIN",
                    )
                ],
            )
        ],
    )


# --------------------------------------------------------------------------
# MCP1700-3302E -- deliberately undersized, for the broken variant
# --------------------------------------------------------------------------


def mcp1700_3302e() -> ComponentSpec:
    return ComponentSpec(
        part_id="MCP1700T-3302E-TT",
        mpn="MCP1700T-3302E/TT",
        manufacturer="Microchip Technology",
        category=ComponentCategory.REGULATOR_LINEAR,
        description="250 mA fixed 3.3 V LDO with very low quiescent current, SOT-23-3.",
        lifecycle=Lifecycle.ACTIVE,
        datasheet=MCP1700_DOC,
        packages=[
            PackageOption(
                name="SOT-23-3",
                pin_count=3,
                hand_solderable=True,
                kicad_footprint="Package_TO_SOT_SMD:SOT-23",
            )
        ],
        pins=[
            PinSpec(
                number="1",
                name="VOUT",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_OUT,
            ),
            PinSpec(
                number="2",
                name="GND",
                roles=[PinRole.GROUND],
                electrical_type=PinElectricalType.POWER_IN,
            ),
            PinSpec(
                number="3",
                name="VIN",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_IN,
                supply_rail="VIN",
            ),
        ],
        supply_rails=[
            SupplyRail(
                name="VIN",
                operating=ValueRange(minimum=V(2.3), maximum=V(6.0)),
                evidence=[
                    catalog_evidence(
                        "MCP1700 input voltage range",
                        document=MCP1700_DOC,
                        page=3,
                        text_value="Input voltage 2.3 V to 6.0 V",
                    )
                ],
            )
        ],
        regulator=RegulatorSpec(
            output_voltage=ValueRange(minimum=V(3.234), typical=V(3.3), maximum=V(3.366)),
            output_current_max=A(0.25),
            input_voltage=ValueRange(minimum=V(2.3), maximum=V(6.0)),
            dropout_at_max_current=V(0.178),
            quiescent_current=A(1.6e-6),
            evidence=[
                catalog_evidence(
                    "MCP1700 output current capability",
                    document=MCP1700_DOC,
                    page=3,
                    quantity=A(0.25),
                    text_value="250 mA maximum output current",
                )
            ],
        ),
    )


# --------------------------------------------------------------------------
# BME280 -- two independent supply domains, the case the flat model could not express
# --------------------------------------------------------------------------


def bme280() -> ComponentSpec:
    return ComponentSpec(
        part_id="BME280",
        mpn="BME280",
        manufacturer="Bosch Sensortec",
        category=ComponentCategory.SENSOR,
        description="Combined humidity, pressure and temperature sensor with I2C and SPI.",
        lifecycle=Lifecycle.ACTIVE,
        datasheet=BME280_DOC,
        interfaces=[Interface.I2C, Interface.SPI],
        packages=[
            PackageOption(
                name="LGA-8",
                pin_count=8,
                hand_solderable=False,
                kicad_footprint="Sensor:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClearanceHoles",
                notes=(
                    "2.5 x 2.5 x 0.93 mm LGA. Bottom-terminated: needs hot air or reflow. "
                    "A hobbyist with an iron should use a breakout module instead."
                ),
            )
        ],
        pins=[
            PinSpec(
                number="1",
                name="GND",
                roles=[PinRole.GROUND],
                electrical_type=PinElectricalType.POWER_IN,
            ),
            PinSpec(
                number="2",
                name="CSB",
                roles=[PinRole.SPI_CS],
                electrical_type=PinElectricalType.INPUT,
                supply_rail="VDDIO",
                must_not_float=True,
                notes="Tie high to select I2C mode. Floating leaves the interface undefined.",
            ),
            PinSpec(
                number="3",
                name="SDI",
                roles=[PinRole.I2C_SDA, PinRole.SPI_MOSI],
                electrical_type=PinElectricalType.BIDIRECTIONAL,
                supply_rail="VDDIO",
            ),
            PinSpec(
                number="4",
                name="SCK",
                roles=[PinRole.I2C_SCL, PinRole.SPI_SCK],
                electrical_type=PinElectricalType.INPUT,
                supply_rail="VDDIO",
            ),
            PinSpec(
                number="5",
                name="SDO",
                roles=[PinRole.I2C_ADDRESS_SELECT, PinRole.SPI_MISO],
                electrical_type=PinElectricalType.BIDIRECTIONAL,
                supply_rail="VDDIO",
                must_not_float=True,
                notes="In I2C mode this pin selects the address and must be tied high or low.",
            ),
            PinSpec(
                number="6",
                name="VDDIO",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_IN,
                supply_rail="VDDIO",
            ),
            PinSpec(
                number="7",
                name="GND",
                roles=[PinRole.GROUND],
                electrical_type=PinElectricalType.POWER_IN,
            ),
            PinSpec(
                number="8",
                name="VDD",
                roles=[PinRole.POWER],
                electrical_type=PinElectricalType.POWER_IN,
                supply_rail="VDD",
            ),
        ],
        supply_rails=[
            SupplyRail(
                name="VDD",
                operating=ValueRange(minimum=V(1.71), typical=V(1.8), maximum=V(3.6)),
                absolute_max=V(4.3),
                current_max=A(1e-3),
                evidence=[
                    catalog_evidence(
                        "BME280 VDD recommended operating range",
                        document=BME280_DOC,
                        page=10,
                        text_value="VDD supply voltage 1.71 V to 3.6 V",
                    ),
                    catalog_evidence(
                        "BME280 VDD absolute maximum rating",
                        document=BME280_DOC,
                        page=12,
                        quantity=V(4.3),
                        text_value="Voltage at supply pin VDD, maximum 4.3 V",
                        detail=(
                            "Absolute maximum, not an operating target. Exceeding it risks "
                            "permanent damage. Recorded separately from the operating range "
                            "so the two can never be confused."
                        ),
                    ),
                    assumed_evidence(
                        "BME280 worst-case supply current",
                        detail=(
                            "Conservative upper bound of 1 mA entered by hand for regulator "
                            "sizing. The datasheet figures for all documented measurement modes "
                            "are well below this. Marked ASSUMED, not a manufacturer figure."
                        ),
                        quantity=A(1e-3),
                    ),
                ],
            ),
            SupplyRail(
                name="VDDIO",
                operating=ValueRange(minimum=V(1.2), typical=V(1.8), maximum=V(3.6)),
                absolute_max=V(4.3),
                current_max=A(1e-3),
                evidence=[
                    catalog_evidence(
                        "BME280 VDDIO recommended operating range",
                        document=BME280_DOC,
                        page=10,
                        text_value="VDDIO interface supply voltage 1.2 V to 3.6 V",
                        detail=(
                            "A second, independent supply domain. This is the case the "
                            "specification's flat supply_voltage_min_v/max_v fields could not "
                            "represent."
                        ),
                    ),
                    assumed_evidence(
                        "BME280 worst-case interface supply current",
                        detail="Conservative upper bound of 1 mA entered by hand, as for VDD.",
                        quantity=A(1e-3),
                    ),
                ],
            ),
        ],
        i2c_addresses=[
            I2CAddressOption(
                address=0x76,
                selected_by="SDO tied to GND",
                strap_pin="5",
                strap_level="low",
                is_default=True,
            ),
            I2CAddressOption(
                address=0x77,
                selected_by="SDO tied to VDDIO",
                strap_pin="5",
                strap_level="high",
            ),
        ],
        decoupling_rules=[
            DecouplingRule(
                rail="VDD",
                per_pin_capacitance=Quantity.farads(100e-9),
                max_distance_mm=2.0,
                note="100 nF close to VDD.",
                evidence=[
                    catalog_evidence(
                        "BME280 recommended supply decoupling",
                        document=BME280_DOC,
                        page=38,
                        text_value="100 nF decoupling capacitor close to the VDD pin",
                    )
                ],
            ),
            DecouplingRule(
                rail="VDDIO",
                per_pin_capacitance=Quantity.farads(100e-9),
                max_distance_mm=2.0,
                note="100 nF close to VDDIO.",
            ),
        ],
    )


# --------------------------------------------------------------------------
# Generic parts. No MPN is claimed, so none is invented.
# --------------------------------------------------------------------------


def _two_terminal_pins() -> list[PinSpec]:
    return [
        PinSpec(
            number="1",
            name="1",
            roles=[PinRole.TERMINAL],
            electrical_type=PinElectricalType.PASSIVE,
        ),
        PinSpec(
            number="2",
            name="2",
            roles=[PinRole.TERMINAL],
            electrical_type=PinElectricalType.PASSIVE,
        ),
    ]


def _chip_packages() -> list[PackageOption]:
    return [
        PackageOption(name="0402", pin_count=2, hand_solderable=False),
        PackageOption(name="0603", pin_count=2, hand_solderable=True),
        PackageOption(name="0805", pin_count=2, hand_solderable=True),
        PackageOption(name="1206", pin_count=2, hand_solderable=True),
    ]


def generic_resistor() -> ComponentSpec:
    return ComponentSpec(
        part_id="GENERIC_RESISTOR",
        mpn=None,
        is_generic=True,
        category=ComponentCategory.RESISTOR,
        description="Generic chip resistor. Resistance is an instance value, not a part fact.",
        packages=_chip_packages(),
        pins=_two_terminal_pins(),
    )


def generic_capacitor() -> ComponentSpec:
    return ComponentSpec(
        part_id="GENERIC_CAPACITOR",
        mpn=None,
        is_generic=True,
        category=ComponentCategory.CAPACITOR,
        description="Generic MLCC. Capacitance is an instance value, not a part fact.",
        packages=_chip_packages(),
        pins=_two_terminal_pins(),
    )


def generic_led_green() -> ComponentSpec:
    return ComponentSpec(
        part_id="GENERIC_LED_GREEN",
        mpn=None,
        is_generic=True,
        category=ComponentCategory.LED,
        description="Generic green indicator LED.",
        packages=[
            PackageOption(name="0603", pin_count=2, hand_solderable=True),
            PackageOption(name="0805", pin_count=2, hand_solderable=True),
        ],
        pins=[
            PinSpec(
                number="1",
                name="A",
                roles=[PinRole.ANODE],
                electrical_type=PinElectricalType.PASSIVE,
            ),
            PinSpec(
                number="2",
                name="K",
                roles=[PinRole.CATHODE],
                electrical_type=PinElectricalType.PASSIVE,
            ),
        ],
        led=LedSpec(
            forward_voltage=ValueRange(minimum=V(1.8), typical=V(2.1), maximum=V(2.4)),
            max_forward_current=A(20e-3),
            test_current=A(5e-3),
            colour="green",
            evidence=[
                assumed_evidence(
                    "Generic green LED forward voltage",
                    detail=(
                        "Class-typical figures for a green indicator LED, not a specific part. "
                        "Marked ASSUMED. Selecting a real MPN replaces these with catalog or "
                        "datasheet evidence, and the LED current calculation inherits the "
                        "stronger status automatically."
                    ),
                    quantity=V(2.1),
                )
            ],
        ),
    )


def usb_c_receptacle() -> ComponentSpec:
    """A 16-pin USB Type-C sink receptacle.

    Generic on purpose: pin designations (A1, A4, A5, ...) come from the USB
    Type-C specification rather than any vendor, so nothing is invented by
    declining to name an MPN here.
    """
    pins: list[PinSpec] = []
    for number in ("A1", "A12", "B1", "B12"):
        pins.append(
            PinSpec(
                number=number,
                name="GND",
                roles=[PinRole.GROUND],
                electrical_type=PinElectricalType.PASSIVE,
            )
        )
    for number in ("A4", "A9", "B4", "B9"):
        pins.append(
            PinSpec(
                number=number,
                name="VBUS",
                roles=[PinRole.USB_VBUS, PinRole.POWER],
                # Passive, not power_out. A receptacle does not generate VBUS; the
                # net's declared ExternalSource is what says it is 5 V. Marking four
                # paralleled pins as power outputs would read as driver contention.
                electrical_type=PinElectricalType.PASSIVE,
            )
        )
    pins.append(
        PinSpec(
            number="A5",
            name="CC1",
            roles=[PinRole.USB_CC],
            electrical_type=PinElectricalType.BIDIRECTIONAL,
            must_not_float=True,
            notes="A sink must present Rd (5.1 kohm to GND) here or no source will supply VBUS.",
        )
    )
    pins.append(
        PinSpec(
            number="B5",
            name="CC2",
            roles=[PinRole.USB_CC],
            electrical_type=PinElectricalType.BIDIRECTIONAL,
            must_not_float=True,
            notes="A sink must present Rd (5.1 kohm to GND) here or no source will supply VBUS.",
        )
    )
    for number, name in (("A8", "SBU1"), ("B8", "SBU2")):
        pins.append(
            PinSpec(
                number=number,
                name=name,
                roles=[PinRole.OTHER],
                electrical_type=PinElectricalType.PASSIVE,
                notes="Sideband use. Unused on a power-and-USB2.0 sink.",
            )
        )
    for number, name, role in (
        ("A6", "DP1", PinRole.USB_DP),
        ("A7", "DN1", PinRole.USB_DM),
        ("B6", "DP2", PinRole.USB_DP),
        ("B7", "DN2", PinRole.USB_DM),
    ):
        pins.append(
            PinSpec(
                number=number,
                name=name,
                roles=[role],
                electrical_type=PinElectricalType.BIDIRECTIONAL,
            )
        )

    return ComponentSpec(
        part_id="USB_C_RECEPTACLE_16P",
        mpn=None,
        is_generic=True,
        category=ComponentCategory.CONNECTOR,
        description="USB Type-C 16-pin receptacle, USB 2.0, power sink.",
        interfaces=[Interface.USB_POWER_SINK, Interface.USB_DEVICE],
        packages=[
            PackageOption(
                name="USB-C-16P-SMD",
                pin_count=16,
                hand_solderable=True,
                kicad_footprint="Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
            )
        ],
        pins=pins,
        design_rules=[
            DesignRule(
                rule_id="usbc.rd_required",
                description=(
                    "A USB-C sink must pull each of CC1 and CC2 to ground through its own "
                    "5.1 kohm resistor. Sharing one resistor between them, or omitting them, "
                    "leaves the port dead on a Type-C to Type-C cable."
                ),
                category="other",
                evidence=[
                    catalog_evidence(
                        "USB Type-C sink CC termination",
                        document=USB_C_DOC,
                        text_value="Rd = 5.1 kohm +/- 20% on each CC pin for a sink",
                    )
                ],
            )
        ],
    )


def pin_header_1x6() -> ComponentSpec:
    return ComponentSpec(
        part_id="HEADER_1X6_254",
        mpn=None,
        is_generic=True,
        category=ComponentCategory.HEADER,
        description="Generic 1x6 2.54 mm pin header, used here as a programming/debug header.",
        packages=[
            PackageOption(
                name="1x6-2.54mm-THT",
                pin_count=6,
                hand_solderable=True,
                kicad_footprint="Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
            )
        ],
        pins=[
            PinSpec(
                number=str(i),
                name=f"P{i}",
                roles=[PinRole.TERMINAL],
                electrical_type=PinElectricalType.PASSIVE,
            )
            for i in range(1, 7)
        ],
    )


BUILDERS = (
    esp32_wroom_32e,
    ap2112k_33,
    mcp1700_3302e,
    bme280,
    generic_resistor,
    generic_capacitor,
    generic_led_green,
    usb_c_receptacle,
    pin_header_1x6,
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for build in BUILDERS:
        spec = build()
        path = OUT_DIR / f"{spec.part_id}.json"
        payload = spec.model_dump(mode="json", exclude_none=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(OUT_DIR.parents[4])}  ({len(spec.pins)} pins)")


if __name__ == "__main__":
    main()
