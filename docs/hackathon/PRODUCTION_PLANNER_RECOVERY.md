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
