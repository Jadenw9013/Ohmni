"""JSON-backed part catalog."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from ..adapters import PartNotFoundError
from ..domain.component import ComponentSpec

DATA_DIR = Path(__file__).parent / "data" / "parts"


class JsonPartCatalog:
    """Loads ComponentSpec records from a directory of JSON files.

    Files are validated on load. A malformed catalog entry raises immediately
    rather than degrading into a part with silently missing facts -- a spec with
    absent limits would make every voltage rule report INSUFFICIENT_DATA and
    look like a data problem rather than the authoring bug it is.
    """

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or DATA_DIR
        self._parts: dict[str, ComponentSpec] = {}
        self._load()

    def _load(self) -> None:
        if not self.directory.is_dir():
            raise FileNotFoundError(f"catalog directory not found: {self.directory}")
        for path in sorted(self.directory.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            try:
                spec = ComponentSpec.model_validate(raw)
            except ValidationError as exc:
                raise ValueError(f"invalid catalog entry {path.name}: {exc}") from exc
            if spec.part_id in self._parts:
                raise ValueError(f"duplicate part_id {spec.part_id!r} in {path.name}")
            self._parts[spec.part_id] = spec

    def get(self, part_id: str) -> ComponentSpec | None:
        return self._parts.get(part_id)

    def require(self, part_id: str) -> ComponentSpec:
        spec = self._parts.get(part_id)
        if spec is None:
            raise PartNotFoundError(
                f"part {part_id!r} is not in the catalog; known parts: "
                f"{sorted(self._parts)}"
            )
        return spec

    def all_parts(self) -> list[ComponentSpec]:
        return [self._parts[k] for k in sorted(self._parts)]

    def __len__(self) -> int:
        return len(self._parts)

    def __contains__(self, part_id: object) -> bool:
        return part_id in self._parts


@lru_cache(maxsize=1)
def default_catalog() -> JsonPartCatalog:
    """The bundled catalog. Cached: the files do not change at runtime."""
    return JsonPartCatalog()
