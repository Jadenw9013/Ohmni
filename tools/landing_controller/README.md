# Controller landing board

This isolated authoring tool builds the real-component board requested on
2026-10-09. The photograph supplies composition and finish references, not pin
identities or engineering evidence. No image or video generator is involved.

The 100 × 70 mm board has 69 electronic components: an STM32F103VBT6, an
AP2112K-3.3 regulator, a 25LC256 SPI EEPROM, two SN74HC595D registers, sixteen
Kingbright indicators with individual resistors, supply capacitors, boot/reset
support, two buttons, USB-C power and two expansion/debug headers. Every
electronic instance has a manufacturer part number. Four separate 3.2 mm
non-plated mounting holes are mechanical board features, not fictitious parts.

The MCU uses its internal HSI clock. USB-C supplies power only. The 40-contact
header exposes 36 GPIOs, two grounds and two 3.3 V outputs with a custom pinout;
it is not compatible with a named computer's expansion interface. The six-pin
header is a custom SWD connection with target voltage reference, not a second
power source. Firmware, input protection, external loads and supply current
entitlement still need engineering work.

## Reproduce

Run in this checkout with the project environment and a new output directory:

```powershell
$env:PYTHONPATH = (Join-Path $PWD 'src')
$env:PYTHONUTF8 = '1'
& C:/Dev/hackathon/.venv/Scripts/python.exe -m tools.landing_controller.build --output out/landing-controller/reproduction --captured-on 2026-10-09 --route-seconds 900
```

The build records CircuitIR, requirements, exact catalog records, source hashes,
placement constraints, schematic, copper, checks and the derived scene. It
refuses to overwrite earlier evidence. A reused `--routing-plan` must match
the circuit, placed PCB, constraints and routing rules, then pass the complete
connectivity/geometry verifier again. The output scene is withheld if topology,
placement or routing fails. Native DRC and semantic results remain explicit.

The controller-specific router reserves real copper escapes around the fine-pitch
MCU before connecting distant nets. It checks these authored paths against the
same clearance rules as every other route. The 40-pin connector has a custom
assignment chosen to reduce crossovers; manufacturer pin numbers are unchanged.
Routing uses 0.15 mm signals, 0.25 mm power, 0.15 mm clearance and 0.6/0.3 mm
through vias. These are authored geometry rules, not a qualified fabrication
process or proof of current capacity.
Non-plated hole search envelopes add 0.10 mm per side to the source hole
envelope, enforcing KiCad's 0.25 mm copper-to-hole clearance with the 0.15 mm
general trace clearance. Actual holes and component pads are unchanged.

Source research is in `examples/landing-controller/research.json`. The evidence
is manually reviewed, catalog-reported data, not machine-relocated verification.
The Murata bulk capacitor is corroborated by TI's reference-design BOM; this is
explicitly distinguished from a capacitor-manufacturer datasheet. Local KiCad
footprint subsets are pinned by byte hash and imported without mutating the
shared registry permanently.

The schematic adapter spaces the real 100-pin symbol without overlapping other
pin-label coordinates. The PCB adapter emits real non-plated holes before the
artifact hash is computed and requires matching placement/routing exclusions.
No holes or unconnected decorative traces are painted onto the image.

## Presentation and limits

`apps/web/landing-pcb-controller/` renders generated source pads and copper with
the reusable component library. Its explicit package transforms reconcile the
library's Y-up coordinates with the source footprints. The STM32's thicker
LQFP body has its own sourced profile; it does not silently reuse the thinner
TQFP envelope. The lens, lettering, finish and small internal details remain
illustrative. Masked copper is emphasized for readability; this is not a
fabrication finish specification.

The home hero embeds this viewer. The old saved engineering demo and the prior
32-part candidate retain their original identities. Rendering this authored
controller does not add a new product synthesis family or imply the workbench
can generate arbitrary STM32 projects.

Passing topology, placement, routing or native checks is not a whole-system
electrical PASS. No firmware, SPICE, bench, EMC, thermal or manufacturing release
is claimed. LED drive brightness, effective capacitance and physical fit across
manufacturing tolerances remain separate checks.

The source-centered USB mouth sits 1.325 mm behind the board edge. Mating fit
remains unverified; neither the source pads nor the shell were shifted to hide
this. HRO's 7.35 mm nominal body length differs from the pinned KiCad F.Fab
outline by 0.05 mm. C8's exact nominal height is unverified. The STM32 standoff
and lead thickness are stated range midpoints; LED internals, switch cover,
markings and surface finish remain cosmetic approximations.

## Recorded review

The checked candidate connects all 89 nets and 198 required connections with
2,324 track segments and 209 vias. KiCad 10.0.5 reports zero DRC violations or
unconnected items. ERC reports zero electrical errors and 71 retained symbol
library configuration warnings. Native pcbnew independently agrees with all
343 pad positions, sizes, drill axes and nets. Whole-system electrical status
remains UNKNOWN; these results are not a fabrication release.

The preview checks all 337 modeled contacts against numbered source pads, all
69 entries through the selector and native keyboard, an actual U1 mouse pick,
drag orbit, mobile reflow, reduced motion and WebGL fallback. The actual app
serves the exact audited assets and passes with zero browser errors. Native and
browser evidence is retained in `.ai/evidence/LP-CONTROLLER/`; the commit-bound
gate is `.ai/verification/LP-CONTROLLER.yaml`.

To view it through the actual application, start a fresh local server snapshot:

```powershell
& C:/Dev/hackathon/.venv/Scripts/python.exe scripts/demo_server.py --port 8783 --output-root out/landing-controller/live-app
```

Open `/` for the new home hero or `/landing-pcb-controller/` for its full viewer.
