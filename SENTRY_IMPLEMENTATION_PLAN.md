# Ohmni Sentry implementation and AI handoff plan

Status: **PROPOSED implementation; research and documentation only authorized.**

Research date: 2026-10-12 America/Los_Angeles (2026-10-13 UTC).  
Repository baseline: `7f91881d65a4823c1f77b664e6b37bf97e36c8f4`, fetched from `origin/main`.  
Research branch: `codex/sentry-integration`.  
Owner: Jaden. No Sentry account/projects/DSNs are configured at this handoff.

This replaces the technical recommendations in the supplied
`Sentry_Integration_Proposal_Ohmni.md` and the earlier conversational plan.
It does not replace [SECURITY.md](SECURITY.md), [AGENTS.md](AGENTS.md), or
[the development workflow](docs/AI_WORKFLOW.md). Sections below distinguish
observed facts, proposed decisions, and external facts awaiting confirmation.

## 1. Start here: authority and scope

The user explicitly changed the request from implementation to audit, then
authorized this researched Markdown plan. **Do not interpret this file as
permission to install, implement, enable telemetry, deploy, or incur charges.**
On a subsequent explicit implementation instruction:

1. Inspect Git status/worktrees and fetch latest `origin/main`. Preserve unrelated
   work, especially the uncommitted BM-T02 battery-motion worktree.
2. Start a fresh `codex/` branch from that main; never a `codex/behavior-*` branch.
   Recheck the function map below against that revision. Never push/merge main.
3. Read the current `.ai` ledger; record the new human authorization durably and
   reconcile the single active slot through the existing workflow. Proposed task
   IDs below are not already approved ledger tasks. Do not cancel or complete BM-T02.
4. Do not modify `src/ohmni/behavior/`, `tools/behavior_audit/`, `docs/behavior/`,
   `out/component-behavior/`, or `scripts/generate_behavior_*`.
5. Implement the offline core first. Ask before user-facing behavior changes,
   spending, Seer/trial activation, or any unapproved live telemetry collection.
6. Deliver reviewable PRs and verification evidence; do not merge them yourself.

Earlier interrupted setup downloaded Python `sentry-sdk 2.72.0` into the shared
local virtualenv and browser `11.7.0`/esbuild `0.28.2` into this worktree's ignored
`node_modules`. Dependency-file changes were reverted. Their local presence is
not a repository dependency, implementation, configuration, or live validation.

## 2. Objective and success criteria

Explain why a particular board-generation attempt stopped, which operation
caused it, and whether recovery completed, without collecting circuit content
or changing engineering outcomes. The integration is useful when it shortens a
real debugging investigation, not when it merely produces many events.

The minimum compelling **activated demonstration** is:

- One unexpected planner failure and one native-tool failure visible as owned
  Sentry issues, correlated with their actual operation traces.
- Browser action -> API -> asynchronous generation worker -> actual stages and
  tools connected correctly, including concurrent jobs.
- Separate engineering rejection, infrastructure failure, and successful repair.
- A small outcome/duration dashboard with explicit denominators and unknowns.
- Automated evidence that telemetry cannot leak design content or alter a job.

Offline implementation and live acceptance are separate milestones. T01-T04 can
prove code readiness using recording transports without an account. The connected
Sentry demonstration remains unverified until the owner authorizes live collection
and the activation checks run; offline success alone is not integration completion.

**Non-goals:** changing error messages/status codes; adding an LLM repair path
to saved projects; adding SPICE where it does not currently run; changing
verification/release gates; database migration; queue infrastructure; full SQL
tracing; profiling; public fault-injection endpoints; an observability UI;
automatic Seer code changes; guaranteed eligibility, prizes, or root-cause accuracy.

## 3. New research that materially changes the approach

| Observed fact | Consequence for implementation |
|---|---|
| Normal chat planning and saved-project generation are different operations. `ProjectPipeline.run()` does not call SPICE or the model repair loop. | Separate action traces; never invent repair/simulation spans for this flow. |
| `StructuredGenerationError` subclasses `ValueError`; planner/assistant HTTP handlers can map provider outages to their existing 400 response. | Capture a safe classification in the provider adapter. Looking only for HTTP 500 or broad handlers misses this failure. Preserve existing HTTP semantics. |
| There are 42 broad handlers in the demo server, plus typed handlers. Other frontend modules own the main chat flow. | Inventory recovery boundaries, not a target number of catch blocks. |
| Raw SDK exception serialization can invoke hostile `__str__`/`__repr__` before the outgoing filter. | Do not pass raw caught exceptions at fail-closed boundaries. A catch around the SDK call alone does not preserve the no-inspection invariant. |
| Sentry Python 2.68 changed direct logs/metrics enablement; the old global flags are not reliable channel kill switches. [S1] | Gate calls in Ohmni and explicitly drop disabled log/metric events. |
| Python 2.72 granular `data_collection` has permissive defaults for omitted categories, and providing it changes the legacy scrubber path. [S2, S3] | Specify every sensitive category and use owned outgoing allowlists; do not assume `send_default_pii=False` is enough. |
| Default Python integrations include subprocess/thread instrumentation. | Disable defaults for the initial core; explicit tool spans avoid argv/cwd collection and child-environment mutation. [S4] |
| The frontend uses native ESM, Vercel has no install/build step, and the demo server snapshots a static allowlist. | Bundle only the telemetry adapter locally; installing a package does not make a bare browser import resolve. |
| SDK/marketing examples differ from current source in places. | Pin audited versions and write executable option/transport tests before relying on an example. |

