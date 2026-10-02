"""Regressions for the independent audit of CS-T01 through CS-T04.

Every test here is a counterexample the audit reproduced against the original
implementation, where it *passed* verification. Each one is now required to be
rejected. They are kept as a group, named after their finding, because the value
is in the exact shape of the false positive, not in the rule that happens to
catch it today.

Audit: COMPONENT_SYNTHESIS_AUDIT.md, record .ai/verification/CS-T01-T04-AUDIT.yaml.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from corpus import document_path, missing_reason, recorded_proposal, recording
from pydantic import ValidationError

from ohmni.adapters import ToolStatus
from ohmni.datasheet.constraint_verifier import verify_extraction
from ohmni.datasheet.pdf import BoundedObservationExtractor
from ohmni.domain.component_synthesis import (
    ExtractionProposal,
    VerifiedConstraintSet,
)
from ohmni.eda.kicad.component_asset_parser import AssetParseError, measure_footprint
from ohmni.eda.kicad.component_assets import render_footprint, render_symbol_library
from ohmni.eda.kicad.component_harness import export_symbol_svg
from ohmni.physical.component_asset_verifier import verify_assets
from ohmni.physical.land_patterns import (
    REQUIRED_LAND_DIMENSIONS,
    build_land_pattern,
    build_symbol,
)

DOCUMENT_ID = "MCP73831-DS20001984H"
PAGES = [11, 24, 26]
PACKAGE_COLUMN = "SOT-23-5"

pytestmark = pytest.mark.corpus


@pytest.fixture(scope="module")
def observations():
    reason = missing_reason(DOCUMENT_ID)
    if reason:
        pytest.skip(reason)
    return BoundedObservationExtractor().observe(document_path(DOCUMENT_ID), PAGES, render=True)


@pytest.fixture(scope="module")
def verified(observations):
    bundle, images = observations
    proposal, unbound = recorded_proposal(bundle, images, requested_package=PACKAGE_COLUMN)
    if unbound:
        pytest.skip(unbound)
    report = verify_extraction(
        bundle, proposal,
        required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
    )
    assert report.verified is not None, report.missing
    return report.verified


def _assets(verified, mutate=None):
    """Generate, mutate the emitted text, and run the asset checks on the result."""
    import hashlib

    land_pattern = build_land_pattern(verified)
    symbol = build_symbol(verified)
    footprint_text = render_footprint(land_pattern)
    symbol_text = render_symbol_library(symbol)
    if mutate is not None:
        footprint_text = mutate(footprint_text)
    footprint_digest = hashlib.sha256(footprint_text.encode("utf-8")).hexdigest()
    symbol_digest = hashlib.sha256(symbol_text.encode("utf-8")).hexdigest()
    return verify_assets(
        verified,
        measure_footprint(footprint_text),
        __import__(
            "ohmni.eda.kicad.component_asset_parser", fromlist=["measure_symbol_library"]
        ).measure_symbol_library(symbol_text),
        land_pattern=land_pattern, symbol_definition=symbol,
        footprint_digest=footprint_digest, symbol_digest=symbol_digest,
        recorded_footprint_digest=footprint_digest, recorded_symbol_digest=symbol_digest,
    )


class TestAudit001SourceMeaning:
    """A real row, cited correctly, but given the wrong engineering meaning."""

    def test_the_pad_width_row_cannot_be_accepted_as_the_pad_length(self, observations):
        bundle, _images = observations
        raw = copy.deepcopy(recording("MCP73831_SOT23-5_accepted.proposal.json")["proposal"])
        width = next(item for item in raw["dimensions"] if item["kind"] == "land_pad_width")
        length = next(item for item in raw["dimensions"] if item["kind"] == "land_pad_length")
        # The audit's exact mutation: cite the genuine X / Contact Pad Width row,
        # with its genuine printed 0.60 mm, and label it land_pad_length. The
        # optional redundancy that would have caught it is dropped.
        relabelled = dict(width, candidate_id=length["candidate_id"], kind="land_pad_length")
        raw["dimensions"] = [
            relabelled if item["kind"] == "land_pad_length" else item
            for item in raw["dimensions"]
            if item["kind"] not in ("land_row_gap", "land_overall_width")
        ]
        proposal = ExtractionProposal.model_validate(raw)
        report = verify_extraction(
            bundle, proposal,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None, (
            "a row that prints the contact pad WIDTH was accepted as the pad LENGTH; "
            "the generated footprint would have 0.60 x 0.60 mm lands"
        )
        offender = next(
            r for r in report.receipts if r.candidate_id == length["candidate_id"]
        )
        assert not offender.supported
        assert any("mean" in reason or "denote" in reason for reason in offender.reasons)

    def test_a_row_the_grammar_does_not_map_is_refused(self, observations):
        bundle, _images = observations
        raw = copy.deepcopy(recording("MCP73831_SOT23-5_accepted.proposal.json")["proposal"])
        for item in raw["dimensions"]:
            if item["kind"] == "land_pad_width":
                item["row_label"] = "Overall Width"
                item["dimension_symbol"] = "Z"
        proposal = ExtractionProposal.model_validate(raw)
        report = verify_extraction(
            bundle, proposal,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None

    def test_a_pin_row_cannot_be_relabelled_as_an_exposed_pad(self, observations):
        bundle, _images = observations
        raw = copy.deepcopy(recording("MCP73831_SOT23-5_accepted.proposal.json")["proposal"])
        raw["pins"][0]["kind"] = "exposed_pad"
        proposal = ExtractionProposal.model_validate(raw)
        report = verify_extraction(
            bundle, proposal,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None


class TestAudit002ReceiptBinding:
    """Receipts must describe the values actually being carried."""

    def test_a_value_changed_after_verification_is_rejected_on_revalidation(self, verified):
        altered = verified.model_dump(mode="json")
        replacements = {
            "land_pad_length": "0.6", "land_overall_width": "3.4", "land_row_gap": "2.2",
        }
        for item in altered["dimensions"]:
            value = replacements.get(item["kind"])
            if value:
                item["value"] = {
                    "source_text": value, "unit": "mm",
                    "nanometres": round(float(value) * 1_000_000),
                }
        assert altered["receipts"] == verified.model_dump(mode="json")["receipts"]
        with pytest.raises(ValidationError) as error:
            VerifiedConstraintSet.model_validate(altered)
        assert "receipt" in str(error.value).casefold()

    def test_a_changed_terminal_symbol_is_rejected_on_revalidation(self, verified):
        altered = verified.model_dump(mode="json")
        altered["terminals"][0]["symbol"] = "VDD"
        with pytest.raises(ValidationError):
            VerifiedConstraintSet.model_validate(altered)

    def test_a_changed_identity_field_is_rejected_on_revalidation(self, verified):
        altered = verified.model_dump(mode="json")
        altered["identity"]["orderable_part_number"] = "MCP73831T-2ACI/MC"
        with pytest.raises(ValidationError):
            VerifiedConstraintSet.model_validate(altered)

    def test_a_changed_pad_slot_is_rejected_on_revalidation(self, verified):
        altered = verified.model_dump(mode="json")
        altered["pad_ordering"]["traversal"] = "clockwise_from_pin_1"
        with pytest.raises(ValidationError):
            VerifiedConstraintSet.model_validate(altered)

    def test_a_receipt_from_another_checker_version_is_rejected(self, verified):
        altered = verified.model_dump(mode="json")
        for receipt in altered["receipts"]:
            receipt["checker_version"] = "0.9.0"
        with pytest.raises(ValidationError):
            VerifiedConstraintSet.model_validate(altered)


class TestAudit003SerialisedGeometry:
    """Geometry the file actually contains, not the subset we happened to read."""

    def test_rotated_pads_are_rejected(self, verified):
        def rotate(text: str) -> str:
            return re.sub(r"(\(pad[^\n]*\n\s*\(at [^ ()]+ [^ ()]+)\)", r"\1 90)", text)

        with pytest.raises(AssetParseError, match="rotation"):
            measure_footprint(rotate(render_footprint(build_land_pattern(verified))))

    def test_an_unsupported_pad_field_is_rejected_rather_than_dropped(self, verified):
        text = render_footprint(build_land_pattern(verified)).replace(
            "(roundrect_rratio 0.25)", "(roundrect_rratio 0.25)\n\t\t(solder_mask_margin -0.4)"
        )
        with pytest.raises(AssetParseError, match="solder_mask_margin"):
            measure_footprint(text)

    def test_added_copper_is_rejected(self, verified):
        text = render_footprint(build_land_pattern(verified))
        injected = text.rstrip()[:-1] + (
            '\n\t(fp_line\n\t\t(start -1.5 1.4)\n\t\t(end 1.5 1.4)\n'
            '\t\t(stroke\n\t\t\t(width 0.4)\n\t\t\t(type solid)\n\t\t)\n'
            '\t\t(layer "F.Cu")\n\t)\n)\n'
        )
        report_or_error = None
        try:
            measured = measure_footprint(injected)
        except AssetParseError as exc:
            report_or_error = exc
        if report_or_error is None:
            report = verify_assets(
                verified, measured,
                __import__(
                    "ohmni.eda.kicad.component_asset_parser",
                    fromlist=["measure_symbol_library"],
                ).measure_symbol_library(render_symbol_library(build_symbol(verified))),
                land_pattern=build_land_pattern(verified),
                symbol_definition=build_symbol(verified),
                footprint_digest="a" * 64, symbol_digest="b" * 64,
                recorded_footprint_digest="a" * 64, recorded_symbol_digest="b" * 64,
            )
            assert not report.passed, "copper added across the land row was not checked"
        else:
            assert "F.Cu" in str(report_or_error) or "copper" in str(report_or_error)

    def test_an_unknown_footprint_construct_is_rejected(self, verified):
        text = render_footprint(build_land_pattern(verified))
        injected = text.rstrip()[:-1] + '\n\t(zone (net 0) (layer "F.Cu"))\n)\n'
        with pytest.raises(AssetParseError):
            measure_footprint(injected)


class TestAudit004NativeOutputFreshness:
    """A tool that wrote nothing has corroborated nothing."""

    def test_a_preexisting_unrelated_svg_cannot_corroborate(
        self, verified, tmp_path: Path
    ):
        library = tmp_path / "lib.kicad_sym"
        library.write_text(render_symbol_library(build_symbol(verified)), encoding="utf-8")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        (out_dir / "unrelated.svg").write_text("<svg>" + " " * 300 + "</svg>", encoding="utf-8")
        with patch(
            "ohmni.eda.kicad.component_harness.run_tool",
            return_value=SimpleNamespace(returncode=0, stdout="fake version", stderr=""),
        ):
            run = export_symbol_svg(
                library, "missing_symbol", out_dir, executable="mock-no-output"
            )
        assert run.status is not ToolStatus.OK
        assert not run.corroborated

    def test_a_zero_exit_that_writes_nothing_is_a_failure(self, verified, tmp_path: Path):
        library = tmp_path / "lib.kicad_sym"
        symbol = build_symbol(verified)
        library.write_text(render_symbol_library(symbol), encoding="utf-8")
        with patch(
            "ohmni.eda.kicad.component_harness.run_tool",
            return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
        ):
            run = export_symbol_svg(
                library, symbol.name, tmp_path / "empty", executable="mock-no-output"
            )
        assert run.status is ToolStatus.FAILED
        assert not run.corroborated

    def test_an_output_that_is_not_an_svg_is_a_failure(self, verified, tmp_path: Path):
        library = tmp_path / "lib.kicad_sym"
        symbol = build_symbol(verified)
        library.write_text(render_symbol_library(symbol), encoding="utf-8")
        out_dir = tmp_path / "out"

        def fake_run(command, *, timeout):
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{symbol.name}_unit1.svg").write_text("x" * 500, encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch("ohmni.eda.kicad.component_harness.run_tool", side_effect=fake_run):
            run = export_symbol_svg(
                library, symbol.name, out_dir, executable="mock-not-svg"
            )
        assert run.status is ToolStatus.FAILED
        assert not run.corroborated


class TestAudit005RecordingProvenance:
    """A fixture rebound to new inputs is scripted, not a recorded response."""

    def test_the_stored_proposal_carries_the_original_request_identity(self):
        stored = recording("MCP73831_SOT23-5_accepted.proposal.json")
        original = stored["provenance"].get("original_request")
        assert original, "the proposal must record the request the model actually saw"
        for key in ("request_fingerprint", "instructions_sha256", "observation_digest",
                    "render_digests", "parser_version", "renderer_version", "model"):
            assert key in original, key

    def test_a_rebound_fixture_is_not_labelled_recorded(self):
        """Matching fingerprints are necessary for ``recorded``, never sufficient.

        The first version of this test asserted only the implication "if it says
        recorded then the fingerprints match", which the rebuild step guarantees
        by construction -- it could not fail. The condition that actually has to
        hold is the one below: the identity must also have been witnessed at the
        call, and ``capture_kind`` is the only thing that says so.
        """
        stored = recording("MCP73831_SOT23-5_accepted.json")
        original = stored["provenance"]["original_request"]
        assert stored["fidelity"] in {"recorded", "reconstructed", "scripted"}
        if stored["fidelity"] == "recorded":
            assert stored["request_fingerprint"] == original["request_fingerprint"]
            assert original["capture_kind"] == "captured_at_call_time"


class TestAudit006ExtractionBounds:
    """Bounds must be decided before the expensive operation, not after."""

    def test_an_oversized_page_is_rejected_before_rasterising(self, tmp_path: Path):
        import pymupdf

        from ohmni.datasheet.observations import ObservationLimitError

        document = pymupdf.open()
        document.new_page(width=14000, height=14000).insert_text((20, 20), "x")
        path = tmp_path / "huge.pdf"
        document.save(path)
        document.close()
        with (
            patch("pymupdf.Page.get_pixmap", side_effect=AssertionError("rasterised")),
            pytest.raises(ObservationLimitError),
        ):
            BoundedObservationExtractor().observe(path, [1], render=True)

    def test_a_token_over_the_length_bound_is_rejected_not_truncated(self, tmp_path: Path):
        import pymupdf

        from ohmni.datasheet.observations import ObservationLimitError

        document = pymupdf.open()
        document.new_page(width=4000, height=200).insert_text((5, 100), "A" * 400, fontsize=6)
        path = tmp_path / "long.pdf"
        document.save(path)
        document.close()
        with pytest.raises(ObservationLimitError, match="token"):
            BoundedObservationExtractor().observe(path, [1])


class TestAudit005ReconstructedProvenance:
    """A reconstructed request identity is not a contemporaneous capture.

    The first remediation pass added ``original_request`` and compared it to the
    current request, which is right. What it left open is that the stored
    identity was itself *computed by the current code from the current pinned
    PDF*, one day after the provider call. Comparing that to the current request
    is a comparison of a value with itself: it can only succeed, and it cannot
    witness what the model saw.

    So the record has to say which of the two it is, and the label a consumer
    reads has to differ. ``recorded`` means an identity captured at the time of
    the call. ``reconstructed`` means the inputs are argued to be equivalent but
    nothing witnessed it. ``scripted`` means they are known to differ.
    """

    def test_the_stored_original_request_declares_how_it_was_obtained(self):
        stored = recording("MCP73831_SOT23-5_accepted.proposal.json")
        original = stored["provenance"].get("original_request")
        assert original, "the proposal must record the request identity it answers"
        assert original.get("capture_kind") in {
            "captured_at_call_time",
            "reconstructed_after_the_fact",
        }, (
            "the record must say whether this identity was witnessed at the provider "
            "call or rebuilt afterwards; without that, a rebuild is indistinguishable "
            "from a capture"
        )

    def test_a_reconstructed_identity_is_never_labelled_recorded(self):
        stored = recording("MCP73831_SOT23-5_accepted.proposal.json")
        derived = recording("MCP73831_SOT23-5_accepted.json")
        kind = stored["provenance"]["original_request"]["capture_kind"]
        assert derived["fidelity"] in {"recorded", "reconstructed", "scripted"}
        if kind == "reconstructed_after_the_fact":
            assert derived["fidelity"] != "recorded", (
                "an identity rebuilt from today's code cannot establish that the model "
                "saw these inputs; it must not be presented as a recorded response"
            )
            assert derived["fidelity_reason"], "a non-recorded fixture must say why"

    def test_a_reconstructed_fixture_states_that_fidelity_is_unevaluated(self):
        derived = recording("MCP73831_SOT23-5_accepted.json")
        if derived["fidelity"] != "recorded":
            assert "UNEVALUATED" in derived["fidelity_reason"]

    def test_the_replayed_label_reaches_the_caller(self, observations):
        """The label is only worth writing if something can read it.

        Before this, ``fidelity`` was written into the derived recording and
        read by nobody: ``RecordedVisionProvider`` took only the fingerprint and
        the proposal, so a scripted fixture replayed exactly like a recorded one.
        """
        from ohmni.adapters.vision import RecordedVisionProvider
        from ohmni.datasheet.multimodal import MultimodalCandidateExtractor

        bundle, images = observations
        provider = RecordedVisionProvider(
            directory=Path(__file__).resolve().parent / "corpus" / "recordings"
        )
        assert provider.replayed_fidelity is None, "nothing has been replayed yet"
        MultimodalCandidateExtractor(provider).extract(
            bundle, images, requested_package=PACKAGE_COLUMN
        )
        # Assert the value the fixture actually carries, not merely that the
        # attribute holds one of the legal strings: the latter is satisfied by
        # the hardcoded "scripted" default and would pass a gutted implementation.
        assert provider.replayed_fidelity == recording(
            "MCP73831_SOT23-5_accepted.json"
        )["fidelity"]
        assert provider.replayed_fidelity == "reconstructed"

    def test_the_corpus_helper_reports_the_fidelity_it_replayed(self, observations):
        from corpus import recorded_proposal_with_fidelity

        bundle, images = observations
        proposal, fidelity, unbound = recorded_proposal_with_fidelity(
            bundle, images, requested_package=PACKAGE_COLUMN
        )
        if unbound:
            pytest.skip(unbound)
        assert proposal is not None
        assert fidelity == recording("MCP73831_SOT23-5_accepted.json")["fidelity"]
        assert fidelity == "reconstructed", (
            "the pinned fixture's identity was rebuilt after the call, so the label "
            "the caller sees must say so"
        )
