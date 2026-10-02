# Architecture

Ohmni is an evidence-first AI electronics engineering mentor. The architecture
supports a path from idea and requirements through evidence-grounded circuit
design, verification, simulation, EDA artifacts, prototyping and learning. The
current MVP remains the low-voltage PCB vertical slice; this broader positioning
does not expand its implementation scope.

## High-level design

Frontend -> API -> Orchestrator -> Typed domain services -> EDA / simulation / verification tools

### Services

- Intent service
- Datasheet ingestion service
- Component knowledge service
- Part resolver
- Circuit planner
- Circuit verifier
- Schematic compiler
- Simulation runner
- Cost optimizer
- Lesson generator
- Artifact exporter

## Critical design rule

No important subsystem should pass unconstrained prose to another subsystem.

Use typed contracts.

Example flow:

`UserRequest`
-> `RequirementsSpec`
-> `ComponentSpec[]`
-> `ArchitectureProposal`
-> `CircuitIR`
-> `VerificationReport`
-> `SimulationReport`
-> `CostReport`
-> `ArtifactBundle`
-> `EngineeringNotebook`

Milestone 4 implements the first bounded generation slice. A provider-neutral
structured-output adapter may propose requirements, architecture, `CircuitIR`, and
typed repair operations. Catalog/pin validation and the deterministic verifier remain
the authority. Only an export-eligible semantic circuit reaches the KiCad compiler.

Physical intent is a separate pure layer: `BoardConstraints`, placements, footprint
and pad bindings never enter `CircuitIR`. The deterministic PCB adapter consumes the
verified circuit plus the exact schematic fingerprint, emits a fingerprinted two-layer
board, runs pure geometry rules, and then invokes KiCad DRC as an independent verifier.

## Recommended stack

Frontend:
- Next.js
- React
- Tailwind
- shadcn/ui optional

Backend:
- Python
- FastAPI
- Pydantic

Domain graph:
- NetworkX or custom graph model

EDA:
- KiCad CLI
- SKiDL or custom emitter
- optional Freerouting CLI

Simulation:
- ngspice

Datasheets:
- PyMuPDF
- structured extraction
- page-aware citations

Persistence:
- SQLite for hackathon
- PostgreSQL later

Async:
- start synchronous
- only add queueing if jobs become too slow

## LLM responsibilities

The LLM may:
- interpret intent
- extract candidate structured facts
- propose architecture
- suggest component alternatives
- propose repairs
- generate educational explanations

The LLM may not be final authority for:
- pin mappings
- voltage limits
- absolute maximum ratings
- MPN existence
- ERC / DRC results
- simulation output
- arithmetic
- lifecycle state
- real-time availability

## Provenance

Every extracted fact should store:

- source document id
- manufacturer
- part number
- datasheet revision
- page number
- source text snippet or structured region reference
- extraction confidence
- verifier status

## Deterministic routing boundary

Routing is separate from electrical and placement intent. `CircuitIR` remains
the netlist. A fingerprint-bound `PlacementRequest` records functional groups,
exact capacitor ownership, edge preferences, and antenna exclusion. The bounded
functional placement search generates `BoardConstraints`; it does not select
coordinates from a reference-designator table. `RoutingPlan` owns tracks and
through-vias. A bounded deterministic A* router proposes copper and an
independent connectivity verifier checks it before KiCad emission. KiCad DRC is
a separate external verifier. Routing has no LLM, network, or randomness path.

Physical verification evaluates every requested constraint, including rotated
body/pad envelopes and exact capacitor-pad proximity. The separately pinned
ESP32 body envelope includes the antenna extension omitted by the original pad
subset. A geometric antenna exclusion does not establish RF performance. An
unrecognized or malformed constraint returns ERROR and blocks release.

Product routing has a finite wall-clock budget. Exhaustion preserves diagnostics,
marks every unfinished net `ROUTING_INCOMPLETE`, and prevents DRC/release from
proceeding. Successful geometry is deterministic; elapsed time is not part of
its fingerprint. Repeated physical lands for one electrical pin each require
copper connectivity. Quality projections use emitted copper length/vias, while
unrouted net-span estimates are labeled separately.
## Manufacturing and release boundary

`ohmni.manufacturing` evaluates an immutable routed `PcbArtifact` against one
provenance-bearing `ManufacturingProfile`. It cannot change electrical or
physical intent. The bounded KiCad exporter is the only manufacturing module
allowed to spawn a process. BOM aggregation, supplier identity checking, cost
arithmetic, assembly classification, manufacturing rules, and release gating
are deterministic and have no LLM or network dependency.

