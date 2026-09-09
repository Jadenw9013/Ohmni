"""Deterministic synthesis for A1: a USB-C powered ESP32 I2C sensor node.

This module is intentionally a bounded compiler, not a general circuit-design
claim. It accepts typed slots, applies explicit A1 topology policies, resolves
parts and pins through the catalog, and returns either CircuitIR or a typed
refusal. It never reads a golden design or asks a model to invent connectivity.
"""

from __future__ import annotations

import math

from ..adapters import PartCatalog
from ..catalog import default_catalog
from ..domain import (
    CircuitComponent,
    CircuitIR,
    ComponentSpec,
    ConstraintKind,
    DesignConstraint,
    ExternalSource,
    ExternalSourceKind,
    FunctionalRequirement,
    Interface,
    Net,
    NetKind,
    PinRef,
    PinRole,
    Quantity,
    RequirementsSpec,
    ValueRange,
)
from .models import (
    ArchetypeId,
    InputPower,
    RefusalCode,
    SynthesisBrief,
    SynthesisRefusal,
    SynthesisResult,
)

# A1 board-template policies. These are visible here because the bundled
# catalog does not yet encode them as machine-readable numeric rules.
USB_VBUS_MIN_V = 4.75
USB_VBUS_MAX_V = 5.25
USB_CURRENT_LIMIT_A = 0.5
USB_CC_RESISTANCE_OHM = 5_100
REGULATOR_OUTPUT_CAPACITANCE_F = 1e-6
MCU_ENABLE_PULLUP_OHM = 10_000
MCU_ENABLE_DELAY_CAPACITANCE_F = 100e-9
I2C_PULLUP_OHM = 4_700

USB_PART_ID = "USB_C_RECEPTACLE_16P"
REGULATOR_PART_ID = "AP2112K-3.3TRG1"
RESISTOR_PART_ID = "GENERIC_RESISTOR"
CAPACITOR_PART_ID = "GENERIC_CAPACITOR"
LED_PART_ID = "GENERIC_LED_GREEN"
HEADER_PART_ID = "HEADER_1X6_254"
SUPPORTED_MCU_PART_ID = "ESP32-WROOM-32E"


class _CatalogCapabilityError(ValueError):
    pass


def _refuse(
    brief: SynthesisBrief,
    code: RefusalCode,
    message: str,
    *field_paths: str,
    context: dict[str, str] | None = None,
) -> SynthesisResult:
    return SynthesisResult(
        brief_fingerprint=brief.fingerprint,
        refusal=SynthesisRefusal(
            code=code,
            message=message,
            field_paths=tuple(field_paths),
            context=context or {},
        ),
    )


def _select_package(spec: ComponentSpec, prefer_hand_solderable: bool) -> str:
    compileable = [package for package in spec.packages if package.kicad_footprint]
    if not compileable:
        raise _CatalogCapabilityError(f"{spec.part_id} has no compileable package")
    return min(
        compileable,
        key=lambda package: (
            # Preserve the authored 0805 passive policy as other footprint
            # sizes become available; catalog expansion must not silently
            # change an existing saved brief's circuit.
            package.name != "0805",
            prefer_hand_solderable and not package.hand_solderable,
            package.name,
        ),
    ).name


def _pin_named(spec: ComponentSpec, name: str) -> str:
    matches = [pin.number for pin in spec.pins if pin.name == name]
    if len(matches) != 1:
        raise _CatalogCapabilityError(
            f"{spec.part_id} requires exactly one pin named {name!r}; found {len(matches)}"
        )
    return matches[0]


def _pins_with_role(spec: ComponentSpec, role: PinRole) -> list[str]:
    matches = [pin.number for pin in spec.pins_with_role(role)]
    if not matches:
        raise _CatalogCapabilityError(f"{spec.part_id} has no {role.value} pin")
    return matches


def _one_pin_with_role(spec: ComponentSpec, role: PinRole) -> str:
    matches = _pins_with_role(spec, role)
    if len(matches) != 1:
        raise _CatalogCapabilityError(
            f"{spec.part_id} requires exactly one {role.value} pin; found {len(matches)}"
        )
    return matches[0]


def _package(catalog: PartCatalog, part_id: str, prefer_hand: bool) -> str:
    spec = catalog.get(part_id)
    if spec is None:
        raise _CatalogCapabilityError(f"required A1 part {part_id!r} is absent from the catalog")
    return _select_package(spec, prefer_hand)


