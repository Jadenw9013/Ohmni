"""Owned planning/build orchestration and private artifact boundary regressions."""
from uuid import uuid4

from ohmni.application.conversation import BoardPlan
from ohmni.application.hackathon_demo import DEMO_BRIEF
from ohmni.application.project_store import ProjectStore
from ohmni.integrations.fetch_ai.bridge import ChatBridge, describe_result, owner_key


class Provider:
    def __init__(self):
        self.calls = 0
        self.questions = ()

    def generate_structured(self, request, schema):
        self.calls += 1
        return BoardPlan(brief=DEMO_BRIEF, questions=self.questions)


class Jobs:
    def __init__(self, root):
        self.project_store = ProjectStore(root)
        self.items = {}
        self.starts = 0
        self.package_current = True

    def start_revision(self, project, revision):
        previous = self.project_store.revision(project, revision)['job_id']
        if previous and self.items[previous]['status'] != 'failed':
            return previous
        self.starts += 1
        job = uuid4().hex[:12]
        self.items[job] = {'job_id': job, 'status': 'queued', 'report': None, 'error': None, 'error_code': None, 'progress': []}
        self.project_store.claim_job(project, revision, self.items[job], previous)
        return job

    def get(self, job):
        return self.items.get(job)

    def read_build_package(self, job):
        return ('current', b'checked-zip') if self.package_current else ('stale', None)

    def stop(self):
        pass


def setup(tmp_path):
    provider = Provider()
    jobs = Jobs(tmp_path)
    clock = [1000.0]
    bridge = ChatBridge(tmp_path, provider, 'https://agent.example', jobs=jobs, clock=lambda: clock[0])
    return bridge, provider, jobs, clock


def send(bridge, session, text, *, sender='signed-agent', message=None):
    return bridge.handle(sender, session, message or str(uuid4()), text)


def confirm_code(bridge, session):
    with bridge.db() as db:
        return bridge._load(db, owner_key('signed-agent', session))['plan']['plan_id']


def test_no_build_without_exact_latest_owned_review_and_no_duplicate_build(tmp_path):
    bridge, provider, jobs, _ = setup(tmp_path)
    session = str(uuid4())
    try:
        reply = send(bridge, session, 'A USB ESP32 with one button and one LED, no sensors.')
        assert 'AI/default choices to review' in reply
        assert jobs.starts == 0
        code = confirm_code(bridge, session)
        assert 'cannot start' in send(bridge, session, 'yes')
        assert 'does not match' in send(bridge, str(uuid4()), 'CONFIRM ' + code)
        assert 'does not match' in send(bridge, session, 'CONFIRM ' + code, sender='another-agent')
        assert jobs.starts == 0
        message = str(uuid4())
        first = send(bridge, session, 'CONFIRM ' + code, message=message)
        assert 'queued' in first
        assert send(bridge, session, 'CONFIRM ' + code, message=message) == first
        send(bridge, session, 'CONFIRM ' + code)
        send(bridge, session, 'STATUS')
        assert jobs.starts == 1 and provider.calls == 1
    finally:
        bridge.close()


def test_questions_expiry_and_changed_plan_invalidate_confirmation(tmp_path):
    bridge, provider, jobs, clock = setup(tmp_path)
    session = str(uuid4())
    try:
        provider.questions = ('Would a temperature sensor be an acceptable supported alternative?',)
        send(bridge, session, 'I want a smell detector.')
        old = confirm_code(bridge, session)
        assert 'unresolved' in send(bridge, session, 'CONFIRM ' + old)
        provider.questions = ()
        send(bridge, session, 'Use the button and LED option instead.')
        assert 'does not match' in send(bridge, session, 'CONFIRM ' + old)
        current = confirm_code(bridge, session)
        clock[0] += 1801
        assert 'expired' in send(bridge, session, 'CONFIRM ' + current)
        assert jobs.starts == 0
    finally:
        bridge.close()


