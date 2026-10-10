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
    url = "https://manufacturer.example/source.txt"
    row = {"url": url, "http_status": 200, "timestamp": "2026-10-04T00:00:00Z", "tool_used": "test", "content_sha256": digest}
    assert evidence.source_errors({url}, [row], tmp_path)
    archive = tmp_path / "fetched-sources" / f"{digest}.bin"
    archive.parent.mkdir()
    archive.write_bytes(content)
    assert evidence.source_errors({url}, [row], tmp_path) == []
    archive.write_bytes(b"different source")
    assert evidence.source_errors({url}, [row], tmp_path)


def test_html_refusal_at_pdf_url_is_not_source_evidence(tmp_path):
    content = b"<html><title>Request rejected</title>Access denied</html>"
    digest = hashlib.sha256(content).hexdigest()
    archive = tmp_path / "fetched-sources" / f"{digest}.bin"
    archive.parent.mkdir()
    archive.write_bytes(content)
    url = "https://manufacturer.example/datasheet.pdf"
    row = {"url": url, "http_status": 200, "timestamp": "2026-10-05T00:00:00Z",
           "tool_used": "test", "content_sha256": digest}
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


def test_measurement_suffixes_are_parsed_without_accepting_arbitrary_prose():
    from tools.behavior_audit.benches import scalars

    assert scalars("pavg = 2.998362e-1 from=4e-2 to=6e-2\nvmax = 4.2 at=0.5\n") == {
        "pavg": 0.2998362, "vmax": 4.2,
    }
    assert scalars("pavg = 0.3 assumed because it should pass\n") == {}
    assert scalars("pavg = 0.3\npavg = 0.4\n") == {}


def test_explicit_binding_uses_named_measurement_not_nearest_expected_number(audit):
    from tools.behavior_audit.benches import observed_value

    item = {"measure": "|Z| at 120 Hz (ohm)"}
    output = "z120 = 12.0\nz100k = 13.2663\n"
    assert observed_value(audit, "BEH-CAP-ALEL/B1", item, output) == 12.0
    assert observed_value(audit, "BEH-CAP-ALEL/B1", item, "z100k = 13.2663\n") is None


def test_exact_and_percent_words_preserve_the_stated_numeric_tolerance():
    from tools.behavior_audit.benches import numeric_contract

    assert numeric_contract({"value": 2, "tolerance": "exact"}) == {"expected": 2, "tolerance": 0}
    assert numeric_contract({"value": 2, "tolerance": "0.1 percent"}) == {"expected": 2, "tolerance": 0.002}
    assert numeric_contract({"value": 2, "tolerance": "unclear"})["tolerance"] is None


def test_source_ids_are_resolved_within_their_bibliography_not_globally():
    from tools.behavior_audit.sources import reference_ids, source_catalog

    assert reference_ids("see S1..S3, S5") == ["S1", "S2", "S3", "S5"]
    catalog = source_catalog(ROOT)
    header = next(row for row in catalog["BEH-CON-HEADER"]["sources"] if row["id"] == "S1")
    wtb = next(row for row in catalog["BEH-CON-WTB"]["sources"] if row["id"] == "S1")
    assert any("samtec" in url for url in header["urls"])
    assert all("jst-mfg.com" in url for url in wtb["urls"])
    assert not any(url.endswith("):") for url in wtb["urls"])


def test_structured_url_with_spaces_is_preserved_as_one_citation():
    from tools.behavior_audit.audit import _urls_in

    url = "https://manufacturer.example/data/My Datasheet.pdf"
    assert _urls_in({"url": url, "title": "A descriptive title"}) == {url}


