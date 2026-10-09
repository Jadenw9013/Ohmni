"""Isolated manufacturer-reported parts for the authored controller demo.

No web access on import and no shared default catalog mutation. Manual source
review is CATALOG_REPORTED, never a relocated or electrically verified claim.
"""
from datetime import UTC, datetime

from ohmni.adapters.fakes import InMemoryPartCatalog
from ohmni.catalog import default_catalog
from ohmni.domain.component import (
    ComponentCategory,
    ComponentSpec,
    DecouplingRule,
    Interface,
    LedSpec,
    PackageOption,
    PinElectricalType,
    PinRole,
    PinSpec,
    SupplyRail,
)
from ohmni.domain.evidence import DocumentRef, Evidence, EvidenceKind
from ohmni.domain.units import Quantity, ValueRange

MCU_ID = "STM32F103VBT6"
SHIFT_ID = "SN74HC595D"
LED_ID = "APT1608SGC"
HEADER_ID = "TSW-120-07-G-D"
SWD_ID = "TSW-106-07-G-S"
USB_ID = "TYPE-C-31-M-12"
BUTTON_ID = "B3F-1000"
RESISTORS = {1000: "ERJ3EKF1001V", 5100: "ERJ3EKF5101V", 10000: "ERJ3EKF1002V"}
CAPACITORS = {100e-9: "C1608X7R1H104K080AA", 1e-6: "C1608X5R1C105K080AA",
              10e-6: "GRM21BR71A106KE51L"}
MCU_PIN_NAMES = dict(enumerate(["PE2", "PE3", "PE4", "PE5", "PE6", "VBAT", "PC13", "PC14", "PC15", "VSS_5", "VDD_5", "OSC_IN", "OSC_OUT", "NRST", "PC0", "PC1", "PC2", "PC3", "VSSA", "VREF-", "VREF+", "VDDA", "PA0", "PA1", "PA2", "PA3", "VSS_4", "VDD_4", "PA4", "PA5", "PA6", "PA7", "PC4", "PC5", "PB0", "PB1", "PB2", "PE7", "PE8", "PE9", "PE10", "PE11", "PE12", "PE13", "PE14", "PE15", "PB10", "PB11", "VSS_1", "VDD_1", "PB12", "PB13", "PB14", "PB15", "PD8", "PD9", "PD10", "PD11", "PD12", "PD13", "PD14", "PD15", "PC6", "PC7", "PC8", "PC9", "PA8", "PA9", "PA10", "PA11", "PA12", "PA13", "NC", "VSS_2", "VDD_2", "PA14", "PA15", "PC10", "PC11", "PC12", "PD0", "PD1", "PD2", "PD3", "PD4", "PD5", "PD6", "PD7", "PB3", "PB4", "PB5", "PB6", "PB7", "BOOT0", "PB8", "PB9", "PE0", "PE1", "VSS_3", "VDD_3"], 1))
MCU_VDD = (11, 28, 50, 75, 100)
MCU_GND = (10, 19, 20, 27, 49, 74, 99)
SHIFT_PIN_NAMES = {1: "QB", 2: "QC", 3: "QD", 4: "QE", 5: "QF", 6: "QG",
                   7: "QH", 8: "GND", 9: "QH_PRIME", 10: "SRCLR", 11: "SRCLK",
                   12: "RCLK", 13: "OE", 14: "SER", 15: "QA", 16: "VCC"}
