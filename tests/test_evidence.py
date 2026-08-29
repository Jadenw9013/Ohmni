"""Provenance: what a claim's status is allowed to be, and who decides."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ohmni.domain import (
    Claim,
    ClaimStatus,
    DocumentRef,
    Evidence,
    EvidenceKind,
    Quantity,
    assumed_evidence,
    calculated_evidence,
    catalog_evidence,
    datasheet_evidence,
    status_rank,
)

DOC = DocumentRef(document_id="doc-1", part_number="BME280", manufacturer="Bosch Sensortec")


class TestEvidenceRequiresProvenance:
    def test_datasheet_evidence_needs_a_citation(self):
        with pytest.raises(ValidationError, match="datasheet evidence requires"):
            Evidence(kind=EvidenceKind.DATASHEET, label="VDD range")

    def test_datasheet_evidence_needs_a_page(self):
        with pytest.raises(ValidationError, match="page"):
            Evidence(
                kind=EvidenceKind.DATASHEET,
                label="VDD range",
                source_id="doc-1",
                snippet="1.71 to 3.6 V",
            )

    def test_datasheet_evidence_needs_a_snippet(self):
        with pytest.raises(ValidationError, match="snippet"):
            Evidence(kind=EvidenceKind.DATASHEET, label="VDD range", source_id="doc-1", page=10)

    def test_calculation_must_show_its_working(self):
        with pytest.raises(ValidationError, match="formula and inputs"):
            Evidence(kind=EvidenceKind.CALCULATION, label="LED current")

    def test_simulation_needs_a_run_id(self):
        with pytest.raises(ValidationError, match="run id"):
            Evidence(kind=EvidenceKind.SIMULATION, label="operating point")

    def test_bench_needs_a_measurement(self):
        with pytest.raises(ValidationError, match="measurement id"):
            Evidence(kind=EvidenceKind.BENCH, label="rail voltage", source_id="m-1")

    def test_a_complete_citation_is_accepted(self):
        e = datasheet_evidence(
            "VDD operating range",
            document=DOC,
            page=10,
            snippet="VDD supply voltage 1.71 V to 3.6 V",
            quantity=Quantity.volts(3.3),
        )
        assert e.status is ClaimStatus.DATASHEET_SUPPORTED


class TestStatusIsDerived:
    def test_status_is_not_a_settable_field(self):
        e = assumed_evidence("something", detail="because")
        with pytest.raises((AttributeError, ValidationError)):
            e.status = ClaimStatus.BENCH_VERIFIED  # type: ignore[misc]

    def test_failed_citation_supports_nothing(self):
        # A snippet that was checked against the document and not found means
        # the citation is fabricated. It must not confer datasheet support.
        e = Evidence(
            kind=EvidenceKind.DATASHEET,
            label="VDD range",
            document=DOC,
            source_id="doc-1",
            page=10,
            snippet="VDD supply voltage 1.71 V to 3.6 V",
            snippet_verified=False,
        )
        assert e.status is ClaimStatus.UNKNOWN
        assert not e.provenance_machine_verified

    def test_unchecked_citation_is_supported_but_not_machine_verified(self):
        e = datasheet_evidence("VDD range", document=DOC, page=10, snippet="1.71 V to 3.6 V")
        assert e.status is ClaimStatus.DATASHEET_SUPPORTED
        assert e.snippet_verified is None
        assert not e.provenance_machine_verified

    def test_verified_citation_is_machine_verified(self):
        e = datasheet_evidence(
            "VDD range", document=DOC, page=10, snippet="1.71 V to 3.6 V"
        ).model_copy(update={"snippet_verified": True})
        assert e.provenance_machine_verified

    @pytest.mark.parametrize(
        ("kind_evidence", "expected"),
        [
            (assumed_evidence("x", detail="d"), ClaimStatus.ASSUMED),
            (calculated_evidence("x", detail="a + b"), ClaimStatus.CALCULATED),
            (catalog_evidence("x", document=DOC, page=1), ClaimStatus.CATALOG_REPORTED),
        ],
    )
    def test_kind_determines_status(self, kind_evidence, expected):
        assert kind_evidence.status is expected

    def test_hand_entered_catalog_facts_rank_below_a_real_citation(self):
        # This is the honesty property that keeps the seed catalog from
        # masquerading as datasheet-verified data.
        hand = catalog_evidence("VDD range", document=DOC, page=10)
        cited = datasheet_evidence("VDD range", document=DOC, page=10, snippet="1.71 V to 3.6 V")
        assert status_rank(hand.status) < status_rank(cited.status)


class TestClaim:
    def test_no_evidence_means_unknown(self):
        claim = Claim(subject="U3 VDD range")
        assert claim.status is ClaimStatus.UNKNOWN
        assert not claim.is_supported
        assert claim.strongest_evidence() is None

    def test_strongest_evidence_wins(self):
        claim = Claim(
            subject="LED current",
            quantity=Quantity.amps(0.0047),
            evidence=[
                assumed_evidence("guess", detail="rule of thumb"),
                calculated_evidence("ohms law", detail="(3.3-2.1)/330"),
            ],
        )
        assert claim.status is ClaimStatus.CALCULATED
        assert claim.strongest_evidence() is not None
        assert claim.strongest_evidence().kind is EvidenceKind.CALCULATION

    def test_bench_measurement_outranks_everything(self):
        claim = Claim(
            subject="3V3 rail",
            evidence=[
                datasheet_evidence("nominal", document=DOC, page=4, snippet="3.3 V"),
                Evidence(
                    kind=EvidenceKind.BENCH,
                    label="measured",
                    source_id="bench-run-1",
                    quantity=Quantity.volts(3.29),
                ),
            ],
        )
        assert claim.status is ClaimStatus.BENCH_VERIFIED
