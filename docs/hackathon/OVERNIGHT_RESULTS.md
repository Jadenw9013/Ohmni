# Overnight hackathon results (HACK-DEMO-01)

Status: **VERIFIED by the commands below and independently reviewed; awaiting your review.**
The task is not COMPLETE: completion needs your acceptance. Nothing was merged,
deployed, or sent to a paid provider.

## 1. Commits, PR, changed files, phase status

- Base: `origin/main` at `db985333dff91cdab20fd50fca42e693347cf5e0`.
- Branch: `claude/hackathon-overnight-9assxm`.
- PR (draft): https://github.com/Jadenw9013/Ohmni/pull/73
- Implementation commits, oldest first:

| Commit | Purpose |
| --- | --- |
| `42fb74f2` | Ledger: human approval record, HACK-DEMO-01 active |
| `24823fa6` | Fail-closed board qualification harness and isolated DRC fault |
| `88806e0c` | Saved qualified capture and boundary tests |
| `41e35bc3` | CI: Node suite and real-KiCad hackathon gate |
| `4eb9fde7` | Offline saved demonstration with fault and restore |
| `77e7be75` | Demo server: bounded admission for every billed AI request |
| `7ab7c26d` | Fixes for the independent review findings |
| `75ddcf7d` | Saved demonstration recaptured from a clean run at `7ab7c26d` |
| final | This document, verification record and ledger close-out |

Main changed files (run `git diff --stat db985333..HEAD` for the full list):

- `src/ohmni/application/hackathon_demo.py`: qualification, attempt runner, fault snapshot and diagnostic.
- `scripts/verify_hackathon_demo.py`: the harness CLI (exit 0 pass, 1 fail, 2 blocked).
- `scripts/run_in_kicad_image.sh`: runs any command inside `kicad/kicad:10.0.5`.
- `scripts/capture_hackathon_demo.py`: turns a qualified run into the saved offline demonstration.
- `examples/hackathon-demo/`: saved run, fault receipt, fabrication zip, `demo.json`, `harness-summary.json`.
- `apps/web/hackathon-demo.{html,js}`, `apps/web/hackathon-demo-model.js`: offline viewer.
- `scripts/serve_offline_demo.py`, `scripts/browser_check_offline_demo.py`: offline server and browser acceptance check.
- `src/ohmni/application/request_budget.py`, `scripts/demo_server.py`, `scripts/ai_budget.py`: AI request admission.
- `apps/web/{app.js,client-contract.js,project-contract.js}`: truthful 429 and budget-unavailable messages.
- `.github/workflows/ci.yml`: `frontend` and `kicad-gate` jobs.
- Tests: `tests/test_hackathon_demo.py`, `tests/test_request_budget.py`, `apps/web/tests/hackathon-demo.test.mjs`, `apps/web/tests/ai-request-limits.test.mjs`, `tests/test_ai_workflow.py`.
- Ledger: `.ai/approvals/HACK-DEMO-1.yaml`, `.ai/tasks.yaml`, `.ai/state.yaml`, `.ai/checkpoint.yaml`, `.ai/verification/HACK-DEMO-01.yaml`.

| Phase | Status | Evidence |
| --- | --- | --- |
| 0 Environment | DONE | Docker started in the cloud container; `kicad/kicad:10.0.5` pulled; Python 3.13.5, Node available |
| 1 Reproducible board | DONE | 3/3 attempts PASS, 18/18 checks each, identical routed PCB bytes |
| 2 Real checks in CI | DONE | `kicad-gate` job ran the real harness on GitHub (see section 5) |
| 3 Offline demonstration | DONE | Browser check 11/11 PASS with all non-local requests aborted |
| 4 Fault and report | DONE | Real KiCad DRC on the damaged copy, original unchanged |
| 5 AI request controls | DONE | 11 Python and 2 Node tests with fake providers; no production change |
| 6 Optional explanation | NOT STARTED | Left out to keep the night's scope verified; deterministic explanation text ships instead |

## 2. The demo board

- Brief (`hackathon_demo.DEMO_BRIEF`): project "ESP32 button and LED board",
  archetype `a2_usb_gpio_controller`, USB-C 5 V input, 3.3 V logic,
  ESP32-WROOM-32E, no sensors, 1 status LED, 1 button, no programming header,
  2 layers, budget 20 USD.
- Brief fingerprint: `3d1198b29e94303a6d125e010c5e6a7dd020f044ed8f07f0646ddc5a7da77dba`.
- Board: 100 x 70 mm (the archetype default), 15 parts, 179 track segments,
  25 vias, 458.5 mm of copper.
- Routed PCB sha256 (all three attempts): `378e0ab5838dd253a4f45d4f696a422111ab8e640bd1cddc11076820571a7c92`.
- Fabrication package fingerprint of the saved attempt: `157625d3d6b4fcc565022fea236c7889242476f1dce25da061c464019bfa1941`;
  release status `READY_FOR_MANUFACTURING_REVIEW` (synthetic fab profile, human review required).
  The package fingerprint differs between attempts because KiCad writes a creation
  timestamp into each Gerber; the routed PCB bytes do not differ.
