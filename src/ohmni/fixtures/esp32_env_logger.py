"""The golden reference project: an ESP32 environmental logger.

USB-C 5 V in, a 3.3 V rail, an ESP32-WROOM-32E, an I2C environmental sensor, a
status LED, and a programming header. Two layers, hand-solderable preference,
roughly a $20 hobbyist budget.

Every broken variant below is the golden circuit with **one** deliberate defect,
so a regression test can name exactly which rule should catch it and nothing
else changes underneath. They are permanent regression cases, not demo props.

The circuit is real. Notable details that are there on purpose:

* The status LED is on IO2, a strapping pin. That is what real ESP32 boards do,
  and it is worth the mentor mentioning.
* CC1 and CC2 get their own 5.1 kohm resistors, not one shared between them.
* EN gets a pull-up and an RC delay capacitor, because the module has no
  internal pull on that pin.
* The sensor's SDO is tied to ground, which strengthens the declared 0x76
  address into something the verifier can derive from the topology instead of
  taking on trust.
"""

from __future__ import annotations

from copy import deepcopy

from ..domain.circuit import (
    CircuitComponent,
    CircuitIR,
    ConstraintKind,
    DesignConstraint,
    ExternalSource,
    ExternalSourceKind,
    Net,
    NetKind,
    PinRef,
)
from ..domain.component import Interface
from ..domain.evidence import DocumentRef, catalog_evidence
from ..domain.requirements import FunctionalRequirement, RequirementsSpec
from ..domain.units import Quantity, ValueRange

V = Quantity.volts
R = Quantity.ohms
F = Quantity.farads

USB_PD_DOC = DocumentRef(
    document_id="usb-2.0-spec",
    title="Universal Serial Bus Specification Revision 2.0",
    manufacturer="USB Implementers Forum",
    part_number="VBUS",
)


def requirements() -> RequirementsSpec:
    """The user's request, structured."""
    return RequirementsSpec(
        project_name="ESP32 environmental logger",
        description=(
            "A small battery-free logger that reads temperature, humidity and pressure over "
            "I2C and reports over Wi-Fi. Powered from USB-C, programmed over a serial header."
        ),
        max_input_voltage=V(5.0),
        target_logic_voltage=V(3.3),
        budget_usd=20.0,
        max_board_layers=2,
        hand_solderable=True,
        interfaces=[Interface.I2C, Interface.UART, Interface.USB_POWER_SINK, Interface.GPIO],
        functional_requirements=[
            FunctionalRequirement(
                requirement_id="FR-1", description="Accept 5 V from a USB-C receptacle."
            ),
            FunctionalRequirement(
                requirement_id="FR-2", description="Provide a regulated 3.3 V rail."
            ),
            FunctionalRequirement(
                requirement_id="FR-3", description="Run an ESP32 with Wi-Fi."
            ),
            FunctionalRequirement(
                requirement_id="FR-4",
                description="Read an I2C environmental sensor on the 3.3 V bus.",
            ),
            FunctionalRequirement(
                requirement_id="FR-5", description="Show status on a single LED."
            ),
            FunctionalRequirement(
                requirement_id="FR-6",
                description="Expose a serial programming and debug header.",
            ),
        ],
        assumptions=[
            "Powered from a standard USB-C source; no USB Power Delivery negotiation.",
            "Indoor use at room temperature; no environmental sealing.",
        ],
    )