def test_verifier_seed_and_unique_sample_are_enforced(audit):
    population = [f"OHM-{index:03d}" for index in range(1, 31)]
    plan = audit.verifier_plan("stage2", population, seed=314159)
    assert len(plan["sample"]) == 5
    report = dict(plan, reviewer_context="fresh", results=[{"entry_id": entry, "primary_sources": ["source"], "mismatches": []} for entry in plan["sample"]])
    assert audit._verifier_errors("stage2", report) == []
    report["sample"] = [plan["sample"][0]] * 5
    assert audit._verifier_errors("stage2", report)


def test_verifier_report_must_match_current_plan_and_reviewed_bytes(audit):
    population = [f"OHM-{index:03d}" for index in range(1, 11)]
    plan = audit.verifier_plan("stage2", population, seed=314159)
    results = []
    for entry_id in plan["sample"]:
        reviewed = {}
        for key, relative in (
            ("gapfill_sha256", f"docs/behavior/gapfill/{entry_id}.md"),
            ("generated_record_sha256", f"src/ohmni/behavior/data/entries/{entry_id}.json"),
        ):
            reviewed[key] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        results.append({"entry_id": entry_id, "primary_sources": ["source"],
                        "mismatches": [], "reviewed_content": reviewed})
    report = dict(plan, reviewer_context="fresh", results=results)
    report_path = audit.run_dir / "verifier/stage2.json"
    _atomic_json(report_path, report)
    state = audit._state()
    state["completed_research_stages"] = ["stage2"]
    audit._write_state(state)
    assert audit.check_independent_verifiers().passed
    audit.verifier_plan("stage2", population, seed=271828)
    assert not audit.check_independent_verifiers().passed
    audit.verifier_plan("stage2", population, seed=314159)
    report["results"][0]["reviewed_content"]["gapfill_sha256"] = "0" * 64
    _atomic_json(report_path, report)
    assert not audit.check_independent_verifiers().passed


def test_resume_preserves_original_run_and_baselines(audit):
    before = audit._state()
    after = audit.initialize()
    assert before == after


def test_ordered_operating_point_binding_requires_every_point(audit):
    from tools.behavior_audit.benches import observed_value

    # BEH-DIO-PN/B1 now prints a named scalar (REPIN-003); B7 keeps an ordered binding.
    item = {"measure": "VF at 100 C, 10 mA"}
    text = "v(d) = 0.6\nv(d) = 0.7\n"
    assert observed_value(audit, "BEH-DIO-PN/B7", item, text) == 0.7
    assert observed_value(audit, "BEH-DIO-PN/B7", item, "v(d) = 0.7\n") is None


def test_named_model_binding_does_not_select_the_comparator(audit):
    from tools.behavior_audit.benches import observed_value

    assert observed_value(audit, "BEH-TRN-MOSFET/B2", {"measure": "Rds_4p5V_L3"},
                          "r45a = 0.026\nr45b = 0.016\n") == 0.026


def test_unit_tolerance_is_converted_exactly():
    from tools.behavior_audit.benches import numeric_contract

    assert numeric_contract({"value": 0.7, "tolerance": "1 mV"}) == {"expected": 0.7, "tolerance": 0.001}
    assert numeric_contract({"value": 4000, "tolerance": 0.15})["tolerance"] == 0.15


def test_relocated_author_include_is_locked_and_contained(tmp_path):
    import hashlib

    from tools.behavior_audit.audit import AuditError
    from tools.behavior_audit.benches import inline_deck

    deck = tmp_path / "bench.cir"
    lib = tmp_path / "model.lib"
    deck.write_text("title\n.include /old/model.lib\n.end\n")
    lib.write_text(".model DTEST D(IS=1e-12)\n")
    binding = {"/old/model.lib": {"relative_path": "model.lib", "sha256": hashlib.sha256(lib.read_bytes()).hexdigest()}}
    assert ".model DTEST" in inline_deck(deck, tmp_path, relocations=binding)
    lib.write_text(".model DTEST D(IS=1)\n")
    with pytest.raises(AuditError, match="content changed"):
        inline_deck(deck, tmp_path, relocations=binding)
    binding["/old/model.lib"]["relative_path"] = "../outside.lib"
    with pytest.raises(AuditError, match="escapes"):
        inline_deck(deck, tmp_path, relocations=binding)


