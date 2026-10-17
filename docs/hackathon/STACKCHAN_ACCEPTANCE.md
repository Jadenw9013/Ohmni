# Stack-chan acceptance and troubleshooting

These are required future implementation checks, **not recorded passes**.
Read the [handoff](STACKCHAN_HANDOFF.md) and [contract](STACKCHAN_CONNECTOR_CONTRACT.md).
Use a separate clone/worktree, venv, output directory and test workspace per owner.

## Existing baseline checks

From the repository root, using the clone's activated Python environment:

```sh
python scripts/ai_state.py validate
python scripts/verify.py workflow
npm --prefix apps/web ci
npm --prefix apps/web test
python -m pytest -q tests/test_connected_workspace.py tests/test_fetch_bridge.py
```

For connected browser acceptance install the existing optional dependencies first:

```sh
python -m pip install -e '.[dev,fetch,browser]'
python -m playwright install chromium
python -m pytest -q tests/test_connected_browser.py
```

Set `OHMNI_REQUIRE_BROWSER=1` in the environment when a browser pass is required;
otherwise an unavailable browser can be reported as a skip. Check output rather
than treating an exit code with skips as full coverage. The existing connected
browser test uses fake providers/jobs and saved geometry: it proves UI and session
behavior, not a new physical-engine build or real robot behavior.

For a local full generation setup, follow [engineering setup](../LOCAL_ENGINEERING_SETUP.md):

```sh
python -m ohmni doctor
python scripts/demo_server.py --output-root out/stackchan-local
```

Open `http://127.0.0.1:8765/#workspace` in desktop Chrome. `doctor` can exit zero
with missing tools: inspect its KiCad/library/ngspice results. Keep this server
loopback-only. Connected tutor/history need the gateway/proxy setup described in
the connector contract; standalone demo-server success does not prove them.

No hardware test/flash command exists in this documentation change. The hardware
owner must deliver the exact pinned build, flash and harness commands alongside
their implementation. Do not pretend the command names below already exist.

## Test matrix to implement

| Layer | Cases | Required result |
| --- | --- | --- |
| Firmware/host protocol | Split frames, joined frames, CRLF, boot chatter, invalid UTF-8/JSON, >1024-byte frame, unknown version/command | Bounded memory; invalid input never moves motors; next valid hello/frame recovers |
| Ordering | Duplicate state, old sequence, conflicting duplicate, old connection, delayed ack | No duplicate gesture; stale updates ignored/rejected |
| Lifecycle | Denied picker, occupied port, unsupported browser, reset, unplug, missing pong, reconnect | Clear status; no frozen UI; no automatic build or gesture replay |
| Motion | Neutral boot, range limits, repeated gestures, watchdog expiry | No cable winding/extreme positions; stop on lost heartbeat |
| Voice | Permission denied, silence, noise, corrected transcript, 30-second limit, cancel, network/provider failure | Clear fallback; retained text; tracks released; no implicit confirmation |
| Application | Late response after project/revision/component switch; stale plan; repeated Generate click | Correct context; no cross-project speech, duplicate mutation or build |
| Security | Another browser's project/job; expired/used connection link; old viewer token; cross-origin mutation | Existing access restrictions preserved |
| Release | Build failure, blocked release, unknown checks, expired/stale artifact | No false ready/success claim; valid recovery and accurate report |

Use fake serial streams and fake speech adapters for repeatable automated tests;
inject fake clocks for heartbeat/timeout cases. Keep meaningful adapter tests
under `apps/web/tests/` so the existing npm command runs them. Test speech gateway
ownership/limits in Python if new backend routes are added. Physical motion and
microphone permissions also require the following real-browser checklist.

## Physical acceptance on the actual unit

- Record SKU, OS, Chrome version, toolchain/library versions, firmware commit,
  browser/backend commits, and tested USB port/cable.
- Compile and flash from a fresh checkout with the documented command. Reboot;
  the application serial port must enumerate. Test factory recovery separately
  or explicitly mark recovery untested; preserve existing settings first.
- Connect from Chrome. Inspect the matching hello/version/capabilities. Connection
  failure must not leave a false green indicator.
- Exercise each implemented face and LED state; exercise only bounded nod/tilt
  gestures. Film or record observations without credentials/private link fragments.
- Stop host heartbeat while power remains. Within the documented watchdog interval,
  motion stops and the connection becomes unavailable. Reconnect restores current
  state without replaying earlier gestures.
- Unplug during a real or explicitly labeled test job. The website still tracks
  the server job. Replug, select port if necessary, and resynchronize.
- Try a second tab/serial monitor occupying the port. Give an actionable busy-port
  message; no endless reconnect loop. No automatic reopening after user Disconnect.

## Full-flow acceptance script

