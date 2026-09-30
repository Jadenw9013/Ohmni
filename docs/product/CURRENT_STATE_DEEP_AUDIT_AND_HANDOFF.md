# Ohmni current-state deep audit and AI handoff

**Audit date:** 2026-09-30  
**Repository snapshot:** `d7b1175` on `codex/personal-sensor-projects`  
**Working-tree state:** uncommitted component-synthesis work plus unrelated
reference-planning material  
**Purpose:** give a new Claude, Gemini, Codex, or human maintainer one truthful
starting point for deciding what Ohmni is, what is proven, what remains open,
and what may be worked on next.

**Subsequent implementation:** the human later approved the component atlas and
builder plan. The read-only library, stories and learning sandbox are tracked
in [COMPONENT_ATLAS_IMPLEMENTATION.md](COMPONENT_ATLAS_IMPLEMENTATION.md).
This audit retains the `d7b1175` baseline; its missing-library observations and
then-current scope selection are historical. The CS review and real-board
admission gates were not closed by that later work.

This is an audit, not an approval record. The development ledger under `.ai/`
remains authoritative for task execution and human approval. If this document
and the ledger disagree, stop and reconcile them; do not infer permission from
this document.

## 1. Executive verdict

Ohmni has a real and unusually disciplined deterministic electronics pipeline.
Within three bounded ESP32 board families it can compile typed requirements,
verify electrical intent, generate KiCad artifacts, place and route boards,
run independent artifact checks, persist project revisions, and present the
result in an educational interface. Its strongest asset is the separation of
proposal, evidence, and deterministic authority.

Ohmni is not yet a general AI electronics engineer, a proven manufacturing
system, or a hardware-validated product. The current implementation has five
release-blocking gaps:

1. The component-synthesis work is uncommitted and awaits independent review of
   its last seven fixes. CS-T01 through CS-T04 are `VERIFIED`, not `COMPLETE`.
2. The M10 product benchmark is incomplete and retains a real four-connection
   `NO_PATH` routing failure.
3. KiCad 10 is installed but hung during this audit. The canonical integration
   and corpus tiers could not be reproduced, and interrupted runs left child
   processes that required manual cleanup.
4. The top-level README and a commercialization handoff claim general dynamic
   AI design and SPICE behavior that the current code and verification manual
   explicitly mark bounded or `UNSUPPORTED`.
5. No fabricated board, assembled board, firmware run, electrical measurement,
   thermal check, EMC/RF check, or field test validates the generated hardware.

The next engineering move should be closure and truthfulness, not broader
feature expansion. Finish review and commit boundaries, make native-tool runs
reliable, complete the frozen synthesis benchmark, and build one measured board
before expanding the supported design envelope.

## 2. The project's main point

Ohmni's durable product idea is:

> **Build circuits. Understand why.** A model may propose an interpretation or
> design, source evidence must ground component facts, and deterministic systems
> must decide whether the resulting electrical and physical artifacts satisfy
> supported rules.

That produces a useful product only when all four layers stay connected:

1. **Intent:** capture what the user is trying to build and preserve ambiguity,
   assumptions, and unsupported requests.
2. **Evidence:** bind electrical and package claims to independently relocatable
   source regions, with explicit provenance and fidelity.
3. **Deterministic engineering:** verify semantic rules, compile EDA artifacts,
   measure emitted bytes, and corroborate with independent native tools.
4. **Learning and physical feedback:** explain the circuit from authoritative
   artifacts, then validate selected outputs on real hardware.

The repository is strongest in layer 3, has a carefully bounded start on layer
2, provides a credible educational interface for layer 4, and remains narrow in
layer 1. The physical-feedback half of layer 4 has not begun.

## 3. Authority and evidence used for this audit

Read these in this order before changing code:

1. `AGENTS.md`
2. `.ai/state.yaml`, `.ai/tasks.yaml`, `.ai/checkpoint.yaml`, and
   `.ai/reviews.yaml`
