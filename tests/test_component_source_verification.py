"""CS-T03: independent deterministic source verification, and its rejection corpus.

The positive case runs against a real, pinned manufacturer datasheet. When those
bytes are absent the tests skip with a reason -- a skip is not a pass, and that
is stated in the verification record rather than hidden.

The rejection corpus is the point of the task. Every case below is a proposal
that is schema-valid, addressable, internally consistent, and wrong. Each one
must fail, because "the model said so and the JSON agrees with itself" is not
evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from corpus import annotation, document_path, missing_reason, recording

from ohmni.datasheet.constraint_verifier import (
    CONSISTENCY_RELATIONS,
    UnsupportedSource,
    parse_land_pattern_table,
    parse_pin_function_table,
    verify_dimension,
    verify_extraction,
    verify_pad_ordering,
    verify_pin,
)
from ohmni.datasheet.pdf import BoundedObservationExtractor
from ohmni.domain.component_synthesis import (
    CHECKER_CONTRACT_VERSION,
    DimensionKind,
    ExtractionProposal,
    LimitColumn,
    ReceiptOutcome,
    SourceRegion,
)
from ohmni.physical.land_patterns import REQUIRED_LAND_DIMENSIONS

DOCUMENT_ID = "MCP73831-DS20001984H"
PAGES = [11, 24, 26]
PACKAGE_COLUMN = "SOT-23-5"
LAND_PAGE = 24
PIN_PAGE = 11

pytestmark = pytest.mark.corpus


@pytest.fixture(scope="module")
def corpus_source() -> Path:
    reason = missing_reason(DOCUMENT_ID)
    if reason:
        pytest.skip(reason)
    return document_path(DOCUMENT_ID)


@pytest.fixture(scope="module")
def observations(corpus_source: Path):
    bundle, _ = BoundedObservationExtractor().observe(corpus_source, PAGES)
    return bundle


@pytest.fixture(scope="module")
def proposal() -> ExtractionProposal:
    return ExtractionProposal.model_validate(
        recording("MCP73831_SOT23-5_accepted.proposal.json")["proposal"]
    )


@pytest.fixture(scope="module")
def annotated() -> dict:
    return annotation("MCP73831_SOT23-5.json")


def _dimension(proposal: ExtractionProposal, candidate_id: str):
    return next(item for item in proposal.dimensions if item.candidate_id == candidate_id)


def _pin(proposal: ExtractionProposal, candidate_id: str):
    return next(item for item in proposal.pins if item.candidate_id == candidate_id)


class TestPrintedTableGrammars:
    def test_the_land_table_is_read_from_its_printed_column_rules(self, observations, annotated):
        table = parse_land_pattern_table(observations.page(LAND_PAGE))
        assert table.grammar == "microchip_land_pattern_v1"
        assert table.units.value == "mm"
        assert table.drawing_number == annotated["selected_variant"]["drawing_number"]
        assert table.package_heading == annotated["selected_variant"]["package_description"]
        read = {
            (row.label, row.symbol): (row.limit.value, row.value_text, row.basic)
            for row in table.rows
        }
        expected = {
            (row["row_label"], row["symbol"]):
                (row["limit"], row["value"], row["basic_dimension"])
            for row in annotated["land_pattern_table"]["rows"]
        }
        assert read == expected

    def test_a_basic_dimension_spanning_the_limit_columns_is_not_read_as_nominal(
        self, observations
    ):
        table = parse_land_pattern_table(observations.page(LAND_PAGE))
        pitch = table.row("Contact Pitch", "E")
        assert pitch is not None
        assert pitch.limit is LimitColumn.BASIC
        assert pitch.basic is True

    def test_the_pin_table_keeps_each_package_column_separate(self, observations, annotated):
        table = parse_pin_function_table(observations.page(PIN_PAGE))
        assert set(table.package_columns) == {"DFN", PACKAGE_COLUMN}
        rows = {
            row.pin_numbers.get(PACKAGE_COLUMN): (row.symbol, row.function)
            for row in table.rows
            if PACKAGE_COLUMN in row.pin_numbers
        }
        expected = {
            row["pin_number"]: (row["symbol"], row["function"])
            for row in annotated["pin_function_table"]["rows"]
        }
        assert rows == expected

    def test_an_em_dash_means_the_package_has_no_such_pin(self, observations, annotated):
        table = parse_pin_function_table(observations.page(PIN_PAGE))
        for entry in annotated["pin_function_table"]["dfn_only_rows"]:
            row = table.row_for("DFN", entry["dfn_pin"])
            assert row is not None and row.symbol == entry["symbol"]
            assert PACKAGE_COLUMN not in row.pin_numbers

    def test_a_page_without_a_supported_table_is_unsupported_not_guessed(self, observations):
        with pytest.raises(UnsupportedSource):
            parse_land_pattern_table(observations.page(PIN_PAGE))
        with pytest.raises(UnsupportedSource):
            parse_pin_function_table(observations.page(LAND_PAGE))


class TestAcceptedProposal:
    def test_every_claim_is_supported_and_a_constraint_set_is_built(
        self, observations, proposal, annotated
    ):
        report = verify_extraction(
            observations, proposal,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.unsupported() == ()
        assert report.missing == ()
        assert report.verified is not None
        verified = report.verified
        assert verified.identity.orderable_part_number == (
            annotated["selected_variant"]["orderable_part_number"]
        )
        assert [(t.pin_number, t.symbol) for t in verified.terminals] == [
            (row["pin_number"], row["symbol"])
            for row in annotated["pin_function_table"]["rows"]
        ]
        assert {slot.pin_number: (slot.row, slot.column)
                for slot in verified.pad_ordering.slots} == {
            "1": (0, 0), "2": (0, 1), "3": (0, 2), "4": (1, 2), "5": (1, 0),
        }

    def test_the_printed_arithmetic_is_checked_as_its_own_receipts(
        self, observations, proposal
    ):
        report = verify_extraction(
            observations, proposal,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        relations = [r for r in report.receipts if r.checker == "CS-SOURCE-CONSISTENCY"]
        assert len(relations) == len(CONSISTENCY_RELATIONS)
        assert all(item.supported for item in relations)

    def test_receipts_bind_to_the_exact_document_and_observations(
        self, observations, proposal
    ):
        report = verify_extraction(
            observations, proposal,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        for receipt in report.receipts:
            assert receipt.document_digest == observations.document_digest
            assert receipt.observation_digest == observations.observation_digest
            assert receipt.checker_version == CHECKER_CONTRACT_VERSION


class TestRejectionCorpus:
    """Schema-valid, addressable, self-consistent -- and wrong."""

    def test_the_right_number_in_the_wrong_limit_column_fails(self, observations, proposal):
        candidate = _dimension(proposal, "dim-pad-width").model_copy(
            update={"limit": LimitColumn.MIN}
        )
        result = verify_dimension(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED
        assert any("column" in reason for reason in result.reasons)

    def test_a_value_from_a_different_row_fails(self, observations, proposal):
        """1.10 is printed on this page -- just not on the Contact Pad Width row."""
        length = _dimension(proposal, "dim-pad-length")
        candidate = _dimension(proposal, "dim-pad-width").model_copy(
            update={"value": length.value}
        )
        result = verify_dimension(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED
        assert any("row prints" in reason for reason in result.reasons)

    def test_a_row_label_paired_with_another_rows_symbol_fails(self, observations, proposal):
        candidate = _dimension(proposal, "dim-pad-width").model_copy(
            update={"dimension_symbol": "Y"}
        )
        result = verify_dimension(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED

    def test_the_same_number_in_the_wrong_unit_fails(self, observations, proposal):
        from ohmni.domain.component_synthesis import LengthValue, SourceUnit

        candidate = _dimension(proposal, "dim-pad-width").model_copy(
            update={"value": LengthValue.parse("0.60", SourceUnit.INCH)}
        )
        result = verify_dimension(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED
        assert any("declares" in reason for reason in result.reasons)

    def test_dropping_the_basic_marking_fails(self, observations, proposal):
        candidate = _dimension(proposal, "dim-contact-pitch").model_copy(
            update={"basic_dimension": False, "limit": LimitColumn.NOM}
        )
        result = verify_dimension(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED

    def test_a_package_terminal_dimension_read_off_a_land_table_is_unsupported(
        self, observations, proposal
    ):
        candidate = _dimension(proposal, "dim-pad-width").model_copy(
            update={"kind": DimensionKind.PACKAGE_TERMINAL_WIDTH}
        )
        result = verify_dimension(observations, candidate)
        assert result.outcome is ReceiptOutcome.UNSUPPORTED_SOURCE

    def test_a_dimension_cited_on_a_page_without_the_table_is_unsupported(
        self, observations, proposal
    ):
        candidate = _dimension(proposal, "dim-pad-width")
        moved = candidate.model_copy(
            update={"locator": candidate.locator.model_copy(update={"page": PIN_PAGE})}
        )
        result = verify_dimension(observations, moved)
        assert result.outcome is ReceiptOutcome.UNSUPPORTED_SOURCE

    def test_a_dimension_cited_on_an_unobserved_page_is_not_located(
        self, observations, proposal
    ):
        candidate = _dimension(proposal, "dim-pad-width")
        moved = candidate.model_copy(
            update={"locator": candidate.locator.model_copy(update={"page": 7})}
        )
        assert verify_dimension(observations, moved).outcome is ReceiptOutcome.NOT_LOCATED

    def test_a_fabricated_region_does_not_change_the_verdict_either_way(
        self, observations, proposal
    ):
        """The checker re-reads the table; it never trusts the cited rectangle."""
        candidate = _dimension(proposal, "dim-pad-width")
        moved = candidate.model_copy(update={
            "locator": candidate.locator.model_copy(
                update={"region": SourceRegion(x0=1, y0=1, x1=5, y1=5)}
            )
        })
        assert verify_dimension(observations, moved).outcome is ReceiptOutcome.SUPPORTED
        wrong = moved.model_copy(update={"limit": LimitColumn.MIN})
        assert verify_dimension(observations, wrong).outcome is ReceiptOutcome.NOT_SUPPORTED

    def test_a_pin_number_borrowed_from_the_other_package_column_fails(
        self, observations, proposal
    ):
        """DFN 8 is PROG. SOT-23-5 8 does not exist, and is not inherited."""
        candidate = _pin(proposal, "pin-sot-5").model_copy(update={"pin_number": "8"})
        result = verify_pin(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED

    def test_a_pin_row_from_a_dfn_only_row_fails_for_the_sot_package(
        self, observations, proposal
    ):
        candidate = _pin(proposal, "pin-sot-1").model_copy(
            update={"pin_number": "7", "symbol": "NC", "function": "No Connection"}
        )
        assert verify_pin(observations, candidate).outcome is ReceiptOutcome.NOT_SUPPORTED

    def test_a_swapped_pin_symbol_fails(self, observations, proposal):
        candidate = _pin(proposal, "pin-sot-1").model_copy(update={"symbol": "VSS"})
        result = verify_pin(observations, candidate)
        assert result.outcome is ReceiptOutcome.NOT_SUPPORTED
        assert any("symbol" in reason for reason in result.reasons)

    def test_an_unnamed_package_column_fails(self, observations, proposal):
        candidate = _pin(proposal, "pin-sot-1").model_copy(update={"package_column": "TO-92"})
        assert verify_pin(observations, candidate).outcome is ReceiptOutcome.NOT_SUPPORTED

    def test_a_mirrored_traversal_fails_the_printed_labels(self, observations, proposal):
        ordering = proposal.pad_ordering.model_copy(
            update={"traversal": "clockwise_from_pin_1"}
        )
        receipt, verified = verify_pad_ordering(observations, ordering, pin_count=5)
        assert receipt.outcome is ReceiptOutcome.NOT_SUPPORTED
        assert verified is None

    def test_one_printed_label_cannot_establish_a_direction(self, observations, proposal):
        ordering = proposal.pad_ordering.model_copy(update={"labelled_pins": ("1",)})
        receipt, verified = verify_pad_ordering(observations, ordering, pin_count=5)
        assert receipt.outcome is ReceiptOutcome.NOT_SUPPORTED
        assert verified is None
        assert any("fewer than two" in reason for reason in receipt.reasons)

    def test_a_wrong_pin_count_finds_no_congruent_land_group(self, observations, proposal):
        receipt, verified = verify_pad_ordering(observations, proposal.pad_ordering, pin_count=6)
        assert receipt.outcome is ReceiptOutcome.UNSUPPORTED_SOURCE
        assert verified is None

    def test_a_wrong_orderable_part_number_fails_identity(self, observations, proposal):
        identity = proposal.identity.model_copy(
            update={"orderable_part_number": "MCP73831T-2ACI/MC"}
        )
        report = verify_extraction(
            observations, proposal.model_copy(update={"identity": identity}),
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None
        assert any(r.receipt_id == "CS-IDENT-MPN" and not r.supported for r in report.receipts)

    def test_a_package_code_that_the_legend_binds_elsewhere_fails(self, observations, proposal):
        """MC is the 8-lead DFN in this document's own package legend."""
        identity = proposal.identity.model_copy(update={"package_code": "MC"})
        report = verify_extraction(
            observations, proposal.model_copy(update={"identity": identity}),
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None
        assert any(r.receipt_id == "CS-IDENT-PACKAGE" and not r.supported
                   for r in report.receipts)

    def test_a_wrong_document_revision_fails(self, observations, proposal):
        identity = proposal.identity.model_copy(update={"document_revision": "G"})
        report = verify_extraction(
            observations, proposal.model_copy(update={"identity": identity}),
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None


class TestRequiredFactMatrix:
    def test_an_all_pass_report_over_too_few_claims_cannot_verify(
        self, observations, proposal
    ):
        """Every claim supported is not the same as every required fact present."""
        trimmed = proposal.model_copy(update={
            "dimensions": tuple(
                item for item in proposal.dimensions
                if item.kind is not DimensionKind.LAND_PAD_WIDTH
            )
        })
        report = verify_extraction(
            observations, trimmed,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.unsupported() == ()
        assert report.verified is None
        assert any("land_pad_width" in item for item in report.missing)

    def test_a_missing_pin_blocks_the_constraint_set(self, observations, proposal):
        trimmed = proposal.model_copy(update={"pins": proposal.pins[:-1]})
        report = verify_extraction(
            observations, trimmed,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None
        assert any("verified terminals" in item for item in report.missing)

    def test_an_empty_proposal_is_never_admitted(self, observations, proposal):
        empty = proposal.model_copy(update={
            "dimensions": (), "pins": (), "pad_ordering": None,
        })
        report = verify_extraction(
            observations, empty,
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None
        assert report.quarantined
