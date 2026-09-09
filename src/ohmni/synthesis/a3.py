"""Bounded USB SPI memory-board synthesis with distinct chip selects."""

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
    CAPACITOR_PART_ID,
    LED_PART_ID,
    REGULATOR_PART_ID,
    RESISTOR_PART_ID,
    _CatalogCapabilityError,
    _decoupling,
    _led_resistance,
    _one_pin_with_role,
    _package,
    _pin_named,
    _pins,
    _refuse,
)
from .base import build_usb_esp32_base, common_preflight
from .models import ArchetypeId, RefusalCode, SynthesisBrief, SynthesisResult
from .peripherals import SUPPORTED_I2C_PARTS, add_i2c_bus, add_i2c_sensor, address_option

SPI_MEMORY_PART_ID = "25LC256-I/SN"
SPI_PIN_POLICY = (("SPI_SCK", "IO18", PinRole.SPI_SCK),
                  ("SPI_MOSI", "IO23", PinRole.SPI_MOSI),
                  ("SPI_MISO", "IO19", PinRole.SPI_MISO))


def synthesize_a3(brief: SynthesisBrief, catalog=None) -> SynthesisResult:
    """Derive one or two EEPROMs with optional I2C sensor and status LED."""
    catalog = catalog or default_catalog()
    if refusal := common_preflight(brief, catalog):
        return refusal
    if brief.archetype is not ArchetypeId.A3_USB_SPI_PERIPHERAL:
        return _refuse(brief, RefusalCode.ARCHETYPE_NOT_IMPLEMENTED, "Choose the A3 SPI family.", "archetype")
    if not 1 <= len(brief.spi_devices) <= 2:
        return _refuse(brief, RefusalCode.SPI_COUNT_UNSUPPORTED, "A3 supports one or two SPI devices.", "spi_devices")
    if brief.button_count or brief.status_led_count not in (0, 1):
        return _refuse(brief, RefusalCode.PERIPHERAL_SLOTS_UNSUPPORTED,
                       "A3 supports no buttons and zero or one status LED.", "button_count", "status_led_count")
    if len(brief.sensors) > 1:
        return _refuse(brief, RefusalCode.SENSOR_COUNT_UNSUPPORTED, "A3 supports at most one I2C sensor.", "sensors")
    for index, slot in enumerate(brief.spi_devices):
        if slot.part_id != SPI_MEMORY_PART_ID or catalog.get(slot.part_id) is None:
            return _refuse(brief, RefusalCode.SPI_UNAVAILABLE,
                           f"A3 currently supports catalog-backed {SPI_MEMORY_PART_ID} EEPROMs.",
                           f"spi_devices.{index}.part_id")
    for slot in brief.sensors:
        if slot.part_id not in SUPPORTED_I2C_PARTS or catalog.get(slot.part_id) is None:
            return _refuse(brief, RefusalCode.SENSOR_UNAVAILABLE, "Choose a supported I2C sensor.", "sensors")
        try:
            address_option(catalog.require(slot.part_id), slot.address)
        except _CatalogCapabilityError as exc:
            return _refuse(brief, RefusalCode.SENSOR_ADDRESS_UNAVAILABLE, str(exc), "sensors.0.address")
    if brief.status_led_count and catalog.get(LED_PART_ID) is None:
        return _refuse(brief, RefusalCode.PART_UNAVAILABLE, "The status LED is absent from the catalog.", "status_led_count")
    try:
        base = build_usb_esp32_base(brief, catalog)
        components, nets = base.components, base.nets
        controller = next(part for part in components if part.ref == "U1")
        controller.selected_interfaces = [Interface.SPI]
        if brief.sensors:
            controller.selected_interfaces.append(Interface.I2C)
        if brief.status_led_count:
            controller.selected_interfaces.append(Interface.GPIO)
        prefer = brief.hand_solderable_preferred
        mcu = catalog.require(brief.mcu_part_id)
        logic = next(net for net in nets if net.name == "3V3")
        ground = next(net for net in nets if net.name == "GND")
        bus = {}
        for name, mcu_pin, _ in SPI_PIN_POLICY:
            bus[name] = Net(name=name, connections=_pins(("U1", _pin_named(mcu, mcu_pin))))
            nets.append(bus[name])
        for index, slot in enumerate(brief.spi_devices):
            spec = catalog.require(slot.part_id)
            if Interface.SPI not in spec.interfaces:
                raise _CatalogCapabilityError(f"{slot.part_id} lacks its SPI interface")
            ref, cap, pull = f"U{3+index}", f"C{6+index}", f"R{4+index}"
            components.extend([
                CircuitComponent(ref=ref, part_id=slot.part_id, package=_package(catalog, slot.part_id, prefer),
                                 selected_interfaces=[Interface.SPI]),
                CircuitComponent(ref=cap, part_id=CAPACITOR_PART_ID, package=_package(catalog, CAPACITOR_PART_ID, prefer),
                                 value=_decoupling(spec, "VCC"), notes=f"Catalog-derived {ref} supply decoupling."),
                CircuitComponent(ref=pull, part_id=RESISTOR_PART_ID, package=_package(catalog, RESISTOR_PART_ID, prefer),
                                 value=Quantity.ohms(10_000), notes="Authored 10k pull-up keeps EEPROM deselected while MCU resets."),
            ])
            logic.connections.extend(_pins((ref, _one_pin_with_role(spec, PinRole.POWER)),
                                           (ref, "3"), (ref, "7"), (cap, "1"), (pull, "2")))
            ground.connections.extend(_pins((ref, _one_pin_with_role(spec, PinRole.GROUND)), (cap, "2")))
            for name, _, role in SPI_PIN_POLICY:
                bus[name].connections.extend(_pins((ref, _one_pin_with_role(spec, role))))
            nets.append(Net(name=f"SPI_CS{index+1}", connections=_pins(
                ("U1", _pin_named(mcu, ("IO25", "IO26")[index])),
                (ref, _one_pin_with_role(spec, PinRole.SPI_CS)), (pull, "1"),
            )))
        if brief.sensors:
            add_i2c_bus(components, nets, catalog, prefer)
            add_i2c_sensor(components, nets, catalog, brief.sensors[0], prefer,
                           ref="U5", cap_refs=("C8", "C9"))
        if brief.status_led_count:
            led = catalog.require(LED_PART_ID)
            components.extend([
                CircuitComponent(ref="D1", part_id=LED_PART_ID, package=_package(catalog, LED_PART_ID, prefer)),
                CircuitComponent(ref="R8", part_id=RESISTOR_PART_ID, package=_package(catalog, RESISTOR_PART_ID, prefer),
                                 value=_led_resistance(catalog.require(REGULATOR_PART_ID), led)),
            ])
            ground.connections.extend(_pins(("D1", _one_pin_with_role(led, PinRole.CATHODE))))
            nets.extend([
                Net(name="LED_DRIVE", connections=_pins(("U1", _pin_named(mcu, "IO27")), ("R8", "1"))),
                Net(name="LED_A", connections=_pins(("R8", "2"), ("D1", _one_pin_with_role(led, PinRole.ANODE)))),
            ])
        assumptions = [*base.design_assumptions,
            "Firmware must configure SPI clock GPIO18, MOSI GPIO23, MISO GPIO19 and chip selects GPIO25/GPIO26.",
            "Firmware must select at most one EEPROM at a time; static wiring does not verify runtime bus arbitration.",
            "EEPROM WP and HOLD are tied high; writes and write protection require deliberate firmware handling.",
            "No firmware or SPI timing simulation is supplied by circuit synthesis."]
        circuit = base.model_copy(update={"ir_id":f"a3-{brief.fingerprint[:16]}", "design_assumptions":assumptions})
        # Revalidate after composing mutable block lists, including unique pins/refs.
        circuit = type(circuit).model_validate(circuit.model_dump())
        interfaces = [Interface.USB_POWER_SINK, Interface.SPI]
        if brief.sensors:
            interfaces.append(Interface.I2C)
        if brief.status_led_count:
            interfaces.append(Interface.GPIO)
        if brief.include_programming_header:
            interfaces.append(Interface.UART)
        functions = [
            FunctionalRequirement(requirement_id="FR-1", description="Accept 5 V from USB-C without PD."),
            FunctionalRequirement(requirement_id="FR-2", description="Provide one regulated 3.3 V logic rail."),
            FunctionalRequirement(requirement_id="FR-3", description="Run the ESP32 processor."),
            FunctionalRequirement(requirement_id="FR-SPI", description=f"Connect {len(brief.spi_devices)} EEPROMs to SPI with distinct chip selects."),
        ]
        if brief.sensors:
            functions.append(FunctionalRequirement(requirement_id="FR-I2C", description=f"Read one {brief.sensors[0].part_id} sensor over I2C."))
        if brief.status_led_count:
            functions.append(FunctionalRequirement(requirement_id="FR-LED", description="Drive one status LED."))
        if brief.include_programming_header:
            functions.append(FunctionalRequirement(requirement_id="FR-UART", description="Expose a serial programming header."))
        requirements = RequirementsSpec(
            project_name=brief.project_name, description=brief.description,
            max_input_voltage=Quantity.volts(5.25), target_logic_voltage=Quantity.volts(3.3),
            budget_usd=brief.budget_usd, max_board_layers=brief.max_board_layers,
            hand_solderable=brief.hand_solderable_preferred, interfaces=interfaces,
            required_part_ids=sorted({brief.mcu_part_id, *[slot.part_id for slot in brief.spi_devices],
                                      *[slot.part_id for slot in brief.sensors]}),
            functional_requirements=functions,
            assumptions=assumptions,
        )
        return SynthesisResult(brief_fingerprint=brief.fingerprint, requirements=requirements, circuit=circuit)
    except (_CatalogCapabilityError, KeyError) as exc:
        return _refuse(brief, RefusalCode.CATALOG_CAPABILITY_MISSING, str(exc))