3. `ARCHITECTURE.md` and `VERIFICATION.md`
4. `docs/AI_WORKFLOW.md` and `docs/AI_REVIEW_PROTOCOL.md`
5. `docs/DECISIONS.md`
6. `COMPONENT_SYNTHESIS_PLAN.md` and `COMPONENT_SYNTHESIS_AUDIT.md`
7. This audit
8. The focused implementation document for the task being considered

The following documents are useful but are not current execution authority:

- `docs/product/PRODUCT_V1.md`, `ROADMAP.md`, `EVALUATION_PLAN.md`, and
  `DEPLOYMENT_PLAN.md` are explicitly **PROPOSED**.
- `docs/product/CAPABILITY_AUDIT.md` and
  `docs/product/HACKATHON_IMPROVEMENT_AUDIT.md` are historical snapshots. Many
  of their gaps have since been implemented.
- `docs/product/V2_COMMERCIALIZATION_HANDOFF.md` contains stale claims about
  SPICE and should not be used as an as-built description.
- The top-level `README.md` is a product pitch and currently overstates several
  implemented capabilities.

## 4. Truthful capability map

| Area | Current state | Evidence and boundary |
|---|---|---|
| Typed circuit domain and semantic verification | **Real** | Typed `CircuitIR`, evidence-aware claims, deterministic rules, complete/unknown/unsupported outcomes, and export gates exist. |
| Bounded circuit synthesis | **Real but narrow** | Three deterministic families: A1 I2C sensor, A2 GPIO controller, and A3 SPI memory. This is not unrestricted prompt-to-circuit generation. |
| Natural-language proposal | **Provider-dependent and bounded** | A structured provider path exists. The provider proposes requirements/architecture/circuit data; it does not establish evidence or verification. Routine tests use scripted/recorded providers. |
| Placement and routing | **Real but not milestone-complete** | Constraint-driven placement and bounded routing exist. The frozen M10 corpus still includes a four-net `NO_PATH` failure. |
| KiCad schematic/PCB compilation | **Real** | KiCad writers, parsers, artifact checks, ERC/DRC adapters, fabrication export, and historical native checks exist. Current local KiCad execution is unhealthy. |
| Personal projects | **Real local workflow** | SQLite stores projects, immutable revisions, jobs, and attempts for a local workspace. This is not multi-user authorization or a cloud service. |
| Educational PCB explorer | **Real** | Artifact-derived 3D/learning projections and 180 frontend tests exist. Visual tasks remain `VERIFIED`, not ledger-complete. |
| MCP semantic server | **Real and bounded** | Local stdio semantic verification exists. It is not a general EDA or SPICE service. |
| Component datasheet synthesis | **Proof only** | One real MCP73831 SOT-23-5 source/CAD proof exists. The last remediation is uncommitted and awaiting re-review. No imported component is admitted to active design use. |
| Component catalog | **Useful seed catalog** | Twelve part records and nineteen offered packages compile, but many claims are `CATALOG_REPORTED` or `ASSUMED`; the catalog is not a fully source-verified production library. |
| Manufacturing release | **Artifact generation only** | Gerber/drill/BOM-style outputs and a deterministic profile exist. Fabrication rules, pricing, availability, assembly yield, and total build cost are example/synthetic or unknown. |
| SPICE simulation | **Unsupported** | `VERIFICATION.md` states that SPICE is unimplemented and reports `UNSUPPORTED`; standalone ngspice was unavailable during this audit. |
| Firmware | **Absent** | No firmware generation, build, flashing, or board bring-up is part of the verified product. |
| Physical hardware validation | **Absent** | No board spin or bench evidence exists. Software checks cannot establish working hardware. |
| Production service | **Not established** | A prior commit was released to existing hosts, but the current working tree is local, dirty, and not release-bound. No paid infrastructure work is authorized here. |

## 5. Progress against approved scopes

Ledger status on 2026-09-30:

