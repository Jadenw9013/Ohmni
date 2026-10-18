# Stack-chan desk tutor for Ohmni boards

**Status: ST-T01 to ST-T04 APPROVED by a human** (`.ai/approvals/STACKCHAN-TUTOR-1.yaml`,
repository placement `tools/stackchan`). **ST-T05 (phase 2 change requests) remains
PROPOSED** and is not authorized.

## Goal

A user prompts Ohmni through Fetch.ai (ASI:One). The finished board opens in the
Ohmni workspace. An M5Stack StackChan desk robot next to the screen explains the
board aloud, answers questions like a teacher, and can steer the workspace view
(focus, isolate, trace a part). It can also *ask* for a design change, which the
user confirms on screen and which goes through Ohmni's existing revision and
verification pipeline.

The robot is a narrator and a remote control. **It never creates evidence,
verdicts or check results, and it can never change a design by voice alone.**

## Pipeline

```
ASI:One prompt ─► Fetch agent (Fly) ─ plan → CONFIRM → ProjectPipeline (ERC, routing, DRC)
                        │ reply: private workspace link
                        ▼
      Ohmni main workspace (connected session; app.js + BoardView + tour + tutor)
                        │ opt-in WebSocket ws://127.0.0.1:8770 (Origin-checked)
                        ▼
      Stack-chan companion (Python, user's computer)
                        │ USB serial, line-delimited JSON
                        ▼
      Stack-chan robot (custom firmware: speech, face, head, touch, microphone)
```

1. **Build (existing).** ASI:One → Fetch agent → `ChatBridge` → `ProjectPipeline`.
   The reply links to the connected main workspace (`connected.py`).
2. **Board context (new, ST-T02).** When a board renders (`setupBoard`), the
   workspace optionally connects to the local companion and sends a read-only
   context: `job_id`, project and revision ids, `experience.components[]` (ref,
   name, purpose, system), `experience.tour.steps[]` and the current selection.
   With no companion running, nothing changes.
3. **Narration (new, ST-T03).** The companion narrates `experience.tour.steps[]`.
   That text is produced deterministically
   (`narration_source: deterministic_projection_not_a_language_model`). For each
   step it asks the page to highlight that step's `component_refs` and `net_names`.
4. **Questions (new, ST-T03).** Double-tapping the robot's head pauses narration and
   records speech, which is transcribed locally with Whisper. Questions go to the
   page, which calls the existing per-revision `teach` route (`component-tutor.js`
   → `/api/projects/{p}/revisions/{r}/teach`). The answer is grounded in the
   recorded component, connections, requirements and checks, and it returns
   `unknowns`. The robot speaks the answer and offers the returned `next_questions`.
   The companion holds no provider key; usage counts against the existing shared
   AI budget.
5. **View commands (new, ST-T02/ST-T04).** Spoken commands map to a closed set of
   view-only operations that the page carries out with existing `BoardView` paths.
6. **Change requests (new, phase 2, ST-T05).** "Swap", "add" and "what if" requests
   are routed to the existing project assistant. A real change appears as an
   assistant `change` turn with its before/after diff. Only an on-screen click
   applies it and starts the rebuild (existing `apply` → `run`). The robot then
   narrates a deterministic old-vs-new comparison. "What if" questions are
   answered as labelled explanations ("not a checked design") and change nothing.

## Command set (page side, view-only)

| Command | Page action (existing code path) |
|---|---|
| `focus {ref}` | `boardView.select` → `setHighlight({refs})` → `renderSelection` → `focus(ref)`, the same order as the systems list (app.js), avoiding `CircuitLessons.select` re-entry |
| `isolate {ref \| null}` | `boardView.setOptions({isolate})`. One part only; isolating several needs a renderer change (ST-T05 optional) |
| `trace {ref}` | `setHighlight({nets: component net_names})` + `setOptions({animateFlow: true})` |
| `frame` / `camera {top\|back\|front}` | `frame()` / `setCameraPreset()` |
| `tour {index}` | `showTourStep(index)` |
| `ask {ref?, question}` | existing `teach` request; the answer is shown in the page tutor and returned to the companion |
| `propose_change {text}` (phase 2) | existing assistant `ask`; never `apply` |

Events from the page to the companion: `context`, `selected {ref}`, `answer`,
`assistant_turn`, `run_status`, `revision_changed`.

## Security and privacy

- **Loopback only.** The companion listens on `127.0.0.1` only. It rejects WebSocket
  connections whose `Origin` is not the configured Ohmni origin
  (`OHMNI_MAIN_UI_URL`, default `https://ohmni-yvnd.vercel.app`) or the local demo
  origin. Without this check, any website the user visits could connect to localhost.
- **Closed command set.** The page accepts only the commands above, validates refs
  against the rendered board, and carries out no mutation on behalf of the
  companion. Changes still need the existing `X-Ohmni-Client: main-ui` request,
  made by the page after a user click.
- **Local data.** Board context stays on the user's computer. Microphone audio
  is transcribed locally and not stored. Only the question text reaches the
  existing teach route.
- **Opt-in.** The connection is attempted only when enabled (for example a
  workspace toggle) and fails silently.

## Repository placement (decision for the approver)

The robot code currently lives outside this repository: PlatformIO firmware
(Arduino-ESP32 2.0.17, M5Unified 0.2.26) and a Python bridge with voice
(macOS `say`, `mlx-whisper`). The proposal is to add it under `tools/stackchan/`
(ST-T01) so that hackathon work is visible and reviewable. It would have no
runtime dependency in either direction: Ohmni must not import it, and its
packages stay out of `pyproject.toml` extras unless approved.

