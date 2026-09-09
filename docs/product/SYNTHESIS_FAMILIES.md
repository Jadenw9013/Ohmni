# Bounded circuit families

The deterministic compiler now supports three families through
`ohmni.synthesis.synthesize(brief)`. Each accepted result includes electrical
intent and a separate fingerprint-bound placement request. M10-T03 adds
constraint-driven placement; full frontend integration follows in M10-T04.
The existing personal-project UI remains its original
eight-configuration sensor workspace until that integration is complete.

| Family | Supported composition |
| --- | --- |
| A1 sensor | One to three BME280/TMP102 sensors on one I2C bus, optional LED and header |
| A2 controller | One to four independent LEDs, one to two normally-open buttons, optional header |
| A3 SPI memory | One or two 25LC256-I/SN EEPROMs, optional I2C sensor, LED and header |

All families use USB-C 5 V power, one 3.3 V regulator, and ESP32-WROOM-32E.
Each selected feature creates real parts and connections. Unused foreign-family
slots are refused rather than ignored. Explicit I2C addresses are reserved
before automatic assignment; impossible combinations receive typed refusals.
TMP102's ground/supply address straps (0x48/0x49) are supported; its documented
SDA/SCL straps (0x4A/0x4B) remain refused because the current typed strap model
does not represent those connections.

New empty brief fields preserve schema-v1 fingerprints. The original eight
A1 circuits retain exactly their previous hashes and 0805 package choices.
New families use a shared USB/processor compiler, not a reference fixture.
Physical artifact fingerprints can change when geometry is corrected; preserving
the electrical circuit hash does not mean preserving an obsolete PCB layout.

`ohmni.physical.placement.generate_placement(circuit, placement_request, catalog)`
generates front-side, zero-degree placements on the requested board. Functional
groups and exact capacitor owners are recorded when the circuit is assembled,
instead of being guessed from shared power nets. Search considers complete pad
and body extents, edge access, proximity, orientation and antenna exclusions.
Local and bulk capacitor distances are authored policy, explicitly marked
ASSUMED. Impossible or unsupported requests receive a typed placement failure.

The original ESP32 envelope omitted its antenna body. The physical verifier now
includes a separately source-pinned F.Fab envelope, and the current reference
policy moves the overlapping enable capacitor. Historical verification records
remain historical evidence, not verification of this corrected layout.

Product routing stops at its configured 180-second budget and preserves an
explicit incomplete result for unfinished nets. A placement PASS is followed by
independent copper connectivity, real KiCad DRC and manufacturing checks; it
does not predict those results. The board-area, emitted track-length and emitted
via-count metrics come from the actual result, not illustration geometry.

The SPI verifier checks static bus topology and reset-state chip-select pull-ups.
Firmware still controls pin setup, mutually exclusive chip selection, timing,
EEPROM writes, GPIO operation and button debounce. None of those behaviors is
verified by drawing the circuit. Current allowances marked ASSUMED are budget
estimates, not measured or manufacturer-guaranteed peak currents.

New catalog entries retain source references and CATALOG_REPORTED/ASSUMED
status. No PDF relocation or DATASHEET_SUPPORTED upgrade is claimed. Added
footprint pads and hashes were checked against installed KiCad 10.0.5 files;
all 19 catalog-offered packages compile with complete pin bindings. Generic
switch geometry has no invented manufacturer or part rating.

The exact commands, counts, sources, and review resolutions are recorded in
[M10-T02.yaml](../../.ai/verification/M10-T02.yaml). Family-wide routing benchmark,
production deployment, firmware and hardware validation remain separate gates.
