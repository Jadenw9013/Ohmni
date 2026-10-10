"""Immutable atlas descriptions and untrusted board-edit requests (CAB-T01).

These contracts do not admit parts, validate geometry, or persist edits. A
visual revision is a display dependency, never electrical authority. Future
handlers must resolve catalog/board revisions from server-owned snapshots.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=500)]
Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/+@()-]{0,159}$")]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
Coordinate = Annotated[int, Field(strict=True, ge=-500_000_000, le=500_000_000)]
Dimension = Annotated[int, Field(strict=True, gt=0, le=500_000_000)]
Sequence = Annotated[int, Field(strict=True, ge=1, le=2_147_483_647)]
Rotation = Annotated[int, Field(strict=True, ge=0, lt=360_000)]


class AtlasContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")

    def model_copy(self, *, update=None, deep=False):
        """Validate copies too: a changed field cannot retain a stale invariant."""
        values = self.model_dump(mode="python")
        values.update(update or {})
        return type(self).model_validate(values)

    @property
    def content_sha256(self) -> str:
        """Content identity only; this hash does not establish source truth."""
        encoded = json.dumps(self.model_dump(mode="json"), sort_keys=True,
                             separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class RevisionRef(AtlasContract):
    id: Identifier
    sha256: Digest


class VisualDimensions(AtlasContract):
    width_nm: Dimension
    depth_nm: Dimension
    height_nm: Dimension
    basis: Literal["ARTISTIC_SAMPLE", "PACKAGE_APPROXIMATION"]
    # Accurate mechanical measurements will need a source verifier, not a label.


class VisualProvenance(AtlasContract):
    source: Text
    license: Text
    attribution: Text
    redistribution: Literal["UNRESOLVED", "REVIEWED"] = "UNRESOLVED"
    license_review: RevisionRef | None = None

    @model_validator(mode="after")
    def review_is_explicit(self) -> Self:
        if (self.redistribution == "REVIEWED") != (self.license_review is not None):
            raise ValueError("Reviewed redistribution requires an exact license review reference")
        return self


class VisualAssetRecord(AtlasContract):
    asset: RevisionRef
    family: Identifier
    representation_grade: Literal["ILLUSTRATIVE_FAMILY", "ARTIFACT_BOUND"]
    format: Literal["PROCEDURAL_THREE"] = "PROCEDURAL_THREE"
    units: Literal["mm"] = "mm"
    up_axis: Literal["z"] = "z"
    contact_plane_nm: Annotated[int, Field(strict=True, ge=0, le=0)] = 0
    origin_policy: Literal["ILLUSTRATION_ORIGIN", "FOOTPRINT_ORIGIN"]
    dimensions: VisualDimensions
    contact_basis: Literal["NONE", "ILLUSTRATION_PARAMETERS", "SOURCE_PADS"]
    footprint: RevisionRef | None = None
    provenance: VisualProvenance
    limitations: Annotated[tuple[Text, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def exact_contact_binding(self) -> Self:
        bound = self.representation_grade == "ARTIFACT_BOUND"
        if bound != (self.footprint is not None):
            raise ValueError("Artifact-bound visuals require an exact footprint revision")
        if bound and (self.contact_basis != "SOURCE_PADS" or self.origin_policy != "FOOTPRINT_ORIGIN"):
            raise ValueError("Artifact-bound contacts must use source pads and the footprint origin")
        if not bound and (self.contact_basis == "SOURCE_PADS" or self.origin_policy != "ILLUSTRATION_ORIGIN"):
            raise ValueError("Illustrations cannot claim source-pad binding")
        return self


class VisualTransform(AtlasContract):
    x_nm: Coordinate = 0
    y_nm: Coordinate = 0
    z_nm: Coordinate = 0
    rotation_mdeg: Rotation = 0
    # Unit scaling is deliberately absent: the asset has a normalized unit system.


class ComponentReferenceRecord(AtlasContract):
    """Server projection of a catalog record; never accepted in an edit request."""

    catalog_part: RevisionRef
    display_name: Text
    category: Identifier
    package_variant: Text
    footprint: RevisionRef | None = None
    pin_map: RevisionRef | None = None
    visual: VisualAssetRecord | None = None
    visual_transform: VisualTransform = VisualTransform()
    lifecycle_status: Literal["SEED", "QUARANTINED", "ACTIVE", "REVOKED", "UNSUPPORTED"]
    evidence_summary: Annotated[tuple[Text, ...], Field(min_length=1, max_length=40)]
    supported_roles: Annotated[tuple[Identifier, ...], Field(max_length=40)] = ()
    supported_project_families: Annotated[tuple[Identifier, ...], Field(max_length=20)] = ()
    assembly_guidance_status: Literal["UNKNOWN", "ASSUMED", "CATALOG_REPORTED"] = "UNKNOWN"

    @model_validator(mode="after")
    def visual_matches_footprint(self) -> Self:
        if self.visual and self.visual.footprint and self.visual.footprint != self.footprint:
            raise ValueError("Visual and component footprint revisions differ")
        return self


class PlacementTarget(AtlasContract):
    x_nm: Coordinate
    y_nm: Coordinate
    rotation_mdeg: Rotation = 0
    side: Literal["F.Cu", "B.Cu"] = "F.Cu"


class MoveExisting(AtlasContract):
    kind: Literal["move_existing"]
    component_ref: Identifier
    target: PlacementTarget


class AddSupported(AtlasContract):
    kind: Literal["add_supported"]
    role_id: Identifier
    catalog_part: RevisionRef
    requested_location: PlacementTarget


class RemoveDraftAddition(AtlasContract):
    kind: Literal["remove_draft_addition"]
    draft_component_id: Identifier


class AddMountingFeature(AtlasContract):
    kind: Literal["add_mounting_feature"]
    feature: RevisionRef
    target: PlacementTarget


class Point(AtlasContract):
    x_nm: Coordinate
    y_nm: Coordinate


class SetBoardKeepout(AtlasContract):
    kind: Literal["set_board_keepout"]
    keepout_id: Identifier
    points: Annotated[tuple[Point, ...], Field(min_length=3, max_length=128)]
    # Polygon validity and applicability require the later physical verifier.


class Undo(AtlasContract):
    kind: Literal["undo"]
    target_sequence: Sequence


class Redo(AtlasContract):
    kind: Literal["redo"]
    target_sequence: Sequence


class DiscardDraft(AtlasContract):
    kind: Literal["discard_draft"]


DraftCommand = Annotated[
    MoveExisting | AddSupported | RemoveDraftAddition | AddMountingFeature
    | SetBoardKeepout | Undo | Redo | DiscardDraft,
    Field(discriminator="kind"),
]


class DraftIdentity(AtlasContract):
    draft_id: Identifier
    project_id: Identifier
    base_revision_id: Identifier
    base_artifact_sha256: Digest
    catalog_snapshot_sha256: Digest


class DraftCommandRequest(AtlasContract):
    """Untrusted input: no status, receipt, nets, assets or eligibility fields."""

    identity: DraftIdentity
    sequence: Sequence
    idempotency_key: Identifier
    command: DraftCommand


class DraftContext(AtlasContract):
    """Server-owned context; ownership must be resolved before constructing this.

    No client-provided context may reach a handler. These fields witness a saved
    snapshot, not an authorization system. Persistence and validation are later
    CAB tasks. Schema validity cannot make a draft valid or exportable.
    """

    identity: DraftIdentity
    owner_workspace_id: Identifier
    next_sequence: Sequence
    status: Literal["OPEN", "VALIDATING", "VALID", "INVALID", "COMMITTED", "DISCARDED", "STALE"]
    existing_components: Annotated[tuple[Identifier, ...], Field(max_length=2048)] = ()

    @model_validator(mode="after")
    def unique_refs(self) -> Self:
        if len(set(self.existing_components)) != len(self.existing_components):
            raise ValueError("Existing component references must be unique")
        return self


class DraftCommandRecord(AtlasContract):
    sequence: Sequence
    idempotency_key: Identifier
    request_sha256: Digest
    command: DraftCommand


class BoardDraft(AtlasContract):
    """Server-owned replayable placement draft bound to one immutable revision."""

    context: DraftContext
    source_revision_number: Annotated[int, Field(strict=True, ge=1)]
    source_bytes_sha256: Digest
    circuit_sha256: Digest
    parts_sha256: Digest
    nets_sha256: Digest
    pads_sha256: Digest
    base_placements: Annotated[tuple[tuple[Identifier, PlacementTarget], ...], Field(max_length=2048)]
    placements: Annotated[tuple[tuple[Identifier, PlacementTarget], ...], Field(max_length=2048)]
    commands: Annotated[tuple[DraftCommandRecord, ...], Field(max_length=10000)] = ()
    invalidated: tuple[InvalidatedStage, ...] = ()

    @model_validator(mode="after")
    def placement_refs_are_exact(self) -> Self:
        base = [ref for ref, _ in self.base_placements]
        current = [ref for ref, _ in self.placements]
        if len(base) != len(set(base)) or len(current) != len(set(current)):
            raise ValueError("Draft placement references must be unique")
        if tuple(sorted(base)) != tuple(sorted(self.context.existing_components)):
            raise ValueError("Base placements must cover the server-owned components exactly")
        if sorted(base) != sorted(current):
            raise ValueError("A layout draft cannot add or remove components")
        return self


class Eligibility(StrEnum):
    LEARN_ONLY = "LEARN_ONLY"
    PLACEMENT_ELIGIBLE = "PLACEMENT_ELIGIBLE"
    DESIGN_ELIGIBLE = "DESIGN_ELIGIBLE"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"
    UNSUPPORTED = "UNSUPPORTED"


class EligibilityDecision(AtlasContract):
    eligibility: Eligibility
    reason: Text


def current_library_eligibility(record: ComponentReferenceRecord) -> EligibilityDecision:
    """Fail closed until CS-T07/T08 admission is wired in; appearance is irrelevant.

    No provider, UI-supplied status, source receipt, or asset grade can switch on
    design insertion here. Existing-part placement eligibility is contextual and
    must be checked against the current board by the later draft service.
    """
    record = ComponentReferenceRecord.model_validate(record)
    if record.lifecycle_status in {"QUARANTINED", "REVOKED", "UNSUPPORTED"}:
        return EligibilityDecision(eligibility=Eligibility(record.lifecycle_status),
                                   reason="This catalog revision is not eligible for project edits.")
    return EligibilityDecision(eligibility=Eligibility.LEARN_ONLY,
                               reason="Component addition awaits the electrical admission and project integration gates.")


class InvalidatedStage(StrEnum):
    REQUIREMENTS = "requirements"
    CIRCUIT = "circuit"
    SEMANTIC = "semantic"
    SCHEMATIC = "schematic"
    ERC = "erc"
    PLACEMENT = "placement"
    PHYSICAL = "physical"
    ROUTING = "routing"
    PCB = "pcb"
    DRC = "drc"
    BOM = "bom"
    ECONOMICS = "economics"
    MANUFACTURING = "manufacturing"
    PROJECTION = "projection"
    BUILD_PACKAGE = "build_package"


def invalidated_stages(command: DraftCommand) -> tuple[InvalidatedStage, ...]:
    """Conservative dependency contract; this does not mark any stage successful.

    Undo/redo invalidate all stages until command replay computes an exact diff.
    Discard never touches the base revision or restores a stale PASS.
    """
    if isinstance(command, DiscardDraft):
        return ()
    if isinstance(command, (MoveExisting, AddMountingFeature, SetBoardKeepout)):
        return tuple(InvalidatedStage(s) for s in (
            "placement", "physical", "routing", "pcb", "drc", "bom", "economics",
            "manufacturing", "projection", "build_package",
        ))
    if isinstance(command, (AddSupported, RemoveDraftAddition, Undo, Redo)):
        return tuple(InvalidatedStage)
    raise TypeError("Unsupported draft command")


def check_request_binding(request: DraftCommandRequest, context: DraftContext,
                          *, workspace_id: str) -> None:
    """Reject stale/foreign commands before later geometry or electrical checks.

    This is a precondition, never permission to execute. Future handlers must
    resolve idempotent retries from persisted request hashes BEFORE this check,
    and reject the same key with a different payload. No mutation API exists yet.
    """
    request = DraftCommandRequest.model_validate(request)
    context = DraftContext.model_validate(context)
    if workspace_id != context.owner_workspace_id:
        raise ValueError("Draft belongs to another workspace")
    if request.identity != context.identity:
        raise ValueError("Draft or source revision is stale or mismatched")
    if context.status not in {"OPEN", "INVALID", "VALID"}:
        raise ValueError("Draft cannot be edited in its current state")
    if request.sequence != context.next_sequence:
        raise ValueError("Draft command sequence is stale or out of order")
    if isinstance(request.command, MoveExisting) and request.command.component_ref not in context.existing_components:
        raise ValueError("Component is absent from the server-owned base board")
    if isinstance(request.command, (Undo, Redo)) and request.command.target_sequence >= request.sequence:
        raise ValueError("Undo/redo must reference an earlier command")


BoardDraft.model_rebuild()
