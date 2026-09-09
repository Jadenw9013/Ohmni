# Bounded circuit families — M10-T02

The deterministic compiler now supports three families through
`ohmni.synthesis.synthesize(brief)`. This unit adds compiler capability;
constraint-driven placement and the full frontend integration follow in
M10-T03 and M10-T04. The existing personal-project UI remains its original
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
[M10-T02.yaml](../../.ai/verification/M10-T02.yaml). Full physical routing,
production deployment, firmware and hardware validation are separate work.
