# Stack-chan connector contract v1

Status: proposed wire contract for implementation, not an existing endpoint or
driver. Changes require firmware/browser owners to agree and update tests together.
See [handoff](STACKCHAN_HANDOFF.md) for ownership and [acceptance](STACKCHAN_ACCEPTANCE.md).

## USB framing and lifecycle

- USB CDC serial, host opens at 115200 baud. Actual native-USB throughput is not
  implied by this setting. Verify enumeration and settings on the physical unit.
- UTF-8 JSON, one object per LF-terminated line; accept CRLF. Maximum 1024 bytes
  before newline. Use a bounded receive buffer; discard an overlong frame through
  its next newline and recover. Never log arbitrary incoming text or emit firmware
  debug logs onto this protocol channel. Ignore non-JSON boot chatter until hello.
- Every frame has integer `v: 1`, `type`, and a request `id` (1–64 ASCII characters
  from letters, digits, hyphen and underscore) where shown below. Reject unsupported
  versions, malformed fields, unknown commands and invalid enum values.
- Browser permits one serial reader and writer per connection. User-selected
  connection -> hello -> ready -> state/ping. Show Connected only after a valid
  matching hello response. An occupied port must produce an actionable error.
- Firmware boots into neutral idle with motion disabled until handshake. The
  browser sends hello with a fresh random connection ID (`connection`, same format
  as `id`). Firmware echoes it and resets command sequencing for this connection.
- State and ping frames carry that connection ID and are rejected if it differs.
  For a new connection, clear pending acknowledgements and reject late replies.

Examples are illustrative IDs, not credentials:

```json
{"v":1,"type":"hello","id":"h1","connection":"conn-a"}
{"v":1,"type":"hello","id":"h1","connection":"conn-a","firmware":"0.1.0","capabilities":["face","led","motion"]}
{"v":1,"type":"state","id":"s1","connection":"conn-a","seq":1,"state":"thinking","motion":"none"}
{"v":1,"type":"ack","id":"s1","connection":"conn-a","seq":1}
{"v":1,"type":"ping","id":"p1","connection":"conn-a"}
{"v":1,"type":"pong","id":"p1","connection":"conn-a"}
{"v":1,"type":"error","id":"s2","connection":"conn-a","code":"unsupported_state"}
```

Host `state` fields are exactly `v,type,id,connection,seq,state,motion`. Sequence
is a positive integer <= 2^31-1, increasing per connection; a new connection is
required before wrap. Matching duplicate sequence/content is acknowledged without
replaying motion. Reject an older sequence or conflicting duplicate. Retain the
last accepted command for this comparison. Coalesce queued states to the latest;
do not accumulate gestures while the device is slow.

Allowed states: `idle`, `listening`, `thinking`, `needs_input`, `building`,
`checking`, `speaking`, `ready`, `error`. Allowed motion: `none`, `nod`, `tilt`.
These names select pretested firmware gestures; no raw angle, executable code,
URL, prompt, credentials or project contents cross this link. A device lacking
motion rejects a motion request with `unsupported_capability`; the browser
resends the latest state with `motion: none`. Base implementation requires face;
LED and motion capability flags reflect what was actually initialized.

Proposed timing defaults to implement and test: hello/ack timeout 2 seconds;
one retransmission of the same state ID/sequence; ping every 2 seconds; after
6 seconds without pong, show robot unavailable. Firmware requires a valid
connection ping at least every 6 seconds. On timeout, stop movement, select a
neutral/offline face and invalidate the connection. Use the vendor's tested motor
stop facility; do not blindly drive home on connection loss. Reconnection requires
hello and a fresh current-state snapshot, never replaying an old gesture.

Unknown fields fail validation rather than invoking extra behavior. For invalid
frames with no safely parseable ID, discard without reply. For valid framed
requests return bounded codes: `invalid_frame`, `unsupported_version`,
`unsupported_command`, `unsupported_state`, `unsupported_capability`,
`stale_sequence`, `invalid_connection`, `device_fault`. Rate-limit error replies.
An ack means the device accepted a UI state, **not** that a PCB operation succeeded.

Optional later touch event (only advertise `touch` once tested):

```json
{"v":1,"type":"event","connection":"conn-a","event_id":"touch-1","event":"tap","zone":"top"}
```

Debounce in firmware and deduplicate by connection/event_id in browser. Allowed
zone values: `top`, `left`, `right`. A tap can focus the Talk button or stop
playback; it must never approve generation or a design change. Browser microphone
permission still requires the browser's own interaction/consent flow.

## Application adapter (new work, not a second server)

Suggested public adapter surface to implement:

```text
robot.connect() -> user chooses port; handshake; returns capabilities
robot.setState({state, motion}) -> latest-only queued projection
robot.disconnect() -> close streams/port and clear pending work
robot.subscribe(listener) -> connection/error events; returns unsubscribe
```

