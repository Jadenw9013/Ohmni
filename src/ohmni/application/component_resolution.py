"""Durable component resolution gate before deterministic project synthesis."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..synthesis import SynthesisBrief
from . import database
from .projects import ProjectPipeline


class ResolutionState(StrEnum):
    READY = "READY"
    WAITING_IMPORT = "WAITING_IMPORT"
    RESOLVED = "RESOLVED"


class ComponentResolutionRequest(BaseModel):
    """Exact functional slots that must resolve before architecture/synthesis."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    resolution_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    brief_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_part_ids: tuple[str, ...]
    missing_part_ids: tuple[str, ...]
    catalog_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    active_component_revisions: dict[str, str] = Field(default_factory=dict)
    state: ResolutionState


class ResolutionBypassError(ValueError):
    """Synthesis was attempted without a current successful resolution gate."""


def _requested(brief: SynthesisBrief) -> tuple[str, ...]:
    return tuple(sorted({brief.mcu_part_id, *(slot.part_id for slot in brief.sensors),
                         *(slot.part_id for slot in brief.spi_devices)}))


class ComponentResolutionService:
    """Persist request, pause for import, and resume against one catalog snapshot."""

    def __init__(self, project_store, catalog):
        if not hasattr(catalog, "snapshot_hash"):
            raise TypeError("resolution requires a hash-bound active catalog snapshot")
        self.store = project_store
        self.catalog = catalog

    def request(self, brief: SynthesisBrief, *, project_id: str | None = None
                ) -> ComponentResolutionRequest:
        requested = _requested(brief)
        missing = tuple(part for part in requested if self.catalog.get(part) is None)
        payload = {"brief": brief.model_dump(mode="json"), "requested_part_ids": requested}
        identity = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                             separators=(",", ":")).encode()).hexdigest()[:32]
        result = ComponentResolutionRequest(
            resolution_id=identity, brief_fingerprint=brief.fingerprint,
            requested_part_ids=requested, missing_part_ids=missing,
            catalog_snapshot_sha256=self.catalog.snapshot_hash,
            active_component_revisions=self.catalog.revision_bindings,
            state=ResolutionState.WAITING_IMPORT if missing else ResolutionState.READY,
        )
        envelope = {"brief": payload["brief"], "resolution": result.model_dump(mode="json")}
        now = database.now()
        with self.store._connection() as db:
            prior = db.execute("SELECT request_json FROM component_resolutions WHERE resolution_id=?",
                               (identity,)).fetchone()
            encoded = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
            if prior is not None and prior["request_json"] != encoded:
                raise ResolutionBypassError("resolution identity was reused with different content")
            db.execute(
                "INSERT INTO component_resolutions VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(resolution_id) DO UPDATE SET request_json=excluded.request_json, "
                "state=excluded.state, updated_at=excluded.updated_at",
                (identity, project_id, brief.fingerprint, encoded, result.state.value, now, now),
            )
        return result

    def resume(self, resolution_id: str) -> tuple[SynthesisBrief, ComponentResolutionRequest]:
        with self.store._connection() as db:
            row = db.execute("SELECT request_json FROM component_resolutions WHERE resolution_id=?",
                             (resolution_id,)).fetchone()
        if row is None:
            raise ResolutionBypassError("component resolution request does not exist")
        envelope = json.loads(row["request_json"])
        brief = SynthesisBrief.model_validate(envelope["brief"])
        previous = ComponentResolutionRequest.model_validate(envelope["resolution"])
        missing = tuple(part for part in previous.requested_part_ids if self.catalog.get(part) is None)
        if missing:
            raise ResolutionBypassError("component import is incomplete: " + ", ".join(missing))
        newly_resolved = set(previous.missing_part_ids)
        if not newly_resolved <= set(self.catalog.revision_bindings):
            raise ResolutionBypassError("missing parts must resolve through admitted active revisions")
        resolved = previous.model_copy(update={
            "missing_part_ids": (), "catalog_snapshot_sha256": self.catalog.snapshot_hash,
            "active_component_revisions": self.catalog.revision_bindings,
            "state": ResolutionState.RESOLVED,
        })
        envelope["resolution"] = resolved.model_dump(mode="json")
        with self.store._connection() as db:
            db.execute("UPDATE component_resolutions SET request_json=?, state=?, updated_at=? "
                       "WHERE resolution_id=?", (json.dumps(envelope, sort_keys=True,
                       separators=(",", ":")), resolved.state.value, database.now(), resolution_id))
        return brief, resolved

    def run(self, resolution_id: str, destination: Path):
        brief, resolved = self.resume(resolution_id)
        report = ProjectPipeline(catalog=self.catalog).run(destination, brief)
        report.project.update({"component_resolution_id": resolved.resolution_id,
                               "component_resolution_state": resolved.state.value})
        return report


__all__ = ["ComponentResolutionRequest", "ComponentResolutionService", "ResolutionBypassError",
           "ResolutionState"]
