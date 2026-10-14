# Sentry core results (HACK-SENTRY-01)

Status: **offline core VERIFIED, live telemetry NOT activated.** Nothing in this
change sends data anywhere by default. Every claim below was checked against the
real pinned SDKs with a recording transport (Python) or intercepted requests
(browser); no Sentry account, DSN, dashboard or paid call was used, so nothing
here proves live ingestion. Plan: [SENTRY_IMPLEMENTATION_PLAN.md](../../SENTRY_IMPLEMENTATION_PLAN.md).
Assignment: [CLAUDE_SENTRY_CORE_PROMPT.md](CLAUDE_SENTRY_CORE_PROMPT.md).

## 1. What works offline

| Area | Offline result |
|---|---|
| SDKs exercised | Python `sentry-sdk==2.72.0` (pinned; any other version refuses activation). Browser `@sentry/browser@11.7.0`, bundled with `esbuild@0.28.2` into `apps/web/vendor/sentry-telemetry.js`. |
| Default | Disabled. With `OHMNI_TELEMETRY_ENABLED` unset the server never imports `sentry_sdk`, and the committed `apps/web/telemetry-config.js` never loads the bundle. Responses, stderr and browser request headers are unchanged. |
| Owned issues | One issue per failed operation, typed `OhmniBoundaryFailure` with value `site.code` (for example `provider.provider_connection`, `worker.eda_tool_failed`, `persistence.job_persist_failed`). Raw exceptions are never handed to the SDK or stringified; engineering rejections are outcomes, not issues. |
| Connected traces | `POST` API routes continue a validated incoming `sentry-trace` (sampled flag stripped, baggage ignored). The worker transaction is a child of the request span through a three-field handoff. Stage, native-tool and manual `gen_ai.chat` spans carry bounded outcomes only. |
| Metrics | `ohmni.jobs.accepted`, `ohmni.jobs.terminal`, `ohmni.stage.duration`, `ohmni.verifier.attempts`, `ohmni.provider.calls`, with fixed low-cardinality attributes. A failed persisted completion is never counted as complete. |
| Browser | A no-throw facade (`apps/web/telemetry.js`) loads the local bundle only when enabled. Manual request transactions for the seven traced POST routes; a trace header only for the exact API origin and `/api/` paths; issues only for `transport_unreachable`, `timeout` and `contract_mismatch`, which the backend cannot see. No default integrations, breadcrumbs, URLs, headers, bodies or thrown values. |
| Channels | Only `event`, `transaction` and `trace_metric` envelope items pass a transport gate. Sessions, client reports, logs, profiles, replay, attachments and breadcrumbs are off and tested. |

## 2. Reproduce

```bash
python -m pip install -e ".[dev]"                     # includes sentry-sdk 2.72.0
python -m pytest -q tests/test_telemetry.py tests/test_telemetry_integration.py tests/test_architecture.py
python scripts/telemetry_fault_harness.py            # 5 scenarios, recording transport
node --test apps/web/tests/telemetry.test.mjs
npm ci --prefix scripts/telemetry-browser && node scripts/telemetry-browser/build.mjs --check
python -m pip install playwright==1.56.0             # plus a local Chromium
python scripts/smoke_browser_telemetry.py            # 3 modes x 2 hostings, external traffic denied
```

Sanitized evidence (issue codes, span names and outcomes, metric attributes; no
raw envelopes) is committed in [.ai/evidence/HACK-SENTRY-01/](../../.ai/evidence/HACK-SENTRY-01/):

- `fault-harness.json`: expected rejection, provider failure, tool timeout,
  publication failure and recovery, with the public outcome beside what was captured.
- `browser-smoke.json`: Chromium version, per-scenario checks, captured item
  summaries and uncaught-error counts for local and static hosting.

## 3. Test and review results

GATES_PLACEHOLDER

## 4. Owner checklist to activate later (two projects)

Activation is a separate owner decision. Do it only after this PR merges.

1. **Create** one Sentry organization with two projects: `ohmni-api` (Python) and
   `ohmni-web` (Browser JavaScript). Confirm plan, region and quotas yourself; this
   work assumes no free tier, trial or billing cap.
2. **Protect spend** before any DSN is used: in each project set a client-key rate
   limit, enable spike protection if your plan has it, and leave Replay, Seer,
   profiling and logs off.