def _components() -> list[CircuitComponent]:
    return [
        CircuitComponent(ref="J1", part_id="USB_C_RECEPTACLE_16P", package="USB-C-16P-SMD"),
        CircuitComponent(ref="R1", part_id="GENERIC_RESISTOR", package="0805", value=R(5_100),
                         notes="Rd for CC1. Type-C sinks need one per CC pin."),
        CircuitComponent(ref="R2", part_id="GENERIC_RESISTOR", package="0805", value=R(5_100),
                         notes="Rd for CC2."),
        CircuitComponent(ref="U2", part_id="AP2112K-3.3TRG1", package="SOT-23-5"),
        CircuitComponent(ref="C1", part_id="GENERIC_CAPACITOR", package="0805", value=F(1e-6),
                         notes="Regulator input capacitor."),
        CircuitComponent(ref="C2", part_id="GENERIC_CAPACITOR", package="0805", value=F(1e-6),
                         notes="Regulator output capacitor."),
        CircuitComponent(ref="U1", part_id="ESP32-WROOM-32E", package="Module-SMD-38"),
        CircuitComponent(ref="C3", part_id="GENERIC_CAPACITOR", package="0805", value=F(100e-9),
                         notes="Local decoupling for the module."),
        CircuitComponent(ref="C4", part_id="GENERIC_CAPACITOR", package="0805", value=F(22e-6),
                         notes="Bulk capacitance for RF transmit bursts."),
        CircuitComponent(ref="R3", part_id="GENERIC_RESISTOR", package="0805", value=R(10_000),
                         notes="EN pull-up."),
        CircuitComponent(ref="C5", part_id="GENERIC_CAPACITOR", package="0805", value=F(100e-9),
                         notes="EN RC delay capacitor."),
        CircuitComponent(ref="U3", part_id="BME280", package="LGA-8",
                         selected_i2c_address=0x76, selected_interfaces=[Interface.I2C]),
        CircuitComponent(ref="C6", part_id="GENERIC_CAPACITOR", package="0805", value=F(100e-9),
                         notes="Sensor VDD decoupling."),
        CircuitComponent(ref="C7", part_id="GENERIC_CAPACITOR", package="0805", value=F(100e-9),
                         notes="Sensor VDDIO decoupling."),
        CircuitComponent(ref="R4", part_id="GENERIC_RESISTOR", package="0805", value=R(4_700),
                         notes="I2C SDA pull-up."),
        CircuitComponent(ref="R5", part_id="GENERIC_RESISTOR", package="0805", value=R(4_700),
                         notes="I2C SCL pull-up."),
        CircuitComponent(ref="D1", part_id="GENERIC_LED_GREEN", package="0805"),
        CircuitComponent(ref="R6", part_id="GENERIC_RESISTOR", package="0805", value=R(330),
                         notes="LED current limiting."),
        CircuitComponent(ref="J2", part_id="HEADER_1X6_254", package="1x6-2.54mm-THT"),
    ]


def _pins(*pairs: tuple[str, str]) -> list[PinRef]:
    return [PinRef(component=c, pin=p) for c, p in pairs]


def _nets() -> list[Net]:
    return [
        Net(
            name="VBUS",
            kind=NetKind.POWER,
            external_source=ExternalSource(
                kind=ExternalSourceKind.USB_VBUS,
                # USB 2.0 allows VBUS at a downstream port to sit between 4.75 V
                # and 5.25 V. Using the range rather than a flat 5 V is what
                # lets the verifier reason about tolerance instead of nominals.
                voltage=ValueRange(minimum=V(4.75), typical=V(5.0), maximum=V(5.25)),
                current_limit=Quantity.amps(0.5),
                description="Bus power from a USB-C source, no PD negotiation.",
                evidence=[
                    catalog_evidence(
                        "USB VBUS voltage at a downstream port",
                        document=USB_PD_DOC,
                        page=171,
                        text_value="4.75 V to 5.25 V",
                    )
                ],
            ),
            connections=_pins(
                ("J1", "A4"), ("J1", "A9"), ("J1", "B4"), ("J1", "B9"),
                ("U2", "1"), ("U2", "3"), ("C1", "1"),
            ),
            notes="5 V input rail.",
        ),
        Net(
            name="GND",
            kind=NetKind.GROUND,
            connections=_pins(
                ("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"),
                ("R1", "2"), ("R2", "2"),
                ("U2", "2"), ("C1", "2"), ("C2", "2"),
                ("U1", "1"), ("U1", "15"), ("U1", "38"), ("U1", "39"),
                ("C3", "2"), ("C4", "2"), ("C5", "2"),
                ("U3", "1"), ("U3", "7"), ("U3", "5"),
                ("C6", "2"), ("C7", "2"),
                ("D1", "2"), ("J2", "2"),
            ),
            notes="Single ground plane on the bottom layer.",
        ),
        Net(name="CC1", connections=_pins(("J1", "A5"), ("R1", "1"))),
        Net(name="CC2", connections=_pins(("J1", "B5"), ("R2", "1"))),
        Net(
            name="3V3",
            kind=NetKind.POWER,
            connections=_pins(
                ("U2", "5"), ("C2", "1"),
                ("U1", "2"), ("C3", "1"), ("C4", "1"), ("R3", "2"),
                ("U3", "6"), ("U3", "8"), ("U3", "2"),
                ("C6", "1"), ("C7", "1"), ("R4", "2"), ("R5", "2"),
                ("J2", "1"),
            ),
            notes="Regulated logic rail. U3 CSB is tied here to select I2C mode.",
        ),
        Net(
            name="EN",
            connections=_pins(("U1", "3"), ("R3", "1"), ("C5", "1"), ("J2", "5")),
            notes="Module enable, pulled up with an RC delay so reset releases after the rail.",
        ),
        Net(name="SDA", connections=_pins(("U1", "33"), ("U3", "3"), ("R4", "1"))),
        Net(name="SCL", connections=_pins(("U1", "36"), ("U3", "4"), ("R5", "1"))),
        Net(name="UART_TX", connections=_pins(("U1", "35"), ("J2", "3"))),
        Net(name="UART_RX", connections=_pins(("U1", "34"), ("J2", "4"))),
        Net(name="IO0", connections=_pins(("U1", "25"), ("J2", "6"))),
        Net(name="LED_DRIVE", connections=_pins(("U1", "24"), ("R6", "1"))),
        Net(
            name="LED_A",
            connections=_pins(("R6", "2"), ("D1", "1")),
            notes="Private node between the series resistor and the LED anode.",
        ),
    ]


