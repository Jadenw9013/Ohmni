"""A2: a bounded USB-powered ESP32 controller with indicator LEDs and buttons.

This compiler describes static wiring. Firmware direction/debounce and physical
switch operation are not simulated or verified by its construction.
"""

from __future__ import annotations

from ..adapters import PartCatalog
from ..catalog import default_catalog
from ..domain import (
    CircuitComponent,
    CircuitIR,
    ComponentCategory,
    ComponentSpec,
    FunctionalRequirement,
    Interface,
    Net,
    PinElectricalType,
    PinRole,
    Quantity,
    RequirementsSpec,
)
from .a1 import (
    LED_PART_ID,
    REGULATOR_PART_ID,
    RESISTOR_PART_ID,
    USB_VBUS_MAX_V,
    _CatalogCapabilityError,
    _led_resistance,
    _one_pin_with_role,
    _package,
    _pin_named,
    _pins,
    _refuse,
)
from .base import build_usb_esp32_base, common_preflight
from .models import ArchetypeId, RefusalCode, SynthesisBrief, SynthesisResult

BUTTON_PART_ID = "GENERIC_MOMENTARY_BUTTON"
LED_GPIO_NAMES = ("IO25", "IO26", "IO27", "IO32")
BUTTON_GPIO_NAMES = ("IO33", "IO23")
BUTTON_PULLUP_OHM = 10_000


def _safe_gpio(spec: ComponentSpec, name: str, *, output: bool = False) -> str:
    number = _pin_named(spec, name)
    pin = next(item for item in spec.pins if item.number == number)
    if PinRole.GPIO not in pin.roles or PinRole.BOOT_STRAP in pin.roles:
        raise _CatalogCapabilityError(f"{spec.part_id} {name} is not a catalog-backed non-strapping GPIO")
    supported = {PinElectricalType.BIDIRECTIONAL,
                 PinElectricalType.OUTPUT if output else PinElectricalType.INPUT}
    if pin.electrical_type not in supported:
        raise _CatalogCapabilityError(f"{spec.part_id} {name} cannot support the requested GPIO direction")
    return number


def _requirements(brief: SynthesisBrief) -> RequirementsSpec:
    interfaces = [Interface.USB_POWER_SINK, Interface.GPIO]
    functions = [
        FunctionalRequirement(requirement_id="FR-1", description="Accept 5 V from USB-C without PD."),
        FunctionalRequirement(requirement_id="FR-2", description="Provide a regulated 3.3 V logic rail."),
        FunctionalRequirement(requirement_id="FR-3", description=f"Run the {brief.mcu_part_id} processor."),
        FunctionalRequirement(requirement_id="FR-4", description=f"Drive {brief.status_led_count} individual indicator LEDs."),
        FunctionalRequirement(requirement_id="FR-5", description=f"Read {brief.button_count} active-low momentary buttons."),
    ]
    if brief.include_programming_header:
        interfaces.append(Interface.UART)
        functions.append(FunctionalRequirement(requirement_id="FR-6", description="Expose a serial programming header."))
    return RequirementsSpec(
        project_name=brief.project_name, description=brief.description,
        max_input_voltage=Quantity.volts(USB_VBUS_MAX_V), target_logic_voltage=Quantity.volts(brief.logic_voltage_v),
        budget_usd=brief.budget_usd, max_board_layers=brief.max_board_layers,
        hand_solderable=brief.hand_solderable_preferred, interfaces=interfaces,
        functional_requirements=functions, required_part_ids=[brief.mcu_part_id, LED_PART_ID, BUTTON_PART_ID],
        safety_domains=list(brief.safety_domains), assumptions=[
            "USB-C is a power sink only; programming needs the separate serial connections.",
            "Buttons are normally open and connect their GPIO input to ground when pressed.",
            "Firmware must configure button pins as inputs and handle switch bounce; neither is simulated.",
            "GPIO source/sink and aggregate current ratings are absent from the seed catalog and are not verified.",
        ],
    )


