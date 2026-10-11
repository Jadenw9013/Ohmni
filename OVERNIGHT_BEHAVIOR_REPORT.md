# Overnight component-behavior report (2026-10-10 21:30 → 2026-10-11 ~05:00 UTC)

Unattended run under the owner's standing authorization. Owner-only decisions are in
[MORNING_DECISIONS.md](MORNING_DECISIONS.md). No owner-only item was decided. Two queued questions were acted on under the engineering authorization, after approving proxy reviews, and each can be reverted with a new PR: item 12, where option (a), the tantalum dual solve, was merged in #43 and #45; and item 13, where the design-run panel and endpoint were merged in #42. Item 13 adds a user-facing product surface; please confirm or revert it.

## Setup

- **ngspice:** 42 built from the sha256-verified tarball. `ngspice -v` reports ngspice-42, and `probe-ngspice` passes.
- **Source bundle:** all 13 parts arrived (they were uploaded in three batches during setup). `sha256sum -c` gave OK, and 382 documents were extracted to `out/component-behavior/run/fetched-sources/` (gitignored, never committed).
- **Smoke branch:** pushing `codex/behavior-smoke` worked. Deleting it was refused by the session's git proxy (MORNING_DECISIONS item 2).
- **Audit baseline on main 4fa890a:**
  - `check --no-regression` gave 9/13. AUD-REGRESSION-001 is a fixed failure with that flag, and AUD-RESUME-001 failed on a shallow clone (it passes after `git fetch --unshallow`).
  - The full `check` gave **11/13**. The two failures are AUD-PROTECT-001 (only the owner's checkout can pass it) and AUD-VERIFY-001 (42 stale stage-2/stage-4 verifier reviews, waiting on the `codex/behavior-verifier` round, which never appeared on the remote).
  - The 13 results are tabulated in #28.
- **Codex's parallel work:** Codex was not idle. It merged CS-T07 (#29), CS-T08 (#31), CS-T09 (#33) and CS-T10 (#38) during the night, in parallel with this run. Its CS-T11 (#40) was still open at the end of this run and was not touched.

## Per item

| Item | Shipped | PRs | Proxy verdicts |
|---|---|---|---|
| 1. Design-level simulation | `run_design` + `POST /api/behavior/design/run`, fail-closed binding, per-design summary, per-part model-name scoping (ngspice silently keeps the first duplicate `.model`) | #28 (D056); follow-ups in #34; UI panel #42 | #28 APPROVE; #42 APPROVE after 7 rounds |
| 2. AC analysis and exact ripple | `ACExcitation` (RMS), marker- and frequency-checked AC points and sweep, DC-plus-AC peak/RMS rows, linearity read from the netlist | #30 (D057); fixes #34 (D060), #36 (receipts), #41 (display limits) | #30 BLOCK (after merge) → fixed in #34; #36 APPROVE; #41 APPROVE (round 2) |
| 3. Capacitor ESR | T491 cards carry the sourced 100 kHz maximum ESR with a 100 kHz impedance receipt per part. Their ripple rows are unknown (D063) unless the dual solve proves a pass | #32 (D058); fixes #35 (D061), #37 (D062/D063); dual solve #43 (D064); recipe wording #45 (D065) | #32 BLOCK → #35 BLOCK → #37 APPROVE (round 2); #43 BLOCK → APPROVE (round 2); #45 BLOCK → APPROVE (round 2) |
| 4. Blocked entries | 41 researched against the archive; OHM-037 bound to WIMA MKS4G031003F; 40 reasons updated with what is missing | #39 (D059); fixes #44 | #39 BLOCK (after merge) → #44 APPROVE (round 2) |
| 5. Reviewer follow-ups | everything flagged as must-fix; most follow-ups | #34, #35, #36, #37, #41, #43, #44, #45 | see above. #34 was merged before any review ran; a post-hoc review at the end of the run gave **APPROVE**. As merged it let the T491 ripple and ESR-heating rows pass at ambients ≤ 25 C, which #35–#37 already fixed (D061–D063), and it found nothing open on current main (MORNING_DECISIONS item 11) |

**Scope notes**
- Ceramic: the one simulable part has a dissipation factor with no stated frequency, so no ESR can be derived.
- Film: no film entry was simulable before item 4.
- The mains/safety, protocol and generic-package groups were not touched.

## Counts

- **Audited simulable:** 77 → **78** (OHM-037). Bound entries: 97 → 98.
- **Runtime receipts:** 181 → **186** (all restamped by the #44 and #45 recipe edits). The new ones are four T491 AC impedance receipts and one film charge receipt. All pass, and all 98 bound entries validate.
- **Audit:** **11/13 on main at every recorded checkpoint except between #34 and #36**, the same two rules as the baseline (PROTECT: owner checkout; VERIFY: pending verifier round). One mid-run artifact: between #34 and #36, main failed AUD-BENCH-001 on the four stale tantalum AC receipts (fixed by #36).
- **Full pytest (`verify.py full`):** 2283 passed, 129 skipped, 3 failed on #45's final head, the last behavior PR (2259 passed on #37's head earlier in the night). The 3 failures need KiCad 10 (`kicad-cli` is absent here; apt offers 7.0.11): `test_personal_project_reaches_real_kicad_release…` ×2 and `test_admitted_part_traverses_real_project_release…`. All three fail identically on unchanged main.
- **Node:** 1058/1058 on #42's and #45's heads.

## Notable findings

- **Duplicate model names:** ngspice 42 silently keeps the first of two same-named `.model` cards. Fixed by per-part scoping (D056).
- **Maximum-ESR card:** with the maximum ESR bound, a tantalum's simulated current bounds the real current in neither direction (D063). The dual solve (D064) proves passes without sourcing C or ESL.
- **Rejected download in the ledger:** the ledger counts a 269-byte "Request Rejected" page as a fetched Lite-On datasheet (MORNING_DECISIONS item 5).
- **Mirror and distributor citations:** several blocked records cite mirrors or distributors as manufacturer datasheets (item 6).
- **Wrong reference LED:** `GENERIC_LED_GREEN` is bound to a red reference LED (item 1).

## Process notes

- Seven PRs were merged before their proxy review finished (MORNING_DECISIONS item 11). Every block that a review found was fixed forward, and main was never reverted. #34 was reviewed only post hoc, at the end of the run (APPROVE; its one leak was already fixed by D063).
- One audit run was contaminated by concurrent git operations in its worktree. It was rerun cleanly, and only clean runs are reported.

## Open engineering follow-ups (not owner decisions)

From the post-hoc review of #34; not fixed tonight:
- In the EDLC **transient** branch, a declared ambient above 85 C still lets the "peak voltage at ambient" row pass against the 85 C rating (`ratings.py` around line 523). The part as a whole still reports a violation through the operating-point row "ambient within rated range". The AC branch has had this guard since #34.
- No test covers the AC EDLC branch with an undeclared ambient or one above 85 C, or the T491 transient path with no ambient.
- The "AC swing" unknown row is added only when a class has no AC rows at all, so a class with partial AC coverage is not flagged for each missing limit.

## PRs opened by this run

All merged by squash after green CI (fast and corpus), a full pytest run, node, `ai_state.py validate`, an 11/13 audit and an approving proxy verdict recorded in the PR body. Exceptions:
- The seven merges listed in MORNING_DECISIONS item 11 were merged before their review finished, and #34 was reviewed only post hoc (APPROVE, recorded in its body). #28–#39 landed as merge commits, not squashes (item 10).
- #41's body records neither the node suite nor `ai_state.py validate`.
- #43 did not run the node suite (no `apps/web` change); node passed on #42 and #45 around it.

| PR | Title (short) | Decision |
|---|---|---|
| #28 | Design-level simulation | D056 |
| #30 | AC analysis and exact ripple | D057 |
| #32 | T491 maximum-ESR cards | D058 |
| #34 | AC/design review fixes | D060 |
| #35 | ESR review fixes | D061 |
| #36 | Tantalum AC receipts regenerated | — |
| #37 | Tantalum ripple fails closed | D062, D063 |
| #39 | OHM-037 bound to WIMA MKS 4 | D059 |
| #41 | Display cuts stated | — |
| #42 | Design-run panel and circuit endpoint | — |
| #43 | Tantalum dual solve | D064 |
| #44 | Film review fixes | D059 amended |
| #45 | T491 recipe wording for D064 | D065 |

`ai_state.py validate` passed throughout. No task status or approval record was written. No owner-only item was decided: COMPONENT_BEHAVIOR_SPEC.md, docs/behavior/bench/, class defaults, the blue LED and approval records are untouched.