def _constraints() -> list[DesignConstraint]:
    return [
        DesignConstraint(
            constraint_id="C-1",
            kind=ConstraintKind.VOLTAGE,
            description="All logic runs from a single 3.3 V rail.",
            source_requirement_id="FR-2",
            applies_to=["3V3"],
        ),
        DesignConstraint(
            constraint_id="C-2",
            kind=ConstraintKind.ASSEMBLY,
            description="Prefer packages a hobbyist can solder with an iron.",
            hard=False,
        ),
        DesignConstraint(
            constraint_id="C-3",
            kind=ConstraintKind.COST,
            description="Keep the assembled board under about $20 in single quantities.",
            hard=False,
        ),
    ]


def golden() -> CircuitIR:
    """The known-good reference circuit."""
    return CircuitIR(
        ir_id="esp32-env-logger",
        name="ESP32 environmental logger",
        revision=1,
        components=_components(),
        nets=_nets(),
        constraints=_constraints(),
        design_assumptions=[
            ("The USB-C port is power-sink only; D+/D- are left unconnected because "
             "programming goes through the serial header rather than a USB bridge."),
            ("The sensor is read at a low rate, so its supply current is negligible next to "
             "the module's RF bursts."),
        ],
        notes="Golden reference. Any ERROR or CRITICAL finding here is a regression.",
    )


# --------------------------------------------------------------------------
# Broken variants: one deliberate defect each.
# --------------------------------------------------------------------------


def _mutate(name: str, note: str) -> CircuitIR:
    circuit = golden()
    circuit.ir_id = f"esp32-env-logger-{name}"
    circuit.name = f"ESP32 environmental logger ({name})"
    circuit.parent_hash = golden().content_hash
    circuit.revision = 2
    circuit.notes = note
    return circuit


def _net(circuit: CircuitIR, name: str) -> Net:
    net = circuit.net(name)
    if net is None:
        raise KeyError(f"fixture has no net {name!r}")
    return net


def _drop(circuit: CircuitIR, *refs: str) -> None:
    """Remove components and every connection to them."""
    doomed = set(refs)
    circuit.components = [c for c in circuit.components if c.ref not in doomed]
    for net in circuit.nets:
        net.connections = [p for p in net.connections if p.component not in doomed]
    circuit.nets = [n for n in circuit.nets if n.connections]


def broken_sensor_on_5v() -> CircuitIR:
    """Sensor moved to the 5 V rail: an absolute-maximum violation.

    Expected: PB-PWR-001 CRITICAL. This is the variant that proves the verifier
    separates 'outside the recommended range' from 'may destroy the part'.
    """
    circuit = _mutate("sensor-on-5v", "U3 supplies moved from 3V3 to VBUS.")
    three_v3 = _net(circuit, "3V3")
    vbus = _net(circuit, "VBUS")
    moved = _pins(("U3", "6"), ("U3", "8"))
    three_v3.connections = [
        p for p in three_v3.connections if (p.component, p.pin) not in {("U3", "6"), ("U3", "8")}
    ]
    vbus.connections.extend(moved)
    return circuit


