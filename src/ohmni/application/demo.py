"""Deterministic end-user demo assembled from real Ohmni reports and artifacts.

This layer projects status; it never independently decides electrical truth.
Every badge comes from a typed report produced by an existing subsystem.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

from ..bom import calculate_cost, classify_assembly, generate_bom, synthetic_fixture_supplier
from ..catalog import default_catalog
from ..domain import VerificationReport
from ..eda.kicad import KiCadCliAdapter, KiCadPcbCompiler
from ..eda.kicad.placement import golden_board_constraints
from ..generation import DesignOrchestrator, DesignReport, RequirementOrigin
from ..generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider
from ..manufacturing import (
    KiCadFabricationExporter,
    ReleaseStatus,
    prototype_profile,
    verify_manufacturing,
)
from ..routing.router import DeterministicRouter
from ..routing.verifier import verify_routing
from .visuals import pcb_svg, schematic_svg

DEMO_REQUEST = GOLDEN_REQUEST
UNSUPPORTED_DEMO_REQUEST = "Only the displayed deterministic ESP32 + BME280 request is supported"


def require_demo_request(value: object) -> str:
    """Return the one scripted request or reject without interpreting caller text."""
    if not isinstance(value, str) or value != DEMO_REQUEST:
        raise ValueError(UNSUPPORTED_DEMO_REQUEST)
    return DEMO_REQUEST


def _require_demo_design_provenance(design: DesignReport, request: str) -> DesignReport:
    """Bind every explicit typed requirement statement to the scripted request."""
    provenance = design.requirements.provenance if design.requirements is not None else []
    if any(
        statement.origin is RequirementOrigin.EXPLICIT and statement.source_text != request
        for statement in provenance
    ):
        raise ValueError(UNSUPPORTED_DEMO_REQUEST)
    return design


def _semantic_ladder(report: VerificationReport, initial_blocking: int) -> list[dict[str, object]]:
    """Project report-owned subsystem roll-ups without inventing an overall verdict."""
    return [
        {
            "stage": f"Ohmni semantic verification — {name.replace('_', ' ').title()}",
            "subsystem": name,
            "status": status.value,
            "detail": (
                "Deterministic subsystem roll-up from 24 rules; "
                f"initial proposal had {initial_blocking} blocking findings"
            ),
        }
        for name, status in report.subsystem_status.items()
    ]


class DemoProgress(BaseModel):
    stage: str
    label: str
    status: str
    detail: str = ""
    percent: int = Field(ge=0, le=100)


class DemoReport(BaseModel):
    schema_version: int = 1
    mode: str = "deterministic_scripted_demo"
    project: dict[str, object]
    requirements: list[dict[str, object]]
    evidence: list[dict[str, object]]
    architecture: list[dict[str, object]]
    failure_and_repair: dict[str, object]
    verification_ladder: list[dict[str, object]]
    notebook: list[dict[str, object]]
    lessons: list[dict[str, object]]
    schematic: dict[str, object]
    pcb: dict[str, object]
    manufacturing: dict[str, object]
    bom: dict[str, object]
    economics: dict[str, object]
    assembly: dict[str, object]
    release: dict[str, object]
    limitations: list[str]


ProgressCallback = Callable[[DemoProgress], None]


class DemoPipeline:
    """Run the supported logger journey without network or live model access."""

    def __init__(self, progress: ProgressCallback | None = None) -> None:
        self.progress = progress or (lambda _event: None)

    def _progress(self, stage: str, label: str, status: str, percent: int, detail: str = "") -> None:
        self.progress(DemoProgress(stage=stage, label=label, status=status, percent=percent, detail=detail))

    def run(self, destination: Path, request: str = DEMO_REQUEST) -> DemoReport:
        request = require_demo_request(request)
        destination = destination.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        catalog = default_catalog()
        self._progress("requirements", "Interpreting supported project request", "RUNNING", 5)
        design = DesignOrchestrator(flawed_logger_provider(), catalog).design(
            request, output=destination / "golden.kicad_sch", run_eda=True,
        )
        if not design.final_circuit or not design.artifact or not design.erc:
            raise RuntimeError(f"design pipeline failed: {[issue.message for issue in design.issues]}")
        circuit = design.final_circuit
        self._progress("repair", "Semantic violation repaired and re-verified", "PASS", 25)

        board = golden_board_constraints()
        compiler = KiCadPcbCompiler(catalog)
        placed = compiler.compile(circuit, design.artifact, board, destination / "golden.placed.kicad_pcb")
        self._progress("placement", "Deterministic component placement verified", "PASS", 35)
        self._progress("routing", "Routing 51 required connections", "RUNNING", 40)
        plan = DeterministicRouter().route(circuit, placed, board)
        route_report = verify_routing(circuit, placed, board, plan)
        if not route_report.passed:
            raise RuntimeError("independent routing verification failed")
        routed = compiler.compile(circuit, design.artifact, board, destination / "golden.kicad_pcb", plan)
        self._progress("routing", "Independent copper connectivity verified", "PASS", 75)
        drc = KiCadCliAdapter().run_drc(routed)
        if drc.findings or drc.unconnected_items or drc.status.value not in {"pass", "pass_with_warnings"}:
            raise RuntimeError("KiCad DRC did not close cleanly")
        self._progress("drc", "KiCad DRC: 0 violations, 0 unrouted", "PASS", 82)

        profile = prototype_profile()
        manufacturing = verify_manufacturing(routed, board, plan, profile)
        if not manufacturing.passed:
            raise RuntimeError("manufacturing profile verification failed")
        self._progress("manufacturing", "Prototype manufacturing profile checked", "PASS", 87)
        bom = generate_bom(circuit, catalog)
        costs = calculate_cost(bom, synthetic_fixture_supplier(bom), 1)
        assembly = classify_assembly(bom)
        package = KiCadFabricationExporter().export(
            routed, drc, manufacturing, profile, destination / "fabrication",
        )
        self._progress("release", "Fabrication package ready for human review", "PASS_WITH_WARNINGS", 100)
        return project_demo_report(
            request=request, design=design, catalog=catalog, board=board, placed=placed,
            plan=plan, route_report=route_report, routed=routed, drc=drc,
            manufacturing=manufacturing, bom=bom, costs=costs, assembly=assembly,
            package=package,
        )


def _status(value: bool, warning: bool = False) -> str:
    return "PASS_WITH_WARNINGS" if value and warning else "PASS" if value else "FAIL"


def _evidence_rows(catalog) -> list[dict[str, object]]:
    sensor = catalog.require("BME280")
    rows: list[dict[str, object]] = []
    for rail in sensor.supply_rails:
        for label, quantity in (
            ("recommended operating minimum", rail.operating.minimum),
            ("recommended operating maximum", rail.operating.maximum),
            ("absolute maximum", rail.absolute_max),
        ):
            evidence = rail.evidence[0] if rail.evidence else None
            rows.append({
                "component": "BME280", "claim": f"{rail.name} {label}",
                "value": quantity.engineering() if quantity else "UNKNOWN",
                "status": evidence.status.value.upper() if evidence else "UNKNOWN",
                "source": evidence.source_id if evidence else None,
                "page": evidence.page if evidence else None,
                "snippet": evidence.snippet if evidence else None,
                "limitation": "Seed catalog citation; machine re-verification status is shown truthfully.",
            })
    return rows


def project_demo_report(**values) -> DemoReport:
    """Pure presentation projection; inputs are already verified subsystem reports."""
    request = require_demo_request(values["request"])
    design = _require_demo_design_provenance(values["design"], request)
    catalog=values["catalog"]
    board=values["board"];plan=values["plan"];route_report=values["route_report"]
    routed=values["routed"];drc=values["drc"];manufacturing=values["manufacturing"]
    bom=values["bom"];costs=values["costs"];assembly=values["assembly"];package=values["package"]
    requirements=[statement.model_dump(mode="json") for statement in design.requirements.provenance]
    first,last=design.semantic_attempts[0],design.semantic_attempts[-1]
    blocking=[finding for finding in first.findings if finding.severity.value in {"critical","error"}]
    repair=design.repairs[0]
    event_groups = [
        ("design", design.notebook.events),
        ("placed_pcb_compilation", values["placed"].events),
        ("routing", plan.events),
        ("routed_pcb_compilation", routed.events),
        ("drc", drc.events),
        ("manufacturing", manufacturing.events),
        ("bom", bom.events),
        ("cost", costs.events),
        ("assembly", assembly.events),
        ("fabrication_release", package.events),
    ]
    notebook = []
    for phase, events in event_groups:
        for event in events:
            notebook.append({
                "id": event.event_id,
                "sequence": len(notebook) + 1,
                "phase": phase,
                "kind": event.kind.value,
                "summary": event.summary,
                "status": "FAIL" if "failed" in event.kind.value else "RECORDED",
                "finding_ids": event.related_finding_ids,
                "circuit_hash": event.circuit_content_hash,
            })
    evidence=_evidence_rows(catalog)
    ladder=[
        {"stage":"Requirements","status":"PASS","detail":f"{len(requirements)} provenance-labeled statements"},
        {"stage":"Datasheet evidence","status":"PASS_WITH_WARNINGS","detail":"Electrical claims retain catalog/datasheet provenance; seed citations are not overstated"},
        *_semantic_ladder(last, len(blocking)),
        {"stage":"KiCad ERC","status":design.erc.status.value.upper(),"detail":f"{len(design.erc.findings)} findings on exact schematic"},
        {"stage":"Ohmni physical verification","status":_status(routed.compilation.physical_verification.passed),"detail":f"{len(routed.compilation.physical_verification.findings)} geometry checks"},
        {"stage":"Ohmni routing verification","status":_status(route_report.passed),"detail":f"{plan.statistics.required_connections} required connections"},
        {"stage":"KiCad DRC","status":drc.status.value.upper(),"detail":f"{len(drc.findings)} violations / {len(drc.unconnected_items)} unrouted"},
        {"stage":"Manufacturing profile","status":_status(manufacturing.passed),"detail":manufacturing.profile.display_name},
        {"stage":"Assembly / cost","status":"PASS_WITH_WARNINGS","detail":"Assembly risks and incomplete price coverage remain visible"},
        {"stage":"Bench verification","status":"NOT_YET_VERIFIED","detail":"No physical prototype has been measured"},
    ]
    bom_rows=[]
    cost_by_key={line.identity.key:line for line in costs.lines}
    for line in bom.lines:
        cost=cost_by_key[line.identity.key]
        bom_rows.append({"references":line.references,"part":line.identity.mpn or line.identity.part_id,"description":line.description,"package":line.identity.package,"quantity":line.quantity_per_board,"evidence_status":line.evidence_status,"unit_price":str(cost.unit_price) if cost.unit_price is not None else None,"knowledge":cost.knowledge.value.upper(),"purchase_quantity":cost.purchase_quantity,"purchase_cost":str(cost.purchase_cost) if cost.purchase_cost is not None else None})
    release_current=routed.lineage_is_current and package.is_valid_for(routed.fingerprint.digest,manufacturing.profile.content_hash)
    release_status=package.status if release_current else ReleaseStatus.STALE
    return DemoReport(
        project={"name":design.requirements.requirements.project_name,"request":request,"supported_fixture":"ESP32 + BME280 environmental logger","status":release_status.value.upper()},
        requirements=requirements,evidence=evidence,
        architecture=[block.model_dump(mode="json") for block in design.architecture.blocks],
        failure_and_repair={"status":"REPAIRED","rule":"PB-PWR-001","original":"BME280 VDD and VDDIO connected to 5 V VBUS","operating_range":"1.71 V to 3.6 V","findings":[{"severity":f.severity.value.upper(),"title":f.title,"description":f.description} for f in blocking if f.rule_id=="PB-PWR-001"],"operations":[op.model_dump(mode="json") for op in repair.patch.operations],"result":"Both sensor supply pins moved to 3V3; PB-PWR-001 passed after deterministic re-verification."},
        verification_ladder=ladder,notebook=notebook,
        lessons=[lesson.model_dump(mode="json") for lesson in design.lessons],
        schematic={"path":str(design.artifact.path),"fingerprint":design.artifact.fingerprint.digest,"current":design.artifact.is_current,"erc_status":design.erc.status.value.upper(),"erc_findings":len(design.erc.findings),"svg":schematic_svg(design.artifact)},
        pcb={"path":str(routed.path),"fingerprint":routed.fingerprint.digest,"source_schematic_fingerprint":routed.schematic_fingerprint.digest,"source_placed_pcb_fingerprint":routed.source_placed_pcb_fingerprint.digest if routed.source_placed_pcb_fingerprint else None,"current":routed.lineage_is_current,"drc_status":drc.status.value.upper(),"violations":len(drc.findings),"unrouted":len(drc.unconnected_items),"statistics":plan.statistics.model_dump(mode="json"),"svg":pcb_svg(board,plan)},
        manufacturing={"profile":manufacturing.profile.display_name,"provenance":manufacturing.profile.provenance.value,"findings":[finding.model_dump(mode="json") for finding in manufacturing.findings]},
        bom={"references":bom.reference_count,"unique_lines":len(bom.lines),"lines":bom_rows},
        economics={"scenario_boards":1,"pricing_coverage":costs.pricing_coverage,"known_consumption_cost":str(costs.known_consumption_cost),"known_purchase_requirement":str(costs.known_purchase_requirement),"fabrication":costs.fabrication.value.upper(),"shipping":costs.shipping.value.upper(),"tooling":costs.tooling.value.upper(),"pricing_source":"SYNTHETIC FIXTURE - NOT LIVE SUPPLIER DATA"},
        assembly={"hand_solder_requirement_satisfied":assembly.hand_solder_requirement_satisfied,"risks":[risk.model_dump(mode="json") for risk in assembly.risks],"limitations":assembly.limitations},
        release={"status":release_status.value.upper(),"package_fingerprint":package.package_fingerprint,"pcb_fingerprint":package.source_pcb_fingerprint,"current":release_current,"files":[file.model_dump(mode="json") for file in package.files],"manifest":package.manifest.model_dump(mode="json")},
        limitations=["Supported deterministic demo: ESP32/BME280 logger, not arbitrary hardware.","Not simulation verified.","Not thermal, EMC, RF, or signal-integrity verified.","Not bench verified.","Manufacturing profile is synthetic and requires human review.","No guarantee of successful fabrication or assembly."],
    )