Use localhost/isolated services first. Use existing owner authorization for paid
or production work; absent that authorization, record the missing access and do
the remaining offline/hardware checks. Never paste keys or private URLs into evidence.

1. Start a fresh project. Speak: **“I want a USB-powered board with two buttons
   and one indicator light.”** Check the transcript, correct it if necessary, and
   Send. Record what reached the planner; no build may exist before confirmation.
2. Review the proposed parts, power and programming limitations. Click Generate
   once. Verify a single saved revision/job and truthful waiting/building states.
3. While building, disconnect the robot. Verify the server job continues and text
   controls remain usable. Reconnect and check current-state recovery.
4. Wait for the actual result. Confirm rendered board, report and saved brief all
   refer to that job/revision. Do not accept a cached/saved demo replacement.
5. Select a component; ask **“What does this part do?”** Check that the tutor uses
   that reference and revision, shows an AI-explanation label and reads the current
   response. Stop speaking, then select another component; old responses must not
   be spoken as answers about the new selection.
6. Ask Board chat **“Add one more button.”** Review the proposal and explicitly
   apply/save and generate. Check that the new brief has three buttons and the old
   revision and its artifacts remain unchanged. If this configuration cannot pass
   current generation, retain/report the real failure rather than fake success.
7. Download via the actual browser control. Open the ZIP, verify it is not an HTML
   error page, parse its report/confirmed brief/revision receipt, check job/revision
   consistency, and hash fabrication files against their manifest. Inspect native
   DRC/unrouted findings and preserved UNKNOWN/VIOLATED outcomes. Do not rely on a
   fixed ZIP entry count; use the release manifest for this build.
8. Refresh/reopen the connected workspace. Verify saved project and board/component
   history, then recover the selected build without generating again.
9. Start a separate **“USB-C voice-activated diary recorder”** request. Check that
   audio limitations and the reply input are visible. Decline the simpler controller:
   no build. Explicitly accept the controller without recording functionality:
   verify a clearly renamed supported plan and a fresh confirmation opportunity.
10. For ASI acceptance, start a project through the actual selected Ohmni agent,
    confirm there, send `OPEN`, and claim the link in the same demo browser. Verify
    the same project in main UI. Make a reviewed change there, then send `STATUS`
    in ASI and verify it reflects the saved revision. A browser-only test is not
    evidence that speech traveled through ASI or that ACP was exercised.

After implementation, run `python scripts/verify.py fast`, relevant frontend and
connected browser tests, and native generation tests when generation behavior or
contracts changed. Report actual commands/counts/skips. Documentation-only changes
do not establish any runtime or physical acceptance result.

## Troubleshooting

| Symptom | Next action |
| --- | --- |
| No USB port | Check data cable/base port, download-mode procedure and application USB CDC configuration; record OS enumeration before guessing drivers |
| Port busy | Close Arduino/CLI serial monitor and other connected tabs, then retry manually |
| `navigator.serial` absent | Use supported desktop Chrome on HTTPS/localhost; keep typed flow available |
| Robot connects but stays idle | Inspect hello/capability mismatch, LF framing and application events; ack alone is not state/progress evidence |
| Random JSON failures | Separate debug logging from protocol, handle fragmented reads and bound/reset parser buffer |
| Motors strain or cable twists | Stop motion immediately; inspect configuration/clearance and reduce tested gesture range; do not force by hand |
| Voice duplicates requests | Submit final edited transcript once with a pending-operation guard; never submit interim recognition results |
| Robot listens while audio plays | Stop playback before capture; restore previous build expression after audio finishes |
| Tutor missing locally | Standalone server is not connected mode; use isolated gateway + same-origin proxy, not a production URL fallback |
| HTTP 403 / stale server identity | Reconnect using existing workspace flow and refresh health identity; never disable ownership/CSRF checks |
| Build has no new updates | Check current job and server response; show last update/error. Do not start another build just because polling failed |
| Cloud fails, robot still smiles | Show backend error separately from robot connectivity; stop stale speaking/celebration |

## Teammate evidence to return

```text
Implementation commit / branch:
Firmware commit and pinned toolchain:
Physical SKU / OS / Chrome / cable-port:
Build, flash and protocol-harness commands:
Automated tests (counts, skips, logs):
Physical checks (PASS / FAIL / NOT RUN for each):
Fresh project/revision/job IDs (no private access links):
Downloaded package hash and manifest comparison:
Native check results and remaining UNKNOWN/VIOLATED:
ASI path exercised? Which actual steps:
Known limitations / next exact action:
```

Keep raw evidence in an ignored local output directory (for example
`out/stackchan-acceptance/`). Commit only a sanitized summary. Never commit
microphone recordings, session cookies, API keys, connection links or seed values.
