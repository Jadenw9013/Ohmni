# Generated sensor and controller explorer

The landing page's **Sense & control** board is a saved, reproducibly generated
design. It contains an ESP32-WROOM-32E, a BME280 environmental sensor, four LED
outputs, two active-low buttons, a USB-C power input, regulated 3.3 V supply,
programming header, and their support components: 29 components on 90 × 55 mm.

Select **Customize this board** to copy its exact confirmed brief into a new,
unsaved project. Sensor choice, LED/button counts, programming-header inclusion
and board dimensions are editable. Save and generate to obtain that revision's
own schematic, PCB and reports. Changes are compiled through the existing
deterministic synthesis and verification pipeline; the saved preview never
becomes a result for the new project.

The A2 family supports zero or one BME280/TMP102 I2C sensor, one to four LEDs,
and one or two buttons. Dimensions are 40–100 mm wide and 40–70 mm high. A size
inside these bounds can still fail placement or routing. Default 100 × 70 mm
briefs retain their historical fingerprints.

## Reproduce the showcase

With the project environment and KiCad available, use a new output directory:

```powershell
.\.venv\Scripts\python.exe -m ohmni generate --brief examples/sensor-controller.json --output out/sensor-controller
.\.venv\Scripts\python.exe -m ohmni.application.reference_preview --run-dir out/sensor-controller --output apps/web/reference-board.json --captured-on 2026-09-14
```

The date is explicit capture metadata; use the date of a new capture. The exporter
reconstructs the design from its confirmed brief, regenerates placement and
schematic/PCB artifacts, checks their exact bytes and release files, reruns
semantic, physical, routing and manufacturing checks, then reruns bounded KiCad
ERC/DRC. Incomplete, changed, failed or unreproducible source runs are rejected
before replacing the preview. Restart the demo server to serve the new immutable
asset snapshot.

`reference-board.json` contains the confirmed brief, projected parts, footprints,
pads, copper, pin/net membership, systems, learning content, check summaries,
source fingerprints and limitations. Every component in the lab is selectable;
its inspector explains its purpose and shows the pins and peer parts on each
connection. The same renderer and lessons support fresh generated projects.

## What the saved board establishes

The captured design has 21 nets, 452 track segments and 55 vias. Routing passes;
KiCad DRC has zero violations and zero unconnected items. ERC passes with 31
warnings, recorded in the source run. Electrical checks use the bundled catalog;
identity remains partially verified. The example manufacturing profile is
synthetic and still needs fabricator review.

Package bodies, heights, finishes and reference lettering are illustrative.
Footprint/pad coordinates and copper are projected from the PCB; no decorative
components, traces, pours or mounting holes are added. Connection pulses are
learning aids. Firmware, simulation and bench validation are not provided by
this enhancement. A fabricated, assembled and programmed board still needs
bring-up and measurement before its operation can be established.

M10-T05 remains parked. Its frozen R-18 benchmark expected an A2 sensor request
to be refused; optional sensing now deliberately changes that contract. The
historical corpus is preserved, and its evaluator reports this as a mismatch,
not a silently updated success or completed milestone.
