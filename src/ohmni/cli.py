"""Command line interface.

    python -m ohmni verify golden
    python -m ohmni verify sensor_on_5v --verbose
    python -m ohmni verify --file path/to/circuit.json
    python -m ohmni verify-all
    python -m ohmni rules
    python -m ohmni parts
    python -m ohmni doctor

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
from .datasheet import BoundedTextExtractor, DatasheetPipeline, PdfIngestError, PyMuPdfExtractor
from .datasheet.pipeline import format_ingestion_report
from .domain import CircuitIR, RuleOutcome
from .eda.kicad import KiCadCliAdapter, KiCadSchematicCompiler, SchematicCompilationError
from .eda.models import EdaVerificationBundle, ErcStatus
from .eda.verification import aggregate_eda
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

    if args.eda:
        destination = Path("out") / "eda" / circuit.ir_id / f"{circuit.ir_id}.kicad_sch"
        try:
            artifact = KiCadSchematicCompiler(default_catalog()).compile(circuit, destination)
        except SchematicCompilationError as exc:
            print(f"schematic compilation failed: {exc}", file=sys.stderr)
            return EXIT_BLOCKED
        erc = KiCadCliAdapter().run_erc(artifact)
        if args.json:
            print(EdaVerificationBundle(
                semantic=report, aggregated=aggregate_eda(report, erc),
                artifact=artifact, erc=erc,
            ).model_dump_json(indent=2))
        else:
            print(format_report(report, verbose=args.verbose))
            print("\n" + format_erc_summary(artifact, erc))
        return EXIT_BLOCKED if report.export_blocked or erc.status in {
            ErcStatus.FAIL, ErcStatus.ERROR, ErcStatus.UNAVAILABLE, ErcStatus.STALE_ARTIFACT,
        } else EXIT_OK

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(format_report(report, verbose=args.verbose))

    return EXIT_BLOCKED if report.export_blocked else EXIT_OK


def format_compilation_summary(artifact) -> str:
    lines = [
        "Compiled schematic", "", f"Circuit hash: {artifact.circuit_content_hash}",
        f"Artifact: {artifact.path}",
        f"Components: {len(artifact.compilation.symbol_bindings)}",
        f"Nets: {len(artifact.compilation.net_mapping)}",
        f"Artifact SHA-256: {artifact.fingerprint.digest}",
        f"Compilation warnings: {len(artifact.compilation.warnings)}",
    ]
    lines.extend(f"  - {w.code}: {w.message}" for w in artifact.compilation.warnings)
    return "\n".join(lines)


def format_erc_summary(artifact, erc) -> str:
    counts = {"error": 0, "warning": 0, "exclusion": 0}
    for finding in erc.findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return "\n".join([
        f"KiCad {erc.kicad_version or 'UNAVAILABLE'} ERC",
        f"Artifact: {artifact.path}",
        f"Artifact SHA-256: {erc.artifact_fingerprint.digest}",
        f"Violations: {counts['error']} errors, {counts['warning']} warnings, {counts['exclusion']} exclusions",
        f"Status: {erc.status.value.upper()}",
        "Limitation: ERC validates only configured KiCad electrical checks on this exact artifact.",
    ])


def _compile_named(args):
    circuit = _load_circuit(args.fixture, None)
    destination = args.output or Path("out") / "eda" / args.fixture / f"{args.fixture}.kicad_sch"
    return circuit, KiCadSchematicCompiler(default_catalog()).compile(circuit, destination)


def cmd_compile_schematic(args: argparse.Namespace) -> int:
    try:
        _, artifact = _compile_named(args)
    except SchematicCompilationError as exc:
        print(f"schematic compilation failed: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    print(artifact.model_dump_json(indent=2) if args.json else format_compilation_summary(artifact))
    return EXIT_OK


def cmd_erc(args: argparse.Namespace) -> int:
    try:
        _, artifact = _compile_named(args)
    except SchematicCompilationError as exc:
        print(f"schematic compilation failed: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    erc = KiCadCliAdapter().run_erc(artifact)
    print(erc.model_dump_json(indent=2) if args.json else format_erc_summary(artifact, erc))
    return EXIT_BLOCKED if erc.status in {
        ErcStatus.FAIL, ErcStatus.ERROR, ErcStatus.UNAVAILABLE, ErcStatus.STALE_ARTIFACT,
    } else EXIT_OK


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


def cmd_ingest_datasheet(args: argparse.Namespace) -> int:
    catalog = default_catalog()
    component = catalog.get(args.part) if args.part else None
    try:
        report, _ = DatasheetPipeline(PyMuPdfExtractor(), BoundedTextExtractor()).ingest(
            args.path, component
        )
    except PdfIngestError as exc:
        print(f"datasheet ingestion failed [{exc.status.value}]: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    print(report.model_dump_json(indent=2) if args.json else format_ingestion_report(report))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ohmni",
        description="Ohmni: evidence-first electronics engineering mentor and deterministic circuit verifier.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify_parser = sub.add_parser("verify", help="verify one circuit")
    verify_parser.add_argument(
        "fixture", nargs="?", help=f"one of: {', '.join(sorted(BUILDERS))}"
    )
    verify_parser.add_argument("--file", type=Path, help="verify a CircuitIR JSON file instead")
    verify_parser.add_argument("--verbose", "-v", action="store_true", help="list every rule")
    verify_parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    verify_parser.add_argument("--eda", action="store_true", help="also compile and run real KiCad ERC")
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

    ingest_parser = sub.add_parser(
        "ingest-datasheet", help="extract and independently verify bounded datasheet facts"
    )
    ingest_parser.add_argument("path", type=Path)
    ingest_parser.add_argument("--part", help="catalog part_id to review for evidence upgrades")
    ingest_parser.add_argument("--json", action="store_true", help="emit serializable report JSON")
    ingest_parser.set_defaults(func=cmd_ingest_datasheet)

    compile_parser = sub.add_parser("compile-schematic", help="compile a fixture to KiCad")
    compile_parser.add_argument("fixture", help=f"one of: {', '.join(sorted(BUILDERS))}")
    compile_parser.add_argument("--output", type=Path)
    compile_parser.add_argument("--json", action="store_true")
    compile_parser.set_defaults(func=cmd_compile_schematic)

    erc_parser = sub.add_parser("erc", help="compile a fixture and run KiCad ERC")
    erc_parser.add_argument("fixture", help=f"one of: {', '.join(sorted(BUILDERS))}")
    erc_parser.add_argument("--output", type=Path)
    erc_parser.add_argument("--json", action="store_true")
    erc_parser.set_defaults(func=cmd_erc)

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
