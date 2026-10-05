"""Adversarial tests: a plausible-looking receipt must not manufacture a pass."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from tools.behavior_audit import BehaviorAudit, evidence
from tools.behavior_audit.audit import _atomic_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def audit(tmp_path, monkeypatch):
    value = BehaviorAudit(ROOT, tmp_path / "run")
    monkeypatch.setattr(value, "_protected_snapshot", lambda: {"main_ref": "baseline"})
    value.initialize()
    return value


def test_all_canaries_rejected_by_real_validators(audit):
    result = audit.run_canaries()
    assert result.passed, result.details
    rows = json.loads((audit.run_dir / "CANARY_RESULTS.json").read_text())["results"]
    assert len(rows) == 7 and all(row["rejected_by"] == row["expected_rule"] for row in rows)


def test_disabling_real_source_validator_breaks_its_canary(audit, monkeypatch):
    monkeypatch.setattr(evidence, "source_errors", lambda *args: [])
    assert not audit.run_canaries().passed


def test_disabling_real_bench_validator_breaks_its_canary(audit, monkeypatch):
    monkeypatch.setattr(evidence, "bench_errors", lambda *args: [])
    assert not audit.run_canaries().passed


def test_a_changed_expected_value_cannot_agree_with_itself():
    errors = evidence.comparison_errors(
        {"expected": 4.0, "measured": 4.0, "tolerance": 0.01},
        {"expected": 5.0, "tolerance": 0.01},
    )
    assert any("locked" in error for error in errors)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True])
def test_nonfinite_or_boolean_reading_is_not_evidence(value):
    assert evidence.comparison_errors(
        {"expected": 5, "measured": value, "tolerance": 0.1},
        {"expected": 5, "tolerance": 0.1},
    )


@pytest.mark.parametrize("text", ["42", "ngspice-142", "ngspice-421", "ngspice-43"])
def test_version_is_an_exact_ngspice_major(text):
    assert not evidence.version_42(text)


def test_archived_source_content_must_match_ledger(tmp_path):
    content = b"manufacturer source actually downloaded"
    digest = hashlib.sha256(content).hexdigest()
    url = "https://manufacturer.example/datasheet.pdf"
    row = {"url": url, "http_status": 200, "timestamp": "2026-10-04T00:00:00Z", "tool_used": "test", "content_sha256": digest}
    assert evidence.source_errors({url}, [row], tmp_path)
    archive = tmp_path / "fetched-sources" / f"{digest}.bin"
    archive.parent.mkdir()
    archive.write_bytes(content)
    assert evidence.source_errors({url}, [row], tmp_path) == []
    archive.write_bytes(b"different source")
    assert evidence.source_errors({url}, [row], tmp_path)


def test_stage_one_does_not_satisfy_new_bench_runs(audit):
    result = audit.check_benches()
    assert not result.passed
    contracts = audit._state()["bench_contracts"]
    assert len(contracts) == 205
    assert "BEH-RES-FIXED/B1" in contracts
    assert "BEH-RES-SENSE/B1" in contracts


def test_rule_change_cannot_lower_coverage_with_a_self_asserted_tighten(audit, tmp_path):
    rules = copy.deepcopy(audit.rules)
    rules["expected_entry_count"] = 1
    changed = tmp_path / "changed-rules.yaml"
    _atomic_json(changed, rules)
    audit.rules_path = changed
    audit.rules = rules
    change = {"old_sha256": audit._state()["rule_hash"], "new_sha256": audit.rule_hash, "classification": "tighten"}
    (audit.run_dir / "RULE_CHANGES.md").write_text("```rule-change\n" + json.dumps(change) + "\n```", encoding="utf-8")
    assert not audit.check_rule_hash().passed


def test_changing_a_state_baseline_is_detected(audit):
    state = audit._state()
    state["bench_contracts"]["BEH-RES-FIXED/B1"]["expected"][0]["value"] = 4
    audit._write_state(state)
    assert not audit.check_state().passed


def test_rule_hash_cannot_be_rebased_by_editing_state(audit):
    state = audit._state()
    state["rule_hash"] = "0" * 64
    audit._write_state(state)
    assert not audit.check_rule_hash().passed


def test_canary_fixture_tampering_is_detected(audit, tmp_path):
    import shutil

    directory = tmp_path / "fixtures"
    shutil.copytree(audit.fixtures_dir, directory)
    audit.fixtures_dir = directory
    fixture = directory / "non_run_marked_pass.json"
    fixture.write_text(fixture.read_text() + "\n", encoding="utf-8")
    assert not audit.run_canaries().passed


def test_ledger_cannot_authorize_an_unbenchmarked_status_upgrade(audit):
    errors = audit._upgrade_evidence_errors({"field_updates": [], "bench_result": "missing.json"})
    assert any("bench" in error for error in errors)


def test_matching_zero_difference_is_valid_but_no_run_is_not():
    contract = {"expected": 5, "tolerance": 0.01}
    run = dict(contract, measured=5, run_status="passed", ngspice_version="** ngspice-42 **", product_code_path=True)
    assert evidence.bench_errors(run, contract) == []
    run["run_status"] = "not_run"
    assert evidence.bench_errors(run, contract)


def test_errors_and_violations_never_display_as_pass():
    for status in ("not_run", "failed", "unavailable", "timed_out", "unexpected"):
        assert evidence.honesty_errors({"simulation_status": status, "display_status": "pass"})
    assert evidence.honesty_errors({"simulation_status": "ok", "rating_status": "violation", "display_status": "pass"})
    assert evidence.honesty_errors({"simulation_status": "ok", "rating_status": "violation", "display_status": "violation"}) == []


def test_verifier_seed_and_unique_sample_are_enforced(audit):
    population = [f"OHM-{index:03d}" for index in range(1, 31)]
    plan = audit.verifier_plan("stage2", population, seed=314159)
    assert len(plan["sample"]) == 5
    report = dict(plan, reviewer_context="fresh", results=[{"entry_id": entry, "primary_sources": ["source"], "mismatches": []} for entry in plan["sample"]])
    assert audit._verifier_errors("stage2", report) == []
    report["sample"] = [plan["sample"][0]] * 5
    assert audit._verifier_errors("stage2", report)


def test_resume_preserves_original_run_and_baselines(audit):
    before = audit._state()
    after = audit.initialize()
    assert before == after