def test_runtime_receipts_relocate_observations_and_reject_stale_inputs(audit, monkeypatch):
    from ohmni.eda.simulation import NgspiceAdapter
    from tools.behavior_audit.runtime_benches import resistor_receipt_errors, run_resistor_recipes

    def fake(self, compiled, *, work_dir, analysis):
        node = compiled.node_names["middle"]
        output = (f"v({node}) = 2.5\n" if analysis == "op" else
                  f"Index time v({node})\n0 0 2.5\n1 0.001 2.5\n")
        return {"status": "ran", "stdout": output, "stderr": "", "version_output": "ngspice-42",
                "problems": [], "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit",
                "operating_point": {"node_voltages": {node: {"value": 2.5, "unit": "V"}}},
                "transient": {"series": [{"name": f"v({node})", "values": [2.5, 2.5]}]}}
    monkeypatch.setattr(NgspiceAdapter, "behavior_circuit", fake)
    run_resistor_recipes(audit, ["OHM-004"])
    assert not resistor_receipt_errors(audit, "OHM-004")
    path = audit.run_dir / "runtime-bench-results/OHM-004-op.json"
    receipt = json.loads(path.read_text())
    receipt["observations"] = [0]
    _atomic_json(path, receipt)
    assert any("observations" in e for e in resistor_receipt_errors(audit, "OHM-004"))
    receipt["observations"] = [2.5]
    receipt["recipe_source_sha256"] = "0" * 64
    _atomic_json(path, receipt)
    assert any("recipe_source" in e for e in resistor_receipt_errors(audit, "OHM-004"))


def test_mosfet_receipt_cannot_replace_captured_current(audit, monkeypatch):
    from ohmni.eda.simulation import NgspiceAdapter
    from tools.behavior_audit.runtime_benches import mosfet_receipt_errors, run_mosfet_recipes

    def fake(self, compiled, *, work_dir):
        branch = compiled.source_elements["drain"]
        return {"status": "ran", "stdout": f"{branch}#branch = -25\n", "stderr": "",
                "version_output": "ngspice-42", "problems": [],
                "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit",
                "operating_point": {"branch_currents": {branch: {"value": -25}}}}
    monkeypatch.setattr(NgspiceAdapter, "behavior_circuit", fake)
    run_mosfet_recipes(audit, ["OHM-098"])
    assert not mosfet_receipt_errors(audit, "OHM-098")
    path = audit.run_dir / "runtime-bench-results/OHM-098-op.json"
    receipt = json.loads(path.read_text())
    receipt["observed_current"] = 2500
    _atomic_json(path, receipt)
    assert any("captured current" in error for error in mosfet_receipt_errors(audit, "OHM-098"))


def test_failed_dc_contract_cannot_be_presented_as_passing(audit, monkeypatch):
    from ohmni.eda.simulation import NgspiceAdapter
    from tools.behavior_audit.runtime_benches import dc_probe_receipt_errors, run_dc_probes

    def fake(self, compiled, *, work_dir):
        node = compiled.node_names["anode"]
        # 0.73039 V (the old 27 C value) is outside the corrected 25 C contract 0.725559 +/- 1 mV.
        return {"status": "ran", "stdout": f"v({node}) = 0.73039\n", "stderr": "",
                "version_output": "ngspice-42", "problems": [],
                "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit"}
    monkeypatch.setattr(NgspiceAdapter, "behavior_circuit", fake)
    # OHM-062 still uses the shared class card, so it keeps the locked analytic comparison
    # (OHM-056 now has its own datasheet fit and a source-bound check, D048).
    receipts = run_dc_probes(audit, ["OHM-062"])
    assert receipts[0]["run_status"] == "failed"
    path = audit.run_dir / "runtime-bench-results/OHM-062-op.json"
    _atomic_json(path, dict(receipts[0], run_status="passed", observed=0.725559))
    assert any("raw observation" in error for error in dc_probe_receipt_errors(audit, "OHM-062"))


