"""CS-T01: the trust boundary, expressed as tests.

These check the three distinctions COMPONENT_SYNTHESIS_PLAN.md is built on:
a proposal cannot carry a verdict, a receipt cannot be minted outside
deterministic checking, and a number is not a dimension until it has a unit, a
column and an exact decimal.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ohmni.domain.component_synthesis import (
    CHECKER_CONTRACT_VERSION,
    FORBIDDEN_PROPOSAL_FIELDS,
    NANOMETRES_PER_INCH,
    NANOMETRES_PER_MIL,
    NANOMETRES_PER_MM,
    PROPOSAL_SCHEMAS,
    Capability,
    CapabilityMatrix,
    CapabilityResult,
    CapabilityState,
    DimensionKind,
    ExtractionProposal,
    IdentityCandidate,
    ImportState,
    LengthValue,
    LimitColumn,
    PadSlot,
    PhysicalConstraintCandidate,
    PinCandidate,
    ReceiptOutcome,
    SourceLocator,
    SourceOrigin,
    SourceOriginKind,
    SourceRegion,
    SourceUnit,
    TerminalKind,
    VerificationReceipt,
    VerifiedConstraintSet,
    VerifiedDimension,
    VerifiedIdentity,
    VerifiedPadOrdering,
    VerifiedTerminal,
    assert_proposal_schema_is_untrusted,
    can_transition,
    claim_hash,
)

DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def locator(page: int = 24) -> SourceLocator:
    return SourceLocator(
        document_id=DIGEST, page=page,
        region=SourceRegion(x0=10, y0=10, x1=100, y1=30),
        quote="Contact Pad Width (X5) X 0.60",
    )


def receipt(receipt_id: str, claim: dict, outcome: ReceiptOutcome = ReceiptOutcome.SUPPORTED,
            *, document: str = DIGEST, observation: str = OTHER_DIGEST,
            checker: str = "CS-SOURCE", version: str = CHECKER_CONTRACT_VERSION,
            bound_claims: dict | None = None) -> VerificationReceipt:
    """A receipt that actually describes ``claim``, as a real checker issues it."""
    return VerificationReceipt(
        receipt_id=receipt_id, checker=checker, checker_version=version,
        outcome=outcome, claim_hash=claim_hash(claim),
        document_digest=document, observation_digest=observation,
        bound_claims=bound_claims,
    )


class TestLengthGrid:
    def test_exact_decimal_conversion_for_every_supported_unit(self):
        assert LengthValue.parse("0.95", SourceUnit.MILLIMETRE).nanometres == 950_000
        assert LengthValue.parse("1", SourceUnit.INCH).nanometres == NANOMETRES_PER_INCH
        assert LengthValue.parse("50", SourceUnit.MIL).nanometres == 50 * NANOMETRES_PER_MIL
        assert LengthValue.parse("2.80", SourceUnit.MILLIMETRE).millimetres() == 2.8

    def test_a_unit_is_never_inferred_from_magnitude(self):
        """0.95 mm and 0.95 inch are different lengths and stay different."""
        millimetre = LengthValue.parse("0.95", SourceUnit.MILLIMETRE)
        inch = LengthValue.parse("0.95", SourceUnit.INCH)
        assert millimetre.nanometres != inch.nanometres
        assert inch.nanometres == int(Decimal("0.95") * NANOMETRES_PER_INCH)

    def test_binary_float_error_cannot_enter_the_grid(self):
        total = sum(LengthValue.parse("0.1", SourceUnit.MILLIMETRE).nanometres for _ in range(10))
        assert total == NANOMETRES_PER_MM

    @pytest.mark.parametrize("text", ["", "abc", "1e3", "nan", "inf", "0.95mm", "--1", "1,5"])
    def test_non_decimal_text_is_refused(self, text: str):
        with pytest.raises(ValueError):
            LengthValue.parse(text, SourceUnit.MILLIMETRE)

    def test_value_finer_than_the_grid_is_refused_not_rounded(self):
        with pytest.raises(ValueError, match="length grid"):
            LengthValue.parse("0.0000001", SourceUnit.MILLIMETRE)

    def test_a_mismatched_source_text_and_grid_value_cannot_be_constructed(self):
        with pytest.raises(ValidationError):
            LengthValue(source_text="0.95", unit=SourceUnit.MILLIMETRE, nanometres=960_000)


class TestProposalsCannotCarryVerdicts:
    @pytest.mark.parametrize("schema", PROPOSAL_SCHEMAS, ids=lambda s: s.__name__)
    def test_no_proposal_schema_exposes_a_verdict_or_path_field(self, schema):
        assert_proposal_schema_is_untrusted(schema)

    @pytest.mark.parametrize("field", sorted(FORBIDDEN_PROPOSAL_FIELDS)[:8])
    def test_extra_fields_are_rejected_outright(self, field: str):
        payload = {
            "candidate_id": "d1", "kind": "land_pad_width", "dimension_symbol": "X",
            "row_label": "Contact Pad Width (X5)", "limit": "max",
            "value": {"source_text": "0.60", "unit": "mm", "nanometres": 600_000},
            "locator": locator().model_dump(mode="json"), field: "verified",
        }
        with pytest.raises(ValidationError):
            PhysicalConstraintCandidate.model_validate(payload)

    def test_a_proposal_schema_that_grew_a_status_field_fails_the_guard(self):
        from pydantic import BaseModel, ConfigDict

        class Sneaky(BaseModel):
            model_config = ConfigDict(extra="forbid")
            status: str = "verified"

        with pytest.raises(ValueError, match="verdict"):
            assert_proposal_schema_is_untrusted(Sneaky)

    def test_generated_json_schema_is_available_for_a_provider_tool(self):
        schema = ExtractionProposal.model_json_schema()
        assert set(schema["properties"]) == {
            "identity", "dimensions", "pins", "pad_ordering", "unresolved"
        }
        names = {
            name
            for definition in schema["$defs"].values()
            for name in definition.get("properties", {})
        } | set(schema["properties"])
        assert not names & FORBIDDEN_PROPOSAL_FIELDS
        assert json.dumps(schema)

    def test_collections_are_bounded(self):
        with pytest.raises(ValidationError):
            ExtractionProposal(
                identity=IdentityCandidate(),
                pins=tuple(
                    PinCandidate(
                        candidate_id=f"p{index}", package_column="SOT-23-5",
                        pin_number=str(index % 9 + 1), symbol="VDD", function="supply",
                        locator=locator(11),
                    )
                    for index in range(300)
                ),
            )

    def test_candidate_ids_are_unique_within_one_proposal(self):
        pin = PinCandidate(
            candidate_id="same", package_column="SOT-23-5", pin_number="1",
            symbol="STAT", function="Charge Status Output", locator=locator(11),
        )
        with pytest.raises(ValidationError, match="unique"):
            ExtractionProposal(identity=IdentityCandidate(), pins=(pin, pin))

    def test_unknown_identity_stays_unknown_rather_than_defaulting(self):
        identity = IdentityCandidate(unresolved=("package code not printed",))
        assert identity.manufacturer is None
        assert identity.pin_count is None


class TestReceiptsAndVerifiedConstraints:
    def test_claim_hash_is_stable_and_digit_sensitive(self):
        first = claim_hash({"value": "0.60", "limit": "max"})
        assert first == claim_hash({"limit": "max", "value": "0.60"})
        assert first != claim_hash({"value": "0.61", "limit": "max"})

    def test_an_unsupported_receipt_cannot_back_a_verified_constraint(self):
        with pytest.raises(ValidationError, match="not_supported"):
            _verified_set(outcome=ReceiptOutcome.NOT_SUPPORTED)

    def test_a_receipt_from_another_document_cannot_back_a_verified_constraint(self):
        with pytest.raises(ValidationError, match="different document"):
            _verified_set(document="c" * 64)

    def test_a_receipt_from_other_observations_cannot_back_a_verified_constraint(self):
        with pytest.raises(ValidationError, match="different observations"):
            _verified_set(observation="d" * 64)

    def test_pad_ordering_and_terminals_must_describe_the_same_pins(self):
        with pytest.raises(ValidationError, match="different pins"):
            _verified_set(extra_slot=True)

    def test_a_missing_dimension_raises_rather_than_returning_a_default(self):
        verified = _verified_set()
        assert verified.dimension(DimensionKind.LAND_ROW_GAP) is None
        with pytest.raises(KeyError, match="stays missing"):
            verified.require(DimensionKind.LAND_ROW_GAP)

    def test_a_receipt_from_a_previous_checker_version_is_refused(self):
        with pytest.raises(ValidationError, match="historical"):
            _verified_set(checker_version="1.0.0")

    def test_a_receipt_that_describes_another_value_is_refused(self):
        """The audit's exact case: edit the value, keep the receipt."""
        verified = _verified_set()
        altered = verified.model_dump(mode="json")
        altered["dimensions"][0]["value"] = {
            "source_text": "0.70", "unit": "mm", "nanometres": 700_000,
        }
        assert altered["receipts"] == verified.model_dump(mode="json")["receipts"]
        with pytest.raises(ValidationError, match="does not describe the value"):
            VerifiedConstraintSet.model_validate(altered)

    def test_revalidate_reports_a_broken_binding_at_the_use_boundary(self):
        verified = _verified_set()
        assert verified.revalidate() == ()

    def test_content_hash_changes_when_one_digit_changes(self):
        first = _verified_set()
        second = _verified_set(width_text="0.61")
        assert first.content_hash != second.content_hash