def _decoupling(spec: ComponentSpec, rail: str, *, bulk: bool = False) -> Quantity:
    for rule in spec.decoupling_rules:
        if rule.rail != rail:
            continue
        value = rule.bulk_capacitance if bulk else rule.per_pin_capacitance
        if value is not None:
            return value
    kind = "bulk" if bulk else "per-pin"
    raise _CatalogCapabilityError(
        f"{spec.part_id} has no {kind} decoupling value for rail {rail!r}"
    )


def _ceil_e12(value_ohm: float) -> float:
    """Round a positive resistance up to the next E12 preferred value."""

    if value_ohm <= 0:
        raise ValueError("resistance must be positive")
    e12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2, 10.0)
    decade = 10 ** math.floor(math.log10(value_ohm))
    normalized = value_ohm / decade
    for candidate in e12:
        if candidate + 1e-12 >= normalized:
            return candidate * decade
    return 10.0 * decade


def _led_resistance(regulator: ComponentSpec, led: ComponentSpec) -> Quantity:
    if regulator.regulator is None or led.led is None or led.led.test_current is None:
        raise _CatalogCapabilityError("LED resistor calculation needs regulator and LED limits")
    supply = regulator.regulator.output_voltage.maximum
    forward = led.led.forward_voltage.minimum
    if supply is None or forward is None:
        raise _CatalogCapabilityError("LED resistor calculation needs worst-case voltage bounds")
    resistance = (supply.value - forward.value) / led.led.test_current.value
    return Quantity.ohms(_ceil_e12(resistance))


def _pins(*pairs: tuple[str, str]) -> list[PinRef]:
    return [PinRef(component=component, pin=pin) for component, pin in pairs]


