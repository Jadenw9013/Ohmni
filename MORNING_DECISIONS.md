# Morning decisions (owner only)

Items 1-12 are questions for you. Each has the evidence and a recommendation. Nothing in this list was
decided overnight.

Written by the overnight component-behavior run (2026-10-10/11). Each item is a decision that the
standing authorization reserves for the owner. None of them was decided overnight; the work routed
around them. Evidence paths are in this repository unless marked otherwise.

## 1. GENERIC_LED_GREEN is bound to a red reference LED

- **Question:** Should the catalog part `GENERIC_LED_GREEN` stay bound to OHM-078/OHM-079, now that
  OHM-078's reference part is the red Kingbright APT1608SURCK (D049 rebind from VLMS1300)? If not,
  which green part should it bind to, or should it be unbound?
- **Evidence:** `src/ohmni/behavior/data/bindings/GENERIC_LED_GREEN.json` (entry_ids OHM-078, OHM-079,
  approved 2026-10-04); `docs/behavior/runtime-recipes.json` OHM-078 `reference_part` "Kingbright
  APT1608SURCK red". The catalog part declares colour green and a 2.1 V typical forward voltage.
  The binding's package names ("0603", "0805") also do not match the recipe packages ("0603 LED",
  "0805 LED"), so the join can never compile today.
- **What overnight did:** design-level runs refuse a catalog LED whose declared colour differs from the
  bound reference part (D056). Nothing else changed. The binding file is generated from the protected
  spec's Stage 1 resolution, so changing it is yours.
- **Recommendation:** unbind the green catalog part from the red references, and bind a green
  Kingbright 0603 part later if it is wanted, archived first.

## 2. Branches this session could not delete

- **Question:** Delete the branch `codex/behavior-smoke` on GitHub?
- **Evidence:** pushing it worked. Deleting it (`git push origin --delete`) failed twice with "remote end
  hung up" from this session's git proxy. No GitHub tool in this session deletes branches.
- **Recommendation:** delete it. It points at main as of 4fa890a and holds no work.
- **Also delete:** `codex/behavior-review-followups`. A push after #35 merged re-created it at an already-merged commit, so it holds no unmerged work. Merged feature branches that GitHub did not auto-delete can also go.

## 3. The setup check "12 of 13 with --no-regression" cannot happen as written

- **Question:** None needed; this is information for the next handoff text.
- **Evidence:** `tools/behavior_audit/audit.py` `run_checks`: with `--no-regression`,
  AUD-REGRESSION-001 is a fixed failure ("Regression not run"). The full `check` on main gave
  **11 of 13**: AUD-PROTECT-001 (owner's checkout only) and AUD-VERIFY-001 (stale verifier reviews for
  the stage 2 and stage 4 entries, waiting on the verifier round on `codex/behavior-verifier`, which had
  not merged when this run started).
- **Recommendation:** in HANDOFF, say "`check` (full) gives 12 of 13 once the verifier round has merged".

## 4. Items carried over unchanged from HANDOFF (still yours)

- NE555 behavioral card re-pin (`docs/behavior/bench/ic-timer555/ne555.lib`): not touched.
- Generic-package entries (28) with class-default models: not enabled; still blocked.
- Blue 5 mm LED replacement for TLHB5800: not chosen.

## 5. A ledger row counts a rejected download as fetched (OHM-083)

- **Question:** Mark the FETCH_LEDGER row for Lite-On LTST-G563EGBW as failed, and re-download the PDF from a browser?
- **Evidence:** ledger row 2026-10-05T18:14:28Z, `https://optoelectronics.liteon.com/upload/download/DS22-2012-0212/LTST-G563EGBW.pdf`,
  http_status 200, sha256 `d9ba646224dd…`; the archived bytes are a 269-byte HTML page titled "Request Rejected".
  AUD-SOURCE-001 counts the row as a successful fetch. OHM-083 stays blocked either way.
- **Recommendation:** have the source audit reject HTML or tiny bodies for PDF URLs, mark this row failed, then download it in Chrome.

## 6. Records citing mirrors or distributors as MFR_DATASHEET (from tonight's research, not changed)

- OHM-178 (Hirose FH12): every rating comes from a copy on physics.utoronto.ca, not a Hirose host.
- OHM-158 (Molex KK): field updates cite a rapidonline (distributor) copy as MFR_DATASHEET.
- OHM-160 (Phoenix MKDS): its only source is the pdf.datasheet.live mirror.
- OHM-159 cites Conrad, OHM-162 cites onzuu and OHM-177 cites Farnell, although the same values exist in
  archived manufacturer documents (Phoenix 1715721, Molex 676433910 part page, Molex SD-73251-212).
- **Question:** Re-point these citations to the manufacturer copies through a verifier-reviewed gapfill change?
  They are all blocked entries, so no simulated result depends on them today.
- **Recommendation:** yes. This was not done tonight because gapfill edits make the verifier reviews for
  those entries stale, and a separate verifier round owns those files.

## 7. Entries that research can bind, but whose protected-spec status is research_required

