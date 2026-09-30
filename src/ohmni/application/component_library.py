"""Read-only learning projection of server-owned catalog and visual snapshots.

No admission, source verification, model execution, native CAD or project writes.
Catalog claims are reported as such; a footprint name is not footprint geometry.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal
from urllib.parse import parse_qsl

from pydantic import Field

from ..domain.component import ComponentSpec
from ..domain.component_atlas import (
    AtlasContract,
    ComponentReferenceRecord,
    Digest,
    EligibilityDecision,
    Identifier,
    Text,
    VisualAssetRecord,
    VisualDimensions,
    current_library_eligibility,
)


def _sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


class VisualBinding(AtlasContract):
    part_id: Identifier
    package: Text
    family: Identifier


class VisualSample(AtlasContract):
    family: Identifier
    dimensions: VisualDimensions
    contact_basis: Literal["NONE", "ILLUSTRATION_PARAMETERS"]


class VisualManifest(AtlasContract):
    schema_version: Literal[1]
    asset_version: Identifier
    samples: tuple[VisualSample, ...]
    bindings: tuple[VisualBinding, ...]


class LibraryVariant(AtlasContract):
    record: ComponentReferenceRecord
    eligibility: EligibilityDecision
    catalog_footprint_name: Text | None
    catalog_hand_solderable: bool
    visual_status: Literal["ILLUSTRATIVE", "MISSING_MODEL"]
    visual_note: Text


class LibraryItem(AtlasContract):
    part_id: Identifier
    description: Annotated[str, Field(max_length=4000)]
    variants: tuple[LibraryVariant, ...]


class LibraryQueryError(ValueError):
    """Invalid bounded query; callers expose a fixed error code only."""


class LibrarySnapshotConflict(ValueError):
    """The requested catalog/visual snapshot has changed."""


class LibraryQuery(AtlasContract):
    q: Annotated[str, Field(max_length=120)] = ""
    category: Identifier | None = None
    status: Literal["learn", "restricted", "all"] = "learn"
    offset: Annotated[int, Field(strict=True, ge=0, le=100_000)] = 0
    limit: Annotated[int, Field(strict=True, ge=1, le=50)] = 12
    snapshot: Digest | None = None

    @classmethod
    def from_url(cls, query: str) -> LibraryQuery:
        if len(query) > 2048:
            raise LibraryQueryError
        try:
            pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True,
                              errors="strict", max_num_fields=6)
            values = dict(pairs)
            if len(values) != len(pairs):
                raise ValueError
            for key in ("offset", "limit"):
                if key in values:
                    if not values[key].isascii() or not values[key].isdigit():
                        raise ValueError
                    values[key] = int(values[key])
            return cls.model_validate(values)
        except ValueError:
            raise LibraryQueryError from None


class ComponentLibrary(AtlasContract):
    snapshot_sha256: Digest
    source_hashes: tuple[tuple[str, str], ...]
    items: tuple[LibraryItem, ...]

    def page(self, query: LibraryQuery) -> dict:
        query = LibraryQuery.model_validate(query)
        if query.offset and query.snapshot is None:
            raise LibraryQueryError
        if query.snapshot is not None and query.snapshot != self.snapshot_sha256:
            raise LibrarySnapshotConflict
        needle = query.q.strip().casefold()
        matches = []
        for item in self.items:
            variants = tuple(v for v in item.variants
                             if (query.category is None or v.record.category == query.category)
                             and (query.status == "all" or
                                  (v.eligibility.eligibility == "LEARN_ONLY") == (query.status == "learn")))
            searchable = " ".join([item.part_id, item.description] +
                                  [f"{v.record.category} {v.record.package_variant}" for v in variants])
            if variants and needle in searchable.casefold():
                matches.append(item.model_copy(update={"variants": variants}))
        end = query.offset + query.limit
        return {"snapshot_sha256": self.snapshot_sha256,
                "total": len(matches), "offset": query.offset, "limit": query.limit,
                "next_offset": end if end < len(matches) else None,
                "items": [item.model_dump(mode="json") for item in matches[query.offset:end]],
                "notice": "Learning library. Illustrations and catalog labels do not admit parts to a design."}


def build_component_library(parts: list[ComponentSpec], visual_sources: dict[str, bytes]) -> ComponentLibrary:
    """Freeze normalized catalog contents and the exact served renderer sources.

    The manifest is local, reviewed application configuration, never user input.
    Missing mappings fall back explicitly. Invalid manifest data fails startup.
    """
    required = {"component-visuals.json", "visual-assets.js", "vendor/three.module.js", "vendor/three.core.min.js"}
    if set(visual_sources) != required or any(type(data) is not bytes or not data for data in visual_sources.values()):
        raise ValueError("Incomplete visual source snapshot")
    manifest = VisualManifest.model_validate_json(visual_sources["component-visuals.json"])
    samples = {sample.family: sample for sample in manifest.samples}
    bindings = {(b.part_id, b.package): b.family for b in manifest.bindings}
    if len(samples) != len(manifest.samples) or len(bindings) != len(manifest.bindings):
        raise ValueError("Duplicate visual manifest key")
    if set(bindings.values()) - samples.keys():
        raise ValueError("Unknown visual sample")
    # Copies detach the snapshot from the mutable seed catalog's lists/dicts.
    normalized = sorted((part.model_dump(mode="json") for part in parts), key=lambda p: p["part_id"])
    if len({part["part_id"] for part in normalized}) != len(normalized):
        raise ValueError("Duplicate catalog part")
    source_hashes = tuple(sorted((name, hashlib.sha256(data).hexdigest())
                                 for name, data in visual_sources.items()))
    visual_hash = _sha(source_hashes)
    items = []
    for raw in normalized:
        part = ComponentSpec.model_validate(raw)
        catalog_ref = {"id": part.part_id, "sha256": _sha(raw)}
        variants = []
        for package in sorted(part.packages, key=lambda p: p.name):
            family = bindings.get((part.part_id, package.name))
            sample = samples.get(family)
            visual = None
            if sample is not None:
                visual = VisualAssetRecord(
                    asset={"id": f"ohmni-procedural/{family}@{manifest.asset_version}", "sha256": visual_hash},
                    family=family, representation_grade="ILLUSTRATIVE_FAMILY",
                    origin_policy="ILLUSTRATION_ORIGIN", dimensions=sample.dimensions,
                    contact_basis=sample.contact_basis,
                    provenance={"source": "apps/web/visual-assets.js + component-visuals.json",
                                "license": "Repository license unspecified",
                                "attribution": "Ohmni original procedural illustrations"},
                    limitations=("Artistic sample dimensions; not measured package dimensions.",
                                 "No verified footprint, pin map, electrical behavior or manufacturing claim.",
                                 "Contacts are omitted or illustrative; this is not a pad preview."))
            record = ComponentReferenceRecord(
                catalog_part=catalog_ref, display_name=part.mpn or part.part_id,
                category=part.category.value, package_variant=package.name,
                lifecycle_status="SEED", visual=visual,
                evidence_summary=(f"{len(part.evidence)} catalog evidence records; not reverified by this library.",
                                  "Package and assembly guidance are catalog-reported.",
                                  "Electrical admission and dynamic project integration are pending."),
                assembly_guidance_status="CATALOG_REPORTED")
            variants.append(LibraryVariant(
                record=record, eligibility=current_library_eligibility(record),
                catalog_footprint_name=package.kicad_footprint,
                catalog_hand_solderable=package.hand_solderable,
                visual_status="ILLUSTRATIVE" if visual else "MISSING_MODEL",
                visual_note="Illustrative family; not a verified package model." if visual
                else "No model is bound to this exact catalog package; use the text details."))
        items.append(LibraryItem(part_id=part.part_id, description=part.description, variants=tuple(variants)))
    items = tuple(items)
    snapshot = _sha({"schema_version": 1, "catalog": normalized, "sources": source_hashes,
                     "items": [item.model_dump(mode="json") for item in items]})
    return ComponentLibrary(snapshot_sha256=snapshot, source_hashes=source_hashes, items=items)
