"""A confirmed, bounded brief through the real engineering pipeline.

No scripted model responses or faulty proposals participate in personal projects.
The historical demo remains separately available for regression and explanation.
"""

from pathlib import Path

from ..adapters import telemetry
from ..catalog import default_catalog
from ..domain import EngineeringEvent, EngineeringNotebook, EventKind
from ..eda.kicad import KiCadCliAdapter, KiCadSchematicCompiler
from ..generation.models import (
    ArchitectureBlock,
    ArchitectureProposal,
    CompiledRequirements,
    DesignReport,
    GenerationState,
    RequirementOrigin,
    RequirementStatement,
)
from ..physical.placement import PlacementFailure, generate_placement
from ..synthesis import ArchetypeId, SpiPeripheralSlot, SynthesisBrief, synthesize
from ..synthesis.a4 import RECORDER_LIMITATIONS, recorder_brief
from ..synthesis.models import RefusalCode, SynthesisRefusal
from ..synthesis.peripherals import SUPPORTED_I2C_PARTS
from ..verifier import verify
from .demo import DemoPipeline, DemoReport, eda_check_outcomes, require_eda_check
from .product import Brief, build_brief


class ProjectRefusalError(ValueError):
    def __init__(self, refusal):
        self.refusal = refusal
        super().__init__(refusal.message)


FAMILY_COPY = {
    ArchetypeId.A4_USB_VOICE_RECORDER: ("Voice recorder", "Record mono WAV audio to removable microSD using an I2S microphone, record/stop button and status LED. Includes firmware and behavioral simulation."),
    ArchetypeId.A1_USB_I2C_SENSOR: ("Sensor station", "Read temperature and environmental sensors over a shared I2C bus."),
    ArchetypeId.A2_USB_GPIO_CONTROLLER: ("Sensor & controls", "Connect buttons, indicator LEDs and an optional environmental sensor to an ESP32."),
    ArchetypeId.A3_USB_SPI_PERIPHERAL: ("Memory & data", "Connect SPI EEPROM memory, with an optional environmental sensor."),
}


def project_options() -> dict:
    """Public editor choices for the implemented, bounded synthesis families.

    Counts describe compiler policy; sensor addresses come from catalog strap
    options the compiler can actually wire. Null requests automatic allocation.
    """
    catalog=default_catalog()
    defaults=[SynthesisBrief(hand_solderable_preferred=False),SynthesisBrief(archetype=ArchetypeId.A2_USB_GPIO_CONTROLLER,
        project_name="Button and light controller",description="USB-C powered ESP32 with buttons and indicator LEDs.",
        sensors=(),button_count=1,hand_solderable_preferred=False),SynthesisBrief(archetype=ArchetypeId.A3_USB_SPI_PERIPHERAL,
        project_name="SPI memory board",description="USB-C powered ESP32 with SPI EEPROM memory.",
        sensors=(),spi_devices=(SpiPeripheralSlot(part_id="25LC256-I/SN"),),hand_solderable_preferred=False)]
    defaults.append(recorder_brief())
    bounds=[((1,3),(0,1),(0,0),(0,0)),((0,1),(1,4),(1,2),(0,0)),((0,1),(0,1),(0,0),(1,2)),((0,0),(1,1),(1,1),(0,0))]
    families=[]
    for brief,limits in zip(defaults,bounds,strict=True):
        title,description=FAMILY_COPY[brief.archetype]
        families.append({"id":brief.archetype.value,"title":title,"description":description,
            **{field:{"min":limits[i][0],"max":limits[i][1]} for i,field in
               enumerate(("sensor_count","status_led_count","button_count","spi_count"))},
            "defaults":brief.model_dump(mode="json"),
            "sensor_slot_defaults":([{"part_id":"BME280","address":None},
                                     {"part_id":"TMP102AIDRLR","address":None},
                                     {"part_id":"TMP102AIDRLR","address":None}][:limits[0][1]])})
    return {"schema_version":1,"families":families,
        "sensors":[{"part_id":part_id,"label":catalog.require(part_id).display_name,
                    "description":catalog.require(part_id).description + (" Not available for generation: its 0.15 mm pad gaps conflict with the current 0.20 mm PCB clearance policy. Use BME280 for temperature sensing." if part_id == "TMP102AIDRLR" else ""),
                    "addresses":[option.address for option in catalog.require(part_id).i2c_addresses
                                 if option.strap_pin and option.strap_level in {"low","high"}]}
                   for part_id in sorted(SUPPORTED_I2C_PARTS)],
        "spi_devices":[{"part_id":"25LC256-I/SN","label":catalog.require("25LC256-I/SN").display_name,
                        "description":catalog.require("25LC256-I/SN").description}],
        "automatic_sensor_address":None,
        "board_dimensions":{"board_width_mm":{"min":40,"max":100,"default":100},
                            "board_height_mm":{"min":40,"max":70,"default":70}},
        "fixed":{"input_power":"usb_c_5v","input_voltage_v":{"min":4.75,"max":5.25},
                 "logic_voltage_v":3.3,"mcu_part_id":"ESP32-WROOM-32E","max_board_layers":2,
                 "safety_domains":[]},
        "limitations":["USB-C supplies power only; programming needs an external 3.3 V serial adapter.",
                       "Voice recorder includes firmware source and digital behavioral simulation; other families do not. Physical measurements are not included.",
                       "Catalog evidence and synthetic prices have explicit limitations; total build cost is unknown.",
                       "Address collisions and unsupported combinations are refused before a revision is saved."]}