Use existing UI controllers to submit transcripts. Add small public hooks where
needed, with lifecycle cleanup and a fake robot/speech adapter for tests. Avoid a
new generic `/voice/turn` that independently creates projects or bypasses checks.
If speech needs server endpoints, define authenticated, bounded transcription/
speech-only routes; decoded text still goes through current plan/assistant APIs.

The operation map below is **existing code**, relative to `API_BASE`. In hosted
connected mode `API_BASE` is `/connected`, so `/api/projects` becomes
`/connected/api/projects`. The standalone local server uses `/api/...` directly.

| Intent | Existing operation / integration point |
| --- | --- |
| Initialize browser workspace | `POST /connected/session`, `connected-session.js` |
| Initial idea / clarification | `POST /api/project-plans`, `{message, parent_id}` through `conversation.js` |
| Explicit plan confirmation | `POST /api/project-plans/{plan}/confirm` through existing confirmation controller |
| Generate saved revision | `POST /api/projects/{project}/revisions/{revision}/run`, `app.js` |
| Observe actual job | `GET /api/jobs/{job}`, existing poller in `app.js` |
| Board answer/change proposal | `POST /api/projects/{project}/revisions/{revision}/assistant` |
| Explicitly apply reviewed proposal | `POST /api/projects/{project}/revisions/{revision}/assistant/{turn}/apply` |
| Ask selected component | `POST /api/projects/{project}/revisions/{revision}/teach`, `{component, question}` |
| Saved conversation | `GET /api/projects/{project}/revisions/{revision}/history` |
| Download | Existing report-generated artifact link under `/api/artifacts/{job}/{name}` |

Payloads above describe intent fields, **not complete copyable HTTP requests**.
Reuse `projectRequest` and existing parsers; they add/validate API, UI and server
identity. Preserve the same-origin cookie, `X-Ohmni-Client` mutation guard, ownership,
limits and stale-revision checks. Use existing links/handlers for downloads rather
than synthesizing filenames or calling an unprotected host. Legacy private viewer
tokens grant no edit rights and must not be upgraded by this connector.

## State projection and conversation context

The adapter retains project/revision/job IDs locally to reject stale updates;
the robot receives only the minimal state above. Capture that context when a
question is submitted. A response from an older revision must not speak as if it
describes the currently selected board. Switching projects/components cancels
pending speech playback and ignores obsolete responses without deleting history.

| Actual application condition | Robot state | Visible UI requirement |
| --- | --- | --- |
| No active operation | idle | Ready to type/talk |
| Microphone actively recording | listening | Recording indicator, Stop/Cancel |
| Waiting for planner/tutor response | thinking | Elapsed time and retained input |
| Plan needs an answer | needs_input | Question and reply input together |
| Build accepted/running | building | Actual job identifier/status |
| Backend explicitly reports check stage | checking | Check stage from backend only |
| Current response audio playing | speaking | Transcript and Stop speaking |
| Current build/package ready for review | ready | Actual findings and unknowns |
| Request/build failed | error | Reason and specific recovery action |

Do not infer checking from a timer. Without finer job events, keep building until
the poller reports a terminal result. A completed job with blocked release or
unmet requirements needs attention, not the download-ready animation. Determine
readiness from the existing result/release projection, not just a status string.

Track connection, speech and engineering state separately. Speaking/listening can
temporarily override an expression without losing the underlying build state;
when audio ends, restore the latest engineering state. Avoid starting recording
while playback is active. Never use a robot acknowledgement as server progress.

An ambiguous HTTP timeout must not trigger a second build automatically. Preserve
the saved revision and consult existing run state before retrying. Cancel recording
means cancel recording, not cancel a server build. Reload/reconnect may resume job
observation but must not submit a transcript, confirm a plan or rebuild by itself.

## Local development integration

Start with `scripts/demo_server.py` for serial UI and ordinary local planning.
It does not expose the connected-only tutor/history services. Test those with
the real gateway behind a same-origin local frontend proxy; the existing
`tests/test_connected_browser.py` `frontend_server` fixture demonstrates the
allowlisted static serving and `/connected/*` forwarding pattern. That fixture
is a test harness, not a shipped development CLI. If a reusable local launcher is
needed, the integrator should implement it with isolated storage and no production
fallback. Keep `OHMNI_MAIN_UI_URL` aligned with that local frontend origin.

Add new modules to `scripts/demo_server.py`'s static allowlist as needed; check
the agent asset allowlist if using its legacy viewer. Do not add wildcard serving.
Test main bootstrap before mounting the connector so API_BASE and session identity
are established. A Vercel preview may proxy production: it is not a local test.
