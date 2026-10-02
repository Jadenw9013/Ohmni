# Dynamic Multimodal Component Synthesis

Status: **PROPOSED — implementation awaits explicit human approval**  
Prepared: 2026-09-14  
Repository baseline inspected: `d7b1175`, branch `codex/personal-sensor-projects`

This document fulfills the user's request to inspect the architecture and plan
the feature before writing implementation code. It proposes a new scope,
`COMPONENT-SYNTHESIS-1`; it does not approve that scope, start its tasks, change
the active catalog, or authorize deployment. Existing milestone history and the
parked `M10-T05` checkpoint remain authoritative.

## 1. Outcome and engineering contract

Allow a user to attach a manufacturer datasheet for a part absent from Ohmni's
catalog. Ohmni should extract candidate identity, electrical, pin, and mechanical
information; independently check its support in the source; deterministically
generate KiCad assets; verify the actual emitted files; and admit an immutable
component revision for the operations it demonstrably supports. A paused design
can then resume against a new, explicit catalog snapshot.

The target is new part numbers without handwritten per-part Python or hidden
catalog fixtures. Reusable package geometry, source-layout grammars, electrical
device rules, and simulator primitives remain bounded, tested algorithms. A new
part number is not necessarily a new package family or a newly supported class
of circuit behavior.

**LLMs propose; evidence grounds; deterministic systems verify.** This requires
four distinctions throughout the implementation:

1. JSON schema validity is not evidence that an extracted dimension is correct.
2. Matching a footprint to model-produced JSON proves consistency with that JSON,
   not agreement with the datasheet. Source and semantic checks must happen first.
3. Datasheet/package conformance is not complete IPC compliance, soldering yield,
   thermal adequacy, or successful hardware operation.
4. A SPICE deck that parses or converges is not a validated model of an unknown
   microchip. Simulation has separate provenance, coverage, and fidelity gates.

The runtime will use specialized agent roles coordinated by a typed state
machine. Agents exchange bounded proposals, evidence references, concise
decision summaries, and tool reports. Agent agreement, confidence scores, or
reasoning narratives never constitute verification.

## 2. Repository findings and reuse

The as-built code takes precedence over older roadmap descriptions of what
already works. In particular, simulation code exists despite historical
`UNSUPPORTED` descriptions, but it has no verified arbitrary vendor-model path.

| Existing seam | What exists | Required change |
|---|---|---|
| `src/ohmni/datasheet/pdf.py` | `PyMuPdfExtractor.load()` hashes PDF bytes, limits bytes/pages, records text spans/regions; image-only PDFs are explicitly unsupported by this path. Identity discovery recognizes Bosch/BME280/BMP280. | Preserve text behavior; add separately typed rendered-page/vector/table observations and general identity candidates. |
| `src/ohmni/domain/document.py` | Document fingerprints, metadata, pages, spans, and regions. | Extend provenance with renderer/parser version, page transforms, stable token/cell/feature IDs, and observation hashes. |
| `src/ohmni/datasheet/extract.py` | `CandidateExtractor` and a deliberately narrow `BoundedTextExtractor`. | Add a provider-neutral multimodal proposal adapter; keep source text/images as data. |
| `src/ohmni/datasheet/verify.py` | Independent source relocation and bounded electrical text checks. Matching can be fuzzy; context includes preceding spans. | New admission needs exact row/column/feature/applicability verification; reuse the separation, not broad text membership as a universal proof. |
| `src/ohmni/datasheet/pipeline.py`, `merge.py` | Extract, verify, and attach evidence to an existing `ComponentSpec`; preserve conflicts. Required facts currently include I2C-specific fields. | Construct new parts only from checked claims; derive required facts from device/package/use profiles. |
| `src/ohmni/domain/component.py` | Electrical `ComponentSpec`, pins, supply rails, packages, regulator facts. | Preserve electrical/physical separation; add relational and adjustable-regulator semantics where required. Do not accept permissive defaults as complete evidence. |
| `src/ohmni/catalog/loader.py` | `JsonPartCatalog`; `default_catalog()` caches bundled JSON. | Add a persistent synthesized-part store and immutable combined snapshots. There is no current SQLite component catalog. |
| `src/ohmni/application/database.py`, `project_store.py` | SQLite project/revision/job persistence. | Versioned migrations for component imports, catalog revisions, and durable design suspension. |
| `src/ohmni/eda/kicad/compiler.py` | Generic embedded schematic symbols derived from component pins. | Extract a reusable deterministic symbol builder and standalone `.kicad_sym` export; preserve existing schematic semantics. |
| `src/ohmni/physical/footprints.py` | Pinned project-local `FOOTPRINTS` geometry and geometry fingerprints. | Inject a revision-bound asset resolver through placement, compilation, routing, verification, and release. Do not mutate the global registry. |
| `src/ohmni/generation/orchestrator.py` | `DesignOrchestrator.design()` rejects unavailable required parts before architecture generation. | Add structured missing-part requests and a resumable component-resolution stage before this rejection. |
| `src/ohmni/application/demo.py`, `physical/sensor_layout.py` | `run_proposed` uses `sensor_board_constraints`, which assumes the authored sensor-board references. | Build placement requests from validated functional intent and admitted asset geometry, not reference-designator positions. |
| `src/ohmni/application/projects.py`, `synthesis/peripherals.py` | The guided A1/A2/A3 flows have fixed family choices, including `SUPPORTED_I2C_PARTS`. | Add an explicit dynamic design path; a new catalog row must not silently alter the guided family contract. |
| `src/ohmni/eda/simulation.py` | KiCad netlist export, bounded ngspice operating-point/transient execution; model presence is classified as an approximation. | Add model manifests, exact pin bindings, coverage, provenance, and behavioral validation. Preserve explicit unavailable/failure results. |
| `src/ohmni/verifier/engine.py`, MCP service | General semantic report identity does not yet bind an immutable catalog snapshot; MCP already carries additional catalog/verifier hashes. | Bind changed facts and their revisions into new verification/run lineage without rewriting historical reports. |

