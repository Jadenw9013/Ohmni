# Component behavior revisions

## 2026-10-04 — Stage 1 approved resolutions

- Added an explicit role-preserving `GENERIC_LED_GREEN` permutation from
  catalog pins `1/A, 2/K` to package terminals `2/A, 1/K` for its 0603 and
  0805 variants.
- Corrected the MCP1700 SOT-23 catalog order to `1=GND, 2=VOUT, 3=VIN` and
  recorded the distinct SOT-89 and TO-92 family orders from Microchip
  DS20001826F page 11.
- No bench was re-run. Canonical YAML bench measurements remain imported
  research records reporting ngspice 42, and the generated data labels them as
  such.
- Preserved the unresolved source inconsistency where the master table assigns
  `BEH-REG-LINEAR` to OHM-133 but the class YAML omits it from `applies_to`.

## 2026-10-05 — Stage 2 first research checkpoint (OHM-001..020)

- Added field-level research ledgers with actual opened PDF pages, scoped
  reference variants, unchanged source status, and links to current-run bench
  receipts. No `complete` status upgrade is made.
- Re-derived tiny-chip film temperatures and the CFR/MFR derating endpoints.
  The MFR graph reaches zero power at 155 C; the earlier extraction was ambiguous.
- Recorded the 4608X 1 W package limit and consecutive isolated terminal pairs.
- Recorded the 3296 clockwise endpoint as terminal 3, and the 3296/3314 end
  resistance limit as max(1% of total resistance, 2 ohm). These are bounds,
  not nominal contact resistances. The original spec remains byte-preserved.
- Kept RV16AF power-rating and physical-array pin binding blockers explicit.
  RV16AF's manufacturer document supplies a 150 VAC limit but no power rating;
  the distinct PTV09 alternative cannot supply that missing rating.
