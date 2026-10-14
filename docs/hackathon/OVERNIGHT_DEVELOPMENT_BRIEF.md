# Ohmni overnight demo development brief

Prepare a dependable three-minute demonstration for October 17–18: one supported
idea, its generated board, recorded checks, one deliberately damaged copy, a real
DRC failure, and an immediate return to the original. Reliability and truthful
results take priority over feature count.

This is a development assignment template, not an approval record. Product work
is authorized when the owner sends or explicitly adopts the accompanying
[Claude Cloud prompt](CLAUDE_CLOUD_PROMPT.md). Creating these documents does not
authorize deployment, expenditure, a new product milestone or behavior-library work.

## Working baseline

Prepared against fetched main `1ed1abd411b2b9f302ca235bb390185a33a33b31`.
Revalidate against the main commit actually fetched by the implementing agent.
The reviewed attachment was `HACKATHON_PLAN.md`; it was not present at
`docs/HACKATHON_PLAN.md` on this baseline. Do not assume that attachment's broader
must-build list is authorized by this narrower assignment.

Important findings from read-only inspection and deterministic probes:

| Finding | Implementation consequence | Evidence |
|---|---|---|
| A2 with two LEDs, one button, no sensors, 50×40 mm fails placement at C5, both with and without programming header | Begin with the existing A2 minimum/default-size case; do not spend the night forcing a small outline | `src/ohmni/physical/placement.py:313`; `tests/test_generated_routing.py:64` |
| Width accepts 40–100 mm; height accepts 40–70 mm; defaults are 100×70 mm | Accepted dimensions do not establish placement/routing feasibility | `src/ohmni/synthesis/models.py:73` |
| Twelve is the number of catalog types, not a per-board component cap | Do not add or lift a fictional 12-part limit | `src/ohmni/synthesis/base.py:105`; `src/ohmni/synthesis/a2.py:123` |
| A2's button is a GPIO-to-ground input | Say momentary input button, never power disconnect; firmware remains outside proof | `src/ohmni/synthesis/a2.py:155` |
| An unresolved behavior binding refuses the entire circuit simulation | Do not count bound parts as simulated or claim partial-board simulation | `src/ohmni/application/component_behavior.py:299` |
| The existing FreeRouting adapter lacks DSN export and verified SES import in the pipeline | Keep the current router | `src/ohmni/routing/freerouting.py:10` |
| The router's existing budget is 180 seconds | Do not require an entire fresh run to finish during the presentation | `src/ohmni/application/demo.py:39` |
| CI runs fast and corpus, without a real KiCad gate or frontend Node suite | Add small, real gates; do not treat mocked/subprocess-skipped tests as tool evidence | `.github/workflows/ci.yml:7`; `tests/conftest.py:32` |
| Changed PCB bytes invalidate existing artifact provenance | Use an independent diagnostic artifact for a fault; preserve the original release | `src/ohmni/eda/kicad/erc.py:92` |
| Manufacturing rules consume owned artifacts, constraints and routing plans | Do not implement arbitrary PCB grading or bypass stale guards | `src/ohmni/manufacturing/rules.py:17` |
| The saved reference fetches local assets; normal project paths contact the backend | An offline fallback needs its own verified serving/asset path | `apps/web/reference-preview.js:16`; `apps/web/client-contract.js:74` |
| AI routes lack application request quotas; two active jobs is not an AI budget | Any request guard must cover planner, assistant, brief and generation paths | `scripts/demo_server.py:967`; `scripts/demo_server.py:1126` |

These are dated findings, not permission to alter the cited behavior paths.

## Scope, Git and ledger

Use one bounded scope, suggested ID `HACK-DEMO-1`, and one task, suggested ID
`HACK-DEMO-01`, with the phases below as substeps. Use one integration branch and
one PR with coherent commits. This avoids requiring overnight approval of several
dependent PRs while preserving the one-PR-per-task convention.

- Read `AGENTS.md`, `docs/AI_WORKFLOW.md`, `SECURITY.md`, the ledger, and current
  product projections. Inspect status and preserve unrelated work.
- Fetch latest `origin/main`; branch from it using `codex/hackathon-demo-readiness`
  or a unique suffix. Never push to, merge into, force-update or rewrite main.
- If the owner has sent/adopted the prompt, record the actual instruction as
  approval evidence. Do not cite this template as a human statement. Only then
  activate the scoped task under existing ledger rules.
- Keep one ledger owner and one active task. Do not steal another agent's active
  task, alter its approvals, or resolve unrelated findings. If concurrent ledger
  ownership cannot be reconciled, finish read-only diagnostics and record the blocker.
- No changes under `src/ohmni/behavior/`, `tools/behavior_audit/`, `docs/behavior/`,
  `out/component-behavior/`, or `scripts/generate_behavior_*`.