SOURCES = {
    "mcu": ("STMicroelectronics", "STM32F103x8/xB DS5319 Rev 20", "https://www.st.com/resource/en/datasheet/stm32f103vb.pdf"),
    "hardware": ("STMicroelectronics", "AN2586 Rev 8 hardware development", "https://www.st.com/resource/en/application_note/an2586-getting-started-with-stm32f10xxx-hardware-development-stmicroelectronics.pdf"),
    "shift": ("Texas Instruments", "SN74HC595 SCLS041J", "https://www.ti.com/lit/ds/symlink/sn74hc595.pdf"),
    "led": ("Kingbright", "APT1608SGC DSAD0932 Rev 22B", "https://www.kingbrightusa.com/images/catalog/spec/apt1608sgc.pdf"),
    "usb": ("HRO", "TYPE-C-31-M-12 product and drawing", "https://en.krhro.com/Product-Details/726.html"),
    "button": ("Omron", "B3F tactile switches", "https://components.omron.com/us-en/system/files/2023-01/datasheet_pdf/A070-E1.pdf"),
    "header": ("Samtec", HEADER_ID, "https://www.samtec.com/products/tsw-120-07-g-d"),
    "swd": ("Samtec", SWD_ID, "https://www.samtec.com/products/tsw-106-07-g-s"),
    "resistor": ("Panasonic", "ERJ3EKF precision chip resistor family", "https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models?model_number=ERJ3EKF&order=series&page=0&sort=asc"),
    "rd": ("Panasonic", "ERJ3EKF5101V", "https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ3EKF5101V"),
    "cap100n": ("TDK", CAPACITORS[100e-9], "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1H104K080AA"),
    "cap1u": ("TDK", CAPACITORS[1e-6], "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X5R1C105K080AA"),
    "cap10u": ("Texas Instruments", "TLV62569 SLVSDG1C reference-design BOM, Table 3", "https://www.ti.com/lit/ds/symlink/tlv62569.pdf"),
}


def reported(source, page, label, text):
    maker, title, url = SOURCES[source]
    return Evidence(kind=EvidenceKind.CATALOG, label=label, page=page,
                    document=DocumentRef(document_id=f"landing-controller-{source}",
                                         title=title, manufacturer=maker, url=url),
                    source_id=f"landing-controller-{source}", text_value=text,
                    recorded_at=datetime(2026, 10, 9, tzinfo=UTC),
                    detail="Manufacturer source manually reviewed; deterministic source relocation not verified.")


def assumption(label, detail):
    return Evidence(kind=EvidenceKind.ASSUMPTION, label=label, detail=detail,
                    source_id="landing-controller-design", recorded_at=datetime(2026, 10, 9, tzinfo=UTC))


def voltage_range(minimum=None, maximum=None, typical=None):
    return ValueRange(minimum=Quantity.volts(minimum) if minimum is not None else None,
                      maximum=Quantity.volts(maximum) if maximum is not None else None,
                      typical=Quantity.volts(typical) if typical is not None else None)


def _pin(number, name, role, electrical, evidence, rail=None, **kwargs):
    return PinSpec(number=str(number), name=name, roles=[role], electrical_type=electrical,
                   supply_rail=rail, evidence=[evidence], **kwargs)


def _mcu():
    evidence = reported("mcu", 22, "LQFP100 top-view pin identities", "Figure 4; Table 5 pages 28-33. Pin 73 is NC.")
    pins = []
    for number, name in MCU_PIN_NAMES.items():
        role, kind, rail = PinRole.GPIO, PinElectricalType.BIDIRECTIONAL, "VDD"
        if number in MCU_GND:
            role, kind, rail = PinRole.GROUND, PinElectricalType.POWER_IN, None
        elif number in (*MCU_VDD, 6, 21, 22):
            role, kind = PinRole.POWER, PinElectricalType.POWER_IN
        elif number == 73:
            role, kind, rail = PinRole.NOT_CONNECTED, PinElectricalType.NO_CONNECT, None
        elif number in (12, 13):
            role, kind = PinRole.CRYSTAL, PinElectricalType.INPUT if number == 12 else PinElectricalType.OUTPUT
        elif number == 14:
            role, kind = PinRole.RESET, PinElectricalType.BIDIRECTIONAL
        elif number in (37, 94):
            role, kind = PinRole.BOOT_STRAP, PinElectricalType.INPUT
        elif number in (29, 30, 31, 32):
            role = {29: PinRole.SPI_CS, 30: PinRole.SPI_SCK, 31: PinRole.SPI_MISO, 32: PinRole.SPI_MOSI}[number]
        pins.append(_pin(number, name, role, kind, evidence, rail))
    power = reported("hardware", 8, "Supply and decoupling", "All five VDD pins each have 100 nF; shared 10 uF bulk. VBAT uses VDD and 100 nF; VDDA uses 100 nF and 1 uF; VREF+ tied to VDDA.")
    return ComponentSpec(part_id=MCU_ID, mpn=MCU_ID, manufacturer="STMicroelectronics",
        category=ComponentCategory.MCU, description="128 KiB Arm Cortex-M3 controller; internal 8 MHz HSI demo.",
        packages=[PackageOption(name="LQFP-100", pin_count=100, hand_solderable=False,
                               kicad_footprint="Package_QFP:LQFP-100_14x14mm_P0.5mm")],
        pins=pins, supply_rails=[SupplyRail(name="VDD", operating=voltage_range(2.4, 3.6, 3.3),
            evidence=[reported("mcu", 38, "ADC-enabled operating supply", "VDD/VDDA 2.4 to 3.6 V with ADC enabled.")],
            notes="VBAT/VDDA/VREF+ tied to VDD in this authored board. Current depends on clock and peripherals; not inferred.")],
        interfaces=[Interface.SPI, Interface.GPIO, Interface.SWD],
        decoupling_rules=[DecouplingRule(rail="VDD", per_pin_capacitance=Quantity.farads(100e-9),
                                        bulk_capacitance=Quantity.farads(10e-6),
                                        evidence=[power])], evidence=[evidence, power])