`tests/test_architecture.py` currently bans model/network imports throughout
`datasheet/`, limits PyMuPDF imports there to `pdf.py`, and keeps domain,
electrical, physical, routing, and manufacturing checks isolated. Preserve these
boundaries: the SDK implementation belongs under `adapters/`; the adapter under
`datasheet/` calls an injected typed provider port. Never relax the blanket
deterministic verifier restrictions to accommodate vision.

Legacy `Evidence.status` and `provenance_machine_verified` are not sufficient
catalog-admission predicates. The former can represent an unchecked historical
citation; the latter records source relocation without proving every new
mechanical/electrical association. New admission requires explicit verification
receipts. Existing evidence semantics are not silently rewritten.

## 3. Scope and staged support

### First complete vertical slice

- One exact manufacturer/MPN/package selection per import, including documented
  family-to-package applicability and revision.
- Text-bearing PDF pin tables and explicit dimensional tables or manufacturer
  recommended land-pattern drawings with mechanically checkable associations.
- For the first CAD proof, explicit manufacturer-recommended land dimensions are
  required. Package terminal dimensions alone are insufficient; deriving lands
  instead requires a separately validated policy and all its tolerance inputs.
- Generic SOT-23-style and SOIC-style rectangular SMD pad families first. The
  initial proof uses one family; the second demonstrates reusable geometry.
- A previously uncataloged device whose required electrical behavior fits an
  existing supported profile, with all required facts independently checked.
- Real `.kicad_mod`, `.kicad_sym`, source receipts, asset measurements, and an
  immutable local catalog entry; restart-safe resume through existing semantic,
  ERC, placement, routing, DRC, and manufacturing gates.
- Simulation eligibility is reported separately. A first CAD-capable part may
  have `simulation: UNSUPPORTED`; that is not completion of the later model slice.

### Subsequent slices within the proposed plan

- A bounded QFN/QFP asset extension after explicit pad equivalence, paste-window,
  mask, orientation, and manufacturing-policy support. These families become
  usable only if their own source and geometry acceptance cases pass.
- Vendor-model ingestion and bounded model validation; evidence-derived
  behavioral approximations only for implemented behavior profiles.
- The requested LM317 example, initially targeting a verified SOT-223 package
  selection with explicit output/tab mapping, adjustable-feedback derivation,
  application conditions, and a separately checked SPICE model. TO-220/TO-263
  support is not implied by support for that package.

Arbitrary scanned drawings, BGAs, arbitrary custom pads, RF/high-speed behavior,
switch-mode control loops, and unrestricted unknown-chip behavioral synthesis
are outside the first support envelope. They produce diagnostic candidates and
explicit unsupported/review states. This plan does not promise a safe autonomous
result from every possible datasheet.

## 4. Typed contracts and module layout

Proposed names below are implementation targets, not files already present.

| Location | Responsibility |
|---|---|
| `domain/component_synthesis.py` | Frozen, strict contracts for import requests, constraints, pin bindings, receipts, manifests, capabilities, and state transitions. Domain imports no infrastructure. |
| `datasheet/pdf.py` | Bounded PDF parsing/rendering and original-source observations. |
| `datasheet/multimodal.py` | Provider-neutral extraction adapter and candidate orchestration. |
| `adapters/vision_provider.py`, `adapters/anthropic_vision.py` | Vision capability port and SDK transport, schema enforcement, payload limits, usage accounting. |
| `datasheet/constraint_verifier.py` | Pure source/semantic verification over immutable observations and candidate claims. No provider, filesystem, clock, or network access. |
| `physical/land_patterns.py` | Deterministic package/land-pattern calculations from verified constraints and versioned policies. |
| `physical/component_asset_verifier.py` | Pure geometry and pin-binding checks over parsed emitted artifacts and verified constraints. |
| `eda/kicad/component_assets.py` | Deterministic symbol and footprint serialization. Reuse supported S-expression infrastructure. |
| `eda/kicad/component_asset_parser.py` | Independent, bounded structural parsing/measurement of actual artifact bytes. |
| `catalog/component_store.py`, `catalog/snapshot.py` | SQLite persistence, admission transactions, immutable asset/catalog snapshots. Persistence stays outside pure checks. |
| `application/component_synthesis.py` | Runtime state machine; coordinates extraction, verification, CAD, native tools, and admission. |
| `generation/models.py`, `orchestrator.py` | Typed unresolved-part requests and suspension/resume results; no provider SDK or direct catalog writes. |
| `eda/spice_models.py` | Model manifests, safe supported-deck handling, pin maps, and test harness integration through existing bounded tool runners. |

Keep this distinct from `src/ohmni/synthesis`, the existing pure A1/A2/A3 circuit
compiler. Do not turn that package into a model-driven datasheet subsystem.

### Proposal schemas