def _build(brief: SynthesisBrief, catalog: PartCatalog) -> CircuitIR:
    base = build_usb_esp32_base(brief, catalog)
    components = list(base.components)
    nets = [net.model_copy(deep=True) for net in base.nets]
    ground = next(net for net in nets if net.name == "GND")
    logic = next(net for net in nets if net.name == "3V3")
    mcu = catalog.require(brief.mcu_part_id)
    regulator = catalog.require(REGULATOR_PART_ID)
    led = catalog.require(LED_PART_ID)
    button = catalog.require(BUTTON_PART_ID)
    if (button.category is not ComponentCategory.SWITCH
            or {pin.number for pin in button.pins} != {"1", "2"}
            or any(pin.electrical_type is not PinElectricalType.PASSIVE
                   or PinRole.TERMINAL not in pin.roles for pin in button.pins)):
        raise _CatalogCapabilityError("The momentary-button policy requires exactly terminals 1 and 2")
    if led.led is None or led.led.test_current is None or led.led.test_current.value <= 0:
        raise _CatalogCapabilityError("LED resistor calculation needs a positive catalog test current")
    if regulator.regulator is None:
        raise _CatalogCapabilityError("The controller requires catalog regulator output limits")
    output = regulator.regulator.output_voltage.maximum
    forward = led.led.forward_voltage.minimum
    if output is None or forward is None or output.value <= forward.value:
        raise _CatalogCapabilityError("The controller needs a known supply bound above the LED forward-voltage minimum")
    resistance = _led_resistance(regulator, led)
    packages = {part: _package(catalog, part, brief.hand_solderable_preferred)
                for part in (LED_PART_ID, BUTTON_PART_ID, RESISTOR_PART_ID)}
    for index in range(brief.status_led_count):
        ref, resistor = f"D{index + 1}", f"R{10 + index}"
        gpio = LED_GPIO_NAMES[index]
        current = (output.value - forward.value) / resistance.value
        components.extend([
            CircuitComponent(ref=ref, part_id=LED_PART_ID, package=packages[LED_PART_ID],
                             notes=f"Active-high indicator driven by {gpio}; firmware is required."),
            CircuitComponent(ref=resistor, part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
                             value=resistance, evidence=[*led.led.evidence, *regulator.regulator.evidence],
                             notes=f"R rounded up to E12 from catalog voltage and LED test-current bounds. "
                                   f"I(max) = ({output.value:g} V - {forward.value:g} V) / {resistance.value:g} ohm = {current:g} A. "
                                   "Generic LED limits are assumptions; GPIO current capacity is not established."),
        ])
        nets.extend([
            Net(name=f"LED{index + 1}_DRIVE", connections=_pins(("U1", _safe_gpio(mcu, gpio, output=True)), (resistor, "1"))),
            Net(name=f"LED{index + 1}_A", connections=_pins((resistor, "2"), (ref, _one_pin_with_role(led, PinRole.ANODE)))),
        ])
        ground.connections.extend(_pins((ref, _one_pin_with_role(led, PinRole.CATHODE))))
    for index in range(brief.button_count):
        ref, resistor = f"SW{index + 1}", f"R{20 + index}"
        gpio = BUTTON_GPIO_NAMES[index]
        components.extend([
            CircuitComponent(ref=ref, part_id=BUTTON_PART_ID, package=packages[BUTTON_PART_ID],
                             notes=f"Normally-open button: pressing grounds {gpio}. Firmware must keep this pin an input."),
            CircuitComponent(ref=resistor, part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
                             value=Quantity.ohms(BUTTON_PULLUP_OHM), evidence=list(regulator.regulator.evidence),
                             notes=f"Authored 10 kohm pull-up policy. Pressed current(max) = {output.value:g} V / "
                                   f"{BUTTON_PULLUP_OHM} ohm = {output.value / BUTTON_PULLUP_OHM:g} A. "
                                   "Switch timing and debounce are not modeled."),
        ])
        nets.append(Net(name=f"BUTTON{index + 1}", connections=_pins(
            ("U1", _safe_gpio(mcu, gpio)), (ref, "1"), (resistor, "1")),
            notes="External pull-up defines idle high; the normally-open switch grounds it when pressed."))
        logic.connections.extend(_pins((resistor, "2")))
        ground.connections.extend(_pins((ref, "2")))
    return CircuitIR(ir_id=f"a2-{brief.fingerprint[:16]}", name=brief.project_name,
                     components=components, nets=nets, constraints=base.constraints,
                     design_assumptions=[*base.design_assumptions, *_requirements(brief).assumptions],
                     notes="Deterministic A2 GPIO topology from typed slots and catalog-backed pin identities.")


def synthesize_a2(brief: SynthesisBrief, catalog: PartCatalog | None = None) -> SynthesisResult:
    """Compile one to four LED outputs and one to two normally-open button inputs."""
    resolved = default_catalog() if catalog is None else catalog
    if refusal := common_preflight(brief, resolved):
        return refusal
    if brief.archetype is not ArchetypeId.A2_USB_GPIO_CONTROLLER:
        return _refuse(brief, RefusalCode.ARCHETYPE_NOT_IMPLEMENTED,
                       "The A2 compiler accepts the USB GPIO controller archetype only.", "archetype")
    if brief.sensors or brief.spi_devices:
        return _refuse(brief, RefusalCode.PERIPHERAL_SLOTS_UNSUPPORTED,
                       "The GPIO controller supports LEDs and buttons without I2C or SPI peripherals.",
                       "sensors", "spi_devices")
    if not 1 <= brief.status_led_count <= len(LED_GPIO_NAMES):
        return _refuse(brief, RefusalCode.STATUS_LED_COUNT_UNSUPPORTED,
                       "The GPIO controller supports one to four status LEDs.", "status_led_count")
    if not 1 <= brief.button_count <= len(BUTTON_GPIO_NAMES):
        return _refuse(brief, RefusalCode.BUTTON_COUNT_UNSUPPORTED,
                       "The GPIO controller supports one or two momentary buttons.", "button_count")
    missing = [part for part in (LED_PART_ID, BUTTON_PART_ID) if resolved.get(part) is None]
    if missing:
        return _refuse(brief, RefusalCode.PART_UNAVAILABLE, "Required GPIO catalog parts are missing.",
                       context={"missing": ",".join(missing)})
    try:
        circuit = _build(brief, resolved)
    except _CatalogCapabilityError as exc:
        return _refuse(brief, RefusalCode.CATALOG_CAPABILITY_MISSING, str(exc), context={"reason": str(exc)})
    return SynthesisResult(brief_fingerprint=brief.fingerprint, circuit=circuit, requirements=_requirements(brief))


__all__ = ["synthesize_a2"]
