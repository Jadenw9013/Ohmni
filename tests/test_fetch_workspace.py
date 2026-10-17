"""Revision isolation, expiry, grounding, and the actual public HTTP boundary."""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from test_fetch_bridge import confirm_code, owner_key, send, setup

from ohmni.integrations.fetch_ai.workspace import TeachingAnswer, WorkspaceUnavailable


def prepared(tmp_path):
    bridge, provider, jobs, clock = setup(tmp_path)
    session = str(uuid4())
    send(bridge, session, 'A USB ESP32 with one button and one LED, no sensors.')
    send(bridge, session, 'CONFIRM ' + confirm_code(bridge, session))
    owner = owner_key('signed-agent', session)
    with bridge.db() as db:
        state = bridge._load(db, owner)
    good = json.loads((Path(__file__).parents[1] / 'examples/hackathon-demo/demo.json').read_text())['good']
    jobs.items[state['job_id']].update(status='complete', report={
        'pcb': {'current': True, 'fingerprint': good['board']['artifact_fingerprint']}, 'schematic': {'current': True},
        'experience': {'board': good['board'], 'components': good['components']},
        'requirements': [{'label': 'Firmware', 'status': 'UNKNOWN', 'detail': 'Not included'}],
        'verification_ladder': [{'stage': 'Simulation', 'status': 'UNSUPPORTED'}],
    })
    token = bridge.board_workspace.issue(owner, state).split('access=')[1]
    return bridge, provider, jobs, clock, state, token


class Teacher:
    def __init__(self, bad=False):
        self.requests = []
        self.bad = bad

    def generate_structured(self, request, schema):
        self.requests.append(request)
        return TeachingAnswer(explanation='This part has the recorded role shown in your board. General explanation: connections carry power or signals.',
                              source_ids=['invented'] if self.bad else ['component', 'connections'],
                              unknowns=['Physical operation has not been measured.'],
                              next_questions=['How is it connected?'])


def test_workspace_exact_revision_expiry_and_stale_artifacts(tmp_path):
    bridge, _, jobs, clock, state, token = prepared(tmp_path)
    try:
        data = bridge.board_workspace.read(token)
        assert data['job_id'] == state['job_id'] and data['revision_id'] == state['revision_id']
        assert data['requirements'][0]['status'] == 'UNKNOWN'
        with pytest.raises(WorkspaceUnavailable):
            bridge.board_workspace.read('x' * 43)
        jobs.items[state['job_id']]['report']['pcb']['current'] = False
        with pytest.raises(WorkspaceUnavailable):
            bridge.board_workspace.read(token)
        jobs.items[state['job_id']]['report']['pcb']['current'] = True
        clock[0] += 86401
        with pytest.raises(WorkspaceUnavailable):
            bridge.board_workspace.read(token)
    finally:
        bridge.close()


def test_teaching_is_component_bound_with_history_and_no_verdict_mutation(tmp_path):
    bridge, _, jobs, _, state, token = prepared(tmp_path)
    teacher = Teacher()
    bridge.board_workspace.provider = teacher
    try:
        ref = bridge.board_workspace.read(token)['experience']['components'][0]['ref']
        before = json.dumps(jobs.items[state['job_id']], sort_keys=True)
        answer = bridge.board_workspace.teach(token, ref, 'Explain this part')
        assert answer['component'] == ref and answer['job_id'] == state['job_id']
        bridge.board_workspace.teach(token, ref, 'Tell me more')
        assert teacher.requests[-1].data['history'][0]['text'] == 'Explain this part'
        assert teacher.requests[-1].data['sources']['component']['value']['ref'] == ref
        assert json.dumps(jobs.items[state['job_id']], sort_keys=True) == before
        with pytest.raises(ValueError):
            bridge.board_workspace.teach(token, 'NOT_ON_BOARD', 'Explain')
        assert len(teacher.requests) == 2
        teacher.bad = True
        with pytest.raises(ValueError):
            bridge.board_workspace.teach(token, ref, 'Explain')
    finally:
        bridge.close()


def test_links_survive_status_and_restart_and_remain_job_bound(tmp_path):
    bridge, _, jobs, _, state, token = prepared(tmp_path)
    try:
        with bridge.db() as db:
            owner = db.execute('SELECT owner FROM workspaces').fetchone()[0]
        assert '/workspace/#access=' in bridge.result(owner)
        assert bridge.board_workspace.read(token)['job_id'] == state['job_id']
        from ohmni.integrations.fetch_ai.workspace import BoardWorkspace
        reopened = BoardWorkspace(bridge, Teacher())
        assert reopened.read(token)['job_id'] == state['job_id']
        assert reopened.download(token) == b'checked-zip'
        jobs.package_current = False
        with pytest.raises(WorkspaceUnavailable):
            reopened.download(token)
    finally:
        bridge.close()


def test_gateway_workspace_requires_capability_and_blocks_project_enumeration(tmp_path):
    async def run():
        from aiohttp import ClientSession

        from ohmni.integrations.fetch_ai.http import start_gateway
        bridge, _, _, _, _, token = prepared(tmp_path)
        bridge.board_workspace.provider = Teacher()
        runner, transport = await start_gateway(bridge, 0, 1)
        base = 'http://127.0.0.1:' + str(runner.addresses[0][1])
        headers = {'Authorization': 'Bearer ' + token}
        try:
            async with ClientSession() as client:
                for path in ['/workspace/api/board', '/workspace/api/download']:
                    async with client.get(base + path) as r:
                        assert r.status == 410
                async with client.get(base + '/workspace/') as r:
                    assert r.status == 200 and 'fetch-workspace.js' in await r.text()
                    assert r.headers['Referrer-Policy'] == 'no-referrer'
                async with client.get(base + '/workspace/api/board', headers=headers) as r:
                    data = await r.json()
                    assert r.status == 200
                    ref = data['experience']['components'][0]['ref']
                async with client.post(base + '/workspace/api/teach', headers=headers, json={'component': ref, 'question': 'Teach me'}) as r:
                    assert r.status == 200 and (await r.json())['component'] == ref
                for path in ['/api/projects', '/workspace/api/projects', '/assets/.env', '/assets/../.env', '/connect']:
                    async with client.get(base + path, headers=headers) as r:
                        assert r.status == 404
                async with client.get(base + '/workspace/api/download', headers=headers) as r:
                    assert r.status == 200 and await r.read() == b'checked-zip'
        finally:
            await runner.cleanup()
            await transport.close()
            bridge.close()
    asyncio.run(run())


def test_projection_fingerprint_mismatch_is_not_displayed(tmp_path):
    bridge, _, jobs, _, state, token = prepared(tmp_path)
    try:
        jobs.items[state['job_id']]['report']['experience']['board']['artifact_fingerprint'] = '0' * 64
        with pytest.raises(WorkspaceUnavailable, match='projection'):
            bridge.board_workspace.read(token)
    finally:
        bridge.close()
