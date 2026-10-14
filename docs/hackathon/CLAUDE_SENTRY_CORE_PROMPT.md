# Claude Cloud Sentry implementation assignment

Prepared against fetched `origin/main` at `6f2a7827` on 2026-10-14, after PR #75.
Final status refresh: `7698cea8`, after the judge Q&A in PR #74 also merged.
This is a handoff template. Saving it does not approve or start implementation.
The owner sending the prompt below authorizes its bounded offline scope.

## Remaining work and division of ownership

| Work | Current evidence | Next action |
| --- | --- | --- |
| Saved board, fault and restore demo | PRs #73 and #75 are merged; HACK-DEMO-01/02 are VERIFIED. | Independently rehearse the deployed version and local fallback. A merge alone does not prove deployment. |
| Sentry | [Researched plan](../../SENTRY_IMPLEMENTATION_PLAN.md) is merged; SDK integration is not implemented in main. | Claude builds the disabled-by-default core below. Live activation follows account setup and owner approval. |
| Live conversational demo | [Overnight results](OVERNIGHT_RESULTS.md) record no paid-provider rehearsal or production budget configuration. | Verify deployment/readiness without paid requests first; a live model test remains separately authorized. |
| Judge Q&A | [PR #74](https://github.com/Jadenw9013/Ohmni/pull/74) is now merged. | Codex uses and updates its acceptance checklist against the now-merged demo while preparing the rehearsal handoff. |
| Grounded finding explanations | Optional Phase 6 in the overnight results was not started. | Follow-up after demo reliability and Sentry core; keep verdicts deterministic. |
| Paper visual redesign | [Paper plan](../../PAPER_FRONTEND_IMPLEMENTATION_PLAN.md) remains proposed. | Separate design/implementation approval; not part of this cloud assignment. |
| Battery motion and component addition | `ai_state.py next` offers BM-T02. BM-T03 through BM-T07 depend on that work; the state also identifies CAB-T07 as dependency-ready but unstarted. | Keep the existing approved backlog intact. Do not add a new board family for this demo task. |
| Deferred maintenance and behavior audit | HACK-R08/R09 remain LOW quota findings. CBH-STAGE7 lists source approval, a fresh verifier round, and baseline-refresh approval as blockers. | Preserve these records; this assignment does not close findings or take over protected behavior work. |

The ledger contains stale pre-merge summary wording, including
`SAVED_DEMO_INTEGRATION_IN_PROGRESS` with `active_task: null`. Claude may reconcile
current summaries while taking its approved task slot, but must preserve previous
verification records, approval evidence, accepted risks and open findings. A
merged PR is not permission to invent a new independent review or acceptance.

Claude owns the Sentry implementation, its tests, telemetry CI/dependency changes,
and ledger updates. Codex starts **only after the owner says Claude is running**,
and owns independent release rehearsal: public static/health checks, local offline
browser verification, and presenter recovery instructions. Codex will not edit
application/server code, telemetry tests, CI/dependencies, or the shared ledger
while Claude works.

Codex reserves `docs/hackathon/REHEARSAL_ACCEPTANCE.md`,
`scripts/rehearse_hackathon_release.py`, and
`tests/test_hackathon_release_rehearsal.py` if a new checker is necessary. Prefer
the existing browser checker over duplicating it. Claude must not edit these
reserved files or `scripts/browser_check_offline_demo.py`.

## Copy this prompt into Claude Cloud

```text
Implement the offline Sentry core for Ohmni in one substantial, reviewable PR.
I approve this bounded implementation scope. Work autonomously within it; make
routine implementation choices without waiting for me. Do not enable live
telemetry, spend money, change user-facing behavior, deploy, or merge to main.

REPOSITORY AND PURPOSE
Repository: https://github.com/Jadenw9013/Ohmni
Make real planner, generation and native-tool failures diagnosable, with connected
traces and truthful outcomes, while keeping every existing security and
engineering gate intact. Deliver code and offline evidence now. Sentry account
setup and real ingestion are a separate owner-controlled step.

READ AND START
1. Fetch origin/main and inspect status. Create a new implementation branch from
   that exact tip; never work on main. Use codex/hackathon-sentry-core or a unique
   suffix if the environment permits; a required Claude Cloud branch prefix is
   acceptable. Never use codex/behavior-* or force-push another agent's branch.
2. Read AGENTS.md, docs/AI_WORKFLOW.md, SECURITY.md, README.md, ARCHITECTURE.md,
   VERIFICATION.md, docs/DECISIONS.md and the current .ai ledger.
3. Read SENTRY_IMPLEMENTATION_PLAN.md in full, then
   docs/hackathon/OVERNIGHT_RESULTS.md and DEMO_SITE_INTEGRATION.md.
   Read docs/hackathon/CLAUDE_SENTRY_CORE_PROMPT.md too. If that last file has not
   merged, fetch origin/codex/cloud-next-handoff and read it with git show; do not
   base your implementation branch on that documentation branch.
4. The Sentry plan was researched against 7f91881d. Recheck every named boundary
   against current main, especially the newer durable AI request budgets and
   background lease lifetime. Do not copy old line numbers or assume route names.
5. Record THIS OWNER MESSAGE as approval for one scope/task, HACK-SENTRY-1 /
   HACK-SENTRY-01 if unused. This explicitly selects Sentry next rather than
   BM-T02; it does not cancel or complete battery-motion work. Keep one active
   ledger task. If another task is genuinely active, report that specific
   ownership conflict; do not clear or overwrite it. Correct stale summary text
   only from Git/ledger evidence, without upgrading historical review statuses.

SCOPE AND DELIVERY ORDER
Implement the plan's SENTRY-T01 through SENTRY-T04 together as one task/PR, in
coherent commits. This avoids waiting for intermediate merges during the cloud
run. The 180-minute estimate in the plan is a coding target, not an excuse to cut
privacy tests or call partial work complete. Reserve the final quarter of your
available session for tests, independent review where available, and handoff.

A. Adapters and executable privacy contract first.
- Pin audited Python/browser SDK versions. Start from the versions researched in
  the plan; check exact APIs against official docs and installed SDK source.
  Record any justified version deviation. Install ordinary test dependencies,
  but do not acquire paid services or upgrade CI/service plans.
- Only src/ohmni/adapters/telemetry.py imports the Python SDK. Use a small browser
  facade and locally bundled adapter compatible with native ESM, Vercel's current
  no-build publication, and the demo server's immutable static allowlist.
- Disabled/missing/invalid telemetry configuration must leave the product usable,
  import no SDK in disabled mode, and create no transport. Initialization,
  context entry/exit, capture, metric emission and flush are independently safe.
- Test with the actual pinned SDK and recording transports as well as fakes.
  A stub-only test does not prove actual SDK serialization is safe.
- Isolate inherited SENTRY*/OHMNI_TELEMETRY* configuration in test processes without
  printing it. Block outbound network in telemetry tests; accept synthetic DSNs
  only with explicit recording transports. An inherited account must never receive
  test traffic. Fail a test if an unexpected transport/network path is attempted.

B. Capture meaningful swallowed failures safely.
- Inventory current provider, planner/assistant, worker, publication/persistence
  and browser request recovery boundaries. Inventory outcomes, not catch counts.
- Emit one owned issue at the responsible boundary. Preserve existing JSON,
  status codes, messages, fail-closed behavior and rate-limit/lease semantics.
  Provider outages can reach typed ValueError/400 handlers; do not only watch 500s.
- Use the researched plan's owned error codes and safe fields. Never pass raw
  caught exceptions to capture_exception or stringify/repr an exception/object.
  A before_send hook alone cannot prevent earlier SDK inspection.
- Distinguish expected engineering rejection from infrastructure/provider failure.
  Duplicate nested catches must not create duplicate issues.

C. Trace real execution end to end.
- Cover current conversational planning/assistant requests, confirmed-project
  generation, and legacy generation. These are distinct flows/actions; do not
  hold a transaction open while a human reviews a plan.
- Connect the short HTTP request to the actual async worker with explicit bounded
  trace metadata, isolated per-request/per-worker scopes, and tested thread handoff.
  Worker completion includes validation and durable publication, not just the
  pipeline returning. Emit outside job-store locks.
- Wrap actual application stages and the shared run_tool boundary. Record owned
  tool classification, duration and outcomes, never argv/cwd/env/stdout/stderr.
  Missing executable, timeout, nonzero exit and engineering rejection differ.
- Instrument real provider attempts manually; no auto Anthropic/subprocess/
  threading capture that bypasses the plan's privacy boundary. Record only actual
  reported usage; absence is unknown, never invented zero cost or tokens.
- Propagate only to the exact allowed API origin and /api/ path. Validate incoming
  trace headers and baggage, preserve CORS/authentication, and never propagate to
  providers or subprocess environments. Caller sampling cannot override limits.
- Confirmed-project generation has no model-repair or SPICE step today. Do not
  invent spans. Keep detailed legacy observer instrumentation optional if a
  truthful coarse orchestration span meets the bounded core.

D. Metrics, controlled demonstration and activation handoff.
- Add only the plan's bounded low-cardinality outcomes/durations. Count actual
  transitions after persistence; polling/reopening/reuse cannot recount jobs.
  Unknowns and engineering warnings remain visible. Channel flags must really
  suppress metrics/logs, not merely configure an ineffective SDK option.
- Build an isolated local fault harness: expected rejection, provider failure,
  tool timeout, publication failure, and recovery. No public crash endpoint.
  Do not mutate canonical examples/hackathon-demo or its public mirror; reuse
  existing receipts as explicitly saved evidence and use temporary copies for tests.
- Produce local recording-transport evidence of the issue/trace relationship and
  a practical dashboard/activation recipe. No fabricated SaaS screenshots, live
  ingestion claims, account assumptions or sponsor eligibility promises.

NON-NEGOTIABLE TESTS
Use SENTRY_IMPLEMENTATION_PLAN.md section 11 as the acceptance checklist. At minimum:
- SDK failure at init/enter/capture/status/exit/flush never skips application work,
  repeats it, suppresses its exception, replaces its result, or breaks startup.
- Hostile __str__/__repr__/getters are not invoked by telemetry.
- Canary secrets in prompts, model outputs, exception args, request URLs/headers,
  paths, local variables, circuit content and tool input/output never appear in
  ANY serialized envelope/channel, including transactions and metrics.
- No implicit session/profile/replay/console/DOM/vendor/subprocess capture.
- Concurrent requests/jobs do not mix parents/tags; scopes restore on every path.
- Reuse/polls and persistence failures do not report fictional success/counts.
- Native and engineering outcomes remain distinct. Synthetic fixtures are labeled.
- Enabled versus disabled telemetry preserves API errors and engineering/artifact
  fingerprints. New request budgets remain enforced with unchanged worker leases.
- Browser missing-bundle/disabled paths remain usable. Static/local serving works;
  exact same-origin and cross-origin trace propagation never targets third parties.
- Run an isolated real-browser smoke with the actual bundled SDK and recording
  transport, with external traffic denied. Exercise enabled, disabled and missing
  bundle modes under both static publication and local server hosting. Record
  browser version, results and uncaught errors. Node mocks alone are insufficient.

BOUNDARIES AND PARALLEL WORK
Do not modify src/ohmni/behavior/, tools/behavior_audit/, docs/behavior/,
out/component-behavior/, scripts/generate_behavior_*, or their review findings.
Do not implement battery-motion, Paper redesign, conversational UX changes,
grounded DRC explanations, or unrelated quota fixes in this PR.
Do not alter deterministic electrical/routing/manufacturing/BOM semantics. Do not
import the concrete telemetry adapter into deterministic domain/verifier code.
Read secrets neither for debugging nor for tests. Use synthetic test canaries.
No real DSN/account traffic, paid AI calls, telemetry activation, deployment,
Replay, Seer, source-map upload, broad logs, public diagnostics, or purchases.

Codex owns independent release rehearsal in a separate branch after I start you.
Leave scripts/browser_check_offline_demo.py and these reserved files untouched:
  scripts/rehearse_hackathon_release.py
  tests/test_hackathon_release_rehearsal.py
  docs/hackathon/REHEARSAL_ACCEPTANCE.md
You are the sole shared-ledger writer during this run. Codex will not edit your
application/server files, telemetry tests, CI/dependencies, or .ai files.

VERIFICATION AND STOP RULES
Run ai_state.py validate; verify.py workflow; verify.py fast; the full Node suite;
verify.py integration; focused telemetry/privacy tests and architecture checks;
and the applicable existing real-KiCad gate if native execution semantics change.
Enable the actual SDK recording transports explicitly in the telemetry suite;
missing SDKs must not silently skip that suite. Preserve all existing CI gates.
No required gate may pass with zero tests or only stubs. Record exact commands,
versions, counts, skips and failures. Missing KiCad/corpus/ngspice-42 results remain
NOT_RUN/BLOCKED, not PASS; do not change pinned behavior tools or tests to fix them.
Do not spend more than 45 minutes obtaining unavailable tools. Continue independent
work and record the remaining gate. No account/DSN is needed for offline acceptance.
Seek an independent privacy/correctness review with a separate agent if available.
Do not invent one if unavailable. Open BLOCKER/HIGH findings prevent completion.

DELIVER
Open one PR against main; never push/merge main. Include completed acceptance
checks, evidence commit, files changed, scope omissions and known limitations.
Write docs/hackathon/SENTRY_CORE_RESULTS.md and a commit-bound verification record.
The results must contain:
1. What works offline and which real SDK versions were exercised.
2. Reproduction commands and sanitized recording-transport evidence locations.
3. Test/review results and every unresolved finding or blocked gate.
4. Smallest owner checklist to activate two Sentry projects later, including
   required public/private configuration, sampling, quotas and disable/rollback.
5. A 30-45 second Sentry demo script using a controlled local failure and recovery,
   clearly separating offline proof from the still-unverified live dashboard.

Re-read the diff before committing. If any no-inspection, fail-closed, trace
isolation or fingerprint guarantee fails, fix it or leave the task incomplete.
Report safe verified progress instead of expanding scope or claiming completion.
```

## Starting the parallel Codex task

After sending the prompt, tell Codex **“Claude is running.”** Codex can then
start its reserved independent rehearsal without assuming the cloud session exists.
Read-only public checks do not establish a successful paid AI call or prove that
production quotas persist across restarts. Those require separate authorized
deployment/provider evidence and should remain explicit in the final readiness report.
