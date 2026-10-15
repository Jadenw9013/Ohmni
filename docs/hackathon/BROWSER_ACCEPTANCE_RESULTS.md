# Hackathon browser acceptance — PR #81

This records the bounded `HACK-BROWSER-01` implementation and the owner-requested
Codex takeover of Claude's draft PR. Approval is in
`.ai/approvals/HACK-BROWSER-1.yaml`. The repair branch starts at main `eae91ecd`
(merged PR #82) and retains Claude's commits through `041d6016`.

## What failed

The original push run
[38684246505](https://github.com/Jadenw9013/Ohmni/actions/runs/38684246505)
passed all 188 saved-demo steps and the six then-existing browser regressions.
Its telemetry smoke process timed out after 15 seconds waiting for the
confirmation button to become enabled during static hosting; the process exited
before writing its summary. The pull-request run on the same head passed.
This was a failing browser test, not a merge conflict or a Vercel build failure.
The PR also remained a draft.

The smoke test waited for any response with the `/api/brief` path, including a
CORS preflight, and treated an enabled confirmation button as proof the brief
was ready. That button is initially enabled even while its section is hidden.
The repair requires the exact API origin and POST method, waits for response
completion, and then checks the rendered brief, visible review section,
released start button and enabled confirmation button. Codex's initial local
runs did not reproduce the historical timeout. Claude subsequently pushed
`041d6016`, reporting a reproduction under CPU load where the page's polling
timer stalled although direct evaluation found an enabled button. That commit
is preserved: readiness is polled from Python with a 30 s budget for the brief,
3 s for board layout and 5 s for restored focus. These are polling budgets;
an individual `page.evaluate()` is not interruptible by that loop. The runner's
600 s process deadline is the outer bound. Readiness arriving after its polling
budget fails, and the focus assertion consumes the polling result. Browser
regressions retain pending-brief, disabled-control and persistent-overflow
failures. Each failed smoke scenario now leaves a sanitized failure entry and
closes its browser context, so the remaining scenarios and summary survive.

## Changes retained and completed

- Saved-demo layout waits for the overlay dimensions to match the board, then
  retains the original overflow assertion. Cold loads and resizing cover
  desktop and 390/375/320 px, original/fault/restore, keyboard controls, missing
  files, delayed responses, draft preservation and hash-verified ZIP downloads.
- Confirmation and proposal application record telemetry success only after
  the real caller accepts the returned revision. Caller tests use the actual
  bundled SDK and an intercepted recording transport.
- The CI runner requires every hosting mode and telemetry scenario. Missing
  browsers, incomplete reports and non-passing checks fail the gate.
- Independent review identified count-only telemetry assertions and accepted
  xfail/xpass/deselected pytest summaries. The gate now rejects those cases,
  requires every named assertion, and validates the recorded envelope counts
  and names for each enabled, disabled and missing-bundle mode.
- Windows verification exposed POSIX-only process cleanup, an implicit-encoding
  approval-file read and CRLF conversion of byte-compared bundle metadata. The
  repair addresses these without changing the committed SDK bundle or license.
- The historical Codex Sentry review remains `CHANGES REQUIRED` at `1e143537`;
  the later passing Claude re-review remains a separate record.

## Verification

Implementation commit: `946d281b781d78f4ac95132791a164046e113356`. Final commands, counts, limitations and
independent review are recorded in `.ai/verification/HACK-BROWSER-01.yaml`
and `.ai/reviews.yaml`. Sanitized browser results are in
`.ai/evidence/HACK-BROWSER-01/browser-acceptance.json`.

| Check | Result |
| --- | --- |
| Ledger and workflow | Valid; 12 tests passed |
| Canonical fast selection | 2688 passed, 88 skipped, 63 deselected |
| Frontend Node suite | 1128 passed |
| Telemetry/integration/architecture | 177 passed, 1 existing Windows skip |
| Offline fault harness | 8 checks passed |
| Pinned browser bundle | Byte-for-byte reproducible |
| Saved demo: offline / site / static | 60 / 64 / 64 checks passed |
| Telemetry browser smoke | 6 scenarios; 58 checks passed |
| Browser regressions / runner regressions | 14 / 13 passed |
| Independent review | Passed; four recorded findings fixed |

The canonical fast tier used a fresh `build/pytest-merged` temporary
directory because this Windows checkout has an access-denied ACL on
`build/pytest`. Its automatic system-temp fallback breaks two existing
repo-relative export tests. No test selection or application code was
changed to work around those tests; the full run passed with the intended
repository-local directory. A browser run concurrent with the fast suite
rejected two loopback asset connection failures. Their cause was not
established. The final aggregate ran by itself after fast; request-failure
assertions were retained, with no retry or failure exemptions added.
Fresh native KiCad and corpus checks are
separate CI gates, not a claim made by these local browser results.
Human acceptance is separate from verification; no implementation agent grants
the task `COMPLETE` status.

## Boundaries

These checks exercise local servers and synthetic telemetry with recording
transports. They do not authorize or prove a paid AI response, live Sentry
ingestion, a fresh manufacturing release, or production deployment. The saved
board and its recorded engineering results are unchanged. Presenter browser
zoom remains unqualified; viewport resizing is not browser zoom.

Vercel previews currently proxy `/api/*` to the production Fly backend.
Preview access protection does not make authenticated preview testing offline.
The acceptance runner uses loopback servers and blocks external browser
requests; it does not run its flows on a Vercel preview. Preview isolation and
credential-scope changes remain a separate owner decision.
