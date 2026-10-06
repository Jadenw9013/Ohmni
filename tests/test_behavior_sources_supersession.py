"""Source supersessions, local artifact bindings and manual downloads stay evidence-bound."""

import hashlib
import json
from pathlib import Path

import pytest

from tools.behavior_audit import BehaviorAudit, evidence

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "AUD-SOURCE-001: missing successful archived fetch: "
OLD, NEW = "https://mirror.example/old.pdf", "https://maker.example/new.pdf"


@pytest.fixture
def audit(tmp_path, monkeypatch):
    value = BehaviorAudit(ROOT, tmp_path / "run")
    monkeypatch.setattr(value, "_protected_snapshot", lambda: {"main_ref": "baseline"})
    value.initialize()
    return value


def _archive(run_dir, url, content=b"%PDF-1.4 test", **row):
    digest = hashlib.sha256(content).hexdigest()
    (run_dir / "fetched-sources").mkdir(parents=True, exist_ok=True)
    (run_dir / "fetched-sources" / f"{digest}.bin").write_bytes(content)
    base = {"url": url, "http_status": 200, "content_sha256": digest, "timestamp": "t", "tool_used": "test"}
    base.update(row)
    return base


def _bindings(audit, monkeypatch, approved=True, **entry):
    table = {OLD: dict({"archive_url": NEW, "supports": "yes", "evidence": "p1"}, **entry)}
    doc = {"approved_by": "r" if approved else "", "approved_on": "2026-10-05" if approved else "", "supersessions": table}
    monkeypatch.setattr(audit, "source_bindings", lambda: doc)


def test_supersession_needs_an_archived_replacement(audit, monkeypatch):
    _bindings(audit, monkeypatch)
    remaining, _ = audit._superseded([PREFIX + OLD], [])
    assert remaining
    ledger = [_archive(audit.run_dir, NEW)]
    remaining, errors = audit._superseded([PREFIX + OLD], ledger)
    assert not remaining and not errors


def test_unapproved_supersession_does_not_satisfy(audit, monkeypatch):
    _bindings(audit, monkeypatch, approved=False)
    remaining, errors = audit._superseded([PREFIX + OLD], [_archive(audit.run_dir, NEW)])
    assert remaining and errors


def test_partial_supersession_must_explain_the_gap(audit, monkeypatch):
    _bindings(audit, monkeypatch, supports="partial", note="")
    remaining, errors = audit._superseded([PREFIX + OLD], [_archive(audit.run_dir, NEW)])
    assert remaining and errors


def test_supersession_cannot_point_at_itself(audit, monkeypatch):
    _bindings(audit, monkeypatch, archive_url=OLD)
    remaining, errors = audit._superseded([PREFIX + OLD], [_archive(audit.run_dir, OLD)])
    assert remaining and errors


def test_manual_download_needs_named_provenance_and_no_invented_status(tmp_path):
    good = _archive(tmp_path, NEW, http_status=None, manual_download={"downloaded_by": "owner", "downloaded_on": "2026-10-05"})
    assert not evidence.source_errors({NEW}, [good], tmp_path)
    anonymous = _archive(tmp_path, NEW, http_status=None, manual_download={"downloaded_by": ""})
    assert evidence.source_errors({NEW}, [anonymous], tmp_path)
    claimed = _archive(tmp_path, NEW, http_status=None)
    assert evidence.source_errors({NEW}, [claimed], tmp_path)


def test_manual_download_bytes_must_match(tmp_path):
    row = _archive(tmp_path, NEW, http_status=None, manual_download={"downloaded_by": "owner", "downloaded_on": "d"})
    (tmp_path / "fetched-sources" / f"{row['content_sha256']}.bin").write_bytes(b"%PDF-tampered")
    assert evidence.source_errors({NEW}, [row], tmp_path)


def test_artifact_binding_locks_file_bytes(tmp_path):
    from tools.behavior_audit.sources import _artifact_binding_errors

    (tmp_path / "docs/behavior").mkdir(parents=True)
    (tmp_path / "local.txt").write_text("evidence")
    digest = hashlib.sha256(b"evidence").hexdigest()
    doc = {"approved_by": "r", "approved_on": "d", "artifact_bindings": {"BEH-X/S1": {"files": {"local.txt": digest}}}}
    (tmp_path / "docs/behavior/SOURCE_BINDINGS.json").write_text(json.dumps(doc))
    assert _artifact_binding_errors(tmp_path, "BEH-X/S1") is None
    (tmp_path / "local.txt").write_text("changed")
    assert _artifact_binding_errors(tmp_path, "BEH-X/S1")
    assert _artifact_binding_errors(tmp_path, "BEH-X/S2") == "unbound"
