# Landing circuit candidate

This is an isolated authoring tool for the user's requested real circuit redesign.
It does not replace product synthesis, the default catalog/footprint registry,
the accepted saved board, or the production landing page.

The rendered candidate has 32 components: the existing ESP32, BME280, four LEDs,
two buttons, USB power input and programming header, with a TLV62569 switching
regulator, 2.2 uH inductor and feedback divider. The exact circuit, pad geometry
and emitted copper have new identities. The supplied inventory is retained under
`examples/landing-redesign/supplied-proposal.json` as an unverified proposal.
Manufacturer sources and corrections are recorded in `research.json` beside it.

The optional 38-part variant has a PCA9306 and a separate board-powered 5 V I2C
header. The owner's choice of that endpoint is still pending. Its catalog,
topology and placement tests exist; it has not been selected for the preview.

## Reproduce the candidate

Run from this worktree in PowerShell, using a new output directory:

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'src')
& C:/Dev/hackathon/.venv/Scripts/python.exe -m tools.landing_redesign.build --output out/landing-pcb-redesign/reproduction --captured-on 2026-10-09 --route-seconds 180
```

The build writes CircuitIR, catalog records, requirements, placement constraints,
source hashes, schematic, placed/routed PCB, native project rules, and reports.
It refuses to overwrite an earlier output directory. It publishes a candidate
scene only after topology, placement, connectivity and the explicit switching
route constraints pass. Native and general semantic findings remain visible;
the scene is a draft, not a release certificate.

`scoped_footprints()` restores the original registry even after failure. The
new KiCad project rules express the actual authored routing profile; they do
not exclude violations or change their severities. The schematic's internal
buck power-intent marker is guarded by fresh topology checks. It is a KiCad
connectivity annotation, not an external supply or dynamic regulation result.

## Current evidence

The final local run is `out/landing-pcb-redesign/buck-final/`:

- 32 components, 23 nets, 548 track segments, 68 vias.
- KiCad 10.0.5 ERC: no electrical errors; 35 library-configuration warnings.
- KiCad DRC: zero violations and zero unconnected items, with the same geometric
  limits used by the router. The initial mismatched-rule failure is preserved.
- Switching-node route: 4.679 mm; feedback route: 7.628 mm; both on the front
  copper without vias. These are authored geometric budgets, not EMI proof.
- Final browser review: all 32 parts selectable by mouse and keyboard,
  native scrolling, motion preference behavior and 320 px reflow checked.

The original board remains unchanged. Its old LED discrepancy is not copied
into the candidate: the current approved catalog-to-pad permutation applies.

## Open engineering and visual limits

The default electrical verifier cannot derive the buck's post-inductor DC rail;
its blocked/incomplete report is retained. Scoped checks do not replace that
missing capability. USB current entitlement, exact passive realization, MLCC
derating, converter dynamics, thermal behavior, EMC/RF and hardware bring-up are
unresolved. No SPICE or bench run is claimed.

The inherited hand-solderable requirement conflicts with the BME280 LGA package.
Assembly method needs resolution. The inherited WROOM-32 footprint's fit to the
32E module, including thermal-pad and antenna details, also needs review.

The rendering uses generated pads and copper with approximate package bodies.
The added inductor and translator envelopes are based on the recorded source
dimensions; their detailed physical fits remain unestablished. USB/ESP32 close-ups
and the overall sparse composition remain open visual work. Owner acceptance,
production integration, paid Higgsfield work and publication have not occurred.
