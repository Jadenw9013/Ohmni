# Saved-demo release rehearsal

Rehearsed on 2026-10-14 against candidate
`00016f5fb406b7c0633501e749a0299c04a33aec` (main after PR #76).
This is the independent rehearsal assigned in
[the Claude handoff](CLAUDE_SENTRY_CORE_PROMPT.md). The owner confirmed that the
handoff was sent. Claude owns Sentry and the ledger; this work changes neither
application behavior nor `.ai` acceptance records.

**Disposition: desktop saved-demo checks passed; mobile acceptance remains open.**
This is not approval of a live AI presentation, Sentry ingestion, or a hardware
release. The saved engineering run and this browser rehearsal are separate events.

## What was actually exercised

| Check | Result and boundary |
| --- | --- |
| Public saved-demo assets | At 18:50:31 UTC all 20 reviewed assets at `https://ohmni-yvnd.vercel.app` matched the candidate's committed bytes, with expected content types. Corrected preflight: **PASS**. This identifies these assets, not the whole deployment's commit. |
| Public backend configuration | Vercel `/api/health` and Fly `/api/health` returned `ready`, `free_text: true`, API version 2 and the expected identity field shapes. No model was invoked. This proves neither provider success nor persistent production budgets. |
| Public desktop path | Fresh landing page → Explore demo opened a separate tab. Three.js rendered the original. Show fault displayed its own failed DRC; Restore original restored the original report and download. Back to Ohmni returned home; Start your own board opened the conversational workspace without submitting an idea. |
| Keyboard path | Tab reached Show fault; Space activated it. Tab/Enter reached and activated Restore original. The original-board control regained focus. This is a narrow functional check, not a screen-reader or WCAG audit. |
| Download | Public click produced a download event, but the automation stalled before returning: download latency is **not qualified**. The public ZIP bytes matched the recorded hash, and isolated local browser downloads matched it. |
| Offline browser checker | **17/18 passed; overall FAIL.** Desktop original/fault/restore, stale-response protection, missing-file recovery, ZIP hash, no external requests and no browser errors passed. Original mobile overflow failed. |
| Site-host browser checker | **21/22 passed; overall FAIL.** The same failure occurred. Additional landing/workspace links, return links and preservation of a seeded unsaved draft passed in an isolated browser context. |
| Mobile observation | On resizing to 390 px the checker measured original content at 639 px; fault content was 390 px. A recorded independent localhost diagnostic reproduced 639 px immediately in 7/8 resizes and 390 px after two animation frames in 8/8, all with Three.js active. A separately settled public mobile view also fit its 375 px layout viewport. The existing checker still exits FAIL. |
| 200% zoom / assistive technology | **NOT VERIFIED.** The in-app browser zoom shortcut did not change its scale. Repeat on the actual presenter browser. |
| Fresh engineering, paid AI, Sentry | **NOT RUN.** No new KiCad/SPICE receipt, provider request, telemetry event or production mutation was created. |

The existing browser checker was run unchanged, with Playwright 1.58.0 and
Chromium 145.0.7632.6. Ignored local evidence is under
`build/release-rehearsal/{offline,site}/browser-check.json`, with screenshots.
Those files are local evidence, not committed release artifacts. Preserve failed
reports when repeating a check; use a new evidence directory.
The additional resize diagnosis is recorded locally in
`build/release-rehearsal/mobile-resize-diagnostic.json`; it observed zero external
requests and zero page errors.

The public preflight's first health check incorrectly expected API version 1.
The server contract is version 2 (`scripts/demo_server.py`, `API_VERSION`). That
checker defect was found during this rehearsal; it is not evidence of a public
backend outage. A source-contract regression test guards the correction.

The checker and its tests received an independent review. Both the API-version
defect and an unbounded slow-response wait were corrected before publication;
63 focused tests passed, including a real localhost slow-response regression.
This review is recorded here without modifying Claude's shared task ledger.

Repository validation: `ai_state.py validate` passed; workflow tests 12 passed;
frontend tests 1,105 passed; fast Python suite 2,548 passed, 86 skipped and 63
deselected. That full run collected the original 61 checker cases; after the
version/deadline fixes, the final 63-case checker suite passed separately and was
rerun by the independent reviewer. Changed-file Ruff passed. These are software
checks; skipped/deselected tests and native engineering checks are not passes.

## Reproduce before presenting

Run from the intended candidate checkout. Fetch first and deliberately select the
merged candidate; do not overwrite another agent's working tree. The checker
compares Git blobs, avoiding Windows checkout line-ending differences. It also
checks the local and committed copies of the four capture files.

```powershell
python scripts/rehearse_hackathon_release.py --site https://ohmni-yvnd.vercel.app --health-url https://ohmni-yvnd.vercel.app/api/health --output build/release-rehearsal/preflight.json
```

Exit 0 means all requested static/health checks passed; exit 1 means at least one
failed. Omitting `--health-url` leaves health `NOT_RUN`. No endpoint is contacted
without an explicit site/health URL. The command makes GET requests only, refuses
redirects, checks exact bytes and content types, and bounds response size. It does
not print response bodies, instance IDs or raw transport exceptions.

The default request deadline is 10 seconds, at most 30 with `--timeout`. It bounds
the caller's wait; an in-flight GET may finish afterward while the process lives.
The fixed list permits at most 21 requests. A stalled service should fail the
preflight, not consume the rehearsal indefinitely. Health `free_text: false` is
a valid configured state; it is not a green light for a live AI segment.

Prepare the offline fallback **before** the talk:

```powershell
python scripts/serve_offline_demo.py --port 8765
```

Open `http://127.0.0.1:8765/hackathon-demo.html` and keep that tab and terminal
open. This server uses the Python standard library and local assets; it needs no
AI key, KiCad, SPICE, Sentry or internet connection. Do not open the HTML as a
`file://` URL. Try original → fault → restore → download once before going offline.

For isolated browser checks, use an environment with Playwright and Chromium:

```powershell
python scripts/browser_check_offline_demo.py --host-mode offline --evidence build/release-rehearsal/offline-repeat
python scripts/browser_check_offline_demo.py --host-mode site --evidence build/release-rehearsal/site-repeat
```

Use `--chromium <installed-browser-executable>` when the default managed browser
is unavailable. These commands create temporary local servers, abort non-local
requests and exercise the existing saved capture. They do not qualify a newly
generated board. A browser-check exit of 1 remains a failure even when desktop
steps pass.

## Three-minute presentation and recovery

| Time | Action and truthful narration |
| --- | --- |
| 0:00–0:25 | Open the prepared demo. “Ohmni turns supported electronics ideas into circuit files and shows what was checked. This is a saved run so the demonstration works offline.” |
| 0:25–1:00 | Orbit the original ESP32 button/LED board. Point to the recorded checks. Mention the 17 ERC warnings, clear recorded DRC, and human manufacturing review. The displayed 17.4 seconds is the historical capture time. |
| 1:00–1:45 | Show fault. Point to the disconnected LED pad and the saved real KiCad DRC finding. Other checks are NOT CHECKED for this damaged copy. This button loads a diagnostic capture; it does not run KiCad live. |
| 1:45–2:05 | Restore original. “We returned to the exact original artifact.” This demonstrates artifact separation, not an AI repair. |
| 2:05–2:30 | Download the prepared fabrication package, or show the already-downloaded copy if the browser delays. Explain that the example fab profile is synthetic. |
| 2:30–3:00 | Explain the product path: AI proposes, the user confirms, deterministic checks report their results and limitations. Whole-board simulation and bench operation are not proven by this capture. Show Sentry only after its separate implementation and real-ingestion acceptance. |

If the site or backend fails, switch to the already-open offline tab and identify
it as the saved run. If the renderer fails, use the saved board/report screenshot
as recorded evidence; do not describe a screenshot as an interactive pass. If
asset hashes differ, freeze the last rehearsed checkout and investigate before
using the public site. Do not regenerate a capture, reset budgets or deploy during
the presentation. A live AI failure should return to the saved demonstration,
not trigger repeated billable retries on stage.

The qualified brief is **A2, USB-C 5 V, ESP32-WROOM-32E, one button, one status
LED, no sensors, no programming header, 100 × 70 mm, two layers**. The existing
Buttons and lights shortcut is not this exact brief. See
[overnight results](OVERNIGHT_RESULTS.md) for the recorded 15-part design and its
three qualification runs. No smaller board or expanded configuration is covered
by this rehearsal.

## Remaining work and ownership

1. **MEDIUM — mobile acceptance synchronization:** the label overlay retains a
   desktop pixel width until `ResizeObserver` updates it (`board-view.js:334–341`,
   `:518–526`), while `browser_check_offline_demo.py:193–200` measures immediately
   after resizing. The 8/8 diagnostic establishes a transient layout race, not
   persistent page overflow. In a separate task, make the checker wait for the
   overlay/fallback width to match the board within a bounded deadline, then keep
   the overflow assertion. Consider containing the overlay in runtime CSS after
   coordinating with Claude. Preserve these failed reports and rerun both modes;
   do not silently relabel the unchanged checker as passing.
2. **Presenter check:** perform 200% zoom, keyboard flow and download timing on
   the actual laptop/browser/projector. Avoid an old cached tab; reload after
   deployment and repeat the preflight against the final candidate.
3. **Live AI decision:** a real provider rehearsal and production budget/storage
   evidence remain separate from configuration health. Obtain the owner's
   authorization before paid requests or configuration changes.
4. **Sentry acceptance:** Claude's offline implementation does not prove account
   ingestion. Configure and demonstrate a real sanitized event/trace only after
   the owner authorizes activation; keep it out of the stage story until then.

No independent ledger review or task status was upgraded by this document.

## Capture identity

Capture source commit: `7ab7c26d3d2f67beedebcea21f2e017bc638df8f`.
These hashes identify saved artifacts, not newly executed checks.

| Artifact | SHA-256 |
| --- | --- |
| Original PCB | `378e0ab5838dd253a4f45d4f696a422111ab8e640bd1cddc11076820571a7c92` |
| Fault PCB | `49b74d6c59a8ea6b7dfc92c8af96bfff9579b1e159e48c06761434bd60e3c852` |
| Fabrication ZIP | `5855af1640918185f90d6efc8c51f20fe4046060f32982a098ef5e6b69617748` |

See [the judge Q&A](INDEPENDENT_DEMO_REVIEW.md) for supporting product boundaries
and [site integration](DEMO_SITE_INTEGRATION.md) for the published capture layout.