## 4. Architecture decisions

### 4.1 Explicit collection instead of broad auto-instrumentation

Create `src/ohmni/adapters/telemetry.py` as the only production Python module
importing Sentry. All callers pass owned enums and bounded primitive metadata.
Initialize in `scripts/demo_server.py:main`, after local environment loading and
before provider/server construction. Disabled mode imports no SDK and creates no
transport. Bad telemetry configuration must not prevent normal server startup;
emit one fixed local diagnostic, with no DSN or exception text.

Use `default_integrations=False` and `auto_enabling_integrations=False` initially.
Do not enable Anthropic, stdlib, logging, threading, framework, argv, or uncaught
exception integrations implicitly. Manual provider spans are the core decision,
not an inferior fallback: the auto Anthropic exception path serializes the
exception before the privacy hook. [S4, S5]

The SDK still supplies ingestion, issue grouping, traces, metrics and dashboards.
Keep the adapter small; do not build a second tracing framework or custom protocol.

Proposed adapter surface (interface sketch, not tested implementation):

```text
initialize(config) -> enabled/disabled
http_operation(route_template, method, validated_parent) -> context manager
worker_operation(validated_parent, opaque_job_id, flow) -> context manager
stage(stage_enum) -> context manager
record_boundary_failure(site_enum, code_enum) -> no-throw
record_tool_result(tool_enum, outcome_enum, return_code_or_none) -> no-throw
record_job_transition(flow, old_state, persisted_new_state) -> no-throw
record_verification(report_owned_rollup) -> no-throw
record_provider_attempt(owned_attempt_summary) -> no-throw
shutdown(timeout_seconds) -> no-throw
```

SDK initialization, scope entry/exit, attribute setting, emission and shutdown
must be independently guarded. A telemetry context manager must execute the
application body exactly once. It must never swallow, replace, stringify, or pass
an application exception to Sentry's context manager exit. Finalize with an owned
status and preserve the original exception unchanged. Do not hold the job-store
lock across a network flush or telemetry call; snapshot owned state under the
lock, then emit outside it.
In particular, `_persist_locked()` currently reaches `_emit()` under the lock;
do not attach Sentry indiscriminately to `_emit()` or `_diagnostic()`. Preserve
their current local diagnostics and emit copied, owned telemetry after unlocking.

### 4.2 Keep deterministic code deterministic

Do not add Sentry/network dependencies or telemetry timing to domain, verifier
rules, routing algorithms, manufacturing arithmetic, or BOM arithmetic.
Preserve the router's existing injected deadline clock for its execution budget;
it is not telemetry. Instrument application callers instead.
For detailed legacy generation-stage spans, inject an optional no-op observer
protocol into `DesignOrchestrator`; the adapter implements it. The generation
module must not import Sentry or the concrete telemetry adapter. Default behavior
and report fingerprints remain unchanged. If observer work exceeds the core
timebox, retain an honestly named coarse `design.orchestrate` span and defer
per-attempt timings; do not infer timing from progress percentages.

### 4.3 Three real flows, not one invented pipeline

```text
Planning action (separate trace)
  browser.plan -> POST /api/project-plans
    -> ConversationPlanner.propose -> provider attempt(s) -> plan validation

Confirmed project generation action
  browser.generate -> POST /api/projects/{project}/revisions/{revision}/run
    -> accept/reuse job -> worker transaction
      -> synthesis -> semantic verification -> schematic -> ERC
      -> placement -> routing -> DRC -> manufacturing -> artifact packaging
      -> report validation -> durable publication

Legacy scripted/model-proposed generation action
  browser.generate -> POST /api/demo -> worker transaction
    -> DesignOrchestrator: actual proposal/check/repair steps
      -> schematic -> ERC -> optional SPICE attempt
    -> shared physical/manufacturing stages -> durable publication
```

Span order must follow the actual code. Use `flow=confirmed_project`,
`scripted_fixture`, or `model_proposed`; the scripted provider is synthetic and
must not emit fictional paid-model token usage. Planning, confirmation and a later
generation are separate user actions, possibly separated by minutes. Do not keep
one transaction alive across human think time. Cross-action journey linking is
deferred rather than changing persisted API/project schemas for telemetry.

