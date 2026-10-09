"""Candidate export must preserve failed evidence and never reuse a saved identity."""
import json
from pathlib import Path

import pytest

from tools.landing_redesign import build


def test_refuses_nonempty_output_before_overwriting_evidence(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    prior = output / "candidate-board.json"
    prior.write_text('{"prior":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="empty output"):
        build.generate(output, include_i2c_extension=False, captured_on="2026-10-09",
                       native=False)
    assert prior.read_text(encoding="utf-8") == '{"prior":true}'


def test_route_exhaustion_cannot_publish_scene_or_change_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "_tool_version", lambda *_: {"status": "NOT_RUN_TEST"})
    reference = Path(build.ROOT / "apps/web/reference-board.json")
    original = reference.read_bytes()
    output = tmp_path / "bounded"
    report = build.generate(output, include_i2c_extension=False, captured_on="2026-10-09",
                            route_seconds=0, native=False)
    assert report["status"] == "ROUTING_INCOMPLETE"
    assert not report["checks"]["routing"]["passed"]
    assert report["checks"]["topology"]["system_status"] == "UNKNOWN"
    assert not (output / "candidate-board.json").exists()
    persisted = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert persisted["original_reference_unchanged"]
    assert persisted["default_footprint_registry_restored"]
    assert reference.read_bytes() == original
