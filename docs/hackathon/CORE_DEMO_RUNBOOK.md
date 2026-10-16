# Core demo: presenter checklist

This is the core-product handoff for the October 17–18 demo. Sentry and Paper
are excluded by the owner's instruction. This does not start the battery-motion
roadmap or change the component-behavior library.

## Choose a dependable presentation path

**Fresh guided build (no paid AI required):**

1. Start the local workspace server with `python scripts/demo_server.py`.
2. Open `http://127.0.0.1:8765/#workspace` and choose **Buttons and lights**.
3. Review the plan, then click **Generate my board**. This saves the revision
   and runs real engineering checks; wait for **Explore your board**.
4. Orbit the board. Open **Checks & evidence** and distinguish warnings,
   checked results and unknowns. The starter includes two buttons, one light
   and a programming header on a 100 × 70 mm board.
5. Open **Build & export**, download the complete package, then use
   **Back to the board**. Reload and open the project from Recent projects;
   **Open this revision's run** restores the existing result.

The sensor and memory starters are also included in the fresh rehearsal. The
landing-page board is a different illustration; do not identify it as the board
whose generated receipts you are showing.

**Conversational opening (only after a successful paid rehearsal):**

Use the fixed prompt from `scripts/rehearse_live_plan.py`: USB-C powered ESP32,
one momentary input button, one indicator LED, no sensors/SPI devices/programming
header, 100 × 70 mm, and an explicit acknowledgment that firmware is separate.
The AI must propose the requested supported configuration. It may not silently
swap parts or constraints to make the demonstration pass. If clarification or a
failure appears, use the offered recovery; do not repeatedly spend on retries.

**Offline fallback:** before presenting, start
`python scripts/serve_offline_demo.py --port 8766` and keep
`http://127.0.0.1:8766/` open. This needs neither native tools nor a key. It shows
saved receipts, a deliberately damaged copy and the restored original. Say
"saved run" and "restore original", not "live simulation" or "AI repair".

## Three-minute sequence

| Time | Action |
|---|---|
| 0:00–0:30 | State the problem and describe the supported controller. Use live planning only if rehearsed; otherwise use the guided starter. |
| 0:30–1:00 | Review the plan and start generation. If generation stalls, switch to the prepared saved result and identify it as saved. |
| 1:00–1:45 | Explore the board and explain one power connection and one button/LED connection. Firmware supplies behavior; moving highlights are not electrical simulation. |
| 1:45–2:20 | Show actual checks. Optionally demonstrate the saved damaged-copy DRC finding and restore the original. |
| 2:20–2:45 | Download the checked original package and show the schematic/PCB/manufacturing inventory. |
| 2:45–3:00 | Explain the boundary: AI proposes, independent checks verify, and unknowns remain visible. |

Keep the saved tab and a previously downloaded, hash-checked package ready. Do
not make a whole-board SPICE claim: these generated boards still lack complete
simulation bindings. They have not been assembled or bench-tested. Example BOM
prices and fabrication assumptions are synthetic, not a supplier quotation.

## Repeatable checks

For a single readiness report covering setup, a fresh qualified board and the
three-family browser rehearsal, run from the project venv:

```sh
python scripts/rehearse_hackathon.py
```

Each invocation creates a new directory under `build/hackathon-rehearsal/` with
`report.txt`, `summary.json`, child logs and engineering/browser receipts. Existing
output directories are refused. A blocked/failed stage stops later stages and
remains visible as such; nothing skipped counts as ready. Exit codes are 0 for
local guided-demo PASS, 1 for failure and 2 for blocked setup. This does not
qualify live AI, Fetch, whole-board simulation or bench hardware. It makes no
model calls and does not register an agent. It installs nothing; run teammate
setup first. A full run includes local board generation and takes about a minute
on the currently qualified Mac; allow longer on other machines.

Use the project venv, installed with `pip install -e ".[dev,mcp,browser,fetch]"`, then
`python -m playwright install chromium`. KiCad 10.0.5 with its libraries must be
available. Follow `docs/TEAM_SETUP.md` for OS-specific setup.

```text
python scripts/rehearse_core_demo.py --output build/core-demo-rehearsal-1
```

The command owns a new local workspace and process tree, with a 15-minute outer
deadline. It runs all three starters through the real browser, HTTP server,
SQLite persistence, KiCad, routing and artifact-download paths. It checks 3D,
390 px layout, back navigation, reload/reopen, server-restart recovery and a simulated provider-outage
recovery. The browser blocks external requests. No real provider is configured
for these checks. Output folders cannot be reused: retain failed reports and use
a new suffix. Screenshots and generated packages stay in the ignored output
folder; `summary.json` reports failures, missing checks and blocked tools honestly.

A separate fresh engineering qualification of the fixed presentation board:

```text
python scripts/verify_hackathon_demo.py --attempts 1 --output-root build/demo-engineering
```

This checks actual ERC, DRC, routing and Gerber/drill receipts. ngspice installation
alone does not add simulation evidence for this board.

Public read-only alignment (no AI calls or writes):

```text
python scripts/rehearse_hackathon_release.py --site https://ohmni-yvnd.vercel.app --include-app --backend-site https://ohmni-demo.fly.dev --health-url https://ohmni-yvnd.vercel.app/api/health --output build/demo-public.json
```

Health proves configuration, not that the provider key works. Static alignment
checks selected assets, not every backend source file or deployment state.

## Guarded live-planning rehearsal

Running `python scripts/rehearse_live_plan.py` alone reports NOT_RUN and reads no
credentials. Only after explicit owner approval:

```text
python scripts/rehearse_live_plan.py --execute-approved --env-file /absolute/private/path/.env --output build/live-plan-1
```

The fixed prompt is submitted through the real local UI to the real planner.
The guard permits one structured provider request with a maximum of 4096 output
tokens. Both provider repair attempts and SDK retries are disabled. A changed
plan or unresolved question fails; the script never silently corrects the model.
An accepted plan is confirmed, generated and downloaded locally, with the ZIP
checked against the saved revision and reports. No production project is created.
No raw provider errors or credentials are written to the summary. The local
workspace contains this fixed public demo request and its generated artifacts.
Do not commit that workspace or copy credentials into the repository.

The flag is an execution guard, not permission to spend. One failed run does not
authorize another paid request. A passing local result does not prove that the
production deployment uses the same key, model or configuration.

## Before going on stage

- Rehearse on the actual presenter browser at the intended zoom and display size.
- Open the public and local fallback tabs and download the original ZIP once.
- Check local native tools before selecting fresh generation. A missing tool
  must show an error, never a fabricated success.
- Refresh stale tabs after a backend restart. Keep each server's workspace separate.
- If paid planning has not passed, present the working guided flow and be clear
  that live AI is unqualified. Do not describe health `free_text: true` as a live pass.
- Do not activate telemetry or deploy as part of this runbook. Merging a PR does
  not itself update Fly.
