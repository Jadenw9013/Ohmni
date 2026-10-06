"""UI claims cannot survive a missing or changed receipt."""

from pathlib import Path
from types import SimpleNamespace

from tools.behavior_audit.ui_gate import ui_receipt_errors


def test_missing_browser_evidence_is_failure(tmp_path):
    audit = SimpleNamespace(root=tmp_path)
    assert ui_receipt_errors(audit)


def test_changed_browser_script_is_failure(monkeypatch):
    from tools.behavior_audit import ui_gate

    root = Path(__file__).resolve().parents[1]
    real_json = ui_gate._json

    def stale(path):
        if path.name == 'BROWSER_RESULTS.json':
            return {'passed': True, 'checks': [], 'script_sha256': '0' * 64}
        return real_json(path)

    monkeypatch.setattr(ui_gate, '_json', stale)
    assert 'Browser script changed after run' in ui_receipt_errors(SimpleNamespace(root=root))