- Saved download zip sha256: `5855af1640918185f90d6efc8c51f20fe4046060f32982a098ef5e6b69617748`.
- Damaged copy sha256: `49b74d6c59a8ea6b7dfc92c8af96bfff9579b1e159e48c06761434bd60e3c852`.
- ERC: `pass_with_warnings`, 17 `lib_symbol_issues` warnings, kept visible in the report.
- Harness run used for the capture: `20261014T070148Z` at commit `7ab7c26d`, clean tree,
  copied to `examples/hackathon-demo/harness-summary.json`. An earlier run at `24823fa6`
  also passed 3/3 with the same routed PCB hash.

Measured timings (seconds, local cloud container, KiCad 10.0.5):

| Attempt | Total | Schematic + ERC | Placement | Routing | DRC | Release | Fault diagnostic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 17.37 | 6.45 | 0.76 | 2.29 | 7.00 | 0.84 | 5.95 |
| 2 | 16.42 | 5.78 | 0.79 | 1.79 | 7.15 | 0.89 | 6.14 |
| 3 | 15.63 | 4.98 | 0.85 | 1.98 | 6.76 | 1.04 | 6.63 |

The GitHub `kicad-gate` run measured 11.2 s for one attempt.

The live conversational prompt was **not** exercised: no model call is made by
the harness. Candidate wording is recorded in `CONVERSATIONAL_WORDING`.

## 3. Reproduction

Fresh engineering run with real KiCad (needs Docker; exit 0 only if every attempt passes):

```text
scripts/run_in_kicad_image.sh python3 scripts/verify_hackathon_demo.py --attempts 3
```

That form installs the project inside the image. To reuse an existing local
venv instead, prefix `OHMNI_HOST_SITE_PACKAGES=$PWD/.venv/lib/python3.13/site-packages`.
Without a pinned `kicad-cli` the harness exits 2 (BLOCKED) and never reports a pass.

Offline preview (no network, no KiCad, no model):

```text
python scripts/serve_offline_demo.py
```

Then open http://127.0.0.1:8765/. Browser acceptance check:
`python scripts/browser_check_offline_demo.py` (needs the optional Playwright package).

## 4. Good, bad, and reset

- **Original board:** ERC `pass_with_warnings`, DRC 0 violations and 0 unconnected,
  routing independently re-verified, fabrication bound to the PCB. Report outcome
  `PASS_WITH_WARNINGS`; simulation shows NOT RUN and bench testing NOT VERIFIED.
- **Damaged copy (`cut-led1-anode-track`):** one segment removed, line 362 of
  `golden.kicad_pcb`, net `LED1_A`, from (12.938, 18.9) to (13.75, 19.0) on F.Cu.
  Real `kicad-cli pcb drc` result `fail`:
  - error `unconnected_items`: "Missing connection between items", Pad 2 [LED1_A] of D1 on F.Cu
    and Track [LED1_A] on F.Cu, length 3.0000 mm;
  - warning `track_dangling`: "Track has unconnected end" at (13.75, 19.0).
  The copy is `diagnostic_fault_only`, never releasable, carries no copied checks,
  and shows 7 checks as NOT_CHECKED. The original's hashes are checked before and
  after the diagnostic and stay unchanged.
- **Reset:** "Restore original" re-verifies the original's PCB hash in the browser
  before showing it and returns focus to the original button. The browser check
  ran fault and restore twice, then held the damaged board's file, switched back
  to the original, released the file, and confirmed the late response did not
  replace the original.

## 5. Tests, tools, CI, browser

All at `75ddcf7d` unless noted:

| Command | Result |
| --- | --- |
| `python scripts/ai_state.py validate` | VALID |
| `python scripts/verify.py workflow` | 12 passed |
| `python scripts/verify.py fast` | 2445 passed, 91 skipped, 63 deselected (452 s) |
| `node --test` on every `apps/web/tests/*.test.mjs` file | 1096 passed, 0 failed |
| Harness, 3 attempts, real KiCad (run `20261014T070148Z` at `7ab7c26d`, clean tree) | 3/3 PASS, 18/18 checks each |
| `pytest -m slow_integration tests/test_hackathon_demo.py` in the KiCad image | 1 passed |
| `python scripts/browser_check_offline_demo.py` | 11/11 steps PASS |
| `pytest -m integration` in the KiCad image | 16 passed, 19 skipped, **9 failed** (not this PR, below) |
| `python -m ruff check .` | 21 findings, all pre-existing in untouched files (same on `db985333`) |

The 9 integration failures are behavior simulation tests (`test_behavior_ac`,
`test_behavior_design`, `test_behavior_display_limits`) that need ngspice 42.
The plain `kicad/kicad:10.0.5` image ships ngspice 44.2; the production
Dockerfile builds 42 separately. This branch changes no behavior source or test,
and those paths are protected for this assignment.

