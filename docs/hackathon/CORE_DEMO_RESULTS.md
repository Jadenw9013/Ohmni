# Core demo readiness

Evaluated implementation: `3e6dbb067e253dfcd69bfa49f671c2e1c01d8d09`,
including merged PR #84 (`d42f0b16`). Sentry and Paper are excluded.

## What works locally

The browser rehearsal generated all three supported USB/ESP32 starter boards
through the actual application server and KiCad 10.0.5. Each passed eight checks:
starter selection, generation, rendered 3D board, current engineering report,
downloaded package integrity, back navigation, mobile layout, and reopening the
same run. The downloaded schematic, PCB, fabrication files, report and revision
were checked against their recorded hashes and lineage.

Two further checks passed: a simulated planner outage preserves the request and
offers guided recovery; restarting the server preserves the saved project and
completed run. These checks made zero provider calls, attempted zero external
browser requests, and reported zero browser page errors. The report records a
clean working tree at the evaluated commit.

The planning-to-confirmation-to-generation-to-download wiring also passed with
a synthetic provider and real browser/KiCad. This verifies the wiring, not Claude.

The Windows console discovery fix finds the owner's standard ngspice 42 install
even when an already-open shell has a stale PATH. An executable found through
PATH still takes precedence. Relative paths, directories and the GUI executable
are rejected. Simulation compatibility checks remain unchanged.

## Remaining limits

- Live paid AI planning has not been rehearsed in this pass. The one-call runner
  is opt-in; a flag alone is not authorization to spend. Health/configuration
  checks cannot establish a successful provider response.
- The local generated boards do not have whole-board SPICE, generated firmware,
  assembly or hardware bench qualification. Existing supported simulation tests
  are a separate gate.
- Production received only read-only checks. No deployment or production project
  mutation was performed. Merging this PR does not deploy the Fly backend.
- These are the three existing supported starters, not arbitrary circuit support.
  Battery/motion work and protected behavior findings remain separate.
- Final presenter browser zoom, stage display, network and live credentials still
  need rehearsal on the actual presentation setup.

Use [the presenter runbook](CORE_DEMO_RUNBOOK.md). Commit-bound suite results and
skips are recorded in [the verification record](../../.ai/verification/DEMO-FINAL-01.yaml).
Raw local reports and generated packages are intentionally ignored under
`build/final-readiness/`; reproduce them using the runbook rather than treating
this prose as a test receipt.
