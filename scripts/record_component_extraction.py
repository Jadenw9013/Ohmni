#!/usr/bin/env python3
"""Bind stored extraction proposals to the current provider-request fingerprint.

A recorded provider response answers one exact request. The request covers the
document digest, the observation digest, Ohmni's instruction text and the digest
of every rendered page -- so when the observation contract or the render settings
change, an old recording must stop answering rather than replay a proposal that
was made about different input.

This script never edits a proposal. It reads
``tests/corpus/recordings/*.proposal.json``, rebuilds the request from the pinned
source document, and writes the keyed recording beside it. The proposals are the
durable record of what a model actually said; the key is derived.

Usage::

    python scripts/acquire_corpus.py          # the pinned PDFs must be present
    python scripts/record_component_extraction.py
    python scripts/record_component_extraction.py --check   # verify keys only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ohmni.datasheet.multimodal import build_request
from ohmni.datasheet.pdf import BoundedObservationExtractor

RECORDINGS = ROOT / "tests" / "corpus" / "recordings"
MANIFEST = ROOT / "tests" / "corpus" / "manifest.json"

#: How a stored request identity came to exist. The distinction is the whole
#: point of CS-AUDIT-005: only the first witnesses what the provider was sent.
#: The second is a rebuild that may be argued equivalent but proves nothing, and
#: it must never be presented as a recorded response.
CAPTURE_KINDS = {"captured_at_call_time", "reconstructed_after_the_fact"}


def _document_path(document_id: str) -> Path:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return ROOT / manifest["workspace"] / f"{document_id}.pdf"


def rebuild(path: Path, *, check: bool) -> tuple[bool, str]:
    stored = json.loads(path.read_text(encoding="utf-8"))
    pdf = _document_path(stored["document_id"])
    if not pdf.is_file():
        return False, f"{path.name}: {pdf.relative_to(ROOT)} is absent; run acquire_corpus.py"
    bundle, images = BoundedObservationExtractor().observe(
        pdf, stored["observed_pages"], render=True
    )
    if bundle.document_digest != stored["document_sha256"]:
        return False, f"{path.name}: the acquired document does not match the pinned digest"
    request = build_request(
        bundle, images, requested_package=stored["requested_package"]
    )
    original = stored["provenance"].get("original_request")
    if not original:
        return False, (
            f"{path.name}: the stored proposal records no original request; it cannot be "
            "presented as a response to one. Re-record it against a live provider."
        )
    capture_kind = original.get("capture_kind")
    if capture_kind not in CAPTURE_KINDS:
        return False, (
            f"{path.name}: the original request does not say how it was obtained "
            f"(capture_kind must be one of {sorted(CAPTURE_KINDS)}). An identity rebuilt "
            "from today's code is not a witness to what the model saw."
        )
    # A recording answers the request the model actually saw. When the current
    # inputs differ, the honest outcome is to demote the fixture to 'scripted'
    # -- a valid offline test input whose extraction fidelity is unevaluated --
    # not to relabel an old proposal as a response to inputs it never saw.
    differences = [
        field
        for field in ("document_digest", "instructions_sha256", "page_text_sha256",
                      "requested_package", "extractor_version")
        if original.get(field) != request.identity()[field]
    ]
    if original.get("render_digests") != request.identity()["render_digests"]:
        differences.append("render_digests")
    # Matching today's request is necessary but not sufficient. When the stored
    # identity was itself rebuilt by this script, the comparison above is a value
    # against itself: it cannot fail, and it witnesses nothing. Such a fixture is
    # usable offline and is labelled so -- never as a recorded response.
    if differences:
        fidelity = "scripted"
        reason = (
            "inputs changed since the response was recorded ("
            + ", ".join(sorted(differences))
            + "); extraction fidelity against the current inputs is UNEVALUATED"
        )
    elif capture_kind == "reconstructed_after_the_fact":
        fidelity = "reconstructed"
        reason = (
            "the stored request identity was rebuilt from the current code and the "
            "pinned source after the provider call, not captured during it, so it "
            f"cannot witness the inputs the model saw ({original.get('capture_note') or 'no note'}). "
            "The proposal is a valid offline input; extraction fidelity against a live "
            "provider is UNEVALUATED"
        )
    else:
        fidelity = "recorded"
        reason = None
    target = path.with_name(path.name.replace(".proposal.json", ".json"))
    payload = {
        "schema_version": 1,
        "recording_id": stored["recording_id"],
        "fidelity": fidelity,
        "fidelity_reason": reason,
        "request_fingerprint": request.fingerprint,
        "document_sha256": stored["document_sha256"],
        "observation_digest": bundle.observation_digest,
        "observed_pages": stored["observed_pages"],
        "requested_package": stored["requested_package"],
        "provenance": stored["provenance"],
        "proposal": stored["proposal"],
    }
    if check:
        if not target.is_file():
            return False, f"{target.name}: absent"
        current = json.loads(target.read_text(encoding="utf-8"))
        if current.get("request_fingerprint") != request.fingerprint:
            return False, f"{target.name}: stale request fingerprint"
        # Comparing only the fingerprint would let a hand-edited or reverted
        # fixture claim `recorded` while its stored identity is a reconstruction
        # -- exactly the CS-AUDIT-005 defect, passing the gate meant to stop it.
        # So the label is recomputed from the proposal and must agree.
        if current.get("fidelity") != fidelity:
            return False, (
                f"{target.name}: fidelity says {current.get('fidelity')!r} but this "
                f"proposal derives {fidelity!r}"
            )
        if bool(current.get("fidelity_reason")) != bool(reason):
            return False, (
                f"{target.name}: a {fidelity!r} fixture must carry "
                f"{'a' if reason else 'no'} fidelity_reason"
            )
        return True, f"{target.name}: current ({fidelity})"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True, f"{target.name}: bound to request {request.fingerprint[:16]}..."


def capture_original(path: Path, *, note: str) -> tuple[bool, str]:
    """Reconstruct the request this proposal answered, labelled as a rebuild.

    This script runs after the fact. It can rebuild what the request *would be*
    from the current code and the pinned source, and it can record an argument
    that those inputs are unchanged -- but it cannot witness the call. So what
    it writes is always ``reconstructed_after_the_fact``, and the fixture it
    keys is labelled ``reconstructed``, never ``recorded``.

    A ``captured_at_call_time`` identity can only be written by the live
    recording path at the moment a provider is invoked. That path does not exist
    yet (CS-T02-R01 is open), which is why no fixture in this repository carries
    one. It refuses to overwrite an identity that is already there.
    """
    stored = json.loads(path.read_text(encoding="utf-8"))
    if stored["provenance"].get("original_request"):
        return False, f"{path.name}: an original request is already recorded; refusing to replace it"
    pdf = _document_path(stored["document_id"])
    if not pdf.is_file():
        return False, f"{path.name}: {pdf.relative_to(ROOT)} is absent"
    bundle, images = BoundedObservationExtractor().observe(
        pdf, stored["observed_pages"], render=True
    )
    request = build_request(bundle, images, requested_package=stored["requested_package"])
    stored["provenance"]["original_request"] = {
        **request.identity(),
        "model": stored["provenance"].get("produced_by", "unknown"),
        "capture_kind": "reconstructed_after_the_fact",
        "reconstructed_at": "2026-09-15",
        "capture_note": note,
    }
    path.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
    return True, f"{path.name}: original request captured ({request.fingerprint[:16]}...)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify keys without writing")
    parser.add_argument(
        "--capture-original", metavar="NOTE",
        help="record the current request as the one an existing proposal answered, "
             "with an explicit justification. Refuses if one is already recorded.",
    )
    args = parser.parse_args(argv)
    failures = 0
    for path in sorted(RECORDINGS.glob("*.proposal.json")):
        if args.capture_original:
            ok, message = capture_original(path, note=args.capture_original)
        else:
            ok, message = rebuild(path, check=args.check)
        print(message)
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
