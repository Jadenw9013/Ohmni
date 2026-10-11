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

## D040 — Truthful reference UI and selection identity

The behavior panel runs the generated, scoped reference circuit only. It exposes all180 entries, disables118 unbound entries with their recorded reasons, and preserves unknown ratings and violations. Two browser cases use real ngspice42; transport-error and cancellation checks are explicitly synthetic. Removed the universal marking override that rejected resistor geometry and left the previous selected model visible; no dimensions or electrical parameters changed. Full corpus acceptance remains blocked.

## D041 — 2026-10-05: Human-approved bench deck re-pin REPIN-001

Jaden approved the re-pin in session ("yes apply locally and continue") after reading BENCH_REPIN_PROPOSAL.md. 105 locked decks are replaced with the v2 decks, which print each locked quantity once as a named scalar. Only `netlist_sha256` moves, through docs/behavior/BENCH_REPINS.json; every locked expected value, tolerance, measure label and file path is unchanged, and the audit now refuses any re-pin row that carries anything else or does not start from the current locked hash. Each locked label is bound to one v2 scalar (scale 1) in measurement_bindings.json, with its source line. Five v2 decks printed a bound scalar twice (meas plus print), which the audit correctly treats as ambiguous; the duplicate print token was removed, circuit unchanged. Shared libraries differ only in comments and were not replaced. Result: 171 of 205 canonical benches pass in an ngspice 42 run through the product adapter (was 73). The 34 still failing are unchanged in status and need human decisions: 7 bare-number tolerances read as absolute units (the authors meant fractions; switching would loosen), 4 locked values the v2 analysis disputes by more than 2%, and 23 locked values written as text that need explicit, reviewed parsers. No status upgrade follows from this re-pin alone.

## D042 — 2026-10-05: Contract corrections, additions and the 25 C diode fix (CORRECTION-001/002, REPIN-002/003, ADDITION-001)

Jaden approved correcting the locked contracts that could not pass ("Correct them"). The bench ledger gained two entry types, each needing a recorded human approval: corrections, which must quote the exact locked expected list they replace and whose new items must all be numeric with a basis, and additions, which add bench identities without replacing any. Class records and the spec keep their original expectations; model/runtime code that parses the original text reads the uncorrected view. CORRECTION-001 covers 34 benches: 21 text values rewritten numerically with every stated number kept (lists split, bands and windows as centre plus half-width, qualitative outcomes as derived flags), 5 bare-fraction tolerances read as the percentages the authors meant (this widens the absolute window and is listed as a loosening), and 8 values re-derived with written derivations (CT open-secondary first spike, flyback values from design quantities rather than measured ones, flyback B3b asserted as its own stated intent, 1N4148 trr including the depletion tail, LDO mV unit error, buck efficiency window, BJT runaway observable). CORRECTION-002 and REPIN-003 fix BEH-DIO-PN/B1: its deck set no temperature, so ngspice ran at 27 C and the locked 0.73039 V is the 27 C value; the deck now states 25 C and the value is the 25 C derivation 0.725559 V, which the product runtime matches for OHM-056, 059, 061, 062 and 063 (the five Stage 3 temperature failures). ADDITION-001 adds contracts for the 20 authored decks that had none, the light-load buck deck split from BEH-REG-BUCK-DCS/B2, and the harness smoke deck. Eight decks printed a checked scalar twice; the duplicate print token was removed. Result: 227/227 canonical benches and all runtime receipts pass in ngspice 42 through the product adapter. Two Codex tests that encoded the old DIO-PN/B1 data were retargeted with their intent unchanged.

## D043 — 2026-10-05: Verifier round 4 (human-authorized) and record corrections

Jaden authorized a fourth verification round after the three-attempt ceiling ("Yes, new round"). New random seeds sampled 11 stage2 and 8 stage4 entries; fresh-context reviewers read only each gapfill, generated record and the archived source bytes, with no web access. 8 of 19 entries had mismatches. Fixed against the archived documents and re-checked: OHM-060 maximum forward voltage 1.1 V -> 1.2 V (doc 88546 p2: 1.2 V is the GL41K-Y value), OHM-012 tcr_max 300 -> 600 ppm/C with the 1.0-ohm split stated, OHM-079 body height marked as a drawing maximum, OHM-175 edition date Sep. 2024. Not fixed, because they need primary documents that must be fetched on the owner's machine: OHM-074 and OHM-082 (Farnell and RS distributor copies), OHM-164 (Farnell copies plus an undated presentation) and OHM-166 (third-party mirror; "20 MOHM" unit reading). The round-4 reports keep every mismatch as found, so AUD-VERIFY-001 still fails; a clean round needs those sources replaced and a further fresh sample. The 1-in-2.4 mismatch rate in this sample suggests similar issues exist in unsampled entries.

## D044 — 2026-10-05: Source supersessions and local artifact bindings (approved)

