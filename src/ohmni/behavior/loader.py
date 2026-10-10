"""Validated loader for generated behavior records."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from .models import (
    BehaviorClassRecord,
    BehaviorEntryRecord,
    BehaviorManifest,
    CatalogPartBinding,
    SourceAnchor,
)

DATA_DIR = Path(__file__).parent / "data"


class BehaviorRegistryError(ValueError):
    """Generated behavior data is incomplete, malformed, or detached from its evidence."""


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BehaviorRegistryError(f"cannot load behavior record {path}: {exc}") from exc


def _safe_local_path(root: Path, relative: str) -> Path:
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise BehaviorRegistryError(f"behavior evidence path escapes repository: {relative!r}")
    resolved_root = root.resolve()
    resolved = (resolved_root / Path(*candidate.parts)).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise BehaviorRegistryError(f"behavior evidence path escapes repository: {relative!r}")
    return resolved


def _validate_anchor(root: Path, anchor: SourceAnchor, context: str) -> None:
    path = _safe_local_path(root, anchor.document)
    if not path.is_file():
        raise BehaviorRegistryError(f"{context} points to missing source {anchor.document}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != anchor.document_sha256:
        raise BehaviorRegistryError(
            f"{context} source hash changed for {anchor.document}; regenerate behavior records"
        )


def validate_registry_references(
    root: Path,
    classes: dict[str, BehaviorClassRecord],
    entries: dict[str, BehaviorEntryRecord],
    bindings: dict[str, CatalogPartBinding],
) -> None:
    """Require every generated pointer to resolve inside the repository."""
    for behavior_id, record in classes.items():
        _validate_anchor(root, record.source, behavior_id)
        for bench in record.benches:
            path = _safe_local_path(root, bench.file)
            if not path.is_file():
                raise BehaviorRegistryError(
                    f"{behavior_id}/{bench.bench_id} points to missing bench {bench.file}"
                )
    for entry_id, record in entries.items():
        _validate_anchor(root, record.source, entry_id)
        if record.research is not None:
            research = record.research
            if research.entry_id != entry_id:
                raise BehaviorRegistryError(f"{entry_id} has research for {research.entry_id}")
            _validate_anchor(root, research.source, f"{entry_id} research")
            urls = {citation.url for citation in research.documents if citation.url}
            for fact in research.field_updates:
                if not set(fact.sources) <= urls:
                    raise BehaviorRegistryError(f"{entry_id}/{fact.field} cites an undeclared document")
            for receipt in research.bench_results:
                if not _safe_local_path(root, f"out/component-behavior/run/{receipt}").is_file():
                    raise BehaviorRegistryError(f"{entry_id} points to missing research bench {receipt}")
        for behavior_id, relative in zip(
            record.behavior_class_ids, record.class_record_paths, strict=True
        ):
            if behavior_id not in classes:
                raise BehaviorRegistryError(f"{entry_id} references missing class {behavior_id}")
            if not _safe_local_path(root, relative).is_file():
                raise BehaviorRegistryError(f"{entry_id} points to missing class record {relative}")
        for binding_id in record.catalog_binding_ids:
            if binding_id not in bindings:
                raise BehaviorRegistryError(f"{entry_id} references missing binding {binding_id}")
    for part_id, binding in bindings.items():
        _validate_anchor(root, binding.source, f"binding {part_id}")
        for entry_id in binding.entry_ids:
            if entry_id not in entries:
                raise BehaviorRegistryError(f"binding {part_id} references missing entry {entry_id}")


class BehaviorRegistry:
    """In-memory view of the generated class, entry, and catalog-binding records."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        repo_root: Path | None = None,
        validate_references: bool = True,
    ) -> None:
        self.directory = directory or DATA_DIR
        self.repo_root = repo_root
        try:
            self.manifest = BehaviorManifest.model_validate(_json(self.directory / "manifest.json"))
            self.classes = self._load_records("classes", BehaviorClassRecord, "behavior_id")
            self.entries = self._load_records("entries", BehaviorEntryRecord, "entry_id")
            self.bindings = self._load_records("bindings", CatalogPartBinding, "part_id")
        except ValidationError as exc:
            raise BehaviorRegistryError(f"invalid behavior registry: {exc}") from exc
        if len(self.classes) != self.manifest.class_count:
            raise BehaviorRegistryError("behavior class count differs from manifest")
        if len(self.entries) != self.manifest.entry_count:
            raise BehaviorRegistryError("behavior entry count differs from manifest")
        if len(self.bindings) != self.manifest.binding_count:
            raise BehaviorRegistryError("behavior binding count differs from manifest")
        resolution_ids = [item.resolution_id for item in self.manifest.resolutions]
        if len(resolution_ids) != len(set(resolution_ids)):
            raise BehaviorRegistryError("duplicate Stage 1 resolution ID in manifest")
        known_resolutions = set(resolution_ids)
        for entry in self.entries.values():
            missing = set(entry.resolution_ids) - known_resolutions
            if missing:
                raise BehaviorRegistryError(
                    f"{entry.entry_id} references missing resolutions {sorted(missing)}"
                )
        if validate_references:
            root = repo_root or _find_repo_root(self.directory)
            self.repo_root = root
            validate_registry_references(root, self.classes, self.entries, self.bindings)
            for resolution in self.manifest.resolutions:
                _validate_anchor(root, resolution.source, resolution.resolution_id)
                missing = set(resolution.entry_ids) - set(self.entries)
                if missing:
                    raise BehaviorRegistryError(
                        f"{resolution.resolution_id} references missing entries {sorted(missing)}"
                    )

    def _load_records(self, child: str, model, key: str) -> dict:
        directory = self.directory / child
        if not directory.is_dir():
            raise BehaviorRegistryError(f"behavior registry directory missing: {directory}")
        records = {}
        for path in sorted(directory.glob("*.json")):
            record = model.model_validate(_json(path))
            identity = getattr(record, key)
            if identity in records:
                raise BehaviorRegistryError(f"duplicate {key} {identity!r}")
            records[identity] = record
        return records

    def entry(self, entry_id: str) -> BehaviorEntryRecord:
        try:
            return self.entries[entry_id]
        except KeyError as exc:
            raise BehaviorRegistryError(f"unknown behavior entry {entry_id!r}") from exc

    def behavior_class(self, behavior_id: str) -> BehaviorClassRecord:
        try:
            return self.classes[behavior_id]
        except KeyError as exc:
            raise BehaviorRegistryError(f"unknown behavior class {behavior_id!r}") from exc

    def binding(self, part_id: str) -> CatalogPartBinding:
        try:
            return self.bindings[part_id]
        except KeyError as exc:
            raise BehaviorRegistryError(f"unknown behavior catalog binding {part_id!r}") from exc


def _find_repo_root(start: Path) -> Path:
    for candidate in [start.resolve(), *start.resolve().parents]:
        if (candidate / "COMPONENT_BEHAVIOR_SPEC.md").is_file():
            return candidate
    raise BehaviorRegistryError("cannot locate repository root for behavior evidence validation")


@lru_cache(maxsize=1)
def default_behavior_registry() -> BehaviorRegistry:
    return BehaviorRegistry()


__all__ = [
    "BehaviorRegistry",
    "BehaviorRegistryError",
    "default_behavior_registry",
    "validate_registry_references",
]
