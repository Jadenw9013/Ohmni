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

## D015: Diode and LED reference conflicts, 2026-10-05

Use the primary S2M 1.5 A ceiling instead of the unsourced 2 A scaling. Keep earlier conservative 150 C for an unspecified S1M revision although the opened 2024 source says 175 C. BAW56 common-anode variant needs its own 90 V limit and 2 pF maximum, not BAV99 values. Correctly scope SS14 100 C leakage to 6 mA and SS34 to 20 mA. Record the BZT52 thermal-table/note discrepancy rather than selecting a convenient value. DF10M drawing has adjacent AC pins: rotating its top view 90 degrees into the library yields PLUS1/MINUS2/AC3/AC4; the old assumed permutation remains blocked until tested. WOG/MCC mixed physical binding remains unresolved. Do not promote generic LED ratings from a single color/reference, nor treat an absent thermal rating as zero heating. Record reference/body mismatches without changing the 3D library.

## D016 — display bindings and package-specific power limits

Keep display mappings specific to SC56-11EWA, DC56-11EWA and CA56-12EWA; do not infer shared pins from segment count. WS2812B top-view notch is pin3, opposite pin1; intersect its conflicting supply intervals at4.5..5.3 V. Controller-only SSD1306 ratings do not establish module pin order, 5 V tolerance or load current. Block module simulation until those facts are supplied. Keep the six-terminal RGB package blocked when no complete primary PDF can be archived.

XP-E2 Rev25B white reverse limit is1 V; retain its revision scope and do not silently increase existing current ratings. Transistor bindings remain part-specific. IRFP260N source gives1=G,2=D,3=S,tab=D, resolving the earlier extraction error. IRLR8721 power65 W atTC25 and33 W atTC100 are separate conditions. IRFZ44N94 W versus RthJC1.5 remains a genuine conflict: enforce both limits, choosing the lower power. None of these datasheet facts makes a generic package an electrically verified part.

Python TLS errors were recoverable with normal Windows trust-store validation. Added a PowerShell fetch adapter that preserves certificate verification and records exact response hashes; HTTP success does not by itself establish that a response is a datasheet, so HTML rejection pages were not used as evidence.

## D017 — final batch-A power-package conditions

The IRFZ44NS manufacturer summary says110 W and1.4 K/W while its archived2004 PDF says94 W and1.5 K/W. Use the lower PDF power ceiling and enforce junction-temperature headroom as well; do not silently combine revisions. The default D2PAK L7805 remains a separate blocked binding. Si7898DP continuous25 C limits are3 A and1.9 W on the specified board;4.8 A and5 W apply for10 seconds. Both time conditions are recorded, with no source-status upgrade.

## D018 — avoid unrelated source hashing during field checks

Restricted each field check to ledger rows for its own cited URLs. Their archived bytes are still hashed afresh on each invocation; no persistent validation cache or acceptance rule was added. Existing tamper tests and all seven canaries pass. This makes the full research audit practical without changing which sources pass.

## D019 — destructive avalanche energy is not an operating rating

Primary IRFZ44N/IRFZ44NS p2 footnotes identify530 mJ as a typical destruction value outside rated limits; the calculated thermal ceiling is150 mJ. The existing BEH-TRN-MOSFET0.53 J guard is therefore unsafe as an operating acceptance condition. Preserve the historical source/bench contracts, but block that avalanche guard in the runtime. Source pulse inductance also differs between table0.47 mH and note0.48 mH. No guessed replacement pulse law is permitted.

## D020 — IRLR8721 package current and pulse conditions

The50 A package ceiling from p12 note4 limits the65 A calculated junction-temperature current on p1. Both remain recorded; runtime limits must obey the lower. The RDS(on) rows reference note4 while the pulse duration/duty statement is note3; retain this ambiguity rather than certifying a guessed linkage.

## D021 — independent-review freshness is checked against inputs

AUD-VERIFY-001 now rejects a report whose seed/population/sample differs from the current plan or whose reviewed gapfill/record hashes differ from current files. This closes a stale-report acceptance path without changing or loosening the locked rule. A regression test proves that both a new seed and changed reviewed content invalidate a prior pass. Historical rejected reports remain retained.

## D022 — HTTP200 HTML rejection is not a PDF source

AUD-SOURCE-001 now checks that a URL ending in.pdf has a PDF header in its archived content before accepting the fetch. This rejects distributor HTML refusal pages even when they return HTTP200 and a valid hash. Existing hash-tamper checks and seven canaries still pass; a dedicated regression covers the false-success response. The source acceptance count decreased from229 to223 of295, as it should; no limit or source requirement was relaxed.