Jaden approved the source-supersession patch ("ok apply"). The protected spec cites 72 URLs that cannot be archived and 20 local paths from the authoring workspace. docs/behavior/SOURCE_BINDINGS.json now (a) supersedes 30 unarchivable URLs with primary documents that research agents opened and checked (16 support the claim, 13 partly, 1 contradicts the spec; every non-full one carries a note), (b) binds the 20 local references to hash-locked repository files, and (c) will map the MCP1700 citation to its archived data sheet once downloaded. A superseded URL counts only when its replacement has its own successful archived fetch. Browser downloads by a named person are accepted with that provenance and no invented HTTP status. Fetch receipts prove bytes, not support; the conflicts (for example WE 750311691 1500 VAC vs the spec's 2.5 kV, Talema AS-103 200 mH/5 ohm, Phoenix MKDS 17.5 A/400 V, Molex KK Rev G 500 V) are recorded in the supersession notes for record review. Remaining: 63 URLs must be fetched on the owner's Windows machine and up to 8 PDFs saved from a browser.

## D045 — 2026-10-06: Primary-source sweep of distributor-only evidence

The round-4 verifier found records resting only on distributor or mirror copies, so every gapfill field was swept. 216 fields in 23 entries cited only Farnell, RS, DigiKey, Avnet, Conrad, Adafruit, SparkFun, datasheet4u or b-cdn copies. Research agents found manufacturer documents for 21 of the 25 cited copies and checked each claim by WebFetch: 109 supported, 23 partly, 81 not found in the primary extract, 3 contradicted. 132 supported or partly supported fields now cite the manufacturer document first (the distributor copy is kept as a secondary citation; partial support is noted in each gapfill). The 21 new documents are declared with status primary_source_opened_via_webfetch_not_yet_archived and must be archived on the owner's machine before the source audit passes. Rule applied to conflicts: the current manufacturer document governs, with the superseded value recorded. OHM-093 PN2222A maximum collector current 600 mA (ON Rev5, 2010) -> 1.0 A (current onsemi data sheet); OHM-097 BD139 ungraded hFE max 160 (Fairchild RevA, 2000) -> 250 (onsemi Rev 3), so the BD139 proxy model BF is now sqrt(40*250) = 100; OHM-164 presentation contact resistance 10 milliohm (the allowed change after test) -> 30 milliohm initial. No manufacturer-hosted document was found for OHM-084 (WS2812B original revision), OHM-136 (PDI1394P23, obsolete), OHM-090 (Kingbright TC23-11CGKWA, site unreachable) and OHM-041 (Murata LQM18DN6R8M70, blocked); those stay distributor-backed and are listed as open. The 13 documents archived from the owner's Windows fetch were re-checked from their bytes; their spec disagreements (Cree XP-E2 Rev 25B, Talema AS-103, WE 750311691 isolation 1500 VAC, Hirose DM3 contact resistance, Epson FC-135 drive level) were already reflected in the records by earlier gapfills or concern bibliography notes only.

## D046 — 2026-10-06: Coverage derives "simulable" from current evidence; Stage 7 report

No code path ever promoted a model from "implemented" to "audited", so COVERAGE.md reported 0 simulable entries. The coverage generator now derives it on every run: an entry is simulable only if its model is implemented, every runtime receipt for it passes now, all its class benches pass, and its record disposition is simulable. Result: 42 of 180 entries are audited simulable. 20 more have passing reference-scoped runtime models (the bound reference ICs and four parts with unresolved terminal evidence) but their records stay not_simulable on their own, and are not counted. 118 entries remain blocked with recorded reasons (38 generic packages without a bound reference part, 16 with unresolved electrical or terminal evidence, 3 protocol/firmware-only, the rest without an implemented model). Browser-saved sources are recorded with tools/behavior_audit/ingest_manual.py; the 75 documents still missing are listed in docs/behavior/source_downloads/BROWSER_DOWNLOADS.md. Audit at this commit: 10 of 13 checks pass; AUD-SOURCE-001 needs those downloads, AUD-VERIFY-001 needs a fresh verifier round after them, and AUD-PROTECT-001 runs only in the owner's worktree.

## D047 — 2026-10-06: Blocker research for the 18 research_required entries

A research round looked for primary evidence that would unblock each research_required entry (findings in docs/behavior/source_downloads/research_round5_blockers.json). None was fully resolved, because the manufacturers do not publish the missing data: Taiwan Alpha gives no power rating for RV16AF (OHM-020; only a distributor lists one); Kingbright does not state whether display PD/IF apply per segment or per package (OHM-087..089) and publishes no thermal resistance for OHM-075/076; no maker document exists for the 32 mm 8x8 matrix (OHM-090) or the PDI1394P23 package (OHM-136); Infineon has no IRLR8721 model card (OHM-100); Wurth gives only a 1500 VAC test voltage, not a working voltage, for 750311691 (OHM-053). Partial findings (WP113HDT Tj 125 C, IRFP260N avalanche ratings and SPICE model, IRLR8721 Foster thermal network, Murata LQM21PH as a fully sourced rebind candidate) are recorded but not applied, since applying them needs archived copies and, for the rebinds, a change of reference part. These entries stay research_required with the reason documented; this is the honest end state for unpublished data. The stale runtime blockers on OHM-062 and OHM-063 (the 27 C vs 25 C diode bench) were resolved by CORRECTION-002 and their runtime receipts pass; their research_required status comes from the protected spec and is unchanged.

## D048 — 2026-10-08: Per-part datasheet fits for the 42 and source-bound probes for own-curve bindings

PR #3 (merged by Jaden) fitted model terms for the 42 audited-simulable entries to each part's own archived datasheet (98 fields; records in docs/behavior/polish/fits_*.json) and bound them through recipe `model_facts`, which follow the critical-fact sourcing rules but do not lower rating confidence. Wrong values in use were corrected (S2M on S1M values, BAT42W on BAT54 values, 1N4148-family TT above the datasheet trr bound, LEDs on a shared card that missed their curves). Four bindings were held back because their runtime probes compared the model to the shared class card's locked analytic point: OHM-056, 059, 061 (1N4148 family) and OHM-073 (TLDR4400). Jaden approved changing those probes in session ("do both run multiple agents", answering the request to "approve the probe change"). A binding whose IS, N and RS come from the part's own curve is now checked against that part's sourced maximum forward voltage at its source test current, the same source-bound interval already used for OHM-057, 058, 064, 065, the Schottky entries and the other LEDs. The class B1 analytic contract and every locked bench value are unchanged; entries still on the shared card keep the analytic comparison.

## D049 — 2026-10-08: Unblocking the not-yet-audited entries (30 of 81 bound)

Jaden asked for the 81 "not yet audited" entries to be worked with multiple agents ("do both run multiple agents"). Each had a specific recorded model blocker, not only a missing test run. Six research agents read the archived sources per entry (records in docs/behavior/unblock81/research_*.json). 30 entries were bound: their blockers close for an explicitly named reference part, with sourced ratings and a pin map read from the part's own drawing; the former blocker and its resolution move to the entry's open items. Explicit alternates follow the S2M/BAT42W precedent and leave the default unbound (OHM-024 TDK, 094 BC817, 096 BCP56, 101 IRFZ44NS, 167/171/172/179/180 connectors). Two documents were archived for this from Jaden's Chrome (Murata JELF243B-0086 for OHM-041, Kingbright APT1608SURCK for OHM-078, a rebind from VLMS1300, which publishes no junction or thermal data). Classes without a runtime check gained one shared DC path check (tools/behavior_audit/runtime_benches.py PATH_PROBES): a sourced current through one bound path must reproduce the sourced path resistance (0.1% numerical tolerance, or the sourced tolerance band for the potentiometer). It is a binding check of contact, winding, leakage or track resistance and claims nothing about frequency response, heating, isolation or protocols. Connector models expose the mating-side contacts (M/W/C roles) as model terminals; they are reference-circuit terminals, not PCB pads. Result: 72 of 180 entries audited simulable (was 42); 124/124 runtime receipts pass. Not bound: 4 resolvable entries that need new probe kinds (OHM-039 mica and 040 EDLC need a transient charge check, 070 BAV99 needs a dual-diode rating guard, 085 XP-E2 needs an 85 C reference) and 47 entries that stay blocked for documented reasons (crystal motional parameters unpublished, no exact MLCC/aluminium parts archived, unpublished connector voltages or pin numbering, mains or safety scope).

## D050 — 2026-10-08: The last four resolvable entries get their own checks

Jaden asked for the four resolvable entries left out of D049 ("go"). No new source data was needed; each needed a check that fits how its part behaves. OHM-039 (CDE CD15 100 pF mica) and OHM-040 (KYOCERA AVX SCCS20B505SRB 5 F EDLC) are checked in the time domain (tools/behavior_audit/runtime_benches.py TRAN_PROBES): a current ramp from zero charges the bound capacitance and the node voltage at a fixed time must match I*ESR + I*(t - ramp/2)/C within the tolerance of the class's own locked bench (0.1% from BEH-CAP-MICA/B1, 1% from BEH-CAP-EDLC/B3; the probe refuses to run if those tolerances change). The EDLC test current is the source's 4*C*VR mA measurement rule; the mica uses 10 uA. Neither check claims Q, RF loss, ESR frequency dependence, leakage or any rating. OHM-070 (Nexperia BAV99) is checked one junction at a time at the source VF test current (variants d1 and d2, the third terminal idle). Its role map keeps the sourced pin 3 label K1/A2 and adds a DERIVED netlist-name copy (K1A2), because role names become rating-expression names. A new rating branch applies the double-loaded current limit whenever both junctions conduct, otherwise the single-loaded limit, and leaves total power and junction temperature unknown with both conducting, since the source states those for one diode loaded only. OHM-085 (Cree XP-E2) is checked at its source test current with the diode instance held at the 85 C junction temperature at which the datasheet publishes VF; a BEH-LED-POWER rating branch checks reverse voltage, forward current and Tsp + Rth(j-sp)*P <= Tj max from the stated solder-point temperature (treating all electrical power as heat, which is conservative), and stays unknown without one. Former blockers moved to each entry's open items. Result: 76 of 180 entries audited simulable.

## D051 — 2026-10-09: Rating checks for the classes bound in D049 and D050

Jaden approved this as the next step ("go"). The 34 parts bound since PR #4 had sourced limits that no rating check read. src/ohmni/behavior/ratings.py now checks them on every simulated operating point, using only the facts already bound in each recipe. Capacitors: ceramic and mica voltage across the terminals against the DC rating; tantalum forward voltage against the 85 C rating (unknown above 85 C, where the category voltage is not bound), the manufacturer's MnO2 application voltage as advisory only (above it is reported unknown with the reason, not a violation, because it is a recommendation for low-impedance circuits), and reverse bias against the temperature-selected transient limit, which can only fail a design because no continuous reverse rating exists; EDLC voltage against the 65 C or 85 C rating chosen by ambient (unknown between the two without an ambient) and any reverse bias as a violation. Connectors: every terminal's current against the contact rating, the largest voltage between any two terminals against the insulation or working voltage, and ambient against the stated range. Limits that can prove a violation but not a pass report unknown when met: the OHM-171 and OHM-172 voltages from a typical column, the Phoenix nominal current above an unbound derating knee, and the JST contact temperature, which includes self-heating the model does not compute. Common-mode chokes check each winding's current and, where sourced, line voltage; the signal transformer checks primary DC unbalance; the potentiometer checks track power with the resistor derating rule, track voltage and wiper voltage. Ripple current, ESR heating, peak current and transformer output power need AC or transient analysis and are not checked at a DC point. No recipe, receipt or bench changed.

## D052 — 2026-10-09: Unmated connector contacts, the mains choke voltage, and the seven dead sources

Jaden asked for the remaining policy items to be handled by Claude's engineering judgment, as close to real-world practice as possible ("for 1 and 2 use your best judgment and try to make it as close to how it works in real life"). These are Claude's choices under that delegation, not owner approvals, and are open to his review in the pull request. Connectors: a recipe may now list open_mating_roles, the cable, plug or card side contacts that are not PCB pads. A design may leave them unconnected; each then gets its own private node, as an unmated contact would, so a connector placed on a board with only its pads wired now simulates. Numbered package pins can never be open mating roles and every pad must still be connected. OHM-051 (Wurth 744821240 mains choke) now binds its sourced 250 V AC rated voltage, checked as a line voltage limit on the DC operating point (conservative, since 250 V rms is 354 V peak); it remains a DC-resistance model with no safety, insulation or mains-frequency claim. Not changed here: the OHM-171/172 typical-column voltages still report unknown when met (relaxing that guard was not applied without an explicit owner decision), and OHM-066 stays blocked because simulating the sourced SS34 as a Schottky needs either a class change in the protected spec or a new reference-function rule. Sources: all seven URLs missing from the fetch ledger were retried from Jaden's Chrome on 2026-10-09 and returned 404 (KEMET F3054, KEMET 2004 CARTS paper, WIMA 2025 catalogue, chipdip mirror, ubbcluj mirror), 503 (Microchip online docs) or failed TLS (AMS ds1117); WIMA's current SMD-PET and SMD-PPS sheets did not download. Superseding them needs replacement documents archived and an owner-approved SOURCE_BINDINGS entry, so AUD-SOURCE-001 stays failed.

## D053 — 2026-10-09: Owner decisions on typical-column connector voltages and the OHM-066 class

Jaden approved both in session ("all 3", answering a numbered request whose items were the .ai ledger update, treating the OHM-171/172 voltages as ratings, and changing OHM-066's class so it simulates as a Schottky). OHM-171 (Same Sky SJ1-3535NG) and OHM-172 (PJ-102A) print their rated voltage in a "typ" column; the contact-to-contact voltage check now uses it as the rating, so a design within it passes instead of reporting unknown. OHM-066 (SMC diode): the master table projects only BEH-DIO-PN, but the spec's own section heading for the entry lists BEH-DIO-PN, BEH-DIO-SCHOTTKY and BEH-DIO-TVS, and its only sourced reference is the Vishay SS34 Schottky. A new owner-gated resolution kind, class_addition (OHM-066-SCHOTTKY-CLASS in STAGE1_MISMATCH_RESOLUTIONS.json, carrying the approval quote), appends BEH-DIO-SCHOTTKY after the master-table classes; the generator refuses one without a recorded approval, the master-table consistency check still runs on the table as written, and the preservation test now allows only approved additions after the unchanged master classes. OHM-066 is bound to the SS34 with IS 2.34e-6 A, N 1.045, RS 0.0138 ohm fitted to the datasheet's 25 C typical forward curve (seven read points, rms 4.3 mV, low confidence), CJO 1 nF read from the capacitance plot and BV the 40 V rated blocking voltage; its runtime check gives 0.419 V at the sourced 3 A test current against the 0.5 V maximum. Leakage and its heating are not modeled. The ledger update itself was refused by the session's safety classifier even with the approval and was not applied. Result: 77 of 180 entries audited simulable.

## D054 — 2026-10-09: Transient rating checks and Schottky leakage runaway

Jaden approved this as the next step ("go"). Until now every rating check used a single operating point, so a waveform whose average was safe passed even when its peaks or RMS were not. A transient run now prints every terminal voltage and probe current of each part (after the requested display signals, which remain the only curves returned to the UI) and the rating step reads them at full resolution. Each part gets its operating-point checks evaluated on the time-averaged values, with power replaced by the true average of instantaneous power and the rows labelled "(time average)", plus checks a single point cannot express: peak voltage for ceramic, mica, tantalum and EDLC capacitors, the tantalum transient reverse-voltage limit chosen by ambient (now a real check, since the limit is defined for transients), tantalum ripple current against the 100 kHz rating (it can prove a violation below 100 kHz and is unknown above, because the frequency multiplier is not bound), EDLC peak current, inductor peak current against saturation and RMS against heating, choke winding RMS, connector contact RMS, resistor and potentiometer peak voltage, IC peak supply against the absolute maximum, diode peak reverse voltage and average forward current, and comparisons against surge (IFSM, 8.3 ms half-sine) and TVS pulse (IPP, 10/1000 us) ratings that can only prove a violation because pulse shape is not compared. Authored failure triggers stay operating-point only. Schottky leakage self-heating: with the two sourced leakage maxima (25 C and 100 C) and their test voltage, IR(T) = IR25*exp(k(T-25)), using the test-voltage leakage below that voltage (conservative) and linear scaling above it; Tj = Tamb + Rth*(P + VR*IR(Tj)) is solved by iteration and a part that does not settle below Tj max is a violation. OHM-066 (SS34) and OHM-067 (BAT42W) gained the leakage facts and their test voltages from their data sheets, OHM-066 its 100 A surge rating, and both, plus the four tantalum parts, now support transient analysis (the tantalum card has no ESR, so ESR heating is not modeled). Example: an SS34 at 40 V reverse settles at about 26 C junction in 25 C air but runs away at 100 C ambient.

## D055 — 2026-10-10: Review findings CBH-R01 to R04, the seven unarchivable sources, and the protection baseline

Jaden delegated three open decisions to Claude ("the repo is public and will be shared for the hackathon, you decide whats best for all 3 questions"). These are Claude's choices under that delegation, recorded here for his review; they are not individually quoted owner approvals. The independent review (PR #12) is answered as follows. CBH-R03: every fitted forward model (13 diodes and LEDs, plus the two RGB dies) now carries its datasheet read points as a structured gapfill field (forward_curve_read_points, taken from the fit evidence already on record) and the runtime check replays the model at three of them spanning the plotted range, each within the datasheet-read uncertainty (5% or 15 mV for vector reads, 8% or 25 mV for plot reads), in addition to the maximum-VF bound; an adversarial test shows a model that outputs ~0 V still passes the bound alone and fails every replay, and coverage follows all receipts. CBH-R02: a class_addition that changes electrical truth is now authorized only by its own file under docs/behavior/approvals/, which carries the sha256 fingerprint of the resolution payload, the human owner, the date and the quoted decision; the generator refuses a mismatch, a missing record or the old presence-only approved_by fields, and tests cover the edited payload, the edited approval, the dropped approval and a forged resolution. CBH-R04: the eight connector limitations that said the mating-terminal schema was missing now describe open_mating_roles. CBH-R01: the repository is public and the archive holds copyrighted datasheets, so the bytes are not published; instead `rebuild-sources` re-downloads every successful ledger URL and verifies it against the recorded hash, docs/behavior/SOURCE_ARCHIVE.md records the policy, and the complete archive (383 documents) was handed to Jaden as a private bundle with its sha256. Sources: six of the seven unarchivable URLs are superseded by manufacturer-hosted documents found, downloaded and claim-checked on Jaden's PC (KEMET C1115 MIL-PRF-123 for the F3054 catalogue, full; KEMET T52X/T530 plus T491 and T2079 for the 2004 CARTS derating paper, partial because the surge failure-rate figures survive nowhere; WIMA 2026 catalogue plus the SMD-PPS and SMD-PET sheets, full; the SAMA5D29 data sheet DS60001764C table 67-19 for the Microchip online page, full, min/max rather than typical; Murata JGC40-5039 for the chipdip mirror, full; the AMS1117 sheet from AMS's own server over http because its TLS fails, full, with two spec conflicts noted). The seventh, Vishay TLHB5800, has no manufacturer copy left and no archive snapshot; it is recorded as withdrawn by the manufacturer, which the audit accepts only because no gapfill fact or runtime recipe cites it (no simulable binding depends on the blue 5 mm card). AUD-SOURCE-001 now passes: 363/364 archived, 1 withdrawn. Protection baseline: a `rebaseline` command re-records the main, remote and production-checkout snapshot as an explicit logged event with a reason and approver, refuses if the protected spec files differ from the old baseline, keeps baseline_commit (the bench-corpus anchor) unchanged, and appends the old and new main refs here; it must be run in the owner's checkout, so the refresh itself is handed to the local session on Jaden's PC.


## Baseline refresh — 2026-10-10

main ab1a8e48df406ef031894aad59bdd37f560d1bce -> 42cd343e1958849bbed3ab39d7cec91aaa99a91e. Reason: Owner-approved merges of PRs #2 through the baseline PR itself moved main; protected spec unchanged. Approved by: Jaden Wong (owner), delegated 2026-10-10: 'you decide whats best for all 3 questions'. Protected spec files unchanged.

## D056 — 2026-10-10: Design-level simulation of a user's own circuit

Jaden authorized the overnight run to build design-level simulation (HANDOFF "What to build next" item 1) and to merge it after an independent proxy review. The overnight Codex run had not landed CS-T07 to CS-T11 (main ends at CS-T06, PR #27), so nothing here was already built; CS-T09 and CS-T10 stay APPROVED and not started, because their acceptance criteria (vendor-model harness, deck restrictions, SOT-223 tab mapping) are broader than this and depend on CS-T07 and CS-T08. What shipped: ComponentBehaviorService.run_design and POST /api/behavior/design/run compile a caller's CircuitIR through the existing compile_circuit with current probes on every part and run the existing rating step on the result. Choices made: (1) only audited simulable entries run, by the same rule the coverage count uses; a reference-only or documented entry stops the whole design with that part named, rather than running part of a circuit or substituting a model; (2) a catalog LED whose declared colour differs from the bound reference part is refused (GENERIC_LED_GREEN is bound to OHM-078, whose reference became the red Kingbright APT1608SURCK in D049; its catalog package name "0603" also matches no recipe package "0603 LED", so today it is refused either way, and the binding itself is queued for the owner); (3) the design verdict is within limits only when every part is, never by majority; (4) ngspice 42 was measured to keep the first of two same-named .model cards silently (two LEDs on different cards both solved to 2.080 V), so compile_circuit now gives each part its own copy of any model or subcircuit name that two parts define and refuses differing definitions of a name inside hash-locked assets. No current pair of bound recipes collides with different parameters (every fitted card is already named per part), so this is a guard; all 97 reference netlists reproduce their recorded hashes unchanged, and no recipe, receipt, bench or record changed. Not done: a UI for design runs, AC analysis, source-capability checks and board-level heating.

## D057 — 2026-10-10: AC analysis and the exact ripple checks

Overnight item 2, under Jaden's standing authorization for this run and the proxy review. Everything was DC or transient; filters, decoupling and the tantalum ripple ratings (stated at 100 kHz, 25 C, RMS) need a frequency-domain path. Choices: (1) the AC excitation amplitude is defined as the sine's RMS value, so every phasor is RMS and peak = |DC| + sqrt(2)*|AC|, RMS = sqrt(DC^2 + |AC|^2) for a sine on a bias; (2) a recipe supports AC when it supports the operating point, because ngspice's AC solve is the linearization of the same model around that point, so no recipe changed; (3) linearity is decided from the compiled netlist, not the class name, because the BEH-MAG-INDUCTOR saturation card (ind_sat.lib) makes inductance a function of its own current; in a nonlinear circuit every AC-derived row is reported unknown with the computed result in its reason, and operating-point rows are unaffected; (4) the KEMET T491 ripple and ESR heating checks are exact only at the conditions the ratings are stated for (100 kHz and an ambient at or below 25 C). The T491 data sheet (archived, KEM_T2005_T491.pdf p.14, ledger sha256 c3c5bb70...) states I(max) = sqrt(P max / R) with R the ESR at the specified frequency, and its table values satisfy this (case A: sqrt(0.075/3) = 158 mA). It also gives temperature compensation multipliers of 1.00 / 0.90 / 0.40 at 25 / 85 / 125 C. Those multipliers are not bound in this change: the table title applies them to ripple current while the text applies them to P max, and binding them is a gapfill change with its own review. So above 25 C the check stays unknown. Below 100 kHz the check can prove a violation only (as in D054); above it, it stays unknown. The ESR heating row computes I^2 * maximum ESR from the sourced value, since the tantalum card itself has no ESR. Also fixed: the failure-approximation rerun now keeps the caller's transient step, stop time and observed nets (it used the defaults). No recipe, receipt, bench or record changed.

## D058 — 2026-10-10: ESR on the KEMET T491 tantalum cards and an impedance receipt

Overnight item 3 (capacitor ESR), under Jaden's standing authorization for this run and the proxy review. Of the capacitor families the handoff names, only the four KEMET T491 tantalum entries (OHM-033..036) are simulable and have a sourced ESR. Ceramic: the one simulable part (OHM-024, TDK) has a 10% maximum dissipation factor whose measurement frequency the source page does not state, so no ESR can be derived. Film: no film entry is simulable (OHM-037 is unbound, OHM-038 is a mains safety part). Choices: (1) the tantalum recipes now bind Resr -> (Cb || Rlk), the class card's own topology (spec lines 1611-1618; Lesl still dropped because ESL is unsourced), with Resr = maximum_esr, the T491 table's 100 kHz, 25 C maximum. PR #3/D048 had dropped Resr because a maximum is not a fitted nominal; it is bound now as a declared worst-case bound, and the limitation says so. It overstates impedance, ripple voltage and ESR loss near 100 kHz. In parallel with other capacitors it shifts ripple current toward them, so their current checks are not conservative. That trade-off is written into each recipe's limitations. (2) A new runtime receipt per part (runtime-bench-results/OHM-03x-ac.json, product adapter, ngspice 42) injects 1 mA RMS at 100 kHz and requires the solved impedance to equal ESR + (Rleak || 1/(jwC)) computed from the part's own sourced facts, within 1e-4 relative for both the real and imaginary parts (observed OHM-033: 3.0000 - j0.15915 ohm). The existing DC leakage receipts still pass (the 3 ohm series term is 2e-6 of the 1.6 Mohm path). Reference circuits and the four DC receipts were regenerated; no gapfill, record, bench or class changed. The AC rating rows of D057 already use the sourced maximum ESR for ESR heating; the model ESR now also appears in transient and AC waveforms.

## D059 — 2026-10-10: Blocked-entry research round; OHM-037 bound to WIMA MKS 4

Overnight item 4, under Jaden's standing authorization for this run and the proxy review. Four research agents re-read the archive (382 documents, unpacked from the owner's verified bundle) for 41 blocked entries. Excluded were the 28 generic packages (owner decision), seven mains/safety entries (028, 038, 053, 054, 055, 173, 174) and seven protocol entries (084, 091, 092 at layer L3, and 164, 165, 168, 169, whose blockers name the protocol). Only archived manufacturer documents counted; nothing was downloaded. Result: one entry bound, 40 kept blocked with their reasons updated in STATE.json model_blockers (each now ends "Re-checked 2026-10-10 against the archive (D059): ..." naming what is missing and, where known, the document that would close it). Research notes are summarized in the reasons; the raw agent output was scratch and is not committed. Bound: OHM-037 (film box capacitor) to WIMA MKS4G031003F, MKS 4 metallized PET, 0.1 uF, 400 VDC/200 VAC, PCM 10 mm, 13 x 5 x 11 mm, from the WIMA 2026 catalogue archived on 2026-10-09 (pages 40 and 42). It is the only 0.1 uF row in the catalogue with the OHMNI default body at 10 mm pitch, and it is a general DC series, not a safety part. Choosing the 400 VDC grade by that body match replaces the spec's assumed 100 V peak with a sourced rating; this is an engineering choice open to review. The model is the Cb || Rlk subset of the class card, with Rlk the 3 x 10^4 Mohm minimum insulation resistance; ESR and ESL are not modeled. Its runtime check is a new BEH-CAP-FILM transient charge probe (1 mA ramp, read at 1 ms, under the 0.1% tolerance of the locked BEH-CAP-FILM/B1 bench): it observed 10.0005 V against 9.999995 V expected. Its ratings are checked by a new BEH-CAP-FILM branch: the DC rating derated 1.25 %/K above 85 C (with no declared ambient, only a voltage over the full 400 V rating can be proven, as a violation, and every lower voltage is unknown, following D060); ambient within 125 C; transient peak voltage; and, in AC runs, the catalogue's 50 Hz rule 1.4 x Urms + UDC <= Ur with 200 V rms, derated above 75 C. That rule is exact at 50 Hz; at other frequencies it can only prove a violation. Research that found bindable values but was not applied, with reasons in MORNING_DECISIONS: OHM-042, 060, 075, 076 and 100 are research_required in the protected spec, so a binding would only be reference-only; OHM-148's new Murata sheet sources its ratings and pins but not its motional C1/C0. Research also found a ledger row whose archived bytes are a "Request Rejected" page (Lite-On, OHM-083), and several records citing mirrors or distributors where a maker copy is archived; both are listed for the owner and not changed, because those gapfills belong to the verifier round. All runtime receipts were regenerated against the changed recipes. Audited simulable: 77 -> 78. Amended after the proxy review of #39: the ambient row checks both sourced limits (-55 to +125 C; it had only the upper one); AC-present peak rows derate from +75 C as the catalogue says for AC voltages; transient runs add an unknown row for the 200 V rms AC rating, its derating and pulse dV/dt, so a waveform cannot pass on its peak alone; the leakage resistor is described as the 20 C, 100 V minimum (not a worst case when hot); the +125 C 1000-hour allowance is stated. The reviewer approved choosing the 400 VDC grade by body match, with the caveat that a lower-voltage MKS 4 in a 4 x 9 x 13 mm body fits the same footprint, so the bill of materials must name MKS4G031003F.

## D060 — 2026-10-10: Proxy-review fixes for design runs (D056) and the AC path (D057)

The owner merged #30 (D057) before its proxy review finished. The retroactive review blocked it, so these fixes are the first part of overnight item 5. AC path:
- A missing operating-point value is no longer read as 0 V or 0 A: the component's AC checks report unknown.
- A class with no AC translation, or a listed class whose limits are not bound, gets an explicit unknown "AC swing" row at each frequency, so no part passes an AC run on operating-point rows alone.
- Linearity now reads continuation lines and counts POLY controlled sources and any include as nonlinear.
- Each AC point prints and checks its solved frequency, so a failed solve cannot reuse the previous plot's vectors. Duplicated values drop the point, and a run missing any requested vector fails.
- The tantalum ripple conditions (100 kHz, 25 C, RMS) are read from the record's own source scope instead of being assumed for the class. The exact ripple row also needs the thermal scope confirmed, like the ESR heating row.
- `.save` and `.meas` are refused in AC decks, the sweep point limit counts the end point, and the AC result carries an explicit limitations list (unsourced parasitics, linearization, untranslated classes).

Temperature ratings now follow their sources in every analysis:
- The KEMET T491 rated voltage applies only up to 85 C ("rated VDC at 85 C" in the record scope). The KYOCERA AVX SCC ratings are 2.7 V at 65 C and 2.3 V at 85 C (fields rated_voltage_at_65C and rated_voltage_at_85C).
- With no declared ambient, those rows can now only prove a violation. Before, they passed against the 85 C rating, which silently assumed a cool ambient; this was a D051 behaviour and is corrected in the operating-point, transient and AC branches alike.

Design runs (from the #28 review):
- A shared model name that is also a circuit or probe node is refused instead of renamed.
- An oversized design is refused before any part is resolved.
- A live test shows that a transient design beyond the rating-signal limit leaves every part unknown.

## D061 — 2026-10-10: The maximum-ESR tantalum card cannot prove a ripple pass

The owner merged #32 (D058) before its proxy review finished. The retroactive review blocked it. With the sourced maximum ESR as the card's series resistor, the simulated tantalum current is a lower bound wherever the part is voltage-driven: at the rating conditions (100 kHz, 25 C) a real part's ESR is at or below the maximum, so it carries at least the simulated current. The fixes:
- **AC runs at the rating conditions:** the exact ripple row and the ESR heating row now prove a violation but never a pass.
- **AC runs away from 100 kHz:** the real ESR can exceed the maximum there, so the ripple row is unknown in both directions.
- **Transient runs:** the ripple row is unknown with the same reason, since a simulated waveform's current bounds the real one in neither direction.
- **Correction to D058:** its limitation text had the parallel-part direction backwards. With the maximum ESR, parallel parts take more current than with a lower real ESR, so their current checks are conservative at the rating conditions; it is the tantalum's own current rows that are not.
- **Recipe wording:** the corrected limitation text ships with the next recipe change (D059), because any recipe edit restamps every runtime receipt.

The D054 test that expected a violation from 0.177 A at 10 kHz now expects unknown: with the bound ESR the simulated current does not bound the real one at 10 kHz.

Other corrections to D058:
- The impedance tolerance is |Z| x 1e-4, applied as an absolute tolerance to each of the real and imaginary parts (not 1e-4 relative to each part).
- OHM-033's leakage path is 16 V / 1.6 uA = 10 Mohm, not 1.6 Mohm.
- All 185 receipts were restamped, not only the four DC ones.

## D062 — 2026-10-11: The maximum ESR proves a ripple violation only at 25 C in a passive circuit

The owner merged #35 (D061) before its proxy review finished. The retroactive review blocked it: D061 still let the bound card prove ripple violations where its own reasoning says the bound does not hold.
- **M1:** at 100 kHz with a warm or undeclared ambient, the row was still violation-only.
- **M2:** any ambient at or below 25 C counted as "at the rating conditions", although the maximum ESR is a 25 C specification and tantalum ESR rises in the cold.

The fixes:
- **Where a violation can still be proven:** the ripple and ESR-heating rows prove a violation, never a pass, only when the ambient is declared as exactly 25 C, the frequency is the sourced 100 kHz, and the circuit is passive and linear. Passive means no E, F, G, H or B source, so Re(Zth) >= 0 and the part's current |Vth| / |Zth + ESR + Zc| falls as ESR rises. Everything else is unknown.
- **Unbound ESR:** a T491 card without the ESR element keeps the ideal-card rules.
- **Bound detection:** the bound is recognized by meaning, not only by element name. The card must bind `maximum_esr` from a 100 kHz scope and carry the series element.
- **Reason texts:** the thermal-scope reason is kept alongside the bound reason. The ESR-heating reason says it is the data sheet's I(max) = sqrt(Pmax/ESR) rating method, not a computed real dissipation.
- **Tests:** they cover cold, warm and fractional ambients, a controlled source, the meaning-based detector, and both reasons in the nonlinear case.

## D063 — 2026-10-11: A bound-ESR tantalum card proves no ripple result; D061 and D062 superseded

The proxy review of D062 blocked it again, on four points:
- **Fail-open detector:** a card whose series ESR was not recognized as the maximum fell back to the ideal-card rules, which can pass.
- **Capacitance tolerance and ESL:** the card uses nominal C, and a real part with lower C carries less current. So "a real part carries at least the simulated current" is not proven near the limit.
- **Wrong correction:** D061's correction about parallel parts was itself wrong. With a current-driven parallel tank, a higher tantalum ESR lowers a parallel inductor's current. Parallel currents are not bounded in either direction.
- **Test claims:** the stated test coverage did not match the tests.

After three blocked rounds the rule is now the simplest sound one, and it fails closed. For any tantalum card with a series element beyond Cb and Rlk (the T491 cards carry the maximum ESR, D058), the ripple and ESR-heating rows are unknown in both directions, in AC and transient runs. A card that is only Cb || Rlk keeps the D057 rules. The passive-circuit test of D062 is removed, because nothing depends on it.

Consequence: the exact 100 kHz T491 ripple check no longer yields a verdict for the bound cards. A sound way to restore it is a dual solve: run with ESR = 0 and with ESR = maximum, and require both to pass, plus a capacitance-tolerance margin. Whether to build that, or to return the T491 cards to the ideal card for ripple purposes, is queued in MORNING_DECISIONS for the owner.

D061's text about parallel parts being conservative is withdrawn. D062's violation proof is withdrawn.

## D064 — 2026-10-11: A dual solve proves a T491 ripple pass at 25 C and 100 kHz, never a violation

D063 queued a dual solve (ESR = 0 and ESR = maximum) as the sound way back to a ripple verdict for the bound T491 cards (OHM-033..036). It is built, but with a different conclusion than the one D063 sketched, because the capacitance-tolerance margin it assumed cannot be sourced:
- **No tolerance is bound.** The reference parts leave the 10 % / 20 % tolerance option unselected, so no recipe carries a capacitance tolerance.
- **A tolerance would not bound the 100 kHz capacitance.** The T491 nominal capacitance and its tolerance are stated at 120 Hz. A tantalum's effective capacitance at 100 kHz is not sourced, and neither is its ESL.
- **A margin on the current is not monotonic.** With an inductive source impedance the part's current can peak inside any capacitance range (series resonance), so scaling the current by the tolerance is not a bound.

The method used instead needs none of these values:
- **Two solves.** At each requested 100 kHz point, the AC adapter repeats the solve with the card's series ESR element replaced by a 0 V source (an exact short). It runs as its own deck, with the same markers and frequency checks, and is recorded in `ac.esr_zero` with its status, the shorted elements, the hash of the netlist it was derived from and its own netlist hash (both hashes are of the netlist before the control block is added, the same definition as the run's `netlist_sha256`). A failed or incomplete second solve stays failed and is never filled from the first. No recipe changes.
- **The port.** The two solves differ only in the part's series resistance, so they give two points of the linear port relation V = Vth - Zth*I seen by the part, from its own terminal voltage and probe current. Both are extracted: Zth = -(V1 - V0)/(I1 - I0), Vth = V1 + Zth*I1. As a consistency check, the part impedances V/I of the two solves must differ by exactly the bound maximum ESR: the complex difference minus ESRmax must be within 1e-6 of the larger impedance, so both a wrong real step and any reactive difference are refused.
- **The bound.** A real part is passive: whatever its ESR (0 to the maximum), its capacitance and its ESL at 100 kHz, its impedance Z has Re(Z) >= 0. So |I| = |Vth|/|Zth + Z| <= |Vth|/Re(Zth) whenever Re(Zth) > 0. This covers the monotonicity that D062 and D063 discussed (|I| falls as the series R rises when Re(Zth) >= 0) and also every reactance the card cannot bound. The simulated current lies under the bound by construction.
- **Numerical error.** Every solved phasor is taken to be within 1e-9 of its magnitude (printing with 15 significant digits contributes at most 5e-15; the rest is an allowance for the solver's floating-point error, which no theorem bounds, about six orders above double precision). Each port voltage carries 1e-9 x (|V_A| + |V_K|). Zth, Vth and the bound are then computed in complex disk arithmetic (centre and radius through every subtraction, product and quotient), and the bound is (|Vth| + r_Vth) / (Re(Zth) - r_Zth). So it is an upper bound for every input within that error; a quotient whose divisor disk contains zero, or an Re(Zth) - r_Zth <= 0, leaves the row unknown. This replaces a fixed inflation factor, which no guard could justify.
- **Why no violation.** There is no lower bound: with the 100 kHz capacitance and ESL unsourced, the part's reactance, and so its current, can be anything below the bound. A bound above the limit is reported unknown with the bound in the reason.

A pass is produced only when all of these hold; otherwise the row stays exactly as in D063 (unknown, with the reason the dual solve did not apply):
- the frequency is the sourced 100 kHz (relative 1e-9), and the ripple scope states 100 kHz, 25 C and RMS;
- the declared ambient is exactly 25 C, the temperature of both the ripple rating and the ESR;
- the thermal scope is confirmed (as for the ideal card);
- the circuit is linear, with no E, F, G, H or B element and no include (a conservative filter: element values are not inspected, and the bound itself needs only Re(Zth) > 0 and the real part's passivity);
- the circuit has exactly one tantalum capacitor of any card (BEH-CAP-TANT), since another one's unsourced 100 kHz impedance would change the port the first one sees;
- the card's netlist is the topology Resr -> (Cb || Rlk), checked by node: the `*_esr` resistor runs from the anode terminal (behind its 0 V probe) to an internal node that no other element touches, and the capacitor and the `*_lk` resistor both run from that node to the cathode terminal; the resistor's value equals the sourced `maximum_esr` from a 100 kHz scope;
- the second solve belongs to this compilation: the run's netlist hash and the second solve's source hash both equal the hash of this compilation's netlist, the shorted elements equal those the rating step recomputes for it, and the second solve's netlist hash equals the hash of this netlist with exactly those elements shorted (a variant with another network or excitation is refused, which the part-impedance check alone could not detect);
- the second solve ran and printed the part's values at that frequency; shorting the ESR changes its current by at least 1e-6 relative (otherwise the port is not resolved); and Re(Zth) is at least 1e-3 of |Zth| (otherwise the part's unsourced reactance decides the current and rounding would dominate).

The ESR-heating row uses the same bound in the data sheet's rating method, Ibound^2 * ESRmax <= Pmax (equivalently Ibound <= sqrt(Pmax/ESRmax)), and proves a pass only. Transient runs, other frequencies and every other case keep the D063 rule. Parallel parts' rows are unchanged; their currents are still not bounded by this card (D063).

In practice a verdict needs a source with real resistance behind the tantalum (for example a current injection into a resistive node: the live test injects 0.1 A RMS into 1 kohm || OHM-033 and proves the 158 mA rating with a 0.1 A bound). A tantalum driven from a low-impedance voltage source stays unknown, which is honest: its current there is set by the unsourced 100 kHz capacitance and ESL. The recipes' limitation text still says the rows are unknown in both directions (D063); the corrected wording ships with the next recipe change, because a recipe edit restamps every runtime receipt.

## D065 — 2026-10-11: The T491 recipe limitation states the D064 pass exception

The four T491 recipes' limitation text said the ripple and ESR-heating rows report unknown in both directions (D063). Since D064 that understated the engine. The rows stay unknown except in one case, which may report a pass: an AC run exactly at 100 kHz, with a declared 25 C ambient and confirmed thermal scope, in a linear passive circuit where this part is the only bound tantalum and its source port has real loss. The text now says this and that a violation is never proven. No rule, value or check changed; this is the "next recipe change" D064 deferred. The recipe edit restamps every runtime receipt: all 186 were rerun and pass, all 98 bound entries validate, and audited simulable stays 78.
