# AI teammate handoff

This is a navigation guide, not approval to implement a roadmap. Read the live
repository records rather than assuming the last chat or this guide is current.

## Read in this order

1. `AGENTS.md`: operating rules and architectural invariants.
2. `README.md` and `docs/TEAM_SETUP.md`: actual setup and current capability limits.
   For the hackathon, also read `docs/LOCAL_ENGINEERING_SETUP.md` and run its
   per-machine verification before implementation. Coordinate assistant ownership
   through `docs/hackathon/ASSISTANT_WORKFLOW.md`.
3. `git status --short --branch`, `git log -5 --oneline`, then
   `python scripts/ai_state.py validate`, `python scripts/project_status.py` and
   `python scripts/ai_state.py next`: current state and approved task selection.
4. `.ai/state.yaml`, the assigned task in `.ai/tasks.yaml`, its approval record,
   `.ai/checkpoint.yaml`, relevant `.ai/reviews.yaml` findings and verification record.
5. `ARCHITECTURE.md`, `VERIFICATION.md`, `docs/DECISIONS.md` and the assigned area's
   tests. `docs/product/` is proposed product direction, not automatic permission.

`CLAUDE.md` points here and to `AGENTS.md`; do not create a second task ledger.
The `.yaml` control-plane files intentionally use JSON syntax. Preserve existing
history, approval wording and independent-review attribution.

## Where to look

| Concern | Entry points |
|---|---|
| Local HTTP server and project persistence | `scripts/demo_server.py`, `src/ohmni/application/` |
| Workspace UI | `apps/web/app.js`, `apps/web/tests/` |
| Free-text proposals and provider adapters | `src/ohmni/generation/`, `src/ohmni/adapters/` |
| Supported families and admission | `src/ohmni/synthesis/` |
| Electrical truth and evidence | `src/ohmni/domain/`, `datasheet/`, `verifier/`, `catalog/` |
| Native EDA, placement, routing, fabrication | `src/ohmni/eda/`, `physical/`, `routing/`, `manufacturing/` |
| Saved stage demo | `scripts/serve_offline_demo.py`, `examples/hackathon-demo/`, `docs/hackathon/DEMO_SITE_INTEGRATION.md` |
| CI and test tiers | `.github/workflows/ci.yml`, `scripts/verify.py` |
| Optional semantic MCP interface | `docs/MCP_SERVER.md` |

Directory names in the middle rows after the first path are relative to
`src/ohmni/`. Saved demo artifacts are evidence, not disposable fixture outputs.
Do not regenerate them just to make a check pass.

## Copy this into a teammate's coding assistant

Replace the bracketed assignment fields before sending:

```text
You are working on Ohmni in [absolute clone path].
Assigned task: [task ID and exact approved acceptance criteria].
Allowed files/area: [bounded ownership]. Other teammates own: [areas/branches].

Read AGENTS.md, docs/TEAM_SETUP.md and docs/AI_TEAMMATE_HANDOFF.md first.
Inspect Git status, fetch origin, and branch from latest origin/main using
team/[name]-[task] (Codex may use codex/[task], never codex/behavior-*).
Preserve uncommitted work. Never push/merge main or deploy.

Validate .ai state and inspect the assigned task, approval, checkpoint and open
findings. If another task is IN_PROGRESS, coordinate rather than replacing its
ledger slot. Don't start a proposed milestone or a task merely because it is next.
Do not edit behavior paths unless this assignment explicitly authorizes them.

Implement only the assignment. Preserve fail-closed behavior, provenance and
UNKNOWN outcomes. Never invent evidence, source values or test passes.
Use this clone's venv. No paid AI calls, live telemetry, production writes or
secrets in code/logs/prompts. Test against localhost, not Vercel preview APIs.

Run ledger validation, workflow and fast suites plus relevant frontend/native/
browser tests. Report exact counts, skips, tool versions and blockers. Do not
weaken assertions or replace evidence to get green. Self-review the diff; do not
label your own review independent. Open a PR and leave merging to the owner.

Finish with: PR link, implementation commit, changed behavior, tests, limitations,
and a concise continuation note for the next AI. If blocked, report what is
missing without overwriting someone else's checkpoint or approval history.
```

## Handoff checklist

- Branch, base commit, PR and current implementation commit.
- Assigned scope, files changed, other agents' ownership and preserved work.
- Commands run and their actual results; unavailable checks explicitly named.
- Remaining tasks and precise next command; no credential values or private PDFs.
- `.ai` status consistent with evidence. VERIFIED is not COMPLETE, and merge is
  not an independent review or proof of a live deployment.
