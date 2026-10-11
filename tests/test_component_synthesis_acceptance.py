"""CS-T11 acceptance inventory, portable proof and fail-closed reporting."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ohmni.datasheet.observations import ObservationLimitError
from ohmni.datasheet.pdf import BoundedObservationExtractor

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/component_synthesis_acceptance.py"
SPEC = importlib.util.spec_from_file_location("component_synthesis_acceptance", SCRIPT)
assert SPEC and SPEC.loader
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


def _cases() -> dict:
    return json.loads(acceptance.CASE_MANIFEST.read_text(encoding="utf-8"))


def test_every_declared_acceptance_selector_resolves_to_a_real_test():
    cases = _cases()
    selectors = [
        selector
        for group in cases["positive_evidence"]
        for selector in group["selectors"]
    ] + cases["negative_corpus"]
    assert len(selectors) == len(set(selectors))
    assert len(cases["negative_corpus"]) >= 12
    assert all(acceptance._selector_exists(selector) for selector in selectors)


def test_prior_stage_records_are_present_and_keep_nonideal_statuses_explicit():
    records, errors = acceptance._prior_verification()
    assert not errors
    assert [item["task"] for item in records] == list(acceptance.PRIOR_STAGES)
    statuses = {item["task"]: item["status"] for item in records}
    assert statuses["CS-T02"] == "PASSED_WITH_UNAVAILABLE_GATE"
    assert statuses["CS-T08"] == "PASSED_WITH_EXTERNAL_BASELINE_FAILURE"


def test_lm317_portable_export_reconstructs_exact_bytes_after_restart(tmp_path: Path):
    evidence, errors = acceptance._portable_evidence(tmp_path / "portable")
    assert not errors
    assert evidence["restart_reconstructed"]
    assert all(item["passed"] for item in evidence["hash_checks"].values())
    assert evidence["assets"][0]["asset_id"] == "TI_LM317_DCY"


def test_missing_real_cad_evidence_cannot_produce_an_acceptance_pass(tmp_path: Path):
    result = acceptance.run(tmp_path / "absent.json", tmp_path / "report")
    report = json.loads((tmp_path / "report/acceptance-report.json").read_text())
    assert result == 1
    assert report["status"] == "FAIL"
    assert "real CAD evidence file is absent" in report["errors"]


@pytest.mark.corpus
def test_pinned_real_source_bytes_are_present_for_final_acceptance():
    source, errors = acceptance._source_evidence()
    if errors:
        pytest.fail("; ".join(errors))
    microchip = next(item for item in source["documents"] if item["id"].startswith("MCP73831"))
    assert microchip["actual_sha256"] == microchip["expected_sha256"]


@pytest.mark.corpus
def test_held_out_mcp1700_sot23_drawing_fails_closed_without_parser_adaptation():
    path = ROOT / "build/corpus/MCP1700-DS20001826F.pdf"
    if not path.is_file():
        pytest.fail("held-out MCP1700 source is absent; run scripts/acquire_corpus.py")
    with pytest.raises(ObservationLimitError, match="rules"):
        BoundedObservationExtractor().observe(path, [19])


def test_operational_document_names_commands_and_support_boundaries():
    text = (ROOT / "docs/COMPONENT_SYNTHESIS.md").read_text(encoding="utf-8")
    for command in (
        "scripts\\acquire_corpus.py",
        "scripts\\component_cad_proof.py",
        "scripts\\component_synthesis_acceptance.py",
        "scripts\\verify.py full",
        "scripts\\verify.py integration",
        "scripts\\verify.py slow",
        "-m ohmni verify-all",
        "-m ruff check .",
    ):
        assert command in text
    for boundary in ("zero error rate", "IPC compliance", "thermal", "arbitrary"):
        assert boundary in text