One short HTTP transaction and one worker transaction share the generation
trace; the worker parent is the actual enqueue/launch span. Worker completion
includes report validation and persisted publication, not just `pipeline.run()`.
Repeated polls and reopening an existing job create no new job-start metric.

### 4.4 Deliberate trace propagation

- Browser: continue only to the exact configured Ohmni API origin and `/api/`
  path, including same-origin Vercel rewrites. No loose substring match for
  `localhost`, arbitrary third-party targets, or propagation to Sentry ingest.
- Backend: custom `ThreadingHTTPServer` has no assumed framework tracing.
  Validate bounded `sentry-trace`/`baggage`, use the pinned SDK continuation API,
  and create a fresh isolated scope per request and per worker. Transfer only
  trace metadata through `_launch`; never copy the HTTP request or entire scope.
- Accept only known trace baggage fields; reject malformed/oversized baggage.
  Same-organization checks are useful but are not authentication: a public DSN
  exposes identifiers. Incoming sampling flags must not override local budgets.
- Add `sentry-trace,baggage` to allowed CORS headers for already-approved origins;
  do not widen the origin policy. Same-origin rewrites and direct Fly requests
  both require tests. [S6]
- Backend outbound trace propagation targets are empty. Do not add trace headers
  to Anthropic or native subprocess environments.
- Restore scopes on all paths. Do not persist trace metadata in CircuitIR,
  artifacts, content hashes, project revisions or electrical evidence.

## 5. Repository instrumentation map

Function names are the stable references; recheck line positions after fetching.

| File / boundary | Required behavior |
|---|---|
| `scripts/demo_server.py:main`, `_configured_provider` | No-op-first initialization, safe configuration failure, bounded shutdown flush. |
| `DemoHandler.do_POST`, relevant handlers, `end_headers` | Normalized routes, continuation, owned outcomes; preserve JSON/status/security contracts. Exclude health/static/poll traffic from core tracing. |
| `JobStore.start`, `start_revision`, `_launch`, `_run`, `_fail`, `_persist_locked` | New job vs reuse, explicit handoff, whole worker lifetime, successful transitions only after persistence. No calls under store lock. |
| `src/ohmni/adapters/anthropic_provider.py:_structured`, `_create` | Logical schema request vs actual vendor attempt, schema retry vs transport failure, actual reported usage. Keep retry policy unchanged. |
| `src/ohmni/application/conversation.py:ConversationPlanner.propose` | Planning validation/refusal outcome, no prompt/messages/plan text. |
| `src/ohmni/application/iteration.py:ProjectAssistant.ask` | Revision-assistant operation, no transcript or revision contents. |
| `src/ohmni/application/projects.py:ProjectPipeline.run` | Actual deterministic synthesis/check/compile stages; no false repair or SPICE stages. |
| `src/ohmni/application/demo.py:run`, `run_proposed`, `finish_design` | Named actual stage spans, separate tool status and report verdict. No second worker root. |
| `src/ohmni/generation/orchestrator.py:DesignOrchestrator.design` | Optional injected observer for actual semantic attempts/repairs; reports remain authoritative. |
| `src/ohmni/adapters/process.py:run_tool` | Whole bounded call including wait/cleanup; safe tool class, duration, numeric exit, timeout/spawn outcome. No command/path/env/output. |
| `apps/web/project-contract.js:projectRequest`, `requestProject` | One owner for transport/timeout/contract failures in current project/chat flow. |
| `apps/web/app.js`, `client-contract.js`, `conversation.js`, `project-assistant.js` | Audit bypass paths and action context; do not indiscriminately capture every catch. |
| `apps/web/index.html`, `scripts/demo_server.py:STATIC_ASSETS` | Load adapter safely, update immutable startup snapshot and content types. |

`run_tool` also serves PDF isolation and other native tooling. Classify from a
small whitelist (`kicad`, `ngspice`, `freerouting`, `pdf_worker`, `other`) without
exporting arbitrary executable names. Its cleanup subprocess is implementation
detail, not a separate engineering stage.

## 6. Privacy and failure contract

### 6.1 Data allowed to leave the process

Allow only release/environment, SDK protocol fields, trace/span IDs, opaque job
correlation, constant operation/site names, owned outcome codes, numeric durations,
bounded counters, known model identifiers, reported token counts and numeric tool
exit codes. Normalize unknown categories to `other`; never serialize arbitrary
objects to decide whether they are safe. Restrict string length, collection size,
recursion depth and numeric finiteness before SDK calls.

No prompts, design descriptions, component lists, netlists, model inputs/outputs,
documents, API keys, cookies, headers, query strings, project names, local variables,
absolute paths, raw stdout/stderr, exception strings/args, or object representations.
Unknown fields are dropped, not passed through with a list of secret replacements.

### 6.2 Owned error events, not raw exception capture

Preserve the existing security contract: broad fail-closed handlers cannot inspect
their exception. Send a constructed event with constant type `OhmniBoundaryFailure`,
an allowlisted site/code, execution context and trace ID. No exception object,
`exc_info`, SDK exception hint or traceback is supplied. Use a stable grouping key
such as site + code; do not group on IDs, paths or variable text.

