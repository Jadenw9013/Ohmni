# Behavior audit decisions

## D-001 — Preserve unresolved source claims

Keep the imported statuses, parameters, basis and confidence unchanged. The
baseline contains 18 complete, 144 partial and 18 research_required entries.
The source ledger records both failed and successful fetches; a named citation
without a resolved fetched URL remains a failure. A fetched file alone does not
establish semantic support. The alternative of promoting a record based on a
download or code change was rejected. Electrical-data effect: no change.

## D-002 — Require the current-run simulator gate

`ngspice -v` is unavailable in the shell. Unit-test doubles and the supplied
ngspice-42 research logs are not current-run bench evidence. All 205 canonical
bench references are sent through the existing product adapter and recorded as
not_run; none is marked passing. The 21 additional authored netlists without a
canonical analytical contract remain flagged. The alternative of importing
historical measurements as new results was rejected. Electrical-data effect:
simulation eligibility is not promoted.

## D-003 — Keep the audit failure visible during independent remediation

The audit software and canaries can work while the component corpus fails the
full checkpoint. Failed source and simulator checks block dependent stages.
Independent source inventory, downloads, coverage generation, and audit repairs
continue. This follows the narrower reading of the failed-checkpoint gate and
the user's independent-work policy. No stage acceptance is inferred from a
passing canary suite.

## D-004 — Protect the actual primary checkout

Hash the primary checkout's tracked and non-ignored untracked files, its index,
HEAD and status, plus main and remote refs. Hashing status alone would miss a
second edit to an already modified file. Existing local work is preserved as the
baseline and is never cleaned or rewritten. No push or merge is performed.

## D-005 — Limit the bench parser to unambiguous sourced measurements

Compare named numeric scalars against the original expected value and tolerance.
Numeric strings and percentage tolerances are parsed without changing the
value. Qualitative expressions, missing measurements and repeated scalar names
remain failures; no guessed alias or enlarged tolerance is introduced.
Electrical-data effect: no change to expectations or tolerances.

## D-006 — Preserve violations and failed-run status in the existing UI

Suppress stale transient curves when a simulation reports unavailable, failed,
timed_out or not_run. A supplied rating violation is displayed as a violation.
The tests exercise the actual existing UI renderer. This is the bounded honesty
repair required by the audit; it does not claim Stage 6's full behavior UI is
implemented or that any electrical rating was evaluated.

## D-007 — Update the approval regression to the newly authorized scope

The workflow regression's exact approved-scope expectation is updated from
Stage 1 to the user's explicit completion scope, with assertions on the new
human approval record. Electrical baselines, benchmark expectations, tolerances
and canary fixture values are unchanged.
