"""The product-shaped projection of one completed engineering run.

`demo.py` projects the engineering pipeline. This module projects the same
verified reports into the shape a person actually reads: a brief they agreed
to, four functional systems, a board they can turn over, the one problem Ohmni
caught, and an honest account of what is still untested.

The boundary is the same and it is strict. Nothing here decides electrical,
physical, routing, manufacturing, or pricing truth. Every status is copied from
a typed report; every geometric coordinate is copied from a compiled artifact;
every derived grouping states the topology it was derived from. Where a value
is UNKNOWN it stays UNKNOWN, and where a subsystem is UNSUPPORTED it stays
UNSUPPORTED, because a friendlier presentation of an unverified claim is still
an unverified claim.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from ..domain.circuit import CircuitIR, NetKind
from ..domain.component import ComponentCategory, Interface, PinRole
from ..domain.verification import RuleCategory, RuleOutcome, VerificationReport
from ..physical.footprints import footprint
from ..verifier.engine import SUBSYSTEM_CATEGORIES
from .naming import Term, component_term, humanise_refs, net_driver_voltage, net_term, phrase
from .systems import (
    ComponentGrouping,
    Flow,
    FunctionalSystem,
    SystemId,
    build_flows,
    build_systems,
    group_components,
    system_name,
)

#: Display-only board thickness. Ohmni does not model stack-up, so this is a
#: rendering constant and is labelled as one wherever it reaches the interface.
DISPLAY_BOARD_THICKNESS_MM = 1.6

STAGE_SEQUENCE: list[tuple[str, str, str]] = [
    ("brief", "Understanding what you asked for",
     "Turning your description into a specification, and saying out loud what it assumed."),
    ("design", "Choosing parts and wiring them up",
     "Selecting components from parts it has evidence for, and connecting them."),
    ("check", "Checking the electrical design",
     "Running deterministic rules over the circuit before anything is drawn."),
    ("repair", "Fixing what it found",
     "Applying a narrow, typed change and re-running every check from the start."),
    ("schematic", "Drawing the schematic",
     "Emitting a real KiCad schematic, then letting KiCad's own checker inspect it."),
    ("placement", "Arranging parts on the board",
     "Placing each component and measuring the distances that matter."),
    ("routing", "Drawing the copper",
     "Finding a path for every connection, then checking the copper independently."),
    ("manufacture", "Checking it can be made",
     "Comparing the board against a manufacturing profile and packaging the files."),
]

#: Plain-language names for the verification layers, so a beginner reads
#: "Voltages and currents" rather than "electrical".
#:
#: The EDA entry names *Ohmni's own* schematic-file rule set, of which there are
#: none. It must not be called "KiCad's own opinion": KiCad's checker does run,
#: reports separately, and passes -- labelling the empty Ohmni category after
#: the external tool told the reader KiCad had both checked and not checked.
CHECK_GROUPS: dict[RuleCategory, tuple[str, str]] = {
    RuleCategory.IDENTITY: (
        "The parts themselves",
        "Are these real parts, in packages they are actually sold in, with pins that exist?"),
    RuleCategory.CONNECTIVITY: (
        "How things are connected",
        "Does everything have power and ground, and is anything left dangling?"),
    RuleCategory.PIN_SEMANTICS: (
        "What each pin is doing",
        "Is anything fighting over the same wire, or left floating when it must not be?"),
    RuleCategory.ELECTRICAL: (
        "Voltages and currents",
        "Is every part inside the voltage it is rated for, and can the supply deliver the load?"),
    RuleCategory.INTERFACE: (
        "The communication buses",
        "Are the shared wires between chips set up the way those chips need?"),
    RuleCategory.THERMAL: (
        "Heat",
        "Ohmni has no thermal rules. Nothing here was analysed."),
    RuleCategory.EDA: (
        "Ohmni's own schematic-file checks",
        "Ohmni does not inspect the schematic file itself yet. KiCad's checker does, and reports below."),
    RuleCategory.SIMULATION: (
        "Simulation",
        "Ohmni does not simulate circuits. Nothing here was simulated."),
}

#: Which of the three families a check group belongs to. Keeping Ohmni's own
#: rules, an external tool's independent opinion, and areas nobody analysed in
#: separate sections is what stops them reading as contradictions.
class CheckFamily(StrEnum):
    OHMNI = "ohmni"
    EXTERNAL = "external"
    NOT_ANALYSED = "not_analysed"


CHECK_FAMILY_LABELS: dict[CheckFamily, tuple[str, str]] = {
    CheckFamily.OHMNI: (
        "Ohmni's own checks",
        "Deterministic rules Ohmni ran over your design."),
    CheckFamily.EXTERNAL: (
        "Checked independently by KiCad",
        "Different software, written by other people, inspecting the same files."),
    CheckFamily.NOT_ANALYSED: (
        "Not analysed",
        "Areas Ohmni has no rules for. These are not passes."),
}

_PASSIVE_ROLE_HINTS = {
    ComponentCategory.CAPACITOR: "capacitor",
    ComponentCategory.RESISTOR: "resistor",
}


class BoardPad(BaseModel):
    number: str
    net_name: str | None = None
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    kind: str
    shape: str


class BoardComponent(BaseModel):
    """One placed part, with the exact geometry the PCB compiler emitted."""

    ref: str
    part_id: str
    name: Term
    package: str
    footprint_id: str
    system: SystemId
    x_mm: float
    y_mm: float
    rotation_deg: float
    side: str
    width_mm: float
    height_mm: float
    placement_reason: str
    pads: list[BoardPad]
    net_names: list[str]


class BoardTrack(BaseModel):
    net_name: str
    layer: str
    start_x_mm: float
    start_y_mm: float
    end_x_mm: float
    end_y_mm: float
    width_mm: float


class BoardVia(BaseModel):
    net_name: str
    x_mm: float
    y_mm: float
    diameter_mm: float
    drill_mm: float


class BoardGeometry(BaseModel):
    """Structured board geometry, copied from one fingerprinted artifact."""

    artifact_fingerprint: str
    routing_plan_fingerprint: str
    constraints_hash: str
    width_mm: float
    height_mm: float
    layer_count: int
    display_thickness_mm: float = DISPLAY_BOARD_THICKNESS_MM
    thickness_is_display_only: bool = True
    layers: list[str]
    #: How the board edge is described where the interface shows its thickness.
    thickness_note: str = (
        "Board thickness is a display value. Ohmni does not model the layer stack-up."
    )
    components: list[BoardComponent]
    tracks: list[BoardTrack]
    vias: list[BoardVia]
    net_names: list[str]


class SchematicPin(BaseModel):
    pin: str
    net_name: str | None
    x_mm: float
    y_mm: float


class SchematicSymbol(BaseModel):
    ref: str
    part_id: str
    name: Term
    system: SystemId
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    pins: list[SchematicPin]


class SchematicGeometry(BaseModel):
    artifact_fingerprint: str
    connection_method: str
    symbols: list[SchematicSymbol]
    net_names: list[str]


class BriefLine(BaseModel):
    field: str
    label: str
    value: str
    origin: str
    #: How this value relates to what the user actually typed. `quoted` means
    #: the value appears in their words; `interpreted` means Ohmni read it out
    #: of their description; `assumed`/`default` mean Ohmni supplied it. The
    #: Agree stage must not tell someone they wrote a value they never wrote.
    grounding: str = "interpreted"
    source_text: str | None = None


class Brief(BaseModel):
    """What the user asked for, kept apart from what Ohmni supplied."""

    project_name: str
    request: str
    asked_for: list[BriefLine]
    assumed: list[BriefLine]
    needs_clarification: list[BriefLine]


class ComponentCard(BaseModel):
    ref: str
    part_id: str
    name: Term
    display_name: str
    package: str
    system: SystemId
    purpose: str
    grouping_basis: str
    quantity_on_board: int
    line_quantity: int = 1
    value: str | None = None
    assembly_difficulty: str | None = None
    assembly_reason: str | None = None
    assembly_basis: str = (
        "Assembly difficulty is an Ohmni estimate from the package shape, not a manufacturer figure."
    )
    orientation_sensitive: bool = False
    price_knowledge: str = "UNKNOWN"
    unit_price: str | None = None
    evidence_status: str | None = None


class StageCard(BaseModel):
    stage: str
    label: str
    detail: str
    status: str
    outcome: str


class CheckRule(BaseModel):
    rule_id: str
    title: str
    outcome: str
    findings: int
    limitations: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)


class CheckGroup(BaseModel):
    group: str
    family: CheckFamily
    label: str
    question: str
    status: str
    rule_count: int
    rules: list[CheckRule]


class CheckSection(BaseModel):
    """One family of checks, so unrelated verdicts never sit side by side."""

    family: CheckFamily
    label: str
    summary: str
    groups: list[CheckGroup]


class RepairStep(BaseModel):
    key: str
    headline: str
    body: str
    component_refs: list[str] = Field(default_factory=list)
    net_names: list[str] = Field(default_factory=list)


class RepairReplay(BaseModel):
    """The caught problem, told as a sequence, with the rule kept underneath."""

    happened: bool
    headline: str
    #: One sentence a beginner can read without knowing any identifier.
    plain_summary: str | None = None
    part: Term | None = None
    from_net: Term | None = None
    to_net: Term | None = None
    operating_min_v: float | None = None
    component_ref: str | None = None
    part_id: str | None = None
    rule_id: str | None = None
    severity: str | None = None
    applied_v: float | None = None
    limit_v: float | None = None
    absolute_max_v: float | None = None
    repaired_v: float | None = None
    supported_range: str | None = None
    steps: list[RepairStep] = Field(default_factory=list)
    moved_pins: list[dict[str, str]] = Field(default_factory=list)
    evidence: list[dict[str, object]] = Field(default_factory=list)
    technical_description: str | None = None


class ConfidenceLine(BaseModel):
    label: str
    status: str
    detail: str


class Confidence(BaseModel):
    checked: list[ConfidenceLine]
    not_verified: list[ConfidenceLine]


class TourStep(BaseModel):
    """One narration step. Deterministic today; an LLM may rephrase it later.

    `facts` is the authoritative input a model would be given. It is emitted
    even though the current narration is deterministic, so the contract does
    not change when narration becomes generated.
    """

    step_id: str
    title: str
    narration: str
    focus: str
    system: SystemId | None = None
    flow_id: str | None = None
    component_refs: list[str] = Field(default_factory=list)
    net_names: list[str] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)


class GuidedTour(BaseModel):
    narration_source: str
    steps: list[TourStep]


class BringUpStep(BaseModel):
    """One bench check, with the value Ohmni actually derived for it.

    `prediction` is None when Ohmni computed nothing for that step. It is never
    filled with a plausible number: an unmeasured expectation presented as a
    prediction is exactly the failure the rest of this projection prevents.
    """

    action: str
    prediction: str | None = None
    basis: str | None = None
    rule_id: str | None = None


class ProductExperience(BaseModel):
    """Everything the product interface renders, and nothing it decides."""

    schema_version: int = 1
    headline: str
    subhead: str
    brief: Brief
    stages: list[StageCard]
    systems: list[FunctionalSystem]
    grouping: list[ComponentGrouping]
    flows: list[Flow]
    board: BoardGeometry
    schematic: SchematicGeometry
    components: list[ComponentCard]
    checks: list[CheckGroup]
    check_sections: list[CheckSection]
    bring_up: list[BringUpStep]
    repair: RepairReplay
    confidence: Confidence
    tour: GuidedTour


# --------------------------------------------------------------------------
# Brief
# --------------------------------------------------------------------------

_BRIEF_LABELS = {
    "description": "What you described",
    "max_input_voltage": "Power coming in",
    "target_logic_voltage": "Voltage the chips run at",
    "budget_usd": "Budget",
    "max_board_layers": "Board complexity",
    "hand_solderable": "You want to solder it yourself",
    "interface": "Connection type",
    "required_part_id": "Part you named",
    "assumption": "Ohmni assumed",
}


def _readable(field: str, value: str) -> str:
    """Present a requirement value in words. The value itself is unchanged."""
    if field == "hand_solderable":
        return "Yes" if value == "True" else "No"
    if field == "max_board_layers":
        return f"{value} layers"
    if field == "budget_usd":
        return f"about ${float(value):.0f}"
    if field == "interface":
        return {"i2c": "I2C (a two-wire sensor bus)",
                "spi": "SPI (a faster four-wire bus)",
                "uart": "UART (a serial connection for programming and logs)",
                "usb_power_sink": "USB-C, used only to take in power"}.get(value, value.upper())
    return value


def _grounding(statement, value: str) -> str:
    """Distinguish what the user wrote from what Ohmni read into it.

    The generation layer marks an interpreted field EXPLICIT with the whole
    request as its source text, which is correct provenance but becomes a false
    claim once an interface renders it as "taken straight from what you wrote".
    A value is only reported as quoted when it appears in the user's own words
    as a whole token: a naked substring search would find the 2 of "I2C" and
    call a two-layer board something the user asked for.
    """
    origin = statement.origin.value
    if origin != "explicit":
        return origin
    source = statement.source_text or ""
    if not source:
        return "interpreted"
    raw = str(statement.value).strip()
    if statement.field == "description":
        # This is the model's description of the request, not the request. It
        # is only the user's words if it actually matches them.
        return "quoted" if raw.casefold() == source.strip().casefold() else "interpreted"
    candidates = {raw.casefold(), value.strip().casefold()}
    try:
        number = float(raw.rstrip(" vV"))
    except ValueError:
        pass
    else:
        candidates.add(f"{number:g}")
    for candidate in candidates:
        if candidate and re.search(rf"(?<![\w.]){re.escape(candidate)}(?![\w.])",
                                   source, re.IGNORECASE):
            return "quoted"
    return "interpreted"


def build_brief(compiled, unsettled: list[str] | None = None) -> Brief:
    """Split the compiled requirements by where each statement came from.

    The three-way split is the existing ``RequirementOrigin`` enum, not a
    presentation invention: EXPLICIT is something the user wrote, ASSUMPTION is
    something Ohmni supplied and knows it supplied, and DEFAULT is a value
    nobody stated. Keeping DEFAULT separate is the point of the Agree stage --
    it is exactly the set a user should be asked to confirm.
    """
    asked, assumed, unclear = [], [], []

    def line(statement):
        value = _readable(statement.field, statement.value)
        return BriefLine(
            field=statement.field,
            label=_BRIEF_LABELS.get(statement.field, statement.field.replace("_", " ")),
            value=value, origin=statement.origin.value,
            grounding=_grounding(statement, value),
            source_text=statement.source_text,
        )

    for statement in compiled.provenance:
        origin = statement.origin.value
        if origin == "explicit":
            asked.append(line(statement))
        elif origin == "assumption":
            assumed.append(line(statement))
        else:
            unclear.append(line(statement))
    # Anything Ohmni read into the request rather than lifting from it belongs
    # in the column the user is asked to check, not under "you asked for".
    interpreted = [item for item in asked if item.grounding == "interpreted"]
    asked = [item for item in asked if item.grounding != "interpreted"]
    unclear.extend(interpreted)
    for topic in unsettled or []:
        unclear.append(BriefLine(
            field="needs_confirmation", label="Ohmni could not settle this",
            value=topic, origin="needs_confirmation", grounding="unsettled",
        ))
    return Brief(
        project_name=compiled.requirements.project_name,
        request=compiled.requirements.description,
        asked_for=asked, assumed=assumed, needs_clarification=unclear,
    )


def unsettled_topics(report: VerificationReport) -> list[str]:
    """Findings whose honest outcome is 'a human must confirm this'.

    `PB-UART-001` is the archetype: header orientation genuinely cannot be
    settled from a netlist, and the rule says so instead of reporting a pass.
    """
    return sorted({
        finding.title for finding in report.findings
        if finding.severity.value == "info" and "confirm" in finding.description.lower()
    })


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def _board_geometry(board, routed, grouping: dict[str, ComponentGrouping],
                    circuit: CircuitIR, catalog) -> BoardGeometry:
    compilation = routed.compilation
    if compilation.artifact_fingerprint != routed.fingerprint:
        raise ValueError("board geometry projection does not match the compiled artifact")
    if compilation.constraints_hash != board.content_hash:
        raise ValueError("board geometry projection does not match the board constraints")
    if routed.routing_plan_fingerprint is None or (
        compilation.routing_plan_fingerprint != routed.routing_plan_fingerprint
    ):
        raise ValueError("board geometry projection does not match the routed copper")

    placements = {p.component_ref: p for p in board.placements}
    bindings = {b.component_ref: b for b in compilation.footprint_bindings}
    pads_by_ref: dict[str, dict[str, str | None]] = {}
    for binding in compilation.pad_bindings:
        pads_by_ref.setdefault(binding.component_ref, {})[binding.pad_number] = binding.net_name

    components: list[BoardComponent] = []
    for ref in sorted(bindings):
        binding = bindings[ref]
        placement = placements[ref]
        definition = footprint(binding.footprint_id)
        if definition is None:
            raise ValueError(f"no footprint geometry for {ref}")
        nets = pads_by_ref.get(ref, {})
        pads = [BoardPad(
            number=pad.number, net_name=nets.get(pad.number), x_mm=pad.x_mm, y_mm=pad.y_mm,
            width_mm=pad.width_mm, height_mm=pad.height_mm, kind=pad.kind, shape=pad.shape,
        ) for pad in definition.pads]
        components.append(BoardComponent(
            ref=ref, part_id=binding.part_id,
            name=component_term(circuit, catalog, ref), package=binding.package,
            footprint_id=binding.footprint_id,
            system=grouping[ref].system, x_mm=placement.x_mm, y_mm=placement.y_mm,
            rotation_deg=placement.rotation_deg, side=placement.side,
            width_mm=definition.width_mm, height_mm=definition.height_mm,
            placement_reason=placement.reason, pads=pads,
            net_names=sorted({name for name in nets.values() if name}),
        ))

    tracks = [BoardTrack(
        net_name=t.net_name, layer=t.layer, start_x_mm=t.start_x_mm, start_y_mm=t.start_y_mm,
        end_x_mm=t.end_x_mm, end_y_mm=t.end_y_mm, width_mm=t.width_mm,
    ) for t in compilation.emitted_tracks]
    vias = [BoardVia(
        net_name=v.net_name, x_mm=v.x_mm, y_mm=v.y_mm,
        diameter_mm=v.diameter_mm, drill_mm=v.drill_mm,
    ) for v in compilation.emitted_vias]

    if len(tracks) != compilation.copper_statistics.track_segment_count:
        raise ValueError("board geometry track count does not match the compiled artifact")
    if len(vias) != compilation.copper_statistics.via_count:
        raise ValueError("board geometry via count does not match the compiled artifact")

    return BoardGeometry(
        artifact_fingerprint=routed.fingerprint.digest,
        routing_plan_fingerprint=routed.routing_plan_fingerprint,
        constraints_hash=board.content_hash,
        width_mm=board.outline.width_mm, height_mm=board.outline.height_mm,
        layer_count=board.layer_count, layers=["F.Cu", "B.Cu"],
        components=components, tracks=tracks, vias=vias,
        net_names=sorted(net.name for net in circuit.nets),
    )


def _schematic_geometry(artifact, grouping: dict[str, ComponentGrouping],
                        circuit: CircuitIR, catalog) -> SchematicGeometry:
    compilation = artifact.compilation
    if compilation.source_artifact_fingerprint != artifact.fingerprint:
        raise ValueError("schematic geometry projection does not match the compiled artifact")
    symbols = [SchematicSymbol(
        ref=b.component_ref, part_id=b.part_id,
        name=component_term(circuit, catalog, b.component_ref),
        system=grouping[b.component_ref].system,
        x_mm=b.x_mm, y_mm=b.y_mm, width_mm=b.width_mm, height_mm=b.height_mm,
        pins=[SchematicPin(pin=p.circuit_pin, net_name=p.net_name, x_mm=p.x_mm, y_mm=p.y_mm)
              for p in b.pins],
    ) for b in sorted(compilation.symbol_bindings, key=lambda item: item.component_ref)]
    return SchematicGeometry(
        artifact_fingerprint=artifact.fingerprint.digest,
        connection_method=compilation.connection_method,
        symbols=symbols, net_names=sorted(compilation.net_mapping),
    )


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------

def _purpose(circuit: CircuitIR, catalog, ref: str, grouping: ComponentGrouping) -> str:
    """Explain observed connections without claiming they work or guessing intent."""
    instance = circuit.component(ref)
    spec = catalog.get(instance.part_id)
    category = spec.category if spec else None
    nets = [n for n in circuit.nets if ref in n.components()]
    kinds = {n.kind for n in nets}
    anchor = grouping.attached_to
    anchor_name = phrase(component_term(circuit, catalog, anchor)) if anchor else None
    value = instance.value.engineering() if instance.value else None

    def peers(net):
        for connection in net.connections:
            if connection.component == ref:
                continue
            other = circuit.component(connection.component)
            other_spec = catalog.get(other.part_id) if other else None
            pin = other_spec.pin(connection.pin) if other_spec else None
            if other_spec and pin:
                yield connection.component, other_spec, pin

    processors = {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}
    signal_nets = [net for net in nets if net.kind is NetKind.SIGNAL]

    if category in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}:
        return "The processor. It runs your program, reads the sensor and drives the outputs."
    if category is ComponentCategory.SENSOR:
        # A bus resistor participates electrically but does not receive readings.
        # Require both documented I2C roles to reach the same processor before
        # describing a complete data-and-clock connection.
        controllers_by_role = {PinRole.I2C_SDA: set(), PinRole.I2C_SCL: set()}
        nets_by_role = {role: set() for role in controllers_by_role}
        controllers = set()
        for net in signal_nets:
            connected = {other_ref for other_ref, other_spec, _ in peers(net)
                         if other_spec.category in processors}
            controllers.update(connected)
            for pin_number in net.pins_of(ref):
                pin = spec.pin(pin_number)
                for role, connected_controllers in controllers_by_role.items():
                    if pin and role in pin.roles:
                        connected_controllers.update(connected)
                        nets_by_role[role].add(net.name)
        bus_controllers = controllers_by_role[PinRole.I2C_SDA] & controllers_by_role[PinRole.I2C_SCL]
        distinct_bus_lines = (all(len(names) == 1 for names in nets_by_role.values())
                              and not nets_by_role[PinRole.I2C_SDA] & nets_by_role[PinRole.I2C_SCL])
        if Interface.I2C in instance.selected_interfaces and distinct_bus_lines and bus_controllers:
            readable = humanise_refs(circuit, catalog, sorted(bus_controllers))
            return (f"Takes measurements. Its I2C data and clock connections link it to the "
                    f"{readable}, which can request readings with a program.")
        if controllers:
            readable = humanise_refs(circuit, catalog, sorted(controllers))
            return f"Takes measurements. Its signal pins connect to the {readable}."
        return "Takes measurements. Its catalog describes how to read them."
    if category in {ComponentCategory.REGULATOR_LINEAR, ComponentCategory.REGULATOR_SWITCHING}:
        return "Produces a regulated supply for the components connected to its output."
    if category is ComponentCategory.CONNECTOR:
        if any(net.external_source is not None for net in nets):
            return "Connects the board to the external power source declared in this design."
        return "Connects the circuit to an external cable or accessory."
    if category is ComponentCategory.HEADER:
        roles_by_processor = {}
        for net in signal_nets:
            for other_ref, other_spec, pin in peers(net):
                if other_spec.category in processors:
                    roles_by_processor.setdefault(other_ref, set()).update(pin.roles)
        programming_roles = {PinRole.UART_TX, PinRole.UART_RX, PinRole.BOOT_STRAP}
        if any(programming_roles <= roles for roles in roles_by_processor.values()):
            return ("Brings the processor's serial and boot-control pins out to an external "
                    "programming adapter. The adapter is separate from the USB power cable.")
        return "Exposes circuit connections for an external cable or accessory."
    if category is ComponentCategory.LED:
        return "An indicator light. It lights when current flows through it in the forward direction."
    if category is ComponentCategory.CAPACITOR:
        if NetKind.POWER in kinds and NetKind.GROUND in kinds:
            target = f" next to the {anchor_name}" if anchor_name else ""
            return (f"Steadies the power supply{target}. It hands over quick bursts of current "
                    "faster than the regulator can react to.")
        return (f"A {value} capacitor. It stores electrical charge; its role depends on the circuit."
                if value else "Stores electrical charge; its role depends on the circuit.")
    if category is ComponentCategory.RESISTOR:
        two_terminals = (len(nets) == 2 and all(len(net.pins_of(ref)) == 1 for net in nets)
                         and len({pin for net in nets for pin in net.pins_of(ref)}) == 2)
        if two_terminals:
            # An exclusive two-pin link establishes a series connection. Merely
            # sharing a bus or supply with an LED does not.
            for net in signal_nets:
                if len(net.connections) != 2:
                    continue
                for _, other_spec, pin in peers(net):
                    if (other_spec.category is ComponentCategory.LED
                            and {PinRole.ANODE, PinRole.CATHODE} & set(pin.roles)):
                        return ("Sits in series with the indicator light to limit its current. "
                                "The resistance and supply voltage determine how much flows.")
                    if (other_spec.category is ComponentCategory.CONNECTOR
                            and PinRole.USB_CC in pin.roles and NetKind.GROUND in kinds):
                        return ("Pulls a USB-C configuration pin toward ground. This is the "
                                "sink-identification connection a USB-C source checks before "
                                "supplying power.")
            if NetKind.POWER in kinds and signal_nets:
                return ("A pull-up: biases this signal toward the supply through a resistor "
                        "when nothing is actively driving it.")
            if NetKind.GROUND in kinds and signal_nets:
                return ("A pull-down: biases this signal toward ground through a resistor "
                        "when nothing is actively driving it.")
        return f"A {value} resistor." if value else "A resistor."
    return f"Part of the {system_name(grouping.system).lower()}."


#: How a package shape translates into what a person has to do at the bench.
_ASSEMBLY_REASONS: dict[str, str] = {
    "easy": "Through-hole or large pads. Straightforward with a soldering iron.",
    "moderate": "Small surface-mount package. Fiddly by hand but doable.",
    "reflow_recommended": "Pads sit under the part where an iron cannot reach. "
                          "You will want hot air or a reflow plate.",
    "unsupported_for_hand_assembly": "Pads are entirely under the part. Not realistic to "
                                     "solder by hand.",
    "unknown": "Ohmni does not recognise this package shape well enough to judge.",
}


def _components(circuit: CircuitIR, catalog, grouping: dict[str, ComponentGrouping],
                bom, costs, assembly) -> list[ComponentCard]:
    risk_by_ref = {ref: risk for risk in assembly.risks for ref in risk.references}
    cost_by_key = {line.identity.key: line for line in costs.lines}
    bom_by_ref = {ref: line for line in bom.lines for ref in line.references}
    cards: list[ComponentCard] = []
    for instance in sorted(circuit.components, key=lambda item: item.ref):
        ref = instance.ref
        spec = catalog.get(instance.part_id)
        bom_line = bom_by_ref.get(ref)
        cost = cost_by_key.get(bom_line.identity.key) if bom_line else None
        risk = risk_by_ref.get(ref)
        difficulty = risk.difficulty.value if risk else None
        cards.append(ComponentCard(
            ref=ref, part_id=instance.part_id,
            name=component_term(circuit, catalog, ref),
            display_name=spec.display_name if spec else instance.part_id,
            package=instance.package or "unknown",
            system=grouping[ref].system,
            purpose=_purpose(circuit, catalog, ref, grouping[ref]),
            grouping_basis=grouping[ref].basis,
            # One board carries one of this reference designator. The BOM line
            # quantity counts every identical part and belongs beside the line,
            # not on each component that happens to share it.
            quantity_on_board=1,
            line_quantity=bom_line.quantity_per_board if bom_line else 1,
            value=instance.value.engineering() if instance.value else None,
            assembly_difficulty=difficulty,
            assembly_reason=_ASSEMBLY_REASONS.get(difficulty or "", None),
            orientation_sensitive=bool(risk and risk.orientation_sensitive),
            price_knowledge=cost.knowledge.value.upper() if cost else "UNKNOWN",
            unit_price=str(cost.unit_price) if cost and cost.unit_price is not None else None,
            evidence_status=bom_line.evidence_status if bom_line else None,
        ))
    return cards


# --------------------------------------------------------------------------
# Stages, checks, confidence
# --------------------------------------------------------------------------

def _stages(design, routed, drc, manufacturing, package, route_report) -> list[StageCard]:
    """Terminal per-stage outcomes for a finished run.

    Every card is a settled result. Nothing here can read as still running,
    because a completed project has no running stage.
    """
    first = design.semantic_attempts[0]
    last = design.semantic_attempts[-1]
    blocking = [f for f in first.findings if f.severity.value in {"critical", "error"}]
    erc = design.erc
    copper = routed.compilation.copper_statistics
    physical = routed.compilation.physical_verification
    brief_detail = (f"{len(design.requirements.provenance)} statements, "
                    f"{len(design.requirements.requirements.assumptions)} assumption(s) recorded")
    design_detail = (f"{len(design.final_circuit.components)} parts, joined by "
                     f"{len(design.final_circuit.nets)} electrical connections")
    repair_detail = (
        f"{sum(len(r.patch.operations) for r in design.repairs)} change(s) applied, then re-checked"
        if design.repairs else "nothing needed fixing")
    routing_detail = (f"{copper.track_segment_count} copper paths drawn, "
                      f"{copper.via_count} crossing between the two sides")
    manufacture_detail = (
        f"{len(drc.findings)} layout problems and "
        f"{'no missing connections' if not drc.unconnected_items else str(len(drc.unconnected_items)) + ' missing connections'}"
        f"; {len(package.files)} manufacturing files ready")
    outcomes = {
        "brief": ("DONE", brief_detail),
        "design": ("DONE", design_detail),
        "check": ("FOUND_PROBLEM" if blocking else "CLEAN",
                  f"{len(blocking)} blocking problem(s) in the first proposal"),
        "repair": ("FIXED" if design.repairs else "NOT_NEEDED", repair_detail),
        "schematic": (erc.status.value.upper() if erc else "UNSUPPORTED",
                      f"KiCad's schematic checker raised {len(erc.findings)} notes"
                      if erc else "KiCad was not available, so nothing was checked"),
        "placement": ("DONE" if physical.passed else "PROBLEM",
                      f"{len(physical.findings)} measurements taken"),
        "routing": ("DONE" if route_report.passed else "PROBLEM", routing_detail),
        "manufacture": ("PASS" if manufacturing.passed else "PROBLEM", manufacture_detail),
    }
    del last
    return [StageCard(stage=key, label=label, detail=detail,
                      status=outcomes[key][0], outcome=outcomes[key][1])
            for key, label, detail in STAGE_SEQUENCE]


#: The verifier owns which categories speak for which subsystem. Reusing its map
#: means a renamed subsystem key cannot silently degrade a VERIFIED status to
#: UNKNOWN on the way to the screen.
_SUBSYSTEM_OF_CATEGORY: dict[RuleCategory, str] = {
    category: name
    for name, categories in SUBSYSTEM_CATEGORIES.items()
    for category in categories
}


def _checks(report: VerificationReport, erc, routed, drc, manufacturing) -> list[CheckGroup]:
    groups: list[CheckGroup] = []
    for category in RuleCategory:
        results = [r for r in report.results if r.category is category]
        label, question = CHECK_GROUPS[category]
        subsystem = _SUBSYSTEM_OF_CATEGORY.get(category)
        if subsystem is None:
            raise ValueError(f"no subsystem owns rule category {category.value}")
        status = report.subsystem_status.get(subsystem)
        if status is None:
            # The verifier owns this map. A category it does not roll up is a
            # drift bug, and must not become a quietly missing row.
            raise ValueError(f"verifier reported no status for subsystem {subsystem!r}")
        family = CheckFamily.OHMNI if results else CheckFamily.NOT_ANALYSED
        groups.append(CheckGroup(
            group=category.value, family=family, label=label, question=question,
            status=status.value.upper(), rule_count=len(results),
            rules=[CheckRule(
                rule_id=r.rule_id, title=r.title, outcome=r.outcome.value.upper(),
                findings=len(r.findings), limitations=r.limitations, missing_data=r.missing_data,
            ) for r in sorted(results, key=lambda item: item.rule_id)],
        ))
    physical = routed.compilation.physical_verification
    groups.append(CheckGroup(
        group="layout", family=CheckFamily.OHMNI, label="The physical layout",
        question="Do the parts fit, stay inside the board, and sit where they need to?",
        status="PASS" if physical.passed else "FAIL", rule_count=len(physical.findings),
        rules=[CheckRule(rule_id=f.rule_id, title=f.description,
                         outcome=f.status.value.upper(),
                         findings=0 if f.status.value == "pass" else 1)
               for f in physical.findings],
    ))
    groups.append(CheckGroup(
        group="manufacturing", family=CheckFamily.OHMNI, label="Can it be made?",
        question="Does the board fit what a fabricator can actually produce?",
        status="PASS" if manufacturing.passed else "FAIL",
        rule_count=len(manufacturing.findings),
        rules=[CheckRule(rule_id=f.rule_id, title=f"{f.subject}: {f.detail}",
                         outcome=f.status.value.upper(),
                         findings=0 if f.status.value == "pass" else 1)
               for f in manufacturing.findings],
    ))
    if erc is not None:
        groups.append(CheckGroup(
            group="kicad_erc", family=CheckFamily.EXTERNAL,
            label="Schematic connection check",
            question="Does KiCad agree the schematic is wired sensibly?",
            status=erc.status.value.upper(), rule_count=1,
            rules=[CheckRule(rule_id="KICAD-ERC", title="KiCad electrical rule check (ERC)",
                             outcome=erc.status.value.upper(), findings=len(erc.findings))],
        ))
    groups.append(CheckGroup(
        group="kicad_drc", family=CheckFamily.EXTERNAL, label="PCB layout check",
        question="Would this board actually be manufacturable copper?",
        status=drc.status.value.upper(), rule_count=1,
        rules=[CheckRule(rule_id="KICAD-DRC", title="KiCad design rule check (DRC)",
                         outcome=drc.status.value.upper(),
                         findings=len(drc.findings) + len(drc.unconnected_items))],
    ))
    return groups


def _check_sections(groups: list[CheckGroup]) -> list[CheckSection]:
    """Group the checks by who ran them, so verdicts cannot read as conflicting."""
    sections: list[CheckSection] = []
    for family in (CheckFamily.OHMNI, CheckFamily.EXTERNAL, CheckFamily.NOT_ANALYSED):
        members = [group for group in groups if group.family is family]
        if not members:
            continue
        label, summary = CHECK_FAMILY_LABELS[family]
        sections.append(CheckSection(family=family, label=label, summary=summary, groups=members))
    return sections


def _confidence(report: VerificationReport, erc, routed, route_report, drc,
                manufacturing, costs, assembly) -> Confidence:
    checked = [
        ConfidenceLine(label="The electrical design", status="CHECKED",
                       detail=f"{len(report.results)} deterministic rules ran; "
                              f"{report.coverage:.0%} of the applicable ones reached a verdict"),
        ConfidenceLine(label="The schematic", status=erc.status.value.upper() if erc else "UNSUPPORTED",
                       detail=f"KiCad's own checker raised {len(erc.findings)} notes on it"
                              if erc else "KiCad was not available, so nothing was checked"),
        ConfidenceLine(label="The layout", status="CHECKED" if routed.compilation.physical_verification.passed else "PROBLEM",
                       detail=f"{len(routed.compilation.physical_verification.findings)} geometry measurements"),
        ConfidenceLine(label="The copper", status="CHECKED" if route_report.passed else "PROBLEM",
                       detail=f"every one of {routed.compilation.copper_statistics.track_segment_count} "
                              "emitted segments was re-checked by a separate verifier"),
        ConfidenceLine(label="Can it be made", status=drc.status.value.upper(),
                       detail=f"KiCad's layout checker found {len(drc.findings)} problems and "
                              f"{len(drc.unconnected_items)} missing connections, against the "
                              f"{manufacturing.profile.display_name}"),
    ]
    not_verified = [
        ConfidenceLine(label="Does it actually work?", status="NOT_YET_VERIFIED",
                       detail="No physical board has been built or measured. This is the one that matters most."),
        ConfidenceLine(label="Simulation", status="UNSUPPORTED",
                       detail="Ohmni does not simulate circuits. Nothing here was simulated."),
        ConfidenceLine(label="Heat, radio interference, signal integrity", status="UNSUPPORTED",
                       detail="Not analysed at all. Ohmni has no rules for these."),
        ConfidenceLine(label="What it costs", status="SYNTHETIC",
                       detail=f"Prices are a fixture, not live supplier data. "
                              f"{costs.pricing_coverage:.0%} of lines have any price at all."),
        ConfidenceLine(label="Assembly by hand", status="NEEDS_REVIEW"
                       if not assembly.hand_solder_requirement_satisfied else "PASS",
                       detail=(("The hand-soldering preference is not met by the selected packages. "
                                if not assembly.hand_solder_requirement_satisfied else "")
                               + ("; ".join(assembly.limitations) or "no recorded limitations"))),
        ConfidenceLine(label="The manufacturing profile", status="SYNTHETIC",
                       detail=f"{manufacturing.profile.display_name}. It is a stand-in, not a "
                              "real factory's published capabilities, and a person has to "
                              "review it before anything is ordered."),
    ]
    return Confidence(checked=checked, not_verified=not_verified)


# --------------------------------------------------------------------------
# Repair replay
# --------------------------------------------------------------------------

def _format_v(value: float | None) -> str:
    return "an unknown voltage" if value is None else f"{value:g} V"


def _repair(design, circuit: CircuitIR, catalog) -> RepairReplay:
    """Tell the caught problem as a story, with identifiers kept underneath.

    Every number here is read back from the report that produced it. The
    language around them is the only thing this function decides.
    """
    if not design.repairs:
        return RepairReplay(happened=False, headline="Ohmni found nothing that needed fixing.")
    first = design.semantic_attempts[0]
    repair = design.repairs[0]
    triggering = [f for f in first.findings if f.finding_id in set(repair.triggering_finding_ids)]
    worst = max(triggering, key=lambda f: (f.severity.value == "critical", f.rule_id), default=None)
    if worst is None:
        return RepairReplay(happened=False, headline="Ohmni found nothing that needed fixing.")

    operations = repair.patch.operations
    ref = worst.affected_components[0] if worst.affected_components else operations[0].component_ref
    instance = circuit.component(ref)
    spec = catalog.get(instance.part_id) if instance else None
    rail = next((r for r in (spec.supply_rails if spec else []) if r.evidence), None)
    applied = limit = minimum = absolute_max = None
    supported = None
    if rail is not None:
        supported = str(rail.operating)
        if rail.operating.worst_case_high is not None:
            limit = rail.operating.worst_case_high.value
        if rail.operating.worst_case_low is not None:
            minimum = rail.operating.worst_case_low.value
        absolute_max = rail.absolute_max.value if rail.absolute_max else None
    for evidence in worst.evidence:
        if evidence.kind.value == "calculation" and evidence.quantity is not None:
            applied = evidence.quantity.value

    from_net, to_net = operations[0].from_net, operations[0].to_net
    part = component_term(circuit, catalog, ref)
    from_term = net_term(circuit, catalog, from_net)
    to_term = net_term(circuit, catalog, to_net)
    repaired = net_driver_voltage(circuit, catalog, to_net)
    thing = phrase(part)

    plain = (f"Your {thing} was going to get too much voltage."
             if applied is not None and limit is not None and applied > limit
             else f"Your {thing} was connected to the wrong supply.")

    problem = (f"The {thing} was wired to {phrase(from_term)}. Its manufacturer only "
               f"specifies it to work up to {_format_v(limit)}."
               if limit is not None else worst.description)
    fix = (f"It moved the {thing}'s power over to {phrase(to_term)}"
           + (f", which sits at {_format_v(repaired)}." if repaired is not None else ".")
           + " Nothing else about the design was touched.")

    steps = [
        RepairStep(key="problem", headline="What was wrong", body=problem,
                   component_refs=[ref], net_names=[from_net]),
        RepairStep(key="why", headline="Why that matters",
                   body=("Too much voltage does not just make a part behave badly. Past the "
                         "manufacturer's limit it can be damaged for good. That is why Ohmni "
                         "refuses to hand over a design in this state."),
                   component_refs=[ref]),
        RepairStep(key="fix", headline="What Ohmni changed", body=fix,
                   component_refs=[ref], net_names=[from_net, to_net]),
        RepairStep(key="recheck", headline="Then it checked again",
                   body=("Every check ran again from the beginning on the changed design. The "
                         "problem is gone and nothing new appeared. Ohmni does not assume a fix "
                         "worked."),
                   component_refs=[ref], net_names=[to_net]),
    ]
    return RepairReplay(
        happened=True,
        headline=f"Ohmni caught {len(triggering)} problem(s) before anything was drawn.",
        plain_summary=plain,
        part=part, from_net=from_term, to_net=to_term,
        component_ref=ref, part_id=instance.part_id if instance else None,
        rule_id=worst.rule_id, severity=worst.severity.value.upper(),
        applied_v=applied, limit_v=limit, operating_min_v=minimum,
        absolute_max_v=absolute_max, repaired_v=repaired, supported_range=supported,
        steps=steps,
        moved_pins=[{"component": op.component_ref, "pin": op.pin,
                     "from_net": op.from_net, "to_net": op.to_net} for op in operations],
        evidence=[{
            "label": e.label, "kind": e.kind.value, "status": e.status.value.upper(),
            "source": e.source_id, "page": e.page, "snippet": e.snippet,
            "value": e.text_value or (e.quantity.engineering() if e.quantity else None),
            "detail": e.detail,
        } for e in worst.evidence],
        technical_description=worst.description,
    )


#: A prediction must look like a measurement. The rule notes it is recovered
#: from are prose written for a human reader, under no format contract, so a
#: token that is not a quantity is discarded rather than shown as one.
_QUANTITY = re.compile(r"^-?\d+(?:\.\d+)?\s*[a-zA-ZΩμµ°]+$")


def _quantity_from_note(note: str) -> str | None:
    """Recover a measured quantity from a rule's prose note, or nothing.

    The verifier owns these strings and does not promise a shape. Anything that
    does not read as a number with a unit is dropped: a wrong number presented
    as a prediction is worse than no prediction at all.
    """
    if "=" not in note:
        return None
    candidate = note.split("=")[-1].split(",")[0].strip()
    return candidate if _QUANTITY.match(candidate) else None


def _bring_up(design, circuit: CircuitIR, catalog, repair: RepairReplay) -> list[BringUpStep]:
    """Bench checks, each carrying the value Ohmni actually derived for it.

    A step whose value Ohmni did not compute carries no prediction, and a step
    for hardware this board does not have is not offered at all. Filling either
    in would be inventing an engineering claim on the last screen a user reads
    before touching hardware.
    """
    report = design.semantic_attempts[-1]
    results = {result.rule_id: result for result in report.results}

    def note_of(rule_id: str) -> str | None:
        """The first note of a rule that actually ran.

        A NOT_APPLICABLE result carries its reason as the first note, so a
        truthiness check alone would treat "circuit has no LEDs" as a finding.
        """
        result = results.get(rule_id)
        if result is None or result.outcome is RuleOutcome.NOT_APPLICABLE:
            return None
        return result.notes[0] if result.notes else None

    steps: list[BringUpStep] = [
        BringUpStep(
            action="Inspect the assembly and check for an unintended short between power "
                   "and ground before applying power.",
            prediction="No unintended short between power and ground",
            basis="A supply short can damage components. Capacitors and other components "
                  "can affect an unpowered resistance reading.",
        ),
        BringUpStep(
            action="Power it from a current-limited bench supply.",
            prediction=None,
            basis="Ohmni has no start-up current figure for this board, so it will not "
                  "predict one. Start low and watch.",
        ),
    ]

    rail = repair.to_net
    if rail is None:
        for net in circuit.nets:
            if net.kind is NetKind.POWER and net.external_source is None:
                rail = net_term(circuit, catalog, net.name)
                break
    if rail is not None:
        volts = net_driver_voltage(circuit, catalog, rail.technical)
        steps.append(BringUpStep(
            action=f"Measure the {phrase(rail)}.",
            prediction=_format_v(volts) if volts is not None else None,
            basis=("Worked out from the datasheet of the part that produces it."
                   if volts is not None else None),
        ))

    # Offer the LED step only when there is exactly one indicator to measure.
    leds = [instance.ref for instance in circuit.components
            if (catalog.get(instance.part_id) and
                catalog.get(instance.part_id).category is ComponentCategory.LED)]
    if len(leds) == 1:
        led_note = note_of("PB-LED-001")
        steps.append(BringUpStep(
            action=f"Measure the current through the {phrase(component_term(circuit, catalog, leds[0]))}.",
            prediction=_quantity_from_note(led_note) if led_note else None,
            basis=led_note, rule_id="PB-LED-001",
        ))

    addresses = sorted(
        (instance.ref, instance.selected_i2c_address) for instance in circuit.components
        if instance.selected_i2c_address is not None
    )
    if addresses:
        listed = ", ".join(f"0x{value:02X}" for _, value in addresses)
        checked = results.get("PB-I2C-003")
        steps.append(BringUpStep(
            action="Scan the sensor bus for devices.",
            prediction=listed,
            basis=("The address each part is set to. Ohmni cross-checked it against how the "
                   "address pin is wired." if checked and checked.outcome is RuleOutcome.PASS
                   else "The address each part is declared to use."),
            rule_id="PB-I2C-003",
        ))
        steps.append(BringUpStep(
            action="Read the sensor and sanity-check the numbers.",
            prediction=None,
            basis="Ohmni cannot predict what your room is like.",
        ))

    for topic in unsettled_topics(report):
        steps.append(BringUpStep(
            action=f"Confirm this by hand: {topic}",
            prediction=None,
            basis="Ohmni could not settle this from the design alone and says so rather "
                  "than guessing.",
        ))
    return steps


# --------------------------------------------------------------------------
# Tour
# --------------------------------------------------------------------------

def _tour(brief: Brief, systems: list[FunctionalSystem], flows: list[Flow],
          repair: RepairReplay, board: BoardGeometry) -> GuidedTour:
    """A deterministic walkthrough assembled from authoritative facts.

    Every step carries the `facts` an LLM would be given if narration were
    generated. They are emitted even though the current narration is written
    here, so the contract does not change when narration becomes generated.
    """
    steps = [TourStep(
        step_id="overview", title="What you built",
        narration=(f"This is {brief.project_name}. It is a {board.width_mm:.0f} by "
                   f"{board.height_mm:.0f} millimetre board with "
                   f"{len(board.components)} parts on it. Everything on it is there because "
                   "something you asked for needed it."),
        focus="board",
        facts=[f"board {board.width_mm} x {board.height_mm} mm",
               f"{board.layer_count} layers",
               f"{len(board.components)} placed components",
               f"{len(board.tracks)} copper segments"],
    )]
    for flow in flows:
        if flow.flow_id == "ground":
            continue
        system = {"power": SystemId.POWER, "sensor_data": SystemId.SENSE,
                  "status_led": SystemId.IO, "programming": SystemId.IO}.get(flow.flow_id)
        steps.append(TourStep(
            step_id=f"flow-{flow.flow_id}", title=flow.label,
            narration=" ".join(stage.detail for stage in flow.stages[:2]),
            focus="flow", flow_id=flow.flow_id, system=system,
            component_refs=flow.component_refs, net_names=flow.net_names,
            facts=[stage.detail for stage in flow.stages],
        ))
    if repair.happened and repair.component_ref:
        part = phrase(repair.part) if repair.part else "a part"
        source = phrase(repair.from_net) if repair.from_net else "the wrong supply"
        target = phrase(repair.to_net) if repair.to_net else "the right supply"
        steps.append(TourStep(
            step_id="repair", title="The thing Ohmni caught",
            narration=(f"Before any of this was drawn, the {part} was wired to {source}. "
                       f"Its manufacturer only specifies it up to "
                       f"{_format_v(repair.limit_v)}. Ohmni moved it to {target} and re-ran "
                       "every check."),
            focus="repair", component_refs=[repair.component_ref],
            net_names=[n.technical for n in (repair.from_net, repair.to_net) if n],
            facts=[f"rule {repair.rule_id}", f"severity {repair.severity}",
                   f"specified range {repair.supported_range}"],
        ))
    if systems:
        steps.append(TourStep(
            step_id="systems", title=f"It is really {len(systems)} smaller systems",
            narration=("A board looks like one object. It is really a few groups of parts that "
                       "each do one job: "
                       + "; ".join(f"{s.label.lower()}" for s in systems) + "."),
            focus="systems",
            component_refs=[ref for s in systems for ref in s.component_refs],
            facts=[f"{s.label} = {', '.join(s.component_refs)}" for s in systems],
        ))
    steps.append(TourStep(
        step_id="limits", title="What has not been tested",
        narration=("Everything you just saw was checked by rules and by KiCad. None of it has "
                   "been built. No Ohmni board has ever been made and measured, so treat this "
                   "as a carefully checked design, not a proven one."),
        focus="confidence",
        facts=["bench verification NOT_YET_VERIFIED", "simulation UNSUPPORTED",
               "thermal, EMC, RF UNSUPPORTED", "pricing SYNTHETIC"],
    ))
    return GuidedTour(
        narration_source="deterministic_projection_not_a_language_model", steps=steps,
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def project_product_experience(*, design, catalog, board, routed, route_report, drc,
                               manufacturing, bom, costs, assembly, package) -> ProductExperience:
    """Assemble the product projection from already-verified subsystem reports."""
    circuit = design.final_circuit
    placements = {p.component_ref: (p.x_mm, p.y_mm) for p in board.placements}
    groupings = group_components(circuit, catalog, placements)
    by_ref = {g.component_ref: g for g in groupings}
    systems = build_systems(groupings)
    flows = build_flows(circuit, catalog, groupings)
    geometry = _board_geometry(board, routed, by_ref, circuit, catalog)
    brief = build_brief(design.requirements,
                        unsettled_topics(design.semantic_attempts[-1]))
    repair = _repair(design, circuit, catalog)
    last = design.semantic_attempts[-1]
    checks = _checks(last, design.erc, routed, drc, manufacturing)
    return ProductExperience(
        headline=brief.project_name,
        subhead=(f"{len(geometry.components)} parts on a {geometry.width_mm:.0f} x "
                 f"{geometry.height_mm:.0f} mm board, checked and ready for you to review"),
        brief=brief,
        stages=_stages(design, routed, drc, manufacturing, package, route_report),
        systems=systems, grouping=groupings, flows=flows,
        board=geometry,
        schematic=_schematic_geometry(design.artifact, by_ref, circuit, catalog),
        components=_components(circuit, catalog, by_ref, bom, costs, assembly),
        checks=checks, check_sections=_check_sections(checks),
        bring_up=_bring_up(design, circuit, catalog, repair),
        repair=repair,
        confidence=_confidence(last, design.erc, routed, route_report, drc, manufacturing,
                               costs, assembly),
        tour=_tour(brief, systems, flows, repair, geometry),
    )
