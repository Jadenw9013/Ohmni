"""Isolated, source-reported catalog overlay for the landing circuit redesign.

No bundled catalog entry is modified. Manufacturer facts are deliberately
CATALOG_REPORTED: URLs and pages were reviewed, but no source-relocation engine
has established a machine-verified datasheet claim. Importing this module does
not access the network or load a catalog.
"""

from datetime import UTC, datetime

from ohmni.adapters.fakes import InMemoryPartCatalog
from ohmni.catalog import default_catalog
from ohmni.domain.component import (
    ComponentCategory,
    ComponentSpec,
    DecouplingRule,
    DesignRule,
    Interface,
    PackageOption,
    PinElectricalType,
    PinRole,
    PinSpec,
    SupplyRail,
)
from ohmni.domain.evidence import DocumentRef, Evidence, EvidenceKind
from ohmni.domain.units import Quantity, ValueRange

RECORDED_AT = datetime(2026, 10, 9, tzinfo=UTC)
BUCK_PART_ID = "TLV62569DBVR"
INDUCTOR_PART_ID = "XAL4020-222MEB"
TRANSLATOR_PART_ID = "PCA9306DCUT"
HEADER_PART_ID = "HEADER_1X4_254"
ADDED_PART_IDS = (BUCK_PART_ID, INDUCTOR_PART_ID, TRANSLATOR_PART_ID, HEADER_PART_ID)

SOURCES = {
    "buck": DocumentRef(
        document_id="landing-tlv62569", title="TLV62569 2-A Buck Converter",
        manufacturer="Texas Instruments", part_number=BUCK_PART_ID,
        url="https://www.ti.com/lit/ds/symlink/tlv62569.pdf",
    ),
    "buck_design": DocumentRef(
        document_id="landing-tidued0", title="TI reference design TIDUED0",
        manufacturer="Texas Instruments", part_number=BUCK_PART_ID,
        url="https://www.ti.com/lit/ug/tidued0/tidued0.pdf",
    ),
    "buck_evm": DocumentRef(
        document_id="landing-slvuay6", title="TLV62569EVM User Guide",
        manufacturer="Texas Instruments", part_number=BUCK_PART_ID,
        url="https://www.ti.com/lit/ug/slvuay6/slvuay6.pdf",
    ),
    "inductor": DocumentRef(
        document_id="landing-coilcraft-xal4000", title="XAL40xx Shielded Power Inductors",
        manufacturer="Coilcraft", part_number=INDUCTOR_PART_ID,
        url="https://www.coilcraft.com/getmedia/6adcb47d-8b55-416c-976e-1e22e0d2848c/xal4000.pdf",
    ),
    "translator": DocumentRef(
        document_id="landing-pca9306-scps113o", title="PCA9306 Dual Bidirectional I2C Translator",
        manufacturer="Texas Instruments", part_number=TRANSLATOR_PART_ID, revision="SCPS113O",
        url="https://www.ti.com/lit/ds/symlink/pca9306.pdf",
    ),
    "esp32": DocumentRef(
        document_id="landing-esp32-wroom-32e-v2.1", title="ESP32-WROOM-32E / 32UE Datasheet",
        manufacturer="Espressif Systems", part_number="ESP32-WROOM-32E", revision="v2.1",
        url="https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf",
    ),
}


def reported(source: str, page: int, label: str, text: str) -> Evidence:
    """Reviewed transcription, explicitly not a verified datasheet extraction."""
    document = SOURCES[source]
    return Evidence(
        kind=EvidenceKind.CATALOG, label=label, source_id=document.document_id,
        document=document, page=page, text_value=text, recorded_at=RECORDED_AT,
        detail="Manufacturer source reviewed; manually transcribed. Source relocation not verified.",
    )


def assumption(label: str, detail: str) -> Evidence:
    return Evidence(kind=EvidenceKind.ASSUMPTION, label=label, detail=detail,
                    source_id="landing-circuit-design-policy", recorded_at=RECORDED_AT)


def _pin(number, name, roles, electrical_type, evidence, rail=None, notes=None):
    return PinSpec(number=str(number), name=name, roles=roles, electrical_type=electrical_type,
                   supply_rail=rail, evidence=[evidence], notes=notes)