The first version has **boundary-level diagnostics, not full exception stacks**.
Do not fabricate stack frames or claim the code proves a root cause. Known site
names and release mapping identify where to investigate. Adding sanitized actual
stack frames later requires a separately reviewed, owner-approved amendment to
`SECURITY.md`, which currently excludes traceback logging.

The provider boundary gets its own safe event because HTTP status alone misses
its failures. Track whether a trace already owns a reported unexpected failure
using adapter-private scoped state, so outer worker handlers do not duplicate it.
A genuinely separate subsequent failure, such as persistence failure, remains
reportable. On the browser, do not turn an already-reported backend failure into
a second issue just because its error UI rendered.

### 6.3 Python 2.72 baseline configuration

Pin `sentry-sdk==2.72.0` initially. Re-audit changed behavior before upgrading.
The following is an inspected schema example, **not a tested initialization**:

```python
data_collection = {
    "user_info": False,
    "cookies": {"mode": "off"},
    "http_headers": {"request": {"mode": "off"}},
    "http_bodies": [],
    "url_query_params": {"mode": "off"},
    "graphql": {"document": False, "variables": False},
    "gen_ai": {"inputs": False, "outputs": False},
    "database_query_data": False,
    "queues": False,
    "stack_frame_variables": False,
    "frame_context_lines": 0,
}
```

Also set an owned fixed `server_name`, `auto_session_tracking=False`,
`send_client_reports=False`, `trace_propagation_targets=[]`, and
`trace_lifecycle="static"` **and `stream_gen_ai_spans=False`**. The latter is
necessary because AI spans can otherwise stream separately from transactions.
Use `before_send` and `before_send_transaction` with
strict allowlists; drop the event if filtering fails. Do not rely on streamed
`before_send_span` as the privacy gate: in this version it cannot drop a span,
and a failed callback can retain the original payload. [S2, S3]

Gate application calls and install `before_send_log`/`before_send_metric` that
return `None` when disabled and sanitize when enabled. Do not use
`enable_logs=False`/`enable_metrics=False` as reliable off switches. No logging
integration is necessary for the core. Keep the current safe local `_diagnostic`
output. [S1]

Validate **all serialized envelope item types**, not just event dictionaries.
Exclude sessions, attachments, profiles, streamed spans and client reports from
the core. Any unexpected item in tests fails the gate. Failure-isolation tests
must exercise the real SDK with a recording transport, not only a fake adapter.

## 7. Frontend packaging and privacy

Pin `@sentry/browser` to audited `11.7.0` in the future implementation and use a
small reproducible esbuild entry solely for the telemetry adapter. Preserve the
existing application ESM files. Commit the generated local bundle and license/
version/hash metadata, analogous to existing vendored Three.js; verify rebuild
determinism in CI. This avoids adding a production Vercel build dependency.

Keep a tiny no-throw `apps/web/telemetry.js` facade. Only load the local SDK bundle
when public runtime configuration explicitly enables it. Initialization or bundle
failure must not prevent app startup. Use dynamic import with a bounded safe
failure path; do not queue raw errors/user data while the SDK loads.

Create `apps/web/telemetry-config.js` exporting a plain immutable object with
disabled defaults. It is committed and served as another snapshot asset, so the
same no-build Vercel and local serving paths work. Owner-approved enablement is a
small public-configuration deployment, not an undocumented build-time substitution.
Proposed public config contains only enabled flag, public frontend DSN, environment,
release, approved API origin, trace rate, and optional replay setting. Backend DSN
and auth tokens are not frontend configuration. Any upload token stays outside
the web root and commits. Add new JS/config files to the static snapshot before
enabling the feature. Verify the actual HTTP response remains the source of truth
for API identity. Avoid an endpoint/schema change solely to carry telemetry.

Set browser `defaultIntegrations: false` for the manual core. Any later default
browser integration requires an explicit audit: no automatic console,
DOM text, URL/query or raw arbitrary thrown-object capture in the core. Start with
manual action/request spans and owned error codes; enable broader browser tracing
only after outgoing-envelope tests cover its attributes and propagation behavior.
Capture useful durations without keeping user-entered text as breadcrumbs.

Browser v11 defaults to streamed traces. Explicitly set `traceLifecycle:"static"`
when using a transaction sanitizer; `beforeSendTransaction` does not govern the
default streaming path. If a static-span callback is used, follow the v11
`withStaticSpan` API rather than copying an older callback signature. The v11
`enableLogs`/`enableMetrics` options were removed: do not use them as disable flags.
Backend-only custom metrics are sufficient for the core. [S8]

Existing app JS is unminified; it does not need a source-map upload project to
remain readable. A minified adapter bundle needs its own reproducible private map
if debugging that bundle is desired. Source-map uploads and release publishing
are optional deployment steps requiring credentials, not prerequisites for local
integration. Never publish maps containing embedded private build paths. [S8]

