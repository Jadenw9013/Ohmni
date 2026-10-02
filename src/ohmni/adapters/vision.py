"""Offline vision providers: recorded responses and scripted failures.

A recorded response is keyed by the request fingerprint, which covers the
document digest, the observation digest, Ohmni's instruction text and the
digest of every rendered page. Change any of those and the recording no longer
answers: the test fails loudly instead of replaying a proposal that was made
about different pixels.

These are the providers the default suite uses. They exist so the extraction
path is exercised end to end with no network, no credentials and no spend --
and so a recorded *wrong* proposal can be replayed to prove the deterministic
source checker rejects it.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

from ..datasheet.multimodal import VisionExtractionError, VisionExtractionRequest


class RecordedResponseMissing(VisionExtractionError):
    """No recording for this exact request. Never silently answered."""


class RecordedVisionProvider:
    """Replays proposals recorded from a real provider call.

    ``strict_fingerprint`` defaults to True. Turning it off keys recordings by
    name instead, which is how a hand-written negative fixture (a proposal that
    is deliberately wrong) is replayed against observations it was never
    recorded from.
    """

    def __init__(
        self,
        recordings: dict[str, dict] | None = None,
        *,
        directory: Path | None = None,
        strict_fingerprint: bool = True,
    ) -> None:
        self.recordings = dict(recordings or {})
        self.strict_fingerprint = strict_fingerprint
        self.calls: list[str] = []
        #: The ``fidelity`` of the recording most recently replayed, or None.
        #: A label nothing reads is decoration: before this existed, a fixture
        #: demoted to ``scripted`` replayed exactly like a real recorded
        #: response, so the demotion changed nothing a caller could act on.
        self.replayed_fidelity: str | None = None
        if directory is not None:
            for path in sorted(directory.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                key = payload.get("request_fingerprint") or path.stem
                self.recordings[key] = payload

    def propose(self, request: VisionExtractionRequest, schema: type[BaseModel]) -> BaseModel:
        key = request.fingerprint
        self.calls.append(key)
        payload = self.recordings.get(key)
        if payload is None and not self.strict_fingerprint and len(self.recordings) == 1:
            payload = next(iter(self.recordings.values()))
        if payload is None:
            raise RecordedResponseMissing(
                f"no recorded provider response for request {key[:16]}...; "
                "re-record it or acquire the pinned source document"
            )
        try:
            proposal = schema.model_validate(payload["proposal"])
        except ValidationError as exc:
            raise VisionExtractionError(
                f"recorded response does not satisfy {schema.__name__}: {exc.error_count()} error(s)"
            ) from exc
        # An unlabelled payload is a hand-written fixture, not a provider
        # response, so it is reported as scripted rather than as unknown.
        self.replayed_fidelity = str(payload.get("fidelity", "scripted"))
        return proposal


class ScriptedVisionProvider:
    """Returns a fixed sequence of outcomes, for failure-path tests.

    Each element is either a payload dict, an already-built model, or an
    exception instance to raise. Running past the end raises, because a test
    that calls a provider more often than it scripted has changed behaviour.
    """

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def propose(self, request: VisionExtractionRequest, schema: type[BaseModel]) -> BaseModel:
        if self.calls >= len(self.outcomes):
            raise VisionExtractionError(
                f"scripted provider exhausted after {self.calls} call(s)"
            )
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, BaseModel):
            return outcome
        return schema.model_validate(outcome)


__all__ = ["RecordedResponseMissing", "RecordedVisionProvider", "ScriptedVisionProvider"]
