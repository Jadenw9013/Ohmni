# Stack-chan desk tutor (tools/stackchan)

Custom firmware for the M5Stack StackChan desk robot (CoreS3 + feedback-servo base)
and a Python companion that runs on the user's computer. Together they let the
robot narrate an Ohmni board, listen when its head is double-tapped, and steer the
Ohmni workspace. Scope and approval: [plan](../../docs/hackathon/STACKCHAN_TUTOR_PLAN.md),
`.ai/approvals/STACKCHAN-TUTOR-1.yaml`.

This directory has **no runtime dependency on Ohmni** and Ohmni does not import it
(`tests/test_stackchan_isolation.py`). Its Python packages are not Ohmni extras.

The factory firmware only talks to M5Stack's mobile app over Wi-Fi/BLE and answers
nothing over USB. This firmware accepts line-delimited JSON over the base's USB-C port.

## Layout

- `firmware/`: PlatformIO project (platform `espressif32@6.12.0` = Arduino-ESP32
  2.0.17, M5Unified 0.2.26, M5GFX 0.2.33, ArduinoJson 7.4.2). M5Unified must know
  `board_M5StackChan` (0.2.7 left the speaker and internal I2C unconfigured).
  `lib/FTServo` is Feetech's servo driver from m5stack/StackChan (MIT, see `SOURCE.md`).
- `companion/stackchan.py`: serial library + CLI (pyserial).
- `companion/voice.py`: narration and double-tap voice commands (macOS `say`,
  local Whisper via `mlx-whisper`).
- `companion/ohmni_link.py`: loopback WebSocket link to the Ohmni workspace page.
- `companion/stall_test.py`: manual stall-protection test.
- `dances/`: timed pose/face/LED sequences (JSON).
- `tests/`: host tests, no hardware needed.

Hardware facts (servo bus, IO expander, touch controller, calibration NVS keys)
come from M5Stack's open-source firmware, github.com/m5stack/StackChan
(`firmware/main/hal`, MIT); `firmware/partitions.csv` is its partition table.

## Set up

```sh
cd tools/stackchan
python3.13 -m venv .venv
.venv/bin/pip install -r companion/requirements.txt        # pyserial, numpy, mlx-whisper (Apple silicon), websockets
.venv/bin/pip install pytest && .venv/bin/python -m pytest tests   # host tests
```

## Back up the factory firmware first

Do this once, before flashing, so the robot can be restored exactly (including
Wi-Fi and app pairing):

```sh
.venv/bin/pip install esptool
.venv/bin/esptool --port /dev/cu.usbmodemXXXX read-flash 0 0x1000000 stackchan-factory-16MB.bin
.venv/bin/esptool --port /dev/cu.usbmodemXXXX verify-flash 0 stackchan-factory-16MB.bin
```

Keep the file outside the repository. Restore with
`esptool --port … write-flash 0 stackchan-factory-16MB.bin`, or flash M5Stack's
**StackChan-UserDemo** firmware with M5Burner (V1.4.4 was the factory version
on the robot used for development).

## Flash

```sh
cd firmware
pio run -t upload --upload-port /dev/cu.usbmodemXXXX   # ls /dev/cu.usbmodem*
```

