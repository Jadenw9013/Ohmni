"""A confirmed, bounded brief through the real engineering pipeline.

No scripted model responses or faulty proposals participate in personal projects.
The historical demo remains separately available for regression and explanation.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
from ..physical.placement import generate_placement
from ..synthesis import ArchetypeId, SynthesisBrief, synthesize_a1
from ..verifier import verify
from .demo import DemoPipeline, DemoReport
from .product import Brief, build_brief


class ProjectRefusalError(ValueError):
    def __init__(self, refusal):
        self.refusal = refusal
        super().__init__(refusal.message)


class ProjectEditorRefusal(BaseModel):
    """An editor capability boundary, separate from circuit synthesis support."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: Literal["editor_configuration_unsupported"] = "editor_configuration_unsupported"
    message: str = (
        "Additional supported configurations are available through the compiler. "
        "The project editor supports one BME280 sensor until the family editor is available."
    )
    field_paths: tuple[str, ...]
    context: dict[str, str] = {"surface": "personal_project_editor"}


def _prepare_project(brief: SynthesisBrief):
    """Resolve the exact same contract for preview and execution."""
    unsupported = []
    if brief.archetype is not ArchetypeId.A1_USB_I2C_SENSOR:
        unsupported.append("archetype")
    if len(brief.sensors) != 1 or brief.sensors[0].part_id != "BME280":
        unsupported.append("sensors")
    if unsupported:
        raise ProjectRefusalError(ProjectEditorRefusal(field_paths=tuple(unsupported)))
    result = synthesize_a1(brief)
    if not result.accepted:
        raise ProjectRefusalError(result.refusal)
    address = result.circuit.component("U3").selected_i2c_address
    choices = [
        ("project_name", brief.project_name),
        ("description", brief.description),
        ("sensor", brief.sensors[0].part_id),
        ("sensor_address", f"0x{address:02X}"),
        ("status_light", "Included" if brief.status_led_count else "Omitted"),
        ("programming_header", "Included" if brief.include_programming_header else "Omitted"),
    ]
    assumptions = [
        "USB-C supplies power only; USB data and programming over USB-C are not provided.",
        "Firmware is not included. The sensor needs a program before it can report readings.",
        "BME280 assembly needs suitable surface-mount tools; hand assembly has not been tested.",
        "Placement is generated on a 100 x 70 mm, two-layer board from circuit blocks, capacitor ownership, and geometric constraints.",
        "Placement policies and antenna exclusion require hardware review; generated geometry does not establish RF performance.",
    ]
    assumptions.append(
        "Programming uses the six-pin header and an external 3.3 V serial adapter."
        if brief.include_programming_header else
        "The programming header is omitted. This revision has no supplied programming connector."
    )
    requirements = result.requirements.model_copy(update={
        "assumptions": [*result.requirements.assumptions, *assumptions],
    })
    provenance = [
        RequirementStatement(field=field, value=value,
                             origin=(RequirementOrigin.DEFAULT
                                     if field == "sensor_address" and brief.sensors[0].address is None
                                     else RequirementOrigin.EXPLICIT),
                             source_text=value)
        for field, value in choices
    ] + [
        RequirementStatement(field="assumption", value=value, origin=RequirementOrigin.ASSUMPTION)
        for value in assumptions
    ] + [
        RequirementStatement(field="target_logic_voltage", value="3.3 V",
                             origin=RequirementOrigin.DERIVED),
    ]
    return result, CompiledRequirements(requirements=requirements, provenance=provenance)


def prepare_project(brief: SynthesisBrief):
    """Preserve the existing public preview contract without dropping internal intent."""
    result, requirements = _prepare_project(brief)
    return result.circuit, requirements


def preview_project(brief: SynthesisBrief) -> Brief:
    _, requirements = prepare_project(brief)
    return build_brief(requirements)


class ProjectPipeline(DemoPipeline):
    def run(self, destination: Path, brief: SynthesisBrief) -> DemoReport:
        result, requirements = _prepare_project(brief)
        circuit = result.circuit
        catalog = default_catalog()
        destination = destination.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        self._progress("requirements", "Using your confirmed project choices", "PASS", 5,
                       "The saved brief determines this circuit and its optional parts.")
        semantic = verify(circuit, catalog, requirements.requirements)
        if semantic.export_blocked or semantic.coverage < 1:
            raise ValueError("The derived circuit did not pass complete semantic verification")
        self._progress("check", "Checked your parts and connections", "PASS", 15,
                       "Deterministic checks ran on this revision; no repair was needed.")
        artifact = KiCadSchematicCompiler(catalog).compile(circuit, destination / "golden.kicad_sch")
        erc = KiCadCliAdapter().run_erc(artifact)
        if erc.status.value not in {"pass", "pass_with_warnings"}:
            raise ValueError("KiCad could not complete the schematic checks")
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
        placement = generate_placement(circuit, result.placement_request, catalog)
        (destination / "placement-request.json").write_text(
            result.placement_request.model_dump_json(indent=2), encoding="utf-8",
        )
        (destination / "placement.json").write_text(placement.model_dump_json(indent=2), encoding="utf-8")
        report = self.finish_design(destination, brief.description, design, catalog,
                                    placement.board, scripted=False)
        report.project.update({"brief_fingerprint": brief.fingerprint,
                               "circuit_hash": circuit.content_hash,
                               "placement_request_fingerprint": placement.request_fingerprint,
                               "supported_fixture": "Configurable USB ESP32/BME280 sensor board"})
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
