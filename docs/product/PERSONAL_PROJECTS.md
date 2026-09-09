# Personal sensor projects — implemented A1 unit

The first implementation unit following the September 8, 2026 research review
turns the reference-only interface into a bounded local project workspace.
This does not complete the broader M10 roadmap or constitute a production launch.

## User journey

The home page offers **Make it my project** alongside the saved reference lab.
Users choose a name, status LED, programming header, and sensor address, then
save a revision before generating. Edits clear the displayed engineering result
and disable generation until saved. Each revision retains its original brief,
preview, and run history. Opening an earlier revision restores those choices.

The sensor challenge asks the user to predict and repair a supply error in a
separate practice circuit. Each answer runs the backend electrical verifier.
Moving only VDD leaves VDDIO incorrect; moving both supplies to 3.3 V clears the
voltage fault. Rule findings and the catalog's actual evidence status are
available. No answer changes a saved project or simulates physical hardware.

Completed projects open in the existing 3D learning lab. Explanations reflect
actual topology; omitted LED/header parts disappear from the board and the
relevant lessons. The build package includes the saved brief, revision and
attempt identity, report, CAD and fabrication files, BOM, and build guidance.

## Supported envelope and implementation

| Choice | Supported values | Electrical effect |
| --- | --- | --- |
| Status light | Included / omitted | Adds or removes D1 and its current-limiting resistor R6 |
| Programming header | Included / omitted | Adds or removes J2 and its programming connections |
| BME280 address | 0x76 / 0x77 | Straps SDO to ground or the 3.3 V rail |

All eight combinations use USB-C 5 V input, a 3.3 V regulator, one
ESP32-WROOM-32E, one BME280, and a two-layer 100 × 70 mm authored layout.
Unsupported inputs receive a typed refusal before EDA. The deterministic
synthesizer does not import the golden circuit or scripted model provider.

The project pipeline runs semantic verification, actual KiCad schematic ERC,
physical checks, deterministic routing, independent route verification, KiCad
PCB DRC, manufacturing checks, BOM evaluation, and fabrication export. Physical
errors stop release. Personal projects do not replay the fixed example's repair.

The authored placement keeps the sensor pull-ups at R4 (82,44) and R5 (86,44).
This leaves a route for CSB power when address SDO is high; the previous placement
failed the minimal 0x77 case. The general router was not changed.

SQLite stores projects, immutable revisions, jobs, and revision attempt history.
An operating-system file lock permits one server per output workspace. A restart
marks interrupted jobs failed and permits retry; it does not declare them
finished. This is local persistence, not multi-user account isolation.

Publication and downloads compare the saved brief fingerprint and deterministically
derived circuit with the report and fabrication lineage. The ZIP is assembled
from verified file buffers and authoritative revision metadata. Changed or
misbound artifacts fail closed instead of being presented as current.

## Evidence and remaining limits

The final authored geometry routed successfully for all eight combinations.
Real KiCad 10.0.5 DRC reported zero violations and zero unconnected items for
each. Its default ignored check categories remain recorded in raw DRC reports.
Fresh default and minimal 0x77 end-to-end pipeline tests both completed with
current fabrication releases. The durable verification record is
[M10-T01.yaml](../../.ai/verification/M10-T01.yaml).

This unit does not provide general placement optimization, arbitrary components,
firmware, simulation, live supplier data, cloud hosting, or physical validation.
Seed catalog citations have not been machine-reverified against source PDFs.
Manufacturing limits, prices, and availability use explicit example data.
Component bodies and animations are illustrative. BME280 assembly requires
suitable equipment, and USB-C supplies power rather than programming data.
Passing software checks does not establish working hardware or RF/mechanical
suitability. These limitations remain visible in the product and download.
