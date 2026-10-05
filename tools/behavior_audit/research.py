"""Publish a supplied research ledger alongside actual current-run receipts.

This helper formats evidence; it neither researches facts nor upgrades status.
"""

from __future__ import annotations

import json

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
