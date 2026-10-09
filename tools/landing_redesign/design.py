"""Deterministic electrical redesign, independent of production synthesis defaults.

``build_design(include_i2c_extension=False)`` returns a ``LandingDesign`` with
``circuit`` (CircuitIR), ``catalog`` (isolated InMemoryPartCatalog), and
``requirements`` (RequirementsSpec). No files, network calls, routes, physical
fits or verification outcomes are produced by construction.
"""

from dataclasses import dataclass

from ohmni.adapters.fakes import InMemoryPartCatalog
from ohmni.domain.circuit import (
    CircuitComponent,
    CircuitIR,
    ConstraintKind,
    DesignConstraint,
    Net,
    PinRef,
)
from ohmni.domain.component import Interface
from ohmni.domain.requirements import FunctionalRequirement, RequirementsSpec
from ohmni.domain.units import Quantity, Unit
from ohmni.synthesis.a2 import synthesize_a2
from ohmni.synthesis.models import ArchetypeId, SynthesisBrief

from .catalog import (
    BUCK_PART_ID,
    HEADER_PART_ID,
    INDUCTOR_PART_ID,
    TRANSLATOR_PART_ID,
    assumption,
    redesign_catalog,
    reported,
)


@dataclass(frozen=True)
class LandingDesign:
    circuit: CircuitIR
    catalog: InMemoryPartCatalog
    requirements: RequirementsSpec


def _pins(*pairs: tuple[str, str]) -> list[PinRef]:
    return [PinRef(component=ref, pin=pin) for ref, pin in pairs]


