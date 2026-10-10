"""One immutable design catalog assembled from seed and admitted revisions."""

from __future__ import annotations

import hashlib
import json

from ..adapters import PartNotFoundError
from ..domain.component import ComponentSpec
from .component_store import ComponentStore
from .loader import JsonPartCatalog


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


class ActivePartCatalog:
    """Startup snapshot of seed parts plus non-revoked CS-T07 admissions."""

    def __init__(self, base: JsonPartCatalog, store: ComponentStore):
        parts = {part.part_id: part.model_copy(deep=True) for part in base.all_parts()}
        bindings: dict[str, str] = {}
        for revision, spec in store.active_specs():
            if spec.part_id in parts:
                raise ValueError(f"active component shadows catalog part {spec.part_id}")
            parts[spec.part_id] = spec.model_copy(deep=True)
            bindings[spec.part_id] = revision.revision_id
        self._parts = parts
        self.revision_bindings = dict(sorted(bindings.items()))
        self.snapshot_hash = _hash({
            "parts": [parts[key].model_dump(mode="json") for key in sorted(parts)],
            "active_revisions": self.revision_bindings,
        })

    def get(self, part_id: str) -> ComponentSpec | None:
        part = self._parts.get(part_id)
        return None if part is None else part.model_copy(deep=True)

    def require(self, part_id: str) -> ComponentSpec:
        part = self.get(part_id)
        if part is None:
            raise PartNotFoundError(part_id)
        return part

    def all_parts(self) -> list[ComponentSpec]:
        return [self._parts[key].model_copy(deep=True) for key in sorted(self._parts)]


__all__ = ["ActivePartCatalog"]
