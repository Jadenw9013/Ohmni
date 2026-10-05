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
