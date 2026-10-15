#!/usr/bin/env python3
"""Rehearse all three guided starters through real UI, HTTP, KiCad and downloads.

No provider, account or telemetry is enabled. Uses a new local workspace per run,
a loopback-only browser, and a bounded child process. This is not a live AI test.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
FAMILIES = ('a1_usb_i2c_sensor', 'a2_usb_gpio_controller', 'a3_usb_spi_peripheral')
STEPS = ('starter', 'generation', 'rendered_board', 'current_report', 'download', 'back_navigation',
         'mobile_layout', 'reopen_same_run')


def verify_package(blob: bytes, report: dict, revision: dict) -> None:
    """Check downloaded bytes against the actual job and saved input, not the UI badge."""
    release = report['release']
    if (release['current'] is not True or release['status'] != 'READY_FOR_MANUFACTURING_REVIEW'
            or report['pcb']['current'] is not True or report['pcb']['drc_status'] != 'PASS'
            or report['schematic']['current'] is not True
            or report['schematic']['erc_status'] not in ('PASS', 'PASS_WITH_WARNINGS')):
        raise ValueError('release_not_current')
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > 32_000_000:
            raise ValueError('invalid_package_inventory')
        for section, name in (('pcb', 'golden.kicad_pcb'), ('schematic', 'golden.kicad_sch')):
            if hashlib.sha256(archive.read(name)).hexdigest() != report[section]['fingerprint']:
                raise ValueError('engineering_hash_mismatch')
        for item in [*release['files'], release['manifest']]:
            data = archive.read('fabrication/' + item['relative_path'])
            if len(data) != item['size_bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError('fabrication_hash_mismatch')
        if json.loads(archive.read('report.json')) != report:
            raise ValueError('report_mismatch')
        if json.loads(archive.read('confirmed-brief.json')) != revision['brief']:
            raise ValueError('brief_mismatch')
        receipt = json.loads(archive.read('project-revision.json'))
        for key in ('revision_id', 'job_id', 'brief_fingerprint'):
            if receipt[key] != revision[key]:
                raise ValueError('revision_mismatch')
        if receipt['package_fingerprint'] != release['package_fingerprint']:
            raise ValueError('package_lineage_mismatch')


def qualified(result: dict, process: dict) -> bool:
    """No skipped family, absent check, blocked worker or empty result can pass."""
    return (process.get('exit_code') == 0 and process.get('timed_out') is False
            and result.get('status') == 'PASS'
            and result.get('provider_calls') == 0
            and result.get('external_requests') == 0
            and result.get('page_errors') == 0
            and result.get('planner_recovery') is True
            and result.get('restart_recovery') is True
            and set(result.get('families', {})) == set(FAMILIES)
            and all(set(checks) == set(STEPS) and all(v is True for v in checks.values())
                    for checks in result['families'].values()))


def worker(output: Path) -> int:
    from ohmni.adapters.tools import find_kicad_cli
    from scripts.verify_hackathon_demo import kicad_version

    result = {'status': 'FAIL', 'provider_calls': 0, 'external_requests': 0, 'page_errors': 0,
              'families': {}, 'live_ai': 'NOT_RUN', 'simulation': 'NOT_RUN'}
    server = None
    thread = None
    try:
        executable = find_kicad_cli()
        version = kicad_version(executable) if executable else None
        result['kicad_version'] = version
        if version != '10.0.5':
            result.update(status='BLOCKED', code='requires_kicad_10_0_5')
            return 2
        from playwright.sync_api import sync_playwright

        from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore
        server = DemoHTTPServer(('127.0.0.1', 0), DemoHandler,
                                store=JobStore(output / 'workspace', provider=None))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_address[1]}'
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                              accept_downloads=True, service_workers='block')

                def route(request_route):
                    target = urlsplit(request_route.request.url)
                    if target.scheme in ('data', 'blob') or (
                            target.scheme == 'http' and target.netloc == urlsplit(origin).netloc):
                        request_route.continue_()
                    else:
                        result['external_requests'] += 1
                        request_route.abort()

                context.route('**/*', route)
                page = context.new_page()
                page.on('pageerror', lambda _: result.update(page_errors=result['page_errors'] + 1))
                for family in FAMILIES:
                    checks = result['families'][family] = {}
                    started = time.monotonic()
                    page.goto(origin + '/#workspace')
                    page.locator('#sidebar-new-project').click()
                    page.locator(f'[data-starter-family="{family}"]').click()
                    page.get_by_role('button', name='Generate my board', exact=True).wait_for()
                    checks['starter'] = True
                    page.get_by_role('button', name='Generate my board', exact=True).click()
                    page.wait_for_function('''() => !document.querySelector('#review').hidden
                        || !document.querySelector('#run-error').hidden''', timeout=240_000)
                    if not page.locator('#review').is_visible():
                        raise ValueError('generation_failed')
                    checks['generation'] = True
                    page.wait_for_function("() => ['three','webgl'].includes(document.querySelector('#board-canvas')?.dataset.renderer)", timeout=10000)
                    checks['rendered_board'] = True
                    page.locator('#open-build').click()
                    link = page.get_by_role('link', name='Download complete build package')
                    link.wait_for()
                    job_id = link.get_attribute('href').split('/')[3]
                    job = page.request.get(origin + '/api/jobs/' + job_id).json()
                    projects = page.request.get(origin + '/api/projects').json()['projects']
                    matches = []
                    for project in projects:
                        full = page.request.get(origin + '/api/projects/' + project['project_id']).json()['project']
                        matches.extend((full['project_id'], r) for r in full['revisions'] if r['job_id'] == job_id)
                    if len(matches) != 1 or job['status'] != 'complete':
                        raise ValueError('job_revision_binding')
                    project_id, revision = matches[0]
                    if revision['brief']['archetype'] != family:
                        raise ValueError('wrong_starter_family')
                    checks['current_report'] = job['report']['release']['current'] is True
                    with page.expect_download(timeout=30_000) as download:
                        link.click()
                    target = output / (family + '.zip')
                    download.value.save_as(target)
                    verify_package(target.read_bytes(), job['report'], revision)
                    checks['download'] = True
                    page.locator('#back-to-board').click()
                    page.locator('#review').wait_for(state='visible')
                    checks['back_navigation'] = True
                    page.set_viewport_size({'width': 390, 'height': 844})
                    # Wait for the real view to resize; persistent overflow fails.
                    page.wait_for_function('''() => Math.max(document.documentElement.scrollWidth,
                        document.body.scrollWidth) <= document.documentElement.clientWidth''', timeout=5000)
                    checks['mobile_layout'] = True
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    page.screenshot(path=str(output / (family + '.png')))
                    page.reload()
                    page.locator(f'[data-project-open="{project_id}"]').first.click()
                    page.get_by_role('button', name="Open this revision's run", exact=True).click()
                    page.locator('#review').wait_for(state='visible')
                    page.locator('#open-build').click()
                    reopened = page.get_by_role('link', name='Download complete build package')
                    checks['reopen_same_run'] = reopened.get_attribute('href') == f'/api/artifacts/{job_id}/build-package.zip'
                    print(f'{family}: {sum(checks.values())}/{len(STEPS)} checks in {time.monotonic()-started:.1f}s', flush=True)
                class UnavailableProvider:
                    calls = 0

                    def generate_structured(self, request, schema):
                        self.calls += 1
                        raise RuntimeError('Synthetic rehearsal outage')

                unavailable = UnavailableProvider()
                server.store.provider = unavailable
                server.planner.provider = unavailable
                page.goto(origin + '/#workspace')
                page.reload()
                page.locator('#sidebar-new-project').click()
                prompt = 'A USB-powered ESP32 with one button and one status light.'
                page.locator('#free-text-request').fill(prompt)
                page.locator('#start-free-text').click()
                page.locator('#conversation-guided-recovery').wait_for()
                if prompt not in page.locator('#conversation').inner_text():
                    raise ValueError('failed_plan_lost_request')
                page.locator('#flow-back').click()
                if page.locator('#free-text-request').input_value() != prompt:
                    raise ValueError('back_navigation_lost_request')
                page.locator('#start-free-text').click()
                page.locator('#conversation-guided-recovery').click()
                page.locator('#project-run').wait_for(state='visible')
                result['planner_recovery'] = unavailable.calls == 2
                result['simulated_provider_failures'] = unavailable.calls
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                server = DemoHTTPServer(('127.0.0.1', 0), DemoHandler,
                                        store=JobStore(output / 'workspace', provider=None))
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                origin = f'http://127.0.0.1:{server.server_address[1]}'
                page.goto(origin + '/#workspace')
                page.locator(f'[data-project-open="{project_id}"]').first.click()
                page.get_by_role('button', name="Open this revision's run", exact=True).click()
                page.locator('#review').wait_for(state='visible')
                page.locator('#open-build').click()
                restored_link = page.get_by_role('link', name='Download complete build package')
                restored = page.request.get(origin + '/api/jobs/' + job_id).json()
                result['restart_recovery'] = (restored['status'] == 'complete' and
                    restored_link.get_attribute('href') == f'/api/artifacts/{job_id}/build-package.zip')
                result['status'] = 'PASS'
            finally:
                browser.close()
        if not qualified(result, {'exit_code': 0, 'timed_out': False}):
            result['status'] = 'FAIL'
        return 0 if result['status'] == 'PASS' else 1
    except Exception as error:  # noqa: BLE001 - sanitized fail-closed rehearsal report
        result['code'] = type(error).__name__  # no raw exception, path or body in report
        return 1
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=5)
        (output / 'core-flow.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/core-demo-rehearsal')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if args.worker:
        return worker(output)
    # Refuse reuse so old evidence can never masquerade as this run.
    output.mkdir(parents=True, exist_ok=False)
    from scripts.run_browser_acceptance import run, scrubbed_environment
    env, _ = scrubbed_environment(dict(os.environ))
    env['OHMNI_TELEMETRY_ENABLED'] = '0'
    process = run([sys.executable, str(Path(__file__).resolve()), '--worker', '--output', str(output)],
                  env, output / 'worker.log', timeout=900)
    try:
        result = json.loads((output / 'core-flow.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        result = {}
    status = 'PASS' if qualified(result, process) else 'FAIL'
    summary = {'status': status, 'process': process, 'result': result,
               'candidate_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
               'limitations': ['Local guided flow only; no paid AI or production writes.',
                               'Native checks do not establish firmware or hardware bench behavior.']}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(f'{status}: core demo rehearsal; report {output / "summary.json"}')
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
