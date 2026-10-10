import hashlib

import pytest

from ohmni.application.layout_drafts import (
    BaseBoardSnapshot,
    LayoutDraftConflict,
    LayoutDraftService,
)
from ohmni.application.project_store import ProjectStore
from ohmni.domain.component_atlas import DraftCommandRequest, PlacementTarget


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


@pytest.fixture
def draft_system(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.save_revision(
        {"project_name": "Layout test"}, digest("brief"),
        {"artifact": "base", "download": "base.kicad_pcb"},
    )
    revision = project["revisions"][0]
    snapshot = BaseBoardSnapshot(
        project_id=project["project_id"], revision_id=revision["revision_id"],
        revision_number=1, source_bytes=b"immutable pcb bytes",
        catalog_snapshot_sha256=digest("catalog"), circuit_sha256=digest("circuit"),
        parts_sha256=digest("parts"), nets_sha256=digest("nets"),
        pads_sha256=digest("pads"),
        placements={
            "R1": PlacementTarget(x_nm=1_000_000, y_nm=2_000_000),
            "U1": PlacementTarget(x_nm=5_000_000, y_nm=6_000_000),
        },
    )
    service = LayoutDraftService(store)
    return store, service, snapshot, service.open(snapshot)


def command(draft, sequence, kind="move_existing", *, key=None, **values):
    if kind == "move_existing":
        values = {"component_ref": "R1", "target": {
            "x_nm": 3_000_000, "y_nm": 4_000_000, "rotation_mdeg": 90_000,
        }} | values
    return DraftCommandRequest(
        identity=draft.context.identity, sequence=sequence,
        idempotency_key=key or f"command-{sequence}", command={"kind": kind, **values},
    )


def test_move_replays_deterministically_and_invalidates_every_physical_output(draft_system):
    _, service, snapshot, draft = draft_system
    moved = service.apply(command(draft, 1))
    assert dict(moved.placements)["R1"] == PlacementTarget(
        x_nm=3_000_000, y_nm=4_000_000, rotation_mdeg=90_000,
    )
    assert {item.value for item in moved.invalidated} == {
        "placement", "physical", "routing", "pcb", "drc", "bom", "economics",
        "manufacturing", "projection", "build_package",
    }
    assert (moved.circuit_sha256, moved.parts_sha256, moved.nets_sha256, moved.pads_sha256) == (
        snapshot.circuit_sha256, snapshot.parts_sha256, snapshot.nets_sha256, snapshot.pads_sha256,
    )
    assert service.apply(command(draft, 1)).content_sha256 == moved.content_sha256


def test_idempotency_payload_stale_sequence_and_foreign_identity_fail(draft_system):
    _, service, _, draft = draft_system
    service.apply(command(draft, 1, key="same"))
    with pytest.raises(LayoutDraftConflict, match="reused"):
        service.apply(command(draft, 1, key="same", target={"x_nm": 9, "y_nm": 9}))
    with pytest.raises(LayoutDraftConflict, match="out of order"):
        service.apply(command(draft, 3))
    foreign = command(service.get(draft.context.identity.draft_id), 2).model_copy(update={
        "identity": draft.context.identity.model_copy(update={"base_revision_id": "other"}),
    })
    with pytest.raises(LayoutDraftConflict, match="stale or mismatched"):
        service.apply(foreign)


def test_undo_redo_are_exact_replay_and_rotation_is_bounded(draft_system):
    _, service, _, draft = draft_system
    moved = service.apply(command(draft, 1))
    undone = service.apply(command(moved, 2, "undo", target_sequence=1))
    assert dict(undone.placements) == dict(undone.base_placements)
    assert not {"circuit", "semantic", "schematic", "erc"}.intersection(
        item.value for item in undone.invalidated
    )
    redone = service.apply(command(undone, 3, "redo", target_sequence=1))
    assert dict(redone.placements) == dict(moved.placements)
    with pytest.raises(LayoutDraftConflict, match="quarter turns"):
        service.apply(command(redone, 4, target={
            "x_nm": 0, "y_nm": 0, "rotation_mdeg": 45_000,
        }))


def test_nonplacement_commands_cannot_change_parts_pads_or_nets(draft_system):
    _, service, _, draft = draft_system
    with pytest.raises(LayoutDraftConflict, match="existing-component"):
        service.apply(command(draft, 1, "add_supported", role_id="sensor",
                              catalog_part={"id": "BME280", "sha256": digest("part")},
                              requested_location={"x_nm": 0, "y_nm": 0}))


def test_discard_restores_base_and_never_writes_a_revision(draft_system):
    store, service, _, draft = draft_system
    moved = service.apply(command(draft, 1))
    discarded = service.apply(command(moved, 2, "discard_draft"))
    assert discarded.context.status == "DISCARDED"
    assert discarded.placements == discarded.base_placements
    assert discarded.invalidated == ()
    assert len(store.get(draft.context.identity.project_id)["revisions"]) == 1
    with pytest.raises(LayoutDraftConflict, match="nonempty open"):
        service.commit(draft.context.identity.draft_id)


def test_commit_appends_revision_with_exact_lineage_and_preserves_base(draft_system):
    store, service, snapshot, draft = draft_system
    base = store.revision(snapshot.project_id, snapshot.revision_id)
    moved = service.apply(command(draft, 1))
    revision = service.commit(draft.context.identity.draft_id)
    assert revision["number"] == 2 and revision["brief"] == base["brief"]
    assert store.revision(snapshot.project_id, snapshot.revision_id) == base
    lineage = revision["preview"]["layout_draft"]
    assert lineage["base_revision_id"] == snapshot.revision_id
    assert lineage["base_artifact_sha256"] == snapshot.source_bytes_sha256
    assert lineage["draft_sha256"] == moved.content_sha256
    assert lineage["electrical_identity"] == {
        "circuit_sha256": snapshot.circuit_sha256, "parts_sha256": snapshot.parts_sha256,
        "nets_sha256": snapshot.nets_sha256, "pads_sha256": snapshot.pads_sha256,
    }
    assert service.get(draft.context.identity.draft_id).context.status == "COMMITTED"


def test_newer_revision_makes_commit_stale(draft_system):
    store, service, snapshot, draft = draft_system
    service.apply(command(draft, 1))
    store.save_revision({"project_name": "Concurrent"}, digest("other"), {},
                        project_id=snapshot.project_id)
    with pytest.raises(LayoutDraftConflict, match="newer revision"):
        service.commit(draft.context.identity.draft_id)


def test_historical_revision_cannot_open_and_source_byte_substitution_fails(draft_system):
    store, service, snapshot, draft = draft_system
    store.save_revision({"project_name": "Concurrent"}, digest("other"), {},
                        project_id=snapshot.project_id)
    with pytest.raises(LayoutDraftConflict, match="stale"):
        LayoutDraftService(store).open(snapshot)
    service._source_bytes[draft.context.identity.draft_id] = b"substituted"
    with pytest.raises(LayoutDraftConflict, match="bytes changed"):
        service.apply(command(draft, 1))