def build_design(include_i2c_extension: bool = False) -> LandingDesign:
    """Compose the approved sensor-controller and replace only its power stage.

    The optional I2C extension is a separate board-powered 5 V header. USB data
    remains unused. The requested output target is not installed as an external
    source or a fixed regulator fact; deriving buck behavior requires independent
    topology and transient checks beyond the core DC verifier's capabilities.
    """
    if not isinstance(include_i2c_extension, bool):
        raise TypeError("include_i2c_extension must be an explicit boolean")
    catalog = redesign_catalog()
    brief = SynthesisBrief(
        archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
        project_name="OHMNI landing sensor controller redesign",
        description="USB-C powered ESP32/BME280 controller with a real synchronous buck power stage.",
        sensors=[{"part_id": "BME280", "address": 0x76}], status_led_count=4,
        button_count=2, include_programming_header=True,
        board_width_mm=90, board_height_mm=55,
    )
    seed = synthesize_a2(brief, catalog)
    if not seed.accepted or seed.circuit is None or seed.requirements is None:
        raise ValueError(f"Existing sensor-controller topology was refused: {seed.refusal}")
    parent_hash = seed.circuit.content_hash
    components = [part.model_copy(deep=True) for part in seed.circuit.components if part.ref != "U2"]
    nets = [net.model_copy(deep=True) for net in seed.circuit.nets]
    for net in nets:
        net.connections = [pin for pin in net.connections if pin.component != "U2"]
        if net.name in {"SDA", "SCL"}:
            net.name += "_3V3"
    by_net = {net.name: net for net in nets}
    by_ref = {part.ref: part for part in components}

    def part(ref, part_id, package, value=None, notes=None, evidence=()):
        created = CircuitComponent(ref=ref, part_id=part_id, package=package, value=value,
                                   notes=notes, evidence=list(evidence))
        components.append(created)
        by_ref[ref] = created
        return created

    def resistor(ref, ohms, notes, evidence):
        return part(ref, "GENERIC_RESISTOR", "0805", Quantity.ohms(ohms), notes, evidence)

    power_example = reported("buck", 8, "Buck input/output capacitor example",
                             "4.7 uF input GRM21BR71A475KA73L; 10 uF output GRM21BR71A106KE51L; 10 V X7R.")
    divider_example = reported("buck_design", 18, "Feedback divider example", "453 kohm upper, 100 kohm lower.")
    component_selection = assumption("Passive selection policy", (
        "Feedback resistors selected at 1% tolerance. Generic capacitor records preserve unresolved "
        "orderable selection, effective capacitance and DC-bias/temperature validation."))
    part("U2", BUCK_PART_ID, "SOT-23-5", evidence=catalog.require(BUCK_PART_ID).evidence)
    part("L1", INDUCTOR_PART_ID, "XAL4020", Quantity(value=2.2e-6, unit=Unit.HENRY),
         "Power inductor between switching node and output; not the proposed Bourns footprint.",
         catalog.require(INDUCTOR_PART_ID).evidence)
    resistor("R6", 453_000, "Upper feedback arm; 1% selected tolerance.", [divider_example, component_selection])
    resistor("R7", 100_000, "Lower feedback arm; 1% selected tolerance.", [divider_example, component_selection])
    for ref, capacitance, note in (
        ("C1", 4.7e-6, "Buck local input: 4.7 uF, 10 V X7R target; capacitor selection/DC bias unverified."),
        ("C2", 10e-6, "Buck local output: 10 uF, 10 V X7R target; additional MCU bulk retained."),
    ):
        by_ref[ref].value = Quantity.farads(capacitance)
        by_ref[ref].notes = note
        by_ref[ref].evidence = [power_example, component_selection]
    mcu_caps = reported("esp32", 39, "Module peripheral decoupling", "22 uF bulk and 0.1 uF local capacitance.")
    mcu_reset = reported("esp32", 39, "Module EN starting RC values", "10 kohm pull-up and 1 uF capacitor; tune to startup timing.")
    for ref, capacitance in (("C3", 0.1e-6), ("C4", 22e-6), ("C5", 1e-6)):
        by_ref[ref].value = Quantity.farads(capacitance)
        by_ref[ref].evidence = [mcu_reset if ref == "C5" else mcu_caps]
    by_ref["R3"].value = Quantity.ohms(10_000)
    by_ref["R3"].evidence = [mcu_reset]
    # Seed series resistors retain 330 ohm but must not cite the removed LDO.
    for ref in ("R10", "R11", "R12", "R13"):
        by_ref[ref].evidence = [assumption("Indicator resistor selection", (
            "330 ohm series resistor for a generic green LED on the intended 3.3 V domain. "
            "Actual LED selection and GPIO aggregate current remain unverified."))]
        by_ref[ref].notes = "330 ohm per indicator; anode catalog pin 1 maps explicitly to physical pad 2."
    for ref in ("R20", "R21"):
        by_ref[ref].evidence = [assumption("Button pull-up selection", "10 kohm to the intended 3.3 V rail.")]
        by_ref[ref].notes = "10 kohm button pull-up; firmware must configure an input and debounce it."

    by_net["VBUS"].connections += _pins(("U2", "1"), ("U2", "4"))
    by_net["GND"].connections += _pins(("U2", "2"), ("R7", "2"))
    by_net["3V3"].connections += _pins(("L1", "2"), ("R6", "1"))
    nets += [Net(name="SW_NODE", connections=_pins(("U2", "3"), ("L1", "1")),
                 notes="Switching waveform; this is not a regulated DC power rail."),
             Net(name="FB_REFB", connections=_pins(("U2", "5"), ("R6", "2"), ("R7", "1")))]
    by_net["3V3"].notes = "Target nominal 3.318 V from 0.600*(1+453k/100k); no DC source is fabricated."
    source = by_net["VBUS"].external_source
    source.current_limit = None
    source.description = "Assumed 4.75-5.25 V USB-C source; available current unknown without source characterization/current-advertisement detection."
    source.evidence = [assumption("USB supply design envelope", source.description)]

    assumptions = [*seed.requirements.assumptions,
        "The buck output is a target derived from feedback, not a fixed DC catalog output; core DC voltage coverage is incomplete.",
        "USB source capability is an assumed 500 mA input budget; the converter's 2 A capability does not authorize drawing 2 A from USB.",
        "Buck stability, startup, ripple, capacitor derating, thermal limits and EMI require further analysis or bench validation.",
        "The module needs at least 500 mA supply capability; that recommendation is not its guaranteed maximum consumption.",
        "Antenna placement and copper keepout require physical verification; this CircuitIR alone cannot verify RF behavior.",
        "Generic passives, LEDs, buttons and headers retain unresolved exact MPN and physical ratings.",
    ]
    requirements = seed.requirements.model_copy(deep=True)
    requirements.required_part_ids += [BUCK_PART_ID, INDUCTOR_PART_ID]
    requirements.hand_solderable = not include_i2c_extension
    requirements.notes = "Isolated landing redesign. No fabrication-readiness, simulation, ERC or DRC pass follows from construction."
    if include_i2c_extension:
        part("U4", TRANSLATOR_PART_ID, "VSSOP-8-DCU", evidence=catalog.require(TRANSLATOR_PART_ID).evidence)
        by_ref["U4"].selected_interfaces = [Interface.I2C]
        part("J3", HEADER_PART_ID, "1x4-2.54mm-THT", notes="1 GND, 2 board 5 V OUT, 3 SDA_5V, 4 SCL_5V.")
        pullup = assumption("Extension pull-ups and bus speed", (
            "4.7 kohm per signal per side, 100 kHz initial target; total load target <=200 pF per line. "
            "Includes external pull-ups and cable capacitance; not measured or guaranteed."))
        resistor("R8", 4700, "High-side SDA pull-up to board VBUS.", [pullup])
        resistor("R9", 4700, "High-side SCL pull-up to board VBUS.", [pullup])
        bias = reported("translator", 18, "Translation bias selection", "EN/VREF2 tied; 200 kohm to high-side supply and 100 pF filter.")
        resistor("R14", 200_000, "High impedance reference bias; never a direct VREF2-to-VBUS connection.", [bias])
        part("C8", "GENERIC_CAPACITOR", "0805", Quantity.farads(100e-12),
             "Bias filter adjacent to U4 VREF2; distinct from bus-line capacitance.", [bias])
        by_net["GND"].connections += _pins(("U4", "1"), ("J3", "1"), ("C8", "2"))
        by_net["3V3"].connections += _pins(("U4", "2"))
        by_net["VBUS"].connections += _pins(("J3", "2"), ("R8", "2"), ("R9", "2"), ("R14", "1"))
        by_net["SDA_3V3"].connections += _pins(("U4", "4"))
        by_net["SCL_3V3"].connections += _pins(("U4", "3"))
        nets += [
            Net(name="SDA_5V", connections=_pins(("U4", "5"), ("J3", "3"), ("R8", "1"))),
            Net(name="SCL_5V", connections=_pins(("U4", "6"), ("J3", "4"), ("R9", "1"))),
            Net(name="I2C_BIAS", connections=_pins(("U4", "7"), ("U4", "8"), ("R14", "2"), ("C8", "1"))),
        ]
        assumptions += [
            "External I2C uses a separate J3 header at 100 kHz; it is not USB data and carries no USB-to-I2C conversion.",
            "J3 pin 2 supplies board VBUS outward. Independently powered endpoints, backfeed, hot-plug and ESD behavior are unverified.",
            "PCA9306 is a passive translator; both bus sides share the capacitance and sink-current budget.",
            "External bus target is <=200 pF total per line; 4.7 kohm rise-time estimate and actual low-level margins require validation.",
        ]
        requirements.required_part_ids += [TRANSLATOR_PART_ID, HEADER_PART_ID]
        requirements.functional_requirements.append(FunctionalRequirement(
            requirement_id="FR-EXT-I2C", description="Provide a distinct board-powered 5 V I2C expansion header at 100 kHz."))
    requirements.assumptions = assumptions
    constraints = [constraint.model_copy(deep=True) for constraint in seed.circuit.constraints]
    constraints += [DesignConstraint(
        constraint_id="LANDING-BUCK-TOPOLOGY", kind=ConstraintKind.VOLTAGE,
        description="Regulation requires VIN/EN, SW-to-inductor, output capacitor and complete divider topology.",
        applies_to=["U2", "L1", "C1", "C2", "R6", "R7"],
    )]
    if include_i2c_extension:
        constraints.append(DesignConstraint(
            constraint_id="LANDING-I2C-BIAS", kind=ConstraintKind.INTERFACE,
            description="PCA9306 pins 7/8 share a 200 kohm/100 pF bias node; no direct high-rail connection.",
            applies_to=["U4", "R14", "C8", "J3"],
        ))
    circuit = CircuitIR(
        ir_id="landing-sensor-controller-buck" + ("-i2c5v" if include_i2c_extension else ""),
        name=brief.project_name, revision=2, parent_hash=parent_hash,
        components=components, nets=nets, constraints=constraints, design_assumptions=assumptions,
        notes="Real deterministic redesign derived from the A2 sensor-controller brief, not a visual inventory edit.",
    )
    return LandingDesign(circuit=circuit, catalog=catalog, requirements=requirements)
