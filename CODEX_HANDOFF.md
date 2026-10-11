# Handoff prompt for Codex: OHMNI full-library behavior pass (continue from main 1f52efab)

You are continuing the owner's request: "make sure all the components are fully sourced and can fully simulate. Go one by one through the component library, fixing any that are lacking. Do additional external research on each specific component for accuracy." The previous agent (Claude) stopped mid-way, and its working copies are gone. Everything you need is on GitHub and below.

## 1. Read first (in this order)
- `AGENTS.md`, `docs/behavior/RUNTIME.md`, `docs/behavior/HANDOFF.md`.
- `out/component-behavior/run/DECISIONS.md`, entries **D066–D075**. These record the owner's decisions and what each batch did.
- `docs/behavior/COVERAGE.md`. It is the per-entry table of what simulates and why not.
- `out/component-behavior/run/STATE.json` → `model_blockers`. This holds the current blocker for every non-simulating entry; most end with a "Re-checked 2026-10-11 (D0xx): …" note naming what's missing and which document would close it.

## 2. Where things stand (main = 1f52efab)
- **Audited simulable: 129 / 180** (it was 78 at the start of this pass). 139 entries are bound, all runtime receipts validate (0 errors), and the audit is 11/13. The two failing rules are expected:
  - AUD-PROTECT-001 can only pass in the owner's checkout;
  - AUD-VERIFY-001 is waiting on the verifier round.
- **Merged this pass:**

  | PR | Batch | Decision |
  |---|---|---|
  | #47 | Packages simulate as their bound reference part | D066 |
  | #50 | 11 capacitors | D067 |
  | #51 | 7 connectors, plus per-contact and collective current limits | D068 |
  | #52 | 5 mains/safety parts as electrical models only | D069 |
  | #56 | LEDs and displays, plus L3 entries simulate "electrical pins only" | D070, D071 |
  | #57 | Misc parts | D072 |
  | #58 | Crystals | D073 |
  | #59 / #61 | 7 MCU/FPGA pin-level models in reset state | D075 |
- **Full pytest:** passes except 3 tests that need KiCad 10 (`test_personal_project…` ×2 and `test_admitted_part…`). They fail identically on main because KiCad isn't installed in the agent sandbox. Node: about 1082/1082.

## 3. Owner decisions already made (don't re-ask)
- **D066:**
  1. Fetch new manufacturer documents from the web into the ledger.
  2. A package entry with a bound exact part simulates "as" that part.
  3. Build pin-level electrical models for MCUs, ICs and L3 parts, with firmware and protocol stated as not modeled.
  4. Build mains/safety parts as electrical models, with the limitation "No mains, isolation or safety acceptance".
- **Spec status flips:** you may change a `research_required` status cell in `COMPONENT_BEHAVIOR_SPEC.md` to `partial` once new evidence closes that entry's recorded blocker and a review approves. The previous agent's sandbox blocked edits to that file, so these flips are still pending (see §4.1).
- **Vendor models:** TI's official PSpice models may be used, and so may Infineon's IRLR8721 model with a typical-to-maximum probe and an IS=0 exemption for vendor cards. **But the repo is PUBLIC and these files must NOT be committed** (see §4.2).
- **Owner-only, never decide:** re-pinning `docs/behavior/bench/`, choosing a replacement blue LED or touching GENERIC_LED_GREEN, and writing any `approved_by` or approval record in the owner's name.

## 4. Remaining tasks, in priority order

### 4.1 Spec status flips (small, high value: +9 simulable)
In the `COMPONENT_BEHAVIOR_SPEC.md` master table, change `research_required` → `partial` for these entries, whose blockers new evidence closed:
- **D071:**
  - OHM-075: WP813ID thermal data.
  - OHM-076: WP113IDT thermal data.
  - OHM-087 and OHM-088: Broadcom HDSP-5503/5523 give their ratings "per Segment or DP".
- **D072:**
  - OHM-042: Murata LQM21PH2R2MGEL.
  - OHM-062 and OHM-063: BAS316/BAS516 have a sourced 250 mA rating.
  - OHM-071: the DF10M outline shows the AC leads adjacent.
  - OHM-099: IRFP260N pin order.

