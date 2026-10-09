"""Deterministic controller netlist; no decorative or electrically fictional ICs."""
from dataclasses import dataclass

from ohmni.adapters.fakes import InMemoryPartCatalog
from ohmni.domain.circuit import (
    CircuitComponent,
    CircuitIR,
    ExternalSource,
    ExternalSourceKind,
    Net,
    NetKind,
    PinRef,
)
from ohmni.domain.component import Interface
from ohmni.domain.requirements import FunctionalRequirement, RequirementsSpec
from ohmni.domain.units import Quantity

from .catalog import (
    BUTTON_ID,
    CAPACITORS,
    HEADER_ID,
    LED_ID,
    MCU_GND,
    MCU_ID,
    MCU_PIN_NAMES,
    MCU_VDD,
    RESISTORS,
    SHIFT_ID,
    SWD_ID,
    USB_ID,
    assumption,
    controller_catalog,
    voltage_range,
)

HEADER_TOP_GPIO_PINS = (98, 97, 96, 95, 93, 92, 91, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78)
HEADER_SIDE_GPIO_PINS = (1, 2, 3, 4, 5, 67, 66, 65, 64, 63, 62, 61, 60, 59, 58, 57, 56, 55)
# Custom board wiring, not a component-manufacturer pin-map change. Top-edge
# GPIO use the near/lower header row; side-edge GPIO use the far/upper row.
HEADER_GPIO_PINS = tuple(pin for pair in zip(HEADER_TOP_GPIO_PINS, HEADER_SIDE_GPIO_PINS, strict=True) for pin in pair)
SHIFT_OUTPUT_PINS = (15, 1, 2, 3, 4, 5, 6, 7)
CONTROL_PINS = {"EEPROM_CS": 29, "SPI_SCK": 30, "SPI_MISO": 31, "SPI_MOSI": 32,
                "SR_DATA": 38, "SR_CLK": 39, "SR_LATCH": 40, "SR_OE": 41,
                "SR_CLR": 42, "NRST": 14, "BOOT0": 94, "BOOT1": 37,
                "USER": 23, "SWDIO": 72, "SWCLK": 76}
PULLS = {"R3": ("NRST", "3V3"), "R4": ("BOOT0", "GND"),
         "R5": ("BOOT1", "GND"), "R6": ("EEPROM_CS", "3V3"),
         "R7": ("SR_DATA", "GND"), "R8": ("SR_CLK", "GND"),
         "R9": ("SR_LATCH", "GND"), "R10": ("SR_OE", "3V3"),
         "R11": ("SR_CLR", "3V3"), "R12": ("USER", "3V3")}
CAP_VALUES = {"C1": 1e-6, "C2": 1e-6, **{f"C{i}": 100e-9 for i in range(3, 8)},
              "C8": 10e-6, "C9": 100e-9, "C10": 100e-9, "C11": 1e-6,
              "C12": 100e-9, "C13": 100e-9, "C14": 100e-9, "C15": 100e-9}
CAP_PURPOSES = {"C1": "U2 input", "C2": "U2 output", "C3": "U1 VDD_5 pin 11",
                "C4": "U1 VDD_4 pin 28", "C5": "U1 VDD_1 pin 50", "C6": "U1 VDD_2 pin 75",
                "C7": "U1 VDD_3 pin 100", "C8": "U1 digital bulk", "C9": "U1 VBAT pin 6",
                "C10": "U1 VDDA/VREF+ high-frequency", "C11": "U1 VDDA/VREF+ bulk",
                "C12": "U1 NRST", "C13": "U3 EEPROM bypass", "C14": "U4 register bypass",
                "C15": "U5 register bypass"}


@dataclass(frozen=True)
class LandingDesign:
    circuit: CircuitIR
    catalog: InMemoryPartCatalog
    requirements: RequirementsSpec