## 8. AI monitoring, outcomes and metrics

### 8.1 AI metadata without content

Instrument the existing provider adapter manually. One logical request may have
multiple schema retries; each actual SDK call is an attempt. The vendor SDK may
also have internal transport retries: do not change their configuration to make
telemetry convenient, and do not claim one observed SDK call equals one wire
request unless tested.

Use Sentry's documented manual AI span conventions for the pinned version [S7]:

```text
op = gen_ai.chat
name = chat {approved request model}
gen_ai.operation.name = chat
gen_ai.provider.name = anthropic
gen_ai.request.model = actual requested model
gen_ai.response.model = actual model reported by a successful response only
```

Set required known attributes at span start. Use a bounded `error.type` and
execution failure status when the call fails. A model span can stand alone; no
fake agent wrapper or conversation ID is needed. Do not relabel deterministic
KiCad stages as model-requested tools. AI latency covers the model call, not later
engineering work. The Conversations dashboard is outside core scope with separate
AI streaming disabled.

Capture the declared provider/model, bounded logical operation, elapsed time and
token usage only when a response actually reports it. Do not upload prompt text,
tools/schema definitions, response IDs, generated JSON or conversation history.
Validate manual span recognition in a local envelope and then in the live AI
dashboard before claiming that dashboard works. Generic provider spans remain
useful if dashboard recognition is not yet demonstrated.

Current `CallUsage` starts token counters at zero, so a missing vendor usage block
can look like zero. Telemetry must retain a separate `usage_reported` fact and omit
unknown counts; do not silently fix production accounting in this task. Never
claim billing cost from tokens alone without known model pricing, cache categories
and a declared estimation basis. Dashboard-estimated cost is not an invoice.

The current span convention counts cache-read and cache-creation tokens inside
`gen_ai.usage.input_tokens`, while also allowing those cache counts as separate
subset attributes. Anthropic reports cache categories separately; normalize only
from observed fields, test cache/no-cache/absent usage cases, and never add subsets
twice. `gen_ai.usage.output_tokens` includes reasoning where applicable and
`gen_ai.usage.total_tokens` is input plus output. Missing categories are not
invented zeros. [S7]

### 8.2 Two orthogonal outcomes

- `execution_outcome`: `ok`, `timeout`, `spawn_failed`, `nonzero_exit`, `error`.
- `engineering_outcome`: owned mapping of `pass`, `reject`, `unknown`,
  `not_applicable`, `not_attempted`, with source report status retained as a bounded
  enum. Missing coverage and unavailable simulation never become pass.

Expected circuit rejection/refusal is an outcome, not an exception issue. SPICE
unavailability does not independently change job/release semantics. A completed
job is not proof of fabrication, hardware safety, RF, firmware or bench validation.

### 8.3 Small metric vocabulary

| Proposed metric | Emission rule / interpretation |
|---|---|
| `ohmni.jobs.accepted` counter | Once for a newly accepted job, never a reused/reopened one. |
| `ohmni.jobs.terminal` counter | Once per actual persisted terminal transition; `complete` or `failed`, flow and bounded reason. |
| `ohmni.stage.duration` distribution, milliseconds | Once per actual timed call; stage + flow + execution outcome. |
| `ohmni.verifier.attempts` counter | One per actual verifier attempt with bounded outcome; denominator for rejection rate. |
| `ohmni.repair.attempts` counter | Actual model-design repair applications only; saved-project flow is not part of its denominator. |
| `ohmni.provider.calls` counter | Observed SDK calls, separate from logical request and internal wire retries. |

Token usage stays on AI spans initially to avoid parallel accounting. Use only
bounded dimensions: environment, release, flow, stage, tool, outcome, failure code.
No job/trace/project IDs, URLs, filenames, user/model prose or timestamps as metric
dimensions. Keep names static and document every enum. Metrics are observations,
not an exactly-once billing ledger: crashes, transport drops and quota exhaustion
can undercount. Do not add a durable telemetry outbox for this hackathon.

Dashboard v1: terminal completion fraction (complete / all terminal jobs),
failure reasons, stage duration by flow, verifier rejection fraction per attempt,
and repair outcomes for model-design flows only. Show counts and sample size with
rates. Accepted-minus-terminal is not an authoritative backlog across crashes.
Custom metrics are emitted independently of trace sampling, but transport/quota
loss can still undercount them. Label trace-derived duration/recovery/token panels
as sampled when applicable; do not mislabel the custom duration distribution as
trace-sampled or extrapolate sampled AI tokens into total account spending.

## 9. Configuration, deployment and spending boundaries

Proposed environment/config names are project decisions, not existing settings:

