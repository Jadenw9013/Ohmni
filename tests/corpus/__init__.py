"""Pinned real-source corpus access for the component-synthesis tests.

The manufacturer PDFs are copyrighted and deliberately not committed. This
module locates the acquired bytes, verifies them against the pinned digest, and
gives the tests one honest way to say "the source is absent" -- a skip, never a
pass. ``python scripts/acquire_corpus.py`` fetches them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.json"
ANNOTATIONS = Path(__file__).resolve().parent / "annotations"
RECORDINGS = Path(__file__).resolve().parent / "recordings"


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def entry(document_id: str) -> dict:
    for item in manifest()["documents"]:
        if item["id"] == document_id:
            return item
    raise KeyError(f"{document_id!r} is not in the corpus manifest")


def document_path(document_id: str) -> Path:
    return ROOT / manifest()["workspace"] / f"{document_id}.pdf"


def missing_reason(document_id: str) -> str | None:
    """Why the pinned source cannot be used, or None when it can.

    A digest mismatch is reported rather than tolerated: the manufacturer may
    have republished the document, and a test that silently accepted the new
    bytes would be checking something nobody annotated.
    """
    path = document_path(document_id)
    if not path.is_file():
        return (
            f"pinned source {document_id} is absent at {path.relative_to(ROOT)}; "
            "run python scripts/acquire_corpus.py"
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pinned = entry(document_id)["sha256"]
    if digest != pinned:
        return f"pinned source {document_id} hashes {digest}, not {pinned}"
    return None


def annotation(name: str) -> dict:
    return json.loads((ANNOTATIONS / name).read_text(encoding="utf-8"))


def recorded_proposal_with_fidelity(bundle, images, *, requested_package: str, recordings=None):
    """Replay the stored proposal for this exact request, with its label.

    Returns ``(proposal, fidelity, None)`` or ``(None, None, reason)``. A
    recording answers one exact request, so a parser or render change
    legitimately unbinds it. That is a reason to re-record and a reason to skip
    -- never a reason to accept a proposal that was made about different input.

    The ``fidelity`` is returned rather than swallowed because it is the only
    thing distinguishing a witnessed provider response from a fixture that was
    rebuilt afterwards or hand-written. A caller asserting extraction fidelity
    must look at it; a caller that only needs a valid offline input need not.
    """
    from ohmni.adapters.vision import RecordedResponseMissing, RecordedVisionProvider
    from ohmni.datasheet.multimodal import MultimodalCandidateExtractor

    provider = RecordedVisionProvider(directory=recordings or RECORDINGS)
    try:
        proposal = MultimodalCandidateExtractor(provider).extract(
            bundle, images, requested_package=requested_package
        )
    except Exception as exc:
        if not isinstance(exc, RecordedResponseMissing) and "no recorded provider response" not in str(exc):
            raise
        return None, None, (
            "the recorded provider response is not bound to the current request "
            "(parser, renderer or instruction change); run "
            "python scripts/record_component_extraction.py"
        )
    return proposal, provider.replayed_fidelity, None


def recorded_proposal(bundle, images, *, requested_package: str, recordings=None):
    """``recorded_proposal_with_fidelity`` for callers that need only the input."""
    proposal, _fidelity, reason = recorded_proposal_with_fidelity(
        bundle, images, requested_package=requested_package, recordings=recordings
    )
    return proposal, reason


def recording(name: str) -> dict:
    path = RECORDINGS / name
    if not path.is_file():
        raise FileNotFoundError(
            f"{name} is absent; run python scripts/record_component_extraction.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "ANNOTATIONS",
    "RECORDINGS",
    "annotation",
    "document_path",
    "entry",
    "manifest",
    "missing_reason",
    "recorded_proposal",
    "recorded_proposal_with_fidelity",
    "recording",
]
