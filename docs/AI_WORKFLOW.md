# AI-assisted development workflow

This is Ohmni's repository-development control plane. It coordinates fresh
coding-agent sessions; it is not an Ohmni product runtime or a multi-agent
service. Product requirements remain in `PRD.md`/`MVP_SCOPE.md`, architecture in
`ARCHITECTURE.md` and `docs/DECISIONS.md`, detailed implementation direction in
`IMPLEMENTATION_PLAN.md`, and product verification in `VERIFICATION.md`.

## Ownership and anti-drift rules

- `AGENTS.md` owns the short operating instructions.
- `.ai/tasks.yaml` owns scopes, task lifecycle, dependencies, acceptance, and blockers.
- `.ai/reviews.yaml` owns durable review outcomes and findings.
- `.ai/verification/*.yaml` owns commit-bound quality-gate evidence.
- `.ai/checkpoint.yaml` owns interrupted-session recovery facts.
- `.ai/milestones.yaml` is the historical product-baseline index.
- `.ai/state.yaml` is only the small session entrypoint and derived summary.

`python scripts/ai_state.py validate` rejects disagreement rather than choosing
one file silently. Files use JSON syntax, which is valid YAML 1.2, so validation
needs no product or third-party runtime dependency.

## Human approval boundary

Product scope statuses are `PROPOSED`, `APPROVED`, `IN_PROGRESS`, `REVIEW`,
`VERIFIED`, `COMPLETE`, and `BLOCKED`. Only a human instruction may transition
`PROPOSED -> APPROVED`; the scope must record `approved_by: human` and durable
approval evidence. Agents may create proposed work but cannot approve it, execute
it, or infer approval from priority. Material scope expansions become proposed
tasks unless they are obviously necessary substeps of approved acceptance criteria.

Task statuses are:

- `PROPOSED`: future work; never autonomously executable.
- `APPROVED`: in the approved scope but dependencies may remain.
- `READY`: approved, dependency-complete, and unblocked.
- `IN_PROGRESS`: the single active task.
- `IMPLEMENTED`: change exists; verification is incomplete.
- `VERIFIED`: required commit-bound verification passed.
- `COMPLETE`: verification and required review/gates passed.
- `BLOCKED`: documented impediment; `CANCELLED`: intentionally closed.

`IMPLEMENTED`, `VERIFIED`, and `COMPLETE` are deliberately distinct.

## Deterministic continuation

For “Read the repository state and continue implementation”:

1. Read `AGENTS.md`; inspect `git status` and recent history.
2. Run `python scripts/ai_state.py validate` and `project_status.py`.
3. If a task is `IN_PROGRESS`, follow stale-session recovery below.
4. Read the human-approved scope and its task acceptance criteria.
5. Consider only `APPROVED`/`READY`, unblocked tasks in that scope whose
   dependencies are `COMPLETE`.
6. Sort by descending numeric priority, then ascending stable task ID.
7. Mark exactly one task `IN_PROGRESS`; update the checkpoint.
8. Implement, test, record commit-bound verification, and conduct required review.
9. Commit a coherent unit and record the resulting commit.
10. Mark `COMPLETE` only when verification and review gates permit, refresh
    `.ai/state.yaml`, validate it, and select again.

`python scripts/ai_state.py next` performs the read-only selection. With no
human-approved product scope it reports no executable task.

## Interrupted-session recovery

Never start another task while one is `IN_PROGRESS`. Inspect Git status, recent
commits, acceptance criteria, its verification record, and `.ai/checkpoint.yaml`:

- committed + verified + clean: reconcile the interrupted ledger update;
- modified/untracked files: inspect and resume partial implementation;
- recorded failure: reproduce and debug it;
- disagreement between task/state/checkpoint: stop and request human resolution.

Before a resource/tool/session-limit stop, update the checkpoint with active task,
current commit, changed files, completed substeps, remaining work, last command,
last failure, and exact resume action. A checkpoint may describe uncommitted work;
it does not authorize committing unsafe code.

## Verification freshness and completion

Verification records name the exact evaluated commit, commands, results, counts,
tool versions, skips, and limitations. Later material changes make earlier results
historical, not current. Historical milestone records are never rewritten.

For product milestones, independent review is normally required. `UNAVAILABLE`
is honest but permits only `VERIFIED`, not formal `COMPLETE`. Open `BLOCKER` or
`HIGH` findings always prevent completion. Resolved findings remain in history.

## Stop conditions

Stop when approved work is exhausted; a material product choice is unresolved;
credentials or destructive authorization are needed; requirements contradict;
a major architecture departure or scope expansion is required; external
infrastructure has no safe substitute; security/privacy/financial/production
behavior would require guessing; resource limits prevent safe continuation; or
repository state cannot be recovered. Record the blocker, attempts, exact human
input required, and any independent approved work that remains executable.

## Human approval procedure

The human reviews a proposed scope/task plan and explicitly authorizes it. Record
that instruction in the scope's `approval_evidence`, set `approved_by` to `human`,
transition the scope to `APPROVED`, transition eligible tasks to `APPROVED` or
`READY`, refresh `.ai/state.yaml`, and validate. Agents must not perform this
transition from their own recommendation.

## Canonical gates

```text
python scripts/verify.py workflow
python scripts/verify.py fast
python scripts/verify.py integration
python scripts/verify.py slow
python scripts/verify.py full
```

Fast is the normal development gate. Integration invokes bounded KiCad tests;
slow exercises the golden route/fabrication pipeline; full runs every tier.