- No production deployment, paid model calls, paid services, purchases, account
  changes, credential rotation, branch deletion or remote-history cleanup.
  Existing repository CI may run within the existing authorized account allowance;
  do not upgrade plans or buy minutes. Preview automation already attached to a PR
  may run; do not promote it to production.
- Routine implementation choices within this scope do not require another approval.
  Material electrical changes, new libraries/families and weakening verification do.

## Execution order and time limits

Treat this as a priority queue for one overnight session, not a promise that all
phases fit. Aim to leave useful, tested commits even if later phases cannot finish.
Spend at most about 20 minutes on an unavailable tool/setup approach and 45 minutes
total on tool acquisition before using the fallback below. Reserve the final
60–90 minutes for checks, review and handoff.
Do not begin optional work while a higher-priority completed feature has a blocker.

| Priority | Phase | Dependency | Deliverable |
|---|---|---|---|
| 0 | Inspect tools, ledger and current code | None | Baseline, tool versions and bounded execution plan |
| 1 | Qualify one board and build a repeatable harness | Real KiCad for qualification | Exact brief, real reports, exports, timings and reproducible command |
| 2 | Add CI protection | Can use existing tests while phase 1 proceeds | Frontend suite plus a real-tool smoke gate |
| 3 | Package a truly offline saved demonstration | A qualified capture, or an explicitly historical reference | Local command, complete asset set and network-disabled browser test |
| 4 | Add one fault, a clear report and reset | Current qualified good/bad artifacts | Honest good → failed diagnostic copy → good flow |
| 5 | Add bounded AI request controls | Independent of board qualification | Configurable quotas, deterministic tests and 429 recovery |
| 6 | Optional explanation improvement | Phases 1–5 verified; time remains | Existing grounded assistant reused, deterministic fallback |

CI setup and request-control design can be delegated in parallel with board
qualification. One coordinator owns integration, `.ai`, shared server routes and
frontend files. Do not run multiple memory-heavy EDA jobs concurrently just to
increase agent utilization. Reviewers should identify bounded findings, not create
new product scope.

If fresh qualification remains blocked, mark phase 4 blocked and proceed to phase 5.
Phase 3 may use its explicitly labeled historical-reference fallback. Do not start
optional phase 6 while any earlier acceptance gate remains unverified.

## Phase 0 Environment and recovery

Use the repository venv or create a local cloud venv; do not assume Windows paths
exist in Claude Cloud. Check Python, Node, `kicad-cli version`, and Docker availability.
Record ngspice availability if relevant, but do not make new SPICE work a dependency.
The current production Dockerfile pins KiCad 10.0.5 and builds ngspice 42; use that
toolchain when available. Do not edit its pins merely to get green tests.

Docker might be unavailable in the cloud. Try a permitted pinned tool installation
or existing CI runner. Installing development tools in the disposable environment
is allowed; provisioning paid infrastructure is not. If real KiCad cannot run,
finish the harness and CI job, pure tests, offline shell and independent request
controls. Record the real-tool gate as NOT_RUN/BLOCKED. Never substitute mocked
outputs for a qualified board, fault receipt or a green integration gate.

Do not download or publish private/licensed source bundles to unblock this scope.
Use the existing permitted corpus acquisition workflow where required and record
missing inputs honestly. An inaccessible bundle does not authorize fabricated evidence.

## Phase 1 One reproducible supported board

Start with `test_generated_family_copper_closes_real_drc_and_manufacturing` and its
A2 minimum case: default 100×70 mm, one indicator LED, one momentary button, no
sensors and no programming header. Treat this as a candidate, not an already
qualified live demo. If it fails, diagnose narrowly and select another existing
supported configuration, preferably an established A1 reference. Do not tune the
router, relax clearances or change electrical facts to meet an arbitrary outline.

Create one CLI harness, suggested `scripts/verify_hackathon_demo.py`, which:

1. Uses a fixed typed brief and the existing production synthesis/generation path;
   prefer `ProjectPipeline.run` in `src/ohmni/application/projects.py`. The routing
   test is an acceptance pattern, not the complete ERC/export pipeline. No model
   API is necessary to verify downstream engineering.
2. Performs fresh synthesis, placement, routing, real KiCad ERC/DRC, manufacturing
   checks and Gerber/drill export in a new output directory.
3. Fails on missing tools, tool errors, malformed reports, stale provenance,
   unresolved routes, DRC errors/unconnected items, or missing/empty required outputs.
4. Preserves supported warnings and limitations. Zero critical errors does not mean
   every applicable and inapplicable check passed.
5. Records Git commit, normalized brief/hash, tool versions, input/output hashes,
   check results, artifact list and stage/total timings in a machine-readable summary.
