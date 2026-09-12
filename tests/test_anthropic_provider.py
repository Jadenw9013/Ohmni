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
    DEFAULT_MAX_ATTEMPTS,
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


VALID_PAYLOAD = {"project_name": "logger", "board_layers": 2}
#: Rejected by Proposal: board_layers has ge=1.
INVALID_PAYLOAD = {"project_name": "logger", "board_layers": 0}


def _tool_use(name: str, payload: object, stop_reason: str = "tool_use",
              usage: tuple[int, int] | None = (100, 20)) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        usage=None if usage is None else SimpleNamespace(input_tokens=usage[0],
                                                         output_tokens=usage[1]),
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="tool_use", name=name, input=payload),
        ],
    )


def _good(usage: tuple[int, int] | None = (100, 20)) -> SimpleNamespace:
    return _tool_use("emit_proposal", VALID_PAYLOAD, usage=usage)


def _bad(usage: tuple[int, int] | None = (100, 20)) -> SimpleNamespace:
    return _tool_use("emit_proposal", INVALID_PAYLOAD, usage=usage)


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
        rejected = {"project_name": "logger", "board_layers": 0, "notes": "SECRET-DRAFT"}
        provider = _provider(*[_tool_use("emit_proposal", rejected)] * 3)
        with pytest.raises(StructuredGenerationError) as excinfo:
            provider.generate_structured(_request(), Proposal)
        message = str(excinfo.value)
        assert "Proposal" in message and "board_layers" in message
        assert "SECRET-DRAFT" not in message

    def test_a_schema_violation_is_a_value_error_the_orchestrator_already_catches(self):
        provider = _provider(_tool_use("emit_proposal", {"project_name": "logger"}),
                             max_attempts=1)
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

    def test_the_design_report_records_what_each_call_cost(self):
        """Cost tracking is only real if it survives the trip to the report."""
        from ohmni.catalog import default_catalog
        from ohmni.generation import DesignOrchestrator

        interpretation = _tool_use("emit_requirement_interpretation", {
            "project_name": "CO2 logger", "description": "A USB-powered CO2 logger",
            "max_input_voltage_v": 5.25, "target_logic_voltage_v": 3.3,
        }, usage=(900, 120))
        # One good answer, then nothing left: the architecture call fails, and a
        # failed call has to account for itself too.
        provider = _provider(interpretation)
        report = DesignOrchestrator(provider, default_catalog()).design("Build a CO2 logger")

        first, second = report.llm_calls
        assert first.success and first.request_type == "requirements"
        assert first.model_id == "claude-sonnet-5"
        assert (first.input_tokens, first.output_tokens) == (900, 120)
        assert first.token_usage == 1020 and first.attempts == 1
        assert first.latency_ms is not None and first.latency_ms >= 0
        assert not second.success and second.attempts == 1
        assert second.token_usage == 0 and second.error

    def test_a_provider_that_reports_no_usage_claims_none(self):
        """The offline fixture provider spends nothing and must not imply zero cost."""
        from ohmni.catalog import default_catalog
        from ohmni.generation import DesignOrchestrator
        from ohmni.generation.fixtures import GOLDEN_REQUEST, flawed_logger_provider

        report = DesignOrchestrator(flawed_logger_provider(), default_catalog()).design(
            GOLDEN_REQUEST, run_eda=False)
        record = report.llm_calls[0]
        assert record.provider == "RecordingLlmProvider"
        assert record.input_tokens is None and record.token_usage is None
        assert record.attempts is None and record.model_id is None
        assert record.latency_ms is not None


