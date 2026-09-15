# Homepage access and functional evidence — VIS-T02

The homepage now has a large live preview, a direct **Open the dense 3D board**
button and a persistent sidebar entry. Selecting a preview body opens its
inspector. Keyboard entry works repeatedly after Escape returns focus. The
separate checked design remains accessible through the 3D circuit lab below.

This follow-up does **not** turn the 124-body image-inspired scene into an
electrical circuit. Unknown reference identities remain unknown. Its geometry
and guide paths do not constitute a BOM or a netlist. The user's request for
every body in that scene to have a verified electrical purpose remains open.

## Actual board audit

The saved ESP32 sensor/controller has 29 components and 21 nets. All 29 resolve
to catalog records and registered footprints, have generated explanations and
named connections, and are reachable from U1 in the shared-net graph. Graph
reachability establishes connectivity, not useful operation or current flow.

| Parts | Established connection or intended role |
| --- | --- |
| J1, R1, R2 | USB-C power input and two sink-identification resistors |
| U2, C1, C2 | 3.3 V regulator with input/output capacitors |
| U1, C3, C4 | ESP32 and supply capacitors |
| R3, C5 | Resistor from supply to enable; capacitor from enable to ground. Precise startup timing is not established. |
| U3, C6, C7 | BME280 sensor and supply capacitors |
| R4, R5 | Pull-ups on the sensor's SDA and SCL wires |
| D1–D4, R10–R13 | Four indicators, each with a series resistor and a separate processor output |
| SW1, SW2, R20, R21 | Two grounded buttons with separate pulled-up processor inputs |
| J2 | Serial and boot-control connections for an external programming adapter |

Only U1 (ESP32-WROOM-32E), U2 (AP2112K-3.3TRG1) and U3 (BME280) have exact
catalog manufacturer part identities. The other 26 instances use six generic
catalog types with selected packages and modeled values. Their manufacturer,
supplier and some electrical ratings remain unspecified. Catalog resolution
does not establish a completely specified purchasing BOM.

Fresh deterministic semantic verification reports 100% rule coverage, no
critical/error findings, one assembly warning and two informational findings.
The warning is the BME280 LGA package's hand-solderability; the information
concerns boot strapping and external serial-header orientation. Identity is
PARTIALLY_VERIFIED. Coverage does not mean every possible property was checked.
Firmware, GPIO current capacity, bus timing, thermal/RF/EMC and bench operation
remain unverified or unsupported.

The audit exposed a learning bug: the I2C measurement explanation treated
compute-group pull-up resistors as receivers. Receiver selection now uses
catalog MCU categories. U1 receives measurements; R4/R5 keep their pull-up
stage. The verified preview exporter regenerated the saved projection. **Only
`flows` changed**; board geometry, component identities and source metadata are
identical. All 22 recorded engineering source files remain byte-identical.

## Functional expansion boundary

The supported generators currently top out at 24 parts for A1 (sensors),
29 for A2 (sensor/controller, the saved board), and 25 for A3 (sensor/memory).
See `src/ohmni/synthesis/a1_extended.py`, `a2.py`, `a3.py` and `models.py`.
The previous user choice of ESP32 sensor/controller fits A2.

A denser functional design must be synthesized from selected requirements and
admitted component evidence. Combining the existing sensor, button/indicator
and memory blocks is not currently implemented: A2 uses GPIO23 for an indicator
where A3 needs MOSI, and A2's GPIO25/26 indicators conflict with A3 chip selects.
Resolving pin allocation requires a new composition and fresh semantic,
placement, routing and release verification. Firmware behavior and physical
validation are additional work. The 124 shapes are not a target component count.

An optional preference question is pending: retain supported function or expand
component support for a denser functional board. No response is recorded as
approval of a new electrical architecture. W8's earlier proposal remains a
proposal; M10-T05 remains parked.

## Reproduction and evidence

Homepage browser regression (installed Playwright and Edge, external requests
blocked):

```powershell
$env:OHMNI_PLAYWRIGHT_MODULE='C:/Users/wongj/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/homepage_acceptance.cjs http://127.0.0.1:8767 out/visual-reference
```

Browser checks cover direct buttons, three successive Enter/Escape inspections,
focus restoration, retained actual circuit access, and 1500/849/390 px layouts.
Screenshots: `out/visual-reference/screenshots/60-homepage-dense-entry.png`,
`61-homepage-849.png` and `61-homepage-390.png`.

Local per-component evidence and its reproducer:
`out/visual-reference/functional-board-audit.json` and
`out/visual-reference/audit-functional-board.py`. These ignored files contain
catalog/package identities, source hashes, pins, nets, explanations, graph paths
and the complete fresh semantic findings. Committed verification/review records
are `.ai/verification/VIS-T02.yaml` and `.ai/reviews.yaml#VIS-T02-FINAL`.

Verification: canonical fast 1,478 passed / 44 deselected; frontend 180 passed;
guarded preview reprojection passed with native ERC/DRC rechecks; homepage
browser regression passed; focused independent review cleared its one keyboard
finding after correction. The earlier human visual acceptance remains pending.