6. Can run three fresh attempts sequentially without reusing old receipts. Record
   measured times; do not promise byte-identical tool logs or a three-minute build.

Keep bulky runs under ignored `build/` output. Commit only small, intentional,
reviewable fixtures and summaries. Any exported public example must contain no
private paths, secrets, copyrighted datasheet bytes or private project history.

Candidate conversational wording for later owner rehearsal:
“A USB-C powered ESP32 board with one momentary input button and one indicator LED,
no sensors, using the default board size.” A deterministic harness pass does not
prove Claude interprets this text identically; mark live prompt rehearsal pending
unless separately authorized and actually performed.

## Phase 2 Real checks in CI

Preserve the current fast and corpus jobs. Add the frontend Node tests and a bounded
KiCad smoke gate that exercises the selected board through real ERC, DRC and export.
Include a known-bad board check when phase 4 is available. It must fail, not skip,
if required tools or fixtures are missing. A poisoned/missing-tool test should show
that the gate cannot report green without running its external checks.

Inspect pytest markers: default `fast` excludes integration and slow tests. The
selected generated-routing test is slow/KiCad-gated, so `verify.py integration`
alone does not select it. Use explicit selection/marker overrides and assert the
expected checks ran. Do not remove markers to make other suites look broader.

The production image does not include all test files/dev dependencies. Mount or
copy the checkout and install the declared dev dependencies in the test environment;
preserve the KiCad library/HOME/user setup. Avoid invoking the server entrypoint
when the CI job intends to run tests. Save small result summaries as CI artifacts.
No new hosted service, workflow secret or paid runner is required by this scope.

## Phase 3 Offline demonstration

Provide a documented one-command local preview that works with no API key and no
internet. It must serve all required HTML, JS, fonts/icons, board models and saved
result data locally. A Python static server or similarly small existing mechanism
is preferable to introducing a service worker/PWA architecture.

Use the existing viewer and a labeled saved artifact. Include the saved Gerber/drill
package locally if downloads are shown. Display capture provenance and recorded
limitations. Distinguish “saved successful run” from “generated just now.”

Do not fake an AI conversation, timed engineering progress or live checks. If phase 1
cannot qualify a fresh capture, an existing approved reference can demonstrate
navigation, clearly labeled with its original provenance. It does not satisfy the
fresh qualification gate or authorize a fabricated failure receipt.

Acceptance: start from a fresh browser context, disable external network access,
then open the board, inspect its recorded checks, download the local package, go
back and reset. No required asset/API request may depend on Fly, Vercel or a CDN.
Avoid changing the production network/identity contract to accommodate this mode.

## Phase 4 Fault demonstration and report

Implement only one robust fault using an existing test pattern, such as the
known different-net overlap in `tests/test_pcb.py`. Alternatively remove one
uniquely identified necessary track, proving that the selected board really gets
an unconnected-item finding. Do not build a general KiCad editor/parser.

Maintain separate immutable good and damaged artifacts. Prefer producing a fresh
owned diagnostic artifact through supported compiler/test seams. If a file-copy
diagnostic path is necessary, give it a separate snapshot hash, fixed server-owned
input ID, checker version, raw DRC receipt and a diagnostic-only result contract.
Verify the snapshot hash before and after DRC, and derive the displayed geometry
from that same snapshot. Do not reuse the original compilation's emitted tracks
after modifying PCB bytes: the current viewer projection uses those tracks.
Never forge an old compiler fingerprint, disable the currentness guard, overwrite
the original saved job, or allow arbitrary client filesystem paths/uploads.

The good board retains its original release lineage and downloads. The damaged
copy must show its own board/selection and DRC result, with no stale green checks
inherited from the original. Do not run intended-plan manufacturing rules against
modified geometry and present that as a fresh actual-geometry pass. Checks that
were not run on the damaged snapshot are NOT_CHECKED. No damaged copy is releasable.

Use existing visual/contract modules rather than replacing the workflow. Show:

- A readable result and the checker responsible for it.
- Relevant component/net identifiers and bounded reason text.
- The source artifact identity and recorded/live status in a details disclosure.
- Explicit unknown/unperformed checks and limitations.
- “Show fault” and “Restore original” controls with keyboard focus, busy/error
  recovery and protection against late responses replacing the current selection.

Represent outcome separately from severity and tier. Preserve PASS_WITH_WARNINGS,
UNAVAILABLE, stale and unknown meanings when projecting existing statuses; no
blanket all-green verdict. “Model-bound” does not mean “simulated.” Do not invoke
partial-board SPICE or expose the STM32 operating-limit issue as a safe result.