def build_design():
    catalog = controller_catalog()
    components, nodes = [], {}

    def part(ref, part_id, package, value=None, notes=None):
        components.append(CircuitComponent(ref=ref, part_id=part_id, package=package, value=value,
                                          notes=notes, evidence=catalog.require(part_id).evidence))

    def wire(net, ref, pin):
        nodes.setdefault(net, []).append(PinRef(component=ref, pin=str(pin)))

    def resistor(ref, ohms, first, second):
        part(ref, RESISTORS[ohms], "0603", Quantity.ohms(ohms))
        wire(first, ref, 1)
        wire(second, ref, 2)

    part("U1", MCU_ID, "LQFP-100", notes="8 MHz HSI; no USB data, HSE or LSE. Pin 73 is NC. Unused GPIOs require firmware analog/input configuration.")
    components[-1].selected_interfaces = [Interface.SPI, Interface.GPIO, Interface.SWD]
    part("U2", "AP2112K-3.3TRG1", "SOT-23-5")
    part("U3", "25LC256-I/SN", "SOIC-8")
    components[-1].selected_interfaces = [Interface.SPI]
    part("U4", SHIFT_ID, "SOIC-16", notes="Indicator bank 0..7; active-high outputs.")
    part("U5", SHIFT_ID, "SOIC-16", notes="Indicator bank 8..15; QH prime intentionally unused.")
    part("J1", USB_ID, "USB-C-16P-SMD", notes="Power only; D+/D-/SBU unconnected. No USB current entitlement inferred.")
    part("J2", HEADER_ID, "2x20-2.54mm-THT", notes="1/2 GND, 39/40 3V3 output, 3..38 GPIO; not Raspberry Pi compatible. External loads not qualified.")
    part("J3", SWD_ID, "1x6-2.54mm-THT", notes="1 3V3 reference, 2 SWDIO, 3 GND, 4 SWCLK, 5 NRST, 6 GND. Custom debug connector; never supply from probe.")
    part("SW1", BUTTON_ID, "6mm-THT", notes="Reset switch, NO.")
    part("SW2", BUTTON_ID, "6mm-THT", notes="User switch, NO; firmware debounce required.")

    for pin in (*MCU_VDD, 6, 21, 22):
        wire("3V3", "U1", pin)
    for pin in MCU_GND:
        wire("GND", "U1", pin)
    for net, pin in CONTROL_PINS.items():
        wire(net, "U1", pin)
    for pin in ("A4", "A9", "B4", "B9"):
        wire("VBUS", "J1", pin)
    for pin in ("A1", "A12", "B1", "B12", "S1"):
        if catalog.require(USB_ID).pin(pin):
            wire("GND", "J1", pin)
    wire("CC1", "J1", "A5")
    wire("CC2", "J1", "B5")
    resistor("R1", 5100, "CC1", "GND")
    resistor("R2", 5100, "CC2", "GND")
    for pin, net in {1: "VBUS", 2: "GND", 3: "VBUS", 5: "3V3"}.items():
        wire(net, "U2", pin)
    for pin, net in {1: "EEPROM_CS", 2: "SPI_MISO", 3: "3V3", 4: "GND",
                     5: "SPI_MOSI", 6: "SPI_SCK", 7: "3V3", 8: "3V3"}.items():
        wire(net, "U3", pin)
    for ref in ("U4", "U5"):
        for pin, net in {8: "GND", 16: "3V3", 10: "SR_CLR", 11: "SR_CLK",
                         12: "SR_LATCH", 13: "SR_OE"}.items():
            wire(net, ref, pin)
    wire("SR_DATA", "U4", 14)
    wire("SR_CHAIN", "U4", 9)
    wire("SR_CHAIN", "U5", 14)
    for index, pin in enumerate(HEADER_GPIO_PINS, 3):
        name = f"GPIO_{MCU_PIN_NAMES[pin]}"
        wire(name, "U1", pin)
        wire(name, "J2", index)
    for pin in (1, 2):
        wire("GND", "J2", pin)
    for pin in (39, 40):
        wire("3V3", "J2", pin)
    for pin, net in {1: "3V3", 2: "SWDIO", 3: "GND", 4: "SWCLK", 5: "NRST", 6: "GND"}.items():
        wire(net, "J3", pin)
    for ref, net in (("SW1", "NRST"), ("SW2", "USER")):
        wire(net, ref, 1)
        wire("GND", ref, 2)
    for ref, (signal, rail) in PULLS.items():
        resistor(ref, 10000, signal, rail)
    for ref, value in CAP_VALUES.items():
        package = "0805" if ref == "C8" else "0603"
        part(ref, CAPACITORS[value], package, Quantity.farads(value), CAP_PURPOSES[ref])
        wire("VBUS" if ref == "C1" else "NRST" if ref == "C12" else "3V3", ref, 1)
        wire("GND", ref, 2)
    for index in range(16):
        driver = "U4" if index < 8 else "U5"
        output, anode = f"LED{index}_DRIVE", f"LED{index}_ANODE"
        wire(output, driver, SHIFT_OUTPUT_PINS[index % 8])
        resistor(f"R{20+index}", 1000, output, anode)
        part(f"D{index+1}", LED_ID, "0603", notes=f"Indicator {index}; 1=K to ground, 2=A via 1 kohm.")
        wire(anode, f"D{index+1}", 2)
        wire("GND", f"D{index+1}", 1)
    assumptions = [
        "Reference-inspired authored 3.3 V GPIO/pattern controller; firmware is not implemented or tested.",
        "Use 8 MHz internal HSI, SPI <=1 MHz initially, separate bit-banged shift clock <=100 kHz. No USB data or crystal accuracy claim.",
        "Firmware must keep OE high until registers are cleared, 16 bits shifted and latched; then enable. No startup pattern is guaranteed by hardware.",
        "Unused GPIOs are physically NC and must be configured to a defined low-power state. U1.73 is manufacturer NC and must remain unconnected.",
        "All VDD/VBAT/VDDA/VREF+ are tied to 3V3; VSSA/VREF- and digital VSS share ground. No precision-ADC or isolated analog performance claimed.",
        "USB source is assumed 4.75-5.25 V; current advertisement is not detected and available current is unknown. Header loading is not authorized by LDO rating.",
        "MLCC DC-bias, LDO stability, thermal rise, indicator brightness and 3.3 V output drive remain unverified; no bench or SPICE run.",
        "Exact electronic MPNs are selected, but nominal package meshes and KiCad footprints are not a verified procurement or mechanical-fit release.",
    ]
    nets = []
    for name, connections in nodes.items():
        kind = NetKind.GROUND if name == "GND" else NetKind.POWER if name in ("VBUS", "3V3") else NetKind.SIGNAL
        source = ExternalSource(kind=ExternalSourceKind.USB_VBUS, voltage=voltage_range(4.75, 5.25, 5),
            current_limit=None, description="Assumed USB input voltage; source current entitlement unknown.",
            evidence=[assumption("USB input envelope", assumptions[5])]) if name == "VBUS" else None
        nets.append(Net(name=name, kind=kind, connections=connections, external_source=source))
    circuit = CircuitIR(ir_id="landing-controller-stm32f103", name="OHMNI controller 01", revision=1,
        components=components, nets=nets, design_assumptions=assumptions,
        notes="Authored draft from real orderable parts. The reference image informs composition, never pinout or circuit evidence.")
    requirements = RequirementsSpec(project_name=circuit.name,
        description="USB-powered controller, 36 GPIO breakout, 16 latched indicators and SPI EEPROM.",
        max_input_voltage=Quantity.volts(5.25), target_logic_voltage=Quantity.volts(3.3),
        hand_solderable=False, max_board_layers=2,
        interfaces=[Interface.GPIO, Interface.SPI, Interface.SWD, Interface.USB_POWER_SINK],
        required_part_ids=[MCU_ID, SHIFT_ID, "25LC256-I/SN", "AP2112K-3.3TRG1"],
        functional_requirements=[FunctionalRequirement(requirement_id="FR-CONTROLLER",
            description="Demonstrate GPIO breakout, persistent pattern storage and 16 indicators using actual connected parts.")],
        assumptions=assumptions, notes="SMT assembly; authored engineering demo, not a manufacturing release.")
    return LandingDesign(circuit, catalog, requirements)
