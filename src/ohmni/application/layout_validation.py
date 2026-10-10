"""Authoritative validation and rerouting for settled layout drafts (CAB-T06)."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from ..domain.component_atlas import BoardDraft
from ..eda.kicad import KiCadCliAdapter, KiCadPcbCompiler, KiCadSchematicCompiler
from ..eda.models import ErcStatus
from ..eda.pcb_models import DrcStatus
from ..manufacturing import prototype_profile, verify_manufacturing
from ..physical.models import BoardConstraints, ComponentPlacement
from ..physical.placement import resolve_physical_bindings
from ..physical.rules import verify_physical
from ..routing.router import DeterministicRouter
from ..routing.verifier import verify_routing


class LayoutValidationStatus(StrEnum):
    VALID = "valid"
    PLACEMENT_INVALID = "placement_invalid"
    ROUTING_FAILED = "routing_failed"
    EDA_UNAVAILABLE = "eda_unavailable"
    ERC_FAILED = "erc_failed"
    DRC_FAILED = "drc_failed"
    MANUFACTURING_FAILED = "manufacturing_failed"
    ARTIFACT_INVALID = "artifact_invalid"


class BuildOutcome(BaseModel):
    """Result from the authoritative build boundary; never inferred by the UI."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    status: LayoutValidationStatus
    details: tuple[str, ...] = ()
    schematic_sha256: str | None = None
    erc_sha256: str | None = None
    placed_pcb_sha256: str | None = None
    routed_pcb_sha256: str | None = None
    routing_plan_sha256: str | None = None
    drc_sha256: str | None = None
    manufacturing_sha256: str | None = None
    parsed_artifact_checked: bool = False


class LayoutBuildEngine(Protocol):
    def run(self, circuit, board: BoardConstraints, destination: Path) -> BuildOutcome: ...


class LayoutValidationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: LayoutValidationStatus
    draft_sha256: str
    base_revision_id: str
    base_artifact_sha256: str
    catalog_snapshot_sha256: str
    circuit_sha256: str
    board_sha256: str
    physical_report_sha256: str
    physical_passed: bool
    build: BuildOutcome | None = None
    failures: tuple[str, ...] = ()
    download_enabled: bool = False

    def is_current_for(self, draft: BoardDraft) -> bool:
        return (
            self.download_enabled
            and self.status is LayoutValidationStatus.VALID
            and self.draft_sha256 == draft.content_sha256
            and self.base_revision_id == draft.context.identity.base_revision_id
            and self.base_artifact_sha256 == draft.context.identity.base_artifact_sha256
            and self.catalog_snapshot_sha256 == draft.context.identity.catalog_snapshot_sha256
            and self.circuit_sha256 == draft.circuit_sha256
        )


class AuthoritativeLayoutValidator:
    """Validate one server-owned draft and issue an exact, revocable receipt."""

    def __init__(self, catalog, engine: LayoutBuildEngine | None = None):
        self.catalog = catalog
        self.engine = engine or KiCadLayoutBuildEngine(catalog)
        self._receipts: dict[str, LayoutValidationReceipt] = {}

    def validate(
        self, draft: BoardDraft, circuit, board_template: BoardConstraints, destination: Path,
    ) -> LayoutValidationReceipt:
        if draft.context.status != "OPEN":
            raise ValueError("Only an open layout draft can be validated")
        if circuit.content_hash != draft.circuit_sha256:
            raise ValueError("Circuit fingerprint differs from the immutable draft identity")
        targets = dict(draft.placements)
        board = board_template.model_copy(update={"placements": [
            ComponentPlacement(
                component_ref=ref,
                x_mm=target.x_nm / 1_000_000,
                y_mm=target.y_nm / 1_000_000,
                rotation_deg=target.rotation_mdeg / 1_000,
                side=target.side,
                reason="User-set existing-component layout draft",
            )
            for ref, target in sorted(targets.items())
        ]})
        _, footprint_ids, pad_bindings = resolve_physical_bindings(circuit, self.catalog)
        physical = verify_physical(circuit, board, footprint_ids, pad_bindings)
        physical_sha = hashlib.sha256(
            physical.model_dump_json(exclude={"events"}).encode()
        ).hexdigest()
        failures = tuple(
            finding.description for finding in physical.findings if finding.status.value != "pass"
        )
        if not physical.passed:
            receipt = LayoutValidationReceipt(
                status=LayoutValidationStatus.PLACEMENT_INVALID,
                draft_sha256=draft.content_sha256,
                base_revision_id=draft.context.identity.base_revision_id,
                base_artifact_sha256=draft.context.identity.base_artifact_sha256,
                catalog_snapshot_sha256=draft.context.identity.catalog_snapshot_sha256,
                circuit_sha256=draft.circuit_sha256,
                board_sha256=board.content_hash,
                physical_report_sha256=physical_sha,
                physical_passed=False,
                failures=failures,
            )
        else:
            outcome = self.engine.run(circuit, board, Path(destination))
            valid = (
                outcome.status is LayoutValidationStatus.VALID
                and outcome.parsed_artifact_checked
                and all((outcome.schematic_sha256, outcome.placed_pcb_sha256,
                         outcome.routed_pcb_sha256, outcome.routing_plan_sha256,
                         outcome.erc_sha256, outcome.drc_sha256,
                         outcome.manufacturing_sha256))
            )
            status = LayoutValidationStatus.VALID if valid else outcome.status
            if outcome.status is LayoutValidationStatus.VALID and not valid:
                status = LayoutValidationStatus.ARTIFACT_INVALID
            receipt = LayoutValidationReceipt(
                status=status,
                draft_sha256=draft.content_sha256,
                base_revision_id=draft.context.identity.base_revision_id,
                base_artifact_sha256=draft.context.identity.base_artifact_sha256,
                catalog_snapshot_sha256=draft.context.identity.catalog_snapshot_sha256,
                circuit_sha256=draft.circuit_sha256,
                board_sha256=board.content_hash,
                physical_report_sha256=physical_sha,
                physical_passed=True,
                build=outcome,
                failures=outcome.details,
                download_enabled=valid,
            )
        self._receipts[draft.context.identity.draft_id] = receipt
        return receipt

    def current_download(self, draft: BoardDraft) -> LayoutValidationReceipt | None:
        receipt = self._receipts.get(draft.context.identity.draft_id)
        return receipt if receipt is not None and receipt.is_current_for(draft) else None


