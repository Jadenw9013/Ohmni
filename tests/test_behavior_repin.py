"""A deck re-pin may move only the locked deck hash, never an expectation."""

from pathlib import Path

import pytest

from tools.behavior_audit import BehaviorAudit
from tools.behavior_audit.benches import compound_contracts

ROOT = Path(__file__).resolve().parents[1]
BENCH = "BEH-RES-FIXED/B1"
NEW = "a" * 64


@pytest.fixture
def audit(tmp_path, monkeypatch):
    value = BehaviorAudit(ROOT, tmp_path / "run")
    monkeypatch.setattr(value, "_protected_snapshot", lambda: {"main_ref": "baseline"})
    value.initialize()
    return value


def _ledger(audit, monkeypatch, row, **repin):
    entry = {"id": "REPIN-T", "approved_by": "test reviewer", "approved_on": "2026-10-05",
             "benches": {BENCH: row}}
    entry.update(repin)
    monkeypatch.setattr(audit, "bench_repins", lambda: {"schema_version": 1, "repins": [entry]})


def _locked(audit):
    return audit._state()["bench_contracts"]


def test_approved_repin_moves_only_the_deck_hash(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger(audit, monkeypatch, {"file": locked["file"], "baseline_netlist_sha256": locked["netlist_sha256"],
                                 "netlist_sha256": NEW, "reason": "test"})
    effective, errors = audit._apply_repins(_locked(audit))
    assert not errors
    assert effective[BENCH]["netlist_sha256"] == NEW
    assert effective[BENCH]["expected"] == locked["expected"]
    assert effective[BENCH]["file"] == locked["file"]


def test_repin_cannot_carry_an_expected_value_change(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger(audit, monkeypatch, {"file": locked["file"], "baseline_netlist_sha256": locked["netlist_sha256"],
                                 "netlist_sha256": NEW, "expected": [{"value": 1, "tolerance": 99}]})
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH]["netlist_sha256"] == locked["netlist_sha256"]


def test_repin_must_start_from_the_locked_hash(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger(audit, monkeypatch, {"file": locked["file"], "baseline_netlist_sha256": "b" * 64,
                                 "netlist_sha256": NEW})
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH]["netlist_sha256"] == locked["netlist_sha256"]


def test_repin_cannot_move_the_file(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger(audit, monkeypatch, {"file": "docs/behavior/bench/other.cir",
                                 "baseline_netlist_sha256": locked["netlist_sha256"], "netlist_sha256": NEW})
    assert audit._apply_repins(_locked(audit))[1]


def test_repin_without_human_approval_is_ignored(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger(audit, monkeypatch, {"file": locked["file"], "baseline_netlist_sha256": locked["netlist_sha256"],
                                 "netlist_sha256": NEW}, approved_by="")
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH]["netlist_sha256"] == locked["netlist_sha256"]


def test_unapproved_hash_change_still_fails_resume(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger(audit, monkeypatch, {"file": locked["file"], "baseline_netlist_sha256": locked["netlist_sha256"],
                                 "netlist_sha256": NEW})
    # The ledger names a hash that the file on disk does not have.
    assert not audit.check_state().passed


def test_compound_value_keeps_the_locked_tolerance_for_every_component():
    parts = compound_contracts({"value": "10/8/5/2", "tolerance": "0.1%"})
    assert [part["expected"] for part in parts] == [10, 8, 5, 2]
    assert parts[1]["tolerance"] == pytest.approx(0.008)


@pytest.mark.parametrize("value", ["10/8 uF", "10, 8", 10.0, "a/b"])
def test_only_pure_numeric_slash_lists_are_compound(value):
    assert compound_contracts({"value": value, "tolerance": "1%"}) is None


def _ledger_entries(audit, monkeypatch, **entries):
    base = {"schema_version": 1, "repins": []}
    base.update(entries)
    monkeypatch.setattr(audit, "bench_repins", lambda: base)


GOOD_ITEM = {"measure": "vout", "value": 1.0, "tolerance": "1%", "basis": "derived"}


def test_correction_must_quote_the_locked_expected_list(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger_entries(audit, monkeypatch, corrections=[{
        "id": "C-T", "approved_by": "r", "approved_on": "2026-10-05",
        "benches": {BENCH: {"baseline_expected": [{"value": 0}], "expected": [GOOD_ITEM], "derivation": "x"}}}])
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH]["expected"] == locked["expected"]


def test_correction_items_must_be_numeric_and_based(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    bad = {"measure": "vout", "value": "about one", "tolerance": "some", "basis": "x"}
    _ledger_entries(audit, monkeypatch, corrections=[{
        "id": "C-T", "approved_by": "r", "approved_on": "2026-10-05",
        "benches": {BENCH: {"baseline_expected": locked["expected"], "expected": [bad], "derivation": "x"}}}])
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH]["expected"] == locked["expected"]


def test_approved_correction_applies_and_class_records_stay_locked(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger_entries(audit, monkeypatch, corrections=[{
        "id": "C-T", "approved_by": "r", "approved_on": "2026-10-05",
        "benches": {BENCH: {"baseline_expected": locked["expected"], "expected": [GOOD_ITEM], "derivation": "x"}}}])
    effective, errors = audit._apply_repins(_locked(audit))
    assert not errors and effective[BENCH]["expected"] == [GOOD_ITEM]
    unchanged, _ = audit._apply_repins(_locked(audit), corrections=False)
    assert unchanged[BENCH]["expected"] == locked["expected"]


def test_unapproved_correction_is_refused(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger_entries(audit, monkeypatch, corrections=[{
        "id": "C-T", "approved_by": "", "approved_on": "2026-10-05",
        "benches": {BENCH: {"baseline_expected": locked["expected"], "expected": [GOOD_ITEM], "derivation": "x"}}}])
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH]["expected"] == locked["expected"]


def test_addition_cannot_replace_an_existing_bench(audit, monkeypatch):
    locked = _locked(audit)[BENCH]
    _ledger_entries(audit, monkeypatch, additions=[{
        "id": "A-T", "approved_by": "r", "approved_on": "2026-10-05",
        "benches": {BENCH: {"file": "docs/behavior/bench/x.cir", "netlist_sha256": NEW,
                            "expected": [GOOD_ITEM], "derivation": "x"}}}])
    effective, errors = audit._apply_repins(_locked(audit))
    assert errors and effective[BENCH] == locked


def test_addition_adds_a_required_bench(audit, monkeypatch):
    _ledger_entries(audit, monkeypatch, additions=[{
        "id": "A-T", "approved_by": "r", "approved_on": "2026-10-05",
        "benches": {"BEH-NEW/B1": {"file": "docs/behavior/bench/x.cir", "netlist_sha256": NEW,
                                   "expected": [GOOD_ITEM], "derivation": "x"}}}])
    effective, errors = audit._apply_repins(_locked(audit))
    assert not errors and "BEH-NEW/B1" in effective
