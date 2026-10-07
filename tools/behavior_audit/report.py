"""Assemble the final account strictly from this run's structured artifacts."""

from collections import Counter

from .audit import _atomic_text, _entries, _json, _read_jsonl


def final_report(audit):
    state = audit._state()
    checkpoints = [_json(path) for path in sorted((audit.run_dir / "checkpoints").glob("*.json"))]
    records = _entries(audit.root)
    before = Counter(row["before"] for row in state["entry_status"].values())
    after = Counter(row["status"] for row in records.values())
    ledger = _read_jsonl(audit.run_dir / "FETCH_LEDGER.jsonl")
    source_check = audit.check_source_ledger()
    bench_check = audit.check_benches()
    probe_path = audit.run_dir / "NGSPICE_PROBE.json"
    probe = _json(probe_path) if probe_path.exists() else {"passed": False, "version_output": "NOT RUN"}
    lines = [
        "# Component behavior final report", "",
        "> Script-generated from this run's structured checkpoint, source, bench and state records.", "",
        f"Run: `{state['run_id']}`. Branch: `{state.get('branch', 'codex/behavior-audit')}`.",
        f"Run state: **{state['stage_status']}**. Hard stop: **{state.get('hard_stop', 'none recorded')}**.", "",
        "## Stage-by-stage results", "",
        "| Stage | Result in this run |", "| --- | --- |",
    ]
    for stage in ["audit", *(f"stage{n}" for n in range(2, 8))]:
        relevant = [row for row in checkpoints if row["stage"] == stage or row["stage"].startswith(stage+"-")]
        result = "NOT RUN / dependent work blocked" if not relevant else ("PASS" if relevant[-1]["passed"] else "FAIL — see checkpoint checks")
        lines.append(f"| {stage} | {result} |")
    lines.extend(["", "Audit-software regression results and component-corpus audit results are separate. A passing unit test is not a bench run.", "", "## Exact coverage totals", "", f"Records: {len(records)}. Before: {dict(sorted(before.items()))}. After: {dict(sorted(after.items()))}.", f"Current-run benchmark gate: **{'PASS' if bench_check.passed else 'FAIL'}** — {bench_check.summary}.", f"Source gate: **{'PASS' if source_check.passed else 'FAIL'}** — {source_check.summary}.", f"Recorded fetch attempts: {len(ledger)}; distinct attempted URLs: {len({row['url'] for row in ledger})}.", "", "## Simulator availability", "", f"Command: `ngspice -v`. Exit: `{probe.get('exit_code')}`. Version gate: **{'PASS' if probe['passed'] else 'FAIL'}**.", "", "```text", probe.get("version_output", ""), "```", "", "## Checkpoints and canaries", "", "| Checkpoint | Rule | Result | Detail |", "| --- | --- | --- | --- |"])
    for cp in checkpoints:
        for check in cp["checks"]:
            lines.append(f"| {cp['number']:03d}-{cp['stage']} | {check['rule_id']} | {'PASS' if check['passed'] else 'FAIL'} | {check['summary'].replace('|', '/')} |")
        for row in cp["canaries"]["results"]:
            lines.append(f"| {cp['number']:03d}-{cp['stage']} | canary: {row['canary_id']} | {'PASS' if row['passed'] else 'FAIL'} | Rejected by {row['rejected_by']} |")
    lines.extend(["", "## Blocked and parked items", ""])
    for identity, reason in sorted(state.get("blocked_entries", {}).items()):
        lines.append(f"- **{identity}:** {reason}")
    if not state.get("blocked_entries"):
        lines.append("No parked state items recorded; failed checks below still block progression.")
    lines.extend(["", "## Unresolved check details", ""])
    if checkpoints:
        for check in checkpoints[-1]["checks"]:
            if not check["passed"]:
                lines.extend([f"### {check['rule_id']}", "", check["summary"], ""])
                lines.extend(f"- {detail}" for detail in check["details"])
                lines.append("")
    lines.extend(["## Decisions (including all electrical-data decisions)", "", (audit.run_dir / "DECISIONS.md").read_text(encoding="utf-8"), "", "## Every rule change", ""])
    changes = audit._rule_change_entries()
    if not changes:
        lines.append("None recorded. Rule hash: `" + state["rule_hash"] + "`.")
    for row in changes:
        lines.append(f"- {row}")
    lines.extend(["", "## Independent verifier results", ""])
    reports = [path for path in (audit.run_dir / "verifier").glob("*.json") if not path.stem.endswith("-plan")]
    if not reports:
        lines.append("NOT RUN: no research stage completed. No independent research acceptance is claimed.")
    for path in sorted(reports):
        data = _json(path)
        errors = audit._verifier_errors(data.get("stage"), data)
        lines.extend([f"### {data.get('stage')}", "", f"Seed: `{data.get('seed')}`. Sample: {data.get('sample')}. Validator: {'FAIL' if errors else 'PASS'}."])
        for row in data.get("results", []):
            lines.append(f"- {row}")
        lines.extend(f"- {error}" for error in errors)
    lines.extend(["", "## Needs human review", ""])
    inventory_path = audit.run_dir / "GAP_INVENTORY.json"
    inventory = _json(inventory_path) if inventory_path.exists() else {"entries": {}}
    for entry_id, record in records.items():
        text = record["component"] + " " + " ".join(record["behavior_class_ids"])
        if any(token in text.lower() for token in ("x2", "xt30", "xt60", "supercap", "edlc", "tvs", "transformer", "xfmr", "power resistor", "cement", "wirewound")):
            lines.append(f"- {entry_id} — {record['component']}: rating-critical/safety-relevant research and current-run bench required; source status stays {record['status']}.")
    manifest = _json(audit.root / "src/ohmni/behavior/data/manifest.json")
    for issue in manifest.get("source_consistency_issues", []):
        lines.append(f"- Source conflict: {issue['detail']}")
    for resolution in manifest.get("resolutions", []):
        if resolution["gate_required"]:
            lines.append(f"- {', '.join(resolution['entry_ids'])}: {resolution['action']}")
    uncertain_count = sum(len(row.get("open_items", [])) for row in inventory["entries"].values())
    lines.extend([f"- {uncertain_count} per-entry open-item references are preserved in GAP_INVENTORY.json and the full coverage table below. No rating-critical field is promoted by this run.", "", "## Full coverage table", "", (audit.root / "docs/behavior/COVERAGE.md").read_text(encoding="utf-8"), ""])
    path = audit.run_dir / "FINAL_REPORT.md"
    _atomic_text(path, "\n".join(lines))
    return path
