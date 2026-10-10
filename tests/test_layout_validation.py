import hashlib

import pytest

from ohmni.application.layout_validation import (
    AuthoritativeLayoutValidator,
    BuildOutcome,
    KiCadLayoutBuildEngine,
    LayoutValidationStatus,
)
from ohmni.domain.component_atlas import (
    BoardDraft,
    DraftContext,
    DraftIdentity,
    PlacementTarget,
)
from ohmni.eda.kicad.placement import golden_board_constraints
from ohmni.eda.models import ErcStatus
from ohmni.eda.pcb_models import DrcStatus
from ohmni.physical.models import PlacementConstraint, PlacementConstraintKind, PlacementRegion


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Engine:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def run(self, circuit, board, destination):
        self.calls.append((circuit, board, destination))
        return self.outcome


def valid_outcome(**changes):
    values = {
        "status": LayoutValidationStatus.VALID,
        "schematic_sha256": digest("schematic"),
        "erc_sha256": digest("erc"),
        "placed_pcb_sha256": digest("placed"),
        "routed_pcb_sha256": digest("routed"),
        "routing_plan_sha256": digest("routing"),
        "drc_sha256": digest("drc"),
        "manufacturing_sha256": digest("manufacturing"),
        "parsed_artifact_checked": True,
    }
    values.update(changes)
    return BuildOutcome(**values)


def board_draft(golden, board=None):
    board = board or golden_board_constraints()
    refs = tuple(sorted(p.component_ref for p in board.placements))
    placements = tuple((p.component_ref, PlacementTarget(
        x_nm=round(p.x_mm * 1_000_000), y_nm=round(p.y_mm * 1_000_000),
        rotation_mdeg=round(p.rotation_deg * 1_000), side=p.side,
    )) for p in sorted(board.placements, key=lambda item: item.component_ref))
    return BoardDraft(
        context=DraftContext(
            identity=DraftIdentity(
                draft_id="draft-t06", project_id="1234567890abcdef",
                base_revision_id="fedcba0987654321",
                base_artifact_sha256=digest("base"),
                catalog_snapshot_sha256=digest("catalog"),
            ),
            owner_workspace_id="local", next_sequence=1, status="OPEN",
            existing_components=refs,
        ),
        source_revision_number=1, source_bytes_sha256=digest("base"),
        circuit_sha256=golden.content_hash, parts_sha256=digest("parts"),
        nets_sha256=digest("nets"), pads_sha256=digest("pads"),
        base_placements=placements, placements=placements,
    )


def move(draft, ref, *, x, y):
    placements = tuple(
        (name, target if name != ref else target.model_copy(update={
            "x_nm": round(x * 1_000_000), "y_nm": round(y * 1_000_000),
        }))
        for name, target in draft.placements
    )
    return draft.model_copy(update={"placements": placements})


@pytest.mark.parametrize("kind", ["overlap", "outside", "keepout", "antenna_edge"])
def test_invalid_geometry_fails_before_build(kind, tmp_path, golden, catalog):
    board = golden_board_constraints()
    draft = board_draft(golden, board)
    if kind == "overlap":
        draft = move(draft, "R1", x=16, y=58)
    elif kind == "outside":
        draft = move(draft, "R1", x=-2, y=-2)
    elif kind == "keepout":
        exclusion = PlacementConstraint(
            constraint_id="MECHANICAL-KEEPOUT", kind=PlacementConstraintKind.KEEPOUT,
            component_ref="U2", relative_to_component=False,
            keepout_region=PlacementRegion(
                x_min_mm=5, y_min_mm=15, x_max_mm=15, y_max_mm=25,
            ),
            reason="Keep components outside the reserved mechanical region",
        )
        board = board.model_copy(update={
            "placement_constraints": [*board.placement_constraints, exclusion],
        })
        draft = move(draft, "R1", x=10, y=20)
    else:
        antenna = PlacementConstraint(
            constraint_id="ESP32-ANTENNA", kind=PlacementConstraintKind.KEEPOUT,
            component_ref="U1", relative_to_component=True,
            keepout_region=PlacementRegion(
                x_min_mm=-9, y_min_mm=-15.74, x_max_mm=9, y_max_mm=-9,
            ),
            reason="Keep components out of the module antenna edge region",
        )
        board = board.model_copy(update={
            "placement_constraints": [*board.placement_constraints, antenna],
        })
        draft = move(draft, "R1", x=45, y=24)
    engine = Engine(valid_outcome())
    receipt = AuthoritativeLayoutValidator(catalog, engine).validate(
        draft, golden, board, tmp_path,
    )
    assert receipt.status is LayoutValidationStatus.PLACEMENT_INVALID
    assert not receipt.physical_passed and not receipt.download_enabled
    assert receipt.failures and engine.calls == []