def _buck() -> ComponentSpec:
    pins = reported("buck", 3, "DBV pin assignments", "1 EN; 2 GND; 3 SW; 4 VIN; 5 FB.")
    operating = reported("buck", 4, "Input and feedback operating values",
                         "VIN 2.5 to 5.5 V; FB reference minimum/typical/maximum 0.588/0.600/0.612 V.")
    circuit = reported("buck", 8, "Example power stage",
                       "2.2 uH XAL4020; input 4.7 uF and output 10 uF ceramic capacitors.")
    return ComponentSpec(
        part_id=BUCK_PART_ID, mpn=BUCK_PART_ID, manufacturer="Texas Instruments",
        category=ComponentCategory.REGULATOR_SWITCHING,
        description="Adjustable synchronous buck; SW is a switching node, not a regulated DC output.",
        packages=[PackageOption(name="SOT-23-5", pin_count=5,
                                kicad_footprint="Package_TO_SOT_SMD:SOT-23-5")],
        pins=[
            _pin(1, "EN", [PinRole.ENABLE], PinElectricalType.INPUT, pins, "VIN"),
            _pin(2, "GND", [PinRole.GROUND], PinElectricalType.POWER_IN, pins),
            _pin(3, "SW", [PinRole.OTHER], PinElectricalType.OUTPUT, pins,
                 notes="Switching output; DC regulation requires external L, C and feedback."),
            _pin(4, "VIN", [PinRole.POWER], PinElectricalType.POWER_IN, pins, "VIN"),
            _pin(5, "FB", [PinRole.ANALOG_IN], PinElectricalType.INPUT, pins,
                 notes="Feedback sense; not a fixed 3.3 V output pin."),
        ],
        supply_rails=[SupplyRail(name="VIN", operating=ValueRange(
            minimum=Quantity.volts(2.5), maximum=Quantity.volts(5.5)), evidence=[operating])],
        # RegulatorSpec's output is interpreted as DC at POWER_OUT by the core
        # verifier. Omitting it is essential: the buck needs topology-aware checks.
        regulator=None,
        decoupling_rules=[DecouplingRule(rail="VIN", per_pin_capacitance=Quantity.farads(4.7e-6),
                                        evidence=[circuit])],
        design_rules=[
            DesignRule(rule_id="landing.buck.feedback", description=(
                "External feedback sets output: Vout = 0.6 V * (1 + Rupper/Rlower). "
                "The isolated design uses 453 kohm / 100 kohm, nominal 3.318 V."),
                evidence=[reported("buck_design", 18, "5 V to 3.3 V example", "453 kohm / 100 kohm divider.")]),
            DesignRule(rule_id="landing.buck.layout", category="layout", description=(
                "Keep input/output power loops short and wide; separate feedback from SW."),
                evidence=[reported("buck", 13, "Buck layout guidance", "Short power loops; feedback away from SW.")]),
        ], datasheet=SOURCES["buck"], evidence=[pins, operating, circuit],
    )


def _inductor() -> ComponentSpec:
    facts = reported("inductor", 1, "XAL4020-222 electrical values",
                     "2.2 uH +/-20%; DCR max 38.7 milliohm; Isat 5.6 A at 30% drop; Irms 4 A at 20 C rise.")
    outline = reported("inductor", 4, "XAL4020 body and land pattern",
                       "Body 4.0 +/-0.3 mm square, height maximum 2.1 mm. Lands 0.98 x 3.4 mm; centers 2.37 mm apart.")
    orderable = reported("buck_evm", 6, "Exact inductor orderable variant", "EVM BOM lists XAL4020-222MEB.")
    return ComponentSpec(
        part_id=INDUCTOR_PART_ID, mpn=INDUCTOR_PART_ID, manufacturer="Coilcraft",
        category=ComponentCategory.INDUCTOR, description="Shielded 2.2 uH power inductor; XAL4020 outline.",
        packages=[PackageOption(name="XAL4020", pin_count=2,
                                kicad_footprint="Inductor_SMD:L_Coilcraft_XAL4020-XXX")],
        pins=[_pin(n, str(n), [PinRole.TERMINAL], PinElectricalType.PASSIVE, facts) for n in (1, 2)],
        datasheet=SOURCES["inductor"], evidence=[facts, outline, orderable],
    )