class TestBoundedSchemaRetries:
    """A rejected shape is the one failure the model can actually fix."""

    def test_a_rejected_answer_is_re_asked_and_the_corrected_one_is_returned(self):
        provider = _provider(_bad(), _good())
        value = provider.generate_structured(_request(), Proposal)
        assert isinstance(value, Proposal) and value.board_layers == 2
        assert len(provider._client.messages.calls) == 2

    def test_the_re_ask_carries_the_rejection_as_data_beside_the_original_request(self):
        provider = _provider(_bad(), _good())
        provider.generate_structured(_request({"allowed_parts": ["BME280"]}), Proposal)
        first, second = (call["messages"][0]["content"]
                         for call in provider._client.messages.calls)
        assert "schema_rejection" not in first
        # The correction names the offending field, and travels inside a tagged
        # block: a schema complaint quotes what the model invented, so it is
        # model-authored text and may not sit in an instruction position.
        assert "<schema_rejection>" in second and "board_layers" in second
        assert second.index("<data>") < second.index("<schema_rejection>")
        assert "BME280" in second
        # The system position stays fixed, so the cacheable prefix is unchanged
        # and no model-authored text is ever promoted to an instruction.
        systems = [[block["text"] for block in call["system"]]
                   for call in provider._client.messages.calls]
        assert systems[0] == systems[1]
        assert all("schema_rejection" not in text for text in systems[1])

    def test_the_loop_is_bounded_and_says_how_many_attempts_it_spent(self):
        provider = _provider(*[_bad()] * 3)
        with pytest.raises(StructuredGenerationError, match="after 3 attempt"):
            provider.generate_structured(_request(), Proposal)
        assert len(provider._client.messages.calls) == 3
        assert DEFAULT_MAX_ATTEMPTS == 3

    def test_the_bound_is_configurable_and_one_means_no_retry(self):
        provider = _provider(_bad(), _good(), max_attempts=1)
        with pytest.raises(StructuredGenerationError, match="after 1 attempt"):
            provider.generate_structured(_request(), Proposal)
        assert len(provider._client.messages.calls) == 1

    def test_an_unusable_bound_is_refused_at_construction(self):
        with pytest.raises(ValueError, match="max_attempts"):
            AnthropicProvider(api_key=SECRET_KEY, client=StubClient(), max_attempts=0)

    @pytest.mark.parametrize(
        ("response", "reason"),
        [
            (_text("refusal"), "a refusal will refuse again"),
            (_text("max_tokens"), "truncation needs a bigger budget, not another ask"),
            (_text("end_turn"), "free text is not a shape the model can correct"),
            (_tool_use("emit_proposal", ["not", "an", "object"]), "not a schema rejection"),
        ],
    )
    def test_only_schema_rejections_are_retried(self, response, reason):
        """Re-asking any other failure spends money to be told the same thing."""
        provider = _provider(response, _good())
        with pytest.raises(StructuredGenerationError):
            provider.generate_structured(_request(), Proposal)
        assert len(provider._client.messages.calls) == 1, reason

    def test_a_vendor_failure_is_not_retried_either(self):
        provider = _provider(RuntimeError("connection reset"), _good())
        with pytest.raises(StructuredGenerationError):
            provider.generate_structured(_request(), Proposal)
        assert len(provider._client.messages.calls) == 1


class TestCostAccounting:
    def test_usage_is_reported_for_a_single_successful_call(self):
        provider = _provider(_good(usage=(1234, 56)))
        provider.generate_structured(_request(), Proposal)
        usage = provider.last_call_usage()
        assert (usage.model, usage.attempts) == ("claude-sonnet-5", 1)
        assert (usage.input_tokens, usage.output_tokens) == (1234, 56)
        assert usage.total_tokens == 1290

    def test_every_attempt_is_counted_including_the_ones_that_were_rejected(self):
        """A retried call reporting only its last attempt would hide the bill."""
        provider = _provider(_bad(usage=(100, 10)), _bad(usage=(120, 12)), _good(usage=(140, 14)))
        provider.generate_structured(_request(), Proposal)
        usage = provider.last_call_usage()
        assert usage.attempts == 3
        assert usage.input_tokens == 360 and usage.output_tokens == 36
        assert usage.total_tokens == 396

    def test_a_call_that_never_succeeds_still_reports_what_it_spent(self):
        provider = _provider(*[_bad(usage=(100, 10))] * 3)
        with pytest.raises(StructuredGenerationError):
            provider.generate_structured(_request(), Proposal)
        usage = provider.last_call_usage()
        assert usage.attempts == 3 and usage.total_tokens == 330

    def test_a_vendor_failure_counts_its_attempt_without_inventing_tokens(self):
        provider = _provider(RuntimeError("connection reset"))
        with pytest.raises(StructuredGenerationError):
            provider.generate_structured(_request(), Proposal)
        usage = provider.last_call_usage()
        assert usage.attempts == 1 and usage.total_tokens == 0

    def test_a_response_without_usage_reports_no_tokens_rather_than_guessing(self):
        provider = _provider(_good(usage=None))
        provider.generate_structured(_request(), Proposal)
        usage = provider.last_call_usage()
        assert usage.attempts == 1 and usage.input_tokens == 0 and usage.output_tokens == 0

    def test_each_call_reports_its_own_usage_rather_than_a_running_total(self):
        provider = _provider(_good(usage=(10, 1)), _good(usage=(20, 2)))
        provider.generate_structured(_request(), Proposal)
        provider.generate_structured(_request(), Proposal)
        assert provider.last_call_usage().total_tokens == 22

    def test_usage_does_not_leak_between_concurrent_jobs(self):
        """The demo server shares one provider across worker threads."""
        import threading

        provider = _provider(*[_good(usage=(10, 1))] * 6)
        seen: dict[str, int] = {}
        barrier = threading.Barrier(2)

        def run(name):
            barrier.wait(timeout=5)
            provider.generate_structured(_request(), Proposal)
            seen[name] = provider.last_call_usage().total_tokens

        workers = [threading.Thread(target=run, args=(f"job-{index}",)) for index in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)
        assert seen == {"job-0": 11, "job-1": 11}


class TestModelSelection:
    def test_proposal_calls_default_to_the_sonnet_tier(self):
        """DEPLOYMENT_PLAN.md puts proposal calls on Sonnet; Opus is reserved."""
        provider = _provider(_good())
        provider.generate_structured(_request(), Proposal)
        assert DEFAULT_MODEL == "claude-sonnet-5"
        assert provider._client.messages.calls[0]["model"] == "claude-sonnet-5"


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
