"""Extended A1 composition; the original single-BME280 branch stays stable."""

from ..catalog import default_catalog
from ..domain import (
    CircuitComponent,
    FunctionalRequirement,
    Interface,
    Net,
    PinRole,
    Quantity,
    RequirementsSpec,
)
from .a1 import (
    LED_PART_ID,
    REGULATOR_PART_ID,
    RESISTOR_PART_ID,
    _CatalogCapabilityError,
    _led_resistance,
    _one_pin_with_role,
    _package,
    _pin_named,
    _pins,
    _refuse,
)
from .base import build_usb_esp32_base, common_preflight
from .models import ArchetypeId, RefusalCode, SynthesisResult
from .peripherals import SUPPORTED_I2C_PARTS, add_i2c_bus, add_i2c_sensor, address_option
from .placement import PlacementIntentBuilder


def synthesize_extended_a1(brief, catalog=None):
    catalog = catalog or default_catalog()
    if refusal := common_preflight(brief, catalog):
        return refusal
    if brief.archetype is not ArchetypeId.A1_USB_I2C_SENSOR:
        return _refuse(brief, RefusalCode.ARCHETYPE_NOT_IMPLEMENTED, "Choose the A1 sensor family.", "archetype")
    if not 1 <= len(brief.sensors) <= 3:
        return _refuse(brief, RefusalCode.SENSOR_COUNT_UNSUPPORTED, "A1 supports one to three I2C sensors.", "sensors")
    if brief.spi_devices or brief.button_count:
        return _refuse(brief, RefusalCode.PERIPHERAL_SLOTS_UNSUPPORTED, "A1 does not include button or SPI slots.", "button_count", "spi_devices")
    if brief.status_led_count not in (0, 1):
        return _refuse(brief, RefusalCode.STATUS_LED_COUNT_UNSUPPORTED, "A1 supports zero or one status LED.", "status_led_count")
    if brief.status_led_count and catalog.get(LED_PART_ID) is None:
        return _refuse(brief, RefusalCode.PART_UNAVAILABLE, "The status LED is absent from the catalog.", "status_led_count")
    reserved = [slot.address for slot in brief.sensors if slot.address is not None]
    if len(reserved) != len(set(reserved)):
        return _refuse(brief, RefusalCode.SENSOR_ADDRESS_CONFLICT,
                       "Two sensors request the same address on the shared bus.", "sensors")
    used = list(reserved)
    resolved_slots = []
    for index, slot in enumerate(brief.sensors):
        spec = catalog.get(slot.part_id)
        if slot.part_id not in SUPPORTED_I2C_PARTS or spec is None:
            return _refuse(brief, RefusalCode.SENSOR_UNAVAILABLE, "Choose a supported catalog I2C sensor.", f"sensors.{index}.part_id")
        if slot.address is not None and slot.address not in {item.address for item in spec.i2c_addresses}:
            return _refuse(brief, RefusalCode.SENSOR_ADDRESS_UNAVAILABLE, f"Address 0x{slot.address:02X} is not offered by {slot.part_id}.", f"sensors.{index}.address")
        try:
            address = slot.address
            if address is None:
                address = address_option(spec, None, used).address
                used.append(address)
            else:
                address_option(spec, address)
            resolved_slots.append(slot.model_copy(update={"address": address}))
        except _CatalogCapabilityError as exc:
            code = RefusalCode.SENSOR_ADDRESS_UNAVAILABLE if slot.address is not None else RefusalCode.SENSOR_ADDRESS_CONFLICT
            return _refuse(brief, code, str(exc), f"sensors.{index}.address")
    try:
        placement = PlacementIntentBuilder(width_mm=brief.board_width_mm, height_mm=brief.board_height_mm)
        base = build_usb_esp32_base(brief, catalog, placement=placement)
        components, nets = base.components, base.nets
        controller = next(part for part in components if part.ref == "U1")
        controller.selected_interfaces = [Interface.I2C]
        if brief.status_led_count:
            controller.selected_interfaces.append(Interface.GPIO)
        prefer = brief.hand_solderable_preferred
        add_i2c_bus(components, nets, catalog, prefer, resistor_refs=("R4", "R5"), placement=placement)
        used = []
        for index, slot in enumerate(resolved_slots):
            used.append(add_i2c_sensor(components, nets, catalog, slot, prefer,
                ref=f"U{3+index}", cap_refs=(f"C{6+2*index}", f"C{7+2*index}"), used_addresses=used,
                placement=placement))
        if brief.status_led_count:
            led = catalog.require(LED_PART_ID)
            components.extend([
                CircuitComponent(ref="D1", part_id=LED_PART_ID, package=_package(catalog, LED_PART_ID, prefer)),
                CircuitComponent(ref="R6", part_id=RESISTOR_PART_ID, package=_package(catalog, RESISTOR_PART_ID, prefer),
                                 value=_led_resistance(catalog.require(REGULATOR_PART_ID), led)),
            ])
            placement.group("gpio", "D1", ("D1", "R6"), "Indicator LED and its own series resistor.")
            next(net for net in nets if net.name == "GND").connections.extend(_pins(("D1", _one_pin_with_role(led, PinRole.CATHODE))))
            nets.extend([
                Net(name="LED_DRIVE", connections=_pins(("U1", _pin_named(catalog.require(brief.mcu_part_id), "IO27")), ("R6", "1"))),
                Net(name="LED_A", connections=_pins(("R6", "2"), ("D1", _one_pin_with_role(led, PinRole.ANODE)))),
            ])
        assumptions = [*base.design_assumptions,
            "One shared 3.3 V I2C bus; address straps are selected deterministically without collisions.",
            "A program must configure I2C on GPIO21/GPIO22 and the optional LED on GPIO27.",
            "Bus speed, capacitance, firmware, and physical sensor behavior are not simulated."]
        circuit = base.model_copy(update={"ir_id": f"a1-{brief.fingerprint[:16]}", "design_assumptions": assumptions})
        circuit = type(circuit).model_validate(circuit.model_dump())
        interfaces = [Interface.USB_POWER_SINK, Interface.I2C]
        if brief.status_led_count:
            interfaces.append(Interface.GPIO)
        if brief.include_programming_header:
            interfaces.append(Interface.UART)
        functions = [
            FunctionalRequirement(requirement_id="FR-1", description="Accept 5 V from USB-C without PD."),
            FunctionalRequirement(requirement_id="FR-2", description="Provide a regulated 3.3 V logic rail."),
            FunctionalRequirement(requirement_id="FR-3", description="Run the ESP32 processor."),
            FunctionalRequirement(requirement_id="FR-I2C", description=f"Read {len(brief.sensors)} I2C sensors with distinct addresses."),
        ]
        if brief.status_led_count:
            functions.append(FunctionalRequirement(requirement_id="FR-LED", description="Drive one status LED."))
        if brief.include_programming_header:
            functions.append(FunctionalRequirement(requirement_id="FR-UART", description="Expose a serial programming header."))
        requirements = RequirementsSpec(
            project_name=brief.project_name, description=brief.description,
            max_input_voltage=Quantity.volts(5.25), target_logic_voltage=Quantity.volts(3.3),
            budget_usd=brief.budget_usd, max_board_layers=brief.max_board_layers,
            hand_solderable=brief.hand_solderable_preferred, interfaces=interfaces,
            required_part_ids=sorted({brief.mcu_part_id, *[slot.part_id for slot in brief.sensors]}),
            functional_requirements=functions, assumptions=assumptions,
        )
        return SynthesisResult(brief_fingerprint=brief.fingerprint, requirements=requirements, circuit=circuit,
                               placement_request=placement.finish(circuit))
    except _CatalogCapabilityError as exc:
        return _refuse(brief, RefusalCode.CATALOG_CAPABILITY_MISSING, str(exc))