class KiCadLayoutBuildEngine:
    """Run the existing deterministic toolchain without converting absence to PASS."""

    def __init__(self, catalog, *, eda: KiCadCliAdapter | None = None,
                 router: DeterministicRouter | None = None):
        self.catalog = catalog
        self.eda = eda or KiCadCliAdapter()
        self.router = router or DeterministicRouter()

    @staticmethod
    def _drc_sha(report) -> str:
        return report.model_dump_json(exclude={"events"})

    def run(self, circuit, board: BoardConstraints, destination: Path) -> BuildOutcome:
        destination.mkdir(parents=True, exist_ok=True)
        schematic = KiCadSchematicCompiler(self.catalog).compile(
            circuit, destination / "draft.kicad_sch",
        )
        erc = self.eda.run_erc(schematic)
        if erc.status is ErcStatus.UNAVAILABLE:
            return BuildOutcome(status=LayoutValidationStatus.EDA_UNAVAILABLE,
                                details=("KiCad ERC is unavailable",))
        if erc.status not in {ErcStatus.PASS, ErcStatus.PASS_WITH_WARNINGS}:
            return BuildOutcome(status=LayoutValidationStatus.ERC_FAILED,
                                details=(f"KiCad ERC status: {erc.status.value}",))
        erc_sha = hashlib.sha256(
            erc.model_dump_json(exclude={"events"}).encode()
        ).hexdigest()
        compiler = KiCadPcbCompiler(self.catalog)
        placed = compiler.compile(circuit, schematic, board, destination / "placed.kicad_pcb")
        plan = self.router.route(circuit, placed, board)
        route_report = verify_routing(circuit, placed, board, plan)
        if plan.failures or not route_report.passed:
            details = tuple(f"{failure.net_name}: {failure.reason.value}" for failure in plan.failures)
            return BuildOutcome(status=LayoutValidationStatus.ROUTING_FAILED,
                                details=details or ("Routing verification failed",),
                                schematic_sha256=schematic.fingerprint.digest,
                                erc_sha256=erc_sha,
                                placed_pcb_sha256=placed.fingerprint.digest,
                                routing_plan_sha256=plan.content_hash)
        routed = compiler.compile(
            circuit, schematic, board, destination / "routed.kicad_pcb", plan,
        )
        parsed = (
            routed.is_current and routed.lineage_is_current
            and routed.compilation.artifact_fingerprint == routed.fingerprint
            and routed.compilation.constraints_hash == board.content_hash
            and routed.compilation.routing_plan_fingerprint == plan.content_hash
            and routed.compilation.routing_verification is not None
            and routed.compilation.routing_verification.passed
        )
        if not parsed:
            return BuildOutcome(status=LayoutValidationStatus.ARTIFACT_INVALID,
                                details=("Parsed PCB artifact lineage is inconsistent",))
        drc = self.eda.run_drc(routed)
        if drc.status is DrcStatus.UNAVAILABLE:
            return BuildOutcome(status=LayoutValidationStatus.EDA_UNAVAILABLE,
                                details=("KiCad DRC is unavailable",))
        if drc.status not in {DrcStatus.PASS, DrcStatus.PASS_WITH_WARNINGS}:
            return BuildOutcome(status=LayoutValidationStatus.DRC_FAILED,
                                details=(f"KiCad DRC status: {drc.status.value}",))
        profile = prototype_profile()
        manufacturing = verify_manufacturing(routed, board, plan, profile)
        if not manufacturing.passed:
            return BuildOutcome(status=LayoutValidationStatus.MANUFACTURING_FAILED,
                                details=tuple(f.detail for f in manufacturing.findings
                                              if f.status.value != "pass"))
        drc_sha = hashlib.sha256(self._drc_sha(drc).encode()).hexdigest()
        return BuildOutcome(
            status=LayoutValidationStatus.VALID,
            schematic_sha256=schematic.fingerprint.digest,
            erc_sha256=erc_sha,
            placed_pcb_sha256=placed.fingerprint.digest,
            routed_pcb_sha256=routed.fingerprint.digest,
            routing_plan_sha256=plan.content_hash,
            drc_sha256=drc_sha,
            manufacturing_sha256=manufacturing.content_hash,
            parsed_artifact_checked=True,
        )


__all__ = [
    "AuthoritativeLayoutValidator", "BuildOutcome", "KiCadLayoutBuildEngine",
    "LayoutBuildEngine", "LayoutValidationReceipt", "LayoutValidationStatus",
]
