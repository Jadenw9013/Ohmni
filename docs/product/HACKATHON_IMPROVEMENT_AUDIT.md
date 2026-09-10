# Ohmni hackathon improvement audit

**Audited at:** commit `df41225`, 2026-09-04  
**Purpose:** durable handoff for a later AI session. This document records the
current product assessment and recommended improvements; it does not approve or
start a product milestone.

## Executive verdict

Ohmni has an unusually strong deterministic verification foundation and a
polished explanation layer. Its central weakness is that it currently looks
like a board-design product while actually being a sophisticated replay of one
pre-authored design.

The next level is not another broad UI rewrite. It is:

1. making the design genuinely derived;
2. making the PCB physically credible;
3. proving the design on real hardware; and
4. turning the deterministic verifier into the memorable center of the demo.

The current product is best described as a polished deterministic circuit
verification showcase, not yet a general board-design product.

## What is already strong

- 24 deterministic rules with explicit verified, partially verified,
  unsupported, not-applicable, and unknown outcomes.
- Real KiCad schematic generation, PCB generation, ERC/DRC ingestion, Gerber
  and drill export, integrity manifests, and artifact fingerprints.
- A real bounded two-layer router followed by an independent copper
  connectivity verifier.
- Strong evidence and limitation disclosure. The UI clearly distinguishes what
  ran from what was not analysed.
- A compelling interactive board, system decomposition, signal-flow,
  failure/repair, confidence, and bring-up experience.
- A well-defended architecture in which the frontend presents engineering
  results but does not invent them.
- A substantial automated test corpus.

These are real differentiators. Future work should preserve them rather than
replacing the verifier with model-generated confidence.

## Verified repository and demo snapshot

At the time of this audit:

- Branch: `main`
- HEAD: `df41225`
- Upstream: `origin/main`
- AI development state: valid, with no interrupted task
- Fast test equivalent with an explicitly writable pytest temporary directory:
  `483 passed, 10 deselected`
- Verifier corpus: all 14 fixtures behaved as intended with 100% rule coverage
- Normal local KiCad probe: KiCad CLI 10.0.5 available
- Live HTTP demo: completed all eight progress stages and reached 100%
- Final routed PCB: KiCad DRC reported 0 violations and 0 unrouted items
- Release lineage: current and ready for human manufacturing review
- Demo endpoint: `http://127.0.0.1:8765`
- Exactly one confirmed Ohmni demo process owned port 8765 when the audit ended

The canonical fast check initially produced pytest temporary-directory access
errors inside a constrained audit sandbox. Running the same test selection with
a writable `--basetemp` passed all 483 selected tests. This was an execution
environment issue, not a repository regression.

No implementation change or product milestone was started during the audit.

## Major improvements

### 1. Replace the scripted board with bounded deterministic synthesis — P0

The application accepts one byte-identical request in
`src/ohmni/application/demo.py:39-43`. The provider in
`src/ohmni/generation/fixtures.py:14-48` queues the interpreted requirements,
architecture, complete faulty circuit, and repair response. The verifier and
EDA pipeline are real, but the design itself is replayed.

Build a typed brief and three bounded archetypes that derive components,
passives, nets, and values from catalog facts. A language model is not required
for this step. Identical briefs must produce identical `CircuitIR` hashes;
changing the sensor, interfaces, or constraints must produce a meaningfully
different circuit and board.

**Judge-visible proof:** run three visibly different supported briefs and show
three different schematics, layouts, BOMs, and artifact fingerprints.

### 2. Make repair selection real — P0

The verifier genuinely detects the BME280 voltage error, but the demonstrated
repair is two literal `move_pin` operations in
`src/ohmni/generation/fixtures.py:43-44`.

Implement a deterministic repair planner over a small safe operation set:
move a pin, add a passive, change a passive value, swap a compatible part, or
refuse. Repairs must cite the active findings, make a minimal change, and pass a
complete re-verification.

**Judge-visible proof:** inject several existing fixture defects and show Ohmni
derive a different repair for each, or clearly explain why it cannot repair one.

### 3. Replace the hard-coded placement table — P0

All component positions are literal coordinates in
`src/ohmni/eda/kicad/placement.py:12-26`. The real router is therefore operating
on a hand-authored starting point rather than a generated placement.