| Setting | Default / policy |
|---|---|
| `OHMNI_TELEMETRY_ENABLED` | false; absent SDK/DSN is a true no-op. |
| `SENTRY_DSN` | unset; server only. |
| `SENTRY_RELEASE` | deployment commit-derived identifier; never a username/path. |
| `OHMNI_ENV` | explicit `local`, `preview`, `production`, or `hackathon`. |
| `OHMNI_TRACE_SAMPLE_RATE` | 0 unless explicitly enabled; 1 only for a bounded authorized demonstration. |
| `OHMNI_TELEMETRY_METRICS` / `OHMNI_TELEMETRY_LOGS` | false until individually enabled; hooks enforce off. |
| Browser telemetry / replay enablement | false; public frontend DSN and exact API origin supplied separately. |

Use two projects in the same Sentry organization if its chosen plan supports the
team's required access. Confirm organization/region/quotas with the owner; no
account exists yet. Do not infer free quotas, trial availability or billing caps
from the original proposal. Seer is a separate approval and cost decision. [S9]

Preview/CI uses fake transport or telemetry off. Live tests with real Anthropic
calls need the owner's spending approval; an offline fake provider is sufficient
for core tests but is not live AI evidence. Production enablement, replay and
sampling settings require explicit owner approval and observed budget controls.
No tunnel that bypasses ad blockers in this scope.

Errors are emitted independently of trace sampling; an error may therefore have
trace metadata without a retained waterfall. Do not promise every error has a
full trace at partial sampling. Bound queues and avoid per-request flush. Shutdown
may flush with a short configured timeout; upload completion is best effort.
The disable flag/redeploy is the rollback, not a product data migration.

## 10. Delivery sequence and timebox

Proposed work items; not approved ledger entries. Target **180 minutes of core
implementation**, excluding account setup, approval waiting and existing suite
runtime. This is a timebox, not a guarantee that every stretch feature fits.

| Item | Budget | Files / acceptance |
|---|---:|---|
| SENTRY-T01: contracts and SDK adapters | 35 min | New `adapters/telemetry.py`, browser facade/build entry, pinned dependencies/build script. Recording transports, no-op and no-inspection tests first; no live DSN. |
| SENTRY-T02: meaningful failures | 35 min | Provider, planner, server worker/persistence boundaries and shared browser request helper. Exactly one owned issue per failure; unchanged public error/body/status and job behavior. |
| SENTRY-T03: connected execution | 65 min | HTTP scope, `_launch` handoff, worker root, actual application stage spans, manual AI metadata, `run_tool` span. Planning/assistant, confirmed-project generation and legacy demo generation are covered, including concurrent jobs. |
| SENTRY-T04: metrics and proof | 45 min | Bounded metrics, fault harness, dashboard recipe, gates and evidence manifest. Local captures labelled local; no fabricated SaaS screenshots. |
| Live activation gate | After account setup and owner approval; outside core coding budget | Verify real issue ingestion, trace continuity and manual AI/dashboard recognition using authorized test data. Record remaining limitations. Required for a live-integration completion claim. |
| Optional SENTRY-T05 | Later | Masked replay, selected logs, source-map upload and possibly owner-approved Seer. |

Prefer two coherent PRs after approval: core/privacy/error boundaries (T01-T02),
then tracing/metrics/proof (T03-T04). Each starts from latest main once dependencies
merge; do not quietly stack an unmerged implementation dependency. If only one
PR fits the event, combine core work as an explicitly scoped single reviewable
unit; keep deployment switches off until all gates pass.

At the timebox boundary, record exactly what works and what does not. Defer replay,
Seer, broad logging and detailed legacy observer spans first. Never cut privacy,
failure isolation, current chat-flow coverage or honest outcome labeling. An
incomplete trace link is an incomplete feature, not a reason to stage a fake demo.

## 11. Acceptance matrix: required before enabling telemetry

Implement new `tests/test_telemetry.py`, `tests/test_telemetry_integration.py` and
`apps/web/tests/telemetry.test.mjs`, plus focused regressions in existing tests.
Use the actual pinned SDK and a recording transport in addition to unit fakes.