Uploads use the factory addresses: app at `0x20000`, OTA selector at `0xd000`
(`factory_layout.py` patches Arduino's hardcoded `0xe000`). The partition table
matches the factory one, so the robot's servo calibration (NVS namespace `servo`)
is reused. The firmware only reads it.

## Use

```sh
.venv/bin/python companion/stackchan.py ping
.venv/bin/python companion/stackchan.py face happy
.venv/bin/python companion/stackchan.py pose 20 40 --ms 500
.venv/bin/python companion/stackchan.py led 0 80 255
.venv/bin/python companion/stackchan.py play dances/hello.json
.venv/bin/python companion/stackchan.py record dances/mine.json --seconds 8   # move the head by hand
.venv/bin/python companion/voice.py listen-test --once   # double-tap, speak, see transcript + levels
.venv/bin/python companion/voice.py ohmni                # narrate the board open in the Ohmni workspace
.venv/bin/python companion/voice.py demo                 # offline example narration; double-tap to interrupt
```

Opening the port can reset the robot; the companion waits for the boot `ready` event.

## Serial protocol

One JSON object per line, each answered by one line with the same `id`:

| cmd | params | notes |
|---|---|---|
| `ping` | | `{fw, version, ioe}` |
| `state` | | `{yaw, pitch, torque, limits, face, battery}`; angles `null` if a servo doesn't answer |
| `pose` | `yaw`, `pitch` (deg), `ms` | yaw −128..128, pitch 3..87 (factory limits, clamped) |
| `torque` | `on` | `false` lets you move the head by hand (also clears stall limits) |
| `reset_limits` | | clear limits narrowed by stalls |
| `face` | `expr`, `mouth` 0..1 | neutral, happy, sad, angry, surprised, sleepy, thinking, listening |
| `led` | `rgb:[r,g,b]` or `leds:[[r,g,b]×12]` | |
| `tone` | `hz`, `ms` | error `listening` while listening |
| `play` | `pcm` (base64 int16 LE mono 16 kHz, ≤ 4096 samples) | replies once queued (real-time flow control); error `listening` while listening |
| `play_stop` | | stop speech playback |
| `listen` | `on` | start/stop streaming the microphone |
| `diag` | | board id, PSRAM, sprite, speaker, mic, touch, IO-expander registers |

Errors: `{"ok": false, "error": "..."}`. Unsolicited messages:

- `{"event":"ready","fw","version","ioe","touch"}` on boot
- `{"event":"stall","axis","deg","dir","current","load"}` when a move is blocked
- `{"event":"touch","gesture":"double_tap"|"swipe_forward"|"swipe_backward"}`
- `{"event":"listen","on":true,"source":"touch"|"host"}` and
  `{"event":"listen","on":false,"reason":"touch"|"host"|"timeout","chunks","drops"}`
- `{"event":"audio","seq","pcm"}`: 512-sample microphone chunks while listening

## Stall protection

The thresholds come from the factory firmware: every 50 ms, check for a stuck
position while current or load spikes, and require two confirmations. On a stall
the servo holds where it stopped and that direction's range is narrowed until
`reset_limits` or torque off. Our servos get the final target in one command, so
"stuck" is only judged while the planned move is fast enough that the head should
visibly be moving. Protection is enabled on both axes (the factory enables it on
pitch only).

## With the Ohmni workspace

1. Start the companion: `.venv/bin/python companion/voice.py ohmni`. It listens on
   `ws://127.0.0.1:8770` and accepts only pages from the Ohmni origins
   (`OHMNI_MAIN_UI_URL`, default `https://ohmni-yvnd.vercel.app`, plus the local demo
   server `http://127.0.0.1:8765`; add others with `--allow-origin`). Other websites are
   refused with HTTP 403.
2. Open your board in the Ohmni workspace (for Fetch builds, the "Open your board in
   Ohmni" link) and click **Desk robot: off** in the board panel to connect. Chrome may
   ask once to allow access to apps on this device. The choice is remembered, and later
   boards reconnect after they render.
3. The robot narrates the board's tour. That text is generated deterministically, not by an AI,
   and the page highlights each step. Double-tap the head to pause and talk.

The page sends a read-only description of the board (parts, tour, check statuses; no
tokens or links). The companion can only ask for view-only actions and questions; it
cannot change a design, start a build or download anything. Questions go through the
page to Ohmni's existing component tutor, so answers are grounded in your board's records
and use the workspace's shared AI budget. **The companion holds no AI key.** Spoken answers
start with "From your board's records", keep the tutor's "not yet known" items, and
offer one suggested follow-up. If a question names no part, the robot uses the part
selected on screen; if a name matches several parts, it asks which one.

## Voice: double tap to talk

- **Double tap** (two taps within 0.45 s): the robot stops talking, shows a
  listening face and cyan LEDs, and streams its microphone. It only does this after
  a host has talked to it since boot. Double-tap again to cancel. Listening ends
  by itself after 15 s.
- The companion detects the end of speech (energy-based, 0.8 s of silence), then
  transcribes with Whisper (`mlx-community/whisper-base.en-mlx`, local) and
  classifies the text. A phrase that is exactly a narration command maps to
  `resume`, `stop`, `next`, `back`, `repeat` or `more`; anything else is a question.
- Speaker and microphone share one I2S bus, so the robot never talks and listens
  at the same time.

## Hardware verification status

Recorded in `.ai/verification/ST-T01.yaml`. The verified/unverified split:

| Capability | Status |
|---|---|
| USB serial protocol, ping/state/diag | verified on hardware |
| Servo moves (yaw ±20°, pitch 15°, within ~2°) and factory calibration reuse | verified on hardware |
| Stall protection: no false positives in 9 unobstructed moves | verified on hardware |
| Stall protection: detection with a blocked head | **UNKNOWN** (not yet tested) |
| LEDs: register readback matches the colours sent | verified (firmware side); visible output confirmed by user: **UNKNOWN** |
| Face rendering | firmware side verified (sprite allocated); visible output confirmed by user: **UNKNOWN** |
| Speaker streaming (real-time pacing) | verified (timing); audible output confirmed by user: **UNKNOWN** |
| Microphone streaming (3.01 s of audio per 3 s, no gaps) | verified on hardware |
| Head-touch double tap with a real finger | **UNKNOWN** |
| Speech threshold with a real voice | **UNKNOWN** |
