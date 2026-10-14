# Independent Sentry core review

Date: 2026-10-14. Reviewer: Codex, with separate Python privacy, browser and
pipeline reviewers. This is a **read-only review of a frozen work-in-progress
snapshot**, not approval of a completed Claude PR.

- Fetched main: `18022852d102558a9f659c637aaa5a3be99371a1`, after PR #77.
- Reviewed branch: `claude/offline-sentry-core-0k93bj`.
- Initial reviewed commit: `f0adf2043893f581e9e83ee242763a2554b2febd`.
- Delta reviewed through: `1e143537437f23a34826d74b1e9d95dfa003518a`, including
  corrective commit `b0194514` pushed while this review was running.
- Implementation baseline: `00016f5fb406b7c0633501e749a0299c04a33aec`.
- Authority: the owner said “merged go next” after the release rehearsal and
  proposed independent Sentry review. Claude retains implementation and ledger
  ownership. No behavior paths, application files, SDK dependencies or `.ai`
  records were changed by this review.

**Outcome: CHANGES REQUIRED. One HIGH and seven MEDIUM findings remain open.**
IR02 is the remaining HIGH startup blocker. IR05 is FIXED at `b0194514` and
independently retested. IR01's original HIGH disabled-mode failure is fixed;
its enabled-mode residual is MEDIUM and still violates the no-inspection gate.
Later Claude commits require re-review; do not apply this outcome blindly to a
moving branch.