Prove the fault causes at least one actual KiCad error or unconnected finding;
a stale-artifact refusal alone is not a successful fault demonstration. Reset must
restore the original hash, view, report and downloads repeatedly. Deterministic
explanation text tied to the known finding is sufficient for the first slice.

## Phase 5 AI request controls

Add request admission before every billed provider path, including planning,
assistant questions, legacy brief and free-text generation. Reuse existing body
limits, identity validation and fail-closed public errors. Do not restrict ordinary
health reads or polling behind the billed-request quota.

Use configurable finite global daily request limits, a bounded in-flight limit,
and a small burst limiter. Document defaults and their rationale. A request count
is not a dollar guarantee: existing provider retries can produce multiple paid
attempts. Count admitted failed calls too; quota admission must be atomic and
survive restart. If quota storage cannot be trusted, refuse the billed call.
Acquire admission before launching a billed background job and retain its
concurrency lease until the worker's provider work finishes, not merely until the
HTTP handler returns. Release the lease on every failure path without refunding
the daily count. Include an asynchronous-worker test for this lifetime.

Do not trust arbitrary forwarded IP headers, mistake CORS for authentication,
or depend solely on per-IP limits: a campus may share an IP. Retain a global cap
that cannot be bypassed by changing request headers. This does not add accounts
or claim comprehensive abuse protection. Do not create a public bypass/reset API.

Test all billed routes, concurrent admissions, failed calls, day rollover, restart,
storage failures, legitimate retries and budget exhaustion using fake providers.
Rate rejection returns 429 with appropriate Retry-After; the UI preserves the
request and offers a truthful retry/guided path without an automatic retry storm.
Document presenter preflight/reset via local operator tooling, without deploying
or changing production quota state overnight.

## Phase 6 Optional explanation

Only when higher priorities are verified, reuse the existing assistant/fact-ID
boundary in `src/ohmni/application/iteration.py` to explain the named DRC finding.
Do not create a general grading agent. The original deterministic report is
immutable; unknown facts remain unavailable. Escape text, bind it to the current
artifact, handle timeout and provide a deterministic explanation fallback.

Fake-provider tests can establish schema/status/freshness behavior, not the quality
of live model prose. Record live explanation evaluation as pending. No paid API
calls are authorized by this assignment.

## Verification and release boundaries

At minimum run:

```text
python scripts/ai_state.py validate
python scripts/verify.py workflow
python scripts/verify.py fast
node --test apps/web/tests/*.test.mjs
```

Run relevant real KiCad integration/slow tests and the new harness explicitly.
Use separate temp roots or serialize pytest tiers; they otherwise share the
`build/pytest` directory. On environments where shell globs do not expand for Node,
enumerate test paths rather than accidentally running no tests.

Test meaningful boundaries rather than asserting the implementation mirrors itself:
missing checker must not pass, damaged artifact must not inherit good evidence,
quota exhaustion must not call the provider, and late replies must not overwrite
the currently selected result. Preserve existing source, fingerprint, release and
UI identity guards. Fix only regressions caused by this scope; report unrelated
failures with evidence instead of weakening tests.

Ask an available independent subagent to review the final diff for false passes,
artifact confusion, unbounded provider calls and broken recovery. Fix resulting
BLOCKER/HIGH findings within scope. If review is unavailable, record that fact;
do not mark the task COMPLETE or pretend self-review is independent. Incomplete
real-tool/browser checks mean implementation is not fully verified.

No production deployment or merge is part of this assignment. Push only the task
branch and open one PR; keep it draft if required checks are incomplete or blocking
findings remain. Do not knowingly commit broken product code as a checkpoint.
Use `.ai/checkpoint.yaml` for uncommitted work when necessary.

## Morning handoff

Create `docs/hackathon/OVERNIGHT_RESULTS.md` with:

1. Base/implementation commits, PR URL, changed files and each phase's actual status.
2. Exact demo brief, board dimensions, part count, fingerprints and measured timings.
3. One-command fresh engineering reproduction and one-command offline preview.
4. Good/bad/reset results and the specific real DRC finding, or explicit NOT_RUN.
5. Test counts, skipped checks, tool versions, CI links and browser evidence.
6. Request-limit defaults, all guarded routes and the untested production boundaries.
7. A 180-second walkthrough with a labeled saved-run fallback and no live third-party upload.
8. Exact remaining owner actions: review/merge, production deployment, permitted live
   prompt rehearsal and any missing cloud resources. Do not list completed work as pending.

Do not start these overnight: A4/flashlight, Freerouting integration, arbitrary
uploads/import, catalog expansion, partial-circuit simulation, CPL/JLC procurement,
new fab limits, full M10 benchmark, behavior fixes, Paper redesign, Sentry integration
or a hardware order. Do not close AUD-VERIFY-001 or alter the STM32 test to green.
