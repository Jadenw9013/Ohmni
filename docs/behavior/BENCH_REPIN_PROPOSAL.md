# Bench re-pin proposal (not applied)

Prepared by Claude on 2026-10-05 from branch `codex/behavior-stage6` at `b0fd60f`. Nothing here has been applied to the repo or the audit. Applying it means editing the audit's validator and its locked baseline, which is your call, not the agent's.

## Why

In a fresh ngspice 42 run of the locked corpus, 73 of 205 benches pass. 143 comparisons fail as `missing/non-finite numeric comparison`, because the locked decks never print the locked quantity as a scalar. The v2 decks print one named scalar per quantity. Swapping a deck changes its locked `netlist_sha256`, and the audit refuses that by design (AUD-RESUME-001 and AUD-BENCH-001).

## What the re-pin would change, and what it would not

It would replace 105 deck files with their v2 versions, update those 105 `netlist_sha256` values, and add one label-to-scalar binding per locked item in `measurement_bindings.json` (all with scale 1). It would not change any locked expected value, tolerance or measure label, and it would not touch the shared libraries, which differ only in comments. The audit code would need two additions: support for slash-compound locked values such as `10/8/5/2`, split into components that each keep the locked tolerance, and a re-pin ledger that the resume and bench checks verify, so that the old hash must match the baseline, the expected list must equal the baseline, and every changed corpus path must be listed.

## Result against the locked expectations (outside the audit, same ngspice 42 and pipeline)

98 of the 105 pass. With the 73 that already pass, the corpus would go to 171 of 205. These seven still fail, and every one is a tolerance-interpretation question rather than a physics error:

| Bench | Locked item | Locked value | Locked tolerance (as parsed) | v2 measured |
|---|---|---|---|---|
| BEH-IC-LDO-SOT235/B2 | delta_mV | 9.7 | 0.001 | 9.747 |
| BEH-MAG-CMC/B2 | Z_2p5MHz | 7500.0 | 0.15 | 7499.836 |
| BEH-MAG-CMC/B2 | Z_10MHz | 4000.0 | 0.15 | 3707.45 |
| BEH-MAG-CMC/B2 | Z_100MHz | 400.0 | 0.15 | 399.5682 |
| BEH-MAG-INDUCTOR/B3 | f_peak | 4500000000.0 | 0.02 | 4501196000.0 |
| BEH-MAG-XFMR-CT/B2 | fc | 1639.3 | 0.03 | 1640.907 |
| BEH-MAG-XFMR-FLYBACK/B1 | Vout | 21.466 | 0.03 | 21.27373 |
| BEH-MAG-XFMR-FLYBACK/B2 | Vdrain_pk | 184.4 | 0.05 | 183.0938 |
| BEH-MAG-XFMR-SIGNAL/B2 | fL | 51.2 | 0.03 | 50.70204 |

The bare numbers 0.15, 0.02, 0.03 and 0.05 are read as absolute units. Read as fractions (15%, 2%, 3%, 5%), as the bench authors meant, all but LDO/B2 would pass. Switching to the fraction reading loosens the contract, so only a human should approve it.

## Not covered by this proposal (27 benches)

The 4 below need an expectation decision, because the v2 analytic value differs from the locked value by more than 2%:

- BEH-MAG-XFMR-CT/B3: V_open_pk locked 235.6
- BEH-MAG-XFMR-FLYBACK/B3: P_clamp locked 0.2529
- BEH-MAG-XFMR-FLYBACK/B3b: P_clamp locked 0.3528
- BEH-REG-BUCK-DCS/B2: eta_1A locked 89.6 to 91.9 percent; fsw_10mA_kHz locked 104

These 23 have locked values that are text, so a number cannot be compared without a new explicit parser. They fall into lists (`0.100, 3.135`), bounds (`<= 0.677 V`), bands (`band 0.9..1.1`), windows (`3.28 to 3.32`), and qualitative outcomes (`diverges`, `equals address`):

- BEH-DIO-BRIDGE/B2: ripple: '<= 0.677 V' / 'bound'
- BEH-DIO-BRIDGE/B3: blocked current: '< 1e-6' / 'n/a'
- BEH-DIO-PN/B2: trr: '<= 4 ns (datasheet); storage estimate 3.2 ns' / '20% of estimate'
- BEH-DIO-SCHOTTKY/B3: runaway at Ta 95C: 'diverges' / 'n/a'
- BEH-IC-DIGITAL-IF/D1: VOL, VOH at 5 mA: '0.100, 3.135' / '0.1 percent'
- BEH-IC-DIGITAL-IF/D2: I_inj mA, Vpin V: '1.0438, 3.9562' / '0.5 percent'
- BEH-IC-DIGITAL-IF/D4: Idd mA at 1 and 18 MHz: '1.389, 25.00' / '0.5 percent'
- BEH-IC-DRIVER-DIP16/B1: vce_100mA: 0.99 / 'band 0.9..1.1'
- BEH-IC-DRIVER-DIP16/B1b: vf: 1.85 / 'band 1.7..2.0'
- BEH-IC-LOGIC-SEQ/B1: QA..QH: '0,1,0,0,1,1,0,1' / 'exact'
- BEH-IC-LOGIC-SEQ/B2: low_output_index: 'equals address' / 'exact'
- BEH-IC-PKGBIND/B3: V bounce: '32.0/12.8 mV' / '1 %'
- BEH-IC-TIMER555/B1: f_TI_formula: 6857 / 'documented -2.9 %'
- BEH-IC-TIMER555/B4: VOH_100mA: 13.3 / 'TI band 12.75..13.3'
- BEH-MEM-SPINOR/F2: peak_droop_mV: '5.508, 2.554' / '3 percent'
- BEH-PKG-IC-BINDING/P1: Tj: '70.0, 55.9, 106.26, 43.396, 89.5, 54.2' / '0.1 percent'
- BEH-PKG-IC-BINDING/P3: f0_MHz: '7.5026, 7.5874, 15.0454, 12.2066, 25.1646' / '0.5 percent'
- BEH-PKG-IC-BINDING/P4: peak_droop_mV: '42.43, 21.16, 12.65' / '2 percent'
- BEH-PWR-PKGTHERMAL/B2: pmax_12_rows: 'equal datasheet' / '1.5%'
- BEH-REG-BUCK-DCS/B1: fsw_MHz: '2.381 to 2.59' / '10 percent'
- BEH-REG-BUCK-DCS/B3: deviation_mV: '5 to 30' / 'window'
- BEH-REG-BUCK-DCS/B5: vout_V: '3.28 to 3.32' / 'window'
- BEH-TRN-BJT/B8: loop_gain_criterion: 'A diverges, B converges' / 'qualitative'

## Files

`repin_plan.json` maps each locked label to its v2 scalar per bench. `repin_eval_locked.json` holds per-item measured values against the locked numbers. The v2 decks are in `bundle/docs/behavior/bench/`.
