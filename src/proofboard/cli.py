"""Command line interface.

    python -m proofboard verify golden
    python -m proofboard verify sensor_on_5v --verbose
    python -m proofboard verify --file path/to/circuit.json
    python -m proofboard verify-all
    python -m proofboard rules
    python -m proofboard parts
    python -m proofboard doctor

`verify` exits non-zero when the design cannot be exported as verified, so this
is usable in CI without anything else being built.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters.tools import probe_all
from .catalog import default_catalog
from .domain import CircuitIR, RuleOutcome
from .fixtures.esp32_env_logger import BROKEN_VARIANTS, BUILDERS, requirements
from .verifier import all_rules, format_report, verify

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_USAGE = 2


def _load_circuit(name: str | None, path: Path | None) -> CircuitIR:
    if path is not None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("_content_hash", None)
        return CircuitIR.model_validate(payload)
    if name is None:
        raise SystemExit("give a fixture name or --file")
    if name not in BUILDERS:
        raise SystemExit(f"unknown fixture {name!r}; known: {', '.join(sorted(BUILDERS))}")
    return BUILDERS[name]()


def cmd_verify(args: argparse.Namespace) -> int:
    circuit = _load_circuit(args.fixture, args.file)
    report = verify(circuit, default_catalog(), requirements() if args.requirements else None)

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(format_report(report, verbose=args.verbose))

    return EXIT_BLOCKED if report.export_blocked else EXIT_OK


def cmd_verify_all(args: argparse.Namespace) -> int:
    """Verify every fixture and report whether each behaved as intended.

    Golden must be exportable; every broken variant must be caught by the rule
    it was built to trip. This is the regression suite in one line of output
    per case.
    """
    catalog = default_catalog()
    spec = requirements()
    failures = 0

    print(f"{'fixture':<28} {'expected':<26} {'result':<10} coverage")
    print("-" * 82)

    for name in BUILDERS:
        report = verify(BUILDERS[name](), catalog, spec)
        if name == "golden":
            expected = "no blocking findings"
            ok = not report.export_blocked and report.coverage == 1.0
            actual = "clean" if not report.export_blocked else "BLOCKED"
        else:
            rule_id, severity = BROKEN_VARIANTS[name]
            expected = f"{rule_id} {severity}"
            hits = [
                f
                for f in report.findings
                if f.rule_id == rule_id and f.severity.value == severity
            ]
            ok = bool(hits) and report.export_blocked
            actual = "caught" if hits else "MISSED"

        crashed = [r.rule_id for r in report.results if r.outcome is RuleOutcome.ERROR]
        if crashed:
            ok = False
            actual = f"CRASH {','.join(crashed)}"

        if not ok:
            failures += 1
        marker = "  " if ok else "! "
        print(f"{marker}{name:<26} {expected:<26} {actual:<10} {report.coverage:>6.0%}")

    print("-" * 82)
    if failures:
        print(f"{failures} fixture(s) did not behave as intended")
        return EXIT_BLOCKED
    print(f"all {len(BUILDERS)} fixtures behaved as intended")
    return EXIT_OK


def cmd_rules(args: argparse.Namespace) -> int:
    rules = all_rules()
    by_category: dict[str, list] = {}
    for registered in rules:
        by_category.setdefault(registered.category.value, []).append(registered)

    for category in sorted(by_category):
        print(f"\n{category}")
        print("-" * 76)
        for registered in by_category[category]:
            print(f"  {registered.rule_id:<12} {registered.title}")
            if args.verbose and registered.description:
                print(f"               {registered.description}")
    print(f"\n{len(rules)} deterministic rules")
    return EXIT_OK


def cmd_parts(args: argparse.Namespace) -> int:
    catalog = default_catalog()
    print(f"{'part_id':<24} {'mpn':<22} {'category':<18} pins  packages")
    print("-" * 88)
    for spec in catalog.all_parts():
        mpn = spec.mpn or "(generic)"
        packages = ", ".join(p.name for p in spec.packages)
        print(
            f"{spec.part_id:<24} {mpn:<22} {spec.category.value:<18} "
            f"{len(spec.pins):>4}  {packages}"
        )
    print(f"\n{len(catalog)} parts")
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    print("External tools")
    print("-" * 76)
    for availability in probe_all():
        print(f"  {availability.name:<14} {availability.status.value.upper()}")
        if availability.version:
            print(f"                 version   : {availability.version}")
        if availability.executable:
            print(f"                 path      : {availability.executable}")
        if availability.detail:
            print(f"                 note      : {availability.detail}")
    print()
    print(
        "None of these are required. The deterministic verifier is the primary evidence\n"
        "layer; KiCad ERC and SPICE are corroboration. When a tool is missing its\n"
        "subsystem is reported UNSUPPORTED, never as a pass."
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proofboard",
        description="Evidence-first PCB mentor: deterministic circuit verification.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify_parser = sub.add_parser("verify", help="verify one circuit")
    verify_parser.add_argument(
        "fixture", nargs="?", help=f"one of: {', '.join(sorted(BUILDERS))}"
    )
    verify_parser.add_argument("--file", type=Path, help="verify a CircuitIR JSON file instead")
    verify_parser.add_argument("--verbose", "-v", action="store_true", help="list every rule")
    verify_parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    verify_parser.add_argument(
        "--no-requirements",
        dest="requirements",
        action="store_false",
        help="verify without the project requirements (skips requirement-dependent rules)",
    )
    verify_parser.set_defaults(func=cmd_verify, requirements=True)

    all_parser = sub.add_parser("verify-all", help="verify every fixture (regression sweep)")
    all_parser.set_defaults(func=cmd_verify_all)

    rules_parser = sub.add_parser("rules", help="list the deterministic rules")
    rules_parser.add_argument("--verbose", "-v", action="store_true")
    rules_parser.set_defaults(func=cmd_rules)

    parts_parser = sub.add_parser("parts", help="list the part catalog")
    parts_parser.set_defaults(func=cmd_parts)

    doctor_parser = sub.add_parser("doctor", help="report external tool availability")
    doctor_parser.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
