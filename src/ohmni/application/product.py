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

from pydantic import BaseModel, Field

from ..domain.circuit import CircuitIR, NetKind
from ..domain.component import ComponentCategory
from ..domain.verification import RuleCategory, VerificationReport
from ..physical.footprints import footprint
from ..verifier.engine import SUBSYSTEM_CATEGORIES
from .systems import (
    ComponentGrouping,
    Flow,
    FunctionalSystem,
    SystemId,
    build_flows,
    build_systems,
    group_components,
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
#: "The power supply" rather than "electrical".
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
    RuleCategory.THERMAL: ("Heat", "Not analysed."),
    RuleCategory.EDA: ("KiCad's own opinion", "An independent second check by different software."),
    RuleCategory.SIMULATION: ("Simulation", "Not implemented."),
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
    display_name: str
    package: str
    system: SystemId
    purpose: str
    grouping_basis: str
    quantity_on_board: int
    value: str | None = None
    assembly_difficulty: str | None = None
    assembly_detail: str | None = None
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
    label: str
    question: str
    status: str
    rule_count: int
    rules: list[CheckRule]


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
    component_ref: str | None = None
    part_id: str | None = None
    rule_id: str | None = None
    severity: str | None = None
    applied_v: float | None = None
    limit_v: float | None = None
    absolute_max_v: float | None = None
    repaired_v: float | None = None
    supported_range: str | None = None
    from_net: str | None = None
    to_net: str | None = None
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
        return BriefLine(
            field=statement.field,
            label=_BRIEF_LABELS.get(statement.field, statement.field.replace("_", " ")),
            value=_readable(statement.field, statement.value), origin=statement.origin.value,
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
    for topic in unsettled or []:
        unclear.append(BriefLine(
            field="needs_confirmation", label="Ohmni could not settle this",
            value=topic, origin="needs_confirmation",
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
                    circuit: CircuitIR) -> BoardGeometry:
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
            ref=ref, part_id=binding.part_id, package=binding.package,
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


def _schematic_geometry(artifact, grouping: dict[str, ComponentGrouping]) -> SchematicGeometry:
    compilation = artifact.compilation
    if compilation.source_artifact_fingerprint != artifact.fingerprint:
        raise ValueError("schematic geometry projection does not match the compiled artifact")
    symbols = [SchematicSymbol(
        ref=b.component_ref, part_id=b.part_id, system=grouping[b.component_ref].system,
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
    """Plain language derived from part category and this board's topology."""
    instance = circuit.component(ref)
    spec = catalog.get(instance.part_id)
    category = spec.category if spec else None
    nets = [n for n in circuit.nets if ref in n.components()]
    net_names = {n.name for n in nets}
    kinds = {n.kind for n in nets}
    anchor = grouping.attached_to
    value = instance.value.engineering() if instance.value else None

    if category in {ComponentCategory.MCU, ComponentCategory.MCU_MODULE}:
        return "The processor. It runs your program, reads the sensor and drives the outputs."
    if category is ComponentCategory.SENSOR:
        return f"The sensor. It performs the measurement and reports it over {', '.join(sorted(net_names & {'SDA', 'SCL'})) or 'its data pins'}."
    if category in {ComponentCategory.REGULATOR_LINEAR, ComponentCategory.REGULATOR_SWITCHING}:
        return "The voltage regulator. It converts the incoming supply into the steady lower voltage everything else needs."
    if category is ComponentCategory.CONNECTOR:
        return "Where power comes into the board."
    if category is ComponentCategory.HEADER:
        return "The header you connect to in order to load code onto the board."
    if category is ComponentCategory.LED:
        return "The indicator light."
    if category is ComponentCategory.CAPACITOR:
        if NetKind.POWER in kinds and NetKind.GROUND in kinds:
            target = f" for {anchor}" if anchor else ""
            return (f"A {value} capacitor sitting across the supply{target}. It supplies the "
                    "quick bursts of current a chip needs faster than the regulator can react.")
        return f"A {value} capacitor on {', '.join(sorted(net_names))}."
    if category is ComponentCategory.RESISTOR:
        signal_nets = sorted(n.name for n in nets if n.kind is NetKind.SIGNAL)
        if NetKind.POWER in kinds and signal_nets:
            return (f"A {value} resistor holding {', '.join(signal_nets)} up towards the supply "
                    "when nothing else is driving it.")
        if signal_nets:
            return f"A {value} resistor in series on {', '.join(signal_nets)}, limiting how much current can flow."
        return f"A {value} resistor on {', '.join(sorted(net_names))}."
    hint = _PASSIVE_ROLE_HINTS.get(category, "component")
    return f"A {hint} on {', '.join(sorted(net_names))}."


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
        cards.append(ComponentCard(
            ref=ref, part_id=instance.part_id,
            display_name=spec.display_name if spec else instance.part_id,
            package=instance.package or "unknown",
            system=grouping[ref].system,
            purpose=_purpose(circuit, catalog, ref, grouping[ref]),
            grouping_basis=grouping[ref].basis,
            quantity_on_board=bom_line.quantity_per_board if bom_line else 1,
            value=instance.value.engineering() if instance.value else None,
            assembly_difficulty=risk.difficulty.value if risk else None,
            assembly_detail=risk.detail if risk else None,
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
    routing_detail = (f"{copper.track_segment_count} copper segments, "
                      f"{copper.via_count} layer crossings")
    manufacture_detail = (f"{len(drc.findings)} KiCad DRC violation(s), "
                          f"{len(drc.unconnected_items)} unrouted, "
                          f"{len(package.files)} fabrication files")
    outcomes = {
        "brief": ("DONE", brief_detail),
        "design": ("DONE", design_detail),
        "check": ("FOUND_PROBLEM" if blocking else "CLEAN",
                  f"{len(blocking)} blocking problem(s) in the first proposal"),
        "repair": ("FIXED" if design.repairs else "NOT_NEEDED", repair_detail),
        "schematic": (erc.status.value.upper() if erc else "UNSUPPORTED",
                      f"{len(erc.findings)} KiCad ERC finding(s)" if erc else "KiCad did not run"),
        "placement": ("DONE" if physical.passed else "PROBLEM",
                      f"{len(physical.findings)} layout measurement(s)"),
        "routing": ("DONE" if route_report.passed else "PROBLEM", routing_detail),
        "manufacture": (drc.status.value.upper(), manufacture_detail),
    }
    del last, manufacturing
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
        status = report.subsystem_status.get(subsystem) if subsystem else None
        if not results:
            # A subsystem with no rules is not silently dropped: UNSUPPORTED has
            # to stay visible, because an absent row reads as "fine".
            if status is not None:
                groups.append(CheckGroup(
                    group=category.value, label=label, question=question,
                    status=status.value.upper(), rule_count=0, rules=[],
                ))
            continue
        groups.append(CheckGroup(
            group=category.value, label=label, question=question,
            status=status.value.upper() if status else "UNKNOWN",
            rule_count=len(results),
            rules=[CheckRule(
                rule_id=r.rule_id, title=r.title, outcome=r.outcome.value.upper(),
                findings=len(r.findings), limitations=r.limitations, missing_data=r.missing_data,
            ) for r in sorted(results, key=lambda item: item.rule_id)],
        ))
    if erc is not None:
        groups.append(CheckGroup(
            group="kicad_erc", label="KiCad checked the schematic",
            question="Does different software, written by other people, agree?",
            status=erc.status.value.upper(), rule_count=1,
            rules=[CheckRule(rule_id="KICAD-ERC", title="KiCad electrical rule check",
                             outcome=erc.status.value.upper(), findings=len(erc.findings))],
        ))
    physical = routed.compilation.physical_verification
    groups.append(CheckGroup(
        group="layout", label="The physical layout",
        question="Do the parts fit, stay inside the board, and sit where they need to?",
        status="PASS" if physical.passed else "FAIL", rule_count=len(physical.findings),
        rules=[CheckRule(rule_id=f.rule_id, title=f.description,
                         outcome=f.status.value.upper(), findings=0 if f.status.value == "pass" else 1)
               for f in physical.findings],
    ))
    groups.append(CheckGroup(
        group="kicad_drc", label="KiCad checked the board",
        question="Would this board actually be manufacturable copper?",
        status=drc.status.value.upper(), rule_count=1,
        rules=[CheckRule(rule_id="KICAD-DRC", title="KiCad design rule check",
                         outcome=drc.status.value.upper(),
                         findings=len(drc.findings) + len(drc.unconnected_items))],
    ))
    groups.append(CheckGroup(
        group="manufacturing", label="Can it be made?",
        question="Does the board fit what a fabricator can actually produce?",
        status="PASS" if manufacturing.passed else "FAIL",
        rule_count=len(manufacturing.findings),
        rules=[CheckRule(rule_id=f.rule_id, title=f"{f.subject}: {f.detail}",
                         outcome=f.status.value.upper(),
                         findings=0 if f.status.value == "pass" else 1)
               for f in manufacturing.findings],
    ))
    return groups


def _confidence(report: VerificationReport, erc, routed, route_report, drc,
                manufacturing, costs, assembly) -> Confidence:
    checked = [
        ConfidenceLine(label="The electrical design", status="CHECKED",
                       detail=f"{len(report.results)} deterministic rules ran; "
                              f"{report.coverage:.0%} of the applicable ones reached a verdict"),
        ConfidenceLine(label="The schematic", status=erc.status.value.upper() if erc else "UNSUPPORTED",
                       detail=f"KiCad's own checker reported {len(erc.findings)} findings"
                              if erc else "KiCad was not available, so nothing was checked"),
        ConfidenceLine(label="The layout", status="CHECKED" if routed.compilation.physical_verification.passed else "PROBLEM",
                       detail=f"{len(routed.compilation.physical_verification.findings)} geometry measurements"),
        ConfidenceLine(label="The copper", status="CHECKED" if route_report.passed else "PROBLEM",
                       detail=f"every one of {routed.compilation.copper_statistics.track_segment_count} "
                              "emitted segments was re-checked by a separate verifier"),
        ConfidenceLine(label="Manufacturability", status=drc.status.value.upper(),
                       detail=f"KiCad DRC: {len(drc.findings)} violations, "
                              f"{len(drc.unconnected_items)} unrouted; profile "
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
        ConfidenceLine(label="Assembly by hand", status="PASS_WITH_WARNINGS"
                       if not assembly.hand_solder_requirement_satisfied else "PASS",
                       detail="; ".join(assembly.limitations) or "no recorded limitations"),
        ConfidenceLine(label="The manufacturing profile", status="SYNTHETIC",
                       detail=f"{manufacturing.profile.display_name}, provenance "
                              f"{manufacturing.profile.provenance.value}; a human must review it"),
    ]
    return Confidence(checked=checked, not_verified=not_verified)


# --------------------------------------------------------------------------
# Repair replay
# --------------------------------------------------------------------------

def _net_driver_voltage(circuit: CircuitIR, catalog, net_name: str) -> float | None:
    """The voltage a net sits at, taken from whatever drives it.

    Mirrors the verifier's own derivation order rather than reading a label: a
    declared external source, else a regulator's datasheet output voltage.
    """
    net = circuit.net(net_name)
    if net is None:
        return None
    if net.external_source is not None:
        nominal = net.external_source.voltage.nominal
        return nominal.value if nominal else None
    for pin in net.connections:
        instance = circuit.component(pin.component)
        spec = catalog.get(instance.part_id) if instance else None
        if spec is None or spec.regulator is None:
            continue
        pin_spec = spec.pin(pin.pin)
        if pin_spec is not None and pin_spec.electrical_type.value == "power_out":
            nominal = spec.regulator.output_voltage.nominal
            return nominal.value if nominal else None
    return None


def _repair(design, circuit: CircuitIR, catalog) -> RepairReplay:
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
    applied = limit = absolute_max = repaired = None
    supported = None
    if rail is not None:
        supported = str(rail.operating)
        limit = rail.operating.worst_case_high.value if rail.operating.worst_case_high else None
        absolute_max = rail.absolute_max.value if rail.absolute_max else None
    # The voltage that was actually applied is a CALCULATION the rule already
    # made. It is read back, never re-derived here.
    for evidence in worst.evidence:
        if evidence.kind.value == "calculation" and evidence.quantity is not None:
            applied = evidence.quantity.value
    from_net = operations[0].from_net
    to_net = operations[0].to_net
    # What the repaired rail actually sits at comes from the datasheet of the
    # part that drives it. If nothing drives it, the mark is omitted rather
    # than guessed.
    repaired = _net_driver_voltage(circuit, catalog, to_net)

    steps = [
        RepairStep(
            key="problem", headline="Problem found",
            body=(f"{ref} ({instance.part_id if instance else 'the part'}) was connected to "
                  f"{from_net}. The manufacturer's datasheet says it is only specified to work "
                  f"between {supported}." if supported else worst.description),
            component_refs=[ref], net_names=[from_net],
        ),
        RepairStep(
            key="why", headline="Why that matters",
            body=("Above the maximum, the part is not merely out of specification - it can be "
                  "permanently damaged. That is a different kind of problem from 'it might not "
                  "work well', which is why Ohmni refuses to export a design in this state."),
            component_refs=[ref],
        ),
        RepairStep(
            key="fix", headline="What Ohmni changed",
            body=(f"It moved {len(operations)} supply connection(s) on {ref} from {from_net} to "
                  f"{to_net}. Nothing else about the design was touched - the change is one of a "
                  "small number of operations Ohmni is allowed to make."),
            component_refs=[ref], net_names=[from_net, to_net],
        ),
        RepairStep(
            key="recheck", headline="Then it checked again",
            body=("Every rule ran again from the beginning on the changed circuit. The problem is "
                  "gone, and nothing new appeared. Ohmni does not assume a fix worked."),
            component_refs=[ref], net_names=[to_net],
        ),
    ]
    return RepairReplay(
        happened=True,
        headline=f"Ohmni caught {len(triggering)} problem(s) before anything was drawn.",
        component_ref=ref, part_id=instance.part_id if instance else None,
        rule_id=worst.rule_id, severity=worst.severity.value.upper(),
        applied_v=applied, limit_v=limit, absolute_max_v=absolute_max,
        repaired_v=repaired, supported_range=supported,
        from_net=from_net, to_net=to_net, steps=steps,
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


# --------------------------------------------------------------------------
# Tour
# --------------------------------------------------------------------------

def _tour(brief: Brief, systems: list[FunctionalSystem], flows: list[Flow],
          repair: RepairReplay, board: BoardGeometry) -> GuidedTour:
    """A deterministic walkthrough assembled from authoritative facts.

    Every step carries the `facts` an LLM would be given if narration were
    generated. Today the narration is written from those same facts by this
    function, which is why `narration_source` says so plainly.
    """
    by_system = {s.system: s for s in systems}
    steps = [TourStep(
        step_id="overview", title="What you built",
        narration=(f"This is {brief.project_name}. It is a {board.width_mm:.0f} by "
                   f"{board.height_mm:.0f} millimetre, {board.layer_count}-layer board with "
                   f"{len(board.components)} parts on it. Everything on it exists because "
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
            narration=flow.summary + " " + flow.stages[0].detail,
            focus="flow", flow_id=flow.flow_id, system=system,
            component_refs=flow.component_refs, net_names=flow.net_names,
            facts=[stage.detail for stage in flow.stages],
        ))
    if repair.happened and repair.component_ref:
        steps.append(TourStep(
            step_id="repair", title="The thing Ohmni caught",
            narration=(f"Before any of this was drawn, {repair.component_ref} was wired to "
                       f"{repair.from_net}. Its datasheet supports {repair.supported_range}. "
                       f"Ohmni moved it to {repair.to_net} and re-ran every check."),
            focus="repair", component_refs=[repair.component_ref],
            net_names=[n for n in (repair.from_net, repair.to_net) if n],
            facts=[f"rule {repair.rule_id}", f"severity {repair.severity}",
                   f"supported range {repair.supported_range}"],
        ))
    compute = by_system.get(SystemId.COMPUTE)
    if compute:
        steps.append(TourStep(
            step_id="systems", title="It is really four smaller systems",
            narration=("A board looks like one object, but it is a few groups of parts that each "
                       "do one job. " + "; ".join(f"{s.label}: {', '.join(s.component_refs)}"
                                                  for s in systems) + "."),
            focus="systems",
            component_refs=[ref for s in systems for ref in s.component_refs],
            facts=[f"{s.label} = {', '.join(s.component_refs)}" for s in systems],
        ))
    steps.append(TourStep(
        step_id="limits", title="What has not been tested",
        narration=("Everything you just saw was checked by rules and by KiCad. None of it has "
                   "been built. No Ohmni board has ever been fabricated and measured, so treat "
                   "this as a carefully checked design, not a proven one."),
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
    geometry = _board_geometry(board, routed, by_ref, circuit)
    brief = build_brief(design.requirements,
                        unsettled_topics(design.semantic_attempts[-1]))
    repair = _repair(design, circuit, catalog)
    last = design.semantic_attempts[-1]
    return ProductExperience(
        headline=brief.project_name,
        subhead=(f"{len(geometry.components)} parts on a {geometry.width_mm:.0f} x "
                 f"{geometry.height_mm:.0f} mm board, checked and ready for you to review"),
        brief=brief,
        stages=_stages(design, routed, drc, manufacturing, package, route_report),
        systems=systems, grouping=groupings, flows=flows,
        board=geometry,
        schematic=_schematic_geometry(design.artifact, by_ref),
        components=_components(circuit, catalog, by_ref, bom, costs, assembly),
        checks=_checks(last, design.erc, routed, drc, manufacturing),
        repair=repair,
        confidence=_confidence(last, design.erc, routed, route_report, drc, manufacturing,
                               costs, assembly),
        tour=_tour(brief, systems, flows, repair, geometry),
    )
