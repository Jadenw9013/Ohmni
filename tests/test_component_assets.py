"""CS-T04: generated CAD, independently measured, and its mutation corpus.

The order of the checks is the claim. Source verification happens first and
without any knowledge of CAD; geometry is compiled from the verified constraints
only; and the measurements that check it are parsed back out of the emitted
bytes. The mutation tests exist to prove each of those links separately -- in
particular that changing the model's claim *and* the generated footprint
together still fails, because the source check never consults either one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from corpus import annotation, document_path, missing_reason, recorded_proposal

from ohmni.adapters import ToolStatus
from ohmni.datasheet.constraint_verifier import verify_extraction
from ohmni.datasheet.pdf import BoundedObservationExtractor
from ohmni.domain.component_synthesis import (
    Capability,
    CapabilityState,
    DimensionKind,
    LengthValue,
    SourceUnit,
)
from ohmni.eda.kicad.component_asset_parser import (
    AssetParseError,
    measure_footprint,
    measure_symbol_library,
    nanometres,
    parse,
)
from ohmni.eda.kicad.component_assets import (
    AssetSerializationError,
    millimetres,
    render_footprint,
    render_symbol_library,
    write_asset,
)
from ohmni.eda.kicad.component_harness import export_footprint_svg, export_symbol_svg
from ohmni.physical.component_asset_verifier import verify_assets
from ohmni.physical.land_patterns import (
    REQUIRED_LAND_DIMENSIONS,
    LandPad,
    LandPatternError,
    LandPatternMethod,
    build_land_pattern,
    build_symbol,
    cad_capabilities,
)

DOCUMENT_ID = "MCP73831-DS20001984H"
PAGES = [11, 24, 26]
PACKAGE_COLUMN = "SOT-23-5"


@pytest.fixture(scope="module")
def verified():
    reason = missing_reason(DOCUMENT_ID)
    if reason:
        pytest.skip(reason)
    bundle, images = BoundedObservationExtractor().observe(
        document_path(DOCUMENT_ID), PAGES, render=True
    )
    proposal, unbound = recorded_proposal(
        bundle, images, requested_package=PACKAGE_COLUMN
    )
    if unbound:
        pytest.skip(unbound)
    report = verify_extraction(
        bundle, proposal,
        required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
    )
    assert report.verified is not None, report.missing
    return report.verified


@pytest.fixture(scope="module")
def assets(verified):
    land_pattern = build_land_pattern(verified)
    symbol = build_symbol(verified)
    return land_pattern, symbol, render_footprint(land_pattern), render_symbol_library(symbol)


def _report(verified, land_pattern, symbol, footprint_text, symbol_text):
    import hashlib

    footprint_digest = hashlib.sha256(footprint_text.encode("utf-8")).hexdigest()
    symbol_digest = hashlib.sha256(symbol_text.encode("utf-8")).hexdigest()
    return verify_assets(
        verified,
        measure_footprint(footprint_text),
        measure_symbol_library(symbol_text),
        land_pattern=land_pattern, symbol_definition=symbol,
        footprint_digest=footprint_digest, symbol_digest=symbol_digest,
        recorded_footprint_digest=footprint_digest, recorded_symbol_digest=symbol_digest,
    )


pytestmark = pytest.mark.corpus


class TestGeneratedGeometry:
    def test_land_geometry_matches_the_independent_annotation(self, assets):
        land_pattern, _, _, _ = assets
        expected = annotation("MCP73831_SOT23-5.json")["expected_land_geometry_mm"]
        measured = {
            pad.number: (round(pad.centre_x_nm / 1e6, 6), round(pad.centre_y_nm / 1e6, 6))
            for pad in land_pattern.pads
        }
        assert measured == {
            item["number"]: (item["x_mm"], item["y_mm"]) for item in expected["pads"]
        }
        assert {pad.width_nm for pad in land_pattern.pads} == {
            int(expected["pad_width_x_mm"] * 1e6)
        }
        assert {pad.height_nm for pad in land_pattern.pads} == {
            int(expected["pad_length_y_mm"] * 1e6)
        }

    def test_generation_is_byte_reproducible(self, verified):
        first = render_footprint(build_land_pattern(verified))
        second = render_footprint(build_land_pattern(verified))
        assert first == second
        assert "\r" not in first

    def test_no_package_body_is_invented(self, assets):
        land_pattern, _, footprint_text, _ = assets
        measured = measure_footprint(footprint_text)
        assert measured.layer_graphics("F.Fab") == ()
        assert any("body" in item for item in land_pattern.limitations)

    def test_the_artifact_carries_its_own_limitations(self, assets):
        _, _, footprint_text, symbol_text = assets
        footprint = measure_footprint(footprint_text)
        symbol = measure_symbol_library(symbol_text)
        assert any("IPC" in value for value in footprint.properties.values())
        assert any("unspecified" in value for value in symbol.properties.values())

    def test_an_unimplemented_land_method_is_refused_not_approximated(self, verified):
        with pytest.raises(LandPatternError, match="not implemented"):
            build_land_pattern(verified, method=LandPatternMethod.STANDARDS_DERIVED)

    def test_a_missing_required_dimension_blocks_the_footprint(self, verified):
        trimmed = verified.model_copy(update={
            "dimensions": tuple(
                item for item in verified.dimensions
                if item.kind is not DimensionKind.LAND_CONTACT_PITCH
            )
        })
        with pytest.raises(LandPatternError, match="missing"):
            build_land_pattern(trimmed)

    def test_capabilities_do_not_claim_what_has_not_run(self, verified):
        matrix = cad_capabilities(verified, land_pattern_built=True, symbol_built=True)
        assert matrix.supports(Capability.FOOTPRINT)
        assert matrix.supports(Capability.SYMBOL)
        assert matrix.state(Capability.ELECTRICAL_PROFILE) is CapabilityState.NOT_EVALUATED
        assert matrix.state(Capability.SIMULATION) is CapabilityState.UNSUPPORTED


class TestIndependentMeasurement:
    def test_every_check_passes_on_the_generated_pair(self, verified, assets):
        report = _report(verified, *assets)
        assert report.passed, report.failures()
        assert len(report.findings) >= 25

    def test_an_empty_report_is_not_a_pass(self):
        from ohmni.physical.component_asset_verifier import AssetVerificationReport

        assert not AssetVerificationReport(findings=()).passed

    def test_the_measurements_come_from_the_bytes_not_the_generator(self, verified, assets):
        """Editing only the text changes the measurement, so the file is the oracle."""
        land_pattern, _symbol, footprint_text, _symbol_text = assets
        tampered = footprint_text.replace("(size 0.6 1.1)", "(size 0.7 1.1)", 1)
        assert tampered != footprint_text
        assert measure_footprint(tampered).pad("1").width_nm == 700_000
        assert land_pattern.pads[0].width_nm == 600_000

    @pytest.mark.parametrize("payload", [
        "(footprint",
        '(footprint "x" (version 1) (generator "g") (generator_version "1") (layer "F.Cu")))',
        "not an s-expression",
        "",
    ])
    def test_malformed_bytes_fail_closed(self, payload: str):
        with pytest.raises(AssetParseError):
            measure_footprint(payload)

    def test_excess_nesting_is_refused(self):
        payload = "(footprint " + "(a " * 200 + ")" * 200 + ")"
        with pytest.raises(AssetParseError, match="nesting"):
            parse(payload)

    def test_a_duplicated_property_is_refused(self, assets):
        _, _, footprint_text, _ = assets
        duplicated = footprint_text.replace(
            '\t(attr smd)',
            '\t(property "Reference" "REF**"\n\t\t(at 0 0 0)\n\t\t(layer "F.SilkS")\n\t)\n\t(attr smd)',
            1,
        )
        with pytest.raises(AssetParseError, match="duplicated property"):
            measure_footprint(duplicated)

    def test_duplicate_pad_numbers_are_refused(self, assets):
        _, _, footprint_text, _ = assets
        duplicated = footprint_text.replace('(pad "2"', '(pad "1"', 1)
        with pytest.raises(AssetParseError, match="duplicate pad numbers"):
            measure_footprint(duplicated)

    @pytest.mark.parametrize("text", ["nan", "inf", "1e5", "0.0000001", "--1"])
    def test_non_finite_or_sub_grid_numbers_are_refused(self, text: str):
        with pytest.raises(AssetParseError):
            nanometres(text)

    def test_the_serializer_refuses_what_it_cannot_represent_exactly(self):
        with pytest.raises(AssetSerializationError):
            millimetres(0.95)

    def test_millimetre_formatting_is_exact(self):
        assert millimetres(950_000) == "0.95"
        assert millimetres(-1_400_000) == "-1.4"
        assert millimetres(0) == "0"
        assert millimetres(1) == "0.000001"


class TestMutationCorpus:
    """Deliberately incorrect geometry must be rejected, every time."""

    def _mutated(self, verified, assets, **changes):
        land_pattern, symbol, _, symbol_text = assets
        pads = list(land_pattern.pads)
        index = changes.pop("index", 0)
        pads[index] = pads[index].model_copy(update=changes)
        mutated = land_pattern.model_copy(update={"pads": tuple(pads)})
        return _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)

    def test_a_wrong_pad_width_is_rejected(self, verified, assets):
        report = self._mutated(verified, assets, width_nm=700_000)
        assert not report.passed
        assert {item.check_id for item in report.failures()} >= {"CS-DIMENSION-001"}

    def test_a_wrong_pad_length_is_rejected(self, verified, assets):
        report = self._mutated(verified, assets, height_nm=1_200_000)
        assert not report.passed
        assert "CS-DIMENSION-001" in {item.check_id for item in report.failures()}

    def test_a_wrong_pitch_is_rejected(self, verified, assets):
        """One land moved by 0.05 mm: right size, right row, wrong pitch."""
        report = self._mutated(verified, assets, index=1, centre_x_nm=50_000)
        assert not report.passed
        failed = {item.check_id for item in report.failures()}
        assert "CS-DIMENSION-004" in failed

    def test_a_wrong_row_spacing_is_rejected(self, verified, assets):
        land_pattern, symbol, _, symbol_text = assets
        pads = tuple(
            pad.model_copy(update={"centre_y_nm": pad.centre_y_nm + 100_000})
            if pad.centre_y_nm < 0 else pad
            for pad in land_pattern.pads
        )
        mutated = land_pattern.model_copy(update={"pads": pads})
        report = _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)
        assert not report.passed
        assert "CS-DIMENSION-003" in {item.check_id for item in report.failures()}

    def test_a_mirrored_footprint_is_rejected(self, verified, assets):
        """Identical pitch, sizes and span; only the handedness differs."""
        land_pattern, symbol, _, symbol_text = assets
        pads = tuple(
            pad.model_copy(update={"centre_y_nm": -pad.centre_y_nm})
            for pad in land_pattern.pads
        )
        mutated = land_pattern.model_copy(update={"pads": pads})
        report = _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)
        assert not report.passed
        assert "CS-ORIENTATION-006" in {item.check_id for item in report.failures()}

    def test_reversed_numbering_is_rejected(self, verified, assets):
        land_pattern, symbol, _, symbol_text = assets
        renumbered = {"1": "5", "2": "4", "3": "3", "4": "2", "5": "1"}
        pads = tuple(
            pad.model_copy(update={"number": renumbered[pad.number]})
            for pad in land_pattern.pads
        )
        mutated = land_pattern.model_copy(update={"pads": pads})
        report = _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)
        assert not report.passed
        assert {"CS-ORIENTATION-003"} & {item.check_id for item in report.failures()}

    def test_a_missing_land_is_rejected(self, verified, assets):
        land_pattern, symbol, _, symbol_text = assets
        mutated = land_pattern.model_copy(update={"pads": land_pattern.pads[:-1]})
        report = _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)
        assert not report.passed
        assert "CS-PIN-001" in {item.check_id for item in report.failures()}

    def test_an_extra_land_is_rejected(self, verified, assets):
        land_pattern, symbol, _, symbol_text = assets
        extra = LandPad(number="6", centre_x_nm=2_000_000, centre_y_nm=1_400_000,
                        width_nm=600_000, height_nm=1_100_000)
        mutated = land_pattern.model_copy(update={"pads": (*land_pattern.pads, extra)})
        report = _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)
        assert not report.passed
        assert "CS-PIN-001" in {item.check_id for item in report.failures()}

    def test_overlapping_lands_are_rejected(self, verified, assets):
        report = self._mutated(verified, assets, index=1, centre_x_nm=-900_000)
        assert not report.passed
        failed = {item.check_id for item in report.failures()}
        assert failed & {"CS-GEOMETRY-001", "CS-GEOMETRY-002"}

    def test_a_symbol_pin_swap_is_rejected(self, verified, assets):
        land_pattern, symbol, footprint_text, _ = assets
        pins = list(symbol.pins)
        pins[0] = pins[0].model_copy(update={"name": pins[1].name})
        mutated = symbol.model_copy(update={"pins": tuple(pins)})
        report = _report(verified, land_pattern, mutated, footprint_text,
                         render_symbol_library(mutated))
        assert not report.passed
        assert "CS-PIN-003" in {item.check_id for item in report.failures()}

    def test_a_pin_claiming_an_unestablished_electrical_type_is_rejected(
        self, verified, assets
    ):
        land_pattern, symbol, footprint_text, symbol_text = assets
        tampered = symbol_text.replace("(pin unspecified line", "(pin power_in line", 1)
        report = verify_assets(
            verified, measure_footprint(footprint_text), measure_symbol_library(tampered),
            land_pattern=land_pattern, symbol_definition=symbol,
            footprint_digest="a" * 64, symbol_digest="b" * 64,
            recorded_footprint_digest="a" * 64, recorded_symbol_digest="b" * 64,
        )
        assert not report.passed
        assert "CS-PIN-004" in {item.check_id for item in report.failures()}

    def test_a_stale_digest_is_rejected(self, verified, assets):
        land_pattern, symbol, footprint_text, symbol_text = assets
        report = verify_assets(
            verified, measure_footprint(footprint_text), measure_symbol_library(symbol_text),
            land_pattern=land_pattern, symbol_definition=symbol,
            footprint_digest="a" * 64, symbol_digest="b" * 64,
            recorded_footprint_digest="c" * 64, recorded_symbol_digest="b" * 64,
        )
        assert not report.passed
        assert "CS-LINEAGE-001" in {item.check_id for item in report.failures()}

    def test_assets_built_from_different_constraints_are_rejected(self, verified, assets):
        land_pattern, symbol, _footprint_text, symbol_text = assets
        mutated = land_pattern.model_copy(update={"constraint_hash": "f" * 64})
        report = _report(verified, mutated, symbol, render_footprint(mutated), symbol_text)
        assert not report.passed
        failed = {item.check_id for item in report.failures()}
        assert failed & {"CS-LINEAGE-003", "CS-LINEAGE-005"}

    def test_changing_the_claim_and_the_cad_together_still_fails_the_source_check(self):
        """The source check never reads the proposal's own story or the CAD.

        This is the case COMPONENT_SYNTHESIS_PLAN.md singles out: a model that
        claims a 0.70 mm land and a generator that faithfully produces one agree
        with each other perfectly. The document still says 0.60.
        """
        reason = missing_reason(DOCUMENT_ID)
        if reason:
            pytest.skip(reason)
        bundle, images = BoundedObservationExtractor().observe(
            document_path(DOCUMENT_ID), PAGES, render=True
        )
        proposal, unbound = recorded_proposal(
            bundle, images, requested_package=PACKAGE_COLUMN
        )
        if unbound:
            pytest.skip(unbound)
        dimensions = tuple(
            item.model_copy(
                update={"value": LengthValue.parse("0.70", SourceUnit.MILLIMETRE)}
            )
            if item.kind is DimensionKind.LAND_PAD_WIDTH else item
            for item in proposal.dimensions
        )
        report = verify_extraction(
            bundle, proposal.model_copy(update={"dimensions": dimensions}),
            required_dimensions=REQUIRED_LAND_DIMENSIONS, package_column=PACKAGE_COLUMN,
        )
        assert report.verified is None
        assert any(
            r.receipt_id == "CS-DIM-dim-pad-width" and not r.supported for r in report.receipts
        )
        # The relation the drawing prints about itself is then not checkable at
        # all, because its input was refused. That is recorded as a limitation,
        # never as a relation that held.
        assert not any(
            r.receipt_id == "CS-CONSIST-adjacent_gap_is_pitch_minus_pad_width"
            for r in report.receipts
        )
        assert any(
            "adjacent_gap_is_pitch_minus_pad_width" in item for item in report.limitations
        )


@pytest.mark.kicad
class TestKicadCorroboration:
    def test_kicad_loads_and_renders_both_generated_artifacts(
        self, verified, assets, tmp_path: Path
    ):
        land_pattern, symbol, footprint_text, symbol_text = assets
        pretty = tmp_path / "Ohmni.pretty"
        footprint_path = pretty / f"{land_pattern.name}.kicad_mod"
        symbol_path = tmp_path / f"{symbol.name}.kicad_sym"
        footprint_digest = write_asset(footprint_text, footprint_path)
        symbol_digest = write_asset(symbol_text, symbol_path)

        footprint_run = export_footprint_svg(pretty, land_pattern.name, tmp_path / "fp")
        symbol_run = export_symbol_svg(symbol_path, symbol.name, tmp_path / "sym")
        if footprint_run.status is ToolStatus.UNAVAILABLE:
            pytest.skip(footprint_run.detail or "kicad-cli is unavailable")
        assert footprint_run.status is ToolStatus.OK, footprint_run.detail
        assert symbol_run.status is ToolStatus.OK, symbol_run.detail
        # Reports bind to the exact artifact bytes, not to a path.
        assert footprint_run.artifact_sha256 == footprint_digest
        assert symbol_run.artifact_sha256 == symbol_digest
        assert footprint_run.outputs and symbol_run.outputs
        assert all(len(digest) == 64 for digest in footprint_run.output_sha256)

    def test_a_missing_tool_is_unavailable_and_never_a_pass(
        self, assets, tmp_path: Path
    ):
        land_pattern, _symbol, footprint_text, _text = assets
        pretty = tmp_path / "Ohmni.pretty"
        write_asset(footprint_text, pretty / f"{land_pattern.name}.kicad_mod")
        run = export_footprint_svg(
            pretty, land_pattern.name, tmp_path / "out",
            executable=str(tmp_path / "definitely-not-kicad.exe"),
        )
        assert run.status is not ToolStatus.OK
        assert not run.corroborated


@pytest.mark.kicad
class TestConnectedDesignHarness:
    """CS-KICAD: the assets inside a design, not only inside a library.

    A symbol that plots can still fail ERC and a footprint that plots can still
    be malformed to DRC, so the plan asks for both. The harness is deliberately
    trivial -- one component, labelled pins, a rectangular outline -- so that a
    violation is attributable to the asset rather than to the design.
    """

    def _build(self, verified, assets, tmp_path: Path):
        from ohmni.eda.kicad.component_harness import build_harness_pcb, build_harness_schematic

        land_pattern, symbol, footprint_text, symbol_text = assets
        schematic = tmp_path / "harness.kicad_sch"
        board = tmp_path / "harness.kicad_pcb"
        build_harness_schematic(
            symbol_text, symbol.name,
            [(pin.number, pin.x_nm, pin.y_nm) for pin in symbol.pins], schematic,
        )
        build_harness_pcb(footprint_text, land_pattern.name, board)
        return schematic, board

    def test_erc_and_drc_report_no_asset_defect(self, verified, assets, tmp_path: Path):
        from ohmni.eda.kicad.component_harness import run_harness_drc, run_harness_erc

        schematic, board = self._build(verified, assets, tmp_path)
        erc = run_harness_erc(schematic, "a" * 64)
        drc = run_harness_drc(board, "b" * 64)
        if erc.status is ToolStatus.UNAVAILABLE:
            pytest.skip(erc.detail or "kicad-cli is unavailable")
        assert erc.status is ToolStatus.OK, erc.detail
        assert drc.status is ToolStatus.OK, drc.detail
        assert erc.asset_defects == (), erc.violation_counts
        assert drc.asset_defects == (), drc.violation_counts
        # Reports bind to the exact design bytes they were produced from.
        assert erc.report_sha256 and drc.report_sha256
        assert len(erc.design_sha256) == 64

    def test_the_symbol_pins_sit_on_the_schematic_grid(self, assets):
        """An off-grid pin is an asset defect only a connected ERC surfaces."""
        _, symbol, _, _ = assets
        for pin in symbol.pins:
            assert pin.x_nm % 2_540_000 == 0, pin.number
            assert pin.y_nm % 2_540_000 == 0, pin.number

    def test_a_missing_tool_is_unavailable_for_the_connected_gate(
        self, verified, assets, tmp_path: Path
    ):
        from ohmni.eda.kicad.component_harness import run_harness_erc

        schematic, _ = self._build(verified, assets, tmp_path)
        run = run_harness_erc(
            schematic, "a" * 64, executable=str(tmp_path / "definitely-not-kicad.exe")
        )
        assert run.status is not ToolStatus.OK
        assert not run.corroborated