| Probe | Required evidence |
|---|---|
| Hostile errors and objects | Existing no-`str`/`repr` tests pass while enabled; no custom getters invoked by the telemetry path. |
| Disabled/missing SDK/config | No network/transport and identical application outcomes; invalid config does not break startup. |
| SDK failures at every lifecycle point | Init, span entry, status, capture, exit and transport exceptions do not skip work or replace/suppress the original application exception. |
| Canary secrets | Distinct markers in prompt, model output, exception args, local variables, netlist, argv/env/output, path, URL and headers absent from every serialized envelope. |
| Extra/default channels | No unexpected sessions, client reports, profiles, attachments, console/DOM text, subprocess-env injection or auto vendor errors. |
| Provider outage in current chat | One owned event even when public response stays the current `400 invalid_plan` or corresponding assistant response. |
| Two concurrent jobs and requests | Correct parentage, no borrowed breadcrumbs/tags, clean scope restoration on success/failure. |
| Saved project generation | Actual synthesis/ERC/physical spans; no model repair or SPICE spans. |
| Native execution | Missing executable, timeout and nonzero exit distinct; zero exit with failing ERC is not an engineering pass. |
| Publication/persistence failure | No completion metric or success status before a real persisted complete transition. |
| Reuse/poll/restart | No duplicate start/terminal count from polling/reopening; interrupted job is not retroactively a successful trace. |
| Trace input | Missing, foreign, malformed, oversized and caller-sampled headers cannot affect authentication, jobs or local telemetry limits. |
| Frontend serving | Local snapshot and Vercel-style static files load; missing SDK bundle leaves app usable; no bare package import failure. |
| Same/cross-origin requests | Exact target propagation works through same-origin rewrite and allowed direct API; never propagates to other origins. |
| Report regression | Circuit/artifact/report fingerprints and existing status codes/messages unchanged with telemetry on/off. |
| Unknown usage | No invented zero tokens/cost when absent; synthetic fixtures labelled synthetic. |

Existing relevant tests: `test_demo_application.py`, `test_demo_operability.py`,
`test_conversation_api.py`, `test_project_assistant_api.py`, `test_project_api.py`,
`test_anthropic_provider.py`, `test_native_process.py`, `test_architecture.py`,
and frontend conversation/project-contract tests. Extend architecture checks to
keep SDK imports in the adapter and out of deterministic modules.

Canonical future implementation commands (from the implementation worktree):

```powershell
# Use the project virtualenv; an equivalent isolated environment is acceptable.
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& C:\Dev\hackathon\.venv\Scripts\python.exe scripts/ai_state.py validate
& C:\Dev\hackathon\.venv\Scripts\python.exe scripts/verify.py workflow
& C:\Dev\hackathon\.venv\Scripts\python.exe scripts/verify.py fast
& C:\Dev\hackathon\.venv\Scripts\python.exe scripts/verify.py integration
npm.cmd --prefix apps/web test
```

Use the existing full/slow gate when changes affect native execution semantics
or required repository policy demands it. Report missing KiCad/source-corpus
dependencies as skips/limitations; do not rename them passes. Do not buy API
calls merely to make a test green. Record release commit, SDK versions, command
results, local captured envelope artifacts and remaining live checks in the PR.

## 12. Optional replay and Seer

Replay requires explicit enablement after privacy validation. Session sampling
starts at zero; an owner-approved error sampling value is separate. Configure the
actual replay integration with text/input masking and media blocking; no request
or response body capture, no unmask selectors, no canvas integration. Error-only
replay can buffer activity before an error; it is not recording-free beforehand.
Inspect a real captured replay for canaries and linkability before claiming it
works. Owned backend failures need a validated correlation design; do not promise
an automatic frontend replay link when no browser error event was emitted. [S10]

For this product, show navigation/loading/recovery, not a faithful PCB canvas
video. Seer is optional; never promise a full RCA from boundary codes without
stack detail. If approved, label its output as an AI hypothesis and check it
against the known fault. No automatic patch acceptance or merge. [S9]

## 13. Demonstration and eligibility

The strongest demonstration is a real controlled failure with honest recovery:

1. Show the current conversational planner and its separately traced model call.
2. Confirm a supported project and show its deterministic generation trace.
3. In an isolated local harness, inject a named tool timeout; show unchanged safe
   user failure and the correlated issue/tool stage. No new public crash endpoint.
4. Remove the injected fault and run again. Do not count that as autonomous repair.
5. Optionally show the pre-existing scripted repair fixture, explicitly labelled
   synthetic, to demonstrate rejection/repair observability without claiming a
   live model repair or physical hardware proof.

Save an evidence manifest with scenario, flow, fixture/live label, commit, SDK
versions, observed outcome and local/Sentry artifact locations. Screenshots of a
dashboard are evidence only after actual ingestion. No success claims based on
a mocked screenshot or a span name alone.

Published event facts, checked 2026-10-12:

- Organizer site and Devpost identify Oct 17-18 at UCLA. [S11]
- Rules permit existing open-source work but judge newly added event functionality;
  declare Ohmni's pre-existing features and event additions separately. [S12]
- The rules page also lists an April submission deadline, inconsistent with the
  October event. Obtain organizer clarification; do not silently choose one.
- Public Devpost prizes were still undetermined when inspected. Sentry's exact
  minimum feature requirement and interview prize are user-reported, not verified
  by this research. Obtain the sponsor brief; do not assume Seer/replay is mandatory.
- Confirm whether pre-event planning and setup are permitted. Preserve this
  preparation document and a pre-event commit baseline; do not present preparation
  as code built during the event or rewrite timestamps/history.

## 14. Independent plan review and remaining gates

Three separate agents reviewed repository execution, privacy, and primary SDK/event
sources. Findings incorporated: correct current flow; provider errors hidden by
typed HTTP handling; manual AI spans; no raw broad-handler exception capture;
full data-category configuration; explicit thread handoff; no-op log/metric flag
correction; static trace filtering; static bundle serving; bounded metric semantics.