def _shift():
    ev = reported("shift", 3, "SOIC16 pin map", "QA=15; QB..QH=1..7; QH'=9; SRCLR=10; SRCLK=11; RCLK=12; OE=13; SER=14; GND=8; VCC=16.")
    pins = []
    for number, name in SHIFT_PIN_NAMES.items():
        role, kind, rail = PinRole.OTHER, PinElectricalType.INPUT, "VCC"
        if number == 16:
            role, kind = PinRole.POWER, PinElectricalType.POWER_IN
        elif number == 8:
            role, kind, rail = PinRole.GROUND, PinElectricalType.POWER_IN, None
        elif number in (1, 2, 3, 4, 5, 6, 7, 15):
            kind = PinElectricalType.TRI_STATE
        elif number == 9:
            kind = PinElectricalType.OUTPUT
        pins.append(_pin(number, name, role, kind, ev, rail,
                         must_not_float=number in (10, 11, 12, 13, 14)))
    return ComponentSpec(part_id=SHIFT_ID, mpn=SHIFT_ID, manufacturer="Texas Instruments",
        category=ComponentCategory.OTHER, description="8-bit serial-in parallel-out indicator register.",
        packages=[PackageOption(name="SOIC-16", pin_count=16,
                               kicad_footprint="Package_SO:SOIC-16_3.9x9.9mm_P1.27mm")],
        pins=pins, supply_rails=[SupplyRail(name="VCC", operating=voltage_range(2, 6),
            evidence=[reported("shift", 4, "Supply range", "2 to 6 V recommended operation.")])],
        decoupling_rules=[DecouplingRule(rail="VCC", per_pin_capacitance=Quantity.farads(100e-9),
            evidence=[reported("shift", 15, "Local bypass", "100 nF adjacent to the supply pin.")])], evidence=[ev])


def _header(part_id, count, package, footprint, source):
    ev = reported(source, None, "Header configuration", f"{count} contacts; 2.54 mm pitch; 0.635 mm square pins; 5.84 mm exposed post.")
    return ComponentSpec(part_id=part_id, mpn=part_id, manufacturer="Samtec",
        category=ComponentCategory.HEADER, description="Through-hole pin header; board-specific signal assignments.",
        packages=[PackageOption(name=package, pin_count=count, kicad_footprint=footprint)],
        pins=[_pin(i, str(i), PinRole.TERMINAL, PinElectricalType.PASSIVE, ev) for i in range(1, count+1)], evidence=[ev])


