# Ohmni mono voice recorder

This source is bound to the saved revision by `manifest.json` and
`main/recorder_config.h`. It targets ESP32-WROOM-32E (4 MB flash) using ESP-IDF
**v5.4.2**. Build this exported project with that SDK, not Arduino:

```
. /path/to/esp-idf/export.sh
idf.py set-target esp32
idf.py build
idf.py -p /dev/your-serial-port flash monitor
```

Install ESP-IDF v5.4.2 using Espressif's documented tools. No API keys or network
credentials are needed. Do not flash another project's pin configuration.

## Assembly and programming

Fit Adafruit 3421 SPH0645 microphone and Adafruit 4682 microSD breakouts to their
labeled carrier headers. These are complete modules; the carrier footprint is
not for soldering bare MEMS microphones. Keep the microphone acoustic port
facing away from the carrier. Use headers with enough standoff to clear
underside parts (at least 5 mm); inspect the source PCB drawings and orientation.
The card insertion side must remain accessible. Do not substitute other module
pin orders. Add a separately purchased 4–32 GB FAT32 SDHC card; no card is
included in the PCB BOM price. Use a USB-C 5 V supply. USB-C has no data lines.

J2 programming header: 1=3V3 reference, 2=GND, 3=ESP TX/GPIO1 (adapter RX),
4=ESP RX/GPIO3 (adapter TX), 5=EN, 6=GPIO0. With USB power connected, leave the
adapter's power output disconnected. Use **3.3 V logic**, common ground, and
cross TX/RX. Ground GPIO0 and pulse EN low to enter flashing mode; release
GPIO0 and reset EN afterwards. The record button is not the boot button.

## Use

Press the record button once to start; the LED is solid while recording. Press
again to stop. The configured duration limit also stops recording. When the
LED is off, remove the card and open `REC00001.wav` (and subsequent files) on
a computer. There is no speaker, USB mass storage, transcription or upload.

Fast blinking means initialization, missing card, write, capture, or buffer
error. The serial monitor reports the reason. Stop and retry with a good card.
Cards are **never automatically formatted**. Existing WAV files are never
intentionally overwritten. Recording uses a `.tmp` filename and changes it to
`.wav` only after successfully writing the length header, syncing and closing.
Preserve `.tmp` files after an error if recovery matters. Sudden power loss or
removal during writing may corrupt the current file or the FAT filesystem;
this firmware cannot promise power-loss recovery. Back up files before use.

## Checks and physical testing

The software package includes deterministic simulation reports and a synthetic
440 Hz WAV test tone. That tone is not captured audio. Host tests compile the
portable WAV/debounce/conversion core; target compilation is reported separately
in repository verification evidence. Neither test proves microphone operation.

Before treating this as a working device, inspect assembly/polarity and check
for shorts; measure both 3.3 V rails and regulator temperature; measure USB
current and card write transients; verify GPIO26 BCLK and GPIO27 WS timing with
a logic analyzer; check the SPH0645 data alignment on GPIO16; record/play speech
and a known tone; test amplitude, clipping, noise and duration; exercise card
full/removal, slow writes, repeated recordings, reset and power interruption.
Test both 32 and 48 kHz and the maximum supported duration on qualified cards.

The microphone 2 mA and SD assembly 400 mA allocations are **authored design
envelopes, not measured or vendor-guaranteed peak limits**. Actual card peak
current and sustained latency must be qualified. Firmware does not start Wi-Fi
or Bluetooth. USB-current compliance, thermal performance and signal integrity
remain unverified until measured. Never interpret ERC/DRC or a simulation pass
as physical validation or certification.
