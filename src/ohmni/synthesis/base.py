"""Reusable, catalog-derived USB-C supply and ESP32 core for bounded boards.

The base has no sensor, LED or button dependency. It produces real components
and pin connectivity, including an optional programming header.
"""

from __future__ import annotations

import math

from ..adapters import PartCatalog
from ..domain import (
    CircuitComponent,
    CircuitIR,
    ConstraintKind,
    DesignConstraint,
    ExternalSource,
    ExternalSourceKind,
    Net,
    NetKind,
    PinRole,
    Quantity,
    ValueRange,
)
from .a1 import (
    CAPACITOR_PART_ID,
    HEADER_PART_ID,
    MCU_ENABLE_DELAY_CAPACITANCE_F,
    MCU_ENABLE_PULLUP_OHM,
    REGULATOR_OUTPUT_CAPACITANCE_F,
    REGULATOR_PART_ID,
    RESISTOR_PART_ID,
    SUPPORTED_MCU_PART_ID,
    USB_CC_RESISTANCE_OHM,
    USB_CURRENT_LIMIT_A,
    USB_PART_ID,
    USB_VBUS_MAX_V,
    USB_VBUS_MIN_V,
    _CatalogCapabilityError,
    _decoupling,
    _one_pin_with_role,
    _package,
    _pin_named,
    _pins,
    _pins_with_role,
    _refuse,
)
from .models import InputPower, RefusalCode, SynthesisBrief, SynthesisResult
from .placement import PlacementIntentBuilder, record_usb_core


def common_preflight(brief: SynthesisBrief, catalog: PartCatalog) -> SynthesisResult | None:
    """Check the common electrical envelope without assuming a peripheral family."""
    if brief.safety_domains or brief.input_power is InputPower.MAINS:
        return _refuse(brief, RefusalCode.SAFETY_DOMAIN_UNSUPPORTED,
                       "Safety-critical and mains-powered designs are outside this board family.",
                       "safety_domains" if brief.safety_domains else "input_power")
    if brief.input_power is not InputPower.USB_C_5V:
        return _refuse(brief, RefusalCode.INPUT_POWER_UNSUPPORTED,
                       "This board family supports a USB-C 5 V power sink only.", "input_power")
    if not USB_VBUS_MIN_V <= brief.input_voltage_v <= USB_VBUS_MAX_V:
        return _refuse(brief, RefusalCode.INPUT_VOLTAGE_UNSUPPORTED,
                       "USB input must stay within the 4.75-5.25 V VBUS envelope.", "input_voltage_v")
    if not math.isclose(brief.logic_voltage_v, 3.3, rel_tol=0, abs_tol=1e-9):
        return _refuse(brief, RefusalCode.LOGIC_VOLTAGE_UNSUPPORTED,
                       "This board family implements one 3.3 V logic domain.", "logic_voltage_v")
    if brief.max_board_layers != 2:
        return _refuse(brief, RefusalCode.LAYER_COUNT_UNSUPPORTED,
                       "This board family requires two copper layers.", "max_board_layers")
    if brief.mcu_part_id != SUPPORTED_MCU_PART_ID:
        return _refuse(brief, RefusalCode.MCU_UNSUPPORTED,
                       f"This board family supports {SUPPORTED_MCU_PART_ID} only.", "mcu_part_id")
    required = {USB_PART_ID, REGULATOR_PART_ID, RESISTOR_PART_ID,
                CAPACITOR_PART_ID, brief.mcu_part_id}
    if brief.include_programming_header:
        required.add(HEADER_PART_ID)
    missing = sorted(part for part in required if catalog.get(part) is None)
    if missing:
        return _refuse(brief, RefusalCode.PART_UNAVAILABLE,
                       "Required USB/processor catalog parts are missing.",
                       context={"missing": ",".join(missing)})
    return None