## Constraints and honest limits

- Fetch-built boards live on the remote agent's store, not the local demo server
  (`ProjectWorkspaceLock`). The robot therefore reaches them through the browser
  page, never directly.
- There is no single-part swap API. Changes are `SynthesisBrief` edits (sensor
  slots, LED and button counts, SPI memory, programming header, board size,
  archetype options such as the voice recorder) and always trigger a full
  pipeline run, which takes minutes.
- `teach` needs a component. The companion picks one from names in the question,
  then from the current selection, otherwise it asks the user which part.
- Browser support for `wss`/`ws` to loopback from an `https` page varies (Chrome's
  Private Network Access rules, Safari mixed-content rules). It must be validated
  per browser. Chrome is the target.
- Robot hardware status: custom firmware v0.3.0 is flashed and partly verified
  (servos, LEDs readback, speaker streaming, microphone streaming, stall false
  positives). Not yet verified: touch double-tap with a real finger, speech
  threshold with a real voice, a stall with a blocked head.

## Proposed tasks

| ID | Title | Depends on |
|---|---|---|
| ST-T01 | Add the Stack-chan firmware and companion under `tools/stackchan/` with host tests | — |
| ST-T02 | Opt-in loopback robot channel in the main workspace (context out, view-only commands in) | — |
| ST-T03 | Companion: tour narration and grounded questions through the page's teach route | ST-T01, ST-T02 |
| ST-T04 | Spoken view commands with component-name resolution | ST-T03 |
| ST-T05 | Phase 2: spoken change requests through the assistant, on-screen confirmation, old-vs-new narration | ST-T04 |

### Acceptance criteria and verification

**ST-T01** (priority 90). Verification: `fast`, tools host tests, hardware session record.
- Firmware (PlatformIO, pinned platform and libraries, factory partition layout) and
  the Python companion live under `tools/stackchan/`, with a README covering
  flashing, factory restore and the serial protocol.
- No runtime dependency in either direction: `src/ohmni` does not import it and
  `pyproject.toml` extras are unchanged unless separately approved.
- Host tests cover serial framing, intent classification and endpointing without hardware.
- Hardware verification is recorded per capability (servos, stall, LEDs, speaker,
  microphone, touch). Untested capabilities are listed as UNKNOWN.

**ST-T02** (priority 85). Verification: `fast`, web tests, browser.
- When enabled, the workspace connects to loopback (fixed port) after `setupBoard`
  and sends a read-only context: job, project and revision ids, components, tour
  steps and selection. With no companion it fails silently and behavior is unchanged.
- The page accepts only the closed view-only command set and validates refs
  against the rendered board. Unknown commands and refs are rejected.
- Focus follows the existing `select → setHighlight → renderSelection` path without
  `CircuitLessons` re-entry. No command performs a mutation.
- Existing `apps/web` tests keep passing. New tests cover context emission,
  command validation, rejection and the no-companion case. Home routing tests
  are unaffected.

**ST-T03** (priority 80; depends on ST-T01, ST-T02). Verification: `fast`, tools
host tests, browser, hardware session record, live tutor.
- The companion checks the WebSocket `Origin` against the configured Ohmni origin
  and the local demo origin, and refuses others.
- Narration speaks `experience.tour.steps` text verbatim and highlights each step's
  `component_refs` and `net_names`. A double tap pauses it immediately, and
  narration resumes on command.
- Questions go to the page, which uses the existing per-revision teach route. The
  companion holds no provider key. `unknowns` returned by teach are spoken, not dropped.
- The robot never states that a check passed unless the board context records it.
  Spoken answers are labelled as explanations.

**ST-T04** (priority 70; depends on ST-T03). Verification: `fast`, tools host tests,
browser, hardware session record.
- Phrases such as "show me the regulator", "isolate it", "what does it connect to",
  "zoom out" and "next" map to the closed command set, using refs and names from
  the board context.
- Ambiguous or unknown part names lead to a clarifying question, never a guess.
- Selecting a part on screen makes the robot name it and give its purpose from the context.

**ST-T05** (priority 50; depends on ST-T04; phase 2). Verification: `fast`, web tests,
browser, native, hardware session record.
- Spoken change requests go to the existing project assistant. Only an on-screen
  user action applies a change turn and starts the existing run.
- "What if" questions are answered as labelled explanations and change nothing.
- After a new revision completes, the robot narrates a deterministic comparison of
  components, nets and requirement outcomes between the two revisions.
- Optional: isolating several parts at once in the renderer, with tests that keep
  the mesh-position invariants.

All tasks: independent review required for COMPLETE; if unavailable, only VERIFIED.

## Non-goals

- No voice confirmation of design changes, purchases or downloads.
- No new engineering verdicts, evidence or supplier facts from the robot or the companion.
- No exposure beyond loopback. No change to Fetch agent behavior or quotas.
- No firmware generation for user boards. No claim of physical bench validation.

## To approve

A human reviews this plan and tells an agent which tasks to approve (for example
"approve ST-T01 to ST-T04") and which repository-placement option to use. The
agent then:

1. Records that instruction in `.ai/approvals/STACKCHAN-TUTOR-1.yaml`.
2. Adds scope `STACKCHAN-TUTOR-1` (`approved_by: human`, `approval_evidence`
   pointing to that file) and the approved tasks, as `APPROVED`/`READY`, to
   `.ai/tasks.yaml`.
3. Adds the scope id to both allowlists in
   `tests/test_ai_workflow.py::test_repository_product_scope_matches_human_approval`.
4. Refreshes `.ai/state.yaml` and runs `python scripts/ai_state.py validate` and
   `python scripts/verify.py workflow`.