The main requirements are in [the implementation plan](../../SENTRY_IMPLEMENTATION_PLAN.md)
and [Claude's assignment](CLAUDE_SENTRY_CORE_PROMPT.md). No live DSN, provider
request, telemetry activation, deployment or paid service was used. SDK probes
used Sentry Python **2.72.0** and browser **11.7.0**, recording transports/stubs and
synthetic inputs. This is not evidence of Sentry account ingestion.

## Findings and required regressions

All file/line references below refer to the reviewed commit, not this documentation
branch. Unless a delta is stated, line references describe the initial snapshot.
They can be opened under
[`f0adf204` on GitHub](https://github.com/Jadenw9013/Ohmni/tree/f0adf2043893f581e9e83ee242763a2554b2febd).

### SENTRY-IR01 — MEDIUM, partially fixed: enabled telemetry still invokes vendor getters

**Original HIGH disabled-mode defect fixed in `b0194514`; enabled-mode residual
OPEN at `1e143537`.** The history below records the initial regression.

`src/ohmni/adapters/anthropic_provider.py:380–387` reads `message.usage` a second
time, then cache-token and `message.model` properties. `_structured()` always
passes a handle, including the inert handle, so `span is not None` does not skip
this work when telemetry is disabled. These argument expressions are outside
the adapter's no-throw boundary.

Reproduced with valid tool responses and one fake vendor call per scenario:

| Response object | Baseline | Reviewed snapshot, telemetry disabled |
| --- | --- | --- |
| `model` property raises | Returns `Answer(value=7)` | Raises `RuntimeError` |
| `cache_read_input_tokens` property raises | Returns `Answer(value=7)` | Raises `RuntimeError` |
| `usage` property raises on its second read | Reads once; returns `Answer(value=7)` | Reads twice; raises `RuntimeError` |

At `1e143537`, all three disabled probes match baseline results and read counts.
The new enabled path at `anthropic_provider.py:380–392` still invokes the getters.
An ordinary `RuntimeError` is now caught, but its getter side effects occur. A
controlled `GetterSignal(BaseException)` still escapes, replacing the valid
result in all three probes, because the new handler catches only `Exception`.
These are adversarial SDK doubles, not an observed real-provider outage. The
residual is MEDIUM; it remains a failure of the explicit no-inspection acceptance
criterion, even though the default-disabled regression is resolved.

**Fix:** skip optional extraction for inert telemetry. For enabled telemetry,
extract only safe owned/plain fields without invoking arbitrary getters, inside
a failure-isolated helper. Do not change existing provider accounting or response
validation. Add all three disabled/enabled regressions and assert identical
application results/exceptions, not merely that no secret was transmitted.

### SENTRY-IR02 — HIGH: losing the optional browser SDK prevents server startup

`scripts/demo_server.py:108` makes `vendor/sentry-telemetry.js` a mandatory static
asset. `_load_web_snapshot()` at `:265–283`, called during server construction at
`:932`, raises `DemoInitializationError` if it is absent. Reproduced with the
committed disabled configuration by making only that file appear missing.

The browser smoke at `scripts/smoke_browser_telemetry.py:104–108` deliberately
keeps the file present for startup and returns 404 afterward; it does not exercise
this failure. The no-telemetry application should remain usable without the
optional SDK.

**Fix:** retain the immutable static allowlist and UI-version guarantees while
handling this optional artifact's absence safely. Do not broadly disable static
asset validation. Add actual missing-file server-construction tests, followed by
usable disabled and enabled-but-unavailable browser paths.

### SENTRY-IR03 — MEDIUM: invalid response contracts are recorded as successful requests

`apps/web/project-contract.js:224` settles the handle with the HTTP status before
identity validation at `:244`. `apps/web/app.js:338–339` and `:448–449` similarly
finish before `parseBrief`/`parseStart`. A syntactically valid 200 JSON response
with `api_version: 999` throws the existing `api_ui_mismatch` UI error, but the
recorded telemetry calls are only `end(200)`, with no `contract_mismatch` issue.

**Fix:** defer success until the relevant identity/schema validation succeeds.
Preserve HTTP status as a fact, while recording the owned contract failure as
the operation outcome. Keep payloads out of telemetry. Test identity mismatch,
invalid success-body shape, malformed JSON and valid success for each affected
request path; each failure should be reported exactly once.

### SENTRY-IR04 — MEDIUM: independent browser actions share a page-long trace

`scripts/telemetry-browser/entry.mjs:130` calls `startInactiveSpan()` without a
fresh action trace. Two independent requests through the actual bundled SDK
produced distinct span IDs with the same trace ID. The plan explicitly separates
planning, confirmation and later generation; cross-action journey linking was
deferred.

**Fix:** use the pinned SDK's supported fresh-trace context for each independent
action. Continue that action into its API request and worker. With the actual
bundle, assert distinct trace IDs for sequential and concurrent actions, and
matching trace/parent IDs within each browser → server → worker chain.

### SENTRY-IR05 — MEDIUM: progress persistence failure loses its issue and terminal metric

**FIXED in `b0194514`, independently verified at `1e143537`.** The history below
records the original defect. The new worker `finally` drains notices while its
trace scope remains active. The original reproduction now emits one
`persistence.job_persist_failed` issue and one failed-terminal metric, with zero
successful completions. Its new regression and two rejection-marker cases passed
(3 tests). Keep this finding closed unless subsequent edits regress the behavior.

`scripts/demo_server.py:548–558` calls `_persist_locked()`, which queues a
thread-local telemetry notice at `:400–405`. If saving the running progress record
fails and the failed-record recovery save succeeds, the job is already terminal.
The worker returns at `:570–571` before `_flush_telemetry()` at `:592`. The worker
thread then exits with the notice still pending.

Reproduction used a small pipeline that emits one valid `DemoProgress` and
returns the existing test `Report`. The store's `save_job` raises only for status
`running`, and otherwise calls the real store. Actual SDK recording transport:

```json
{"job_status":"failed","error_code":"job_state_invalid","durable_status":"failed",
 "issues":[],"accepted_count":1.0,"terminal_count":0.0,"worker_status":"internal_error"}
```

**Fix:** drain notices on every worker exit in a `finally` outside the store lock
and while its trace scope still exists. Check other early returns and initialization
paths too. Assert one persistence issue, one durable failed-terminal count, zero
completion counts and unchanged job failure behavior. Do not emit under the lock.

### SENTRY-IR06 — MEDIUM: unavailable native checks appear to execute successfully

`src/ohmni/application/projects.py:195–196` and
`src/ohmni/application/demo.py:425–426` explicitly set execution `ok` before
`require_eda_check()` raises. The explicit status survives span exit
(`src/ohmni/adapters/telemetry.py:857–869`); duration metrics use it too.

Actual `ProjectPipeline.run()` with an unavailable-KiCad ERC adapter double and
real SDK recorder raised `EdaToolFailedError`, while its ERC span had status `ok`,
execution `ok`, and engineering `unknown`.

**Fix:** derive execution and engineering outcomes separately from the report.
Missing/error/stale native results require unsuccessful execution and unknown
engineering status. A successfully completed check that finds violations remains
successful execution plus rejection. Assert span status and duration-metric
outcome for both cases. Recheck the analogous DRC and legacy paths.

### SENTRY-IR07 — MEDIUM: a failing SDK child-span exit leaves broken parentage

`src/ohmni/adapters/telemetry.py:857–870,1020–1049` catches an SDK exit failure
without independently restoring the previous current span. A real-SDK probe
made the synthesis span's `Span.__exit__` raise once. The following ERC span
attached to that abandoned synthesis span, which was absent from the serialized
transaction. Application work still ran, but scope restoration did not hold.

**Fix:** restore the owned previous span/context independently of SDK cleanup
success. Cover partial enter and exit failures. Assert that the next sibling
has the correct parent and the outer context is restored, in addition to the
existing assertions about application results and exactly-once execution.

### SENTRY-IR08 — MEDIUM: model-name filtering permits arbitrary prefixed metadata

`src/ohmni/adapters/telemetry.py:107,258–259` accepts arbitrary
`claude-[a-z0-9.-]` text rather than known model identifiers. With the actual SDK,
`response_model="claude-private-design-canary"` appeared in the serialized
envelope. The provider reads this field from `message.model` at `:387`.

This is an adversarial metadata/allowlist gap, **not an observed production
secret leak**. The ordinary owned-event path did not reveal additional raw
content in this review.

**Fix:** allow known identifiers or explicit canonical aliases, and omit or
coarsen unknown values. Add a canary with a valid-looking `claude-` prefix and
assert it never enters any serialized channel.

### SENTRY-IR09 — MEDIUM: Windows fixtures do not isolate the intended test environment

`tests/test_telemetry.py:67` joins `PYTHONPATH` with `:`. Windows uses `;`, so the
child imports the old installed root package rather than the reviewed worktree
and fails with `ImportError`. Independently running this module produced
**70 passed, 1 failed**.

The combined adapter/integration/architecture run finished with **155 passed,
3 failed in 318.35 seconds**. Its two additional failures were the `missing`
and `nonzero` native-tool scenarios at `tests/test_telemetry_integration.py:178–212`:
both observed a real tool `timeout`, instead of no tool span or `nonzero_exit`.
The tests change PATH and create a POSIX shebang file at `:160–166`, but the
Windows locator has an independent Program Files fallback
(`src/ohmni/adapters/tools.py:24,52–62`). These fixtures can reach installed KiCad
rather than their intended missing/fake executable.

**Fix:** use `os.pathsep.join(...)`. Run the subprocess proof from an isolated
worktree on Windows and Linux, explicitly checking that the expected source
module loaded. Make native-tool discovery explicit in tests, with a platform-safe
controlled executable or resolver stub. Assert that the test cannot discover an
installed tool accidentally. Keep actual-native qualification a separate gate.

## Verification and evidence boundaries

The suite counts below are for `f0adf204`. The `1e143537` delta was reviewed by
diff and targeted probes: IR01's disabled/enabled getter cases, IR06's unavailable
ERC case, and IR05's original reproduction plus three new integration cases.
The whole Sentry suite was not rerun at the newer head; these checks are not a
blanket verification claim for it.

- Browser telemetry Node tests: **10 passed**, despite IR02–IR04.
- Python adapter tests: **70 passed, 1 failed** (IR09).
- Combined adapter/integration/architecture tests: **155 passed, 3 failed**
  (IR09). The run completed; it was not cancelled or relabeled as passing.
- Actual SDK probes reproduced IR04, IR05, IR06, IR07 and IR08 without external
  traffic. IR01 compared both source revisions with fake vendor calls.
- IR02 exercised the real immutable-snapshot loader; IR03 exercised the real
  client contract with a controlled invalid response.
- SDK options, channel filtering, explicit capture, and the CI bundle-rebuild
  check are meaningful safeguards. Passing existing tests does not close the
  reproduced gaps above.
- No fresh native-engineering gate passed. The Windows integration fixtures
  attempted installed KiCad and timed out as described above; this is not a new
  engineering receipt. No SPICE qualification, paid model, live ingestion or
  deployment was performed. Committed `.ai/evidence/HACK-SENTRY-01` files are
  Claude's evidence, not new independent executions by this reviewer.
- At the initial snapshot, `SENTRY_CORE_RESULTS.md` contained
  `GATES_PLACEHOLDER` and `LIMITATIONS_PLACEHOLDER`. At `1e143537`, limitations
  are filled in but the gates placeholder remains and no open PR was observed.
  The limitation now acknowledges IR02; documenting a deviation does not resolve
  the missing-bundle acceptance requirement. Treat the handoff as unfinished;
  do not copy its heading's VERIFIED claim into the ledger.

Local ignored diagnostics live under the detached review checkout's
`build/sentry-review/` and `build/privacy-review/`. They are not portable committed
test assets. The scenarios and acceptance conditions above are the durable
handoff; Claude should turn them into repository regression tests.

This documentation PR is based on main `18022852`, not the Sentry branch. Its
own checks passed: `ai_state.py validate`; workflow 12 passed; `verify.py fast`
2,550 passed, 86 skipped, 63 deselected; frontend Node suite 1,105 passed. Those
results establish the review branch's unchanged application baseline and do not
close any Sentry finding. No shared ledger acceptance record was edited.

## Handoff to Claude

Continue your existing Sentry branch; do not rebase or overwrite anyone else's
work. Read this review against the exact commits above, reproduce each open
finding, and address it with the stated regressions. Preserve the IR05 fix and
test; do not repeat already completed work. Keep all existing constraints:
default off, no paid calls or live telemetry, no behavior-path edits, no changed
engineering verdicts, no production deployment or merge.

Fix the HIGH missing-bundle startup defect first, then the remaining
noninterference, request/trace, outcome and privacy/portability gaps. Keep
changes in coherent commits and list each finding with its resolution commit.
Finish the results and commit-bound verification record using actual commands,
counts, skips and blocked gates. Do not silently replace unavailable native or
browser checks with mocks. Open the implementation PR when ready, then request
independent re-review of the final head. Live account activation remains a
separate owner decision after that review passes.
