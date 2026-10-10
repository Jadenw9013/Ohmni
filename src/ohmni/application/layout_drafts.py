"""Authoritative existing-component layout drafts for CAB-T05.

Only placement and quarter-turn rotation are editable. Commands replay from an
immutable base snapshot; no command can alter parts, pads, nets or source bytes.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from ..domain.component_atlas import (
    BoardDraft,
    DiscardDraft,
    DraftCommandRecord,
    DraftCommandRequest,
    DraftContext,
    DraftIdentity,
    MoveExisting,
    Redo,
    Undo,
    check_request_binding,
    invalidated_stages,
)


@dataclass(frozen=True)
class BaseBoardSnapshot:
    project_id: str
    revision_id: str
    revision_number: int
    source_bytes: bytes
    catalog_snapshot_sha256: str
    circuit_sha256: str
    parts_sha256: str
    nets_sha256: str
    pads_sha256: str
    placements: dict

    @property
    def source_bytes_sha256(self) -> str:
        return hashlib.sha256(self.source_bytes).hexdigest()


class LayoutDraftConflict(ValueError):
    """The command or commit no longer applies to the authoritative base."""


class LayoutDraftService:
    """Server-owned draft registry; persistence remains in immutable revisions."""

    def __init__(self, project_store, *, workspace_id: str = "local"):
        self.project_store = project_store
        self.workspace_id = workspace_id
        self._drafts: dict[str, BoardDraft] = {}
        self._source_bytes: dict[str, bytes] = {}

    def open(self, snapshot: BaseBoardSnapshot) -> BoardDraft:
        project = self.project_store.get(snapshot.project_id)
        revision = None if project is None else project["revisions"][-1]
        if (revision is None or revision["revision_id"] != snapshot.revision_id
                or revision["number"] != snapshot.revision_number):
            raise LayoutDraftConflict("Base revision is absent or stale")
        refs = tuple(sorted(snapshot.placements))
        identity = DraftIdentity(
            draft_id=uuid.uuid4().hex[:16], project_id=snapshot.project_id,
            base_revision_id=snapshot.revision_id,
            base_artifact_sha256=snapshot.source_bytes_sha256,
            catalog_snapshot_sha256=snapshot.catalog_snapshot_sha256,
        )
        context = DraftContext(identity=identity, owner_workspace_id=self.workspace_id,
                               next_sequence=1, status="OPEN", existing_components=refs)
        placements = tuple((ref, snapshot.placements[ref]) for ref in refs)
        draft = BoardDraft(
            context=context, source_revision_number=snapshot.revision_number,
            source_bytes_sha256=snapshot.source_bytes_sha256,
            circuit_sha256=snapshot.circuit_sha256, parts_sha256=snapshot.parts_sha256,
            nets_sha256=snapshot.nets_sha256, pads_sha256=snapshot.pads_sha256,
            base_placements=placements, placements=placements,
        )
        self._drafts[identity.draft_id] = draft
        self._source_bytes[identity.draft_id] = bytes(snapshot.source_bytes)
        return draft

    def get(self, draft_id: str) -> BoardDraft:
        try:
            return self._drafts[draft_id]
        except KeyError:
            raise LayoutDraftConflict("Unknown layout draft") from None

    def apply(self, request: DraftCommandRequest) -> BoardDraft:
        request = DraftCommandRequest.model_validate(request)
        draft = self.get(request.identity.draft_id)
        request_sha = request.content_sha256
        for record in draft.commands:
            if record.idempotency_key == request.idempotency_key:
                if record.request_sha256 != request_sha:
                    raise LayoutDraftConflict("Idempotency key was reused with another command")
                return draft
        try:
            check_request_binding(request, draft.context, workspace_id=self.workspace_id)
        except ValueError as exc:
            raise LayoutDraftConflict(str(exc)) from exc
        if not isinstance(request.command, (MoveExisting, Undo, Redo, DiscardDraft)):
            raise LayoutDraftConflict("CAB-T05 accepts existing-component placement commands only")
        if isinstance(request.command, MoveExisting) and request.command.target.rotation_mdeg % 90_000:
            raise LayoutDraftConflict("Existing components rotate in quarter turns")
        if isinstance(request.command, (Undo, Redo)):
            target = next((item for item in draft.commands
                           if item.sequence == request.command.target_sequence), None)
            if target is None or not isinstance(target.command, MoveExisting):
                raise LayoutDraftConflict("Undo/redo must target an earlier move")
        record = DraftCommandRecord(
            sequence=request.sequence, idempotency_key=request.idempotency_key,
            request_sha256=request_sha, command=request.command,
        )
        commands = (*draft.commands, record)
        status = "DISCARDED" if isinstance(request.command, DiscardDraft) else "OPEN"
        context = draft.context.model_copy(update={
            "next_sequence": request.sequence + 1, "status": status,
        })
        placements = self._replay(draft.base_placements, commands)
        invalidation_command = request.command
        if isinstance(request.command, (Undo, Redo)):
            invalidation_command = target.command
        invalidated = () if status == "DISCARDED" else invalidated_stages(invalidation_command)
        if not isinstance(request.command, DiscardDraft):
            invalidated = tuple(dict.fromkeys((*draft.invalidated, *invalidated)))
        updated = draft.model_copy(update={
            "context": context, "placements": placements, "commands": commands,
            "invalidated": invalidated,
        })
        self._assert_source_unchanged(updated)
        self._drafts[request.identity.draft_id] = updated
        return updated

    @staticmethod
    def _replay(base, commands):
        undone: set[int] = set()
        for record in commands:
            if isinstance(record.command, Undo):
                undone.add(record.command.target_sequence)
            elif isinstance(record.command, Redo):
                undone.discard(record.command.target_sequence)
            elif isinstance(record.command, DiscardDraft):
                return base
        placements = dict(base)
        for record in commands:
            if isinstance(record.command, MoveExisting) and record.sequence not in undone:
                placements[record.command.component_ref] = record.command.target
        return tuple((ref, placements[ref]) for ref in sorted(placements))

    def commit(self, draft_id: str) -> dict:
        draft = self.get(draft_id)
        if draft.context.status != "OPEN" or not draft.commands:
            raise LayoutDraftConflict("Only a nonempty open draft can be committed")
        project = self.project_store.get(draft.context.identity.project_id)
        if project is None or project["revisions"][-1]["revision_id"] != draft.context.identity.base_revision_id:
            raise LayoutDraftConflict("Base revision is stale; the project has a newer revision")
        self._assert_source_unchanged(draft)
        base = project["revisions"][-1]
        preview = dict(base["preview"])
        preview["layout_draft"] = {
            "base_revision_id": draft.context.identity.base_revision_id,
            "base_artifact_sha256": draft.context.identity.base_artifact_sha256,
            "draft_sha256": draft.content_sha256,
            "placements": {ref: target.model_dump(mode="json") for ref, target in draft.placements},
            "invalidated": [stage.value for stage in draft.invalidated],
            "electrical_identity": {
                "circuit_sha256": draft.circuit_sha256, "parts_sha256": draft.parts_sha256,
                "nets_sha256": draft.nets_sha256, "pads_sha256": draft.pads_sha256,
            },
        }
        saved = self.project_store.save_revision(
            base["brief"], base["brief_fingerprint"], preview,
            project_id=draft.context.identity.project_id,
        )
        if saved is None:
            raise LayoutDraftConflict("Could not append the layout revision")
        committed = draft.model_copy(update={
            "context": draft.context.model_copy(update={"status": "COMMITTED"}),
        })
        self._drafts[draft_id] = committed
        return saved["revisions"][-1]

    def _assert_source_unchanged(self, draft: BoardDraft) -> None:
        source = self._source_bytes[draft.context.identity.draft_id]
        if hashlib.sha256(source).hexdigest() != draft.source_bytes_sha256:
            raise LayoutDraftConflict("Base artifact bytes changed during the draft")


__all__ = ["BaseBoardSnapshot", "LayoutDraftConflict", "LayoutDraftService"]
