# Stack-chan developer handoff

Status: implementation handoff; no robot firmware, USB connector or speech
connector is implemented by this documentation change. Researched 2026-10-17.
Code baseline: `c3038a47` (main after PR #94). Fetch before starting.

The owner requested this handoff for a teammate using Claude after choosing a
USB-connected expressive robot with laptop audio. This document defines that
bounded deliverable; it does not claim hardware qualification or authorize
unrelated PCB-engine changes. Implementation assignments and status belong in
the existing `.ai` workflow, not a second task ledger in this guide.

Read together:

- [Connector contract](STACKCHAN_CONNECTOR_CONTRACT.md): proposed messages,
  application integration and failure behavior.
- [Acceptance and troubleshooting](STACKCHAN_ACCEPTANCE.md): commands, physical
  checks, full-flow script and evidence to hand back.
- [Team setup](../TEAM_SETUP.md), [engineering tools](../LOCAL_ENGINEERING_SETUP.md),
  [AI handoff](../AI_TEAMMATE_HANDOFF.md), and [assistant coordination](ASSISTANT_WORKFLOW.md).
- [Unified Fetch workspace](UNIFIED_FETCH_WORKSPACE.md) and
  [current PCB limitations](PCB_PRODUCT_AUDIT.md).

## Intended experience

1. Open Ohmni on the computer physically connected to Stack-chan. Click Connect
   robot and select its USB port. Show separate robot/backend/microphone status.
2. Click Talk, describe an idea, review the transcript and send it. Typing remains
   available. Capture is push-to-talk; no hidden continuous recording.
3. Ohmni asks necessary questions and displays actionable replies. The robot
   reflects listening, thinking or waiting for the user. Unsupported requirements
   remain explicit until the user accepts a different supported design.
4. Review the actual plan and click Generate. Speech alone cannot confirm a
   build, apply a design change or order anything.
5. Show actual job state and elapsed time. The robot follows those events; do
   not invent progress percentages or interpret an HTTP acknowledgement as success.
6. Display the generated board. Select a component, then ask about that component.
   Read the explanation aloud through the laptop while the robot animates.
7. Request a supported change through Board chat. Review, explicitly save/apply,
   and generate the new revision using the established UI controls.
8. Download the checked package. Say files are ready for review; do not say the
   device has been physically built, programmed or tested.

If the robot disconnects, the website, project and server build remain usable.
The voice interface is an alternative input method for existing project actions,
not a second planner, project database or build engine.

## Responsibilities and ownership

Assign a named person to each row before concurrent work. One person can own
multiple rows. Separate worktrees/clones and output directories are required.

| Owner | Deliverable | Suggested new files / existing integration points |
| --- | --- | --- |
| Hardware teammate / Claude | Reproducible firmware build, face, bounded motion, LEDs, USB protocol, watchdog, hardware evidence | New `hardware/stackchan/`; optional touch events after core link works |
| Browser connector owner | Serial lifecycle, framing, acknowledgements, reconnect UI, robot-state projection | New `apps/web/stackchan-serial.js`, `stackchan-controller.js`, focused Node tests |
| Voice/UI owner | Push-to-talk, editable transcript, send/cancel, spoken answers, accessible fallback | New `apps/web/voice-controller.js`; integrate existing conversation, board chat and tutor controllers |
| Integrator | Shared contract, frontend lifecycle hooks, authenticated speech service if needed, dependency/config changes, combined acceptance | `apps/web/app.js`, `main.js`, static allowlists, backend gateway and `.ai` records |
| Reviewer | Reproduce fresh clone, errors, ownership isolation, real hardware and final ZIP checks | Evidence/report; no claims of independent review by the implementer |

Proposed new paths above do not exist yet. The integrator owns shared-file edits;
the firmware teammate can finish firmware and a protocol test harness without
editing the PCB engine, production configuration or another person's UI files.

## What already exists — reuse it

PR #94 connected Fetch projects to the main UI. Do not build a second viewer or
invent a new link token. ASI `OPEN` returns a one-use connection link; the main
site exchanges it for an HttpOnly browser session and preserves project access.
Existing board/component conversations, revisions, checks and downloads share
the agent's project store. Details: [unified workspace](UNIFIED_FETCH_WORKSPACE.md).

| Concern | Current source |
| --- | --- |
| Browser connection/session bootstrap | `apps/web/main.js`, `connected-session.js` |
| HTTP identity checks and request helpers | `apps/web/client-contract.js`, `project-contract.js` |
| Initial idea, replies, reviewed plan confirmation | `apps/web/conversation.js` |
| Saved projects, settings and revisions | `apps/web/project-workbench.js` |
| Board questions and reviewed changes | `apps/web/project-assistant.js` |
| Selected-component teaching | `apps/web/component-tutor.js` |
| Start/poll job, render result, artifact links | `apps/web/app.js` |
| Connected route ownership and durable chat | `src/ohmni/integrations/fetch_ai/connected.py` |
| ASI transport/session, budget and deduplication | `src/ohmni/integrations/fetch_ai/bridge.py`, `agent.py`, `http.py` |
| Existing generation/application HTTP handlers | `scripts/demo_server.py` |

Use controller methods or small public hooks, not DOM scraping, fabricated clicks
or direct calls to private `bridge._operate`. The latter bypasses the surrounding
transport/session safeguards. Browser calls use the connected gateway; never
expose its loopback server or weaken route authorization to make voice work.

## Hardware setup on the teammate's computer

1. Verify the physical SKU: this guide targets official K151/K151-R. A community
   Stack-chan assembled from other M5 parts may require different drivers,
   pin assignments and motor limits. Record SKU, OS and current firmware version.
2. Use a USB **data** cable connected to the base port. M5Stack recommends this
   port to reduce accidents from head movement. Keep the cable clear of rotation.
   Place the unit upright; do not force powered motors by hand.
3. Record how to restore factory firmware using M5Burner before replacing it.
   Preserve settings/calibration where supported; do not assume a firmware restore
   also restores pairing or all user data. Never flash an unidentified board.
4. Follow the official Arduino setup: select `M5CoreS3`, install `M5StackChan`
   and its dependencies. Official audio examples require M5Stack board manager
   >= 3.2.2 and M5Unified >= 0.2.11. These are documented minimums, **not a tested
   Ohmni toolchain**. Record and pin the exact successful versions in the firmware
   build configuration. Arduino CLI or PlatformIO is fine once a repeatable build
   is demonstrated; do not guess PlatformIO package versions from Arduino numbers.
5. Enter download mode as described in the product guide: hold RST about three
   seconds until its indicator turns green, then release. Upload a minimal
   display/serial sketch before enabling motors. Close serial monitors before
   opening the port from Chrome. Configure USB CDC for the chosen toolchain and
   confirm that the application enumerates after reboot, not just the bootloader.
6. Prove display and LEDs, then home and gently exercise the motors with the
   official library. Keep vertical movement within M5Stack's recommended 5–85°;
   use a narrower tested range initially. Bound horizontal movement to avoid
   winding the USB cable even though the hardware supports continuous rotation.
7. Implement the versioned USB contract, then test real disconnect/reconnect and
   watchdog behavior. Save build/flash commands in `hardware/stackchan/README.md`.

Do not promise factory animations survive custom firmware: provide a small set
of our own expressions using the supported display APIs. Do not depend on factory
app login, Wi-Fi onboarding, XiaoZhi chat or Qoder tasks for the initial connector.
M5Stack publishes both factory source and an Arduino board-support library.

## Audio, connectivity and scope decisions

- First version: laptop microphone and laptop speaker. The robot USB protocol
  carries states/events, not PCM audio. Robot microphone/speaker streaming is a
  later feature with separate buffering, playback and interruption tests.
- Choose and document one speech adapter before implementation. Browser-native
  speech support varies; feature-detect it and retain text entry. If a hosted
  transcription/TTS provider is chosen, keep keys server-side, define recording
  length/body limits and timeouts, and use existing ownership/quota protections.
  There is currently no implemented Ohmni speech endpoint to call.
- A proposed first capture limit is 30 seconds per utterance. Release microphone
  tracks on stop, cancel, error and navigation. Stop playback when a new recording
  begins. Do not send audio before the user explicitly starts capture; disclose
  the selected processing provider before enabling it.
- Desktop Chrome with Web Serial is the initial supported browser. Require HTTPS
  or localhost, feature detection and a user gesture for port selection. Browser
  permissions cannot be silently granted. Other browsers keep normal text/UI use.
- The computer running the browser must be attached to the robot. Our production
  server cannot open the teammate's USB port. Cloud AI and generation still need
  Internet even when the robot connection is USB.
- ASI remains an actual Fetch entry point. Reusing Ohmni's connected browser
  APIs does not mean every spoken turn traveled through ASI/ACP. To demonstrate
  that path, begin in ASI and open its project in Ohmni through `OPEN`.
- Camera, NFC, robot-native audio, wireless control, wake words, arbitrary part
  substitution and automatic physical PCB programming are outside this first
  deliverable. Robot motor control and PCB electrical verification stay separate.

## Suggested implementation order

These are work packages, not completion claims or alternate `.ai` task IDs.

1. Hardware proof: display/LED/motion/USB echo; record toolchain and recovery path.
2. Freeze contract v1: firmware + browser parser agree; fake serial tests pass.
3. Connect real application state to robot expressions; verify physical unplug.
4. Add voice-to-editable-text and spoken replies using current conversation hooks.
5. Rehearse a fresh board and a reviewed revision, then download both packages.
6. Rehearse ASI `OPEN` -> same main workspace -> selected-part question/change.

If audio takes longer, ship text + truthful robot progress first and report voice
as unfinished. If motion fails, disable motion and retain face/LED operation.
Never substitute a saved board while presenting it as a new generation.

## Copy into Claude on the hardware teammate's computer

```text
Work in my local Ohmni clone. The owner selected the USB Stack-chan companion
design in docs/hackathon/STACKCHAN_HANDOFF.md. Start by reading AGENTS.md,
docs/AI_TEAMMATE_HANDOFF.md, that handoff, its connector contract and acceptance
guide. Inspect Git status, fetch origin and branch from current origin/main in
a clean checkout; preserve other work. Do not merge, push main or deploy.

My assignment is hardware firmware plus the USB connector contract/harness.
Own hardware/stackchan/ and its tests. Coordinate with the integrator before
editing apps/web, dependencies, backend routes or the shared .ai ledger. Record
this bounded assignment under the existing workflow; don't replace another
active task or infer approval for unrelated backlog work.

Verify my actual Stack-chan SKU and serial port, record the factory recovery
procedure, then use M5Stack's official driver library. Implement contract v1,
bounded gestures, watchdog, acknowledgements, capability/version handshake and
safe reconnect. Pin the toolchain that actually compiles and runs. The first
version uses laptop audio; do not rebuild the vendor cloud stack.

Build and test a host harness before the UI connector is ready. A simulated
device test is not hardware evidence. Do not invent successful flashes or motion.
Keep credentials and private links out of code, logs and this chat. Use local
tests first; obey the owner's existing authorization for external actions and
paid calls, and coordinate any missing runtime access with the integrator.

Deliver reproducible build/flash/harness commands, exact dependency versions,
tested SKU/OS, protocol examples, real hardware results, remaining failures and
the implementation commit/diff. Use the acceptance checklist; label every
unexecuted check NOT RUN. Keep the public contract in sync with implementation.
```

## Primary research references

Reviewed 2026-10-17; teammate must verify instructions against their exact unit.

- [M5Stack product, ports, specs, motor limits and download mode](https://docs.m5stack.com/en/StackChan)
- [Official Arduino compile/upload guide](https://docs.m5stack.com/en/arduino/stackchan/program)
- [M5StackChan board-support library](https://github.com/m5stack/StackChan-BSP)
- [Factory firmware/app/server source](https://github.com/m5stack/StackChan)
- [Servo API](https://docs.m5stack.com/en/arduino/stackchan/servo)
- [Microphone example](https://docs.m5stack.com/en/arduino/stackchan/mic): example
  switches microphone/speaker operation; simultaneous audio is not qualified here.
- [Speaker API and build prerequisites](https://docs.m5stack.com/en/arduino/stackchan/speaker)
- [Chrome Web Serial](https://developer.chrome.com/docs/capabilities/serial)
- [Qoder alternative](https://docs.m5stack.com/en/guide/stackchan/qoder): a separate
  firmware/network workflow, not the chosen Ohmni connector.
