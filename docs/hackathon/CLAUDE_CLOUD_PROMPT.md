# Claude Cloud overnight development prompt

Copy the text below into Claude Cloud with access to `Jadenw9013/Ohmni`.
Sending it is the owner's explicit authorization of this bounded development scope.
The repository file alone is not an approval record.

```text
You are implementing one bounded overnight demo-readiness task for Ohmni.
I approve the scope below and the accompanying OVERNIGHT_DEVELOPMENT_BRIEF.md.
Make routine implementation choices and continue without asking me for approval.
Do not expand the scope or invent engineering evidence to keep moving.

Repository: https://github.com/Jadenw9013/Ohmni
Goal: make a three-minute Oct 17–18 demo dependable: supported idea -> real board
-> recorded checks -> one damaged copy -> real DRC failure -> restore original.

FIRST
Fetch origin/main, inspect status, and read AGENTS.md, docs/AI_WORKFLOW.md,
SECURITY.md and the .ai ledger. Read:
  docs/hackathon/OVERNIGHT_DEVELOPMENT_BRIEF.md
If it is not on main yet, fetch origin/codex/hackathon-overnight-handoff and read
the file with git show from that ref. Record the documentation commit you read.
The documentation branch is only a reading source: create your implementation
branch from the latest origin/main, not from that branch. If the brief cannot be
retrieved, use this prompt's bounded scope and report the missing detailed brief.

Use one scope/task (HACK-DEMO-1 / HACK-DEMO-01 if those IDs are unused), one branch
codex/hackathon-demo-readiness (or a unique suffix), and one PR with coherent
commits. Record this actual message as human scope approval when required by the
ledger. Keep exactly one active task and preserve other agents' work/approvals.
Do not take over an unrelated active task or rewrite accepted history.

PRIORITIES
1. Build a reproducible command for one existing supported board. Start with the
   A2 minimum test configuration: default 100x70mm, one indicator LED, one
   momentary GPIO button, no sensors, no programming header. The previous proposed
   50x40mm/two-LED case fails placement at C5; do not force it or weaken checks.
   Run real synthesis, placement, routing, KiCad ERC/DRC and Gerber/drill export.
   Record exact input/artifact hashes, versions and timings across three fresh
   sequential runs. Use the deterministic typed brief; no paid Claude calls.
   Prefer the production ProjectPipeline.run entrypoint over a test-only pipeline.
2. Add frontend Node tests and a bounded real-KiCad smoke gate to existing CI.
   Missing tools/fixtures or skipped required checks must fail that gate. Preserve
   current fast/corpus jobs and existing verification semantics.
3. Package a labeled saved demonstration with a one-command local preview that
   works without internet or API keys. Include all viewer assets and downloads.
   Test it from a fresh browser context with external network disabled.
4. Add one isolated fault using an existing known-failing test pattern, and a
   clear report/restore-original flow. Preserve the original board/release.
   Each diagnostic result must identify its own immutable artifact and actual
   checker receipt. Never bypass stale guards or reuse good-board passes on the
   damaged copy. A stale-file refusal is not proof of a detected DRC fault.
   Its displayed geometry must match the snapshot whose hash DRC checked.
5. Add configurable bounded request controls to every billed provider path:
   planner, assistant, legacy brief and free-text generation. Use atomic durable
   global daily admission, bounded concurrency and burst control; count failed
   admitted calls. Test with fake providers, return 429/Retry-After appropriately,
   preserve user input, and do not create an abuse-prone public reset/bypass.
   Background jobs retain their concurrency lease until provider work finishes.
6. Only if the above is verified, improve the existing grounded assistant's
   explanation of the exact finding. Keep deterministic text as the fallback;
   no general grading agent, new model context architecture or paid API evaluation.

WORK AUTONOMOUSLY
Prioritize completed tested slices over feature count. Reserve the final 60-90
minutes of the session for verification, independent review if available, and
handoff. Parallelize independent work only with clear file ownership; serialize
heavy EDA jobs and ledger updates. Do not wait for intermediate PR merges.
Keep actual pipeline warnings, UNKNOWN/NOT_CHECKED and source limitations visible.
Model binding is not simulation; existing run_design refuses the whole circuit
when any binding is missing. A GPIO button is not a power switch; firmware is
not proven. No all-green or production-ready claim beyond recorded evidence.

TOOLS AND BLOCKERS
Claude Cloud may lack Docker/KiCad. Attempt permitted pinned setup for at most
about 20 minutes per approach, 45 minutes total on tool acquisition; then use
existing authorized CI or continue work that does not depend on the tool.
Missing real-tool evidence remains NOT_RUN or
BLOCKED. Never fabricate a passing board, fault receipt, screenshot or review.
If no fresh capture can be qualified, use an already approved historical reference
only as a labeled viewer example; do not call it a fresh qualification.
If fresh qualification remains blocked, mark the fault phase blocked and proceed
to request controls. Do not start optional explanation work while earlier gates
remain unverified.
Do not read secrets, acquire private bundles or make paid API calls. Do not
upgrade CI/service plans. Record blocked work and continue independent work.

BOUNDARIES
Never push or merge to main, deploy production, purchase/provision paid resources,
delete branches/history, change accounts, or rotate credentials.
Do not modify src/ohmni/behavior/, tools/behavior_audit/, docs/behavior/,
out/component-behavior/ or scripts/generate_behavior_*.
Do not build A4/flashlight, Freerouting integration, arbitrary board import/upload,
new catalog parts, partial-board SPICE, CPL/JLC sourcing, new fab rules, the full
M10 benchmark, Paper redesign, Sentry integration or behavior audit fixes.
Do not silence tests, forge approval/review records or close unrelated findings.
User-facing changes are limited to the report/fault/reset flow, labeled local
saved demo, and request-limit recovery described above; preserve the main workflow.

VERIFY AND DELIVER
Run scripts/ai_state.py validate, scripts/verify.py workflow, scripts/verify.py
fast, the existing Node frontend suite and relevant real-tool/browser checks.
Record exact commands, counts, tool versions, skips and commit. Keep shared pytest
temp roots from colliding. Require actual ERC/DRC/export receipts for tool claims.
Fix in-scope BLOCKER/HIGH review findings; keep unverified work honestly marked.
Do not knowingly commit broken product code as a checkpoint.
Push only your feature branch and open one PR. Leave it draft if acceptance is
incomplete. Do not merge it. If credentials prevent pushing, leave clean coherent
local commits and exact push/PR instructions; do not expose or seek secrets.
Create docs/hackathon/OVERNIGHT_RESULTS.md with phase status, PR link, reproducible
demo/offline commands, evidence, timings, a 180-second walkthrough, blockers and
the precise owner actions needed in the morning. Leave the ledger/checkpoint
accurate. Independent review unavailable means no invented COMPLETE status.

Begin by verifying the environment and current repository, then implement.
```