Add a deterministic constraint-driven placer with edge placement, component
proximity, orientation, thermal separation, antenna, manufacturability, and
compactness objectives. Placement should expose both the selected coordinates
and the reason each constraint was satisfied.

**Judge-visible proof:** animate the constraints while three different boards
are placed, then report placement quality metrics before routing.

### 4. Make the PCB electrically credible, not merely DRC-clean — P0

The fixture says the GND net uses a bottom-layer ground plane in
`src/ohmni/fixtures/esp32_env_logger.py:181`, but the compiler emits no copper
zones, as documented in `docs/product/VISUALIZATION_ARCHITECTURE.md:243`.
There is also no ESP32 antenna keepout or RF placement rule.

Add ground pours, stitching vias, ESP32 antenna clearance, sensible return
paths, decoupling geometry, and board-edge constraints. Add design objectives
for board area, total route length, and via count. The present 19-part design is
spread across a 100 x 70 mm board and uses 296 track segments, 41 vias, and
approximately 1.08 m of copper, which looks inefficient for such a simple
board.

**Judge-visible proof:** show the ground zone and antenna keepout in the 3D
view, plus before/after route length, via count, and board-area metrics.

### 5. Close the requirements-to-verdict loop — P0

The confirmed brief records an approximately $20 budget and a hand-soldering
preference. The final report nevertheless shows a known purchase requirement
of $23 before the unknown sensor price, fabrication, or shipping, and the
BME280 LGA-8 package requires hot air or reflow.

`budget_usd` is retained in `src/ohmni/generation/requirements.py:24-33`, but it
is not consumed by a budget verifier or release gate. Hand soldering is checked
by `PB-ID-005` in `src/ohmni/verifier/rules/identity.py:190-237`, but only as a
warning.

Introduce requirement strength such as `MUST`, `SHOULD`, and `PREFERENCE`.
Every confirmed brief item must finish as `MET`, `VIOLATED`, or `UNKNOWN`, with
an explicit effect on release readiness. Define whether the budget means
consumed BOM cost, actual MOQ purchase cost, or complete first-prototype cost.

**Judge-visible proof:** a requirements coverage panel where every requested
constraint has a traced outcome and no requirement silently disappears.

### 6. Fabricate and bench-test the board — P0

No Ohmni-designed board has been fabricated or measured. The product correctly
reports this in `src/ohmni/application/demo.py:305` and
`docs/product/PRODUCT_V1.md:79-82`, but it is now the largest remaining
credibility gap.

Order several boards. Record assembly outcomes, current draw, the 3.3 V rail,
LED current, I2C address, sensor readings, failures, and predicted-versus-
measured results. Convert every discrepancy into a tracked rule gap, design
defect, assembly issue, or fabrication issue.

**Judge-visible proof:** place the physical board beside the application and
stream its live sensor data while displaying Ohmni's predictions against the
measurements.

### 7. Clarify whether Ohmni is currently a designer or verifier — P0

The landing page says Ohmni works out the required parts and wires them together
in `apps/web/index.html:33-42`. It also honestly says that only one project is
built, but the primary promise still exceeds the implementation. The package
description calls Ohmni an AI mentor in `pyproject.toml:8`, although the runtime
has no production model provider.

Until synthesis exists, position the current version as a deterministic circuit
compiler and verification mentor demonstrating one complete reference design.
After synthesis is real, restore the broader description-driven promise. Do not
use an LLM as the electrical source of truth.

**Judge-visible proof:** the opening screen states exactly what is live today,
and the user can immediately demonstrate it without encountering disabled
examples that carry the main product promise.

### 8. Turn catalog citations into machine-verified evidence — P1

The live evidence disclosure states that the demo's manufacturer references
were entered by hand, lack captured verbatim snippets, and have not been
machine-verified. The repository has a real PDF ingestion and source relocation
pipeline, but the seed catalog is deliberately `CATALOG_REPORTED`, not
`DATASHEET_SUPPORTED`; see `src/ohmni/catalog/__init__.py`.

Ship pinned source documents for supported parts, verified source spans, and
controlled catalog upgrades. Let the user open the exact page region that
supports a voltage or current claim.

**Judge-visible proof:** click “3.6 V maximum” and jump to the highlighted
manufacturer passage, with a verified content hash and page location.

