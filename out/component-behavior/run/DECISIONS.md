# Behavior audit decisions

## D-001 â€” Preserve unresolved source claims

Keep the imported statuses, parameters, basis and confidence unchanged. The
baseline contains 18 complete, 144 partial and 18 research_required entries.
The source ledger records both failed and successful fetches; a named citation
without a resolved fetched URL remains a failure. A fetched file alone does not
establish semantic support. The alternative of promoting a record based on a
download or code change was rejected. Electrical-data effect: no change.

## D-002 â€” Require the current-run simulator gate

`ngspice -v` is unavailable in the shell. Unit-test doubles and the supplied
ngspice-42 research logs are not current-run bench evidence. All 205 canonical
bench references are sent through the existing product adapter and recorded as
not_run; none is marked passing. The 21 additional authored netlists without a
canonical analytical contract remain flagged. The alternative of importing
historical measurements as new results was rejected. Electrical-data effect:
simulation eligibility is not promoted.

## D-003 â€” Keep the audit failure visible during independent remediation

The audit software and canaries can work while the component corpus fails the
full checkpoint. Failed source and simulator checks block dependent stages.
Independent source inventory, downloads, coverage generation, and audit repairs
continue. This follows the narrower reading of the failed-checkpoint gate and
the user's independent-work policy. No stage acceptance is inferred from a
passing canary suite.

## D-004 â€” Protect the actual primary checkout

Hash the primary checkout's tracked and non-ignored untracked files, its index,
HEAD and status, plus main and remote refs. Hashing status alone would miss a
second edit to an already modified file. Existing local work is preserved as the
baseline and is never cleaned or rewritten. No push or merge is performed.

## D-005 â€” Limit the bench parser to unambiguous sourced measurements

Compare named numeric scalars against the original expected value and tolerance.
Numeric strings and percentage tolerances are parsed without changing the
value. Qualitative expressions, missing measurements and repeated scalar names
remain failures; no guessed alias or enlarged tolerance is introduced.
Electrical-data effect: no change to expectations or tolerances.

## D-006 â€” Preserve violations and failed-run status in the existing UI

Suppress stale transient curves when a simulation reports unavailable, failed,
timed_out or not_run. A supplied rating violation is displayed as a violation.
The tests exercise the actual existing UI renderer. This is the bounded honesty
repair required by the audit; it does not claim Stage 6's full behavior UI is
implemented or that any electrical rating was evaluated.

## D-007 â€” Update the approval regression to the newly authorized scope

The workflow regression's exact approved-scope expectation is updated from
Stage 1 to the user's explicit completion scope, with assertions on the new
human approval record. Electrical baselines, benchmark expectations, tolerances
and canary fixture values are unchanged.

## D-008 â€” Resume with the installed ngspice 42 console

The user installed ngspice 42. Its console binary has been executed and the
version is recorded in NGSPICE_PROBE.json. The audit process prepends the
confirmed installation directory to its own PATH; no persisted user settings
are changed. The earlier unavailable result remains in Git history. Existing
source and bench failures remain failures until rechecked. Electrical-data
effect: no parameter, tolerance or expected value changes.

## D009 â€” Bench observation mapping repair

Actual ngspice output uses authored scalar identifiers, whereas the spec often
uses descriptive measurement labels. Explicit mappings now cite exact source
lines and the immutable deck hash. Unit conversions are declared per mapping.
Expected values and tolerances remain unchanged. Ambiguous repeated values,
unsupported qualitative contracts and failed solver runs still fail.

## D010 â€” Scoped primary-source corrections, OHM-001..020

Each field is recorded in its entry gapfill with source/page/basis/confidence.
Use conservative standard-operation chip ratings, not extended-operation
ratings. The 3296 CW endpoint is pin 3. Potentiometer end resistance is a
maximum bound, not a nominal value. The 4608X package needs its own 1 W limit.
CRA06P 5% grade has 200 ppm/K TCR. Refuse default RV16 simulation while its
power rating remains unknown; do not borrow the alternate PTV09 rating.
No source status is upgraded and none of these observations rewrites the spec.

## D011 â€” Simulator availability root cause

The installed engine exposed an adapter inconsistency: an explicitly unresolved
executable could be rediscovered by the availability property. Preserve the
adapter's original resolution for both availability and execution. The existing
missing-executable regression assertion is unchanged; the added test prevents
rediscovery. Generated bench decks use LF to preserve reviewable output.

## D012 — Third bench repair preserves observed failures

Relocate exactly three author-directory includes to their existing repository
files, with explicit SHA-256 checks. Ordered repeated operating-point output
requires an exact occurrence count and a declared index, never nearest-value
selection. Unit-bearing tolerances are converted to SI without changing their
magnitudes. Model comparisons select the authored device A, not the deliberate
counterexample device B. All 205 benches now execute through the product adapter:
74 pass and 131 fail their unchanged contracts. The SIP bench has an actual
current-sign mismatch; several magnetic tolerances are numerically absolute,
not percentages. Neither is silently repaired. Qualitative expectations remain
unsupported and failed. Unresolved corpus gate items will be parked at the
third failed checkpoint under the human repair policy; independent research
and implementation may continue with explicit refusals for affected entries.

## D013 - Capacitor references remain condition-specific

T491 ESR and reverse limits are scoped to MnO2. Nichicon auxiliary terminals cannot inherit a guessed negative connection. The 305 VAC WIMA source does not silently raise the 275 VAC default. The AVX 10 x 20 mm body is 5 F, conflicting with the mixed 10 F default; that binding stays blocked.

## D014 - Magnetic winding and rating corrections require explicit binding

Read primary diagrams for WE-SL5, WE-CMB, TY-145P, WE-FB, AS-103 and H1102NL. Record intrinsic manufacturer pin maps separately from geometric terminal transforms. WE-SL5 is 1-2/4-3, AS-103 is 1:300 with an external primary conductor and two secondary pins, and the named flyback has a 12 uH primary. Do not apply guessed permutations, change protected geometry or borrow safety insulation limits. Original source statuses remain unchanged; physical conflicts and missing safety ratings are blocked.
