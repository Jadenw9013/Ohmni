# Working with Codex Claude and Antigravity

Use the same repository instructions and acceptance criteria in all three tools.
Model capability does not replace shared contracts, isolated checkouts or live
verification. This workflow prepares bounded assignments; it does not authorize
the Fetch runtime or change the existing task ledger.

## Shared entry points

Each assistant reads `AGENTS.md`, `docs/AI_WORKFLOW.md`,
`docs/AI_TEAMMATE_HANDOFF.md`, the current assigned approval/task, and
`docs/hackathon/FETCH_AI_IMPLEMENTATION_PLAN.md`. Claude already has a `CLAUDE.md`
pointer. `GEMINI.md` supplies the same pointer for Gemini-based work; explicitly
include these paths in Antigravity prompts rather than assuming automatic loading.

Do not maintain three task lists or contradictory instructions. `.ai/tasks.yaml`
remains the task authority. Its single active-task convention stays intact:
parallel assignments require an explicitly approved parent task with bounded
substeps. Otherwise use the tools sequentially or for read-only review.

## Suggested responsibilities after implementation approval

Choose tools based on availability; the roles matter more than the product names.

| Role | Suggested tool | Owned work |
|---|---|---|
| Integrator and engineering bridge | Codex | Service contract, pipeline bridge, shared dependency/config changes and integration |
| Fetch transport implementer | Claude | ACP receiver, registration instructions and transport tests under agreed interfaces |
| Independent acceptance reviewer | Antigravity | Review, local/browser rehearsal and failure-case evidence; no edits to implementation during review |

The integrator writes and freezes the shared operation schemas before transport
and bridge work separate. Only one owner edits dependencies, `.ai` records,
shared application modules and CI. Other assistants request shared changes in
their handoff; they do not silently edit those files.

Use separate clones or Git worktrees for concurrent coding. Never aim two editing
assistants at this same checkout. Give each checkout its own venv and output
directory. Never share an active SQLite workspace. Fetch before assigning work,
record the base commit, and have the integrator resolve changes onto one branch.
Do not let multiple assistants merge, deploy or rewrite history independently.

## Assignment template

```text
Repository: [absolute checkout path]
Role: [implementation or independent review]
Approved parent task and evidence: [task ID and approval path]
Base commit: [verified hash]
Deliverable: [one concrete behavior and acceptance cases]
Allowed files: [exact paths]
Other owners: [paths and owners]
Shared interface: [schema/version or implementation commit]

Read AGENTS.md, docs/AI_WORKFLOW.md, docs/AI_TEAMMATE_HANDOFF.md,
docs/hackathon/FETCH_AI_IMPLEMENTATION_PLAN.md and
docs/hackathon/RESEARCH_AND_READINESS.md. Inspect Git and current task state.
Preserve unrelated work. Do not change shared interfaces, dependencies, ledger,
CI or another owner's files without coordination. Do not push, deploy, activate
accounts or spend on model calls unless this assignment authorizes those actions.

Use the checkout's Python 3.13 venv and isolated output directory. Finish with
changed behavior, commit/diff, exact commands and outcomes, skips, limitations,
remaining blocker and the next executable step. Never call your own review
independent. A mock ACP test is not a demonstrated ASI:One integration.
```

## Integration checkpoints

1. Real ASI:One request reaches one harmless tool before substantial feature work.
2. One shared contract defines session ownership, brief confirmation and job states.
3. Transport and engineering bridge pass their focused tests independently.
4. Integrator runs one complete conversation against the combined checkout.
5. Reviewer receives that exact commit and attempts unsupported inputs, duplicate
   messages, session crossover, job failure and recovery.
6. Integrator fixes findings, reruns affected checks and records final evidence.

Use the weekend reduction gates in the implementation guide. If a role is blocked,
handoff the precise missing contract or credential requirement; do not have a
second model rebuild the same component. Keep meetings and prompts short enough
that the engineer can identify the next action immediately.
