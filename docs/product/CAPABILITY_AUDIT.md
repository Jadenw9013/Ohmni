# Ohmni capability audit

**Audited at:** commit `d7b836e` (working tree dirty with the in-flight
M8-RG02 regression scope), 2026-09-01.
**Method:** source inspection, `python -m ohmni doctor` / `parts`, the 465-test
fast tier, and one full local demo run executed through the HTTP API against a
real KiCad 10.0.5 install.

This document is **evidence**, not recommendation. It exists so the rest of
`docs/product/` argues from measured facts rather than from the demo's
impression. Every claim below names the file or command that establishes it.

---

## 1. What is real and general

These subsystems are pure, deterministic, and not coupled to the golden board.
They work on any circuit expressible in `CircuitIR` using catalog parts.

| Capability | Where | Evidence |
|---|---|---|
| Typed units, quantities, explicit tolerant comparison | `domain/units.py` | `tests/test_units.py`; decision 8 |
| Evidence model with **derived** claim status and no setter | `domain/evidence.py` | decision 1; a datasheet citation lacking document, page, or verbatim snippet fails validation |
| Net voltage **derived from drivers**, never declared | `verifier/context.py` | decision 2; renaming the 5 V rail to `3V3_SAFE` still trips the absolute-maximum rule |
| 24 deterministic rules, five outcomes, reported coverage | `verifier/rules/` | `VERIFICATION.md`; golden plus 13 broken fixtures, 100% coverage each |
| Rules cannot reach a model, socket, file, or clock | — | enforced by `tests/test_architecture.py`, which parses imports |
| KiCad 10 schematic emission, symbols generated from pin counts | `eda/kicad/compiler.py` | general over any catalog part; inline `lib_symbols`, global-label connectivity |
| Typed KiCad ERC ingestion that never fabricates a pass | `eda/kicad/erc.py` | measured run produced 21 findings then `PASS_WITH_WARNINGS` |
| Bounded deterministic A* two-layer router | `routing/router.py` | 269 lines, no fixture constants; routed 51 connections |
| Independent copper-connectivity verifier `PB-ROUTE-001..008` | `routing/verifier.py` | separate from the router that proposed the copper |
| Physical geometry rules `PB-PCB-001..007` | `physical/rules.py` | 49 geometry checks on the measured run |
| Manufacturing rules `PB-MFG-001..010` against a profile | `manufacturing/rules.py` | profile-driven, not board-specific |
| BOM aggregation, cost arithmetic, assembly classification | `bom/service.py` | 13 BOM lines; identity-safe; no network path |
| KiCad fabrication export plus integrity manifest | `manufacturing/exporter.py` | 8 Gerber/drill outputs and a `.gbrjob`, each SHA-256'd |
| Artifact fingerprinting and staleness across the whole chain | `eda/pcb_models.py`, `manufacturing/models.py` | `CircuitIR -> sch -> placed -> routed -> DRC -> profile -> fab`; a changed input makes the release `STALE` |
| Engineering Notebook event stream | `domain/events.py` | 513 events emitted on one run |
| Datasheet parse, candidate extraction, **independent source relocation**, semantic support, catalog merge | `datasheet/` | a citation checked and not found downgrades the claim to `UNKNOWN` |

**Measured run** (`POST /api/demo`, real KiCad): completes in about 75 s wall
clock, of which about 60 s is routing. Final state
`READY_FOR_MANUFACTURING_REVIEW`; KiCad DRC 0 violations / 0 unrouted; 8
fabrication outputs.

## 2. What is fixture, scripted, or single-project