## D023 — Stage 2 review repair limit

The third independently seeded review found ten scope omissions in OHM-096/097 and could not verify unsourced OHM-083. Added all stated source conditions without changing numbers. Park the Stage 2 independent-acceptance item after three failed samples under the human repair policy; retain failed reports and do not re-seed to avoid OHM-083. Continue independent implementation with source-critical refusals. This is not a Stage 2 acceptance or source-status upgrade.

## D024 — Checkpoint 010 execution access failure

Checkpoint 010 could not read the primary checkout because Git rejected the sandbox account's ownership, and its focused pytest run could not reuse a test directory owned by a prior process. The full fast suite nevertheless ran (1777 passed, 82 skipped, 49 deselected). Re-running the protected-path assertion with local read access proved main, the production checkout, remote refs and protected files still match the locked baseline. Clear the automatically set protected-path hard-stop flag only after that successful assertion, then rerun the complete checkpoint. No protected path was edited and no rule or baseline was changed.

## D025 — Explicit runtime bindings and independent receipt checks

Stage 3 keeps CircuitIR electrical intent unchanged. Generated runtime recipes join package terminals to canonical model templates and the scoped gapfill rating fields. Catalog pin permutations must be present; the approved LED permutation is tested at node assignment. Missing critical facts, unresolved research blockers, missing pins or package mismatches refuse the entire circuit. The first ten resistor entries use ideal resistance and explicit instance values, never fabricated parasitics. An OHM reference model does not verify a purchased generic component. Runtime checks reuse the locked RES-FIXED/B1 divider expectation, retain raw ngspice-42 output and version, and independently reparse observations and input hashes before they can count toward coverage. Source statuses are unchanged.

## D026 — Preserve model confidence separately from scoped ratings

The first runtime projection initially took its single confidence label from sourced rating fields. Correct it before committing: the authored resistor model confidence remains M, while its newly re-derived scoped ratings can be H. Carry the complete original class confidence dictionary (including L failure confidence) alongside both labels. A high-confidence power rating cannot upgrade model or failure confidence. Regression explicitly asserts this separation; no electrical numbers or source statuses changed.

## D027 — Runtime temperature and scoped model defaults (2026-10-05)

The three fit-A diode bindings retain the authored proxy and the required tnom/temp25 C. Their current-run forward probes measure0.7255607 V, while the unchanged legacy B1 contract expects0.73039 V +/-0.001 V and its source deck leaves temperature at ngspice default27 C. The runtime acceptance remains failed; neither the baseline nor the temperature requirement is relaxed. BCX56-16 uses the explicitly authorized geometric-mean gain model with primary-source100..250 gain limits at2 V/150 mA/25 C; IS=1e-14 remains ASSUMPTION. MOSFET default bindings are IRFZ44N, IRFP260N and Si7898DP only; unrelated researched alternatives are not silently substituted.

## D028 — Checkpoint regression and byte-preserving sources

Checkpoint015 recorded one local HTTP connection-aborted regression failure. The unchanged12-test server suite passed alone; checkpoint016 reran all four locked regressions and passed1817 fast tests with82 skipped and49 deselected. No test timeout, expected value or tolerance was changed. Git attributes preserve exact behavior spec, gapfill, model-asset and generated-record bytes across checkouts, because source anchors and independent reviews use SHA-256. Current protected spec bytes match HEAD; this changes checkout policy only, not electrical content.

## D029 — Scoped discrete and magnetic reference models

Use the sourced 20% SRP7028A and 10% SDR0604/RLB0914 saturation definitions, preserving typical versus guaranteed conditions. Capacitance is derived from sourced SRF with the simple LC equation; it is not a fitted broadband loss model. The 2107-V-RC uses its measured-at-rated-current inductance point and remains DC-only because SRF is unsourced. The explicitly named Fairchild BD139 uses its narrower ungraded 40..160 gain range, not the ST-based 40..250 range or the separate grade-16 classification. The red LED model remains the authored approximate 2.0 V fit, alongside the TLDR4400 source 1.8 V typical and 2.2 V maximum at 20 mA. No source status is upgraded and no model is called a vendor model.

## D030 — Distinguish mandatory rechecks from repair attempts

Earlier STATE.attempts counted every failed checkpoint, including mandatory rechecks of already parked gates. Cap active attempt counters at the unchanged three-attempt ceiling and keep continued failures in failed_gate_observations. Where an old counter exceeds three, preserve it in legacy_checkpoint_attempt_counts; historical checkpoints remain unchanged. Rechecking a parked gate cannot authorize a fourth repair attempt. No rule, baseline, expected value, tolerance or failed verdict changes.