Skips: the fast suite's 91 skips are pre-existing tool- and corpus-gated tests.
No new test is skipped.

Independent review: a separate subagent reviewed `db985333..77e7be75` for false
passes, artifact confusion, unbounded provider calls and broken recovery. It found
no BLOCKER or HIGH. Seven findings (2 MEDIUM, 5 LOW) were fixed in `7ab7c26d`,
and the saved demonstration was recaptured from a fresh clean run. Two LOW findings
stay open: invalid or busy AI requests still count toward the daily limit, and
retrying after a 429 on the demo route costs a second admission. The fixes were
not re-reviewed independently. Records: `.ai/reviews.yaml` (HACK-DEMO-01-INDEPENDENT-REVIEW,
HACK-R01 to HACK-R09) and `.ai/verification/HACK-DEMO-01.yaml`.

Tools: kicad-cli 10.0.5 (`kicad/kicad:10.0.5` image), Python 3.13.5, Playwright
1.64 with the preinstalled Chromium. ngspice was not used; no SPICE work is in scope.

CI: run https://github.com/Jadenw9013/Ohmni/actions/runs/38524406695 (head
`4eb9fde7`) passed all four jobs, including `kicad-gate`
("attempt 1: PASS in 11.2s (18/18 checks)", kicad-cli 10.0.5, summary uploaded
as an artifact). Later heads are on the PR's checks tab.

Browser evidence: `build/offline-demo-browser/browser-check.json` and three
screenshots, regenerated by the browser check command (build output is not committed).

## 6. AI request controls

Defaults (`src/ohmni/application/request_budget.py`), all global, no per-IP trust:

| Limit | Default | Variable |
| --- | --- | --- |
| Daily admitted requests (UTC day, durable SQLite, never refunded) | 200 | `OHMNI_AI_DAILY_LIMIT` |
| In-flight billed requests | 2 | `OHMNI_AI_MAX_IN_FLIGHT` |
| Burst | 6 per 60 s | `OHMNI_AI_BURST_LIMIT`, `OHMNI_AI_BURST_WINDOW_SECONDS` |
| Counter file | `out/demo-jobs/ai-request-budget.sqlite3` | `OHMNI_AI_BUDGET_PATH` |

Rationale: enough for a presenter and judges to use every AI path many times, while
a runaway client stops at a small known number. Rejections return 429 with
`Retry-After`; invalid configuration or unreadable storage refuses every billed call.

Guarded routes (admission only when a provider is configured or text is free-form):
`POST /api/planner/propose`, `POST /api/assistant/ask`, `POST /api/brief` with
free text, and `POST /api/demo` with free text. The background job keeps its
in-flight lease until the worker's provider work ends. Health, polling and the
fixed demo request are not counted. There is no reset route; operators use
`python scripts/ai_budget.py show|reset`.

Untested production boundaries:

- A request count is not a dollar cap: provider retries and repair rounds can make several paid calls per admitted request.
- Multiple Fly machines each hold their own in-flight and burst counters; the daily count is shared only if `OHMNI_AI_BUDGET_PATH` is on one volume reachable by all of them, which is not tested.
- No production environment variables were set and production was not deployed.

## 7. 180-second walkthrough

Use the saved run. It is labeled "Saved successful run" on screen; do not run a
fresh pipeline or upload anything during the presentation.

1. 0:00 to 0:30. Start `python scripts/serve_offline_demo.py`, open the page, read the brief: USB-C ESP32, one button, one LED.
2. 0:30 to 1:10. Original board: point at the report card. KiCad ERC and DRC are real receipts; ERC warnings stay visible; simulation and bench testing say NOT RUN and NOT VERIFIED.
3. 1:10 to 1:30. Download the fabrication package; its hash matches the recorded one.
4. 1:30 to 2:20. Show fault. One copper segment on LED1_A was cut. KiCad DRC names pad 2 of D1. The damaged copy cannot be downloaded and does not inherit the original's checks.
5. 2:20 to 2:50. Restore original. The page re-checks the board's hash before showing it.
6. 2:50 to 3:00. Close: the model proposes, KiCad and Ohmni's checks decide.

Fallback: run the browser check before the talk; if the server will not start
on stage, show its screenshots from `build/offline-demo-browser/`, still labeled
as a saved run. They are local output, not committed.

## 8. Remaining owner actions

1. Review PR #73 and decide whether to merge it.
2. Decide on a production deployment; if yes, set the `OHMNI_AI_*` variables and put the budget file on a persistent volume.
3. Rehearse the live conversational prompt with a permitted provider and record whether it yields the same brief.
4. Accept or reject HACK-DEMO-01 in the ledger (it is VERIFIED, not COMPLETE).
5. Optional: approve Phase 6 (grounded DRC explanation) as follow-up work.
