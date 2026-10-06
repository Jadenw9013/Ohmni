"""Capture frontend checks and reject missing, failed or stale browser evidence."""

import re
import subprocess

from .audit import AuditError, _atomic_json, _atomic_text, _json, _now, _sha_bytes
from .evidence import version_42


def frontend_sources(root):
    return {str(p.relative_to(root)).replace('\\', '/'): _sha_bytes(p.read_bytes())
            for p in sorted((root / 'apps/web').rglob('*')) if p.is_file()}


def run_frontend(audit):
    files = sorted(str(p.relative_to(audit.root)) for p in (audit.root / 'apps/web/tests').glob('*.test.mjs'))
    result = subprocess.run(['node', '--test', *files], cwd=audit.root, capture_output=True, text=True, encoding='utf-8', check=False)
    output = result.stdout + result.stderr
    path = audit.root / 'out/component-behavior/stage-6/frontend-output.txt'
    _atomic_text(path, output)
    receipt = {'timestamp': _now(), 'exit_code': result.returncode,
               'output_sha256': _sha_bytes(path.read_bytes()), 'sources': frontend_sources(audit.root)}
    _atomic_json(path.with_name('FRONTEND_RESULTS.json'), receipt)
    return receipt


def ui_receipt_errors(audit):
    from scripts.demo_server import _load_web_snapshot

    base = audit.root / 'out/component-behavior/stage-6'
    errors = []
    try:
        browser = _json(base / 'browser/BROWSER_RESULTS.json')
        if (browser.get('passed') is not True or len(browser.get('checks', [])) != 8
                or any(c.get('passed') is not True for c in browser['checks']) or browser.get('page_errors')):
            errors.append('Browser checks failed or incomplete')
        if browser.get('script_sha256') != _sha_bytes((audit.root / 'scripts/verify_behavior_ui.cjs').read_bytes()):
            errors.append('Browser script changed after run')
        if browser.get('server_identity', {}).get('ui_version') != _load_web_snapshot(audit.root / 'apps/web')[1]:
            errors.append('Browser evidence belongs to different UI assets')
        if set(browser.get('screenshots', {})) != {'desktop.png', 'mobile.png'}:
            errors.append('Missing desktop/mobile capture')
        for name, digest in browser.get('screenshots', {}).items():
            if name not in {'desktop.png', 'mobile.png'} or _sha_bytes((base / 'browser' / name).read_bytes()) != digest:
                errors.append('Screenshot missing or changed')
        runs = browser.get('runs', [])
        if [(r.get('entry_id'), r.get('rating_status')) for r in runs] != [('OHM-004', 'unknown'), ('OHM-069', 'violation')]:
            errors.append('Real browser run outcomes missing')
        for row in runs:
            if row.get('status') != 'ran' or not version_42(row.get('version_output', '')):
                errors.append('Browser simulation did not run in ngspice42')
        receipt = _json(base / 'FRONTEND_RESULTS.json')
        output = (base / 'frontend-output.txt').read_bytes()
        if (receipt.get('exit_code') != 0 or receipt.get('output_sha256') != _sha_bytes(output)
                or receipt.get('sources') != frontend_sources(audit.root)):
            errors.append('Frontend results failed or stale')
        counts = dict(re.findall(r'^# (tests|pass|fail|cancelled|skipped) (\d+)\s*$', output.decode('utf-8'), re.MULTILINE))
        if (int(counts.get('pass', 0)) == 0 or counts.get('tests') != counts.get('pass')
                or counts.get('fail') != '0' or counts.get('cancelled') != '0'):
            errors.append('Frontend output lacks a complete passing run')
    except (AuditError, OSError, KeyError, ValueError, TypeError) as exc:
        errors.append(f'UI evidence unavailable: {type(exc).__name__}')
    return errors


def write_ui_gate(audit):
    errors = ui_receipt_errors(audit)
    result = {'timestamp': _now(), 'passed': not errors, 'errors': errors}
    _atomic_json(audit.run_dir / 'UI_RESULTS.json', result)
    lines = ['# Stage6 UI gate', '', f"UI evidence validation: **{'FAIL' if errors else 'PASS'}**.", '',
             'Browser coverage checks all 180 rendered selection identities, two actual ngspice42 runs, blocked entries, synthetic error/stale-response handling, mobile access and keyboard controls.',
             'Run is an authored reference circuit; saved projects are unchanged. Rating unknown and violation remain distinct from simulation execution. No corpus acceptance is implied.',
             'Removed an invalid universal marking override that prevented resistor previews from replacing the previously selected model.', '',
             *[f'- {e}' for e in errors]]
    _atomic_text(audit.root / 'out/component-behavior/stage-6/UI-GATE.md', '\n'.join(lines) + '\n')
    return result