def broken_missing_i2c_pullups() -> CircuitIR:
    """No pull-ups on SDA or SCL. Expected: PB-I2C-001 ERROR on both lines."""
    circuit = _mutate("missing-i2c-pullups", "R4 and R5 removed.")
    _drop(circuit, "R4", "R5")
    return circuit


def broken_missing_decoupling() -> CircuitIR:
    """No local decoupling anywhere. Expected: PB-PWR-004 ERROR."""
    circuit = _mutate("missing-decoupling", "C3, C6 and C7 removed; bulk C4 kept.")
    _drop(circuit, "C3", "C6", "C7")
    return circuit


def broken_led_without_resistor() -> CircuitIR:
    """LED wired straight from a GPIO. Expected: PB-LED-001 CRITICAL."""
    circuit = _mutate("led-without-resistor", "R6 removed; D1 anode wired straight to IO2.")
    _drop(circuit, "R6")
    drive = _net(circuit, "LED_DRIVE")
    drive.connections.append(PinRef(component="D1", pin="1"))
    circuit.nets = [n for n in circuit.nets if n.name != "LED_A"]
    return circuit


def broken_duplicate_i2c_address() -> CircuitIR:
    """A second sensor strapped to the same address. Expected: PB-I2C-003 ERROR."""
    circuit = _mutate(
        "duplicate-i2c-address",
        "A second BME280 added on the same bus, also strapped to 0x76.",
    )
    circuit.components.append(
        CircuitComponent(ref="U4", part_id="BME280", package="LGA-8",
                         selected_i2c_address=0x76, selected_interfaces=[Interface.I2C])
    )
    circuit.components.append(
        CircuitComponent(ref="C8", part_id="GENERIC_CAPACITOR", package="0805", value=F(100e-9))
    )
    circuit.components.append(
        CircuitComponent(ref="C9", part_id="GENERIC_CAPACITOR", package="0805", value=F(100e-9))
    )
    _net(circuit, "3V3").connections.extend(
        _pins(("U4", "6"), ("U4", "8"), ("U4", "2"), ("C8", "1"), ("C9", "1"))
    )
    _net(circuit, "GND").connections.extend(
        _pins(("U4", "1"), ("U4", "7"), ("U4", "5"), ("C8", "2"), ("C9", "2"))
    )
    _net(circuit, "SDA").connections.append(PinRef(component="U4", pin="3"))
    _net(circuit, "SCL").connections.append(PinRef(component="U4", pin="4"))
    return circuit


def broken_undersized_regulator() -> CircuitIR:
    """A 250 mA LDO under a module that needs 500 mA. Expected: PB-REG-002 ERROR."""
    circuit = _mutate(
        "undersized-regulator",
        "AP2112K-3.3 (600 mA) swapped for MCP1700-3302E (250 mA).",
    )
    for component in circuit.components:
        if component.ref == "U2":
            component.part_id = "MCP1700T-3302E-TT"
            component.package = "SOT-23-3"
    # The MCP1700 is SOT-23-3: VOUT/GND/VIN, and it has no enable pin.
    vbus = _net(circuit, "VBUS")
    vbus.connections = [
        p for p in vbus.connections if (p.component, p.pin) not in {("U2", "1"), ("U2", "3")}
    ]
    vbus.connections.append(PinRef(component="U2", pin="3"))
    three_v3 = _net(circuit, "3V3")
    three_v3.connections = [p for p in three_v3.connections if (p.component, p.pin) != ("U2", "5")]
    three_v3.connections.append(PinRef(component="U2", pin="1"))
    return circuit


def broken_missing_usb_cc_resistors() -> CircuitIR:
    """No Rd on either CC pin. Expected: PB-USB-001 ERROR on both."""
    circuit = _mutate("missing-usb-cc-resistors", "R1 and R2 removed.")
    _drop(circuit, "R1", "R2")
    return circuit


def broken_floating_enable() -> CircuitIR:
    """EN left with nothing holding it. Expected: PB-PIN-002 ERROR."""
    circuit = _mutate("floating-enable", "R3 and C5 removed, leaving EN floating.")
    _drop(circuit, "R3", "C5")
    return circuit