## D031 — Reference-specific topology and proxy limits

Bind only the two-terminal WSL2512, using its sourced 110 ppm/C TCR bound rather than the original 75 default; four-terminal alternatives remain unavailable. Bind all seven branches of the eight-pin bussed SIP network and retain its separate 0.2 W element and 1 W package limits. DF10M uses the source drawing rotated 90 degrees counter-clockwise, giving library pins PLUS, MINUS, AC1, AC2; test both AC input polarities instead of retaining the unsafe diagonal-AC assumption. S1M and the additional LED bindings explicitly identify their authored family proxy, which is distinct from the named reference's ratings and cannot establish physical equivalence or a typical I/V fit. RGB reverse operation is not recommended; its final-test reverse voltage is not promoted to an operating rating. All original source statuses and locked bench contracts remain unchanged.

## D032 — Explicit alternatives and the TVS rounded-fit defect

Use the original entry-specific S1M fit and its proposed proxy for the explicitly selected S2M PN alternative, without claiming that a PN diode implements the SS24 Schottky default. The Coilcraft alternative is DC-only and its 15 C-rise current is not an absolute maximum. BAT42W uses explicitly provisional BAT54 proxy parameters. The BZT52 binding retains its 0.37 W ambient and distinct 0.5 W lead-temperature conditions; capacitance/temperature response is not invented. The initial SMBJ15A model at25 C produced24.40568 V at24.6 A, which passed the unchanged legacy tolerance but failed the source24.4 V bound. A recorded bisection through the product adapter corrects the runtime series coefficient from the rounded0.266 ohm to0.2657691535949708 ohm; the captured voltage is24.4 V. All21 trial decks, outputs and ngspice42 versions are revalidated by the audit. Source values, class defaults and legacy expectations remain unchanged. The first calibration invocation lacked ngspice in that process PATH and was not counted as a run; the successful invocation used the known installed directory. Static fitting does not validate pulse survival or authorize600 W continuous dissipation.

## D033 — Continue independent Stage4 work

Stage3 acceptance stays blocked at checkpoint019:45 bindings,58/63 limited probes pass,57 entries unbound. The human repair policy permits independent later-stage work after parked failures. Stage4 depends on the verified audit foundation; no failed acceptance is promoted. Protected main stays unchanged.

## D034 — Package-specific sources and source locators

The P89LPC935FA PLCC28 map is re-derived from primary Figure4,page6: VSS7,VDD21,RESET6,pin1P2.0. The spec had the HVQFN numbering; preserve its bytes and record this scoped correction. PDI1394P23EC provides an explicit preliminary BGA64 reference. Preserve ball names through view transforms; its bottom drawing requires mirror-X and90-degree counterclockwise rotation to canonical top view. AMD's manufacturer CSV supplies all256 Artix7 ball functions with an exact archive member and SHA-256; the research schema now accepts an explicit non-paginated locator instead of inventing a page number. This is pinout data,not a vendor simulation model. WLCSP and MCU body mismatches prevent automatic physical binding. AB/ABL through-hole crystals replace the incorrectly associated SMD ABLS reference,while unsourced motional parameters remain assumptions. No source status or historical audit verdict is upgraded.

## D035 — Frequency pin conventions and connector rating scope

ABM8/10/11 source top views place pin1 bottom-left. With the existing library axes, map manufacturer1/2/3/4 to library2/3/4/1, so the two grounded case pads cannot become crystal terminals. Keep the binding blocked until its physical mapping/model is validated. SiT8008 OE and ST differ; the source itself has an OE-disabled-state discrepancy between pages1/2,retained. The SAW sheet's10dBm/10V rows have no explicit maximum qualifier,so do not invent one. Connector withstand-test voltages do not become working voltages. Harwin mating endurance and JST current/wire/contact-temperature conditions remain reference-specific. Phoenix current depends on conductor and derating; its header400V and plug630V II/2 entries limit the pair to400V. Phoenix explicitly prohibits live mating. Unarchived Molex web text is not promoted to a content-hashed source; missing critical pin/rating data remains blocked. No electrical status upgrade or protocol simulation is claimed.


## D036 — 2026-10-05: OHM-163..180 connector source scope