- Preserved variant conflicts: CRCW standard/extended operation, CPR radial
  reference versus axial illustration, RS U versus V operation, and CRA06P
  5% grade TCR (200 ppm/K, not the 1% grade's 100 ppm/K).

## 2026-10-05 — Stage 2 capacitor research (OHM-021..040)

- Added 20 field-level ledgers; all original statuses remain unchanged.
- Kept MLCC bias and aging data scoped to the manufacturer's part or example.
  A generic package size cannot establish a voltage rating or fitted bias curve.
- Recorded Nichicon's isolated auxiliary-terminal rule. The assumed third
  snap-in terminal connection cannot be promoted to a verified negative pin.
- Re-derived T491 MnO2 case ratings and temperature-dependent transient reverse
  limits. Maximum ESR is a bound, not a nominal fit; the generic 3% reverse
  threshold does not establish the T491 operating envelope.
- Recorded the newer WIMA X2 305 VAC family rating without replacing the
  conservative 275 VAC default or implying mains safety certification.
- Recorded the AVX SCCS20B505SRB 5 F reference matching the 10 x 20 mm body.
  The original mixed 10 F default remains a blocking binding conflict; the
  10 F AVX alternative needs a 30 mm-tall can.

## 2026-10-05 - Stage 2 magnetics and initial diode research (OHM-041..060)

- Added primary field ledgers, intrinsic winding diagrams and source conditions.
- WE-SL5 pairings are 1-2/4-3; physical permutations remain explicit blockers.
- AS-103 is 1:300, 200 mH minimum, 10 ohm maximum, with an external primary conductor and pins 1/3 for the secondary. The illustrated center-tapped variant differs.
- The 750311595 flyback has 12 uH primary, 2:1:0.8 ratio and parallel terminal groups; working-voltage and loss limits remain open.
- Re-derived Murata/Coilcraft alternatives without promoting placeholders, Bourns SRF and heating/drop conditions, TY-145P winding DCR and H1102NL OCL/pin roles.
- Separated diode DC and repetitive peak voltage, mounting-specific thermal figures and manufacturer-specific temperature ratings. Corrected the GL41 source identity to document 88546. All original source statuses remain unchanged.

## 2026-10-05: Stage 2 diode and indicator LED source review (OHM-061..080)

Opened package-matched primary sheets; published field/page/condition evidence and current-run class bench receipts. Source status remains unchanged. The DFM bridge drawing contradicts the assumed diagonal AC map; a derived 90-degree package transform is recorded and legacy binding stays blocked pending implementation/tests. S2M is 1.5 A, BAW56 is 90 V, SS14 hot leakage is 6 mA in the source column, and package-specific thermal conditions must not be copied between references. Exact reference LED dimensions differ from some illustrative geometry. No original spec or geometry was changed.

## 2026-10-05: Stage 2 OHM-081 through OHM-100

Added page-specific primary research and current-run receipts for LEDs, displays and transistor packages. Original statuses and canonical fields remain unchanged. OHM-083 remains unresolved after unsuccessful archival fetches. Exact manufacturer/version scopes, display pin maps, WS2812B corner/voltage conflict, OLED module limitations, maximum-versus-typical thermal values and MOSFET case-temperature conditions are explicit in gapfill ledgers.

## 2026-10-05: Stage 2 OHM-101 and OHM-102

Kept D2PAK regulator and MOSFET identities separate. Archived manufacturer product-page and PDF power/thermal conflict for IRFZ44NS; conservative PDF limits remain scoped to that revision. Distinguished Si7898DP steady-state and 10-second current, dissipation and thermal limits. Source statuses remain unchanged.

## 2026-10-05: Stage 2 independent-review corrections, attempt1

Seed10543591816165434960 found17 discrepancy items across7 of11 sampled entries. Corrected page citations and retained omitted temperature, measurement-frequency, RMS, typical-value and pulse qualifications. Downgraded the DF10M package-number mapping to a conditional DERIVED/M fact with explicit coordinate steps and library provenance. Removed unsupported per-segment allocation from three Kingbright display rating tables; aggregate allocation stays blocked. Applied shared T491 and Kingbright qualifications to sibling records. Numerical source values and all bench contracts are unchanged. The failed report is retained as stage2-attempt1.json; a fresh sample follows.

## 2026-10-05: Stage 2 independent-review corrections, attempt2

Seed13643895546496402650 found9 qualification/metadata issues across6 of11 entries. Added missing test temperature, mounting, humidity and short-pulse qualifications and Bourns revision metadata. Renamed IRLR8721 65 A as a calculated value, added its separately limiting50 A package ceiling, and preserved the source ambiguity in its RDS(on) pulse-footnote linkage. Retained the failed review; a new seeded fresh review follows. Additional IRFZ44N/NS destructive-avalanche evidence records explain why the historical0.53 J guard must not authorize operation. No analytical contract or baseline changed.

## 2026-10-05: third independent Stage 2 review

Added the ten omitted primary-source conditions to BCP56 (OHM-096) and BD139 (OHM-097): open-terminal voltage conditions, ambient/case temperature, pulse qualification and free-air board thermal conditions. Numeric values and pin maps are unchanged. OHM-083 remains unsourced and blocked. The three sampled reviews remain failed historical evidence; corrected records are not claimed independently accepted.

- 2026-10-05 Stage 3: OHM-095 adds BCX56-16 gain limits 100..250 at VCE=2 V, IC=150 mA, Tamb=25 C from Nexperia BCX56_SER Rev13 page6. Default BF follows the spec geometric-mean rule; IS remains an explicit assumption. Original source status is unchanged.

- 2026-10-05 Stage3 third batch: primary-source saturation definitions and temperature-rise conditions added for OHM045/046/048/049; SRF-based capacitance replaces the unsourced analogy where available. OHM097 explicitly binds the narrower Fairchild ungraded40..160 gain range, preserving its conflict with the ST-based40..250 spec and separate grade16 range. OHM073 retains the authored2.0 V red fit alongside the source1.8 V typical/2.2 V maximum. All statuses remain unchanged.

- 2026-10-05 Stage 3 fourth batch: OHM-014 binds only the WSL2512 two-terminal 5 milliohm reference. Opened Vishay pages 1–3 establish its value, 70 to 170 C power derating and +/-110 ppm/C component TCR; the original 75 ppm/C default remains a recorded conflict. OHM-016 binds the eight-pin bussed Bourns network, retaining both element and package power limits. OHM-071 implements and tests the derived DF10M rotation and PLUS/MINUS/AC/AC permutation. OHM-064 and six LED entries use explicit authored proxies with separately scoped reference ratings. No status or fidelity upgrade is made.