**Not** OHM-053, whose working-voltage and loss limits are still unsourced. Then run `python scripts/generate_behavior_records.py --write`, the examples generator and coverage, and update the count tests to the new count (129 → 138). The protected-spec baseline (AUD-PROTECT) cannot absorb a spec change; the owner re-records it, so say so in the PR. Record this as a new D-entry.

### 4.2 Vendor models without committing them (D074 redo; +3 or +4)
- **What happened.** The old branch `codex/behavior-vendor-models` (PR **#62**) committed vendor model files:
  - `docs/behavior/vendor/infineon/irlr_u8721pbf.spi`, which reads "UNPUBLISHED LICENSED SOFTWARE … Commercial Use or Resale Restricted by Symmetry License Agreement";
  - three TI libraries reading "(C) Copyright Texas Instruments. All rights reserved."

  Its tip f3d7a50a removes them, but they are still in its history (commit cbda462d). **Do not merge #62.** The owner should close it and delete the branch.
- **Redo it on a new branch from main.**
  1. Port cbda462d's design except `docs/behavior/vendor/**`. Use `git show cbda462d` to read it, and the D074 text in that commit. Never let a commit on the new branch contain the vendor text.
  2. Add an `archived_assets` recipe mechanism. A recipe names the fetch-ledger sha256 (for TI zips, also the member path and the member's sha256). The compiler loads the bytes from `out/component-behavior/run/fetched-sources/` (gitignored), verifies the hash, and inlines them in memory only. When the bytes are missing, it fails closed with the message "vendor model is not in the local source archive; run `python -m tools.behavior_audit rebuild-sources`".
  3. Keep vendor text out of every committed file: receipts, `output.txt`, `reference-circuits.json`, examples. Store hashes, not netlists, for those decks.
  4. Add a test that fails if any tracked file contains strings such as `MODPEX`, `Symmetry` or `Texas Instruments Incorporated`.
  5. Tests that need the bytes skip in CI, where the archive is absent. Coverage counts these entries only when the archive is present.
- **Parts and their checks** (values observed in ngspice 42 with the vendor models):
  - **OHM-132, TI TPS22810DRV load switch:** RON at VIN 12 V, 200 mA, 25 °C against 78.5–86 mΩ; observed 80.0 mΩ. The TI EVM schematic ties the pad to GND.
  - **OHM-133, TI TPS7A8001DRB:** VOUT and FB at VIN = VOUT + 0.5 V, 100 mA, ±3%; observed 3.3002 V and 0.80004 V. TI's model has a fixed 0.35 V dropout and models neither IQ nor NR.
  - **OHM-134, TI TPS62160DSG buck:**
    - Test: 12 V → 3.3 V at 0.5 A, 300 µs start-up, averaged over 250–300 µs, ±3%. Observed 3.3068 V, FB 0.8014 V, PG high.
    - Needs `.options interp`. Without it, one run printed about 111 MB of rows.
    - Needs an ideal 2.2 µH inductor fixture. The bound 1.8 µH OHM-045 stops with "timestep too small".
    - Each run takes about 2.5 minutes, so reference runs need a 600 s timeout.
  - **TI runner mode:** decks containing these TI models need `ngspice -D ngbehavior=psa`, scoped to those decks only.
  - **OHM-100, Infineon IRLR8721PbF, `irlr_u8721pbf.spi`:**
    - Rds(on) checked typical-to-maximum: 6.271 mΩ at 10 V / 25 A and 11.394 mΩ at 4.5 V / 20 A.
    - Pin map from datasheet p10: gate 1, drain 2, source 3, tab drain.
    - Its VTO of 2.59 V is above the datasheet maximum of 2.35 V. State that gate-drive margins taken from the model are optimistic.
    - **Ask the owner first.** The Symmetry licence restricts commercial use even when the file is local only. TI's files are lower risk when kept local.
- The model files are already in the fetch ledger, rows added by research. If the bytes are missing, re-fetch them from TI's product pages and from Infineon's IRLR8721 design-resources page.

### 4.3 MCU pin-level review fix (a proxy reviewer blocked #59's content before it was merged)
- **Must-fix 1.** `ratings._pin_level_checks` compares pads only against their absolute maximum. Add operating-input limits:
  - **STM32F4** (DS8626 Rev 12, Table 14, p82): FT and RST pins −0.3..5.5 V (5.2 V when VDD ≤ 2 V); TTa pins VDDA + 0.3 V.
  - **STM32F103** (DS5319 Rev 20, Table 9, p38): standard I/O VDD + 0.3 V; FT 5.5/5.2 V.
  - **XC7A35T** (DS181, Table 2): VIN ≤ VCCO + 0.20 V.
  - **ATmega328P and ATmega32U4:** whatever the datasheet's DC characteristics give.

  A pad above its operating limit but below its absolute maximum must not read `within_limit`; make it a violation or unknown, and justify the choice. Fix `tests/test_behavior_mcu_pins.py`, which currently asserts PA0 (FT) at 7.2 V and PA4 (TTa) at 3.9 V with VDD 3.3 V are `within_limit`. That is wrong.
- **Must-fix 2.** STM32F4 NRST (OHM-124/125/126) has a permanent pull-up. Per DS8626 Table 14 note 6, VDD + 0.3..4.0 V must be unknown (use `above_supply_unknown`).
- **Nits:**
  - AVR RESET's missing clamp is *inferred* from the +13 V rating; word it that way in `PIN_LEVEL_MODELS.md`.
  - Re-source the ATmega328P 1.8–5.5 V window from DS40002061B instead of the Princeton mirror.
  - In UG475, 8.4 is θJC, not θJA; fix the OHM-138 column label.
- Amend D075.

### 4.4 PR #60 (`codex/behavior-verifier`) conflicts with main
- **Conflicts:**
  - 7 gapfill pages: OHM-015, 122, 123, 124 (2 hunks), 125 (3), 126 (3) and 131.
  - Generated files: `reference-circuits.json`, receipts and `src/ohmni/behavior/data/**`.
- **Pattern.** The verifier corrected existing evidence lines, and main appended new `field_updates` for the D072 and D075 bindings next to them.
- **How to resolve:**
  1. Do a 3-way merge (`git show :1:/:2:/:3:<path>`) that keeps BOTH sides. Where the two sides disagree on a value, the archived PDF decides.
  2. Validate every ```audit-evidence JSON fence.
  3. Regenerate the generated files: records, examples, every receipt, coverage.
  4. Run the tests and push a merge commit. No force-push.

### 4.5 Still-blocked entries worth another try (all researched 2026-10-11; reasons in STATE)
- **Würth sheets that return 403 to the fetcher:** OHM-151..154 (61301021121, 61300811821, 61301021821, 61300811021) and OHM-083 (150505M173300). Browser-download them, then ingest with `tools/behavior_audit/ingest_manual.py`.
- **Molex unreachable:** OHM-158 and OHM-177.
- **Hirose/TE 403:** OHM-168 and OHM-178.
- **No maker publishes a current or power rating:** RF connectors OHM-175/176.
- **No motional C1/L1 published:** crystals OHM-141/142/144, and C1/C0 for resonator OHM-148.
- **Other evidence gaps:**
  - OHM-147, TCXO: no thermal or output limits.
  - OHM-149, SAW filter: its 10 dBm and 10 V are TYP values. An unverified lead says a related Abracon part is rated 0 dBm maximum.
  - OHM-017: no numbered array drawing.
  - OHM-020: no RV16AF power rating.
  - OHM-060: the GL41 derating is against terminal temperature, which needs a rule change.
  - OHM-089 and OHM-090: no source for the four-digit allocation or the 8×8 matrix.
  - OHM-092: no maker sheet for the OLED module.
  - OHM-086: no star-module pad map. Its record says simulable while a blocker remains; reconcile that.
- **ICs:**
  - OHM-108: the ATmega328P-PU is 300 mil, but the library DIP-28 is 600 mil; this needs an owner decision.
  - OHM-109, W65C02S: no ratings published.
  - OHM-121, TPS3808: needs a new supervisor class.
  - OHM-127, TPS62130: needs a BUCKCORE_SW model that exposes SW.
  - OHM-128/129, FT231X and CP2104: no thermal data.
  - OHM-130, ESP32-C3: no per-pin or thermal limits.
  - OHM-135: no absolute-maximum VDD or Tj.
  - OHM-136: obsolete part.
  - OHM-137, LPC1768: needs a current-source pull-up pad.
  - OHM-139, MAX98357A: needs a shutdown-state model.
  - OHM-140, NX5P3290: no vendor model. A draft reverse-blocking model exists but isn't hashed.
- **Blocked for a framework gap:**
  - OHM-054, current transformer: its primary is a wire through the hole.
  - OHM-053, flyback: working-voltage and loss limits are unsourced.

## 5. How every batch must be done (the invariants that kept this honest)
- **Sources.** Every value comes from an archived **manufacturer** document. Fetch it with `python -m tools.behavior_audit fetch --url <url>`, check the bytes are the real datasheet with pdftotext, and quote the page. Never use memory. Distributor pages and mirrors are secondary. Archived bytes live in `out/component-behavior/run/fetched-sources/`, which is gitignored and never committed. Datasheets and vendor models are copyrighted.
- **Fail closed.** `UNKNOWN` never becomes PASS. Rating rules fail closed: a missing condition gives unknown, and an assumption never produces a pass.
- **Recipe file.** `docs/behavior/runtime-recipes.json` is **CRLF**. Edit it binary-safe, then check that `grep -c $'\r$'` equals `wc -l`.
- **Regeneration.** Any recipe edit restamps every runtime receipt (`recipe_source_sha256`), so regenerate everything (about 15 minutes):

  ```
  python scripts/generate_behavior_records.py --write
  python scripts/generate_behavior_examples.py
  python - <<'P'
  from pathlib import Path
  from collections import Counter
  from tools.behavior_audit.audit import BehaviorAudit
  from tools.behavior_audit.runtime_benches import run_runtime_recipes, runtime_receipt_errors
  from ohmni.behavior.loader import BehaviorRegistry
  from ohmni.behavior.netlist import load_recipes
  a=BehaviorAudit(Path('.').resolve(), None); a.initialize()
  rs=run_runtime_recipes(a); print(Counter(r['run_status'] for r in rs))
  rec=load_recipes(BehaviorRegistry(repo_root=a.root),a.root)
  bad={k:e for k in rec.entries if (e:=runtime_receipt_errors(a,k))}; print(len(rec.entries),'with errors',len(bad))
  P
  python -m tools.behavior_audit coverage >/dev/null
  ```
  Then `git add -f` any new receipt files under `out/`. The audit and test runs rewrite `out/component-behavior/run/CANARY_RESULTS.json` and `REGRESSION_RESULTS.json`; revert them with `git checkout -- out` before committing.
- **Count tests.** Update `tests/test_behavior_api.py` (`states.count('simulated')`), `tests/test_behavior_service.py` and `tests/test_behavior_examples.py` (bound count).
- **Merge conflicts between batches.** They always hit receipts, COVERAGE.md, DECISIONS.md, STATE.json, FETCH_LEDGER.jsonl and the count tests. Resolve as follows:
  - FETCH_LEDGER.jsonl: take the union of both sides.
  - DECISIONS.md: keep both entries, in D-number order.
  - STATE.json: drop the blockers of entries either side bound.
  - Count tests: add up both sides' increments.
  - Receipts and generated files: take either side, then regenerate everything.

  Merge with merge commits; the owner merges PRs with merge commits, so stacked branches stay conflict-free.
- **Before each merge.** Run `python scripts/verify.py full` (expect only the 3 KiCad failures), `cd apps/web && npm test`, `python -m tools.behavior_audit check` (11/13) and `python scripts/ai_state.py validate`. Then a fresh-context review must answer three questions: (1) is any unknown shown as a pass? (2) is every value traced to an archived document? (3) are the limitations honest? Record the verdict in the PR. A "no" blocks the merge.
- **Conventions.**
  - Each decision gets a new D-number in `out/component-behavior/run/DECISIONS.md`. The next free one is **D076**.
  - Branch names start with `codex/behavior-`.
  - Never force-push or rewrite main.
  - Don't touch `out/component-behavior/run/verifier/` except when resolving PR #60.
  - Don't commit vendor model files or datasheets: **the repo is public**.
