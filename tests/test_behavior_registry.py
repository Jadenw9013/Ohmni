"""Stage 1 contract for generated component behavior data."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ohmni.behavior import BehaviorFidelity, BehaviorRegistry, SimulationDisposition
from ohmni.behavior.loader import BehaviorRegistryError, validate_registry_references
from ohmni.behavior.models import PackagePinOrder, SourceAnchor
from ohmni.catalog.loader import default_catalog
from scripts.generate_behavior_records import check_records

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "COMPONENT_BEHAVIOR_SPEC.md"
MASTER_ROW = re.compile(
    r"^\| (?P<entry_id>OHM-\d{3}) \| (?P<component>.*?) \| "
    r"(?P<behaviors>.*?) \| (?P<layer>L[123]) \| (?P<fidelity>[^|]+?) \| "
    r"(?P<status>complete|partial|research_required) \| (?P<group>[^|]+?) \|$"
)


@pytest.fixture(scope="module")
def registry() -> BehaviorRegistry:
    return BehaviorRegistry(repo_root=ROOT)


def _canonical_yaml() -> dict[str, dict]:
    text = SPEC.read_text(encoding="utf-8")
    payloads = [
        yaml.safe_load(body)
        for body in re.findall(r"```yaml\r?\n(.*?)\r?\n```", text, re.DOTALL)
    ]
    return {
        item["behavior_id"]: item
        for item in payloads
        if isinstance(item, dict) and "behavior_id" in item
    }


def _basis_values(value) -> list[str]:
    result = set()

    def visit(item) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "basis" and child is not None:
                    result.add(str(child))
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return sorted(result)


def test_all_180_entries_and_66_canonical_classes_are_generated(registry):
    assert sorted(registry.entries) == [f"OHM-{index:03d}" for index in range(1, 181)]
    assert len(registry.classes) == 66
    assert registry.manifest.status_counts == {
        "complete": 18,
        "partial": 144,
        "research_required": 18,
    }
    assert registry.manifest.fidelity_counts == {
        "behavioural_approximation": 145,
        "ideal_components": 35,
    }


def test_master_status_layer_fidelity_and_behavior_ids_are_preserved(registry):
    rows = {}
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        if match := MASTER_ROW.match(line):
            rows[match["entry_id"]] = match.groupdict()
    assert len(rows) == 180
    for entry_id, source in rows.items():
        record = registry.entry(entry_id)
        assert record.status.value == source["status"]
        assert record.layer.value == source["layer"]
        assert record.fidelity.value == source["fidelity"].strip()
        assert record.behavior_class_ids == [
            item.strip() for item in source["behaviors"].split(" + ")
        ]


def test_canonical_payload_status_fidelity_and_basis_are_preserved(registry):
    source = _canonical_yaml()
    assert set(source) == set(registry.classes)
    for behavior_id, payload in source.items():
        record = registry.behavior_class(behavior_id)
        assert record.status.value == payload["status"]
        assert record.fidelity.value == payload["model"]["fidelity"]
        assert record.basis_values == _basis_values(payload)
        assert record.canonical_payload == payload


def test_fidelity_vocabulary_is_exact_and_source_contains_no_vendor_claim(registry):
    assert {item.value for item in BehaviorFidelity} == {
        "ideal_components",
        "behavioural_approximation",
        "vendor_model",
    }
    assert all(record.fidelity is not BehaviorFidelity.VENDOR_MODEL for record in registry.classes.values())
    assert all(record.fidelity is not BehaviorFidelity.VENDOR_MODEL for record in registry.entries.values())


def test_every_entry_has_an_honest_simulation_disposition(registry):
    assert all(record.simulation_reason for record in registry.entries.values())
    for entry in registry.entries.values():
        number = int(entry.entry_id.split("-")[1])
        if entry.layer.value == "L3" or 103 <= number <= 140 or entry.status.value == "research_required":
            assert entry.simulation_disposition is SimulationDisposition.NOT_SIMULABLE
        else:
            assert entry.simulation_disposition is SimulationDisposition.SIMULABLE


def test_generated_projection_is_current():
    assert check_records(ROOT)


def test_missing_source_document_fails_reference_validation(registry, tmp_path):
    record = next(iter(registry.classes.values()))
    missing = SourceAnchor(
        document="missing/source.md",
        line=1,
        document_sha256="0" * 64,
    )
    changed = record.model_copy(update={"source": missing})
    with pytest.raises(BehaviorRegistryError, match="missing source"):
        validate_registry_references(tmp_path, {record.behavior_id: changed}, {}, {})


def test_missing_bench_file_fails_reference_validation(registry):
    record = next(item for item in registry.classes.values() if item.benches)
    bad_bench = record.benches[0].model_copy(update={"file": "docs/behavior/bench/missing.cir"})
    changed = record.model_copy(update={"benches": [bad_bench, *record.benches[1:]]})
    with pytest.raises(BehaviorRegistryError, match="missing bench"):
        validate_registry_references(ROOT, {record.behavior_id: changed}, {}, {})


def test_every_imported_bench_keeps_version_and_is_not_a_new_stage1_run(registry):
    benches = [bench for record in registry.classes.values() for bench in record.benches]
    assert len(benches) == registry.manifest.bench_reference_count == 205
    assert all(bench.run_provenance == "imported_research_record" for bench in benches)
    assert registry.manifest.bench_execution == "imported_research_records_not_rerun_in_stage_1"


@pytest.mark.parametrize("package_name", ["0603", "0805"])
def test_generic_green_led_keeps_catalog_roles_and_explicit_package_permutation(
    registry, package_name,
):
    catalog = default_catalog().require("GENERIC_LED_GREEN")
    assert [(pin.number, pin.name) for pin in catalog.pins] == [("1", "A"), ("2", "K")]
    package = registry.binding("GENERIC_LED_GREEN").package(package_name)
    assert package.catalog_pin_roles == {"1": "A", "2": "K"}
    assert package.package_terminal_roles == {"1": "K", "2": "A"}
    assert package.catalog_to_package_terminal == {"1": "2", "2": "1"}
    assert package.catalog_to_footprint_pad == {"1": "2", "2": "1"}
    assert catalog.package(package_name).catalog_pin_to_pad == {"1": "2", "2": "1"}
    assert package.catalog_pin_roles["1"] == package.package_terminal_roles[
        package.catalog_to_package_terminal["1"]
    ] == "A"
    assert package.catalog_pin_roles["2"] == package.package_terminal_roles[
        package.catalog_to_package_terminal["2"]
    ] == "K"


def test_role_changing_led_permutation_is_rejected(registry):
    original = registry.binding("GENERIC_LED_GREEN").package("0603")
    raw = original.model_dump(mode="json")
    raw["catalog_to_package_terminal"] = {"1": "1", "2": "2"}
    with pytest.raises(ValidationError, match="does not match"):
        PackagePinOrder.model_validate(raw)


@pytest.mark.parametrize(
    ("package_name", "terminal_order", "permutation"),
    [
        pytest.param(
            "SOT-23", ["GND", "VOUT", "VIN"], {"1": "1", "2": "2", "3": "3"},
            id="DS20001826F-page-11-SOT-23",
        ),
        pytest.param(
            "SOT-89", ["GND", "VIN", "VOUT"], {"1": "1", "2": "3", "3": "2"},
            id="DS20001826F-page-11-SOT-89",
        ),
        pytest.param(
            "TO-92", ["GND", "VIN", "VOUT"], {"1": "1", "2": "3", "3": "2"},
            id="DS20001826F-page-11-TO-92",
        ),
    ],
)
def test_mcp1700_package_orders_are_separate_and_cite_the_datasheet_page(
    registry, package_name, terminal_order, permutation,
):
    # Microchip MCP1700 DS20001826F, Table 3-1, page 11.
    package = registry.binding("MCP1700T-3302E-TT").package(package_name)
    assert package.terminal_order() == terminal_order
    assert package.catalog_to_package_terminal == permutation
    assert package.citation.document_id == "DS20001826F"
    assert package.citation.page == 11
    assert package.citation.source_status == "HUMAN_CONFIRMED"


def test_mcp1700_catalog_sot23_pins_are_corrected_with_page_evidence():
    part = default_catalog().require("MCP1700T-3302E-TT")
    assert [(pin.number, pin.name) for pin in part.pins] == [
        ("1", "GND"),
        ("2", "VOUT"),
        ("3", "VIN"),
    ]
    for pin in part.pins:
        assert len(pin.evidence) == 1
        assert pin.evidence[0].document.revision == "DS20001826F"
        assert pin.evidence[0].page == 11


def test_unresolved_electrical_membership_mismatch_stays_visible(registry):
    assert [issue.model_dump(mode="json") for issue in registry.manifest.source_consistency_issues] == [
        {
            "kind": "master_class_application_mismatch",
            "entry_id": "OHM-133",
            "behavior_id": "BEH-REG-LINEAR",
            "detail": (
                "Master table assigns BEH-REG-LINEAR to OHM-133, but the canonical class "
                "applies_to list omits the entry."
            ),
            "resolution": "preserved_unresolved_for_human_gate",
        }
    ]


def test_other_stage0_label_and_permutation_resolutions_are_explicit(registry):
    resolutions = {
        item.resolution_id: item for item in registry.manifest.resolutions
    }
    assert resolutions["POLARITY-CAN-NEGATIVE-STRIPE"].data == {
        "marking": "negative_stripe",
        "electrical_role": "MINUS",
    }
    assert resolutions["POLARITY-TANTALUM-POSITIVE-BAR"].data == {
        "marking": "positive_bar",
        "electrical_role": "PLUS",
    }
    assert resolutions["PLCC28-REFERENCE-LABEL"].data["excluded_reference"] == "AT27C256R"
    assert resolutions["PLCC28-REFERENCE-LABEL"].data["excluded_package"] == "PLCC-32"
    assert resolutions["BGA-WLCSP-TOP-VIEW-TRANSFORM"].data["transform"] == "mirror_x"
    assert resolutions["XT-FOOTPRINT-PAD-PERMUTATION"].data == {
        "package_terminal_to_footprint_pad": {"1": "2", "2": "1"},
        "polarity": "unbound",
    }
    assert resolutions["REFERENCE-DIMENSION-COMPATIBILITY-POLICY"].data[
        "allowed_labels"
    ] == ["exact", "compatible_variant", "mismatch"]
    for resolution in resolutions.values():
        if not resolution.gate_required:
            assert not resolution.changes_electrical_truth
        for entry_id in resolution.entry_ids:
            assert resolution.resolution_id in registry.entry(entry_id).resolution_ids


def test_bridge_electrical_truth_change_remains_a_gate_blocker(registry):
    resolution = next(
        item
        for item in registry.manifest.resolutions
        if item.resolution_id == "BRIDGE-PIN-FUNCTIONS-UNRESOLVED"
    )
    assert resolution.entry_ids == ["OHM-071", "OHM-072"]
    assert resolution.changes_electrical_truth
    assert resolution.gate_required
    assert resolution.data["automatic_binding"] == "blocked"


def test_source_hashes_are_real_sha256_values(registry):
    spec_hash = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    assert registry.manifest.source_spec.document_sha256 == spec_hash
    assert all(record.source.document_sha256 == spec_hash for record in registry.classes.values())
    assert all(record.source.document_sha256 == spec_hash for record in registry.entries.values())


def test_plcc_reference_uses_primary_plcc_figure_not_hvqfn(registry):
    # Philips P89LPC933/934/935/936 Rev05, page6 Figure4 (PLCC28).
    research = registry.entry("OHM-135").research
    facts = {fact.field: fact for fact in research.field_updates}
    mapping = facts["manufacturer_pin_roles"]
    assert mapping.page == 6
    assert len(mapping.value) == 28
    assert {pin: mapping.value[pin] for pin in ["1", "6", "7", "21", "28"]} == {
        "1": "P2_0", "6": "P1_5_RESET", "7": "VSS", "21": "VDD", "28": "P2_7",
    }
    assert any("HVQFN" in conflict for conflict in research.conflicts)


@pytest.mark.parametrize("entry,count,corners", [
    ("OHM-136", 64, {"A1": "AGND", "A8": "AGND", "H1": "LREQ", "H8": "DGND"}),
    ("OHM-137", 100, {"A1": "TDO_SWO", "A10": "P0_9", "K1": "P3_26", "K10": "P2_12"}),
    ("OHM-139", 9, {"A1": "SD_MODE", "A3": "OUTP", "C1": "BCLK", "C3": "LRCLK"}),
    ("OHM-140", 16, {"A1": "VIN", "A4": "FLT", "D1": "VBUS", "D4": "CAP"}),
])
def test_primary_ball_identifiers_are_not_mirrored_as_electrical_names(registry, entry, count, corners):
    # PDI1394P23 p4; LPC1768 pp7-10; MAX98357A p15; NX5P3290 p4.
    facts = {fact.field: fact for fact in registry.entry(entry).research.field_updates}
    mapping = facts["manufacturer_pin_roles"].value
    assert len(mapping) == count
    assert {name: mapping[name] for name in corners} == corners
    assert "ball_view_transform" in facts


def test_non_paginated_manufacturer_pinout_has_exact_locator(registry):
    from ohmni.behavior.models import ResearchFact

    facts = {fact.field: fact for fact in registry.entry("OHM-138").research.field_updates}
    mapping = facts["manufacturer_pin_roles"]
    assert len(mapping.value) == 256
    assert mapping.value["H10"] == "DONE_0"
    assert mapping.value["G7"] == "GNDADC_0"
    assert mapping.page is None
    assert mapping.source_locator == "a7all/xc7a35tftg256pkg.csv"
    payload = mapping.model_dump()
    payload["source_locator"] = " "
    with pytest.raises(ValueError, match="source locator"):
        ResearchFact.model_validate(payload)


@pytest.mark.parametrize("entry", ["OHM-143", "OHM-144", "OHM-145"])
def test_abracon_case_pads_are_not_bound_as_crystal_pads(registry, entry):
    # ABM8/10/11 p2 top views, same drawing axes; library Section6 top-left pin1.
    facts = {fact.field: fact for fact in registry.entry(entry).research.field_updates}
    permutation = facts["manufacturer_to_library_terminal"].value
    source_roles = facts["manufacturer_pin_roles"].value
    mapped = {permutation[pin]: role for pin, role in source_roles.items()}
    assert mapped == {"1": "GND", "2": "XTAL_A", "3": "GND", "4": "XTAL_B"}
    source_corners = {"1": (-1, -1), "2": (1, -1), "3": (1, 1), "4": (-1, 1)}
    library_corners = {"1": (-1, 1), "2": (-1, -1), "3": (1, -1), "4": (1, 1)}
    assert all(source_corners[p] == library_corners[q] for p, q in permutation.items())
    assert registry.entry(entry).research.simulation_blockers


def test_pj102a_switch_connects_to_sleeve_when_unplugged(registry):
    # Same Sky PJ-102A, 03/11/2025, page2 schematic (not a generic jack).
    facts = {fact.field: fact for fact in registry.entry("OHM-172").research.field_updates}
    assert facts["manufacturer_pin_roles"].value == {
        "1": "CENTER", "2": "SLEEVE", "3": "SLEEVE_SWITCH",
    }
    assert facts["unplugged_switch_pairs"].value == [[2, 3]]
    assert facts["unplugged_switch_pairs"].page == 2


def test_ufl_measurement_current_is_not_an_operating_rating(registry):
    # Hirose U.FL catalogue p4: 10mA appears in the measurement condition column.
    facts = {fact.field: fact for fact in registry.entry("OHM-175").research.field_updates}
    assert facts["resistance_test_current_max"].value == .01
    assert "not rated operating current" in facts["resistance_test_current_max"].scope
    assert "current_rated" not in facts
    assert registry.entry("OHM-175").research.simulation_blockers


def test_microsd_data_pin_is_distinct_from_mechanical_detect(registry):
    # Hirose DM3AT-SF-PEJM5 p3 names eight data pins plus switch A/B.
    facts = {fact.field: fact for fact in registry.entry("OHM-180").research.field_updates}
    assert facts["manufacturer_pin_roles"].value["2"] == "CD/DAT3"
    assert len(facts["manufacturer_pin_roles"].value) == 8
    assert facts["card_detect_switch"].value == {
        "contacts": ["A", "B"], "removed": "open", "inserted": "closed",
    }


def test_xt60_source_variants_are_not_merged_into_one_rating(registry):
    facts = {fact.field: fact for fact in registry.entry("OHM-174").research.field_updates}
    assert facts["legacy_current_rated"].value == 45
    assert facts["catalog_current_max"].value == 35
    assert facts["web_voltage_rated_dc"].value == 80
    assert facts["legacy_voltage_rated_dc"].value == 500
    assert registry.entry("OHM-174").research.simulation_blockers
@pytest.mark.parametrize("number", [124, 125, 126])
def test_stm32_capacitance_is_typical_not_a_rating_ceiling(number):
    registry = BehaviorRegistry(repo_root=ROOT)
    facts = {f.field: f for f in registry.entry(f"OHM-{number:03}").research.field_updates}
    assert "io_input_capacitance_max" not in facts
    assert facts["io_input_capacitance_typical"].value == 5
    assert facts["io_input_capacitance_typical"].page == 105
    assert facts["reference_part"].page == 164
