"""Generate the typed component-behavior registry from approved source inputs.

The Markdown specification remains the source of truth. Checked-in JSON is a
runtime projection and must exactly match this generator. Gap-fill JSON files
carry explicit reviewed corrections without rewriting the research document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ohmni.behavior.models import (
    BehaviorClassRecord,
    BehaviorEntryRecord,
    BehaviorManifest,
    BenchReference,
    CatalogPartBinding,
    SourceAnchor,
    SourceConsistencyIssue,
    Stage1Resolution,
)

SPEC_PATH = "COMPONENT_BEHAVIOR_SPEC.md"
GAPFILL_DIR = "docs/behavior/gapfill"
DATA_DIR = "src/ohmni/behavior/data"
MASTER_ROW = re.compile(
    r"^\| (?P<entry_id>OHM-\d{3}) \| (?P<component>.*?) \| "
    r"(?P<behaviors>.*?) \| (?P<layer>L[123]) \| (?P<fidelity>[^|]+?) \| "
    r"(?P<status>complete|partial|research_required) \| (?P<group>[^|]+?) \|$"
)
YAML_BLOCK = re.compile(r"```yaml\r?\n(?P<body>.*?)\r?\n```", re.DOTALL)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _anchor(relative: str, raw: bytes, line: int, fragment: bytes | None = None) -> SourceAnchor:
    return SourceAnchor(
        document=relative,
        line=line,
        document_sha256=_sha(raw),
        fragment_sha256=_sha(fragment) if fragment is not None else None,
    )


def _basis_values(value: Any) -> list[str]:
    found: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "basis" and child is not None:
                    found.add(str(child))
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return sorted(found)


def _master_entries(text: str, spec_raw: bytes) -> list[BehaviorEntryRecord]:
    entries: list[BehaviorEntryRecord] = []
    spec_hash = _sha(spec_raw)
    for line_number, line in enumerate(text.splitlines(), 1):
        match = MASTER_ROW.match(line)
        if not match:
            continue
        values = match.groupdict()
        behavior_ids = [item.strip() for item in values["behaviors"].split(" + ")]
        entry_number = int(values["entry_id"].split("-")[1])
        if values["layer"] == "L3":
            disposition = "not_simulable"
            simulation_reason = "L3 protocol or firmware behavior requires a higher-layer model."
        elif 103 <= entry_number <= 140:
            disposition = "not_simulable"
            simulation_reason = "A package has no electrical function until a sourced reference part is bound."
        elif values["status"] == "research_required":
            disposition = "not_simulable"
            simulation_reason = "Required electrical or terminal evidence remains unresolved."
        else:
            disposition = "simulable"
            simulation_reason = "The canonical class provides an L1/L2 model; fidelity and assumptions remain explicit."
        entries.append(
            BehaviorEntryRecord(
                entry_id=values["entry_id"],
                component=values["component"],
                behavior_class_ids=behavior_ids,
                layer=values["layer"],
                fidelity=values["fidelity"].strip(),
                status=values["status"],
                group=values["group"].strip(),
                simulation_disposition=disposition,
                simulation_reason=simulation_reason,
                class_record_paths=[
                    f"{DATA_DIR}/classes/{behavior_id}.json" for behavior_id in behavior_ids
                ],
                source=SourceAnchor(
                    document=SPEC_PATH,
                    line=line_number,
                    document_sha256=spec_hash,
                    fragment_sha256=_sha(line.encode("utf-8")),
                ),
            )
        )
    expected = [f"OHM-{index:03d}" for index in range(1, 181)]
    actual = [entry.entry_id for entry in entries]
    if actual != expected:
        raise ValueError(f"master table IDs are not exactly OHM-001..OHM-180: {actual}")
    return entries


def _normalize_bench(behavior_id: str, raw: dict[str, Any]) -> BenchReference:
    if not raw.get("id") or not raw.get("file"):
        raise ValueError(f"{behavior_id} has a bench without id/file: {raw}")
    version = raw.get("ngspice_version")
    return BenchReference(
        bench_id=str(raw["id"]),
        file=f"docs/behavior/{raw['file']}",
        expected=raw.get("expected"),
        measured_in_ngspice=raw.get("measured_in_ngspice"),
        ngspice_version=str(version) if version is not None else None,
    )


def _behavior_classes(text: str, spec_raw: bytes) -> list[BehaviorClassRecord]:
    records: list[BehaviorClassRecord] = []
    seen: set[str] = set()
    for match in YAML_BLOCK.finditer(text):
        body = match.group("body")
        payload = yaml.safe_load(body)
        if not isinstance(payload, dict) or "behavior_id" not in payload:
            continue
        behavior_id = str(payload["behavior_id"])
        if behavior_id in seen:
            raise ValueError(f"duplicate canonical YAML behavior_id {behavior_id}")
        seen.add(behavior_id)
        model = payload.get("model") or {}
        fidelity = model.get("fidelity")
        if fidelity is None:
            raise ValueError(f"{behavior_id} has no model.fidelity")
        line = text.count("\n", 0, match.start("body")) + 1
        records.append(
            BehaviorClassRecord(
                behavior_id=behavior_id,
                applies_to=[str(item) for item in payload.get("applies_to") or []],
                layer=payload["layer"],
                category=str(payload["category"]),
                fidelity=fidelity,
                status=payload["status"],
                basis_values=_basis_values(payload),
                source_refs=payload.get("sources") or [],
                source=_anchor(SPEC_PATH, spec_raw, line, body.encode("utf-8")),
                benches=[
                    _normalize_bench(behavior_id, bench)
                    for bench in (payload.get("bench") or [])
                ],
                canonical_payload=payload,
            )
        )
    if len(records) != 66:
        raise ValueError(f"expected 66 canonical behavior classes, found {len(records)}")
    return records


def _binding_filename(part_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", part_id) + ".json"


def _gapfill_bindings(root: Path) -> list[CatalogPartBinding]:
    directory = root / GAPFILL_DIR
    bindings: list[CatalogPartBinding] = []
    if not directory.is_dir():
        return bindings
    for path in sorted(directory.glob("*.json")):
        raw = path.read_bytes()
        payload = json.loads(raw)
        if payload.get("kind") == "stage1_resolutions":
            continue
        if payload.get("kind") != "catalog_binding":
            raise ValueError(f"unsupported behavior gap-fill kind in {path}")
        binding = dict(payload["binding"])
        binding["source"] = _anchor(path.relative_to(root).as_posix(), raw, 1).model_dump()
        bindings.append(CatalogPartBinding.model_validate(binding))
    ids = [binding.part_id for binding in bindings]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate part_id across behavior gap-fill bindings")
    return bindings


def _gapfill_resolutions(root: Path) -> list[Stage1Resolution]:
    directory = root / GAPFILL_DIR
    resolutions: list[Stage1Resolution] = []
    if not directory.is_dir():
        return resolutions
    for path in sorted(directory.glob("*.json")):
        raw = path.read_bytes()
        payload = json.loads(raw)
        if payload.get("kind") == "catalog_binding":
            continue
        if payload.get("kind") != "stage1_resolutions":
            raise ValueError(f"unsupported behavior gap-fill kind in {path}")
        source = _anchor(path.relative_to(root).as_posix(), raw, 1).model_dump()
        for item in payload.get("resolutions") or []:
            resolution = dict(item)
            resolution["source"] = source
            resolutions.append(Stage1Resolution.model_validate(resolution))
    ids = [resolution.resolution_id for resolution in resolutions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate resolution_id across behavior gap-fill records")
    return resolutions


def build_records(root: Path = ROOT) -> tuple[
    list[BehaviorClassRecord],
    list[BehaviorEntryRecord],
    list[CatalogPartBinding],
    BehaviorManifest,
]:
    spec_file = root / SPEC_PATH
    spec_raw = spec_file.read_bytes()
    text = spec_raw.decode("utf-8")
    classes = _behavior_classes(text, spec_raw)
    entries = _master_entries(text, spec_raw)
    bindings = _gapfill_bindings(root)
    resolutions = _gapfill_resolutions(root)

    class_map = {record.behavior_id: record for record in classes}
    binding_map = {record.part_id: record for record in bindings}
    for index, entry in enumerate(entries):
        missing = set(entry.behavior_class_ids) - set(class_map)
        if missing:
            raise ValueError(f"{entry.entry_id} references missing behavior classes {sorted(missing)}")
        attached = sorted(
            binding.part_id for binding in bindings if entry.entry_id in binding.entry_ids
        )
        resolution_ids = sorted(
            resolution.resolution_id
            for resolution in resolutions
            if entry.entry_id in resolution.entry_ids
        )
        if attached or resolution_ids:
            entries[index] = entry.model_copy(
                update={"catalog_binding_ids": attached, "resolution_ids": resolution_ids}
            )

    issues: list[SourceConsistencyIssue] = []
    for entry in entries:
        for behavior_id in entry.behavior_class_ids:
            if entry.entry_id not in class_map[behavior_id].applies_to:
                issues.append(
                    SourceConsistencyIssue(
                        kind="master_class_application_mismatch",
                        entry_id=entry.entry_id,
                        behavior_id=behavior_id,
                        detail=(
                            f"Master table assigns {behavior_id} to {entry.entry_id}, but the "
                            "canonical class applies_to list omits the entry."
                        ),
                        resolution="preserved_unresolved_for_human_gate",
                    )
                )
    referenced = {behavior_id for entry in entries for behavior_id in entry.behavior_class_ids}
    status_counts = Counter(entry.status.value for entry in entries)
    fidelity_counts = Counter(entry.fidelity.value for entry in entries)
    manifest = BehaviorManifest(
        generator="scripts/generate_behavior_records.py",
        source_spec=_anchor(SPEC_PATH, spec_raw, 1),
        entry_count=len(entries),
        class_count=len(classes),
        binding_count=len(binding_map),
        status_counts=dict(sorted(status_counts.items())),
        fidelity_counts=dict(sorted(fidelity_counts.items())),
        bench_reference_count=sum(len(record.benches) for record in classes),
        bench_execution="imported_research_records_not_rerun_in_stage_1",
        source_consistency_issues=issues,
        unbound_reference_classes=sorted(set(class_map) - referenced),
        resolutions=resolutions,
    )
    return classes, entries, bindings, manifest


def render_records(root: Path = ROOT) -> dict[Path, bytes]:
    classes, entries, bindings, manifest = build_records(root)
    rendered: dict[Path, bytes] = {}

    def add(relative: str, model) -> None:
        content = json.dumps(
            model.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False
        ) + "\n"
        rendered[root / relative] = content.encode("utf-8")

    add(f"{DATA_DIR}/manifest.json", manifest)
    for record in classes:
        add(f"{DATA_DIR}/classes/{record.behavior_id}.json", record)
    for record in entries:
        add(f"{DATA_DIR}/entries/{record.entry_id}.json", record)
    for record in bindings:
        add(f"{DATA_DIR}/bindings/{_binding_filename(record.part_id)}", record)
    return rendered


def write_records(root: Path = ROOT) -> None:
    rendered = render_records(root)
    data_root = (root / DATA_DIR).resolve()
    expected = {path.resolve() for path in rendered}
    if data_root.is_dir():
        for existing in data_root.rglob("*.json"):
            if existing.resolve() not in expected:
                existing.unlink()
    for path, content in rendered.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    from ohmni.behavior.loader import BehaviorRegistry

    registry = BehaviorRegistry(root / DATA_DIR, repo_root=root)
    print(
        f"generated {len(registry.entries)} entries, {len(registry.classes)} classes, "
        f"{len(registry.bindings)} bindings"
    )


def check_records(root: Path = ROOT) -> bool:
    rendered = render_records(root)
    data_root = root / DATA_DIR
    expected = {path.resolve() for path in rendered}
    actual = {path.resolve() for path in data_root.rglob("*.json")} if data_root.is_dir() else set()
    mismatches: list[str] = []
    for path, content in rendered.items():
        if not path.is_file():
            mismatches.append(f"missing generated record: {path.relative_to(root)}")
        elif path.read_bytes() != content:
            mismatches.append(f"stale generated record: {path.relative_to(root)}")
    for path in sorted(actual - expected):
        mismatches.append(f"unexpected generated record: {path.relative_to(root)}")
    if mismatches:
        print("\n".join(mismatches[:20]), file=sys.stderr)
        return False
    from ohmni.behavior.loader import BehaviorRegistry

    BehaviorRegistry(data_root, repo_root=root)
    print(f"behavior records current: {len(rendered)} files")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        write_records()
        return 0
    return 0 if check_records() else 1


if __name__ == "__main__":
    raise SystemExit(main())
