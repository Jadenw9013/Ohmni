"""A confirmed, bounded brief through the real engineering pipeline.

No scripted model responses or faulty proposals participate in personal projects.
The historical demo remains separately available for regression and explanation.
"""

from pathlib import Path

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
from ..physical.sensor_layout import sensor_board_constraints
from ..synthesis import SynthesisBrief, synthesize_a1
from ..verifier import verify
from .demo import DemoPipeline, DemoReport
from .product import Brief, build_brief


class ProjectRefusalError(ValueError):
    def __init__(self, refusal):
        self.refusal = refusal
        super().__init__(refusal.message)


def prepare_project(brief: SynthesisBrief):
    """Resolve the exact same contract for preview and execution."""
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
        "Placement uses the authored 100 x 70 mm, two-layer sensor-board layout policy.",
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
    return result.circuit, CompiledRequirements(requirements=requirements, provenance=provenance)


def preview_project(brief: SynthesisBrief) -> Brief:
    _, requirements = prepare_project(brief)
    return build_brief(requirements)


class ProjectPipeline(DemoPipeline):
    def run(self, destination: Path, brief: SynthesisBrief) -> DemoReport:
        circuit, requirements = prepare_project(brief)
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
        report = self.finish_design(destination, brief.description, design, catalog,
                                    sensor_board_constraints(circuit), scripted=False)
        report.project.update({"brief_fingerprint": brief.fingerprint,
                               "circuit_hash": circuit.content_hash,
                               "supported_fixture": "Configurable USB ESP32/BME280 sensor board"})
        (destination / "confirmed-brief.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")
        (destination / "circuit.json").write_text(circuit.model_dump_json(indent=2), encoding="utf-8")
        return report
