"""Command-line entry point for the component behavior audit."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .audit import AuditError, BehaviorAudit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-dir", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("canaries")
    commands.add_parser("check").add_argument("--no-regression", action="store_true")
    checkpoint = commands.add_parser("checkpoint")
    checkpoint.add_argument("--stage", required=True)
    checkpoint.add_argument("--entries", default="")
    checkpoint.add_argument("--no-regression", action="store_true")
    commands.add_parser("coverage")
    commands.add_parser("inventory")
    commands.add_parser("probe-ngspice")
    commands.add_parser("run-benches")
    fetch = commands.add_parser("fetch")
    fetch_group = fetch.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument("--url")
    fetch_group.add_argument("--all", action="store_true")
    verifier = commands.add_parser("verifier-plan")
    verifier.add_argument("--stage", required=True)
    verifier.add_argument("--entries", required=True)
    verifier.add_argument("--seed", type=int)
    commands.add_parser("final-report")
    rebuild = commands.add_parser("rebuild-sources", help="re-download ledgered sources into the local archive and verify their hashes")
    rebuild.add_argument("--only")
    rebuild.add_argument("--report", type=Path)
    rebaseline = commands.add_parser("rebaseline", help="re-record the protected-state baseline after owner-approved merges")
    rebaseline.add_argument("--reason", required=True)
    rebaseline.add_argument("--approved-by", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    audit = BehaviorAudit(args.root, args.run_dir)
    try:
        if args.command == "init":
            state = audit.initialize()
            print(json.dumps({key: state[key] for key in ("run_id", "current_stage", "rule_hash")}, indent=2))
            return 0
        audit.initialize()
        if args.command == "canaries":
            result = audit.run_canaries()
            print(json.dumps(result.to_dict(), indent=2))
            return 0 if result.passed else 1
        if args.command == "check":
            results = audit.run_checks(regression=not args.no_regression)
            print(json.dumps([result.to_dict() for result in results], indent=2))
            return 0 if all(result.passed for result in results) else 1
        if args.command == "checkpoint":
            touched = [item.strip() for item in args.entries.split(",") if item.strip()]
            path, results = audit.checkpoint(
                args.stage, touched, regression=not args.no_regression
            )
            print(path)
            return 0 if all(result.passed for result in results) else 1
        if args.command == "coverage":
            print(audit.write_coverage())
            return 0
        if args.command == "inventory":
            from .inventory import build_inventory
            result = build_inventory(audit)
            print(json.dumps({"entries": len(result["entries"]), "status_counts": result["status_counts"], "entry_sections_found": result["entry_sections_found"]}))
            return 0
        if args.command == "probe-ngspice":
            result = audit.probe_ngspice()
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1
        if args.command == "run-benches":
            from .benches import run_benches
            rows = run_benches(audit)
            print(json.dumps({"benches": len(rows), "passed": sum(row["status"] == "passed" for row in rows)}))
            return 0 if all(row["status"] == "passed" for row in rows) else 1
        if args.command == "fetch":
            urls = sorted(audit.cited_urls()) if args.all else [args.url]
            with ThreadPoolExecutor(max_workers=4) as executor:
                rows = list(executor.map(audit.fetch, urls))
            print(json.dumps(rows, indent=2))
            return 0 if all(row["http_status"] and 200 <= row["http_status"] < 400 for row in rows) else 1
        if args.command == "verifier-plan":
            population = [item.strip() for item in args.entries.split(",") if item.strip()]
            print(json.dumps(audit.verifier_plan(args.stage, population, args.seed), indent=2))
            return 0
        if args.command == "final-report":
            print(audit.final_report())
            return 0
        if args.command == "rebuild-sources":
            from .rebuild_sources import rebuild
            report = rebuild(audit.run_dir, only=args.only)
            target = args.report or audit.run_dir / "SOURCE_REBUILD.json"
            from .audit import _atomic_json
            _atomic_json(target, report)
            print(json.dumps(report["counts"], indent=2))
            return 0 if set(report["counts"]) <= {"present", "rebuilt"} else 1
        if args.command == "rebaseline":
            print(json.dumps(audit.rebaseline(args.reason, args.approved_by), indent=2))
            return 0
    except AuditError as exc:
        print(f"AUDIT ERROR: {exc}")
        return 2
    raise AssertionError(args.command)
