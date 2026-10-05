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
