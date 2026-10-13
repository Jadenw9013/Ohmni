# Battery-powered motion warning board

Status: **APPROVED implementation scope**  
Scope: `BATTERY-MOTION-1`  
Approval: `.ai/approvals/BATTERY-MOTION-1.yaml`

## Product promise

Ohmni can turn a plain-language request for a battery-powered motion warning
board into a reviewed, deterministic circuit and board candidate. The first
supported version uses an external three-cell AA alkaline holder, detects motion
with a digital PIR sensor, lights a warning LED in hardware, and also presents
the PIR signal to an ESP32 for later programmable behavior.

The output is an engineering candidate with explicit evidence, checks and
limitations. It is not a security-certified detector, a complete firmware
product, or a production release.

## Bounded architecture

The admitted design is one vertical family, `A4_BATTERY_PIR_ALARM`:

1. A keyed two-pin JST-PH connection accepts an external three-cell AA alkaline
   holder. Application pin roles define `BAT+` and `BAT-`; connector keying alone
   never implies polarity.
2. An exact P-channel MOSFET protects the downstream circuit against reversed
   battery insertion.
3. A TPS63021 fixed-output buck-boost converter creates 3.3 V. Its inductor,
   input, output and bypass network must be selected from and checked against the
   pinned TI documentation.
4. An ESP32-WROOM-32E reuses the admitted processor core and observes the motion
   signal.
5. A Panasonic EKMB1101111 digital PIR sensor is positioned at a board edge with
   its viewing direction and optical keepout represented as physical intent.
6. The PIR output also drives a source-verified logic-level N-channel MOSFET and
   current-limited green LED. Motion can therefore illuminate the warning light
   without firmware.
7. A programming/debug header is allowed. USB power, battery charging and source
   sharing are absent.

## Evidence baseline

Implementation must pin local source bytes and relocate every admitted claim.
The research baseline is:

- Panasonic EKMB1101111 product and reference specification:
  <https://na.industrial.panasonic.com/products/sensors/sensors-automotive-industrial-applications/lineup/pir-motion-sensor-papirs/series/149462/model/149468>
- Texas Instruments TPS63020/TPS63021 data sheet:
  <https://www.ti.com/lit/ds/symlink/tps63021.pdf>
- Espressif ESP32-WROOM-32E/32UE data sheet:
  <https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.html>
- Energizer E91 AA alkaline data sheet:
  <https://data.energizer.com/pdfs/e91.pdf>
- Texas Instruments reverse-polarity protection application report:
  <https://www.ti.com/lit/an/slvae57b/slvae57b.pdf>
- Alpha & Omega Semiconductor AO3400A product and data sheet:
  <https://www.aosmd.com/products/mosfets/low-voltage-mosfets-12v-30v/ao3400a>
- JST PH-series product data:
  <https://www.jst-mfg.com/product/index.php?lang=2&series=199>

These URLs are discovery inputs, not verified evidence by themselves. `BM-T02`
must archive exact bytes, record hashes, confirm redistribution handling, and
bind every engineering value to recoverable source locations. Part choices may
change only when evidence shows the named candidate cannot satisfy this contract;
such a change is recorded rather than silently substituted.

## Deterministic acceptance

The family is not supported until deterministic checks cover:

- battery chemistry, cell count and supported voltage envelope;
- connector polarity and reverse-protection device orientation;
- converter input range, output voltage, current margin and exact L/C network;
- worst-case PIR supply, output-current and logic-threshold compatibility;
- worst-case LED current and MOSFET gate-drive compatibility;
- ESP32 supply margin, bootstrap-pin safety and pin collisions;
- schematic/PCB lineage, connectivity, ERC, DRC and source freshness.

PIR warm-up, battery runtime, low-battery behavior, enclosure optics and physical
bench results remain limitations unless a later task supplies the required
evidence. Runtime is always an estimate derived from a declared duty cycle and
source curves.

## Delivery sequence

| Task | Deliverable |
| --- | --- |
| `BM-T01` | Approved contract, scope ledger and implementation gates |
| `BM-T02` | Source-traceable component admission |
| `BM-T03` | Typed A4 brief and deterministic synthesis |
| `BM-T04` | Electrical and mutation verification |
| `BM-T05` | KiCad, placement, routing and manufacturing candidates |
| `BM-T06` | Conversational planning and first-user result flow |
| `BM-T07` | End-to-end regression, fallback and independent review |

Each unit is a separate reviewable change. Existing USB family fixtures must
remain stable throughout. `BM-T07` cannot complete the scope with an open
`BLOCKER` or `HIGH` finding, and absence of physical bench evidence must remain
visible in the release result.

## Explicit refusal envelope

The first family refuses or asks the user to change requests for rechargeable or
lithium cells, onboard charging, nine-volt batteries, mains power, USB/battery
source sharing, motors, sirens and other high-current alarm loads. The UI must
state the specific unsupported condition and preserve the user's original idea.