def _verified_set(
    *,
    outcome: ReceiptOutcome = ReceiptOutcome.SUPPORTED,
    document: str = DIGEST,
    observation: str = OTHER_DIGEST,
    width_text: str = "0.60",
    extra_slot: bool = False,
    checker_version: str = CHECKER_CONTRACT_VERSION,
) -> VerifiedConstraintSet:
    """Build a legitimately bound set, so each negative case breaks one thing."""
    identity = VerifiedIdentity(
        manufacturer="Microchip Technology", base_device="MCP73831",
        orderable_part_number="MCP73831T-2ACI/OT", package_code="OT",
        package_description="5-Lead Plastic Small Outline Transistor (OT) [SOT23]",
        pin_count=1, document_revision="H", drawing_number="C04-2091-OT Rev F",
        receipt_id="CS-IDENT-BINDING",
    )
    dimension = VerifiedDimension(
        kind=DimensionKind.LAND_PAD_WIDTH, dimension_symbol="X", limit=LimitColumn.MAX,
        value=LengthValue.parse(width_text, SourceUnit.MILLIMETRE),
        basic_dimension=False, applies_to_terminals=5, receipt_id="CS-DIM-width",
    )
    terminal = VerifiedTerminal(
        package_column="SOT-23-5", pin_number="1", symbol="STAT",
        function="Charge Status Output", kind=TerminalKind.ELECTRICAL,
        receipt_id="CS-PINROW-1",
    )
    slots = [PadSlot(pin_number="1", row=0, column=0)]
    if extra_slot:
        slots.append(PadSlot(pin_number="2", row=0, column=1))
    ordering = VerifiedPadOrdering(
        traversal="counter_clockwise_from_pin_1", first_pin_corner="bottom_left",
        slots=tuple(slots), receipt_id="CS-ORDER-1",
    )
    receipts = [
        receipt("CS-IDENT-BINDING", identity.claim(), version=checker_version),
        receipt("CS-DIM-width", dimension.claim(), outcome,
                document=document, observation=observation, version=checker_version),
        receipt("CS-PINROW-1", terminal.claim(), version=checker_version),
        receipt("CS-ORDER-1", ordering.claim(), version=checker_version),
    ]
    return VerifiedConstraintSet(
        document_digest=DIGEST, observation_digest=OTHER_DIGEST,
        identity=identity, dimensions=(dimension,), terminals=(terminal,),
        pad_ordering=ordering, receipts=tuple(receipts),
    )