def test_persistent_deduplication_and_confirmed_revision_survive_restart(tmp_path):
    bridge, provider, jobs, clock = setup(tmp_path)
    session, message = str(uuid4()), str(uuid4())
    send(bridge, session, 'A USB ESP32 button and LED board.', message=message)
    code = confirm_code(bridge, session)
    bridge.close()
    bridge = ChatBridge(tmp_path, provider, 'https://agent.example', jobs=jobs, clock=lambda: clock[0])
    try:
        send(bridge, session, 'A USB ESP32 button and LED board.', message=message)
        assert provider.calls == 1
        send(bridge, session, 'CONFIRM ' + code)
        assert jobs.starts == 1
    finally:
        bridge.close()


def test_private_links_expire_and_cannot_bypass_stale_artifact_checks(tmp_path):
    bridge, _, jobs, clock = setup(tmp_path)
    session = str(uuid4())
    try:
        send(bridge, session, 'A USB ESP32 button and LED board.')
        send(bridge, session, 'CONFIRM ' + confirm_code(bridge, session))
        owner = owner_key('signed-agent', session)
        job = bridge.latest_job(owner)
        jobs.items[job].update(status='complete', report={'project': {'status': 'READY_FOR_MANUFACTURING_REVIEW'}, 'requirements': [
            {'status': 'VIOLATED', 'label': 'Hand soldering', 'detail': 'Reflow required.'},
            {'status': 'UNKNOWN', 'label': 'RF operation', 'detail': 'Not measured.'}], 'verification_ladder': []})
        reply = send(bridge, session, 'FILES')
        assert 'VIOLATED: 1' in reply and 'UNKNOWN: 1' in reply
        token = reply.split('/downloads/')[1].split('/')[0]
        assert bridge.download(token) == b'checked-zip'
        assert bridge.download('../' + token) is None
        assert 'no generated board' in send(bridge, str(uuid4()), 'FILES')
        jobs.package_current = False
        assert bridge.download(token) is None
        assert 'withheld' in send(bridge, session, 'FILES')
        jobs.package_current = True
        clock[0] += 3601
        assert bridge.download(token) is None
    finally:
        bridge.close()


def test_failed_job_never_claims_download_or_retries_without_command():
    reply = describe_result({'job_id': 'abc', 'status': 'failed', 'error_code': 'server_restarted'})
    assert 'failed (server_restarted)' in reply and 'No current manufacturing package' in reply


def test_interrupted_message_is_not_billed_again(tmp_path):
    bridge, provider, jobs, _ = setup(tmp_path)
    session, message = str(uuid4()), str(uuid4())
    try:
        with bridge.db() as db:
            db.execute('INSERT INTO messages VALUES(?,?,NULL,?)', (owner_key('signed-agent', session), message, 1000))
        assert 'interrupted' in send(bridge, session, 'Please generate a board.', message=message)
        assert provider.calls == 0 and jobs.starts == 0
    finally:
        bridge.close()


def test_result_questions_are_grounded_and_edits_require_fresh_confirmation(tmp_path):
    from ohmni.application.iteration import IterationResponse

    class IteratingProvider(Provider):
        def generate_structured(self, request, schema):
            if request.request_type != 'project_iteration':
                return super().generate_structured(request, schema)
            self.calls += 1
            if request.data['messages'][-1] == 'Why did the build fail?':
                return IterationResponse(kind='answer', fact_ids=('run.failure',))
            updated = DEMO_BRIEF.model_copy(update={'status_led_count': 2})
            return IterationResponse(kind='change', proposal=BoardPlan(brief=updated))

    provider, jobs = IteratingProvider(), Jobs(tmp_path)
    bridge = ChatBridge(tmp_path, provider, 'https://agent.example', jobs=jobs)
    session = str(uuid4())
    try:
        send(bridge, session, 'A USB ESP32 button and LED board.')
        original = confirm_code(bridge, session)
        send(bridge, session, 'CONFIRM ' + original)
        job = bridge.latest_job(owner_key('signed-agent', session))
        jobs.items[job].update(status='failed', error_code='server_restarted')
        answer = send(bridge, session, 'Why did the build fail?')
        assert 'server restarted' in answer and jobs.starts == 1
        proposal = send(bridge, session, 'Use two LEDs instead.')
        assert 'status_led_count: 1 → 2' in proposal and jobs.starts == 1
        assert 'does not match' in send(bridge, session, 'CONFIRM ' + original)
        send(bridge, session, 'CONFIRM ' + confirm_code(bridge, session))
        assert jobs.starts == 2
        with bridge.db() as db:
            state = bridge._load(db, owner_key('signed-agent', session))
        project = bridge.projects.get(state['project_id'])
        assert len(project['revisions']) == 2
    finally:
        bridge.close()