def build_usb_esp32_base(brief: SynthesisBrief, catalog: PartCatalog,
                       *, placement: PlacementIntentBuilder | None = None) -> CircuitIR:
    """Build core topology after ``common_preflight`` has accepted the brief.

    Missing pin/package/numeric catalog capabilities raise the existing typed
    compiler capability error for the caller to turn into a refusal.
    """
    usb = catalog.require(USB_PART_ID)
    regulator = catalog.require(REGULATOR_PART_ID)
    mcu = catalog.require(brief.mcu_part_id)
    part_ids = [USB_PART_ID, REGULATOR_PART_ID, RESISTOR_PART_ID,
                CAPACITOR_PART_ID, brief.mcu_part_id]
    if brief.include_programming_header:
        part_ids.append(HEADER_PART_ID)
    packages = {part: _package(catalog, part, brief.hand_solderable_preferred) for part in part_ids}

    def part(ref: str, part_id: str, value=None, notes=None) -> CircuitComponent:
        return CircuitComponent(ref=ref, part_id=part_id, package=packages[part_id],
                                value=value, notes=notes)

    components = [
        part("J1", USB_PART_ID),
        part("R1", RESISTOR_PART_ID, Quantity.ohms(USB_CC_RESISTANCE_OHM), "USB-C sink policy: CC1 Rd."),
        part("R2", RESISTOR_PART_ID, Quantity.ohms(USB_CC_RESISTANCE_OHM), "USB-C sink policy: CC2 Rd."),
        part("U2", REGULATOR_PART_ID),
        part("C1", CAPACITOR_PART_ID, _decoupling(regulator, "VIN"), "Catalog-derived regulator input decoupling."),
        part("C2", CAPACITOR_PART_ID, Quantity.farads(REGULATOR_OUTPUT_CAPACITANCE_F), "Base policy: regulator output capacitance."),
        part("U1", mcu.part_id),
        part("C3", CAPACITOR_PART_ID, _decoupling(mcu, "VDD"), "Catalog-derived MCU local decoupling."),
        part("C4", CAPACITOR_PART_ID, _decoupling(mcu, "VDD", bulk=True), "Catalog-derived MCU bulk capacitance."),
        part("R3", RESISTOR_PART_ID, Quantity.ohms(MCU_ENABLE_PULLUP_OHM), "Base policy: MCU enable pull-up."),
        part("C5", CAPACITOR_PART_ID, Quantity.farads(MCU_ENABLE_DELAY_CAPACITANCE_F), "Base policy: MCU enable delay."),
    ]
    if brief.include_programming_header:
        components.append(part("J2", HEADER_PART_ID))
    if placement is not None:
        record_usb_core(
            placement, usb_ref="J1", cc_refs=("R1", "R2"), regulator_ref="U2",
            regulator_spec=regulator, input_cap="C1", input_pin=_pin_named(regulator, "VIN"),
            output_cap="C2", output_pin=_pin_named(regulator, "VOUT"), mcu_ref="U1", mcu_spec=mcu,
            supply_pin=_pin_named(mcu, "3V3"), local_cap="C3", bulk_cap="C4", enable_cap="C5",
            enable_pin=_pin_named(mcu, "EN"), enable_pullup="R3",
            header_ref="J2" if brief.include_programming_header else None,
        )

    usb_cc = _pins_with_role(usb, PinRole.USB_CC)
    if len(usb_cc) != 2:
        raise _CatalogCapabilityError(f"{usb.part_id} requires exactly two USB CC pins")
    ground = [*(('J1', pin) for pin in _pins_with_role(usb, PinRole.GROUND)),
              ("R1", "2"), ("R2", "2"), ("U2", _one_pin_with_role(regulator, PinRole.GROUND)),
              ("C1", "2"), ("C2", "2"),
              *(("U1", pin) for pin in _pins_with_role(mcu, PinRole.GROUND)),
              ("C3", "2"), ("C4", "2"), ("C5", "2")]
    logic = [("U2", _pin_named(regulator, "VOUT")), ("C2", "1"),
             ("U1", _pin_named(mcu, "3V3")), ("C3", "1"), ("C4", "1"), ("R3", "2")]
    enable = [("U1", _pin_named(mcu, "EN")), ("R3", "1"), ("C5", "1")]
    if brief.include_programming_header:
        ground.append(("J2", "2"))
        logic.append(("J2", "1"))
        enable.append(("J2", "5"))
    nets = [
        Net(name="VBUS", kind=NetKind.POWER, external_source=ExternalSource(
            kind=ExternalSourceKind.USB_VBUS,
            voltage=ValueRange(minimum=Quantity.volts(USB_VBUS_MIN_V),
                               typical=Quantity.volts(brief.input_voltage_v),
                               maximum=Quantity.volts(USB_VBUS_MAX_V)),
            current_limit=Quantity.amps(USB_CURRENT_LIMIT_A),
            description="USB-C bus power without PD negotiation."),
            connections=_pins(*[("J1", pin) for pin in _pins_with_role(usb, PinRole.USB_VBUS)],
                              ("U2", _pin_named(regulator, "VIN")),
                              ("U2", _pin_named(regulator, "EN")), ("C1", "1"))),
        Net(name="GND", kind=NetKind.GROUND, connections=_pins(*ground)),
        Net(name="CC1", connections=_pins(("J1", usb_cc[0]), ("R1", "1"))),
        Net(name="CC2", connections=_pins(("J1", usb_cc[1]), ("R2", "1"))),
        Net(name="3V3", kind=NetKind.POWER, connections=_pins(*logic)),
        Net(name="EN", connections=_pins(*enable)),
    ]
    if brief.include_programming_header:
        nets.extend([
            Net(name="UART_TX", connections=_pins(("U1", _pin_named(mcu, "TXD0")), ("J2", "3"))),
            Net(name="UART_RX", connections=_pins(("U1", _pin_named(mcu, "RXD0")), ("J2", "4"))),
            Net(name="IO0", connections=_pins(("U1", _pin_named(mcu, "IO0")), ("J2", "6"))),
        ])
    constraints = [
        DesignConstraint(constraint_id="C-1", kind=ConstraintKind.VOLTAGE,
                         description="All logic runs from a single 3.3 V rail.",
                         source_requirement_id="FR-2", applies_to=["3V3"]),
        DesignConstraint(constraint_id="C-2", kind=ConstraintKind.ASSEMBLY,
                         description="Prefer packages that a hobbyist can hand solder.", hard=False),
    ]
    if brief.budget_usd is not None:
        constraints.append(DesignConstraint(constraint_id="C-3", kind=ConstraintKind.COST,
                           description=f"Target a component budget of ${brief.budget_usd:.2f}.", hard=False))
    return CircuitIR(ir_id=f"usb-core-{brief.fingerprint[:16]}", name=brief.project_name,
                     components=components, nets=nets, constraints=constraints,
                     design_assumptions=["USB-C is a 5 V power sink; USB data pins are unused."],
                     notes="Catalog-derived USB-C regulator and processor base.")


__all__ = ["build_usb_esp32_base", "common_preflight"]
