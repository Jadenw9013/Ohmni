"""The vendor boundary, exercised with no SDK installed and no network.

Every test below drives the real parse-and-validate path through an injected
stub client. That is deliberate: the rules this adapter exists to enforce --
nothing but a schema-valid object leaves it, and no key, payload or vendor
envelope leaves it at all -- are properties of *this* code, not of the SDK, and
they must hold on a machine where ``anthropic`` was never installed.

The one test that really calls the API is marked ``integration`` and skips
without a key, so the offline tiers stay offline.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, Field

from ohmni.adapters import LlmProvider, StructuredGenerationRequest
from ohmni.adapters.anthropic_provider import (
    API_KEY_ENV_VAR,
    DEFAULT_MODEL,
    MODEL_ENV_VAR,
    SYSTEM_PROMPT,
    AnthropicProvider,
    StructuredGenerationError,
)

SECRET_KEY = "sk-ant-test-not-a-real-key"


class Proposal(BaseModel):
    """A stand-in for the generation schemas, small enough to read in a failure."""

    project_name: str
    board_layers: int = Field(ge=1)
    notes: list[str] = Field(default_factory=list)


def _tool_use(name: str, payload: object, stop_reason: str = "tool_use") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="tool_use", name=name, input=payload),
        ],
    )


def _text(stop_reason: str, text: str = "Here is a circuit.") -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class StubMessages:
    def __init__(self, responses: list[object]) -> None:
        self.responses, self.calls = responses, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class StubClient:
    """Stands in for ``anthropic.Anthropic`` at the one method this adapter calls."""

    def __init__(self, *responses: object) -> None:
        self.messages = StubMessages(list(responses))


def _provider(*responses: object, **kwargs) -> AnthropicProvider:
    return AnthropicProvider(api_key=SECRET_KEY, client=StubClient(*responses), **kwargs)


def _request(data: dict[str, object] | None = None) -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        request_type="circuit",
        instructions="Return only the requested schema.",
        data=data if data is not None else {"allowed_parts": ["BME280"]},
    )


class TestCredentials:
    def test_missing_key_names_the_variable_and_the_offline_alternative(self, monkeypatch):
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        with pytest.raises(RuntimeError) as excinfo:
            AnthropicProvider()
        assert API_KEY_ENV_VAR in str(excinfo.value)

    def test_a_blank_key_is_missing_rather_than_a_credential(self, monkeypatch):
        monkeypatch.setenv(API_KEY_ENV_VAR, "   ")
        with pytest.raises(RuntimeError):
            AnthropicProvider()

    def test_the_environment_supplies_the_key_when_the_caller_does_not(self, monkeypatch):
        monkeypatch.setenv(API_KEY_ENV_VAR, SECRET_KEY)
        provider = AnthropicProvider(client=StubClient())
        assert provider.model == DEFAULT_MODEL

    def test_the_key_is_never_kept_on_the_instance_or_in_its_repr(self):
        provider = _provider()
        assert SECRET_KEY not in repr(provider)
        assert not any(SECRET_KEY in str(value) for value in vars(provider).values())

    def test_the_model_is_pinned_and_overridable_by_environment(self, monkeypatch):
        monkeypatch.setenv(MODEL_ENV_VAR, "claude-sonnet-5")
        assert _provider().model == "claude-sonnet-5"
        assert _provider(model="claude-opus-5").model == "claude-opus-5"


class TestStructuredGeneration:
    def test_a_well_formed_tool_call_becomes_a_validated_model(self):
        provider = _provider(_tool_use("emit_proposal", {"project_name": "logger", "board_layers": 2}))
        value = provider.generate_structured(_request(), Proposal)
        assert isinstance(value, Proposal)
        assert (value.project_name, value.board_layers, value.notes) == ("logger", 2, [])

    def test_the_schema_is_sent_as_the_one_tool_the_model_must_call(self):
        provider = _provider(_tool_use("emit_proposal", {"project_name": "logger", "board_layers": 2}))
        provider.generate_structured(_request(), Proposal)
        sent = provider._client.messages.calls[0]
        tool = sent["tools"][0]
        assert sent["model"] == DEFAULT_MODEL
        assert sent["tool_choice"] == {"type": "tool", "name": "emit_proposal"}
        assert [tool["name"]] == [sent["tool_choice"]["name"]]
        assert tool["input_schema"] == Proposal.model_json_schema()

    def test_instructions_frame_the_call_and_request_data_stays_data(self):
        provider = _provider(_tool_use("emit_proposal", {"project_name": "logger", "board_layers": 2}))
        provider.generate_structured(_request({"allowed_parts": ["BME280"]}), Proposal)
        sent = provider._client.messages.calls[0]
        system = [block["text"] for block in sent["system"]]
        content = sent["messages"][0]["content"]
        assert system[0] == SYSTEM_PROMPT
        assert system[1] == "Return only the requested schema."
        # The caller's data reaches the model only inside the user turn, and
        # only as the JSON this provider serialized -- never as instructions.
        assert sent["messages"][0]["role"] == "user"
        assert json.dumps({"data": {"allowed_parts": ["BME280"]}, "request_type": "circuit"},
                          sort_keys=True) in content
        assert all("BME280" not in block for block in system)

    def test_complete_structured_honours_its_own_token_bound(self):
        provider = _provider(_tool_use("emit_proposal", {"project_name": "logger", "board_layers": 2}))
        value = provider.complete_structured(
            instructions="Return only the requested schema.", data="{}", schema=Proposal, max_tokens=512,
        )
        assert isinstance(value, Proposal)
        assert provider._client.messages.calls[0]["max_tokens"] == 512

    def test_it_satisfies_the_provider_protocol_the_orchestrator_depends_on(self):
        assert isinstance(_provider(), LlmProvider)


class TestFailuresStayFailures:
    def test_a_schema_violation_raises_without_republishing_the_payload(self):
        provider = _provider(_tool_use(
            "emit_proposal", {"project_name": "logger", "board_layers": 0, "notes": "SECRET-DRAFT"},
        ))
        with pytest.raises(StructuredGenerationError) as excinfo:
            provider.generate_structured(_request(), Proposal)
        message = str(excinfo.value)
        assert "Proposal" in message and "board_layers" in message
        assert "SECRET-DRAFT" not in message

    def test_a_schema_violation_is_a_value_error_the_orchestrator_already_catches(self):
        provider = _provider(_tool_use("emit_proposal", {"project_name": "logger"}))
        with pytest.raises(ValueError):
            provider.generate_structured(_request(), Proposal)

    def test_non_object_tool_arguments_are_rejected_rather_than_coerced(self):
        provider = _provider(_tool_use("emit_proposal", ["project_name", "logger"]))
        with pytest.raises(StructuredGenerationError, match="object was required"):
            provider.generate_structured(_request(), Proposal)

    def test_free_text_is_not_an_answer(self):
        provider = _provider(_text("end_turn"))
        with pytest.raises(StructuredGenerationError, match="free text is not accepted"):
            provider.generate_structured(_request(), Proposal)

    def test_a_truncated_proposal_is_not_a_proposal(self):
        provider = _provider(_text("max_tokens"))
        with pytest.raises(StructuredGenerationError, match="token limit"):
            provider.generate_structured(_request(), Proposal)

    def test_a_refusal_is_reported_as_a_refusal(self):
        provider = _provider(_text("refusal"))
        with pytest.raises(StructuredGenerationError, match="declined"):
            provider.generate_structured(_request(), Proposal)

    def test_another_tools_arguments_are_not_accepted_as_this_schema(self):
        provider = _provider(_tool_use("emit_something_else", {"project_name": "x", "board_layers": 1}))
        with pytest.raises(StructuredGenerationError):
            provider.generate_structured(_request(), Proposal)

    def test_a_vendor_failure_leaks_neither_the_key_nor_the_response_body(self):
        failure = RuntimeError(f"401 {{'error': 'invalid x-api-key {SECRET_KEY}'}}")
        failure.status_code = 401
        provider = _provider(failure)
        with pytest.raises(StructuredGenerationError) as excinfo:
            provider.generate_structured(_request(), Proposal)
        message = str(excinfo.value)
        assert "RuntimeError" in message and "HTTP 401" in message
        assert SECRET_KEY not in message and "invalid x-api-key" not in message


class TestOrchestratorBoundary:
    def test_a_provider_failure_fails_the_design_instead_of_fabricating_one(self):
        """A model that cannot answer must not produce a design report that passes."""
        from ohmni.catalog import default_catalog
        from ohmni.generation import DesignOrchestrator, GenerationState

        provider = _provider(*[RuntimeError("connection reset")] * 4)
        report = DesignOrchestrator(provider, default_catalog()).design("Build me something")
        assert report.state is GenerationState.FAILED
        assert report.issues and report.final_circuit is None
        assert [call.success for call in report.llm_calls] == [False]


@pytest.mark.integration
def test_a_real_call_returns_a_schema_valid_object():
    """The only test here that spends money; skipped unless a key is configured."""
    pytest.importorskip("anthropic")
    if not os.environ.get(API_KEY_ENV_VAR, "").strip():
        pytest.skip(f"{API_KEY_ENV_VAR} is not set")
    provider = AnthropicProvider()
    value = provider.generate_structured(
        StructuredGenerationRequest(
            request_type="requirements",
            instructions="Record the project described by the data as a Proposal.",
            data={"description": "A two-layer USB-powered temperature logger called Logger."},
        ),
        Proposal,
    )
    assert isinstance(value, Proposal) and value.project_name
