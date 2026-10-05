# Behavior audit

Run from the isolated behavior worktree using the project Python environment:

```text
python -m tools.behavior_audit init
python -m tools.behavior_audit canaries
python -m tools.behavior_audit inventory
python -m tools.behavior_audit fetch --all
python -m tools.behavior_audit probe-ngspice
python -m tools.behavior_audit run-benches
python -m tools.behavior_audit coverage
python -m tools.behavior_audit checkpoint --stage audit
python -m tools.behavior_audit final-report
```

`STATE.json` records the run ID, rule hash, entry status before/current, attempts,
blocked items and latest checkpoint. Initialization preserves an existing state.
`BASELINE.json` keeps the original rule settings, canary hashes, 205 class/bench
identities with expectations, and the protected checkout content fingerprint.
Successful source downloads are reused only when the archived bytes still match
the fetch ledger. Neither a unit-test fake nor the imported `bench_rerun.tsv`
counts as a current-run simulation result.

The seven immutable canary fixtures invoke the same validators as real records.
Adversarial unit tests also disable validators to prove that the canaries then
fail, tamper with archived sources, change expected values, inject non-finite
readings, change the state baseline, and duplicate verifier samples.

A checkpoint always records failures. Missing sources, unavailable ngspice and
unparsed analytical expectations remain failures; the audit does not grant a
bootstrap exemption. Audit software tests can pass while the component corpus
fails its audit. A failed checkpoint prevents advancing a dependent stage;
independent remediation and inventory may continue under the user's decision
policy. The third failed attempt parks that stage item. Protected-checkout or
canary-exhaustion failures record a hard stop.

The product bench entry point is
`ohmni.eda.simulation.NgspiceAdapter.behavior_bench`. It requires ngspice 42,
captures raw output, uses the existing bounded native-process adapter, and
refuses external include and shell/file control commands. The audit inlines
local includes from the authored bench directory and compares exact named
scalar measurements. Unrecognized/qualitative expectations and ambiguous scalar
names fail closed. No expected value or tolerance is inferred to obtain a pass.

Source receipts prove that bytes were fetched, not that a document supports a
claim. Research completion also requires a fresh-context verifier report with
the recorded random sample, source URLs and field-level re-derivations. Imported
named references without resolved URLs remain unresolved. The generator check
preserves the full canonical payload, including basis and confidence.

`FINAL_REPORT.md` is assembled from structured checkpoint results, state,
coverage, decisions, rule changes, and verifier reports. It includes the exact
coverage rows and all failed-check details. Fetched source binaries remain local
under the run directory; the fetch ledger and source hashes are committed. An
absent archive is detected on resume rather than silently trusted.

This is a local audit, not a tamper-proof security boundary against a person who
can rewrite both the code and all Git history. Protected-state checks observe
local branch/ref and checkout contents; no remote server is contacted or mutated.