### 9. Expand the usable catalog and footprint coverage — P1

The catalog contains nine parts. `src/ohmni/physical/footprints.py:1-34`
explicitly retains only geometry needed by the golden project. Eight of the 16
advertised catalog package entries were reported as unable to compile at the
PCB layer, including several passive sizes and the alternative regulator.

Expand to approximately 30 carefully selected parts with complete symbol,
footprint, evidence, placement, and manufacturing support. Add tested
substitutions rather than simply adding more JSON entries.

**Judge-visible proof:** compare an LGA sensor, a more hand-assemblable module,
and a lower-cost alternative, and show all downstream changes.

### 10. Replace synthetic economics and manufacturing rules — P1

Prices are generated from `0.05 * (line index + 1)` in
`src/ohmni/bom/service.py:21-27`. The manufacturing profile is explicitly a
synthetic stand-in in `src/ohmni/manufacturing/models.py:28`.

Use a dated distributor data snapshot and one real fabricator's published
capabilities. A live supplier API is optional for a hackathon; cached,
provenance-bearing data is enough. Include PCB fabrication and shipping in the
prototype-cost definition or label them clearly as excluded.

**Judge-visible proof:** show an orderable BOM and fab configuration with source
name, capture date, quantity breaks, availability knowledge, and explicit
unknowns.

### 11. Make the demo faster and operationally diagnosable — P1

The measured pipeline takes roughly 75-120 seconds, with routing dominating.
During the audit, a constrained server process caused KiCad ERC to exceed its
60-second timeout. The public result was only `pipeline_failed` because
`scripts/demo_server.py:212-226` intentionally collapses every worker exception,
while `apps/web/app.js:45` tells the user to inspect a server terminal that only
contains the generic diagnostic code.

Preserve safe public errors, but add operator-only structured diagnostics and
stage-specific codes such as `ERC_TIMEOUT`, `ROUTING_TIMEOUT`, and
`DRC_FAILED`. Add startup preflight, per-stage time budgets, cancellation, and a
truthful `ROUTING_INCOMPLETE` outcome. During long routing, show elapsed time,
completed connections, current net, and the evolving copper rather than a
mostly static progress screen.

**Judge-visible proof:** a cold run either completes within a defined budget or
ends with a precise, recoverable failure that identifies the stage and next
action.

### 12. Eliminate the 21 KiCad ERC warnings — P1

The successful audited run reported 21 identical `lib_symbol_issues` warnings:
the current KiCad configuration does not include the `ohmni` symbol library.
This leaves the most visible independent schematic check at
`PASS_WITH_WARNINGS`, even though the warnings share one setup cause.

Fix the emitted library identity/configuration or make the artifact fully
self-contained in the form KiCad expects. At minimum, deduplicate identical
configuration findings in the user presentation while preserving the raw
report.

**Judge-visible proof:** KiCad ERC reaches a clean result, or presents one
specific and understandable configuration warning rather than 21 copies.

### 13. Add iteration, persistence, and version comparison — P1

The current flow does not let users edit the confirmed brief, replace a part,
compare versions, or revisit a project. Jobs live in an in-memory dictionary
and run on daemon threads in `scripts/demo_server.py:166-179`; restarting the
process loses them.

A small SQLite-backed project and run model is enough initially. Let users
change one requirement and see the resulting requirement, schematic, board,
cost, evidence, and fingerprint diff. Reuse the existing lineage model to mark
old artifacts stale.

**Judge-visible proof:** change one sensor or constraint and show exactly what
changed, why, and which artifacts were invalidated.

### 14. Turn the verifier into an interactive failure laboratory — P1, high wow

The repository already has 13 intentionally broken variants covering voltage,
I2C pull-ups, decoupling, LED current limiting, regulator capacity, USB-C CC
resistors, floating pins, package identity, and invented pins.

Expose selected faults as a judge-controlled mode. Animate the affected net,
the deterministic finding cascade, the supporting evidence, and the repair.
This demonstrates genuinely general logic even before full synthesis exists.

**Judge-visible proof:** a judge can deliberately break the board in several
ways and watch different rules catch each error without changing the verifier's
answer through prompting.

### 15. Complete the user's purpose with firmware and live telemetry — P2, high wow