def _preflight(brief: SynthesisBrief, catalog: PartCatalog) -> SynthesisResult | None:
    if brief.safety_domains:
        domains = ", ".join(sorted(domain.value for domain in brief.safety_domains))
        return _refuse(
            brief,
            RefusalCode.SAFETY_DOMAIN_UNSUPPORTED,
            f"A1 cannot make verified claims for safety-critical domains: {domains}.",
            "safety_domains",
            context={"domains": domains},
        )
    if brief.input_power is InputPower.MAINS:
        return _refuse(
            brief,
            RefusalCode.SAFETY_DOMAIN_UNSUPPORTED,
            "Mains-powered design is outside Ohmni's verified safety envelope.",
            "input_power",
            context={"requested": brief.input_power.value},
        )
    if brief.archetype is not ArchetypeId.A1_USB_I2C_SENSOR:
        return _refuse(
            brief,
            RefusalCode.ARCHETYPE_NOT_IMPLEMENTED,
            f"{brief.archetype.value} is planned but not implemented in M10-T01.",
            "archetype",
            context={"requested": brief.archetype.value},
        )
    if brief.input_power is not InputPower.USB_C_5V:
        return _refuse(
            brief,
            RefusalCode.INPUT_POWER_UNSUPPORTED,
            "A1 currently supports a USB-C 5 V power sink only.",
            "input_power",
            context={"requested": brief.input_power.value},
        )
    if not USB_VBUS_MIN_V <= brief.input_voltage_v <= USB_VBUS_MAX_V:
        return _refuse(
            brief,
            RefusalCode.INPUT_VOLTAGE_UNSUPPORTED,
            "USB-C A1 input voltage must be within the USB VBUS 4.75-5.25 V envelope.",
            "input_voltage_v",
            context={"requested_v": str(brief.input_voltage_v)},
        )
    if not math.isclose(brief.logic_voltage_v, 3.3, rel_tol=0.0, abs_tol=1e-9):
        return _refuse(
            brief,
            RefusalCode.LOGIC_VOLTAGE_UNSUPPORTED,
            "A1 currently implements one 3.3 V logic domain.",
            "logic_voltage_v",
            context={"requested_v": str(brief.logic_voltage_v)},
        )
    if brief.max_board_layers != 2:
        return _refuse(
            brief,
            RefusalCode.LAYER_COUNT_UNSUPPORTED,
            "A1 currently emits a deterministic two-layer board contract.",
            "max_board_layers",
            context={"requested": str(brief.max_board_layers)},
        )
    if brief.mcu_part_id != SUPPORTED_MCU_PART_ID:
        return _refuse(
            brief,
            RefusalCode.MCU_UNSUPPORTED,
            f"A1 currently supports {SUPPORTED_MCU_PART_ID} only.",
            "mcu_part_id",
            context={"requested": brief.mcu_part_id},
        )
    if len(brief.sensors) != 1:
        return _refuse(
            brief,
            RefusalCode.SENSOR_COUNT_UNSUPPORTED,
            "M10-T01 supports exactly one I2C sensor; multi-sensor composition follows in T02.",
            "sensors",
            context={"requested": str(len(brief.sensors))},
        )
    if brief.button_count or brief.spi_devices:
        return _refuse(
            brief, RefusalCode.PERIPHERAL_SLOTS_UNSUPPORTED,
            "The A1 sensor family does not accept button or SPI slots.",
            "button_count", "spi_devices",
        )
    if brief.status_led_count not in (0, 1):
        return _refuse(
            brief,
            RefusalCode.STATUS_LED_COUNT_UNSUPPORTED,
            "A1 supports zero or one status LED.",
            "status_led_count",
            context={"requested": str(brief.status_led_count)},
        )

    sensor_slot = brief.sensors[0]
    if sensor_slot.part_id != "BME280":
        return _refuse(
            brief, RefusalCode.SENSOR_UNAVAILABLE,
            "This sensor-board archetype currently supports the BME280 only.",
            "sensors.0.part_id", context={"requested": sensor_slot.part_id},
        )
    sensor = catalog.get(sensor_slot.part_id)
    if sensor is None:
        return _refuse(
            brief,
            RefusalCode.SENSOR_UNAVAILABLE,
            f"Sensor {sensor_slot.part_id!r} is not in the trusted local catalog.",
            "sensors.0.part_id",
            context={"requested": sensor_slot.part_id},
        )
    if Interface.I2C not in sensor.interfaces:
        return _refuse(
            brief,
            RefusalCode.SENSOR_INTERFACE_UNSUPPORTED,
            f"Sensor {sensor_slot.part_id!r} has no catalog-backed I2C interface.",
            "sensors.0.part_id",
            context={"requested": sensor_slot.part_id},
        )
    supported_addresses = {option.address for option in sensor.i2c_addresses}
    if sensor_slot.address is not None and sensor_slot.address not in supported_addresses:
        return _refuse(
            brief,
            RefusalCode.SENSOR_ADDRESS_UNAVAILABLE,
            f"Sensor {sensor_slot.part_id!r} cannot use address 0x{sensor_slot.address:02X}.",
            "sensors.0.address",
            context={"requested": f"0x{sensor_slot.address:02X}"},
        )

    required_parts = [
        USB_PART_ID,
        REGULATOR_PART_ID,
        RESISTOR_PART_ID,
        CAPACITOR_PART_ID,
        brief.mcu_part_id,
        sensor_slot.part_id,
    ]
    if brief.status_led_count:
        required_parts.append(LED_PART_ID)
    if brief.include_programming_header:
        required_parts.append(HEADER_PART_ID)
    missing = sorted(part_id for part_id in set(required_parts) if catalog.get(part_id) is None)
    if missing:
        return _refuse(
            brief,
            RefusalCode.PART_UNAVAILABLE,
            "A1 cannot be synthesized because required catalog parts are missing.",
            context={"missing": ",".join(missing)},
        )
    return None


def _requirements(brief: SynthesisBrief) -> RequirementsSpec:
    interfaces = [Interface.I2C, Interface.USB_POWER_SINK]
    functions = [
        FunctionalRequirement(
            requirement_id="FR-1", description="Accept 5 V from a USB-C power source."
        ),
        FunctionalRequirement(
            requirement_id="FR-2", description="Provide a regulated 3.3 V logic rail."
        ),
        FunctionalRequirement(
            requirement_id="FR-3", description=f"Run the {brief.mcu_part_id} module."
        ),
        FunctionalRequirement(
            requirement_id="FR-4",
            description=f"Read one {brief.sensors[0].part_id} sensor over I2C.",
        ),
    ]
    if brief.status_led_count:
        interfaces.append(Interface.GPIO)
        functions.append(
            FunctionalRequirement(requirement_id="FR-5", description="Drive one status LED.")
        )
    if brief.include_programming_header:
        interfaces.append(Interface.UART)
        functions.append(
            FunctionalRequirement(
                requirement_id="FR-6", description="Expose a serial programming header."
            )
        )
    return RequirementsSpec(
        project_name=brief.project_name,
        description=brief.description,
        max_input_voltage=Quantity.volts(USB_VBUS_MAX_V),
        target_logic_voltage=Quantity.volts(brief.logic_voltage_v),
        budget_usd=brief.budget_usd,
        max_board_layers=brief.max_board_layers,
        hand_solderable=brief.hand_solderable_preferred,
        interfaces=interfaces,
        functional_requirements=functions,
        required_part_ids=[brief.mcu_part_id, brief.sensors[0].part_id],
        safety_domains=list(brief.safety_domains),
        assumptions=["USB-C is used as a 5 V sink without Power Delivery."],
    )


