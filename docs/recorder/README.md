# Voice recorder

Ohmni's fourth supported family is a USB-powered ESP32 mono PCM16 WAV recorder.
It includes an I2S microphone module, removable microSD module, record/stop
button, status LED, two 3.3 V regulators and an external programming header.
Recordings play on a computer after removing the card. There is no onboard
speaker, transcription, battery charging or USB data connection.

## Use the integrated product

In either Fetch/ASI:One or Ohmni's Board chat, ask:

> Build a USB-powered voice recorder with the included microphone and microSD,
> one record/stop button and LED. Use 32 kHz mono WAV, a 300-second limit, and
> include the programming header. No additional sensors or memory devices.

Review the proposed choices and explicitly confirm. Fetch's `OPEN` opens the
same private saved project in the main Ohmni UI. Select the microphone or card
in 3D or the systems list and ask the component tutor about that part. Its
context includes this revision's connections, firmware GPIO map, synthetic
simulation reports and physical-testing limitations. Questions remain in the
saved project's history; reconnecting or restarting the service preserves them.

In Fetch, `TEACH MIC1 How does this microphone capture sound?` and
`TEACH SD1 How is my recording saved?` use the same component tutor and save
the question/answer in the same component history visible in Ohmni.

Open **Checks & simulation** to inspect the normal, missing-card, full-card,
slow-card, removed-card and microphone-timeout scenarios. Fetch supports
`SIMULATE normal`, `SIMULATE slow card` and the other listed scenarios on the
latest saved revision without generating another PCB or charging an LLM call.
The simulation models a bounded three-second workload; it is not an analog
microphone model, actual capture or ESP32 instruction emulator. Short duration
settings may finish before an injected slow-card overflow develops.

Use project settings or Board chat to change 32/48 kHz, the 1–3600 second limit,
name, dimensions and other supported choices. Fetch can propose the same edits.
Confirmation creates a new revision; generating runs engineering checks again.
Old revisions and their chats remain available. A save never silently reuses
another revision's firmware or engineering results.

**Download build package** includes the board/manufacturing files, BOM,
confirmed choices, firmware source and instructions, six simulation JSON files
and a synthetic 440 Hz WAV. Every added file is hash-checked against that saved
revision. Altered, missing or out-of-date firmware blocks the complete download.
The package contains source, not a claim that a particular physical board was
flashed. Follow `firmware/README.md` using ESP-IDF v5.4.2 and a 3.3 V serial
adapter. No cloud/model key is needed to run the firmware on the board.

## Expanded inventory and mechanical basis

| Part | Carrier interface | Evidence and limitations |
|---|---|---|
| Adafruit 3421 SPH0645 I2S microphone breakout | Six 2.54 mm header pins | Module outline/header positions transcribed from Adafruit Eagle CAD; actual package contact identities retained in 3D. |
| Adafruit 4682 3.3 V microSD SPI/SDIO breakout | Nine 2.54 mm header pins | SPI only in this family. Card detect and chip select wired. Requires a separately purchased FAT32 SDHC card, 4–32 GB. |

These footprints are for the **assembled breakout modules**, not bare microphone
or socket parts. Use at least 5 mm standoff and inspect assembly orientation,
underside clearance, acoustic opening and card insertion access. Header land and
drill sizes are authored carrier policy. The module outlines and header positions
come from source CAD; socket/can shapes, heights and materials in the 3D model
are illustrative, not supplier STEP models or a mechanical fit certification.

Sources:
- [Microphone pinout](https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/pinouts)
- [Microphone PCB source](https://github.com/adafruit/Adafruit-I2S-Microphone-Breakout-PCB)
- [microSD pinout](https://learn.adafruit.com/adafruit-microsd-spi-sdio/pinouts)
- [microSD PCB source](https://github.com/adafruit/Adafruit-MicroSD-SPI-or-SDIO-Card-Breakout-PCB)
- [ESP-IDF I2S documentation](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32/api-reference/peripherals/i2s.html)

The bundled source boards in `src/ohmni/catalog/data/recorder` retain Adafruit's
licenses and original file names. Adafruit Industries authored these designs.
Derived module outlines and header geometry are adapted into Ohmni carrier
footprints under the accompanying Creative Commons Attribution-ShareAlike terms.
The source microphone file's historical name contains `SPK0415HM4H`; the selected
commercial module is product 3421/SPH0645. CAD hash provenance is distinct from
pinout-page evidence; catalog transcription is not machine-reverified datasheet
extraction. Stock, card price and module availability are not live guarantees.

## Firmware and software verification

Firmware continuously services I2S in a capture task, keeps the left slot from
64-clock stereo frames, converts to PCM16, buffers up to 128 blocks of 256
samples, and writes mono WAV to SPI microSD. Button presses are debounced. The
LED indicates recording/errors; serial logs report errors. Firmware does not
start Wi-Fi or Bluetooth. Cards are never automatically formatted; existing
recordings/recovery files are preserved. Only successful finalization renames a
`.tmp` recording to `.wav`. Power interruption may still corrupt FAT or audio.

Tests cover electrical pin mutations, configuration bounds, actual placement,
WAV decoding, the compiled portable C conversion/debounce/file-storage code,
fault outcomes, artifact tampering, old-project compatibility, main-browser
selection/tutoring/history/editing and Fetch revision synchronization. Native
KiCad tests generate the recorder and inspect ERC, routing and DRC. Provider
responses in automated conversation tests are deterministic doubles, so those
tests establish transport/context/persistence, not live model answer quality.

Prepare the exact exported firmware for a target build:

```sh
python scripts/prepare_recorder_firmware.py --output build/recorder --sample-rate 32000 --max-seconds 300
# Activate ESP-IDF v5.4.2 in this shell, then:
cd build/recorder/firmware
idf.py set-target esp32
idf.py build
```

The `recorder-firmware` CI workflow compiles both rates with the maximum duration
using [Espressif's build action](https://github.com/espressif/esp-idf-ci-action).
Compilation and host tests are separate evidence from execution on an ESP32.

## Still needs physical testing

No recorder prototype has been assembled, flashed or measured by this change.
Before calling it a working manufactured device, qualify:

- Module orientation, standoff, soldering, connector and card access.
- Both 3.3 V rails, startup/brownout, regulator temperature and write transients.
  The 2 mA microphone and 400 mA SD allocations are **authored assumptions**, not
  vendor maximum guarantees. USB input-current compliance also needs review;
  the board does not negotiate USB Power Delivery.
- SPH0645 I2S edge timing and data alignment, microphone port clearance, speech
  and known-tone recordings, clipping, noise, acoustic response and WAV playback.
- Both rates over the full supported duration, qualified cards' sustained write
  latency, repeated start/stop, full/missing/removed cards and power loss.
- EMI, RF, signal integrity, enclosure acoustics and manufacturing tolerances.

A successful digital simulation, target compilation, ERC or DRC does not prove
these properties. READY_FOR_MANUFACTURING_REVIEW means human review is possible;
it is not a physical-functionality or compliance certification.