def controller_catalog():
    base = default_catalog()
    parts = [p.model_copy(deep=True) for p in base.all_parts()]
    additions = [_mcu(), _shift(),
        _header(HEADER_ID, 40, "2x20-2.54mm-THT", "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical", "header"),
        _header(SWD_ID, 6, "1x6-2.54mm-THT", "Ohmni_Landing:PinHeader_1x06_P2.54mm_Vertical_Centered", "swd")]
    for value, mpn in RESISTORS.items():
        ev = reported("rd" if value == 5100 else "resistor", None, "Selected resistor", f"{mpn}: {value} ohm, 1%, 0.1 W, 0603.")
        part = base.require("GENERIC_RESISTOR").model_copy(deep=True)
        part.part_id = part.mpn = mpn
        part.manufacturer, part.is_generic = "Panasonic", False
        part.description = f"{value} ohm 1% 0603 resistor; value and power from manufacturer page."
        part.packages = [p for p in part.packages if p.name == "0603"]
        part.evidence = [ev]
        for pin in part.pins:
            pin.evidence = [ev]
        additions.append(part)
    for value, mpn in CAPACITORS.items():
        source = {100e-9: "cap100n", 1e-6: "cap1u", 10e-6: "cap10u"}[value]
        package = "0805" if value == 10e-6 else "0603"
        ev = reported(source, 8 if value == 10e-6 else None, "Selected MLCC", f"{mpn}: nominal {value} F; {package}. Effective capacitance under DC bias is not validated.")
        if value == 10e-6:
            ev = ev.model_copy(update={"detail": "Exact Murata MPN and nominal 10 uF/10 V/X7R/0805 attributes corroborated by TI reference-design BOM Table 3; not Murata datasheet verification. Prior Murata link returned 404; height, derating and exact fit remain unverified."})
        part = base.require("GENERIC_CAPACITOR").model_copy(deep=True)
        part.part_id = part.mpn = mpn
        part.manufacturer, part.is_generic = ("Murata" if value == 10e-6 else "TDK"), False
        part.description = f"{value:g} F MLCC; exact orderable realization with bias/thermal limits still to evaluate."
        part.packages = [p for p in part.packages if p.name == package]
        part.evidence = [ev]
        for pin in part.pins:
            pin.evidence = [ev]
        additions.append(part)
    led_ev = reported("led", 1, "0603 green LED and polarity", "1.6 x 0.8 x 0.75 mm, clear lens; cathode mark. Board terminal convention 1=K, 2=A.")
    additions.append(ComponentSpec(part_id=LED_ID, mpn=LED_ID, manufacturer="Kingbright",
        category=ComponentCategory.LED, description="Green clear-lens 0603 indicator.",
        packages=[PackageOption(name="0603", pin_count=2, hand_solderable=False,
                               kicad_footprint="LED_SMD:LED_0603_1608Metric")],
        pins=[_pin(1, "K", PinRole.CATHODE, PinElectricalType.PASSIVE, led_ev),
              _pin(2, "A", PinRole.ANODE, PinElectricalType.PASSIVE, led_ev)],
        led=LedSpec(forward_voltage=voltage_range(None, 2.5, 2.2),
            max_forward_current=Quantity.amps(.025), test_current=Quantity.amps(.02),
            colour="green", evidence=[reported("led", 2, "LED ratings at 25 C", "VF typical 2.2 V, maximum 2.5 V at 20 mA; absolute maximum DC 25 mA. No minimum VF is specified.")]),
        evidence=[led_ev]))
    for generic, mpn, maker, source in (("USB_C_RECEPTACLE_16P", USB_ID, "HRO", "usb"),
                                       ("GENERIC_MOMENTARY_BUTTON", BUTTON_ID, "Omron", "button")):
        part = base.require(generic).model_copy(deep=True)
        part.part_id = part.mpn = mpn
        part.manufacturer, part.is_generic = maker, False
        text = ("16-contact right-angle USB-C; 8.94 x 7.35 x 3.16 mm. Exact purchased variant and mating fit require checking."
                if source == "usb" else "B3F-1000 6 x 6 mm SPST-NO; four legs form two permanently joined electrical pairs. Catalog terminals collapse those pairs to the KiCad SW_PUSH_6mm pad identities.")
        part.description = text
        part.evidence = [reported(source, None, "Selected connector/switch", text)]
        for pin in part.pins:
            pin.evidence = part.evidence
        if source == "button":
            part.packages = [part.packages[0].model_copy(update={"notes": text})]
            part.design_rules = []
        additions.append(part)
    return InMemoryPartCatalog([*parts, *additions])
