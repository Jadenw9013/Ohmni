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
from .bom import calculate_cost, classify_assembly, generate_bom, synthetic_fixture_supplier
from .catalog import default_catalog
from .datasheet import BoundedTextExtractor, DatasheetPipeline, PdfIngestError, PyMuPdfExtractor
from .datasheet.pipeline import format_ingestion_report
from .domain import CircuitIR, RuleOutcome
from .eda.kicad import (
    KiCadCliAdapter,
    KiCadPcbCompiler,
    KiCadSchematicCompiler,
    PcbCompilationError,
    SchematicCompilationError,
)
from .eda.kicad.placement import golden_board_constraints
from .eda.models import EdaVerificationBundle, ErcStatus
from .eda.pcb_models import DrcStatus, PcbVerificationBundle
from .eda.verification import aggregate_eda
from .fixtures.esp32_env_logger import BROKEN_VARIANTS, BUILDERS, requirements
from .generation import DesignOrchestrator
from .generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider
from .manufacturing import (
    FabricationExportError,
    KiCadFabricationExporter,
    prototype_profile,
    verify_manufacturing,
)
from .routing.router import DeterministicRouter
from .routing.verifier import verify_routing
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
    classes: dict[str, int] = {}
    for finding in erc.findings:
        classes[finding.classification.value] = classes.get(finding.classification.value, 0) + 1
    return "\n".join([
        f"KiCad {erc.kicad_version or 'UNAVAILABLE'} ERC",
        f"Artifact: {artifact.path}",
        f"Artifact SHA-256: {erc.artifact_fingerprint.digest}",
        f"Violations: {counts['error']} errors, {counts['warning']} warnings, {counts['exclusion']} exclusions",
        f"Status: {erc.status.value.upper()}",
        "Warning classes: " + ", ".join(f"{name}={count}" for name, count in sorted(classes.items())),
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


def cmd_design_fixture(args: argparse.Namespace) -> int:
    report = DesignOrchestrator(flawed_logger_provider(), default_catalog()).design(
        GOLDEN_REQUEST, output=args.output, run_eda=not args.no_eda,
    )
    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        first, last = report.semantic_attempts[0], report.semantic_attempts[-1]
        print("OHMNI DESIGN\n")
        print(f"Requirements: {'READY' if report.requirements else 'FAILED'}")
        print(f"Architecture: {'READY' if report.architecture else 'FAILED'}")
        print(f"Circuit proposal: {report.initial_circuit_hash or 'FAILED'}")
        print(f"Ohmni attempt 1: {'BLOCKED' if first.export_blocked else 'PASS'}")
        for finding in first.findings:
            if finding.severity.value in {"critical", "error"}:
                print(f"  {finding.severity.value.upper()} {finding.rule_id}: {finding.title}")
        print(f"Repair: {'APPLIED' if report.repairs else 'NOT APPLIED'}")
        print(f"Ohmni final: {'BLOCKED' if last.export_blocked else 'EXPORT ELIGIBLE'}")
        if report.erc:
            print(f"KiCad ERC: {report.erc.status.value.upper()} ({len(report.erc.findings)} findings)")
        else:
            print("KiCad ERC: NOT RUN")
        print(f"Notebook events: {len(report.notebook.events) if report.notebook else 0}")
        print(f"Final status: {report.state.value.upper()}")
    return EXIT_OK if report.state.value == "complete" else EXIT_BLOCKED


def _compile_pcb_named(args):
    circuit = _load_circuit(args.fixture, None)
    semantic = verify(circuit, default_catalog(), requirements())
    if semantic.export_blocked:
        raise PcbCompilationError("semantic verification blocks PCB compilation")
    base = args.output or Path("out") / "pcb" / args.fixture / f"{args.fixture}.kicad_pcb"
    schematic = KiCadSchematicCompiler(default_catalog()).compile(circuit, base.with_suffix(".kicad_sch"))
    erc = KiCadCliAdapter().run_erc(schematic)
    pcb = KiCadPcbCompiler(default_catalog()).compile(circuit, schematic, golden_board_constraints(), base)
    return semantic, schematic, erc, pcb


def format_pcb_summary(pcb, drc=None):
    physical=pcb.compilation.physical_verification
    lines=["OHMNI PCB VERIFICATION","",f"Artifact: {pcb.path}",f"PCB SHA-256: {pcb.fingerprint.digest}",f"Source schematic SHA-256: {pcb.schematic_fingerprint.digest}",f"Footprints: {len(pcb.compilation.footprint_bindings)}",f"Pad bindings: {len(pcb.compilation.pad_bindings)}","Layers: 2",f"Physical checks: {'PASS' if physical.passed else 'FAIL'}"]
    if drc: lines += [f"KiCad {drc.kicad_version or 'UNAVAILABLE'} DRC: {drc.status.value.upper()}",f"DRC violations: {len(drc.findings)}",f"Unrouted connections: {len(drc.unconnected_items)}","Limitation: DRC covers configured physical rules on this exact PCB, not functional correctness."]
    return "\n".join(lines)


def cmd_compile_pcb(args):
    try: _,_,_,pcb=_compile_pcb_named(args)
    except (PcbCompilationError,SchematicCompilationError) as exc:
        print(f"PCB compilation failed: {exc}",file=sys.stderr);return EXIT_BLOCKED
    print(pcb.model_dump_json(indent=2) if args.json else format_pcb_summary(pcb))
    return EXIT_OK if pcb.compilation.physical_verification.passed else EXIT_BLOCKED


def cmd_drc(args):
    try: _,schematic,erc,pcb=_compile_pcb_named(args)
    except (PcbCompilationError,SchematicCompilationError) as exc:
        print(f"PCB compilation failed: {exc}",file=sys.stderr);return EXIT_BLOCKED
    drc=KiCadCliAdapter().run_drc(pcb)
    if args.json: print(PcbVerificationBundle(schematic=schematic,erc=erc,pcb=pcb,drc=drc).model_dump_json(indent=2))
    else: print(format_pcb_summary(pcb,drc))
    return EXIT_BLOCKED if drc.status in {DrcStatus.FAIL,DrcStatus.ERROR,DrcStatus.UNAVAILABLE,DrcStatus.STALE_ARTIFACT} else EXIT_OK


def cmd_route(args):
    try:
        circuit=_load_circuit(args.fixture,None);catalog=default_catalog();board=golden_board_constraints()
        if verify(circuit,catalog,requirements()).export_blocked: raise PcbCompilationError("semantic verification blocks routing")
        base=args.output or Path("out")/"route"/args.fixture/f"{args.fixture}.kicad_pcb"
        schematic=KiCadSchematicCompiler(catalog).compile(circuit,base.with_suffix(".kicad_sch"))
        placed=KiCadPcbCompiler(catalog).compile(circuit,schematic,board,base.with_name(base.stem+".placed.kicad_pcb"))
        plan=DeterministicRouter().route(circuit,placed,board);routing=verify_routing(circuit,placed,board,plan)
        if not routing.passed: raise PcbCompilationError("independent routing verification failed")
        routed=KiCadPcbCompiler(catalog).compile(circuit,schematic,board,base,plan);drc=KiCadCliAdapter().run_drc(routed)
    except (PcbCompilationError,SchematicCompilationError,ValueError) as exc:
        print(f"routing failed: {exc}",file=sys.stderr);return EXIT_BLOCKED
    if args.json:
        print(json.dumps({"routing_plan":json.loads(plan.model_dump_json()),"routing_verification":json.loads(routing.model_dump_json()),"pcb":json.loads(routed.model_dump_json()),"drc":json.loads(drc.model_dump_json())},indent=2))
    else:
        s=plan.statistics
        print("OHMNI ROUTING\n")
        print(f"Board: {args.fixture}\nRouting profile: {plan.profile.name}")
        print(f"Required connections: {s.required_connections}\nNets routed: {s.routed_net_count} / {s.routed_net_count+s.unresolved_net_count}")
        print(f"Track segments: {s.track_segment_count}\nModeled layer transitions: {s.via_count}\nTotal track length: {s.total_track_length_mm:.3f} mm")
        print(f"Expanded nodes: {s.expanded_nodes}\nRouting attempts: {s.routing_attempts}")
        print(f"Ohmni routing verification: {'PASS' if routing.passed else 'FAIL'}")
        print(f"KiCad {drc.kicad_version or 'UNAVAILABLE'} DRC: {drc.status.value.upper()}\nDRC violations: {len(drc.findings)}\nUnrouted connections: {len(drc.unconnected_items)}")
        print("Final PCB status: "+("VERIFIED WITHIN IMPLEMENTED CHECKS" if routing.passed and not drc.findings and not drc.unconnected_items else "FAIL"))
    return EXIT_OK if routing.passed and drc.status in {DrcStatus.PASS,DrcStatus.PASS_WITH_WARNINGS} and not drc.findings and not drc.unconnected_items else EXIT_BLOCKED

def _release_inputs(fixture,output):
    circuit=_load_circuit(fixture,None);catalog=default_catalog();board=golden_board_constraints();base=output
    semantic=verify(circuit,catalog,requirements())
    if semantic.export_blocked:raise ValueError("semantic verification blocks release")
    schematic=KiCadSchematicCompiler(catalog).compile(circuit,base.with_suffix(".kicad_sch"));erc=KiCadCliAdapter().run_erc(schematic)
    if erc.status not in {ErcStatus.PASS,ErcStatus.PASS_WITH_WARNINGS}:raise ValueError("KiCad ERC blocks release")
    placed=KiCadPcbCompiler(catalog).compile(circuit,schematic,board,base.with_name(base.stem+".placed.kicad_pcb"));plan=DeterministicRouter().route(circuit,placed,board);routing=verify_routing(circuit,placed,board,plan)
    if not routing.passed:raise ValueError("independent routing verification blocks release")
    routed=KiCadPcbCompiler(catalog).compile(circuit,schematic,board,base,plan);drc=KiCadCliAdapter().run_drc(routed);profile=prototype_profile();mfg=verify_manufacturing(routed,board,plan,profile)
    if drc.status not in {DrcStatus.PASS,DrcStatus.PASS_WITH_WARNINGS} or drc.findings or drc.unconnected_items:raise ValueError("KiCad DRC blocks release")
    if not mfg.passed:raise ValueError("manufacturing profile blocks release")
    return circuit,catalog,schematic,erc,plan,routing,routed,drc,profile,mfg

def cmd_bom(args):
    circuit=_load_circuit(args.fixture,None);bom=generate_bom(circuit,default_catalog())
    if args.json:print(bom.model_dump_json(indent=2))
    else:
        print(f"OHMNI BOM\n\nDesign references: {bom.reference_count}\nUnique purchase lines: {len(bom.lines)}")
        for line in bom.lines:print(f"{', '.join(line.references):<24} {line.quantity_per_board} x {line.identity.mpn or line.identity.part_id} [{line.identity.package}]")
    return EXIT_OK

def cmd_cost(args):
    circuit=_load_circuit(args.fixture,None);bom=generate_bom(circuit,default_catalog());report=calculate_cost(bom,synthetic_fixture_supplier(bom),args.quantity)
    if args.json:print(report.model_dump_json(indent=2))
    else:print(f"OHMNI PROTOTYPE COST\n\nScenario: {args.quantity} board(s)\nPricing source: SYNTHETIC FIXTURE - NOT LIVE SUPPLIER DATA\nPricing coverage: {report.pricing_coverage:.1%}\nKnown component consumption: ${report.known_consumption_cost}\nKnown purchase requirement: ${report.known_purchase_requirement}\nPCB fabrication: UNKNOWN\nShipping: UNKNOWN\nTools/consumables: UNKNOWN")
    return EXIT_OK

def cmd_manufacture(args):
    base=args.output or Path("out")/"release"/args.fixture/f"{args.fixture}.kicad_pcb"
    try:*_,mfg=_release_inputs(args.fixture,base)
    except (OSError,RuntimeError,ValueError) as exc:print(f"manufacturing check failed: {exc}",file=sys.stderr);return EXIT_BLOCKED
    if args.json:print(mfg.model_dump_json(indent=2))
    else:
        print("OHMNI MANUFACTURING PROFILE CHECK\n")
        for f in mfg.findings:print(f"{'PASS' if f.status.value=='pass' else 'FAIL'} {f.rule_id} {f.subject}: {f.detail}")
    return EXIT_OK if mfg.passed else EXIT_BLOCKED

def cmd_release(args):
    base=args.output or Path("out")/"release"/args.fixture/f"{args.fixture}.kicad_pcb"
    try:
        circuit,catalog,_schematic,_erc,_plan,_routing,pcb,drc,profile,mfg=_release_inputs(args.fixture,base)
        package=KiCadFabricationExporter().export(pcb,drc,mfg,profile,base.parent/"fabrication")
    except (FabricationExportError,OSError,RuntimeError,ValueError) as exc:print(f"release blocked: {exc}",file=sys.stderr);return EXIT_BLOCKED
    bom=generate_bom(circuit,catalog);cost=calculate_cost(bom,synthetic_fixture_supplier(bom),args.quantity);assembly=classify_assembly(bom)
    if args.json:print(json.dumps({"manufacturing":json.loads(mfg.model_dump_json()),"bom":json.loads(bom.model_dump_json()),"cost":json.loads(cost.model_dump_json()),"assembly":json.loads(assembly.model_dump_json()),"fabrication":json.loads(package.model_dump_json())},indent=2))
    else:
        print("OHMNI HARDWARE RELEASE\n\nElectrical\nPASS Semantic verification\nPASS KiCad ERC: 0 electrical errors\n\nPhysical\nPASS Placement verification\nPASS Routing verification\nPASS KiCad DRC: 0 violations, 0 unrouted")
        print(f"\nManufacturing profile\nPASS {profile.display_name}\nPASS {len(mfg.findings)} deterministic checks")
        print(f"\nAssembly\n{'WARN' if not assembly.hand_solder_requirement_satisfied else 'PASS'} BME280 LGA requires reflow/hot-air; package risk remains visible")
        print(f"\nBOM\n{bom.reference_count} references\n{len(bom.lines)} unique lines\nPricing coverage: {cost.pricing_coverage:.1%}\nKnown consumption: ${cost.known_consumption_cost}\nKnown purchase requirement: ${cost.known_purchase_requirement}\nFabrication price: UNKNOWN\nShipping: UNKNOWN")
        print(f"\nFabrication package\nPASS {len(package.files)} generated files\nPackage SHA-256: {package.package_fingerprint}\n\nSTATUS\nREADY_FOR_MANUFACTURING_REVIEW\n\nNot simulation, thermal, EMC/RF, or bench verified. No guarantee of fabrication or assembly success.")
    return EXIT_OK


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

    design_fixture = sub.add_parser("design-fixture", help="run the scripted flawed-design and repair demo")
    design_fixture.add_argument("fixture", choices=["golden_request"])
    design_fixture.add_argument("--output", type=Path)
    design_fixture.add_argument("--no-eda", action="store_true")
    design_fixture.add_argument("--json", action="store_true")
    design_fixture.set_defaults(func=cmd_design_fixture)

    compile_pcb=sub.add_parser("compile-pcb",help="compile the deterministic placed PCB")
    compile_pcb.add_argument("fixture",choices=["golden"]);compile_pcb.add_argument("--output",type=Path);compile_pcb.add_argument("--json",action="store_true");compile_pcb.set_defaults(func=cmd_compile_pcb)
    drc=sub.add_parser("drc",help="compile a PCB and run real KiCad DRC")
    drc.add_argument("fixture",choices=["golden"]);drc.add_argument("--output",type=Path);drc.add_argument("--json",action="store_true");drc.set_defaults(func=cmd_drc)
    route=sub.add_parser("route",help="deterministically route a placed PCB and run KiCad DRC")
    route.add_argument("fixture",choices=["golden"]);route.add_argument("--output",type=Path);route.add_argument("--json",action="store_true");route.set_defaults(func=cmd_route)
    bom=sub.add_parser("bom",help="generate an identity-safe BOM");bom.add_argument("fixture",choices=["golden"]);bom.add_argument("--json",action="store_true");bom.set_defaults(func=cmd_bom)
    cost=sub.add_parser("cost",help="calculate evidenced prototype purchase economics");cost.add_argument("fixture",choices=["golden"]);cost.add_argument("--quantity",type=int,choices=[1,5,10],default=1);cost.add_argument("--json",action="store_true");cost.set_defaults(func=cmd_cost)
    manufacture=sub.add_parser("manufacture-check",help="route and check a manufacturing profile");manufacture.add_argument("fixture",choices=["golden"]);manufacture.add_argument("--output",type=Path);manufacture.add_argument("--json",action="store_true");manufacture.set_defaults(func=cmd_manufacture)
    release=sub.add_parser("release",help="generate the reviewed fabrication release bundle");release.add_argument("fixture",choices=["golden"]);release.add_argument("--quantity",type=int,choices=[1,5,10],default=1);release.add_argument("--output",type=Path);release.add_argument("--json",action="store_true");release.set_defaults(func=cmd_release)

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