| Scope | Ledger state | Audit interpretation |
|---|---|---|
| M8 | 5 `COMPLETE` | Historical deterministic core milestone is complete. |
| M9 | 4 `COMPLETE` | Historical product slice is complete. |
| M10 | 4 `COMPLETE`, 1 `BLOCKED` | Synthesis families, placement, routing bounds, and project workflow exist; final benchmark/review does not. |
| MCP-SEMANTIC-1 | 1 `COMPLETE` | Bounded semantic MCP slice complete. |
| PCB-EXPLORER-1 | 1 `COMPLETE` | Explorer scope complete. |
| VIS-REF-001 | 2 `VERIFIED` | Implemented and tested, but no recorded completion transition. |
| DEPLOY-1 | 1 `COMPLETE` | Applies to commit `d7b1175`, not the current uncommitted tree. |
| COMPONENT-SYNTHESIS-1 | 4 `VERIFIED`, 7 `APPROVED` | CS-T01–T04 await re-review and commit. CS-T05–T11 have approval but cannot execute until dependencies become `COMPLETE`. |

### Component-synthesis checkpoint

- **CS-T01 — contracts and trust gates:** implemented and verified.
- **CS-T02 — source and vision proof:** implemented and verified with recorded
  responses; live Anthropic vision remains unevaluated.
- **CS-T03 — independent source verification:** implemented and verified for the
  bounded MCP73831 grammar/corpus.
- **CS-T04 — one-package CAD proof:** implemented and historically corroborated
  by KiCad, with adversarial geometry checks.
- **Independent audit:** originally found six defects, including evidence replay,
  stale SVG output, and PDF resource-bound weaknesses.
- **Remediation review:** raised CS2-001 through CS2-016, then NEW-1 through
  NEW-7. All are recorded as fixed in the working tree.
- **Current stop condition:** the NEW-1 through NEW-7 fixes have not themselves
  received independent re-review. The entire change set is uncommitted.
- **CS-T05 hold:** the task has no blocker string, but its dependency CS-T04 is
  not `COMPLETE`; `ai_state.py next` correctly returns no executable task.

The task-level blocker text for CS-T01–T04 mentions the first remediation review
but not NEW-1 through NEW-7. `.ai/state.yaml`, `.ai/checkpoint.yaml`, and
`.ai/reviews.yaml` carry the newer truth. Reconcile that wording during the next
review/ledger update so all four records describe the same gate.