def _prepare_project(brief: SynthesisBrief, catalog=None):
    """Resolve the exact same contract for preview and execution."""
    catalog=catalog or default_catalog()
    result = synthesize(brief,catalog)
    if not result.accepted:
        raise ProjectRefusalError(result.refusal)
    choices = [
        ("project_name", brief.project_name),
        ("description", brief.description),
        ("archetype", brief.archetype.value),
        ("input_power", brief.input_power.value),
        ("input_voltage_v", str(brief.input_voltage_v)),
        ("logic_voltage_v", str(brief.logic_voltage_v)),
        ("mcu_part_id", brief.mcu_part_id),
        ("sensor_count", str(len(brief.sensors))),
        ("status_led_count", str(brief.status_led_count)),
        ("button_count", str(brief.button_count)),
        ("spi_count", str(len(brief.spi_devices))),
        ("include_programming_header", str(brief.include_programming_header)),
        ("max_board_layers", str(brief.max_board_layers)),
        ("board_width_mm", str(brief.board_width_mm)),
        ("board_height_mm", str(brief.board_height_mm)),
        ("hand_solderable_preferred", str(brief.hand_solderable_preferred)),
        ("budget_usd", str(brief.budget_usd) if brief.budget_usd is not None else "Not specified"),
        ("safety_domains", ", ".join(domain.value for domain in brief.safety_domains) or "None requested"),
    ]
    assumptions = [
        "USB-C supplies power only; USB data and programming over USB-C are not provided.",
        "Firmware is not included. The board needs a program before its selected functions can operate.",
        f"Placement is generated on a {brief.board_width_mm:g} x {brief.board_height_mm:g} mm, two-layer board from circuit blocks, capacitor ownership, and geometric constraints.",
        "Placement policies and antenna exclusion require hardware review; generated geometry does not establish RF performance.",
    ]
    if brief.archetype is ArchetypeId.A4_USB_VOICE_RECORDER:
        choices.extend([("recorder_sample_rate_hz", str(brief.recorder_sample_rate_hz)),
                        ("recorder_max_seconds", str(brief.recorder_max_seconds))])
        assumptions = [a for a in assumptions if not a.startswith("Firmware is not included")]
        assumptions.extend(RECORDER_LIMITATIONS)
    for part in result.circuit.components:
        spec=catalog.require(part.part_id);package=spec.package(part.package)
        if package is not None and not package.hand_solderable:
            assumptions.append(f"{part.ref} ({spec.display_name}) uses {package.name}; catalog guidance does not classify this package as hand-solderable.")
    assumptions=list(dict.fromkeys([*result.requirements.assumptions,*result.circuit.design_assumptions,*assumptions]))
    assumptions.append(
        "Programming uses the six-pin header and an external 3.3 V serial adapter."
        if brief.include_programming_header else
        "The programming header is omitted. This revision has no supplied programming connector."
    )
    requirements = result.requirements.model_copy(update={
        "assumptions": assumptions,
    })
    provenance = [
        RequirementStatement(field=field, value=value,
                             origin=RequirementOrigin.EXPLICIT,
                             source_text=value)
        for field, value in choices
    ]
    sensors=[part for part in result.circuit.components if part.selected_i2c_address is not None]
    for index,(slot,part) in enumerate(zip(brief.sensors,sensors,strict=True)):
        provenance.extend([
            RequirementStatement(field=f"sensors.{index}.part_id",value=slot.part_id,
                                 origin=RequirementOrigin.EXPLICIT,source_text=slot.part_id),
            RequirementStatement(field=f"sensors.{index}.address",value=f"0x{part.selected_i2c_address:02X}",
                                 origin=RequirementOrigin.DEFAULT if slot.address is None else RequirementOrigin.EXPLICIT,
                                 source_text="Automatic address allocation requested" if slot.address is None else f"0x{slot.address:02X}"),
        ])
    provenance.extend(RequirementStatement(field=f"spi_devices.{index}.part_id",value=slot.part_id,
                                          origin=RequirementOrigin.EXPLICIT,source_text=slot.part_id)
                      for index,slot in enumerate(brief.spi_devices))
    provenance += [
        RequirementStatement(field="assumption", value=value, origin=RequirementOrigin.ASSUMPTION)
        for value in assumptions
    ]
    return result, CompiledRequirements(requirements=requirements, provenance=provenance)


