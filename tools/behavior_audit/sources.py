"""Relocate named citations to their original, group-scoped bibliography.

This resolves references, not electrical claims. Downloading the resolved URL
still does not establish that a parameter is supported by the document.
"""

from __future__ import annotations

import re

from .audit import _json, _sha_bytes, _urls_in


def reference_ids(text: str) -> list[str]:
    expanded = text
    for match in list(re.finditer(r"S(\d+)\s*(?:\.\.|-|to)\s*S?(\d+)", text)):
        lo, hi = map(int, match.groups())
        if not 0 < lo <= hi < 100:
            continue
        expanded = expanded.replace(match.group(), ", ".join(f"S{i}" for i in range(lo, hi + 1)))
    return sorted(set(re.findall(r"\bS\d+\b", expanded)), key=lambda x: int(x[1:]))


def _artifact_binding_errors(root, key: str) -> str | None:
    """A local reference is resolved only by named repository files whose bytes are locked."""
    from pathlib import Path

    path = Path(root) / "docs/behavior/SOURCE_BINDINGS.json"
    if not path.exists():
        return "unbound"
    bindings = _json(path)
    entry = bindings.get("artifact_bindings", {}).get(key)
    if not entry:
        return "unbound"
    if not bindings.get("approved_by") or not bindings.get("approved_on"):
        return "binding lacks a recorded approval"
    files = entry.get("files") or {}
    if not files:
        return "binding names no files"
    for relative, digest in files.items():
        target = (Path(root) / relative).resolve()
        if Path(root).resolve() not in target.parents or not target.is_file():
            return f"bound file missing: {relative}"
        if _sha_bytes(target.read_bytes()) != digest:
            return f"bound file changed: {relative}"
    return None


def resolve_class_sources(root, record: dict) -> tuple[list[dict], list[str]]:
    raw = (root / "COMPONENT_BEHAVIOR_SPEC.md").read_bytes()
    lines = raw.decode("utf-8").splitlines()
    anchor = record["source"]["line"] - 1
    starts = [i for i, line in enumerate(lines) if line.startswith("<!-- BEGIN ")]
    start = max(i for i in starts if i <= anchor)
    end = min((i for i in starts if i > anchor), default=len(lines))
    # R9 deliberately restarts S1 for each connector class. Never resolve a
    # reference across those class boundaries merely because its ID matches.
    if lines[start] == "<!-- BEGIN R9 -->":
        headings = [i for i in range(start, end) if lines[i].startswith("## BEHAVIOR CLASS:")]
        start = max(i for i in headings if i <= anchor)
        end = min((i for i in headings if i > anchor), default=end)
    bibliography = {}
    for i in range(start, end):
        line = lines[i]
        match = re.match(r"^(?:[-*]\s+|\|\s*)(S\d+)\s*(?::|\|)", line)
        if match:
            bibliography.setdefault(match[1], []).append((i + 1, line))
    refs = record.get("source_refs") or []
    if isinstance(refs, str):
        refs = [refs]
    rows, errors = [], []
    for ref in refs:
        if isinstance(ref, dict):
            if not ref.get("url"):
                errors.append(f"{record['behavior_id']}: external citation lacks URL: {ref.get('id')}")
            else:
                rows.append({"id": ref.get("id"), "urls": [ref["url"]], "source": ref,
                             "source_line": record["source"]["line"], "origin": "canonical_citation"})
            continue
        ids = reference_ids(ref)
        if not ids:
            errors.append(f"{record['behavior_id']}: unresolved named source: {ref}")
        for identity in ids:
            matches = bibliography.get(identity, [])
            if len(matches) != 1:
                errors.append(f"{record['behavior_id']}/{identity}: expected one scoped bibliography definition, found {len(matches)}")
                continue
            line_number, line = matches[0]
            urls = sorted(_urls_in(line))
            if not urls:
                problem = _artifact_binding_errors(root, f"{record['behavior_id']}/{identity}")
                if problem:
                    errors.append(f"{record['behavior_id']}/{identity}: local or unresolved reference requires an explicit artifact binding: {line}" + ("" if problem == "unbound" else f" ({problem})"))
            rows.append({"id": identity, "urls": urls, "source_line": line_number,
                         "source_text": line, "source_sha256": _sha_bytes(raw),
                         "origin": "spec_bibliography"})
    return rows, errors


def source_catalog(root) -> dict:
    result = {}
    for path in sorted((root / "src/ohmni/behavior/data/classes").glob("*.json")):
        rows, errors = resolve_class_sources(root, _json(path))
        result[path.stem] = {"sources": rows, "unresolved": errors}
    return result