def test_gateway_blocks_inspector_and_arbitrary_paths_and_serves_only_capability():
    import asyncio

    import pytest

    ClientSession = pytest.importorskip('aiohttp').ClientSession

    from ohmni.integrations.fetch_ai.http import start_gateway

    class DownloadBridge:
        def download(self, token):
            return b'checked-package' if token == 'valid' else None

    async def check():
        runner, client = await start_gateway(DownloadBridge(), public_port=0, sdk_port=1)
        port = runner.addresses[0][1]
        try:
            async with ClientSession() as session:
                for path in ['/connect', '/disconnect', '/messages', '/api/projects', '/downloads/wrong/build-package.zip']:
                    async with session.get(f'http://127.0.0.1:{port}{path}') as response:
                        assert response.status == 404
                async with session.get(f'http://127.0.0.1:{port}/downloads/valid/build-package.zip') as response:
                    assert response.status == 200
                    assert await response.read() == b'checked-package'
                    assert response.headers['Cache-Control'] == 'private, no-store'
                    assert response.headers['Referrer-Policy'] == 'no-referrer'
        finally:
            await runner.cleanup()
            await client.close()
    asyncio.run(check())


def test_fetch_provider_timeout_disables_hidden_transport_retries(monkeypatch):
    import sys
    from types import SimpleNamespace

    from ohmni.adapters import AnthropicProvider

    received = {}
    monkeypatch.setitem(sys.modules, 'anthropic', SimpleNamespace(Anthropic=lambda **kwargs: received.update(kwargs)))
    AnthropicProvider(api_key='test-only', timeout_seconds=20, max_attempts=2)
    assert received == {'api_key': 'test-only', 'timeout': 20, 'max_retries': 0}


def test_grounded_report_facts_are_readable_and_specific_not_raw_collections(tmp_path):
    bridge, _, jobs, _ = setup(tmp_path)
    session = str(uuid4())
    try:
        send(bridge, session, 'A USB ESP32 button and LED board.')
        send(bridge, session, 'CONFIRM ' + confirm_code(bridge, session))
        with bridge.db() as db:
            state = bridge._load(db, owner_key('signed-agent', session))
        job = state['job_id']
        jobs.items[job].update(status='complete', report={'requirements': [
            {'label': 'Firmware', 'status': 'UNKNOWN', 'display_value': 'Not supplied', 'detail': 'No firmware included.'}],
            'limitations': ['No physical tests.'], 'verification_ladder': []})
        context, _ = bridge.assistant._context(state['project_id'], state['revision_id'])
        selected = next(f for f in context['facts'] if f['id'] == 'report.requirements.0')
        assert selected['value'] == 'Firmware; UNKNOWN; Not supplied; No firmware included.'
        assert not any(f['id'] == 'report.requirements' for f in context['facts'])
        assert next(f for f in context['facts'] if f['id'] == 'report.requirements.summary')['value'] == 'MET: 0; VIOLATED: 0; UNKNOWN: 1'
    finally:
        bridge.close()