def prepare_project(brief: SynthesisBrief, catalog=None):
    """Preserve the existing public preview contract without dropping internal intent."""
    result, requirements = _prepare_project(brief, catalog)
    return result.circuit, requirements


def preview_project(brief: SynthesisBrief) -> Brief:
    catalog = default_catalog()
    result, requirements = _prepare_project(brief, catalog)
    if any(slot.part_id == "TMP102AIDRLR" for slot in brief.sensors):
        raise ProjectRefusalError(SynthesisRefusal(
            code=RefusalCode.PACKAGE_CLEARANCE_UNAVAILABLE,
            message="The TMP102 package has 0.15 mm gaps between pads, below the current 0.20 mm PCB clearance policy. It cannot produce a released board with these rules. BME280 can measure temperature with the current rules, and also measures humidity and pressure. Would that sensor work for your requirements?",
            field_paths=("sensors",),
        ))
    try:
        generate_placement(result.circuit, result.placement_request, catalog)
    except PlacementFailure as error:
        suggestion = "Try a larger board or fewer parts."
        sizes = [(min(100.0, brief.board_width_mm + 10), brief.board_height_mm),
                 (brief.board_width_mm, min(70.0, brief.board_height_mm + 10)), (100.0, 70.0)]
        for width, height in sorted(set(sizes), key=lambda size: size[0] * size[1]):
            if (width, height) == (brief.board_width_mm, brief.board_height_mm):
                continue
            candidate = brief.model_copy(update={"board_width_mm": width, "board_height_mm": height})
            generated = synthesize(candidate, catalog)
            if not generated.accepted:
                continue
            try:
                generate_placement(generated.circuit, generated.placement_request, catalog)
            except PlacementFailure:
                continue
            suggestion = f"The placement check fits the same parts on {width:g} × {height:g} mm. Would that larger size work for you? Routing and final checks have not run."
            break
        raise ProjectRefusalError(SynthesisRefusal(
            code=RefusalCode.BOARD_PLACEMENT_UNAVAILABLE,
            message=(f"The current placement engine could not fit these parts on {brief.board_width_mm:g} × {brief.board_height_mm:g} mm. "
                     + suggestion + " This is an engine limit, not proof that an engineer could never design it."),
            field_paths=("board_width_mm", "board_height_mm"),
        )) from error
    return build_brief(requirements)


