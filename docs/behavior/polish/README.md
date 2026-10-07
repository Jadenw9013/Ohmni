# Polish of the 42 simulable entries (2026-10-07)

`fits_*.json` are the full extraction records behind the `spice_*` and `thermal_resistance_*`
fields added to the gapfill evidence: datasheet page and figure, read points (taken from the PDF
vector paths where the figure is vector), fit method, residuals, confidence and every parameter
left unresolved with the reason. Values were adopted into gapfill `field_updates`; the runtime
binds model terms through recipe `model_facts`, which follow the same sourcing rules as
`critical_facts` but do not lower the rating confidence.

Held back on purpose:
- Forward DC fits for OHM-056, 059, 061 (1N4148 family) and OHM-073 (TLDR4400) are recorded but not
  bound: their runtime probes compare against the shared class card's locked analytic point, so
  binding a per-part curve needs an audit-rule change (compare against the part's own datasheet).
- BCX56 Early voltage (curves likely self-heating), BAT42W junction capacitance (the Schottky
  template's fixed VJ/M cannot match the curve), inductor saturation floor `lr` (no source),
  resistor parasitics (no source), Si7898DP Cgs (model has no Cgd), SMBJ15A RDYN (existing
  calibrated value kept).