Pydantic contracts will use `extra='forbid'`, explicit enums, bounded collections,
finite numeric checks, and JSON Schema generation. Provider output cannot carry
`Evidence`, verification status, approval flags, active-catalog IDs, executable
code, file paths, or arbitrary S-expressions.

| Contract | Required content |
|---|---|
| `ComponentImportRequest` | Import ID, workspace, user-requested identity, selected document IDs, exact package when known, requested operations, permitted source policy, resource budget. |
| `DocumentObservationBundle` | Raw document digest; parser/renderer versions; page dimensions/rotation; PDF-to-image transform; render digest; immutable spans, tokens, table cells, vector features, and original text. |
| `SourceLocator` | Document/page/observation IDs, bounding region in PDF coordinates, token/cell/feature IDs, source quote, table/drawing identifiers. All are candidate locators until checked. |
| `IdentityCandidate` | Manufacturer, base device, exact MPN, package code, pin count, revision, variant conditions, identity source locators. Unknown is explicit. |
| `PhysicalConstraintCandidate` | Package family; body and terminal dimensions; pitch; min/nominal/max/tolerance; original units; dimension symbol/datum; drawing view; pin-1/orientation; recommended land pattern separately from package terminals. |
| `ElectricalConstraintCandidate` | Pin number/name/type/function, NC/reserved requirements, supply references, operating versus absolute limits, applicable conditions, relations between pins/rails, required external components, supported functional profile. |
| `PinBindingCandidate` | Logical terminal, datasheet labels, symbol pin number, physical pad IDs, repeated-pad equivalence, tab/exposed-pad connectivity, mechanical-only features. |
| `VerificationReceipt` | Checked claim hash, document/observation hashes, selected variant, rule/version, outcome, actual measurements, limits/margins, dependencies, reasons, unresolved conditions. Constructed only by deterministic checking. |
| `ComponentAssetManifest` | Component revision and verified-constraint hash; symbol/footprint bytes and parsed-geometry hashes; source/policy/compiler/parser versions; native-tool reports; capability matrix and limitations. |
| `SpiceModelManifest` | Model bytes and source/license, exact supported identity, dialect, subcircuit terminal order, model class/fidelity, supported analyses and domains, harness/results hashes, exclusions. |

Dimensions use exact decimal/rational source values and a documented integer
length grid internally, proposed at one nanometre. Convert mm/inch/mil explicitly;
never infer a unit from number size. Quantization tolerance is separate from
manufacturing tolerance and is recorded. Existing float-based physical APIs need
one tested conversion boundary, not repeated rounding throughout the pipeline.

Keep missing minimum/maximum/nominal values missing. Enforce ordering where values
are present; do not invent tolerances, voltage limits, pin roles, hand-soldering
support, or thermal-pad connectivity from package appearance.

## 5. Extraction and independent evidence verification

### Source handling

1. Accept PDF upload or an already-authorized source document. Store exact bytes
   by content digest and record acquisition origin. A hash proves identity of
   bytes, not manufacturer authenticity.
2. T01 defines the initial origin policy: acquisition from configured official
   manufacturer HTTPS domains, redirect destinations restricted to the same
   reviewed source list, acquisition URL/redirect log retained, and exact bytes
   pinned. Uploaded bytes can inherit that acquisition provenance only on an
   exact digest match. This records an observed manufacturer distribution source,
   not a cryptographic guarantee of silicon identity. Selected-device/package
   applicability still requires separate source checks. A local file with an
   unestablished origin remains labeled as supplied/unverified until resolved.
3. Parse in a bounded worker: byte/page/pixel limits, time and memory budgets,
   no embedded script execution or arbitrary attachment extraction. Keep the
   existing explicit encrypted/invalid/too-large statuses.
4. Render selected pages locally with reproducible DPI, rotation, crop, and
   coordinate transforms. Preserve text glyphs/table structure/vector paths as
   observations before invoking vision. A resource-limit failure produces no
   verified claims.
5. Route images and structured observations to the vision provider. Relevant-page
   discovery may propose regions, but omitted pages/notes cannot be interpreted
   as absence of constraints. Required-section coverage is itself checked.