def _build(brief: SynthesisBrief, catalog: PartCatalog) -> CircuitIR:
    prefer_hand = brief.hand_solderable_preferred
    usb = catalog.require(USB_PART_ID)
    regulator = catalog.require(REGULATOR_PART_ID)
    mcu = catalog.require(brief.mcu_part_id)
    sensor = catalog.require(brief.sensors[0].part_id)

    packages = {
        part_id: _package(catalog, part_id, prefer_hand)
        for part_id in (
            USB_PART_ID,
            REGULATOR_PART_ID,
            RESISTOR_PART_ID,
            CAPACITOR_PART_ID,
            brief.mcu_part_id,
            brief.sensors[0].part_id,
        )
    }
    if brief.status_led_count:
        packages[LED_PART_ID] = _package(catalog, LED_PART_ID, prefer_hand)
    if brief.include_programming_header:
        packages[HEADER_PART_ID] = _package(catalog, HEADER_PART_ID, prefer_hand)

    address_options = {option.address: option for option in sensor.i2c_addresses}
    if brief.sensors[0].address is None:
        defaults = [option for option in sensor.i2c_addresses if option.is_default]
        option = defaults[0] if defaults else min(sensor.i2c_addresses, key=lambda x: x.address)
    else:
        option = address_options[brief.sensors[0].address]
    if option.strap_pin is None or option.strap_level is None:
        raise _CatalogCapabilityError(
            f"{sensor.part_id} address 0x{option.address:02X} has no typed strap topology"
        )

    reg_input_cap = _decoupling(regulator, "VIN")
    mcu_local_cap = _decoupling(mcu, "VDD")
    mcu_bulk_cap = _decoupling(mcu, "VDD", bulk=True)
    sensor_caps = {
        rule.rail: rule.per_pin_capacitance
        for rule in sensor.decoupling_rules
        if rule.per_pin_capacitance is not None
    }
    for rail in ("VDD", "VDDIO"):
        if rail not in sensor_caps:
            raise _CatalogCapabilityError(
                f"{sensor.part_id} has no per-pin decoupling value for rail {rail!r}"
            )

    components = [
        CircuitComponent(ref="J1", part_id=USB_PART_ID, package=packages[USB_PART_ID]),
        CircuitComponent(
            ref="R1", part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
            value=Quantity.ohms(USB_CC_RESISTANCE_OHM), notes="A1 policy: CC1 sink Rd."
        ),
        CircuitComponent(
            ref="R2", part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
            value=Quantity.ohms(USB_CC_RESISTANCE_OHM), notes="A1 policy: CC2 sink Rd."
        ),
        CircuitComponent(
            ref="U2", part_id=REGULATOR_PART_ID, package=packages[REGULATOR_PART_ID]
        ),
        CircuitComponent(
            ref="C1", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=reg_input_cap, notes="Catalog-derived regulator input decoupling."
        ),
        CircuitComponent(
            ref="C2", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=Quantity.farads(REGULATOR_OUTPUT_CAPACITANCE_F),
            notes="A1 policy: regulator output capacitance."
        ),
        CircuitComponent(ref="U1", part_id=mcu.part_id, package=packages[mcu.part_id]),
        CircuitComponent(
            ref="C3", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=mcu_local_cap, notes="Catalog-derived MCU local decoupling."
        ),
        CircuitComponent(
            ref="C4", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=mcu_bulk_cap, notes="Catalog-derived MCU bulk capacitance."
        ),
        CircuitComponent(
            ref="R3", part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
            value=Quantity.ohms(MCU_ENABLE_PULLUP_OHM), notes="A1 policy: MCU enable pull-up."
        ),
        CircuitComponent(
            ref="C5", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=Quantity.farads(MCU_ENABLE_DELAY_CAPACITANCE_F),
            notes="A1 policy: MCU enable delay."
        ),
        CircuitComponent(
            ref="U3", part_id=sensor.part_id, package=packages[sensor.part_id],
            selected_i2c_address=option.address, selected_interfaces=[Interface.I2C]
        ),
        CircuitComponent(
            ref="C6", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=sensor_caps["VDD"], notes="Catalog-derived sensor VDD decoupling."
        ),
        CircuitComponent(
            ref="C7", part_id=CAPACITOR_PART_ID, package=packages[CAPACITOR_PART_ID],
            value=sensor_caps["VDDIO"], notes="Catalog-derived sensor VDDIO decoupling."
        ),
        CircuitComponent(
            ref="R4", part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
            value=Quantity.ohms(I2C_PULLUP_OHM), notes="A1 policy: I2C SDA pull-up."
        ),
        CircuitComponent(
            ref="R5", part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
            value=Quantity.ohms(I2C_PULLUP_OHM), notes="A1 policy: I2C SCL pull-up."
        ),
    ]
    if brief.status_led_count:
        led = catalog.require(LED_PART_ID)
        components.extend(
            [
                CircuitComponent(ref="D1", part_id=LED_PART_ID, package=packages[LED_PART_ID]),
                CircuitComponent(
                    ref="R6", part_id=RESISTOR_PART_ID, package=packages[RESISTOR_PART_ID],
                    value=_led_resistance(regulator, led),
                    notes="Calculated worst case, rounded up to E12."
                ),
            ]
        )
    if brief.include_programming_header:
        components.append(
            CircuitComponent(ref="J2", part_id=HEADER_PART_ID, package=packages[HEADER_PART_ID])
        )

    usb_vbus = _pins_with_role(usb, PinRole.USB_VBUS)
    usb_ground = _pins_with_role(usb, PinRole.GROUND)
    usb_cc = _pins_with_role(usb, PinRole.USB_CC)
    if len(usb_cc) != 2:
        raise _CatalogCapabilityError(f"{usb.part_id} requires exactly two USB CC pins")
    mcu_ground = _pins_with_role(mcu, PinRole.GROUND)
    sensor_ground = _pins_with_role(sensor, PinRole.GROUND)

    ground_pairs = (
        [("J1", pin) for pin in usb_ground]
        + [("R1", "2"), ("R2", "2"), ("U2", _one_pin_with_role(regulator, PinRole.GROUND))]
        + [("C1", "2"), ("C2", "2")]
        + [("U1", pin) for pin in mcu_ground]
        + [("C3", "2"), ("C4", "2"), ("C5", "2")]
        + [("U3", pin) for pin in sensor_ground]
        + [("C6", "2"), ("C7", "2")]
    )
    if option.strap_level == "low":
        ground_pairs.append(("U3", option.strap_pin))
    if brief.status_led_count:
        ground_pairs.append(("D1", _one_pin_with_role(catalog.require(LED_PART_ID), PinRole.CATHODE)))
    if brief.include_programming_header:
        ground_pairs.append(("J2", "2"))

    logic_pairs = [
        ("U2", _pin_named(regulator, "VOUT")), ("C2", "1"),
        ("U1", _pin_named(mcu, "3V3")), ("C3", "1"), ("C4", "1"), ("R3", "2"),
        ("U3", _pin_named(sensor, "VDD")), ("U3", _pin_named(sensor, "VDDIO")),
        ("U3", _pin_named(sensor, "CSB")), ("C6", "1"), ("C7", "1"),
        ("R4", "2"), ("R5", "2"),
    ]
    if option.strap_level == "high":
        logic_pairs.append(("U3", option.strap_pin))
    if brief.include_programming_header:
        logic_pairs.append(("J2", "1"))

    nets = [
        Net(
            name="VBUS", kind=NetKind.POWER,
            external_source=ExternalSource(
                kind=ExternalSourceKind.USB_VBUS,
                voltage=ValueRange(
                    minimum=Quantity.volts(USB_VBUS_MIN_V),
                    typical=Quantity.volts(brief.input_voltage_v),
                    maximum=Quantity.volts(USB_VBUS_MAX_V),
                ),
                current_limit=Quantity.amps(USB_CURRENT_LIMIT_A),
                description="Bus power from a USB-C source, no PD negotiation.",
            ),
            connections=_pins(
                *[("J1", pin) for pin in usb_vbus],
                ("U2", _pin_named(regulator, "VIN")),
                ("U2", _pin_named(regulator, "EN")),
                ("C1", "1"),
            ),
        ),
        Net(name="GND", kind=NetKind.GROUND, connections=_pins(*ground_pairs)),
        Net(name="CC1", connections=_pins(("J1", usb_cc[0]), ("R1", "1"))),
        Net(name="CC2", connections=_pins(("J1", usb_cc[1]), ("R2", "1"))),
        Net(name="3V3", kind=NetKind.POWER, connections=_pins(*logic_pairs)),
    ]

    enable_pairs = [("U1", _pin_named(mcu, "EN")), ("R3", "1"), ("C5", "1")]
    if brief.include_programming_header:
        enable_pairs.append(("J2", "5"))
    nets.extend(
        [
            Net(name="EN", connections=_pins(*enable_pairs)),
            Net(
                name="SDA",
                connections=_pins(
                    ("U1", _pin_named(mcu, "IO21")),
                    ("U3", _one_pin_with_role(sensor, PinRole.I2C_SDA)),
                    ("R4", "1"),
                ),
            ),
            Net(
                name="SCL",
                connections=_pins(
                    ("U1", _pin_named(mcu, "IO22")),
                    ("U3", _one_pin_with_role(sensor, PinRole.I2C_SCL)),
                    ("R5", "1"),
                ),
            ),
        ]
    )
    if brief.include_programming_header:
        nets.extend(
            [
                Net(name="UART_TX", connections=_pins(("U1", _pin_named(mcu, "TXD0")), ("J2", "3"))),
                Net(name="UART_RX", connections=_pins(("U1", _pin_named(mcu, "RXD0")), ("J2", "4"))),
                Net(name="IO0", connections=_pins(("U1", _pin_named(mcu, "IO0")), ("J2", "6"))),
            ]
        )
    if brief.status_led_count:
        led = catalog.require(LED_PART_ID)
        nets.extend(
            [
                Net(
                    name="LED_DRIVE",
                    connections=_pins(("U1", _pin_named(mcu, "IO2")), ("R6", "1")),
                ),
                Net(
                    name="LED_A",
                    connections=_pins(("R6", "2"), ("D1", _one_pin_with_role(led, PinRole.ANODE))),
                ),
            ]
        )

    constraints = [
        DesignConstraint(
            constraint_id="C-1", kind=ConstraintKind.VOLTAGE,
            description="All logic runs from a single 3.3 V rail.",
            source_requirement_id="FR-2", applies_to=["3V3"]
        ),
        DesignConstraint(
            constraint_id="C-2", kind=ConstraintKind.ASSEMBLY,
            description="Prefer packages that a hobbyist can hand solder.", hard=False
        ),
    ]
    if brief.budget_usd is not None:
        constraints.append(
            DesignConstraint(
                constraint_id="C-3", kind=ConstraintKind.COST,
                description=f"Target a component budget of ${brief.budget_usd:.2f}.", hard=False
            )
        )

    return CircuitIR(
        ir_id=f"a1-{brief.fingerprint[:16]}",
        name=brief.project_name,
        components=components,
        nets=nets,
        constraints=constraints,
        design_assumptions=[
            "USB-C is a 5 V power sink; USB data pins are unused.",
            "A1 uses one shared 3.3 V I2C bus and no level shifter.",
        ],
        notes="Synthesized deterministically from SynthesisBrief schema v1 and catalog facts.",
    )


def synthesize_a1(
    brief: SynthesisBrief, catalog: PartCatalog | None = None
) -> SynthesisResult:
    """Compile a typed A1 brief or return a stable, typed refusal."""

    resolved_catalog = catalog or default_catalog()
    if brief.archetype is ArchetypeId.A1_USB_I2C_SENSOR and (
        len(brief.sensors) != 1 or brief.sensors[0].part_id != "BME280"
    ):
        from .a1_extended import synthesize_extended_a1

        return synthesize_extended_a1(brief, resolved_catalog)
    if refusal := _preflight(brief, resolved_catalog):
        return refusal
    try:
        requirements = _requirements(brief)
        circuit = _build(brief, resolved_catalog)
    except _CatalogCapabilityError as exc:
        return _refuse(
            brief,
            RefusalCode.CATALOG_CAPABILITY_MISSING,
            str(exc),
            context={"reason": str(exc)},
        )
    return SynthesisResult(
        brief_fingerprint=brief.fingerprint,
        requirements=requirements,
        circuit=circuit,
    )


__all__ = ["synthesize_a1"]