This is a **plan review**, not approval of future code or proof of live Sentry.
Final privacy/configuration and primary-source/schema reviewers passed the
document with no remaining BLOCKER/HIGH findings; their minor clarifications
about browser defaults and metric-versus-trace sampling are incorporated.
The repository reviewer identified one wording error about routing clocks;
the plan now explicitly preserves the router's existing injected deadline clock.
Its two additional suggestions (under-lock diagnostics and an explicit public
config file) are incorporated as well. No other architecture finding remained.
An additional adversarial review using `gpt-6-astra` at `ultra` reasoning passed
the plan with no BLOCKER/HIGH findings; its suggestions to separate offline
acceptance from live activation and name every flow explicitly are incorporated.
Outstanding external gates: user implementation authorization; event/sponsor rules;
organization/region/DSNs and plan entitlements; permitted live telemetry; any
paid model smoke test; replay/Seer/production enablement approval. None is needed
to read or independently audit this document.

## 15. Primary sources and reproduction notes

Source precedence: pinned installed SDK source + release notes for exact behavior;
official SDK docs for concepts; repository code over README/marketing claims.
Do not treat SDK version numbers as permanently current.

- **S1:** [Python 2.68 release: log/metric control change](https://github.com/getsentry/sentry-python/releases/tag/2.68.0).
- **S2:** [Python 2.72 client implementation](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/client.py) and [option definitions](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/consts.py).
- **S3:** [Data-collection schema](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/_types.py), [defaults](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/data_collection.py), and [serialization helpers](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/utils.py).
- **S4:** [Integration defaults](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/integrations/__init__.py), [stdlib hooks](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/integrations/stdlib.py), [thread hooks](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/integrations/threading.py).
- **S5:** [Anthropic integration source](https://github.com/getsentry/sentry-python/blob/2.72.0/sentry_sdk/integrations/anthropic.py).
- **S6:** [Sentry propagation explanation](https://www.sentry.help/en/articles/13965170-why-am-i-seeing-requests-with-sentry-trace-and-baggage-headers), [Python API](https://getsentry.github.io/sentry-python/api.html).
- **S7:** [Manual AI instrumentation](https://docs.sentry.io/platforms/python/agent-tracing/manual-instrumentation/), [AI span conventions](https://develop.sentry.dev/sdk/telemetry/traces/modules/ai-agents/), [Python 2.72 release](https://github.com/getsentry/sentry-python/releases/tag/2.72.0). Validate actual outgoing envelopes and dashboard recognition before live claims.
- **S8:** [Browser SDK tagged source](https://github.com/getsentry/sentry-javascript/tree/11.7.0/packages/browser), [v11 migration](https://github.com/getsentry/sentry-javascript/blob/11.7.0/MIGRATION.md), [Debug-ID source maps](https://docs.sentry.io/platforms/javascript/sourcemaps/uploading/cli/).
- **S9:** [Pricing](https://sentry.io/pricing/), [Seer billing](https://www.sentry.help/en/articles/13964800-how-is-seer-billed-and-how-do-i-predict-costs). Exact organization quotas/entitlements not verified; no account accessed.
- **S10:** [Replay and privacy defaults](https://sentry.io/product/session-replay/), [Replay documentation](https://docs.sentry.io/platforms/javascript/session-replay/).
- **S11:** [Organizer event site](https://ai.lahacks.com/), [Devpost overview](https://la-ai-hackathon-2026.devpost.com/).
- **S12:** [Event rules](https://la-ai-hackathon-2026.devpost.com/rules).

The audit inspected local SDK source without configuring a client/transport and
used an offline hostile-exception serialization probe. No telemetry was sent.
Some official docs return Markdown that the browsing extractor cannot read;
release notes and installed pinned source resolved the material API questions.

## 16. Copyable next-agent handoff

> Read `SENTRY_IMPLEMENTATION_PLAN.md`, `AGENTS.md`, `SECURITY.md` and the `.ai`
> ledger. This document is a proposed plan, not authorization to execute. First
> check for a later explicit owner implementation instruction and preserve the
> unrelated BM-T02 worktree. After authorization, fetch origin/main, create an
> isolated non-behavior branch, recheck the source map, and record approved scope
> in the existing ledger. Implement T01-T04 offline in order using manual bounded
> telemetry and disabled defaults. Never pass caught exceptions or design content
> to Sentry. Test both current project/chat and legacy demo flows, all serialized
> envelopes, hostile objects, concurrent jobs, SDK failures and native-tool
> outcomes. Follow the existing PR/test rules; never merge main. Ask before costs,
> user-facing behavior changes or unapproved live collection. Report precisely
> which local gates and real Sentry checks ran; no fake dashboard or engineering
> claims. Replay and Seer remain optional separately approved work.
