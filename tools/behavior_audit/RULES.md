# Component behavior self-audit rules

These rules are the machine-enforced guardrails for behavior Stages 2–7. The
audit hashes this file together with `rules.yaml`; `STATE.json` records the
combined SHA-256. A changed hash is a failure unless `RULE_CHANGES.md` contains
a structured `rule-change` entry for that exact old/new pair. A change may add
or tighten a rule, but may not remove a rule, raise a tolerance, lower an
expected value, reduce coverage, or relax a protected baseline.

| ID | Assertion |
| --- | --- |
| AUD-RULE-001 | The rule hash is unchanged or has an explicit non-loosening change record. |
| AUD-SOURCE-001 | Every external source used by a record or gapfill has a successful, content-hashed fetch ledger entry. |
| AUD-UPGRADE-001 | A status upgrade has field-level sources, basis and confidence plus a passing ngspice 42 bench. |
| AUD-VENDOR-001 | `vendor_model` has an attached model and compatible attached license. |
| AUD-SPEC-001 | Generated records exactly match the deterministic spec-plus-gapfill projection. |
| AUD-BENCH-001 | Required benches ran through product code and satisfy their locked analytical tolerance. |
| AUD-HONESTY-001 | Not-run/error never renders as pass; a rating violation remains a violation. |
| AUD-PROTECT-001 | `main`, the pre-existing production checkout, remote refs and protected spec bytes remain unchanged. |
| AUD-COVERAGE-001 | All 180 IDs have one record and one `COVERAGE.md` row. |
| AUD-REGRESSION-001 | Completed earlier-stage checks rerun at every later checkpoint. |
| AUD-CANARY-001 | Every deliberately bad fixture is rejected by its expected rule. |
| AUD-VERIFY-001 | Research stages have a fresh-context random primary-source sample of K=max(5,ceil(10%)). |
| AUD-RESUME-001 | State and checkpoint writes are atomic and sufficient to resume. |

Bench result files must include the actual `ngspice -v` text, major version 42,
the exact expected and measured numeric values, tolerance, output hash, and
`product_code_path: true`. Absence is failure rather than success.

Status upgrades use `docs/behavior/gapfill/OHM-NNN.audit.json` (or an
`audit-evidence` JSON fence in the corresponding Markdown file). Every upgraded
field names at least one ledgered source, its basis, and confidence. The entry
also names a passing bench result. Code changes alone cannot upgrade status.

The audit snapshots existing dirty production work instead of cleaning or
rewriting it. Any later byte or status change to that checkout fails the
protected-state assertion. The working branch must start with
`codex/behavior-`; the audit never pushes or merges.
