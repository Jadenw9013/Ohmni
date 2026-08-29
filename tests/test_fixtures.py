"""The golden circuit and its broken variants. Permanent regression cases.

Every electrical bug found during development gets a variant here, so it can
only ever be fixed once.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ohmni.domain import CircuitIR, RuleOutcome, Severity
from ohmni.fixtures.esp32_env_logger import BROKEN_VARIANTS, BUILDERS
from ohmni.verifier import format_report, verify

FIXTURE_JSON_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "esp32_env_logger"
)


class TestGolden:
    def test_no_blocking_findings(self, golden, catalog, requirements):
        report = verify(golden, catalog, requirements)
        blocking = report.blocking_findings
        assert not blocking, "golden circuit regressed:\n" + format_report(report)
        assert not report.export_blocked

    def test_full_coverage(self, golden, catalog, requirements):
        # Every applicable rule must reach a real verdict. A golden circuit
        # that passes because half the rules could not run is not golden.
        report = verify(golden, catalog, requirements)
        assert report.coverage == 1.0, (
            "rules that could not decide: "
            + str([(r.rule_id, r.missing_data) for r in report.undecided_rules])
        )
        assert report.undecided_rules == []

    def test_no_rule_crashed(self, golden, catalog, requirements):
        report = verify(golden, catalog, requirements)
        crashed = [(r.rule_id, r.error_text) for r in report.results if r.outcome is RuleOutcome.ERROR]
        assert crashed == []

    def test_expected_advisory_findings(self, golden, catalog, requirements):
        """The golden board is not silent, and should not be.

        These three are real, correct observations about a sound design. They
        are asserted so that losing them counts as a regression too.
        """
        report = verify(golden, catalog, requirements)
        rule_ids = {f.rule_id for f in report.findings}
        # The sensor is genuinely an LGA package on a hand-solder project.
        assert "PB-ID-005" in rule_ids
        # The status LED sits on a strapping pin, as on real ESP32 boards.
        assert "PB-PIN-002" in rule_ids
        # UART header orientation cannot be settled from a netlist.
        assert "PB-UART-001" in rule_ids
        assert all(f.severity is not Severity.CRITICAL for f in report.findings)

    def test_derived_led_current_is_correct(self, golden, catalog, requirements):
        # (3.35 V - 1.8 V) / 330 ohm = 4.70 mA, worst case.
        report = verify(golden, catalog, requirements)
        led = report.rule("PB-LED-001")
        assert led is not None
        assert led.outcome is RuleOutcome.PASS
        assert any("4.7 mA" in note for note in led.notes), led.notes

    def test_derived_regulator_load_is_correct(self, golden, catalog, requirements):
        # ESP32 500 mA + BME280 VDD 1 mA + VDDIO 1 mA = 502 mA of a 600 mA part.
        report = verify(golden, catalog, requirements)
        reg = report.rule("PB-REG-002")
        assert reg is not None
        assert reg.outcome is RuleOutcome.PASS
        assert any("502 mA" in note and "600 mA" in note for note in reg.notes), reg.notes

    def test_report_states_its_own_limitations(self, golden, catalog, requirements):
        # A pass must say what it did not establish.
        report = verify(golden, catalog, requirements)
        text = " ".join(report.limitations)
        assert "placement" in text.lower()
        assert "NOT_VERIFIED" in text


@pytest.mark.parametrize(("name", "expected"), sorted(BROKEN_VARIANTS.items()))
class TestBrokenVariants:
    def test_expected_rule_fires_at_expected_severity(self, name, expected, catalog, requirements):
        expected_rule, expected_severity = expected
        report = verify(BUILDERS[name](), catalog, requirements)
        matching = [
            f
            for f in report.findings
            if f.rule_id == expected_rule and f.severity.value == expected_severity
        ]
        assert matching, (
            f"{name}: expected {expected_rule} at {expected_severity}\n"
            + format_report(report)
        )

    def test_export_is_blocked(self, name, expected, catalog, requirements):
        report = verify(BUILDERS[name](), catalog, requirements)
        assert report.export_blocked, f"{name} should not be exportable as verified"

    def test_still_reaches_full_coverage(self, name, expected, catalog, requirements):
        # A broken circuit must still be fully assessed. Silently losing
        # coverage would hide the very defect being tested.
        report = verify(BUILDERS[name](), catalog, requirements)
        assert report.coverage == 1.0, [
            (r.rule_id, r.outcome.value, r.missing_data) for r in report.undecided_rules
        ]

    def test_no_rule_crashed(self, name, expected, catalog, requirements):
        report = verify(BUILDERS[name](), catalog, requirements)
        crashed = [
            (r.rule_id, r.error_text) for r in report.results if r.outcome is RuleOutcome.ERROR
        ]
        assert crashed == []

    def test_findings_are_actionable(self, name, expected, catalog, requirements):
        report = verify(BUILDERS[name](), catalog, requirements)
        for finding in report.blocking_findings:
            assert finding.description, f"{finding.rule_id} has no description"
            assert finding.lesson_topic, f"{finding.rule_id} has no lesson topic"
            assert finding.affected_components or finding.affected_nets


class TestFixtureJsonArtifacts:
    """The committed JSON is what the regression corpus actually is."""

    @pytest.mark.parametrize("name", sorted(BUILDERS))
    def test_json_matches_the_builder(self, name):
        path = FIXTURE_JSON_DIR / f"{name}.json"
        assert path.is_file(), f"missing fixture artifact {path}; run scripts/export_fixtures.py"
        payload = json.loads(path.read_text(encoding="utf-8"))
        recorded_hash = payload.pop("_content_hash")
        loaded = CircuitIR.model_validate(payload)
        built = BUILDERS[name]()
        assert loaded.content_hash == built.content_hash, (
            f"{name}.json is stale; re-run scripts/export_fixtures.py"
        )
        assert loaded.content_hash == recorded_hash

    @pytest.mark.parametrize("name", sorted(BUILDERS))
    def test_json_round_trip_verifies_identically(self, name, catalog, requirements):
        payload = json.loads((FIXTURE_JSON_DIR / f"{name}.json").read_text(encoding="utf-8"))
        payload.pop("_content_hash")
        loaded = CircuitIR.model_validate(payload)
        from_json = verify(loaded, catalog, requirements)
        from_builder = verify(BUILDERS[name](), catalog, requirements)
        assert from_json.finding_ids() == from_builder.finding_ids()

    def test_every_variant_is_exported(self):
        on_disk = {p.stem for p in FIXTURE_JSON_DIR.glob("*.json")} - {"requirements"}
        assert on_disk == set(BUILDERS)


class TestVariantsAreMinimalMutations:
    """Each broken variant must differ from golden by one defect, not many."""

    @pytest.mark.parametrize("name", sorted(BROKEN_VARIANTS))
    def test_variant_differs_from_golden(self, name):
        assert BUILDERS[name]().content_hash != BUILDERS["golden"]().content_hash

    @pytest.mark.parametrize("name", sorted(BROKEN_VARIANTS))
    def test_variant_records_its_parent(self, name):
        variant = BUILDERS[name]()
        assert variant.parent_hash == BUILDERS["golden"]().content_hash
        assert variant.notes, "a broken variant must say what was changed"

    def test_variants_are_distinct_from_each_other(self):
        hashes = {name: BUILDERS[name]().content_hash for name in BROKEN_VARIANTS}
        assert len(set(hashes.values())) == len(hashes), hashes
