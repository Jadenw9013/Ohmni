"""Publish a supplied research ledger alongside actual current-run receipts.

This helper formats evidence; it neither researches facts nor upgrades status.
"""

from __future__ import annotations

import json
from collections import Counter

from .audit import _atomic_text, _json


def publish_research(audit, payload: dict) -> None:
    entry_id = payload["entry_id"]
    record = _json(audit.root / f"src/ohmni/behavior/data/entries/{entry_id}.json")
    payload = {key: value for key, value in payload.items() if key != "source"}
    receipts = []
    for path in sorted((audit.run_dir / "bench-results").glob("*.json")):
        receipt = _json(path)
        if receipt["bench_id"].split("/")[0] in record["behavior_class_ids"]:
            receipts.append((path.relative_to(audit.run_dir).as_posix(), receipt))
    payload["bench_results"] = [relative for relative, _ in receipts]
    passes = [relative for relative, receipt in receipts if receipt["run_status"] == "passed"]
    payload["bench_result"] = passes[0] if passes else None
    lines = [
        f"# {entry_id}: {record['component']}", "",
        f"Research date: {payload['researched_at']}. Original source status retained: **{record['status']}**.", "",
        "Fields apply only to the named reference and conditions. No source-status upgrade or physical-part verification is claimed.", "",
        "## Sources opened", "",
    ]
    for doc in payload["documents"]:
        lines.append(f"- {doc.get('manufacturer')}: [{doc['title']}]({doc['url']}); revision {doc.get('revision') or 'not established'}.")
    lines.extend(["", "## Current-run class benches", "", "| Bench | Result | Observed / expected / tolerance |", "| --- | --- | --- |"])
    for relative, receipt in receipts:
        observations = "; ".join(f"{row.get('measure')}: {row.get('measured')} / {row.get('expected')} / {row.get('tolerance')}" for row in receipt.get("comparisons", []))
        lines.append(f"| [{receipt['bench_id']}](../../../out/component-behavior/run/{relative}) | {receipt['run_status']} | {observations} |")
    lines.extend(["", "Receipts include actual ngspice version, source-deck hash and raw output. A class bench tests its analytical model; it cannot establish an unsourced package rating or destructive-failure behavior.", ""])
    for heading, key in [("Remaining open items", "remaining_open_items"), ("Conflicts", "conflicts"), ("Simulation blockers", "simulation_blockers")]:
        lines.extend([f"## {heading}", ""])
        lines.extend([f"- {item}" for item in payload.get(key, [])] or ["None newly identified; other stated limitations remain."])
        lines.append("")
    lines.extend(["## Field evidence", "", "```audit-evidence", json.dumps(payload, indent=2, ensure_ascii=False), "```", ""])
    _atomic_text(audit.root / f"docs/behavior/gapfill/{entry_id}.md", "\n".join(lines))


def research_gate(audit, stage: str, entry_ids: list[str]):
    """Report every reviewed entry from generated records and actual receipts."""
    state = audit._state()
    rows = []
    for entry_id in entry_ids:
        record = _json(audit.root / f"src/ohmni/behavior/data/entries/{entry_id}.json")
        research = record.get("research") or {}
        receipts = [_json(audit.run_dir / path) for path in research.get("bench_results", [])]
        rows.append({
            "entry_id": entry_id,
            "component": record["component"],
            "before": state["entry_status"][entry_id]["before"],
            "after": record["status"],
            "research_result": research.get("research_result", "not_reviewed"),
            "source_count": len(research.get("documents", [])),
            "fact_count": len(research.get("field_updates", [])),
            "bench_passed": sum(receipt["run_status"] == "passed" for receipt in receipts),
            "bench_total": len(receipts),
            "remaining": research.get("remaining_open_items", []),
            "conflicts": research.get("conflicts", []),
            "blockers": research.get("simulation_blockers", []),
        })
    counts = Counter(row["research_result"] for row in rows)
    lines = [
        f"# {stage}: research gate", "",
        "> Script-generated from gapfill records and current-run ngspice receipts.", "",
        f"Entries: {len(rows)}. Research outcomes: {dict(sorted(counts.items()))}.",
        f"Status upgrades: {sum(row['before'] != row['after'] for row in rows)}.",
        "Class bench results do not establish package ratings or full physical-device validity.", "",
        "| Entry | Before | After | Research | Sources / fields | Class benches |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        entry_id = row["entry_id"]
        lines.append(
            f"| [{entry_id}](../../../docs/behavior/gapfill/{entry_id}.md) | "
            f"{row['before']} | {row['after']} | {row['research_result']} | "
            f"{row['source_count']} / {row['fact_count']} | "
            f"{row['bench_passed']}/{row['bench_total']} PASS |"
        )
    lines.extend(["", "## Remaining work and conflicts", ""])
    for row in rows:
        lines.extend([f"### {row['entry_id']}: {row['component']}", ""])
        for key in ("remaining", "conflicts", "blockers"):
            lines.extend(f"- {key}: {item}" for item in row[key])
        lines.append("")
    output = audit.root / f"out/component-behavior/{stage}/RESEARCH-GATE.md"
    _atomic_text(output, "\n".join(lines))
    return output