Use a configured, available vision-capable model rather than pinning this design
to the user's example model names. Implement strict provider output plus local
validation and bounded schema repair. Native PDF support can aid navigation;
locally rendered images provide controllable coordinates for geometric locators.
Provider citations are candidate locators, not verification receipts. See the
[official PDF](https://platform.claude.com/docs/en/build-with-claude/pdf-support)
and [citation](https://platform.claude.com/docs/en/build-with-claude/citations)
documentation; native citations and strict structured-output modes must be
capability-tested rather than assumed to compose.

### Agent roles and permissible outputs

| Role | Produces | Authority |
|---|---|---|
| Identity/section discovery | Candidate identity, package choices, relevant sections and unresolved questions. | Cannot establish MPN existence from model memory. |
| Mechanical vision extractor | Dimension, view, feature, and land-pattern proposals with source locators. | Cannot approve geometry or choose undocumented tolerances. |
| Pin/electrical extractor | Pin table, limits, conditions, external-component and behavior-profile proposals. | Cannot create evidence or assign unsupported safe defaults. |
| Optional contradiction reviewer | Specific conflicting proposals or missing conditions. | May cause review; agreement never upgrades status. |
| Deterministic source verifier | Source and semantic receipts. | Sole automated source-support authority. |
| Deterministic CAD builder/checkers | Assets, measurements, rule findings, KiCad corroboration. | CAD conformance only; no claim of device behavior. |
| Application coordinator | Durable state transitions, bounded retries, user-visible summaries. | Cannot override failed admission gates. |

Mechanical and electrical extraction can run independently over the same pinned
document/package selection. Reconcile before compilation. A package change
invalidates both branches. No agent can invoke routing or activate catalog rows
directly.

### What a source verifier must establish

For each required claim, independently relocate the source and bind its meaning:

- A value belongs to the selected row and the correct min/typ/max column, under
  the applicable units and conditions. Finding the same number elsewhere fails.
- A dimension symbol is bound to the corresponding mechanical feature and
  selected package. An unrecognized arrow/label/feature association remains
  unsupported; proximity alone is insufficient.
- Pin number, name, electrical behavior, package column, orientation, and
  footnotes belong together. NC, reserved, DNC, tab, and exposed-pad semantics
  are preserved individually.
- Operating limits are distinct from absolute ratings; differential limits
  remain relations, not standalone supply values. Typical values do not become
  guaranteed extremes.
- Manufacturer recommended PCB lands are distinct from the metal lead/body
  dimensions. Pixel distances do not become engineering dimensions: drawings
  may be explicitly not to scale.

Implement bounded deterministic source-layout grammars and association rules,
with explicit unsupported results outside them. OCR output and model-rendered
regions remain observations/proposals. Agreement between OCR and vision is not
automatic proof of ambiguous printed values or drawing semantics.

If source association cannot be checked, retain the import in quarantine and
show the exact highlighted PDF region and missing fact. A human review records
reviewer, reviewed document/claim hashes, decision, and a separately labeled
human-confirmed provenance record. It never sets `snippet_verified` or converts
human interpretation into machine verification. Mandatory automated gates cannot
be bypassed by clicking approve; a future policy for human-confirmed components
would retain a distinct capability/provenance tier.

The legacy text-upgrade path remains available. New-part construction consumes
only the strict receipts and required-fact matrix; it does not infer sufficiency
from a nonempty list of verified claims.

## 6. Deterministic CAD generation and geometric verification

### Generation

Compile verified constraints into separate `SymbolDefinition` and
`LandPatternDefinition` contracts. Generate plain UTF-8/LF S-expressions with
stable ordering, identifiers, numeric formatting, and exact output hashes.
Use an Ohmni generator identifier. The current shared `sexpr.number()` formats
only three decimal places; introduce an explicitly tested component-asset
precision policy without silently changing the serialization of existing boards.

Symbol generation retains explicit pin numbers/types and reference/value fields,
and derives readable pin placement using deterministic rules. Reuse the existing
inline-symbol builder so standalone and schematic-embedded exports represent
the same electrical terminals. No invisible power-pin shortcuts or silently
passive fallback pins may make ERC easier.

Footprint generation includes supported copper pads, masks/paste openings,
fabrication outline, courtyard, polarity/pin-1 indication, and assembly text.
Keep component body, lead extents, copper lands, and placement envelope separate.
Artwork stays clear of solderable regions. Unsupported custom geometry, slots,
drills, paste patterns, or thermal requirements block the corresponding use;
they are not flattened to a convenient rectangle.

Export a portable package containing the generated `.pretty/` footprint library,
`.kicad_sym`, necessary local library tables, provenance manifest, and receipts.
Never modify a user's global KiCad libraries. No generated 3D body is required
for electrical admission; any approximate body in the viewer remains labeled
as appearance, not dimensional evidence.

Extend the typed feature representation through PCB embedding, not just library
export. Current `KiCadPcbCompiler._render_footprint()` reconstructs a subset and
uses fixed SMD/layer/roundrect choices; asset-resolver injection alone would lose
verified mask/paste/fabrication/silkscreen details. Preserve supported features
through a validated serializer or the verified parsed feature representation.
Only placement transforms, reference labels, and checked net bindings may alter
an instantiated asset. Independently parse the resulting PCB and compare each
instance against the admitted footprint after transforming back to its local
frame. Recheck this after routed-board emission and before release. An
unrepresentable feature blocks PCB compilation rather than disappearing.

The implementation will target the installed KiCad 10 toolchain and its
[footprint format](https://dev-docs.kicad.org/en/file-formats/sexpr-footprint/)
and [symbol format](https://dev-docs.kicad.org/en/file-formats/sexpr-symbol-lib/).
Pin the emitted format and tested CLI version in each manifest.

### Independent checks of actual bytes

The verifier reparses the actual emitted `.kicad_mod` and `.kicad_sym` bytes.
It must not obtain its measurements from the generator's in-memory pad objects.
Sharing a low-level tokenizer is acceptable; sharing the generator's geometry
calculation as the only oracle is not. Unsupported or duplicate critical
S-expression fields, nonfinite values, excess nesting, or unexpected primitives
fail closed.

Proposed `CS-*` check families:

| Check | What it proves within the supported subset |
|---|---|
| `CS-SOURCE` | Required identity, source association, applicability, conditions, and claim receipts are complete and current. |
| `CS-PIN` | Complete symbol pin set and types; explicit mapping to every electrical pad; allowed repeated lands; no lost tab/NC or invented pin. |
| `CS-DIMENSION` | Measured pad centers, row pitch/span, size, rotation, drill where supported, and exposed-pad location satisfy verified constraints and the selected land-pattern policy. |
| `CS-ORIENTATION` | Pin-1 position, numbering sequence, top/bottom view transform, and package frame match the source; mirrored numbering cannot pass a pitch-only test. |
| `CS-GEOMETRY` | Valid body/courtyard/pad envelopes, no unintended copper overlap, explicit mask/paste constraints, and required fabrication/assembly details. |
| `CS-LINEAGE` | Exact constraints, source, policy, compiler, emitted bytes, and parsed geometry match the receipts; no stale or replaced file is accepted. |
| `CS-KICAD` | KiCad loads/render-exports the assets and the generated test schematic/PCB; ERC/DRC reports bind to exact harness artifacts. |

For a uniform row, independently compare each measured adjacent center spacing
to the required nominal pitch within the documented numerical tolerance. Check
the full row span, two-dimensional orientation, pad dimensions, and numbering
separately. Source min/max variation contributes to the land-pattern fit/tolerance
calculation; it is not permission to choose arbitrary pitch or ignore lead fit.

Two example geometric predicates, deliberately not IPC formulas:

- Adjacent center separation: `abs(measured_pitch - design_pitch) <= epsilon`.
- Edge gap for aligned rectangular pads: `measured_pitch - (width_a + width_b)/2`,
  compared to a separately specified copper/mask manufacturing requirement.

Pad fit checks additionally account for component terminal bounds, fabrication
and placement tolerance, and the chosen land-pattern method. Different pad
orientations require transformed geometry, not the aligned-row shortcut.

KiCad has CLI footprint/symbol SVG export and schematic ERC/PCB DRC; use those
with controlled harnesses and parsed reports. There is no assumption of a
standalone `footprint verify` command. Syntax acceptance, a picture, and an empty
DRC report from an unconnected board are each insufficient alone. See the
[KiCad 10 CLI manual](https://docs.kicad.org/10.0/en/cli/cli.html).

### IPC claim boundary

Call the initial result **datasheet and land-pattern geometric conformance**.
The official [IPC document revision table](https://www.electronics.org/ipc-document-revision-table)
lists IPC-7351 as no longer maintained and lists IPC-7352 as a land-pattern design
guideline. Matching pad pitch does not establish either standard's full scope.

Provide a separate versioned `LandPatternPolicy` for manufacturer-recommended
lands and for any later standards-derived calculation. Manufacturer policy is
the initial preferred path. Standards-based generation requires authorized
access to the selected standard/revision, explicit package-family applicability,
density/assembly choices, tolerance inputs, traceable implemented rule coverage,
and independently checked reference calculations. Do not invent IPC formulas or
silently copy an unlicensed standard into the repository. If the necessary
standard or inputs are absent, that method returns `UNSUPPORTED`; an eligible
manufacturer-recommended method may still run with its own honest label.

## 7. Catalog admission, persistence, and lineage

Separate lifecycle from capability. Imports may be `RECEIVED`, `EXTRACTING`,
`CANDIDATES_READY`, `VERIFYING_SOURCE`, `NEEDS_REVIEW`, `GENERATING_ASSETS`,
`VERIFYING_ASSETS`, `ADMITTED`, `REJECTED`, `FAILED`, or `CANCELLED`.
Admission does not set a single universal component `VERIFIED` flag.

Capabilities include `identity_supported`, `symbol_supported`,
`footprint_supported`, `electrical_profile_supported`, `routing_supported`, and
`simulation_supported`, each with rule coverage and limitations. Required
unknowns block the affected capability; optional facts stay unknown without
inventing zero values. Discovery may show quarantined candidates only through a
separate diagnostic view; active design selection only sees eligible revisions.

Automatic board eligibility requires all of:

- Exact identity/package and every required source/semantic receipt accepted.
- No unresolved required-fact conflicts, unknown pin roles, or unsupported
  electrical behavior needed by the requested use.
- Both asset checks accepted, with complete logical-terminal/physical-pad mapping.
- An asset family supported by the current placement/router/manufacturing subset.
- Native-tool corroboration required by the admission policy actually ran.
- Exact artifact/policy versions and hashes validated at the transaction boundary.

Passing `not report.export_blocked` alone is insufficient: current semantic
reports may still contain `INSUFFICIENT_DATA`. Admission and design continuation
must evaluate the required-fact matrix, applicable-rule outcomes, and required
coverage explicitly. All-pass on an empty or inapplicable report cannot admit a
part.

Proposed SQLite records: `component_imports`, `component_documents`,
`component_candidates`, `component_revisions`, `component_assets`,
`component_verifications`, `component_model_revisions`, `catalog_snapshots`, and
`design_component_dependencies`. Store immutable report/asset digests plus
normalized serialized contracts; keep raw PDFs/large assets in workspace-local
content-addressed storage. Snapshot entries pin exact component and asset
revisions, not mutable names alone.

Commit verified blobs to their immutable location before publishing a SQLite
transaction that references them. Recheck hashes at admission; use uniqueness
constraints and per-import idempotency keys to prevent duplicate publication.
A crash before the transaction leaves unreachable blobs, not a partial active
part. Recovery fails or retries incomplete work explicitly. Migrations are
versioned and rollback-tested; no long database transaction spans an LLM/native
tool call.

Combine the bundled catalog with workspace-admitted immutable revisions through
the existing `PartCatalog` protocol. Preserve bundled data and its reported
provenance. Reject ambiguous collisions; never overwrite a seed or accepted
revision based on a model suggestion. Inject matching immutable asset resolvers
instead of changing `FOOTPRINTS` or trying to clear a process-global cache.

Bind provenance along this chain:

`PDF + observations -> claims + receipts -> verified constraints -> asset bytes
-> admitted revision -> catalog/asset snapshot -> CircuitIR + semantic report
-> schematic/ERC -> placement -> routed PCB/routing report/DRC -> release`.

The circuit's own electrical-intent hash remains distinct. Add catalog, rule-set,
and asset digests to report/run context rather than placing physical geometry
inside `CircuitIR`. Tests must prove that changing a component fact invalidates
dependent reports even when the circuit topology is unchanged. Older projects
continue to use their saved revision; revocation is explicit and blocks new
verified releases instead of rewriting history.

## 8. Orchestrator pause and resume

1. Interpret the user request into typed requirements as today. Split missing
   component resolution from unrelated requirement conflicts; do not weaken
   operating-envelope or safety rejections.
2. If a requested part is absent, return a typed `ComponentResolutionRequest`
   containing requested identity, needed capability, and available documents.
   Do not ask the model to fabricate a catalog entry inside `CircuitIR`.
3. Persist `WAITING_FOR_COMPONENT` with prompt/requirements hashes, the original
   catalog snapshot, import dependencies, budgets, and continuation stage.
4. If no applicable PDF is present, surface `DATASHEET_REQUIRED`. If several
   package variants fit, surface `PACKAGE_SELECTION_REQUIRED`. Source discovery
   can propose manufacturer documents through a separate authorized adapter;
   fetching unknown URLs from PDF content is not part of a verifier.
5. Execute component synthesis outside semantic verification/routing. Proposed
   initial limits are three new-part imports per design and two extraction
   retries per stage, with separately configured page, token, cost, and time
   ceilings. Limit exhaustion records a reason and stops; it never relaxes gates.
6. After admission, build a new immutable catalog/asset snapshot explicitly
   extending the paused design's snapshot with the approved revisions. Refresh
   evidence/pin context and regenerate dependent architecture/circuit proposals;
   never reuse a proposal verified against different component facts.
7. Rerun catalog references, requirement checks, electrical coverage, and semantic
   verification before schematic compilation. Then rerun ERC, generated placement,
   physical checks, routing connectivity, DRC, and manufacturing/release lineage.
8. If another new dependency appears, handle it within the same bounded state
   machine; detect cycles and duplicate requests. Cancellation, crash recovery,
   import rejection, revoked revisions, and simultaneous imports have explicit
   outcomes. The old in-memory background thread is not the only record of work.

Free-text board integration must replace its reference-position dependency with
a validated functional `PlacementRequest`: supply/decoupling ownership, connector
edge requirements, package/body keepouts, board envelope, and supported routing
constraints. Feed this into the existing bounded deterministic placement/router.
The current generated-placement implementation accepts only `(0,)` as its
allowed-rotation tuple. The first board slice stays within that orientation
subset and reports incompatible constraints; arbitrary placement rotations are
not claimed merely because the footprint parser understands rotation.
Do not reconnect the parked Freerouting path or authorize a general router
rewrite under this feature. An admitted part can still yield
`ROUTING_INCOMPLETE`; that blocks release as it does today.

Expose progress and evidence through the existing application/API projection:
requested part, exact package, current import stage, missing facts, cited PDF
regions, generated assets, separate capability statuses, and resume action.
Part learning panels read these records rather than invented descriptions.
Use an explicit versioned dynamic request path alongside the existing guided
family editor, rather than feeding arbitrary imported parts through
`SUPPORTED_I2C_PARTS`. Persist that path's requirements, snapshots, and status
through the project store. The guided editor retains its existing supported
choices until a separately tested schema change enables new ones.

Keep the MCP semantic boundary intact. Add explicit snapshot injection to
`mcp_server/service.py:SemanticService` so catalog discovery and `verify_circuit`
use the same admitted revisions and catalog hashes as the application. Verify
this with MCP-client tests and prevent a mid-call snapshot change. New import,
EDA, or SPICE MCP tools are not silently added here.

## 9. SPICE models: separate evidence and behavior pipeline

A datasheet does not uniquely specify a chip's internal behavior. The plan
supports these explicit paths:

| Model path | What may be emitted/admitted |
|---|---|
| Manufacturer model | Preserve exact source bytes/license and supported variants; verify subcircuit pin mapping, dialect compatibility, and a bounded behavior harness. Report vendor provenance separately from validation coverage. |
| Documented behavioral approximation | Deterministically compile a supported behavior profile from independently verified equations/parameters/conditions. A model may propose the profile; it cannot invent a validated transfer function. Always label approximation and excluded effects. |
| Unknown or unsupported behavior | Keep the model candidate quarantined or omit it; simulation remains unsupported. No ideal source substitution for an unmodeled regulator. |

Model ingestion must restrict directives/includes and their transitive files,
resolve only manifest-listed content hashes inside the workspace, and reject
shell/control execution, arbitrary file writes, recursive path escape, and
unsupported encrypted/model dialects. Run native tools with the existing bounded
process adapter plus a restricted worker workspace. `shell=False` alone does
not neutralize commands embedded in a simulator input language.
Compatibility and encrypted-model limitations are documented in the
[ngspice model guide](https://ngspice.sourceforge.io/modelparams.html); model
availability is not evidence that its dialect has passed our runner.

Build a deterministic harness per supported behavior profile: documented DC
points, input/load sweeps, and appropriate boundary cases first; transients only
with source-supported dynamics. Define expected ranges and acceptance tolerances
from independent datasheet conditions before running the model. A test computed
from the same generated model equation only proves implementation consistency.
Plot-only typical data remains typical evidence, not a guaranteed limit.

Wire the admitted model into actual design emission. The current schematic
compiler does not emit component model-library/subcircuit/terminal-order bindings,
so storing a manifest alone would still export bare device references. Add
revision-bound simulation bindings from each component instance to its admitted
model and logical-terminal map. Emit the required KiCad simulation properties
and portable hash-bound model/include files, then independently inspect the
exported deck to establish the exact subcircuit invocation and terminal order.
If the supported exporter cannot preserve those bindings, stop that integration
with a diagnostic rather than substitute another model. Maintain schematic/ERC
electrical semantics independently. End-to-end tests must exercise the actual
design deck as well as the isolated model harness.

Bind result hashes to model, source, simulator version, analysis, stimuli,
temperature/load/input domain, pin mapping, and assertion set. Record convergence,
finite outputs, device coverage, failed points, and unmodeled devices. A partial
subcircuit simulation explicitly names what was excluded; it cannot become
whole-board validation. Semiconductor/package thermal, RF, firmware, and bench
operation remain outside the resulting claim unless separately established.

### LM317 acceptance case

The request `Use a TI LM317 regulator` must first resolve an exact package and
document variant. The [TI datasheet](https://www.ti.com/lit/gpn/LM317) includes
package-specific tab/output mapping, differential voltage conditions, and
external adjustment requirements. The bare family name is not enough to select
pad geometry or operating limits. The [TI product page](https://www.ti.com/product/LM317)
also offers a manufacturer PSpice model; its ngspice compatibility must be tested,
not assumed from its availability.

`RegulatorSpec.fixed_output` exists, but current voltage derivation uses the
catalog output range and does not implement arbitrary feedback-network behavior.
Before routing an LM317 design as supported, add typed adjustable-regulator
constraints and pure topology/value derivation. Check the actual output-to-adjust
and adjust-to-reference resistor network, documented reference/adjust current,
tolerances, minimum load, input-output headroom, capacitor/protection conditions,
and operating domain. Do not interpret an input-minus-output rating as an
absolute ground-referenced input limit. Tab equivalence must map to the actual
electrical terminal, never a guessed ground connection.

Unsupported application or thermal conditions remain explicit and may block the
requested capability. First model acceptance is DC behavior within documented
conditions; a regulated DC result is not proof of startup or stability. This
case is a later full acceptance milestone, not the initial geometric proof.

## 10. Delivery sequence and approval checkpoints

All tasks below are **PROPOSED**. Dependencies are sequential unless stated.
After approval, record the human instruction durably in `.ai/approvals/`, add the
scope/tasks to `.ai/tasks.yaml`, and select work under `docs/AI_WORKFLOW.md`.
Do not reactivate `M10-T05` or rewrite accepted milestones.

| Task | Depends on | Deliverable and exit condition |
|---|---|---|
| `CS-T01` Contracts and trust gates | Human plan approval | Typed schemas, source/claim/asset identity, capability matrix, architecture tests, initial source corpus and annotated independent expected values. No model-generated evidence fields accepted. |
| `CS-T02` Source and vision proof | T01 | Bounded local PDF rendering and vision adapter. One uncataloged package's pin/dimension candidates shown with source regions; malformed/ambiguous output stays unverified. Recorded provider responses make tests offline. |
| `CS-T03` Independent source verification | T02 | Exact supported table/drawing grammars, identity/variant checks, units/conditions, and rejection corpus. Wrong-but-consistent model output fails. Unsupported image-only cases remain quarantined. |
| `CS-T04` One-package CAD proof | T03 | One parameterized package -> standalone symbol/footprint -> independent byte parse/measure -> KiCad harness. Show actual KiCad renders beside source crops and a deliberately wrong-pitch failure. No catalog admission yet. |
| `CS-T05` Reusable asset library | T04 | Second initial family, then bounded QFN/QFP exposed-pad cases, portable exports, immutable asset resolver; pad/orientation/geometry mutations. Unsupported paste/thermal policy blocks affected packages. New supported dimensions do not require per-MPN source edits. |
| `CS-T06` Persistent admission infrastructure | T05 | SQLite migrations, immutable revisions, snapshots, report lineage, restart/idempotency/revocation tests. Exercise admission transactions with test receipts; real activation remains disabled until T07. Quarantine is never active discovery. |
| `CS-T07` Electrical profile and admission gates | T03, T06 | Construct `ComponentSpec` from checked claims; required-field/profile coverage gates and unsupported-function refusal. Enable real admission only after these gates pass. Existing catalog fixtures retain their truthful status. |
| `CS-T08` Resume and real board integration | T07 | Missing-part pause/import/resume, explicit dynamic project path, supported functional placement, API progress and MCP snapshot parity; one new supported part through semantic/ERC/routing/DRC/download with exact lineage. Negative requests cannot bypass import. |
| `CS-T09` SPICE model boundary | T07; integrates after T08 | Model provenance/pin-map/deck restrictions, vendor/approximation harnesses, actual design-deck model bindings, explicit unsupported cases, independent measured assertions. CAD-only support remains distinguishable. |
| `CS-T10` LM317 end-to-end | T08, T09 | Independently checked SOT-223 package/tab extension plus adjustable-feedback and conditional-limit rules; real vendor-model compatibility result; valid design and incorrect-divider/tab/limit negative cases. |
| `CS-T11` Acceptance and documentation | T10 | Full regression, held-out datasheet corpus, independent review, real source/asset/UI evidence, portable output/restart verification, complete limitations and operational instructions. |

T03 is the source-association go/no-go checkpoint; T04 is the first CAD proof.
If independent source association cannot be implemented for the chosen family,
stop automatic-admission work and return the measured failure and a narrower
proposal; never compensate with an extra approving LLM. Each subsequent
checkpoint must meet its own evidence gates
before dependent work starts. New package/behavior families beyond this plan
require a scoped proposal rather than an open-ended repair loop.

This work is local-first and must be testable without an active Fly service.
Hosting migration, paid provisioning, and deployment are separate from this
implementation approval. Network model evaluations are bounded, explicit runs;
the default automated suite uses recorded/scripted extraction proposals.

## 11. Verification and acceptance matrix

| Layer | Required tests/evidence |
|---|---|
| Schema and isolation | Extra verdict/evidence fields, null required fields, missing units, NaN/infinity, excess arrays/strings, prompt instructions in PDF, model timeout/refusal/truncated output. AST and runtime guards prevent network/model access in pure checks. |
| Source truth | Correct number in wrong row/column, swapped min/typ/max, operating versus absolute, wrong rail/differential relation, wrong package/revision, detached footnote, fabricated region, document substitution, image-only ambiguity. |
| Mechanical transforms | mm/inch/mil conversions, decimal/OCR mistakes, top/bottom and clockwise/counterclockwise numbering, changed origin/rotation, missing pin-1, incorrect exposed pad and tab equivalence. |
| CAD mutations | Wrong pitch/span/size/rotation, missing/extra/duplicate pad, unintended overlap, symbol pin swap/type change, malformed S-expression, unsafe path/name, stale hash and mismatched asset pair; loss/change of admitted features when embedded into placed or routed PCB. |
| Independent oracle | Independently transcribed source constraints and parsed-byte measurements; mutation tests that change both candidate and generated CAD together must still fail the source check. |
| Native tools | Actual KiCad asset SVG export plus connected schematic/PCB harness ERC/DRC; missing/crashed/timed-out tool never passes. Tests bind reports to the exact artifact hashes. |
| Persistence | Clean migration, restart with admitted part, duplicate concurrent imports, interrupted blob/transaction sequence, stale snapshot, conflict/revision handling, explicit revocation and unaffected old revisions. |
| Orchestration | Unknown-part request before architecture; required PDF/package selection; success resume; rejected import; cancellation; cycle/budget exhaustion; no silent substitute; unsupported electrical profile; no fixed-reference placement dependency. |
| Electrical and SPICE | Missing critical facts block; fixed versus adjustable output derivation; wrong feedback values/topology and tab connection; unsupported model, wrong pin order, escaped include, nonconvergence, empty/NaN results, unmodeled device and out-of-domain stimulus; actual exported design deck uses the admitted model/hash/terminal map. |
| End-to-end | New part absent from bundled JSON, admitted solely through checked import; restart; prompt -> board -> real reports -> portable download. Generated board uses exactly the admitted symbol, pad geometry, and pin map. |
| User-visible truth | Source highlights, generated KiCad image, capability/coverage state, missing facts, model provenance and plotted-domain limits. No blanket verified-chip badge or invented learning content. |

Corpus requirements: multiple public manufacturer PDFs with pinned digests,
exact variants and independent annotations; synthetic perturbations for failure
coverage; at least one held-out part/document per supported source/package
family; and explicit multi-variant, not-to-scale, image-only, exposed-pad, and
unsupported-model cases. Select the actual PDFs at T01 after checking availability
and redistribution rights. Tests must not pass solely on a made-up PDF authored
to match the parser. Acceptance is zero false admission in the defined negative
corpus, complete required-fact coverage for admitted parts, and successful real
tool runs for every claimed supported operation. This does not establish a zero
error rate for arbitrary unseen PDFs.

Planned test modules: `test_component_synthesis_contracts.py`,
`test_multimodal_datasheet.py`, `test_component_source_verification.py`,
`test_component_assets.py`, `test_component_catalog_store.py`,
`test_component_synthesis_resume.py`, `test_spice_model_admission.py`, plus
bounded/slow KiCad and full-board integration cases. Extend existing
`test_datasheet.py`, `test_evidence.py`, `test_architecture.py`, generation,
physical, routing, manufacturing, MCP-client, and project regression suites where
their contracts change.

Run the repository virtual environment and canonical checks: focused tests per
slice, `scripts/verify.py fast`, `integration`, and `full` at final acceptance;
`python -m ohmni verify-all`; `python -m ruff check .`; workflow validation after
ledger changes. Record exact commands, counts, versions, skips, commit, artifact
hashes, and limitations. Missing external tools mean an unverified integration
gate, not a completed milestone. No formatter/type-checker run is claimed unless
one is actually configured and executed.

## 12. Plan completion and approval request

Read `AGENTS.md`, `ARCHITECTURE.md`, all current `src/ohmni/datasheet` modules,
the relevant domain/generation/catalog/EDA/persistence boundaries, and the
development workflow. Checked repository state: validation passed; no interrupted
task or executable task exists under the completed deployment scope.

This turn creates this plan only. Implementation, schema migrations, catalog
activation, API changes, live model extraction, and deployment await approval.

Approval of this plan would authorize the staged `CS-T01` through `CS-T11` scope
and its stated fail-closed support envelope. The implementation must preserve
the first CAD proof checkpoint, separate SPICE gate, and explicit unsupported
results. It would not authorize claiming arbitrary-chip correctness or broad
IPC compliance, bypassing source evidence, or beginning unrelated roadmap work.