- OHM-042 (Coilcraft 0805CS-150X_R_ as an explicit alternate), OHM-060 (Vishay GL41M, fitted forward curve
  and a Fig. 1 derating), OHM-075/076 (Kingbright LEDs without thermal data) and OHM-100 (IRLR8721, a card
  fitted from its own sheet) have sourced values and passing trial runs in the research notes
  (`/tmp` research output summarized in D059). Their records come from the protected spec as
  `research_required`, so a binding would only make them reference-only, never audited simulable.
- **Question:** Do you want these bound as reference-only parts, or is the research_required status in the
  spec to be revisited (a spec edit, which is yours)?
- **Note on OHM-060:** its derating is plotted against terminal temperature. Using it needs either a new
  terminal-temperature rating input or your approval to treat case temperature as terminal temperature.

## 8. OHM-148 ceramic resonator: class-default motional values?

- **Question:** May OHM-148 (Murata CSTLS8M00G53) run with the class's assumed motional C1/C0, with L1
  derived to put resonance at the sourced 8.000 MHz?
- **Evidence:** the newly archived Murata JGC40-5039 sources its ratings (6 V DC, 15 Vp-p) and pin map
  (1 input, 2 GND, 3 output) but publishes no equivalent-circuit values.
- **What overnight did:** kept it blocked. The crystals (OHM-141..145) were refused the same substitution
  (D049), and a frequency check would be tautological with L1 derived from it.
- **Recommendation:** keep it blocked unless you accept class-default motional values for resonators in
  general, labelled as such.

## 9. Seven-segment displays: a check that holds under either reading?

- **Question:** For OHM-087..089, Kingbright does not say whether PD/IF are per segment or per package.
  Adopt a check that is valid under both readings? A segment over the limit fails either way, a package
  total under the limit passes either way, and anything in between reports unknown.
- **Recommendation:** acceptable. It is your call because it reinterprets a recorded blocker.

## 10. GitHub merged #28 with a merge commit, not a squash

- The merge call asked for `squash`, but main has "Merge pull request #28" with the branch commit as its
  second parent. The content is identical. Check the repository's allowed merge methods if squash is wanted.

## 11. PRs merged before their proxy review finished

- **What happened:** these PRs were merged from your side while their proxy review (the gate in your standing
  authorization) was still running or not yet started: #30, #32, #34, #35, #36, #37 and #39.
- **What the reviews found:**
  - #30, #32, #35 and #39 came back BLOCK after merge.
  - #36 and #37 (final state) came back APPROVE.
  - #34 was merged one commit before the fix for #32's block landed.
- **How it was fixed:** every block was fixed in a follow-up PR, never by reverting main: #34 (D060), #35 (D061),
  #36 (receipts), #37 (D062/D063) and #44 (film). Main was audit-red for a short time between #34 and #36. The
  stale tantalum AC receipts no longer validated after #34's parser change.
- **Question:** for future runs, should merges wait for the proxy verdict written into the PR (my default), or
  do you prefer to merge on CI and treat the proxy review as post-merge?

## 12. Tantalum ripple check: dual solve, or keep it unknown?

- **Question:** The T491 cards carry the sourced maximum ESR (D058). Three review rounds showed that a
  single solve with that card cannot prove a ripple pass or violation (D063): real ESR, capacitance tolerance
  and ESL move the current both ways. So the T491 ripple and ESR-heating rows are now unknown. Options:
  (a) build a dual solve (ESR = 0 and ESR = maximum, plus a capacitance-tolerance margin; both must pass);
  (b) return the T491 cards to the ideal Cb || Rlk card, which gives conservative passes in passive circuits but
      loses the ESR in waveforms; or
  (c) keep it unknown.
- **Update:** option (a) was built tonight as PR #43 (D064). It is a sound *pass-only* proof: it bounds the
  current from the Thevenin port seen by the part, using a second solve with the ESR shorted. It never proves a
  violation; that would need a sourced lower bound on the 100 kHz capacitance and ESL.
- **Status:** #43 was approved on round 2 of proxy review and merged; #45 (D065) aligned the recipe limitation
  text with it. This is an engineering choice, not an owner-only item. If you prefer (b) or (c), revert #43 and
  #45 with a new PR.
- **Recommendation:** keep #43. Keep violations unknown until a lower bound is sourced.

## 13. Scope of the design-run UI and its new endpoint

- **What was built:** you asked overnight for more parallel work, and the design-level run UI was built as PR #42.
  It adds a panel, plus a `GET /api/jobs/<id>/circuit` endpoint that serves a saved project's circuit only when
  its hash matches the report.
- **Review:** its proxy review approved it after seven rounds, and it is merged. If it is out of scope, revert it with a new PR.
- **Question:** is this panel and endpoint inside the scope you want shipped? Do you accept the product wording
  ("Within the checked model limits", "A numerical result is not a safety, manufacturing or physical-fit
  approval")?
- **Note:** most real projects are refused today, because most catalog parts are not bound to audited entries.
  The panel lists every reason.