| Claim the demo makes | What the code does | Where |
|---|---|---|
| "Requirements interpretation" | There is **no natural-language parsing anywhere in the repository**. `compile_requirements` is a pure field mapper over an already-structured object. | `generation/requirements.py` |
| "Evidence-grounded circuit generation" | The provider replays four canned payloads. The third payload **is the finished CircuitIR**, loaded from `broken_sensor_on_5v()`. No design is synthesised. | `generation/fixtures.py:38` |
| "Bounded circuit repair" | The repair payload is also canned: two literal `move_pin` operations. The *validation* of that patch is real; the *choice* is not. | `generation/fixtures.py:43-51` |
| User text changes the design | `require_demo_request` rejects any string not byte-identical to one 148-character sentence. The UI textarea is `readonly`. | `application/demo.py:34`, `apps/web/index.html:29` |
| Component placement | A literal dictionary of 20 reference designators mapped to hard-coded x/y millimetres. **There is no placement algorithm.** | `eda/kicad/placement.py:12` |
| Multiple projects | Every board-level CLI subcommand is declared `choices=["golden"]`. | `cli.py:484-492` |
| Catalog breadth | **9 parts.** By test-enforced policy no entry may claim `DATASHEET_SUPPORTED`; all seed facts are `CATALOG_REPORTED`. | `catalog/data/parts/`, decision 7 |
| Footprint coverage | **8 footprints.** 8 of the 16 catalog package entries cannot be PCB-compiled at all, including the second regulator (`MCP1700`, whose `Package_TO_SOT_SMD:SOT-23` is unregistered) and every 0402/0603/1206 passive. Swapping the LDO for the other catalog part fails at PCB compile. | `physical/footprints.py` |
| Prices | `unit_price = 0.05 x (line index + 1)`. BME280 is deliberately priced `UNKNOWN`. The UI labels the whole block `SYNTHETIC FIXTURE - NOT LIVE SUPPLIER DATA`. | `bom/service.py:21-27` |
| Manufacturing profile | `prototype_profile()` is synthetic and marked so in its provenance. | `manufacturing/models.py` |
| Teaching | **One** hard-coded lesson, emitted only when a `PB-PWR-001` CRITICAL appears in the repair set. The measured run produced exactly 1 lesson. | `generation/orchestrator.py:105` |
| Evidence table in the UI | Six rows, hard-coded to the BME280's supply rails. | `application/demo.py:_evidence_rows` |

## 3. What does not exist at all

- **No LLM.** The only runtime dependencies are `pydantic` and `PyMuPDF`.
  Nothing in the repository reads `ANTHROPIC_API_KEY`; `.env.example` says so
  itself. `RecordingLlmProvider` deliberately has no free-text method.
- **No accounts, users, sessions, or authentication.**
- **No database.** Jobs are a `dict` guarded by a `threading.Lock` inside one
  process (`scripts/demo_server.py:165`); artifacts land in `out/demo-jobs/<id>`
  on local disk. A restart loses everything, by explicit design.
- **No queue.** Work runs on a `daemon=True` `threading.Thread`.
- **No isolation.** `kicad-cli` is spawned as a subprocess in the same user
  context as the web server. There is no container, sandbox, or egress control.
- **No file-upload path in the product.** Datasheet ingestion exists as a CLI
  command and a library. There is no HTTP endpoint, size cap, or type check.
- **No safety refusal path.** `RequirementsSpec.safety_domains` is **never
  populated by any code path**. `is_supported_scope` therefore reduces to
  "input voltage <= 12 V", which the schema already enforces as `le=12`, so an
  out-of-envelope request surfaces as a `REQUIREMENTS_INVALID` schema error
  rather than an explained refusal. Nothing detects "mains", "LiPo charger", or
  "motor driver".
- **No simulation.** ngspice is `UNAVAILABLE`; spike S2 is open.
- **No supplier integration, stock, lifecycle, or MOQ data beyond the fixture.**
- **No version history, comparison, or project persistence.**
- **No hardware has ever been fabricated or bench-tested.** The verification
  ladder reports `Bench verification: NOT_YET_VERIFIED`, which is correct.

## 4. Product-shaped problems visible in the measured run

1. **The notebook is 513 raw events.** Phase counts: 151 placed-PCB, 151
   routed-PCB, 133 routing, 39 design, plus 13 cost, 12 release, 10
   manufacturing. The most frequent event kind is `pad_binding_resolved` (204).
   It renders as one flat timeline. That is a log, not an explanation.
2. **The verification ladder is 17 rows**, 8 of them
   `Ohmni semantic verification - <subsystem>` carrying an identical detail
   string, and 3 reading `UNSUPPORTED` (thermal, eda, simulation) with no
   explanation of why an unsupported row is an acceptable outcome.
3. **Routing dominates runtime** (about 60 s of 75 s) and has no product-level
   time budget. A harder board has no defined failure mode other than "slower".
4. **One lesson.** The learning product is a single paragraph.
5. **The screen is organised by pipeline stage.** The first thing a beginner
   reads is a nav rail saying Overview / Repair / Evidence / Notebook /
   Artifacts / BOM & cost / Release.

## 5. Governance state at audit time

- Latest completed product milestone: **M8** at `3a6f9d3`, independently
  reviewed `PASSED` (`M8-REV-INDEPENDENT-FINAL-BOUNDED`), with `M8-R06`
  retained as an accepted LOW risk.
- `active_product_milestone: null`; `proposed_product_milestones` was empty
  before this package. **There is no human-approved next product milestone.**
- Approved scope at audit time is `M8-REGRESSION-2`, a post-milestone
  regression fix, with `M8-RG02` `IN_PROGRESS` and uncommitted work present.
  `scripts/ai_state.py validate` reports `VALID` and `Recovery: RESUME`.