Primary manufacturer archives now cover the final18 entries. The PJ-102A exact schematic has a sleeve switch (2–3 unplugged), not switch-to-tip; retain the source truth and test it, but do not enable an unvalidated physical binding. U.FL 10mA is a resistance-test condition, not rated current. XT30PW-M is 15A rated/30A instantaneous with no duration. XT60PW-M legacy V1.2 gives45A/500V/1000 uses while the M30 catalogue gives35A with delta<85C/500V withstand/100 uses and product page gives80V rated/1.2mOhm. These are unresolved variants: keep the original conservative30A assumption,80V working ceiling and1.2mOhm for review only, with simulation blocked pending exact variant/polarity/thermal evidence. Do not transfer cable AWG conditions to PCB variants or infer safe hot mating. The SameSky PJ102A24V and audio12V rows are typical, not maximum. FH12 all-contact current is derated70% to0.35A. Alternate HDMI/audio/SD/microSD sources remain explicitly separate from default footprints. AdamTech exact RJ11 RevD has125VAC/35mOhm and manufacturer contact numbers1..4, not six-position housing numbers2..5. RF characteristic impedance is not a shunt resistor; dummy-load power does not rate an SMA jack. Source status and numerical benchmark contracts remain unchanged. Missing primary ratings/maps block executable binding; USB/HDMI/SD protocol behavior remains not simulable.

## D037 — Independent Stage4 corrections and IC implementation

Use STM32 CIO5pF only as typical, not a capacitance ceiling; correct all three family records. Keep crystal physical-axis permutations as unvalidated assumptions until both sides are proven. Preserve AST3TQ53 header/drawing dimensions as a conflict and select the actual drawing envelope. Restrict the Artix reference field to source-established device/package until the full ordering code is sourced. These are evidence corrections, not electrical upgrades. The first ten IC bindings explicitly select a researched reference and preserve authored approximation parameters; parser pagination and numeric nodeset emission fixes change no analytical tolerance.

## D038 — Stage4 final bindings and review limits

The third independent sample found omitted conditions on HC capacitance, TPS7A8001 and Phoenix data; corrected all affected siblings. All three samples remain failed historical evidence. Added 4N35 with its unmodeled base explicitly isolated, three HC245 packages with both directions and output disable tested, two further HC595 packages, and the SiT8008 OE-tied-high reference. Enforce model ground and connection restrictions rather than permitting unsupported behavior. Manufacturer SiT8008 top-view pins1/2/3/4 map to library2/3/4/1 with a hashed derivation; its0.90mm source body differs from the1.8mm library default. This named reference does not verify physical equivalence. Frequency measurement uses full-precision native ngspice output and interpolated crossings, retaining the locked1Hz comparison tolerance. No ratings, source statuses, legacy bench files or expectations were changed. Missing reference motional data and switch-node versus averaged-output topology remain explicit blockers rather than substituted models.

## D039 — Reference-scoped ratings and bounded failure responses

Rating checks use compiled primary-source limits and actual terminal observations. Preserve each original class expression and failure response verbatim; unrelated reference literals, missing mounting context, transient peak/RMS/energy, and nonquantitative triggers remain unknown. A global25C SPICE temperature is not proof of a board thermal condition. Negative terminal power from an approximate active model cannot establish heat. Current probes are optional zero-volt series sources; existing calibration decks keep their original identities. Nodesets remain attached to physical nets. The explicit fixed-resistor overvoltage rule may request an open-circuit rerun using the class1G-ohm approximation, while 'several seconds' is not converted into an invented damage duration. Original violations and observations remain visible after the fault rerun. Four ngspice42 checks cover normal/overvoltage/modeled-open/unknown-context results. All source statuses and locked tolerances remain unchanged.

## D041 — 2026-10-05: Human-approved bench deck re-pin REPIN-001

Jaden approved the re-pin in session ("yes apply locally and continue") after reading BENCH_REPIN_PROPOSAL.md. 105 locked decks are replaced with the v2 decks, which print each locked quantity once as a named scalar. Only `netlist_sha256` moves, through docs/behavior/BENCH_REPINS.json; every locked expected value, tolerance, measure label and file path is unchanged, and the audit now refuses any re-pin row that carries anything else or does not start from the current locked hash. Each locked label is bound to one v2 scalar (scale 1) in measurement_bindings.json, with its source line. Five v2 decks printed a bound scalar twice (meas plus print), which the audit correctly treats as ambiguous; the duplicate print token was removed, circuit unchanged. Shared libraries differ only in comments and were not replaced. Result: 171 of 205 canonical benches pass in an ngspice 42 run through the product adapter (was 73). The 34 still failing are unchanged in status and need human decisions: 7 bare-number tolerances read as absolute units (the authors meant fractions; switching would loosen), 4 locked values the v2 analysis disputes by more than 2%, and 23 locked values written as text that need explicit, reviewed parsers. No status upgrade follows from this re-pin alone.