3. **Backend (Fly)**: `fly secrets set SENTRY_DSN=<ohmni-api DSN>`, then set
   `OHMNI_TELEMETRY_ENABLED=1`, `OHMNI_ENV=hackathon`, `SENTRY_RELEASE=ohmni@<git sha>`,
   `OHMNI_TRACE_SAMPLE_RATE=1` for the demo window only (then `0.1` or `0`),
   `OHMNI_TELEMETRY_METRICS=1` and `OHMNI_TELEMETRY_LOGS=0`. The image already
   installs the pinned SDK. Never set `SENTRY_TRACE`, `SENTRY_BAGGAGE`,
   `SENTRY_SPOTLIGHT` or `SENTRY_PRINT_ENVELOPES`; any of them refuses activation.
   On start the server prints one `telemetry_enabled` diagnostic; anything else
   (`invalid`, `unsafe_environment`) means it stayed off.
4. **Web (Vercel)**: in a small reviewed PR, edit `apps/web/telemetry-config.js`:
   `enabled: true`, `dsn: <ohmni-web DSN>` (public by design), the same
   `environment` and `release`, `traceSampleRate` as above, and `apiOrigin: ""`
   while Vercel's `/api` rewrite keeps requests same-origin. Set it to the exact
   API origin only if the page calls the API cross-origin through `OHMNI_API_BASE`.
   The backend DSN and any auth token never go in this file.
5. **Verify live**, which this offline work could not: one controlled failure
   (section 5) produces exactly one issue in each expected project, its trace
   shows browser request, API request and worker in one waterfall, and the
   metrics appear. Record what you saw; until then the dashboard is unverified.
6. **Disable or roll back**: `fly secrets unset SENTRY_DSN` or set
   `OHMNI_TELEMETRY_ENABLED=0` and restart; revert `enabled` to `false` in the web
   config and redeploy. If a DSN leaks, disable that client key in Sentry. No data
   migration is involved.

## 5. 30-45 second demo script

Offline proof (works today, no account):

1. (5 s) "Telemetry is off by default. Here it is on, but every envelope goes to
   an in-memory recorder, and outbound sockets are refused."
2. (15 s) Run `python scripts/telemetry_fault_harness.py`. "Five controlled faults:
   an engineering rejection that is correctly *not* an error, a provider outage,
   a KiCad timeout, a failed save, and the recovery run. Each prints PASS, and a
   canary string we planted in every prompt, path and exception never appears."
3. (10 s) Open `.ai/evidence/HACK-SENTRY-01/fault-harness.json`: "The timeout is a
   `kicad` span with outcome `timeout`, one `worker.eda_tool_failed` issue, and the
   failed save never counted as a completion."

Live dashboard (only after the owner checklist; still unverified):

4. (10 s) Put a fake failing `kicad-cli` first on `PATH` for a local server with
   telemetry enabled, run the fixed example, and show the one issue with its
   linked browser-to-worker trace; remove it, run again, and show the clean
   recovery trace. Say plainly that this part depends on the live account.

## 6. Scope omissions and known limitations

Deliberately omitted, per the plan's timebox and the owner's limits:

- **No live activation.** No account, DSN, deployment, Replay, Seer, source-map
  upload, logs channel or tunnel. The live dashboard, real ingestion and quota
  behavior are unverified.
- **Coarse legacy orchestrator span.** The scripted demo's
  `DesignOrchestrator` runs as one `design_orchestrate` span; its internal
  proposal/check/repair/schematic/ERC steps are not separate spans (plan section 10
  defers detailed legacy observer spans first).
- **Polls are not traced.** `GET /api/jobs/{id}` and other reads create no
  transaction. A persistence failure found during a poll is still reported as an
  issue, but without a trace.
- **Revision reuse** returns the existing job without a separate "reused" marker;
  it never recounts acceptance or completion.
- **Browser coverage** is the seven traced POST routes. Health checks, polls,
  component/behavior pages and the saved hackathon demo page load nothing and are
  not instrumented. The browser emits no metrics.
- **Local server needs the bundle.** The demo server's immutable snapshot
  includes `vendor/sentry-telemetry.js`, so deleting it stops local startup
  (fail closed, like any other snapshot asset). Static hosting without it stays
  usable; the local-server smoke simulates a failed load with a 404 instead.
- **CORS** now always lists `sentry-trace,baggage` as allowed request headers, as
  the plan specifies; `baggage` is accepted and ignored.
- **Supply chain.** `sentry-sdk==2.72.0` is pinned by version, not hash, and its
  transitive dependencies (urllib3, certifi) follow the existing unpinned
  convention. The npm lockfile carries integrity hashes from registry.npmjs.org.
- **Real-browser smoke is local evidence, not a CI job.** CI runs the Node
  facade tests, the bundle reproducibility check and the fault harness; the
  Chromium smoke needs a local Playwright browser.
- **Conflict with the prompt document:** none found. The handoff branch it
  names had already merged as PR #76, so the document was read from `main`.
