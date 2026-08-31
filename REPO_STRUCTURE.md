# Repository Structure

> **Status: implemented.** This is the layout as built. It differs from the
> original sketch in one way — a single installable package under `src/` instead
> of loose modules under `packages/`. Reasoning in `docs/DECISIONS.md` §4.

```text
ohmni/
├── src/ohmni/
│   ├── domain/                 # pure data and pure functions; imports no infrastructure
│   │   ├── units.py            # Unit, Quantity, ValueRange, engineering-notation parsing
│   │   ├── evidence.py         # EvidenceKind, ClaimStatus, Evidence, Claim, DocumentRef
│   │   ├── component.py        # ComponentSpec, PinSpec, SupplyRail, RegulatorSpec, LedSpec
│   │   ├── requirements.py     # RequirementsSpec, Interface, SafetyDomain
│   │   ├── circuit.py          # CircuitIR, CircuitComponent, Net, DesignConstraint, patches
│   │   ├── verification.py     # Severity, RuleOutcome, RuleResult, VerificationReport
│   │   └── events.py           # EngineeringEvent, DecisionRecord, Lesson, Notebook
│   ├── verifier/
│   │   ├── context.py          # VerificationContext: net-voltage derivation, topology helpers
│   │   ├── registry.py         # @rule registration, ResultBuilder, outcome derivation
│   │   ├── engine.py           # verify(), subsystem roll-up, text report
│   │   └── rules/              # one module per verification layer
│   │       ├── identity.py     # PB-ID-*    parts, pins, packages, hand-solderability
│   │       ├── connectivity.py # PB-CONN-*  ground, supply, dangling nets, unconnected pins
│   │       ├── pins.py         # PB-PIN-*   output contention, floating control pins
│   │       ├── power.py        # PB-PWR-*   operating range vs absolute max, domains, decoupling
│   │       ├── regulator.py    # PB-REG-*   input range, dropout headroom, current capacity
│   │       ├── interfaces.py   # PB-I2C-*, PB-UART-*, PB-USB-*
│   │       └── led.py          # PB-LED-*   series current limiting
│   ├── catalog/
│   │   ├── loader.py           # JsonPartCatalog
│   │   └── data/parts/*.json   # the part catalog; facts carry provenance
│   ├── datasheet/               # PDF adapter, bounded extraction, claim verification, merge
│   ├── adapters/
│   │   ├── __init__.py         # Protocols: PartCatalog, LlmProvider, DatasheetExtractor,
│   │   │                       #            KicadTool, SpiceTool, Router
│   │   ├── fakes.py            # fakes that report UNAVAILABLE rather than inventing passes
│   │   └── tools.py            # real availability probes for kicad-cli and ngspice
│   ├── fixtures/
│   │   └── esp32_env_logger.py # the golden circuit and its broken variants
│   ├── eda/                     # typed artifacts and external-verifier aggregation
│   │   └── kicad/               # deterministic emitter, ERC adapter and JSON parser
│   ├── generation/              # strict schemas, requirements, resolver, typed repairs
│   ├── physical/                # pure board constraints, footprint provenance and geometry rules
│   ├── routing/                 # typed route plans, bounded A*, independent copper checks
│   ├── cli.py                  # python -m ohmni
│   └── __main__.py
├── fixtures/esp32_env_logger/  # exported fixture JSON: the regression corpus
├── tests/
│   ├── test_units.py           # quantities, parsing, tolerance
│   ├── test_evidence.py        # provenance requirements, derived claim status
│   ├── test_circuit_ir.py      # referential integrity, content hashing
│   ├── test_catalog.py         # catalog invariants and provenance honesty
│   ├── test_verifier_semantics.py  # outcomes, coverage, export gate, derived voltage
│   ├── test_fixtures.py        # golden + every broken variant
│   ├── test_cli.py             # exit codes, JSON output
│   └── test_architecture.py    # dependency direction, enforced
├── scripts/
│   ├── author_catalog.py       # authors the catalog in typed Python, emits JSON
│   └── export_fixtures.py      # emits the fixture circuits to JSON
├── docs/DECISIONS.md
├── apps/web/                   # dependency-light local demo frontend (implemented)
└── pyproject.toml
```

## Dependency direction

```
domain  <-  verifier
domain  <-  catalog
domain  <-  adapters
domain  <-  fixtures
```

`domain` imports nothing from its siblings and no infrastructure at all.

**This is enforced, not just documented.** `tests/test_architecture.py` parses
every module's imports and fails if:

- anything in `domain/` imports an HTTP client, a model SDK, `subprocess`, a PDF
  library, a database driver or a sibling subpackage;
- anything in `verifier/rules/` imports any of the above, or `random`, `time`,
  `datetime`, `os` or `pathlib` — a rule whose verdict depends on the clock or on
  a file is not reproducible.

It also asserts that verifying the same circuit twice produces an identical
report, and that every rule named in `VERIFICATION.md` and the build prompt is
actually registered.

## Authoring scripts

The catalog and the fixtures are **stored** as JSON, because the datasheet
extractor will eventually write into the same format and because a JSON diff is
reviewable. They are **authored** in typed Python under `scripts/`, because
hand-writing a 39-pin module as JSON puts typos into exactly the data the
verifier trusts most.

`tests/test_fixtures.py` asserts that the committed JSON still matches its
builder, so a stale export is a test failure rather than a silent divergence.

## Keep the first implementation boring

Still true, and still followed. No Kafka, no Kubernetes, no microservices, no
event sourcing, no vector database, no distributed agents.

Also deliberately absent for now: no database (files on disk are enough for the
vertical slice), no `docker-compose.yml`, and no NetworkX — the graph operations
needed are a few dozen lines against our own IR and avoid an infrastructure
import in the layer that must not have one.
## Milestone 7 packages

- `src/ohmni/manufacturing/`: provenance-aware manufacturing profiles,
  PB-MFG rules, release models, and the bounded KiCad fabrication exporter.
- `src/ohmni/bom/`: identity-safe BOM aggregation, provider-neutral supplier
  offers, prototype cost scenarios, and package-based assembly risk.
- `tests/test_manufacturing.py`: pure manufacturing, BOM, supplier, pricing,
  assembly, and adversarial tests.

## Milestone 8 demo application

- `src/ohmni/application/`: frontend-safe projection and artifact-derived SVG views.
- `apps/web/`: dependency-light responsive engineering-instrument interface.
- `scripts/demo_server.py`: local asynchronous HTTP boundary for real demo jobs.
- `tests/test_demo_*`: projection, UI behavior, job progress, and integrated journey.
