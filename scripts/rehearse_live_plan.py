#!/usr/bin/env python3
"""Opt-in, one-call local AI planning rehearsal. Default invocation never calls AI.

Requires separate owner approval. Fixed public demo prompt; no production writes.
No automatic retries, at most one provider request and 4096 output tokens.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
PROMPT = ('A USB-C powered ESP32 board with one momentary input button and one indicator '
          'LED, no sensors, no SPI devices, no programming header, and a 100 by 70 mm board. '
          'I understand that separate firmware is required.')


class SinglePlanProvider:
    """Second requests and other operations fail before reaching the provider."""
    def __init__(self, provider, *, live=False):
        self.provider = provider
        self.live = live
        self.calls = 0
        self.usage = None
        self.lock = threading.Lock()

    def generate_structured(self, request, schema):
        with self.lock:
            if self.calls or request.request_type != 'project_plan':
                raise ValueError('rehearsal_call_limit')
            self.calls += 1
        try:
            return self.provider.generate_structured(request, schema)
        finally:
            usage = self.provider.last_call_usage()
            if usage is not None:
                self.usage = usage.model_dump(mode='json')


def configured_provider():
    from ohmni.adapters.anthropic_provider import AnthropicProvider
    owned = AnthropicProvider(max_attempts=1, max_tokens=4096)
    owned._client = owned._client.with_options(max_retries=0, timeout=45)
    return SinglePlanProvider(owned, live=True)


def validate_plan(plan: dict) -> None:
    from ohmni.application.hackathon_demo import DEMO_BRIEF
    expected = DEMO_BRIEF.model_dump(mode='json')
    if plan.get('ready') is not True or plan.get('questions'):
        raise ValueError('plan_needs_clarification')
    for field in expected.keys() - {'project_name', 'description'}:
        if plan['brief'].get(field) != expected[field]:
            raise ValueError('plan_differs_from_rehearsed_board')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-approved', action='store_true')
    parser.add_argument('--env-file', type=Path, help='Optional private local env file; never copied')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/live-plan-rehearsal')
    args = parser.parse_args(argv)
    if not args.execute_approved:
        print('NOT_RUN: requires explicit owner approval and --execute-approved; one request, '
              '4096 output-token maximum, no retries. No credentials read.')
        return 2
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'FAIL', 'kind': 'local_planning_rehearsal', 'provider_calls': 0,
              'max_output_tokens': 4096, 'automatic_retries': 0,
              'deployment': 'NOT_RUN', 'simulation': 'NOT_RUN'}
    provider = None
    server = None
    thread = None
    try:
        from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore, _load_local_env
        if args.env_file:
            if not args.env_file.is_file():
                raise ValueError('missing_env_file')
            _load_local_env(args.env_file)
        provider = configured_provider()
        result['model'] = provider.provider.model
        result['provider_mode'] = 'live' if provider.live else 'fixture'
        server = DemoHTTPServer(('127.0.0.1', 0), DemoHandler,
                                store=JobStore(output / 'workspace', provider=provider))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                context = browser.new_context(service_workers='block')
                origin = f'http://127.0.0.1:{server.server_address[1]}'
                # The browser talks only to our server. Only the bounded backend
                # provider above may contact Anthropic; telemetry stays off.
                context.route('**/*', lambda route: route.continue_() if
                              route.request.url.startswith(origin + '/') else route.abort())
                page = context.new_page()
                page.goto(origin + '/#workspace')
                page.locator('#free-text-request').fill(PROMPT)
                with page.expect_response(lambda r: r.url == origin + '/api/project-plans',
                                          timeout=60_000) as response:
                    page.locator('#start-free-text').click()
                reply = response.value
                if reply.status != 200:
                    raise ValueError('planner_request_rejected')
                plan = reply.json()['plan']
                validate_plan(plan)
                result['plan_fingerprint'] = plan['brief_fingerprint']
                page.locator('#conversation-confirm').click()
                page.locator('#review').wait_for(state='visible', timeout=240_000)
                page.locator('#open-build').click()
                link = page.get_by_role('link', name='Download complete build package')
                job_id = link.get_attribute('href').split('/')[3]
                job = page.request.get(origin + '/api/jobs/' + job_id).json()
                projects = server.projects.list_projects()
                if len(projects) != 1 or job['status'] != 'complete':
                    raise ValueError('unexpected_project_or_job')
                revision = server.projects.get(projects[0]['project_id'])['revisions'][0]
                if revision['brief_fingerprint'] != plan['brief_fingerprint']:
                    raise ValueError('confirmed_plan_changed')
                with page.expect_download(timeout=30_000) as download:
                    link.click()
                archive = output / 'build-package.zip'
                download.value.save_as(archive)
                from scripts.rehearse_core_demo import verify_package
                verify_package(archive.read_bytes(), job['report'], revision)
                result.update(status='PASS', confirmation='PASS', engineering='PASS', download='PASS')
            finally:
                browser.close()
    except Exception as error:  # noqa: BLE001 - sanitized fail-closed rehearsal report
        result['code'] = type(error).__name__  # never serialize raw provider exceptions
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=5)
        if provider:
            result['provider_calls'] = provider.calls
            result['usage'] = provider.usage
        (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"{result['status']}: local live plan rehearsal; no automatic retry")
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