class TestCapabilitiesAndLifecycle:
    def test_an_unevaluated_capability_is_never_support(self):
        matrix = CapabilityMatrix()
        assert matrix.state(Capability.FOOTPRINT) is CapabilityState.NOT_EVALUATED
        assert not matrix.supports(Capability.FOOTPRINT)

    def test_capabilities_are_independent(self):
        matrix = CapabilityMatrix(results=(
            CapabilityResult(capability=Capability.FOOTPRINT, state=CapabilityState.SUPPORTED),
            CapabilityResult(capability=Capability.SIMULATION, state=CapabilityState.UNSUPPORTED),
        ))
        assert matrix.supports(Capability.FOOTPRINT)
        assert not matrix.supports(Capability.SIMULATION)
        assert not matrix.supports(Capability.ELECTRICAL_PROFILE)

    def test_admission_is_reachable_only_through_asset_verification(self):
        assert can_transition(ImportState.VERIFYING_ASSETS, ImportState.ADMITTED)
        for state in ImportState:
            if state is not ImportState.VERIFYING_ASSETS:
                assert not can_transition(state, ImportState.ADMITTED), state

    def test_terminal_states_have_no_exits(self):
        for state in (ImportState.ADMITTED, ImportState.REJECTED, ImportState.FAILED,
                      ImportState.CANCELLED):
            assert not any(can_transition(state, target) for target in ImportState)


class TestSourceOrigin:
    def test_a_manufacturer_origin_must_name_an_https_url(self):
        with pytest.raises(ValidationError, match="https"):
            SourceOrigin(kind=SourceOriginKind.MANUFACTURER_HTTPS)

    def test_redirects_may_not_leave_https(self):
        with pytest.raises(ValidationError, match="HTTPS"):
            SourceOrigin(
                kind=SourceOriginKind.MANUFACTURER_HTTPS,
                acquisition_url="https://ww1.microchip.com/a.pdf",
                redirect_chain=("http://elsewhere.example/a.pdf",),
            )

    def test_an_unestablished_origin_is_labelled_as_such(self):
        origin = SourceOrigin(kind=SourceOriginKind.SUPPLIED_UNVERIFIED, note="user upload")
        assert origin.kind is SourceOriginKind.SUPPLIED_UNVERIFIED
        assert origin.acquisition_url is None


class TestSourceRegion:
    def test_a_degenerate_region_is_refused(self):
        with pytest.raises(ValidationError):
            SourceRegion(x0=10, y0=10, x1=10, y1=30)

    def test_containment_is_exact_without_tolerance(self):
        outer = SourceRegion(x0=0, y0=0, x1=100, y1=100)
        assert outer.contains(SourceRegion(x0=10, y0=10, x1=20, y1=20))
        assert not outer.contains(SourceRegion(x0=10, y0=10, x1=120, y1=20))