def broken_shared_cc_resistor() -> CircuitIR:
    """One Rd shared between CC1 and CC2. Expected: PB-USB-001 ERROR."""
    circuit = _mutate("shared-cc-resistor", "R2 removed and CC2 tied to CC1.")
    _drop(circuit, "R2")
    cc1 = _net(circuit, "CC1")
    cc2 = _net(circuit, "CC2")
    cc1.connections.extend(cc2.connections)
    circuit.nets = [n for n in circuit.nets if n.name != "CC2"]
    return circuit


def broken_wrong_package() -> CircuitIR:
    """A package the part is not offered in. Expected: PB-ID-003 ERROR."""
    circuit = _mutate("wrong-package", "U2 asks for a package the AP2112K is not made in.")
    for component in circuit.components:
        if component.ref == "U2":
            component.package = "TO-220"
    return circuit


def broken_pullups_to_5v() -> CircuitIR:
    """I2C pulled up to 5 V on a 3.3 V bus. Expected: PB-I2C-002 ERROR."""
    circuit = _mutate("pullups-to-5v", "R4 and R5 moved from the 3V3 rail to VBUS.")
    three_v3 = _net(circuit, "3V3")
    vbus = _net(circuit, "VBUS")
    moved = {("R4", "2"), ("R5", "2")}
    three_v3.connections = [
        p for p in three_v3.connections if (p.component, p.pin) not in moved
    ]
    vbus.connections.extend(_pins(("R4", "2"), ("R5", "2")))
    return circuit


def broken_ground_pin_on_power() -> CircuitIR:
    """A ground pin wired to the 3.3 V rail. Expected: PB-CONN-002 CRITICAL."""
    circuit = _mutate("ground-pin-on-power", "U3 pin 1 moved from GND to 3V3.")
    ground = _net(circuit, "GND")
    ground.connections = [p for p in ground.connections if (p.component, p.pin) != ("U3", "1")]
    _net(circuit, "3V3").connections.append(PinRef(component="U3", pin="1"))
    return circuit


def broken_invented_pin() -> CircuitIR:
    """A connection to a pin the part does not have. Expected: PB-ID-002 CRITICAL."""
    circuit = _mutate("invented-pin", "SDA connected to a pin number the BME280 does not have.")
    sda = _net(circuit, "SDA")
    sda.connections = [p for p in sda.connections if (p.component, p.pin) != ("U3", "3")]
    sda.connections.append(PinRef(component="U3", pin="42"))
    return circuit


#: name -> (builder, rule the defect must trip, minimum severity expected).
BROKEN_VARIANTS: dict[str, tuple[str, str]] = {
    "sensor_on_5v": ("PB-PWR-001", "critical"),
    "missing_i2c_pullups": ("PB-I2C-001", "error"),
    "missing_decoupling": ("PB-PWR-004", "error"),
    "led_without_resistor": ("PB-LED-001", "critical"),
    "duplicate_i2c_address": ("PB-I2C-003", "error"),
    "undersized_regulator": ("PB-REG-002", "error"),
    "missing_usb_cc_resistors": ("PB-USB-001", "error"),
    "floating_enable": ("PB-PIN-002", "error"),
    "shared_cc_resistor": ("PB-USB-001", "error"),
    "wrong_package": ("PB-ID-003", "error"),
    "pullups_to_5v": ("PB-I2C-002", "error"),
    "ground_pin_on_power": ("PB-CONN-002", "critical"),
    "invented_pin": ("PB-ID-002", "critical"),
}

BUILDERS = {
    "golden": golden,
    "sensor_on_5v": broken_sensor_on_5v,
    "missing_i2c_pullups": broken_missing_i2c_pullups,
    "missing_decoupling": broken_missing_decoupling,
    "led_without_resistor": broken_led_without_resistor,
    "duplicate_i2c_address": broken_duplicate_i2c_address,
    "undersized_regulator": broken_undersized_regulator,
    "missing_usb_cc_resistors": broken_missing_usb_cc_resistors,
    "floating_enable": broken_floating_enable,
    "shared_cc_resistor": broken_shared_cc_resistor,
    "wrong_package": broken_wrong_package,
    "pullups_to_5v": broken_pullups_to_5v,
    "ground_pin_on_power": broken_ground_pin_on_power,
    "invented_pin": broken_invented_pin,
}


def build(name: str) -> CircuitIR:
    return deepcopy(BUILDERS[name]())
