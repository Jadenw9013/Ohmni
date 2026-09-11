# LLM Integration Plan — Ohmni

## Context

The `DesignOrchestrator` in `src/ohmni/generation/orchestrator.py` is fully
implemented. It calls `self.provider.generate_structured(...)` at four points:
requirements interpretation, architecture proposal, circuit proposal, and
repair. The `LlmProvider` Protocol is defined in `src/ohmni/adapters/__init__.py`.

**What is missing:** a concrete implementation of `LlmProvider` that calls a
real model API. The demo currently uses `RecordingLlmProvider` (a scripted fake
in `src/ohmni/adapters/fakes.py`) that replays pre-baked responses for the
frozen ESP32/BME280 fixture.

The goal is to wire a real Anthropic provider so the hosted demo can accept
arbitrary user design requests and generate real circuit proposals.

---

## Work Items

### 1. `src/ohmni/adapters/anthropic_provider.py` — NEW

Implement `AnthropicProvider` satisfying the `LlmProvider` Protocol:

```python
class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-opus-4-5") -> None: ...
    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[TStructured]
    ) -> TStructured: ...
    def complete_structured(
        self, *, instructions: str, data: str, schema: type[BaseModel], max_tokens: int = 4096
    ) -> BaseModel: ...
```

Rules:
- Use the `anthropic` Python SDK (`pip install anthropic`). Add it to
  `pyproject.toml` `dependencies`.
- Call `client.messages.create(model=..., max_tokens=..., system=...,
  messages=[...])` with `tool_use` / structured output to get a validated
  Pydantic model back.
- The preferred approach: pass the JSON schema of `response_model` as a
  tool definition, call with `tool_choice={"type":"tool","name":"..."}`, then
  parse `content[0].input` with `response_model.model_validate(...)`.
- If the model returns invalid JSON or schema violations, raise a descriptive
  `ValueError` — the orchestrator catches it and records a failed call.
- Never log or surface the raw API response outside of the provider; never log
  the API key.
- Read `ANTHROPIC_API_KEY` from `os.environ` inside `__init__` if not passed
  explicitly. Raise `RuntimeError` with a clear message if absent.

### 2. `src/ohmni/adapters/__init__.py` — MODIFY

Add `AnthropicProvider` to `__all__` and the public import list.

### 3. `pyproject.toml` — MODIFY

Add `anthropic>=0.40` to `[project] dependencies`.

### 4. `scripts/demo_server.py` — MODIFY

Wire real provider when `ANTHROPIC_API_KEY` is present:

```python
import os
from ohmni.adapters.anthropic_provider import AnthropicProvider

api_key = os.environ.get("ANTHROPIC_API_KEY")
if api_key:
    provider = AnthropicProvider(api_key=api_key)
else:
    provider = None  # falls back to fixture-only mode
```

The existing `DemoPipeline` must:
- Accept arbitrary user text when a real provider is available.
- Return the existing deterministic fixture result when no provider is present
  (current behaviour — do not break it).

### 5. `src/ohmni/application/demo.py` — MODIFY

`DemoPipeline.run()` currently only handles `DEMO_REQUEST` (the frozen fixture).
Add a branch:

```python
if provider is not None and request_text != DEMO_REQUEST:
    report = DesignOrchestrator(provider, default_catalog()).design(request_text)
    # project report → ProductExperience using existing build_brief / project_product_experience
else:
    # existing fixture path unchanged
```

Keep the fixture path working identically — it is the CI/CD and demo fallback.

### 6. `tests/test_anthropic_provider.py` — NEW

Pure unit tests, no network:
- Mock `anthropic.Anthropic.messages.create` to return a well-formed tool-use
  response; assert `generate_structured` returns a correctly validated model.
- Assert a malformed response raises `ValueError`.
- Assert missing API key raises `RuntimeError`.
- Use `pytest.mark.integration` for any test that actually calls the network.

---

## Invariants to preserve (from AGENTS.md)

- Model output cannot create evidence, verified status, ERC/DRC, or supplier
  facts. The Anthropic provider returns only schema-validated Pydantic objects;
  the orchestrator passes them through deterministic `verify()` before any
  report is produced.
- `UNKNOWN` never silently becomes PASS. If the provider errors, the
  orchestrator returns a `DesignReport` with `state=FAILED` and a recorded
  `GenerationIssue` — not a fabricated pass.
- Verification, routing, manufacturing, and BOM arithmetic have no model/network
  path. Those subsystems run after the provider returns and are unaffected.
- The API key must never appear in logs, generated KiCad files, or any artifact
  (SECURITY.md).

---

## File map

```
src/ohmni/adapters/
  __init__.py          ← add AnthropicProvider to exports
  anthropic_provider.py  ← NEW: real Anthropic SDK wrapper
  fakes.py             ← unchanged (RecordingLlmProvider stays)
src/ohmni/application/
  demo.py              ← add real-provider branch in DemoPipeline
scripts/
  demo_server.py       ← read ANTHROPIC_API_KEY, pass provider to pipeline
pyproject.toml         ← add anthropic>=0.40 to dependencies
tests/
  test_anthropic_provider.py  ← NEW: unit + integration tests
```

## Test command

```
python -m pytest tests/test_anthropic_provider.py -v
python scripts/verify.py fast   # must stay green
```