class ProjectPipeline(DemoPipeline):
    def __init__(self, progress=None, *, catalog=None):
        super().__init__(progress)
        self.catalog = catalog or default_catalog()

    def run(self, destination: Path, brief: SynthesisBrief) -> DemoReport:
        with telemetry.stage("synthesis"):
            result, requirements = _prepare_project(brief, self.catalog)
        circuit = result.circuit
        catalog = self.catalog
        destination = destination.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        self._progress("requirements", "Using your confirmed project choices", "PASS", 5,
                       "The saved brief determines this circuit and its optional parts.")
        with telemetry.stage("semantic_verification") as span:
            semantic = verify(circuit, catalog, requirements.requirements)
            outcome = "reject" if semantic.export_blocked else ("unknown" if semantic.coverage < 1 else "pass")
            span.outcome("ok", outcome)
            telemetry.record_verifier_attempt("confirmed_project", outcome)
        if semantic.export_blocked or semantic.coverage < 1:
            if semantic.export_blocked:
                telemetry.engineering_rejection()
            raise ValueError("The derived circuit did not pass complete semantic verification")
        self._progress("check", "Checked your parts and connections", "PASS", 15,
                       "Deterministic checks ran on this revision; no repair was needed.")
        with telemetry.stage("schematic"):
            artifact = KiCadSchematicCompiler(catalog).compile(circuit, destination / "golden.kicad_sch")
        with telemetry.stage("erc") as span:
            erc = KiCadCliAdapter().run_erc(artifact)
            (destination / "erc-report.json").write_text(erc.model_dump_json(indent=2),encoding="utf-8")
            span.outcome(*eda_check_outcomes(erc))
            require_eda_check(erc,"ERC")
        events = [
            EngineeringEvent(event_id=f"{brief.fingerprint[:12]}-brief",
                             kind=EventKind.USER_REQUEST_RECEIVED,
                             summary="Confirmed structured brief received", circuit_content_hash=circuit.content_hash),
            EngineeringEvent(event_id=f"{brief.fingerprint[:12]}-verified",
                             kind=EventKind.VERIFICATION_PASSED,
                             summary="Derived circuit checked without repairs", circuit_content_hash=circuit.content_hash),
            *artifact.events, *erc.events,
        ]
        architecture = ArchitectureProposal(blocks=[
            ArchitectureBlock(block_id=part.ref, purpose=catalog.require(part.part_id).category.value,
                              selected_part_id=part.part_id)
            for part in circuit.components
        ])
        design = DesignReport(
            state=GenerationState.COMPLETE, requirements=requirements, architecture=architecture,
            initial_circuit_hash=circuit.content_hash, final_circuit=circuit,
            semantic_attempts=[semantic], artifact=artifact, erc=erc,
            notebook=EngineeringNotebook(notebook_id=brief.fingerprint[:16],
                                         project_name=brief.project_name, events=events),
        )
        self._progress("schematic", "Drew and checked your schematic", "PASS", 25,
                       f"KiCad reported {len(erc.findings)} findings, retained in the report.")
        if result.placement_request is None:
            raise ValueError("The derived circuit has no fingerprinted placement intent")
        with telemetry.stage("placement"):
            placement = generate_placement(circuit, result.placement_request, catalog)
        (destination / "placement-request.json").write_text(
            result.placement_request.model_dump_json(indent=2), encoding="utf-8",
        )
        (destination / "placement.json").write_text(placement.model_dump_json(indent=2), encoding="utf-8")
        report = self.finish_design(destination, brief.description, design, catalog,
                                    placement.board, scripted=False,placement_request=result.placement_request,
                                    confirmed_brief=brief)
        report.project.update({"brief_fingerprint": brief.fingerprint,
                               "circuit_hash": circuit.content_hash,
                               "placement_request_fingerprint": placement.request_fingerprint,
                               "archetype":brief.archetype.value,
                               "supported_fixture":FAMILY_COPY[brief.archetype][0]})
        if brief.archetype is ArchetypeId.A4_USB_VOICE_RECORDER:
            from .recorder import write_recorder_artifacts
            report.project["recorder"] = write_recorder_artifacts(destination, brief, circuit.content_hash)
            report.limitations = [x for x in report.limitations if not x.startswith(("Firmware is not included", "Not simulation verified"))]
            report.limitations.extend(RECORDER_LIMITATIONS)
            for line in report.experience.confidence.not_verified:
                if line.label == "Simulation":
                    line.status = "PARTIALLY_VERIFIED"
                    line.detail = "Digital recording scenarios were simulated. Acoustics, electrical timing and physical hardware remain unverified."
            report.verification_ladder.append({"stage":"Recorder digital simulation", "status":"SIMULATED",
                "detail":"Six synthetic workload/fault scenarios; not analog simulation, firmware emulation or physical measurement."})
            for group in [*report.experience.checks, *(g for section in report.experience.check_sections for g in section.groups)]:
                if group.group == "simulation":
                    group.label = "Analog circuit simulation"
                    group.question = "Analog behavior was not simulated. Separate recorder digital scenarios are available above."
            for step in report.experience.tour.steps:
                step.facts = ["digital simulation INCLUDED; analog and physical behavior UNVERIFIED" if fact == "simulation UNSUPPORTED" else fact for fact in step.facts]
            from .product import BringUpStep
            report.experience.bring_up.extend([
                BringUpStep(action="Build and flash the exact exported firmware using firmware/README.md. Record speech and a known tone, then play the WAV file on a computer.", prediction=None, basis="Firmware source is included; physical recording has not been tested."),
                BringUpStep(action="Measure microphone clock/data alignment, both 3.3 V rails, SD write-current spikes, USB current and regulator temperature; test full/slow/removed cards and power interruption.", prediction=None, basis="Digital simulation cannot establish these electrical, acoustic or storage properties.")])
        if hasattr(catalog, "snapshot_hash"):
            report.project.update({
                "catalog_snapshot_sha256": catalog.snapshot_hash,
                "active_component_revisions": catalog.revision_bindings,
            })
        report.pcb["placement"] = {
            "algorithm": placement.algorithm,
            "request_fingerprint": placement.request_fingerprint,
            "constraints_hash": placement.board.content_hash,
            "metrics": placement.metrics.model_dump(mode="json"),
            "limitations": list(placement.limitations),
        }
        (destination / "confirmed-brief.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")
        (destination / "circuit.json").write_text(circuit.model_dump_json(indent=2), encoding="utf-8")
        return report
