"""Regressions for CS-AUDIT-005: what a stored proposal is allowed to claim.

The first remediation pass fixed ``scripts/record_component_extraction.py`` and
then asserted only on the *committed JSON files* it had produced. That is an
assertion about an artifact, not about the system: an independent review reverted
the production branch, regenerated the fixture, and got ``fidelity: "recorded"``
back on a reconstructed identity with the whole suite still green.

So these tests execute ``rebuild()`` and ``capture_original()`` against temporary
fixture directories and assert the label each input shape earns. The distinction
being defended is the one the audit named: an identity *witnessed at the provider
call* can support "the model saw these inputs"; an identity *rebuilt afterwards*
cannot, however good the argument that the inputs are unchanged.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from corpus import RECORDINGS, missing_reason

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ID = "MCP73831-DS20001984H"
FIXTURE = "MCP73831_SOT23-5_accepted.proposal.json"

pytestmark = pytest.mark.corpus


def _recorder():
    """Import the script by path; it is a tool, not part of the package."""
    path = ROOT / "scripts" / "record_component_extraction.py"
    spec = importlib.util.spec_from_file_location("_recorder_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def workspace(tmp_path: Path):
    """A private copy of the recordings, so a test never writes to the repo."""
    reason = missing_reason(DOCUMENT_ID)
    if reason:
        pytest.skip(reason)
    directory = tmp_path / "recordings"
    directory.mkdir()
    shutil.copy(RECORDINGS / FIXTURE, directory / FIXTURE)
    recorder = _recorder()
    recorder.RECORDINGS = directory
    return recorder, directory / FIXTURE


def _stored(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class TestFidelityIsEarned:
    def test_a_reconstructed_identity_yields_reconstructed(self, workspace):
        recorder, proposal = workspace
        ok, message = recorder.rebuild(proposal, check=False)
        assert ok, message
        derived = _stored(proposal.with_name(proposal.name.replace(".proposal", "")))
        assert derived["fidelity"] == "reconstructed"
        assert "UNEVALUATED" in derived["fidelity_reason"]

    def test_an_identity_witnessed_at_the_call_yields_recorded(self, workspace):
        """The only input shape that earns the strong label."""
        recorder, proposal = workspace
        payload = _stored(proposal)
        payload["provenance"]["original_request"]["capture_kind"] = "captured_at_call_time"
        _write(proposal, payload)
        ok, message = recorder.rebuild(proposal, check=False)
        assert ok, message
        derived = _stored(proposal.with_name(proposal.name.replace(".proposal", "")))
        assert derived["fidelity"] == "recorded"
        assert derived["fidelity_reason"] is None

    def test_changed_inputs_yield_scripted(self, workspace):
        recorder, proposal = workspace
        payload = _stored(proposal)
        payload["provenance"]["original_request"]["capture_kind"] = "captured_at_call_time"
        payload["provenance"]["original_request"]["instructions_sha256"] = "0" * 64
        _write(proposal, payload)
        ok, message = recorder.rebuild(proposal, check=False)
        assert ok, message
        derived = _stored(proposal.with_name(proposal.name.replace(".proposal", "")))
        assert derived["fidelity"] == "scripted"
        assert "instructions_sha256" in derived["fidelity_reason"]
        assert "UNEVALUATED" in derived["fidelity_reason"]

    def test_an_undeclared_capture_kind_is_refused(self, workspace):
        """Silence is not a capture. An unlabelled identity cannot be keyed."""
        recorder, proposal = workspace
        payload = _stored(proposal)
        del payload["provenance"]["original_request"]["capture_kind"]
        _write(proposal, payload)
        ok, message = recorder.rebuild(proposal, check=False)
        assert not ok
        assert "capture_kind" in message

    def test_a_missing_original_request_is_refused(self, workspace):
        recorder, proposal = workspace
        payload = _stored(proposal)
        del payload["provenance"]["original_request"]
        _write(proposal, payload)
        ok, message = recorder.rebuild(proposal, check=False)
        assert not ok
        assert "no original request" in message


class TestCheckGateCatchesATamperedLabel:
    """The CI gate must fail on the defect it exists to prevent."""

    def test_check_rejects_a_reconstructed_fixture_relabelled_recorded(self, workspace):
        recorder, proposal = workspace
        assert recorder.rebuild(proposal, check=False)[0]
        derived = proposal.with_name(proposal.name.replace(".proposal", ""))
        payload = _stored(derived)
        payload["fidelity"] = "recorded"
        payload["fidelity_reason"] = None
        _write(derived, payload)
        ok, message = recorder.rebuild(proposal, check=True)
        assert not ok, (
            "a fixture claiming 'recorded' over a reconstructed identity passed the "
            "gate; comparing only the request fingerprint cannot detect this"
        )
        assert "fidelity" in message

    def test_check_accepts_the_fixture_it_just_generated(self, workspace):
        recorder, proposal = workspace
        assert recorder.rebuild(proposal, check=False)[0]
        ok, message = recorder.rebuild(proposal, check=True)
        assert ok, message


class TestCaptureOriginalCannotClaimAWitness:
    def test_capture_records_a_reconstruction_not_a_capture(self, workspace):
        """The script runs after the fact, so it may only ever say so."""
        recorder, proposal = workspace
        payload = _stored(proposal)
        del payload["provenance"]["original_request"]
        _write(proposal, payload)
        ok, message = recorder.capture_original(proposal, note="test capture")
        assert ok, message
        original = _stored(proposal)["provenance"]["original_request"]
        assert original["capture_kind"] == "reconstructed_after_the_fact"
        assert "captured_at" not in original
        # And the fixture it keys must not then claim the strong label.
        assert recorder.rebuild(proposal, check=False)[0]
        derived = _stored(proposal.with_name(proposal.name.replace(".proposal", "")))
        assert derived["fidelity"] == "reconstructed"

    def test_capture_refuses_to_overwrite_an_existing_identity(self, workspace):
        recorder, proposal = workspace
        ok, message = recorder.capture_original(proposal, note="second attempt")
        assert not ok
        assert "refusing to replace" in message
