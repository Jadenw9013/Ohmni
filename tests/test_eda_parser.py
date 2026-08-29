import json

import pytest

from ohmni.eda.kicad.parser import ErcReportParseError, parse_erc_json
from ohmni.eda.models import ArtifactFingerprint, ErcStatus

FP = ArtifactFingerprint(digest="a" * 64)


def parse(tmp_path, payload):
    path = tmp_path / "erc.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return parse_erc_json(path, artifact_fingerprint=FP, run_id="run", command=["kicad-cli"], return_code=5)


def test_parser_preserves_finding_and_unknown_fields(tmp_path):
    report = parse(tmp_path, {"kicad_version": "10.0.5", "future": 1, "sheets": [{"path": "/", "violations": [{"type": "pin_to_pin", "severity": "warning", "description": "conflict", "future_field": 2, "items": [{"description": "Symbol U1", "uuid": "u", "pos": {"x": 1.0, "y": 2.0}}]}]}]})
    assert report.status is ErcStatus.PASS_WITH_WARNINGS
    assert report.findings[0].raw["future_field"] == 2
    assert report.findings[0].items[0].x == 1.0


@pytest.mark.parametrize("payload", [{}, {"kicad_version": "10", "sheets": {}}, {"kicad_version": "10", "sheets": ["bad"]}])
def test_parser_rejects_malformed_reports(tmp_path, payload):
    with pytest.raises(ErcReportParseError):
        parse(tmp_path, payload)


def test_error_severity_fails_and_exclusions_do_not(tmp_path):
    failed = parse(tmp_path, {"kicad_version": "10", "sheets": [{"violations": [{"severity": "error", "description": "bad"}]}]})
    excluded = parse(tmp_path, {"kicad_version": "10", "sheets": [{"violations": [{"severity": "exclusion", "description": "ignored"}]}]})
    assert failed.status is ErcStatus.FAIL
    assert excluded.status is ErcStatus.PASS