def test_rechecks_cannot_extend_the_repair_attempt_ceiling():
    from tools.behavior_audit.audit import _record_checkpoint_failure

    state = {"attempts": {}, "blocked_entries": {}}
    for _ in range(7):
        _record_checkpoint_failure(state, "stage3/bench", "unchanged contract failure", 3)
    assert state["attempts"]["stage3/bench"] == 3
    assert state["failed_gate_observations"]["stage3/bench"] == 7
    assert "stage3/bench" in state["blocked_entries"]
    state["attempts"]["stage2/bench"] = 9
    _record_checkpoint_failure(state, "stage2/bench", "historical observations", 3)
    assert state["attempts"]["stage2/bench"] == 3
    assert state["legacy_checkpoint_attempt_counts"]["stage2/bench"] == 9
    assert state["failed_gate_observations"]["stage2/bench"] == 10


def test_fitted_model_that_outputs_nothing_fails_the_curve_replay(audit, monkeypatch):
    """CBH-R03: the 0..vf_max bound alone accepts a dead model; the replayed read points do not."""
    from ohmni.behavior.loader import BehaviorRegistry
    from ohmni.behavior.netlist import load_recipes
    from ohmni.eda.simulation import NgspiceAdapter
    from tools.behavior_audit.runtime_benches import (
        dc_probe_definition,
        dc_probe_variants,
        run_dc_probes,
    )

    registry = BehaviorRegistry(repo_root=ROOT)
    recipe = load_recipes(registry, ROOT).entries["OHM-066"]
    variants = dc_probe_variants(recipe.behavior_id, recipe)
    assert variants == [None, "forward_fit1", "forward_fit2", "forward_fit3"]
    # The replayed points span the plotted range, each with its own expected voltage.
    points = [dc_probe_definition(audit, "OHM-066", v)[1]["comparison"] for v in variants[1:]]
    assert [p["test_current"] for p in points] == [0.01, 2.0, 20.0]
    assert all(p["kind"] == "absolute" and p["tolerance"] < 0.1 * p["expected"] + 0.03 for p in points)

    def dead_model(self, compiled, *, work_dir):
        node = compiled.node_names["anode"]
        return {"status": "ran", "stdout": f"v({node}) = 1e-12\n", "stderr": "",
                "version_output": "ngspice-42", "problems": [],
                "product_code_path": "ohmni.eda.simulation.NgspiceAdapter.behavior_circuit"}

    monkeypatch.setattr(NgspiceAdapter, "behavior_circuit", dead_model)
    receipts = {r.get("variant"): r["run_status"] for r in run_dc_probes(audit, ["OHM-066"])}
    assert receipts[None] == "passed"  # the bound check alone is satisfied by ~0 V
    assert all(receipts[v] == "failed" for v in variants[1:])
    # Coverage follows every receipt, so the entry cannot count as audited with a dead model.
    from tools.behavior_audit.runtime_benches import runtime_receipt_errors

    assert runtime_receipt_errors(audit, "OHM-066")


