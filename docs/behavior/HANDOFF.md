# Component behavior: handoff for the next session

Written 2026-10-10 at the end of the first behavior push (PRs #1 to #25). Read this first, then
`out/component-behavior/run/DECISIONS.md` (D046 to D055 are the recent history), then
`docs/behavior/README.md`, `docs/behavior/RUNTIME.md` and `docs/behavior/SOURCE_ARCHIVE.md`.

## Where things stand

- 180 catalog entries; 77 are audited simulable (`docs/behavior/COVERAGE.md`). "Simulable" is derived
  on every run: a bound runtime recipe, every runtime receipt passing now, the class benches passing
  and a simulable record disposition. Nothing is promoted by a stored flag.
- 181 runtime receipts and 227 class benches pass under ngspice 42 through the product adapter.
- Audit (`python -m tools.behavior_audit check`): 12 of 13 at the time of writing; AUD-VERIFY-001
  (fresh verifier round) was being run on the owner's machine and should be 13/13 when you start.
  Check `out/component-behavior/run/checkpoints/` and the latest PRs before assuming.
- Ratings are checked on every operating point and transient run: DC limits, time-averaged values,
  peaks, RMS, ripple, surge and pulse comparisons, Schottky leakage runaway (D050 to D054). A check
  that cannot prove a pass reports `unknown` with its reason; the UI never shows unknown as pass.
- The public site (`https://ohmni-yvnd.vercel.app`, backend on Fly) tracks `main`; redeploy
  procedure is in `docs/visual-reference/` (see the commit "Record verified public controller
  deployment and backend handoff").

## Rules that are not negotiable

- Work branches must start with `codex/behavior-` (the audit's AUD-PROTECT-001 checks the prefix).
- Never push or merge to `main` unless the owner says so for that specific run.
- Never edit `COMPONENT_BEHAVIOR_SPEC.md` (protected, hash-locked) or the bench corpus under
  `docs/behavior/bench/` outside an owner-approved re-pin (`docs/behavior/BENCH_REPINS.json`).
- Approval fields (`approved_by`, owner approval records) carry only the owner's own words, quoted,
  with the date. A delegation ("you decide") is recorded as a delegation, not as an approval. The
  session's safety classifier blocks writes that misstate this; do not work around it.
- Every value in a record traces to a document in the fetch ledger. No value from memory. Distributor
  and aggregator copies are secondary; manufacturer documents are primary. Dead URLs are superseded
  in `docs/behavior/SOURCE_BINDINGS.json` or recorded as manufacturer-withdrawn under the stated
  conditions.
- `docs/behavior/runtime-recipes.json` is CRLF. Write it with `.replace("\n", "\r\n")`.
- After changing recipes or gapfills: `python scripts/generate_behavior_records.py --write`, then
  `PYTHONPATH=. python scripts/generate_behavior_examples.py`, then regenerate runtime receipts
  (`run_runtime_recipes` for the touched entries), then the audit. New receipt files under `out/`
  must be `git add -f`'d; the directory is gitignored.
- Commit trailers: `Co-Authored-By` for the model in use and the `Claude-Session` URL.

## Things only the owner's machine can do

- The source archive (`out/component-behavior/run/fetched-sources/`, 392 documents, 413 MB) is not
  in the repository (copyright; the repo is public). The owner holds the bundle
  `fetched-sources.tar.gz` with its sha256. `python -m tools.behavior_audit rebuild-sources`
  rebuilds what still downloads; the cloud sandbox cannot reach most manufacturer hosts, so the
  audit's source check needs the bundle unpacked locally.
- AUD-PROTECT-001 evaluates only from a linked worktree whose primary checkout is the owner's
  `C:\Dev\hackathon`; `python -m tools.behavior_audit rebaseline --reason ... --approved-by ...`
  refreshes it after owner-approved merges.
- Browser downloads of datasheets that block scripts: `tools/behavior_audit/ingest_manual.py`
  records them with the named person's provenance.

## Open decisions for the owner (do not decide these yourself)

1. NE555 behavioral card (`docs/behavior/bench/ic-timer555/ne555.lib`): its output stage is
   referenced to the GND port, so the three 555 entries report negative terminal power and an unknown
   junction check. The fix (an added vcc-to-gnd current source equal to the output current) changes a
   hash-locked bench model and needs an approved re-pin.
2. Generic-package entries (28 blocked as "no exact part bound"): simulate them with a clearly
   labelled class-default model, or keep them blocked. The honest version labels every result
   "class default, no datasheet" in the UI and the API.
3. Blue 5 mm LED (TLHB5800): the manufacturer withdrew the datasheet; a current blue part should be
   chosen if a blue binding is ever wanted.

## What to build next, in order

1. Design-level simulation. Today a user runs the authored reference circuit per part. The missing
   step is compiling a user's own multi-part circuit from the component library and running all the
   rating checks on it. CS-T09 ("SPICE model boundary") and CS-T10 ("LM317 end to end") in
   `.ai/tasks.yaml` are this; `src/ohmni/behavior/netlist.py:compile_circuit` already accepts a
   `CircuitIR` with several components and per-component `BehaviorSelection`s, and
   `NgspiceAdapter.behavior_circuit` runs it with ratings. Check whether the overnight Codex run
   already landed these before starting.
2. AC analysis. Everything is DC or transient. Filters, decoupling, the crystal and resonator
   classes and exact ripple ratings need an AC sweep path in `simulation.py` and `ratings.py`.
3. The 83 blocked entries, by group: 28 generic packages (owner decision above), 26 with unsourced
   ratings or thermal data (research per entry against the archived documents; most manufacturers
   genuinely do not publish them, see D047), 10 mains or safety parts (keep blocked unless a scoped
   model is approved), 5 protocol or firmware parts (not simulable in ngspice), 14 mixed.
4. Class benches for the capacitor families (ceramic, tantalum, film) that still use the authored
   ideal cards without ESR; ESR heating is reported unknown until then.

## How the pieces fit

- `COMPONENT_BEHAVIOR_SPEC.md` (protected) -> `scripts/generate_behavior_records.py` ->
  `src/ohmni/behavior/data/` (classes, entries, manifest). Gapfill pages in `docs/behavior/gapfill/`
  carry the sourced `field_updates`; owner-gated resolutions in
  `docs/behavior/gapfill/STAGE1_MISMATCH_RESOLUTIONS.json` with approvals in `docs/behavior/approvals/`.
- `docs/behavior/runtime-recipes.json` binds an entry to a model: terminal roles, critical facts
  (ratings), model facts (fitted terms, with `fit_curves` read points), templates, limitations.
- `tools/behavior_audit/runtime_benches.py` and `ic_benches.py` define the per-entry runtime checks;
  receipts live in `out/component-behavior/run/runtime-bench-results/`.
- `src/ohmni/behavior/ratings.py` evaluates ratings on operating points and transient windows.
- `src/ohmni/application/component_behavior.py` and `scripts/demo_server.py` expose it to the UI
  (`apps/web/component-behavior.js`, `component-stories.js`).
- `tools/behavior_audit/` is the self-audit: 13 rules in `rules.yaml`, canaries, checkpoints.