## 6. Verification performed during this audit

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe scripts\ai_state.py validate` | **PASS** — ledger valid; no recovery required. |
| `.venv\Scripts\python.exe scripts\ai_state.py next` | **PASS** — no executable task; five tasks reported blocked. |
| `.venv\Scripts\python.exe scripts\verify.py fast` | **PASS** — 1,693 passed, 49 deselected in 258.00 s. |
| `.venv\Scripts\python.exe scripts\verify.py workflow` | **PASS** — 11 passed. |
| `.venv\Scripts\python.exe -m ruff check .` | **PASS** — all checks passed. |
| `.venv\Scripts\python.exe -m ohmni verify-all` | **PASS** — 14/14 fixtures behaved as expected; all 13 mutations were caught. |
| `npm test` in `apps/web` | **PASS** — 180 passed, 0 failed. |
| `.venv\Scripts\python.exe -m ohmni doctor` | **FAIL/UNAVAILABLE** — KiCad 10 CLI was found but `--version` timed out after 20 s; standalone ngspice unavailable. |
| `.venv\Scripts\python.exe scripts\verify.py integration` | **NOT COMPLETED** — stalled during native-tool work and was interrupted. |
| `.venv\Scripts\python.exe scripts\verify.py corpus` | **NOT COMPLETED** — emitted 38 early test dots, then made no visible progress for more than two minutes and ignored repeated interrupt signals. |
| `git diff --check` | **PASS** — no whitespace errors; Git emitted only a line-ending warning for `ARCHITECTURE.md`. |

The latest durable remediation record reports 1,693 fast, 108 corpus, 30
integration with 2 skips, 11 workflow, 14/14 fixtures, and 36/36 component-proof
checks with KiCad ERC/DRC. Those results belong to the recorded uncommitted
snapshot from 2026-09-15. This audit reproduced the non-native tiers but did not
reproduce the native corpus/integration results. Do not silently substitute the
historical green record for a current native-tool run.

During interruption, descendants from the audit-started Python/KiCad runs
remained alive, and a KiCad child respawned under the still-running corpus
process. Repeated Ctrl+C input did not end that process tree; its exact
audit-started PIDs were manually terminated. Two delayed Ohmni Python
descendants then appeared after the first cleanup and also required termination.
`adapters.process.run_tool` already
contains bounded waits and best-effort Windows tree cleanup, but this observation
shows that cancellation and descendant ownership are not yet proven reliable for
the canonical suites. After cleanup, only unrelated Python processes from
`C:\Dev\Automa` remained.

## 7. Findings and required fixes

### P0 — release and trust blockers

#### AUDIT-001: The active component-synthesis change has no stable review or commit boundary

**Evidence:** HEAD is still `d7b1175`; Git reports 13 modified tracked files and
53 individual untracked files when untracked directories are expanded. The
latest verification and review records explicitly say `uncommitted working tree`.

**Risk:** tests, evidence images, review findings, and code can drift together.
There is no immutable revision another agent can reproduce or safely review.

**Required fix:** obtain an independent review of NEW-1 through NEW-7 against
the current bytes, resolve any findings, rerun the required gates with working
KiCad, update all ledger records consistently, and commit one coherent
component-synthesis unit. Preserve unrelated reference-planning files.

**Exit gate:** CS-T01–T04 have commit-bound verification, no open blocker/high
review finding, and ledger transitions justified by the review protocol.

#### AUDIT-002: Public capability claims exceed implemented behavior

**Evidence:** `README.md` says a typed idea becomes a “verified,
manufacturable” board, names Claude 3.5 Sonnet as autonomous circuit designer,
claims automatic transient ngspice simulation, and describes MCP as “real
physics.” `VERIFICATION.md` says SPICE is unimplemented. The supported product
is three bounded families, and manufacturing/price data remain synthetic or
unknown. `docs/product/V2_COMMERCIALIZATION_HANDOFF.md` repeats the SPICE claim.

**Risk:** users and future agents will plan from false premises and may present
software geometry checks as hardware or physics validation.

**Required fix:** rewrite the README and stale handoff around the truthful
capability table in this audit. Use “manufacturing artifacts” instead of
“manufacturable” unless a named profile and its limits are stated. Describe the
three supported families, model proposal boundary, lack of SPICE, and lack of
bench evidence.

**Exit gate:** every public claim maps to an implemented path and a current
verification record; unsupported functions are visible before a user depends on
them.

#### AUDIT-003: Native KiCad execution is not operationally reliable in the current environment

**Evidence:** `ohmni doctor` found KiCad at
`C:\Users\wongj\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe` but timed
out on `--version`. Integration and corpus tiers stalled. The corpus process
ignored repeated interrupts, retained descendants, and continued respawning a
KiCad child until the audit-started process tree was manually terminated.

**Risk:** a CI or local job can consume workers indefinitely, report stale
progress, or require manual cleanup. A passing historical EDA result does not
show that current artifacts can be checked now.

**Required fix:** diagnose the KiCad installation/configuration separately from
the product code; add a fast native-tool health preflight; make cancellation kill
the full process tree under test; include stage/time diagnostics; and ensure a
timeout is reported as unavailable/failed, never skipped or passed.

**Exit gate:** `doctor`, corpus, and integration finish twice from a clean
process table, including a forced timeout/cancellation test that leaves no
descendants.

#### AUDIT-004: M10 is not complete and the frozen product benchmark has a real failure

**Evidence:** M10-T05 is `BLOCKED`. Its acceptance requires 54/60 accepted cases
to reach DRC 0/0 and a passing profile, all refusal cases, deterministic
artifacts, full tiers, and independent review. The ledger retains four
`NO_PATH` connections for `job9f2f15c4f068`. The benchmark also predates the
approved A2 optional-sensor behavior, so its R-18 expectation conflicts with the
current family contract.

**Risk:** individual demos can look convincing while unsupported combinations,
routing regressions, or changed refusal semantics remain unmeasured.

**Required fix:** do not rewrite historical results. Under explicit ledger
authorization, version the benchmark expectation for the changed A2 contract,
retain the failing case, fix or truthfully reject the four-net route, run fresh
output directories, and complete independent review.

**Exit gate:** M10-T05 satisfies its recorded acceptance criteria on a
commit-bound run; every changed benchmark case has a documented contract reason.

#### AUDIT-005: Untrusted PDF isolation is a proof-only path

**Evidence:** the resource-capped worker is called only by
`scripts/component_cad_proof.py`. `ohmni ingest-datasheet` still parses untrusted
PDFs in the main process. The Windows job-object cap was observed; the POSIX
`RLIMIT_AS` read-back path remains unobserved.

**Risk:** a normal user-facing ingest can bypass the exact resource boundary
added during remediation. Platform parity is assumed rather than demonstrated.

**Required fix:** before exposing general datasheet import, route the production
ingest through the isolated worker, preserve typed failure modes, test page/byte/
time/memory limits on Windows and POSIX, and record which quantity each platform
actually bounds.

**Exit gate:** no untrusted production PDF path imports a parser or reads
document bytes before its enforced bounds; platform-specific tests are observed,
not skipped and counted as coverage.

### P1 — product completion gaps

#### AUDIT-006: Component synthesis is not connected to catalog admission or board generation

CS-T01–T04 prove one SOT-23-5 source-to-CAD path. They do not provide a reusable
asset library, immutable admission store, electrical profile, project resume, or
active catalog entry. Those are CS-T05 through CS-T08. An imported asset must
remain quarantined until CS-T07 electrical admission succeeds.

**Recommendation:** after the P0 review/commit gate, execute approved tasks
strictly in dependency order. Do not let CAD geometry, model agreement, or a
successful KiCad parse stand in for source association and electrical coverage.

#### AUDIT-007: The source proof is intentionally narrow and live multimodal fidelity is unknown

The current corpus proves exact supported grammars for one Microchip datasheet
and package. Recorded fixtures now distinguish witnessed from reconstructed
capture, but no live Anthropic vision call has established an at-call identity.

**Recommendation:** keep routine tests recorded/scripted. Add a small,
explicitly budgeted live evaluation only when credentials and human approval are
available. Report cost, model/version, request identity, exact input digest,
capture kind, and failures. A model proposal remains non-evidence regardless of
provider agreement.

#### AUDIT-008: The seed catalog is broader than its strongest evidence

The catalog is useful for deterministic development, and all nineteen offered
packages compile. However, catalog-reported and assumed claims still feed the
bounded product. Generic parts are intentionally not specific purchasable MPNs.

**Recommendation:** prioritize source verification for the parts used by the
three canonical hardware candidates. Require identity, variant, package, pin,
absolute maximum, recommended operating, and application-condition coverage
before calling a part production-admitted. Keep supplier availability separate
from electrical truth.

#### AUDIT-009: “Manufacturing pass” is a profile check, not manufacturing proof

Gerber/drill generation and deterministic profile checks are valuable, but the
repository has no fabricator DFM result, assembly yield, stencil/paste review,
thermal validation, impedance stack-up, EMC/RF evidence, or physical fit check.
Budget stays `UNKNOWN` because prices, fabrication, delivery, tools, and total
build cost are not authoritative.

**Recommendation:** rename user-facing statuses so they identify the exact
profile checked. Integrate one real fabricator's current rules and quote as
dated external evidence. Keep price freshness and electrical evidence separate.

#### AUDIT-010: No physical feedback loop validates usefulness or operation

The proposed evaluation plan correctly says software cannot detect a verified
but useless board. No current test measures current draw, rail stability, sensor
communication, button/LED behavior, programming, RF performance, or thermal
behavior.

**Recommendation:** choose one board per supported archetype from benchmark
output without manual CAD edits. Fabricate at least the A1 board first, write
minimal bring-up firmware, publish a test fixture and measurement plan, record
failures as permanent regression cases, and budget for a second spin.

#### AUDIT-011: User-intent quality is not independently measured

The M10 corpus is a structured configuration benchmark, not a natural-language
accuracy or usefulness benchmark. Deterministic correctness can still produce a
board that does not solve the user's problem.

**Recommendation:** implement the proposed held-out request set only after M10
is closed. Separate interpretation accuracy, electrical validity, EDA success,
and user usefulness. Blind human review should happen before reviewers see PASS
labels.

#### AUDIT-012: Deployment evidence applies to an older clean commit

`DEPLOY-1` and the public-release history apply to `d7b1175`. Component synthesis
and its documentation are local working-tree changes. A deployed page cannot be
used as evidence for these changes.

**Recommendation:** after review and commit, create a release candidate with
commit-bound test records and artifact hashes. Deployment remains a separate
human-authorized action; do not provision paid infrastructure as part of cleanup.

### P2 — improvements after core closure

#### AUDIT-013: Documentation has accumulated contradictory eras

The product index still describes the pre-M9 application as a one-button,
single-board replay. Historical audits are useful, but they are easy for an
agent to mistake for present state. The commercialization handoff treats SPICE
as implemented.

**Recommendation:** mark every historical audit with its evaluated commit and a
link to this document. Maintain one generated capability/status page from the
ledger and verification records. Do not duplicate task status by hand in several
files.

#### AUDIT-014: Visual scope is verified but administratively unfinished

VIS-T01 and VIS-T02 are `VERIFIED`, while the associated implementation and
frontend suite are substantial. This is not a code defect, but it leaves scope
status ambiguous.

**Recommendation:** review the existing visual evidence against its completion
criteria and either transition the tasks through the workflow or record the
specific missing gate. Do not mark them complete merely because 180 frontend
tests pass.

#### AUDIT-015: Local persistence is not a multi-user product boundary

SQLite, one OS file lock, and local workspace identity are appropriate for the
current product. They do not provide authentication, authorization, tenant
isolation, distributed jobs, or recovery across hosts.

**Recommendation:** keep the local-first architecture until the engineering
benchmark and hardware loop are credible. If a hosted beta is later approved,
design identity, authorization, quotas, artifact retention, secret handling,
and job isolation before migrating storage or adding queues.

#### AUDIT-016: Simulation should remain separate from CAD admission

CS-T09 defines a defensible SPICE-model boundary, but a convergent deck cannot
validate an arbitrary chip. Package geometry and pin mapping are necessary and
insufficient for behavioral simulation.

**Recommendation:** implement vendor model provenance, model-to-symbol pin maps,
supported analyses, operating-condition bounds, and independent expected values.
Keep CAD-only, electrically admitted, and simulation-eligible as separate states.

## 8. Recommended execution order

### Phase A — stabilize the current working tree

1. Independently review NEW-1 through NEW-7 and the exact current diff.
2. Resolve findings without broadening scope.
3. Repair or isolate the KiCad environment and reproduce all required native
   gates.
4. Reconcile `.ai/tasks.yaml`, `.ai/state.yaml`, `.ai/reviews.yaml`, and
   `.ai/checkpoint.yaml`.
5. Commit the coherent CS-T01–T04 unit. Keep unrelated visual/reference files
   out of that commit.

### Phase B — correct the product contract users see

1. Rewrite `README.md` to the truthful capability map.
2. Correct or retire `V2_COMMERCIALIZATION_HANDOFF.md`.
3. Label old audits as historical and link forward.
4. Make all manufacturing, price, simulation, and hardware limitations visible
   in the UI before download.

### Phase C — close M10 under explicit workflow authorization

1. Reconcile the changed A2 sensor contract with a versioned benchmark case.
2. Fix or reject the retained four-connection routing failure.
3. Run the full 60 accepted, 20 core refusal, and 30 safety refusal corpus twice
   in fresh directories.
4. Complete determinism evidence, all canonical tiers, and independent review.

M10-T05 is currently blocked and COMPONENT-SYNTHESIS-1 explicitly excluded
reactivating it. A future agent must not start this phase until the human/ledger
boundary is changed.

### Phase D — complete the approved component-synthesis chain

After CS-T04 becomes `COMPLETE`, execute CS-T05 through CS-T11 sequentially.
The most important product threshold is CS-T08: one newly admitted component
must survive semantic verification, ERC, placement, routing, DRC, download, and
restart with exact lineage. CS-T09 simulation eligibility remains separate.

### Phase E — build and measure hardware

1. Select an untouched benchmark output.
2. Obtain real DFM feedback and a dated BOM/quote.
3. Fabricate and assemble the board.
4. Bring it up with minimal firmware.
5. Record measurements, defects, rework, and second-spin changes as evidence.
6. Feed every defect into a permanent regression fixture or explicit unsupported
   rule.

Only after this phase should Ohmni claim that a design has worked in hardware.

## 9. Decisions that require a human

- Whether and when to transition CS-T01–T04 from `VERIFIED` to `COMPLETE` after
  independent re-review.
- Whether to reactivate M10-T05 despite the component-synthesis scope's explicit
  non-goal.
- Which fabricator, assembly process, and hardware budget to use for the first
  physical spin.
- Whether to fund a bounded live model evaluation and which provider/model to
  evaluate.
- Whether the next product priority is component import, benchmark closure, or
  hardware validation. This audit recommends benchmark closure and hardware
  validation before wider part/family expansion.
- Whether a hosted multi-user beta is desired. No deployment or paid
  infrastructure provisioning is authorized by this audit.

## 10. Instructions for the next AI

### Start here

```text
git status --short
.venv\Scripts\python.exe scripts\project_status.py
.venv\Scripts\python.exe scripts\ai_state.py validate
.venv\Scripts\python.exe scripts\ai_state.py next
```

Expected current result: the ledger validates, there is no executable task, and
CS-T01–T04/M10-T05 are blocked. If the result differs, read the new checkpoint
and review records before doing anything else.

### Current safe work

- Read-only inspection and independent review of the current component-synthesis
  diff.
- Reproducing tests and native-tool failures without changing product scope.
- Correcting documentation claims while preserving the approval boundary.
- Writing a proposed remediation or benchmark change for human approval.

### Current prohibited assumptions

- Do not start CS-T05 because it is approved; its prerequisite is not complete.
- Do not count `UNKNOWN`, missing evidence, unsupported behavior, a skipped test,
  or an unavailable tool as PASS.
- Do not compare generated CAD only with the model's own JSON and call that
  datasheet verification.
- Do not activate imported components before CS-T07.
- Do not claim IPC compliance, validated SPICE behavior, manufacturability, or
  working hardware from geometry/ERC/DRC checks.
- Do not rewrite accepted benchmark failures or historical milestone evidence to
  make current results pass.
- Do not mix the untracked reference-visual plan into the component-synthesis
  commit.

### Required verification before claiming current-tree health

```text
.venv\Scripts\python.exe scripts\verify.py fast
.venv\Scripts\python.exe scripts\verify.py workflow
.venv\Scripts\python.exe scripts\verify.py corpus
.venv\Scripts\python.exe scripts\verify.py integration
.venv\Scripts\python.exe -m ohmni verify-all
.venv\Scripts\python.exe -m ohmni doctor
.venv\Scripts\python.exe -m ruff check .
cd apps\web
npm test
```

Run the component CAD proof and its adversarial reproducer according to
`.ai/checkpoint.yaml` and `.ai/verification/CS-T01-T04-REMEDIATION-2.yaml`.
Use scripted or recorded provider responses for routine tests. If a live model
run is approved, record model identity, tokens/cost, input/output digests, and
capture fidelity separately.

### Definition of a trustworthy handoff

A handoff is ready only when it names:

- exact HEAD and dirty-tree state;
- approved scope and next executable task;
- completed, verified, blocked, and merely proposed work separately;
- commands run and exact pass/fail/skip/timeout results;
- artifact and verification-record locations;
- open review findings and unsupported capabilities;
- the next action and the approval or dependency that permits it.

## 11. Final recommendation

Preserve Ohmni's core advantage: it is willing to say what it does not know.
The highest-value work is to make that honesty consistent from source evidence
through the README, user interface, benchmark, release records, and physical
board. A smaller product that reproducibly builds and measures one useful board
is more credible than a larger catalog, richer model prompt, or simulation UI
whose evidence boundary is incomplete.