Release lineage is `CircuitIR -> schematic -> placed PCB -> RoutingPlan ->
routed PCB -> DRC -> ManufacturingProfile -> fabrication package`. A changed
PCB, profile, missing output, or mismatched hash makes the release stale.

## End-user application boundary

`ohmni.application` projects existing typed reports into a frontend-safe demo
contract. It orchestrates existing services but contains no electrical,
physical, routing, manufacturing, or pricing verdict logic. The static web
client formats statuses and artifact-derived geometry; it never computes
engineering PASS/FAIL. The separate learning exercise calls the electrical
verifier on a controlled practice circuit and projects its findings.

`ohmni.synthesis` compiles validated A1 sensor, A2 GPIO and A3 SPI briefs into
electrical and separate physical intent without a model or fixture import.
`application.projects` currently exposes the original A1 choices and orchestrates
that result through generated placement and the shared engineering pipeline.
The broader family editor/API integration follows in M10-T04.
The fixed reference demonstration retains its separate scripted provider.

The local threaded server persists projects, immutable revision inputs, and job
attempts through SQLite in `application.project_store`. One OS file lock owns
each output workspace; interrupted jobs fail explicitly on recovery. This is a
local single-workspace boundary, not multi-user authorization. Publication and
download checks bind saved brief, derived circuit, report, and fabrication
lineage. Build ZIPs contain verified buffers and authoritative revision metadata.

## Component synthesis boundary

`ohmni.domain.component_synthesis` holds the trust boundary as data. Everything a
model may return lives under `ExtractionProposal`; none of its schemas has a
field for a verdict, an `Evidence`, a status, a catalog identifier or a file
path, and an architecture test asserts that for every provider-facing schema.
Dimensions are held as exact printed decimals on an integer nanometre grid, so a
unit is never inferred from a magnitude and a pitch never accumulates binary
float error. One tested boundary converts to Ohmni's float millimetres.

The stages are separate packages in one direction. `datasheet/observations.py`
and `datasheet/pdf.py` record immutable observations of the source: word tokens,
the tables' own printed rules, drawn shapes, and locally rendered pages, each
with stable IDs under one observation digest. Page size, render pixel count and
content-stream length are preflighted before `get_pixmap` or `get_text` runs, and
an over-long token is rejected rather than truncated.

Because the parsed bytes are untrusted, that parse may also run out of process.
`datasheet/isolated_observations.py` is the only module in `datasheet/` allowed
to start a child, and it does so through the same `adapters.process.run_tool`
the EDA paths use, which owns the wall clock. The child,
`datasheet/observation_worker.py`, applies an address-space cap to itself —
`adapters/resource_limits.py`, a Windows job object or a POSIX `RLIMIT_AS` —
*before* the parser library is imported or any document byte is read, and
refuses to parse at all if no cap could be applied. A worker that times out,
crashes, or exits zero without writing a bundle is an error, never an empty
observation; the parent streams the file's digest itself, without materialising
the document, and checks every returned image against the digest the bundle
records. An architecture test pins that ordering. A timeout bounds duration, not
allocation; the cap is the half that bounds a decompression bomb. The isolated
path is opt-in — `scripts/component_cad_proof.py` is its only caller, and
`ohmni ingest-datasheet` still parses in process; see VERIFICATION.md. `datasheet/multimodal.py` declares
a provider-neutral vision port; concrete providers live in `adapters/`, and a
proposal is accepted only when it is schema-valid and its locators address this
document. Addressability is not support.

`datasheet/constraint_verifier.py` is the only module that may decide a claim is
supported. It is pure: no provider, no filesystem, no clock, no network, and no
knowledge of CAD. It reconstructs a table from the rules the document prints and
binds each value to its row, dimension symbol, MIN/NOM/MAX column and declared
units; a value printed across the limit columns is read as a basic dimension
rather than assigned to whichever column its centre is nearest. Drawing geometry
supplies topology only — which lands exist and how they line up — because a
drawing may not be to scale. Receipts are constructed here and nowhere else, and
`VerifiedConstraintSet` refuses to hold a claim whose receipt is unsupported or
whose digests name a different document.

CAD generation reads only that verified set. `physical/land_patterns.py`
compiles it to exact nanometre geometry, `eda/kicad/component_assets.py`
serialises byte-exact KiCad 10 assets, `eda/kicad/component_asset_parser.py`
measures the emitted bytes back without importing the generator, and
`physical/component_asset_verifier.py` compares those measurements against the
verified source constraints. The dependency runs `eda -> physical`, so the
measurement contracts live in `physical/asset_measurements.py`.
`eda/kicad/component_harness.py` asks KiCad to load and render the artifacts
through the existing bounded process runner; unavailable, failed or empty runs
are never a pass. No admitted catalog row is produced by any of this: component
admission is a separate later gate.