def _translator() -> ComponentSpec:
    pinout = reported("translator", 4, "PCA9306 DCU pin assignments",
                      "1 GND; 2 VREF1; 3 SCL1; 4 SDA1; 5 SDA2; 6 SCL2; 7 VREF2; 8 EN.")
    bias = reported("translator", 18, "Translator bias network",
                    "Short EN and VREF2; pull up through 200 kohm to high-side rail; 100 pF filter to GND.")
    operating = reported("translator", 5, "Translation operating envelope",
                         "I/O and bias pins 0 to 5.5 V; translation requires high rail >= low rail + 0.6 V.")
    return ComponentSpec(
        part_id=TRANSLATOR_PART_ID, mpn=TRANSLATOR_PART_ID, manufacturer="Texas Instruments",
        category=ComponentCategory.OTHER, interfaces=[Interface.I2C],
        description="Passive bidirectional I2C pass-FET translator, without a DC output supply or USB interface.",
        packages=[PackageOption(name="VSSOP-8-DCU", pin_count=8, hand_solderable=False,
                                kicad_footprint="Package_SO:VSSOP-8_2.3x2mm_P0.5mm")],
        pins=[
            _pin(1, "GND", [PinRole.GROUND], PinElectricalType.POWER_IN, pinout),
            _pin(2, "VREF1", [PinRole.POWER], PinElectricalType.INPUT, pinout, "VREF1"),
            _pin(3, "SCL1", [PinRole.I2C_SCL], PinElectricalType.PASSIVE, pinout),
            _pin(4, "SDA1", [PinRole.I2C_SDA], PinElectricalType.PASSIVE, pinout),
            _pin(5, "SDA2", [PinRole.I2C_SDA], PinElectricalType.PASSIVE, pinout),
            _pin(6, "SCL2", [PinRole.I2C_SCL], PinElectricalType.PASSIVE, pinout),
            _pin(7, "VREF2", [PinRole.OTHER], PinElectricalType.INPUT, pinout,
                 notes="Bias node; never tie directly to the high-side rail."),
            _pin(8, "EN", [PinRole.ENABLE], PinElectricalType.INPUT, pinout,
                 notes="Short to VREF2 in the translation configuration."),
        ],
        supply_rails=[SupplyRail(name="VREF1", operating=ValueRange(
            minimum=Quantity.volts(1.2), maximum=Quantity.volts(4.9)), evidence=[operating],
            notes=("Conditional envelope: VREF1 <= high-side rail minus 0.6 V, high side <=5.5 V. "
                   "The upper-side pull-up supply is external, not a VREF2 DC supply."))],
        design_rules=[DesignRule(rule_id="landing.i2c.bias", description=bias.text_value, evidence=[bias]),
                      DesignRule(rule_id="landing.i2c.poweroff", description=(
                          "Bias current can enter VREF1. Independently powered endpoints, power sequencing, "
                          "hot-plug behavior and connector ESD remain unverified."),
                          evidence=[reported("translator", 14, "Reference bias backfeed consideration",
                                             "VREF2 bias current can raise an unloaded VREF1 rail.")])],
        datasheet=SOURCES["translator"], evidence=[pinout, bias, operating],
    )


def _header() -> ComponentSpec:
    generic = assumption("Generic extension header", "Four generic 2.54 mm contacts; no exact manufacturer or rating selected.")
    return ComponentSpec(
        part_id=HEADER_PART_ID, category=ComponentCategory.HEADER, is_generic=True,
        description="Generic 1x4 2.54 mm header; external I2C connector, not an external power input.",
        packages=[PackageOption(name="1x4-2.54mm-THT", pin_count=4,
                                kicad_footprint="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical")],
        pins=[_pin(n, f"P{n}", [PinRole.TERMINAL], PinElectricalType.PASSIVE, generic)
              for n in range(1, 5)], evidence=[generic],
    )


def redesign_catalog() -> InMemoryPartCatalog:
    """A fresh overlay with no mutable objects shared with the default catalog."""
    catalog = InMemoryPartCatalog([
        *(part.model_copy(deep=True) for part in default_catalog().all_parts()),
        _buck(), _inductor(), _translator(), _header(),
    ])
    # The seed catalog conflates a recommended supply capability with maximum
    # current consumption. Correct that meaning only inside this isolated copy.
    mcu = catalog.require("ESP32-WROOM-32E")
    mcu.rail("VDD").current_max = None
    mcu.rail("VDD").notes = (
        "3.3 V module domain. Maximum consumption remains unknown here; the 0.5 A "
        "manufacturer recommendation is minimum supply capability, not peak draw."
    )
    mcu.design_rules.append(DesignRule(
        rule_id="landing.esp32.supply_capability", category="other",
        description="External supply must provide at least 0.5 A; this is not maximum device current.",
        evidence=[reported("esp32", 28, "Minimum external supply capability", "External supply current capability >=0.5 A.")],
    ))
    return catalog