Ohmni currently produces hardware only. An environmental logger is not useful
until firmware reads the sensor and communicates the result.

After the physical board is validated, generate a minimal, pinned ESP32 firmware
project for the supported design: BME280 readout, status LED behavior, serial
output, build metadata, and a small telemetry panel. Keep firmware-generation
claims separate from PCB verification and show which parts are templates versus
derived configuration.

**Judge-visible proof:** download or flash the firmware and watch live
temperature and humidity readings appear in the Ohmni project.

### 16. Prove generality with a public benchmark — P1

The 14 existing fixtures are one golden circuit plus 13 mutations, not 14
independent designs. They strongly validate the verifier but do not validate
design generation, placement, or routing generality.

Create a benchmark across at least three archetypes and multiple parameter
combinations. Track synthesis success, semantic verification, placement
success, routing completion, DRC, runtime, determinism, and out-of-envelope
refusal accuracy.

**Judge-visible proof:** publish a compact scorecard with reproducible cases,
thresholds, failures, and artifact links rather than claiming broad capability
from one happy path.

### 17. Reduce implementation and documentation drift — P2

`apps/web/app.js` is approximately 49 KB and
`src/ohmni/application/product.py` is approximately 56 KB, concentrating much
of the experience in two large modules. Public documents also disagree on the
test count: `README.md:56` says 457, `docs/product/ROADMAP.md:369` says 465, the
latest recorded remediation says 482, and this audit observed 483 selected fast
tests. `docs/product/PRODUCT_V1.md:3` still says `PROPOSED` even though the
current product experience has been implemented.

Split the large modules by responsibility and generate status statistics from
the repository's durable verification records. Refresh or supersede the older
capability audit so later sessions do not treat pre-current evidence as current.

**Judge-visible proof:** one generated project-status page consistently reports
the current commit, capabilities, limitations, test counts, and demo evidence.

## Recommended hackathon sequence

If time is limited, prioritize work in this order:

1. Real bounded synthesis for three visibly different boards.
2. Requirement closure for budget and assembly constraints.
3. Ground plane, antenna keepout, and compact constraint-driven placement.
4. Fabricate one design and display live sensor telemetry.
5. Add the interactive failure laboratory.
6. Replace hand-entered evidence and synthetic manufacturing data.
7. Remove the 21 ERC warnings and shorten the run.

Physical board fabrication should begin as soon as a design is suitable because
lead time can run in parallel with software work.

## Suggested acceptance gates for a “next-level” demo

- Three supported briefs produce three distinct deterministic designs.
- Identical briefs reproduce identical semantic and artifact fingerprints.
- Every confirmed requirement is reported as met, violated, or unknown.
- Every supported design uses a generated placement, ground zone, and relevant
  module keepouts.
- At least 90% of an agreed in-envelope benchmark reaches semantic export
  eligibility and DRC 0/0 without manual edits.
- Every agreed out-of-envelope case is refused with a specific explanation.
- At least one Ohmni-generated board is assembled and bench-measured.
- The demo shows at least one predicted-versus-measured electrical value.
- Datasheet claims shown as verified carry machine-verified source spans.
- Pricing and manufacturing claims name a real source and capture date.
- A normal live run completes within a declared time budget or terminates with
  a truthful stage-specific failure.
- The independent KiCad checks no longer show 21 repeated symbol-library
  warnings.

## Guidance for the next AI session

1. Treat this document as recommendation and evidence, not milestone approval.
2. Begin by reading `AGENTS.md`, `.ai/state.yaml`, `.ai/checkpoint.yaml`, and the
   active task ledger.
3. Re-run `scripts/ai_state.py validate` and inspect repository status before
   changing anything.
4. Do not infer permission to start a proposed milestone. Obtain explicit human
   approval for the selected scope and record it through the repository's AI
   workflow.
5. Preserve the verifier's fail-closed behavior, provenance model, independent
   KiCad checks, and frontend no-verdict boundary.
6. Prefer a narrow end-to-end capability with measurable acceptance criteria
   over additional broad UI polish.
7. Keep the user-visible distinction between verified, calculated, assumed,
   unknown, unsupported, and not-yet-bench-verified results.
8. Do not claim arbitrary hardware support, successful fabrication, live
   pricing, simulation, or physical verification until the corresponding
   evidence exists.

