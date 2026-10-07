"""Extract preserved research gaps and interface limits without inventing facts."""

from __future__ import annotations

import re
from collections import Counter

from .audit import _atomic_json, _atomic_text, _entries, _json, _now


def evidence_fields(value, pointer=""):
    if isinstance(value, dict):
        if "basis" in value or ("confidence" in value and not isinstance(value["confidence"], dict)):
            yield {"pointer": pointer, "source_value": value}
        for key, child in value.items():
            yield from evidence_fields(child, f"{pointer}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from evidence_fields(child, f"{pointer}/{index}")


def build_inventory(audit):
    text = (audit.root / "COMPONENT_BEHAVIOR_SPEC.md").read_text(encoding="utf-8")
    sections = {}
    headings = list(re.finditer(r"^## .*?(?:\[(OHM-\d{3})\]|(OHM-\d{3})).*$", text, re.MULTILINE))
    for match in headings:
        following = re.search(r"^## ", text[match.end():], re.MULTILINE)
        end = match.end()+following.start() if following else len(text)
        sections[match.group(1) or match.group(2)] = {
            "line": text.count("\n", 0, match.start())+1,
            "text": text[match.start():end].strip(),
        }
    classes = {path.stem: _json(path) for path in (audit.root / "src/ohmni/behavior/data/classes").glob("*.json")}
    records = _entries(audit.root)
    entries = {}
    for entry_id, record in sorted(records.items()):
        fields = []
        for class_id in record["behavior_class_ids"]:
            fields.extend(dict(field, behavior_id=class_id) for field in evidence_fields(classes[class_id]["canonical_payload"]))
        uncertain = [field for field in fields if field["source_value"].get("basis") in ("ASSUMPTION", "RESEARCH_REQUIRED") or field["source_value"].get("confidence") in ("L", "LOW")]
        open_items = []
        for field in uncertain:
            raw = field["source_value"]
            name = raw.get("name", raw.get("id", field["pointer"]))
            open_items.append(f"{field['behavior_id']} {name}: basis={raw.get('basis', 'not specified')}, confidence={raw.get('confidence', 'not specified')}")
        if record["status"] != "complete":
            open_items.append("Retain source status until parameters, ratings, failure behavior and current-run bench are supported")
        if 103 <= int(entry_id[4:]) <= 140:
            open_items.append("Package needs a primary-source reference-part binding before electrical simulation")
        if record["layer"] == "L3":
            open_items.append("Protocol/firmware outside ngspice; electrical-interface simulation is a separate bounded claim")
        if entry_id in {"OHM-071", "OHM-072"}:
            open_items.append("Bridge terminal functions unresolved; automatic electrical binding blocked")
        if entry_id == "OHM-133":
            open_items.append("Master table includes BEH-REG-LINEAR but canonical applies_to omits OHM-133")
        # Text is retained verbatim with a source line, including gaps not represented in YAML.
        section = sections.get(entry_id)
        entries[entry_id] = {
            "status_before": record["status"], "status_after": record["status"],
            "component": record["component"], "class_ids": record["behavior_class_ids"],
            "source_section": section,
            "field_evidence": fields, "open_items": open_items,
            "class_confidence": {class_id: classes[class_id]["canonical_payload"].get("confidence") for class_id in record["behavior_class_ids"]},
            "class_source_refs": {class_id: classes[class_id]["source_refs"] for class_id in record["behavior_class_ids"]},
            "research_result": "not_rederived", "bench_result": "not_run",
        }
    result = {
        "schema_version": 1, "generated_at": _now(),
        "entries": entries,
        "status_counts": dict(Counter(row["status"] for row in records.values())),
        "entry_sections_found": len(sections),
        "note": "This is an inventory of source claims, not a verification or status upgrade.",
    }
    _atomic_json(audit.run_dir / "GAP_INVENTORY.json", result)
    rows = ["# Behavior gap inventory", "", result["note"], ""]
    for entry_id, row in entries.items():
        rows.extend([f"## {entry_id}: {row['component']}", "", f"Status retained: `{row['status_before']}`.", ""])
        rows.extend(f"- {item}" for item in row["open_items"])
        if row["source_section"]:
            rows.extend(["", f"Source: COMPONENT_BEHAVIOR_SPEC.md line {row['source_section']['line']}.", "", row["source_section"]["text"], ""])
    _atomic_text(audit.run_dir / "GAP_INVENTORY.md", "\n".join(rows))
    return result