@pytest.mark.parametrize("status", [
    LayoutValidationStatus.ROUTING_FAILED,
    LayoutValidationStatus.EDA_UNAVAILABLE,
    LayoutValidationStatus.DRC_FAILED,
    LayoutValidationStatus.MANUFACTURING_FAILED,
])
def test_downstream_failure_is_explicit_and_never_enables_download(
    status, tmp_path, golden, catalog,
):
    draft = board_draft(golden)
    engine = Engine(BuildOutcome(status=status, details=("bounded failure",)))
    receipt = AuthoritativeLayoutValidator(catalog, engine).validate(
        draft, golden, golden_board_constraints(), tmp_path,
    )
    assert receipt.status is status
    assert receipt.failures == ("bounded failure",)
    assert not receipt.download_enabled


def test_valid_receipt_binds_base_draft_artifacts_and_stales_after_edit(
    tmp_path, golden, catalog,
):
    draft = board_draft(golden)
    validator = AuthoritativeLayoutValidator(catalog, Engine(valid_outcome()))
    receipt = validator.validate(draft, golden, golden_board_constraints(), tmp_path)
    assert receipt.status is LayoutValidationStatus.VALID
    assert receipt.draft_sha256 == draft.content_sha256
    assert receipt.base_revision_id == draft.context.identity.base_revision_id
    assert receipt.base_artifact_sha256 == draft.context.identity.base_artifact_sha256
    assert receipt.catalog_snapshot_sha256 == draft.context.identity.catalog_snapshot_sha256
    assert receipt.board_sha256 and receipt.physical_report_sha256
    assert receipt.build.parsed_artifact_checked
    assert validator.current_download(draft) == receipt
    edited = move(draft, "R1", x=44, y=58)
    assert validator.current_download(edited) is None


def test_claimed_success_without_parsed_complete_lineage_fails_closed(
    tmp_path, golden, catalog,
):
    draft = board_draft(golden)
    outcome = valid_outcome(parsed_artifact_checked=False, drc_sha256=None)
    receipt = AuthoritativeLayoutValidator(catalog, Engine(outcome)).validate(
        draft, golden, golden_board_constraints(), tmp_path,
    )
    assert receipt.status is LayoutValidationStatus.ARTIFACT_INVALID
    assert not receipt.download_enabled


def test_circuit_fingerprint_is_authoritative(tmp_path, golden, catalog):
    draft = board_draft(golden).model_copy(update={"circuit_sha256": digest("other")})
    with pytest.raises(ValueError, match="fingerprint"):
        AuthoritativeLayoutValidator(catalog, Engine(valid_outcome())).validate(
            draft, golden, golden_board_constraints(), tmp_path,
        )


def test_real_build_boundary_preserves_erc_unavailable(tmp_path, golden, catalog):
    class EdaUnavailable:
        def run_erc(self, artifact):
            return type("Erc", (), {"status": ErcStatus.UNAVAILABLE})()

    outcome = KiCadLayoutBuildEngine(catalog, eda=EdaUnavailable()).run(
        golden, golden_board_constraints(), tmp_path,
    )
    assert outcome.status is LayoutValidationStatus.EDA_UNAVAILABLE
    assert outcome.details == ("KiCad ERC is unavailable",)


@pytest.mark.slow_integration
def test_real_compiler_router_parser_and_manufacturing_chain(tmp_path, golden, catalog):
    class Report:
        def __init__(self, status):
            self.status = status

        def model_dump_json(self, **kwargs):
            return '{"result":"independently supplied EDA pass"}'

    class PassingEda:
        def run_erc(self, artifact):
            return Report(ErcStatus.PASS)

        def run_drc(self, artifact):
            return Report(DrcStatus.PASS)

    outcome = KiCadLayoutBuildEngine(catalog, eda=PassingEda()).run(
        golden, golden_board_constraints(), tmp_path,
    )
    assert outcome.status is LayoutValidationStatus.VALID
    assert outcome.parsed_artifact_checked
    assert all((outcome.schematic_sha256, outcome.erc_sha256,
                outcome.placed_pcb_sha256, outcome.routed_pcb_sha256,
                outcome.routing_plan_sha256, outcome.drc_sha256,
                outcome.manufacturing_sha256))
