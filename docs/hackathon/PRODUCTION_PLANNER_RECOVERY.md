# Production planner recovery on October 16

Owner authorized paid tests, production repair and updating main on October 16, 2026.

The production Anthropic credential returned HTTP 401 AuthenticationError while
the local credential worked. Both the supported demo prompt and the public
smell-identification prompt failed in production. The backend classified vendor
failures as invalid plans, and the frontend always called the failure an outage.

The failing Fly secret was replaced using the locally validated credential,
without putting its value in source, logs or command arguments. Production then
returned a supported plan and a clarification for the smell request. The latter
requires an unsupported odor sensor; it must not be treated as a buildable smell
detector or silently replaced with a temperature/humidity board.

## Code changes

- A provider request failure has its own typed exception, preserving the existing
  StructuredGenerationError base for other callers.
- Planning returns HTTP 503 for provider failure and HTTP 502 for invalid model
  schema output; malformed input and rejected source attribution remain HTTP 400.
- Provider failure logs contain only an owned category such as provider_auth.
  Raw vendor responses, keys, prompts and payloads are not logged.
- Recovery displays the actual safe error message and preserves the request.

## Validation

- Paid local smell prompt: clarification returned, no project confirmed.
- Paid local supported prompt: planning, confirmation, real engineering and
  hash-checked download passed; one provider request, no automatic retries.
- Production before rotation: both prompts rejected; direct bounded provider
  diagnosis confirmed HTTP 401.
- Production after rotation: both planning requests returned HTTP 200; a real
  supported test build completed and its ZIP downloaded with 20 entries and
  valid CRCs. This does not establish firmware or hardware bench operation.
- Focused Python tests: 82 passed, 1 deselected. Frontend tests: 1131 passed.
- Full fast gate after updating the fault harness's expected provider response:
  2743 passed, 101 skipped, 65 deselected. Offline fault harness regression: 3 passed.

Health's free_text flag means a provider is configured, not that credentials
have been tested successfully. After credential changes, perform a bounded live
planning rehearsal rather than inferring success from health alone.


## Production flow and beginner recovery (2026-10-16)

The live flow was exercised through the Vercel UI with a plain-language room
sensor idea, server-owned plan confirmation, real KiCad generation and the
complete build-package download. The ZIP contained 20 CRC-valid entries; all nine
manufacturing file hashes matched the recorded release. A manufacturing-review
release still had a violated hand-soldering preference, which motivated the
following recovery changes:

- A result summary prominently separates unmet choices, unverified items and
  manufacturing readiness. Firmware, assembly and bench work remain explicit.
- Chat is available beside a failed saved-revision build, as well as beside a
  completed board. Suggested prompts prepare editable messages without sending
  model requests automatically.
- The assistant receives report-owned per-choice outcomes and allowlisted failure
  explanations. It can ask plain-language tradeoff questions while preserving the
  saved brief. Only a reviewed proposal can create a new revision; old results do
  not become evidence for the new revision.
- Requirement answers group unmet, unknown and met records; long check ladders
  are presented as separate records rather than one dense paragraph.

Regression commands:

```sh
node --test apps/web/tests/*.test.mjs
.venv/bin/python -m pytest tests/test_conversation.py tests/test_conversation_api.py tests/test_project_assistant.py tests/test_project_assistant_api.py
.venv/bin/python -m pytest -m integration tests/test_build_chat_browser.py
.venv/bin/python scripts/verify.py fast
```

Failed-build UI is exercised with controlled job responses locally; do not break
production tools to test an error. The paid live follow-up asked about the assembly
conflict, then accepted reflow assembly while retaining temperature and humidity
sensing. The reviewed diff changed only `hand_solderable_preferred`. Revision 2
ran fresh checks and its downloaded 20-entry ZIP passed CRC and all nine
manufacturing hashes. Its report contained zero VIOLATED choices and retained
13 UNKNOWN choices/limits. UNKNOWN was not treated as a defect automatically
cured by another PCB build.

The live walkthrough also prompted small presentation fixes: opening a saved
project shows a loading state instead of an unrelated default plan; saving and
starting a run name the active operation; the revision count refreshes after
opening a project; chat puts clarification questions before collapsed supporting
records. These changes do not alter the engineering or release gates.