def test_withdrawn_source_is_rejected_while_a_bound_fact_still_cites_it(audit):
    """A manufacturer withdrawal never excuses a URL that a gapfill fact or recipe relies on."""
    dead = "https://example.invalid/withdrawn.pdf"
    bindings = {"approved_by": "owner", "approved_on": "2026-10-10", "supersessions": {},
                "withdrawn_sources": {dead: {"status": "withdrawn_by_manufacturer", "checks": ["404"],
                                             "checked_by": "someone", "checked_on": "2026-10-10"}}}
    audit.source_bindings = lambda: bindings
    missing = [f"AUD-SOURCE-001: missing successful archived fetch: {dead}"]
    remaining, errors = audit._withdrawn(list(missing), [])
    assert remaining == [] and errors == []
    # Cite it from a fact: the withdrawal no longer applies.
    original = audit._gapfill_evidence
    audit._gapfill_evidence = lambda entry_id: ({"field_updates": [{"field": "x", "value": 1, "sources": [dead]}]}
                                                if entry_id == "OHM-001" else original(entry_id))
    remaining, errors = audit._withdrawn(list(missing), [])
    assert remaining == missing and any("still cited" in e for e in errors)
    # Without a named checker it is not accepted either.
    audit._gapfill_evidence = original
    del bindings["withdrawn_sources"][dead]["checked_by"]
    remaining, errors = audit._withdrawn(list(missing), [])
    assert remaining == missing and any("named checker" in e for e in errors)


def test_rebaseline_is_explicit_and_never_absorbs_a_spec_change(audit, monkeypatch):
    from tools.behavior_audit.audit import AuditError

    old = audit._state()["protected_baseline"]
    monkeypatch.setattr(audit, "_protected_snapshot", lambda: {"main_ref": "after-merge", "protected_files": old.get("protected_files")})
    assert not audit.check_protected_state().passed
    with pytest.raises(AuditError):
        audit.rebaseline("", "owner")
    record = audit.rebaseline("PRs #3-#9 merged by the owner", "Jaden (owner)")
    assert record["old_main_ref"] == "baseline" and record["new_main_ref"] == "after-merge"
    assert audit._state()["baseline_history"][-1] == record
    assert "Baseline refresh" in (audit.run_dir / "DECISIONS.md").read_text(encoding="utf-8")
    # A changed protected spec file is never absorbed by a refresh.
    monkeypatch.setattr(audit, "_protected_snapshot", lambda: {"main_ref": "later", "protected_files": {"COMPONENT_BEHAVIOR_SPEC.md": "tampered"}})
    with pytest.raises(AuditError, match="spec"):
        audit.rebaseline("try to hide a spec edit", "nobody")


def test_rebuild_sources_verifies_bytes_against_the_ledger(tmp_path):
    from tools.behavior_audit.rebuild_sources import rebuild

    run = tmp_path / "run"
    (run / "fetched-sources").mkdir(parents=True)
    good = b"%PDF-1.4 good"
    digest = hashlib.sha256(good).hexdigest()
    rows = [
        {"url": "https://a.example/ok.pdf", "http_status": 200, "content_sha256": digest, "content_bytes": len(good)},
        {"url": "https://a.example/drift.pdf", "http_status": 200, "content_sha256": "0" * 64, "content_bytes": 3},
        {"url": "https://a.example/gone.pdf", "http_status": 200, "content_sha256": "1" * 64, "content_bytes": 3},
        {"url": "https://a.example/manual.pdf", "http_status": None, "content_sha256": "2" * 64,
         "manual_download": {"downloaded_by": "someone", "downloaded_on": "2026-10-10"}},
        {"url": "https://a.example/failed.pdf", "http_status": 404, "content_sha256": None},
    ]
    (run / "FETCH_LEDGER.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def fake_download(url):
        if url.endswith("ok.pdf"):
            return good
        if url.endswith("drift.pdf"):
            return b"something else"
        raise OSError("host refused")

    report = rebuild(run, download=fake_download)
    outcomes = {url.rsplit("/", 1)[1]: r["outcome"] for url, r in report["results"].items()}
    assert outcomes == {"ok.pdf": "rebuilt", "drift.pdf": "changed", "gone.pdf": "unavailable", "manual.pdf": "manual"}
    assert (run / "fetched-sources" / f"{digest}.bin").read_bytes() == good
    assert not list((run / "fetched-sources").glob("0*.bin"))  # changed bytes are never stored under the old hash
    assert rebuild(run, download=fake_download)["results"]["https://a.example/ok.pdf"]["outcome"] == "present"
