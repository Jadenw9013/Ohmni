"""Main UI security and durable project/chat semantics across Fetch and HTTP."""
import asyncio
from uuid import uuid4

import pytest
from test_fetch_bridge import confirm_code, owner_key, send, setup

from ohmni.application.iteration import IterationResponse
from ohmni.integrations.fetch_ai.connected import AccessDenied, ConnectedWorkspace


def project(bridge):
    session = str(uuid4())
    send(bridge, session, 'A USB ESP32 board with one button and LED.')
    send(bridge, session, 'CONFIRM ' + confirm_code(bridge, session))
    owner = owner_key('signed-agent', session)
    with bridge.db() as db:
        state = bridge._load(db, owner)
    return owner, state, session


def test_claim_is_one_use_owner_bound_and_survives_service_reopen(tmp_path):
    bridge, _, _, clock = setup(tmp_path)
    try:
        owner, state, _ = project(bridge)
        claim = bridge.connected.issue(owner, state).split('connect=')[1]
        token, pid = bridge.connected.connect(claim=claim)
        key = bridge.connected.session(token)
        assert pid == state['project_id']
        bridge.connected.owns(key, pid)
        assert bridge.connected.connect(token, claim)[1] == pid  # lost-response retry
        with pytest.raises(AccessDenied):
            bridge.connected.connect(claim=claim)
        reopened = ConnectedWorkspace(bridge)
        reopened.owns(reopened.session(token), pid)
        assert reopened.history(pid, state['revision_id'], 'board')['messages']
        clock[0] += 1801
        with pytest.raises(AccessDenied):
            reopened.connect(token, claim)
        # Existing workspace session does not expire with the link.
        reopened.owns(reopened.session(token), pid)
    finally:
        bridge.close()


def test_main_ui_http_projects_edits_history_and_cross_owner_boundaries(tmp_path):
    pytest.importorskip('aiohttp')
    async def run():
        from aiohttp import ClientSession, CookieJar

        from ohmni.integrations.fetch_ai.http import start_gateway
        bridge, _provider, jobs, _ = setup(tmp_path)
        jobs.output_root = tmp_path
        jobs.set_diagnostic = lambda _callback: None
        owner, state, chat = project(bridge)
        other_owner, other_state, _ = project(bridge)
        claim = bridge.connected.issue(owner, state).split('connect=')[1]
        other_claim = bridge.connected.issue(other_owner, other_state).split('connect=')[1]
        runner, transport = await start_gateway(bridge, 0, 1)
        base = 'http://127.0.0.1:' + str(runner.addresses[0][1]) + '/connected'
        headers = {'X-Ohmni-Client': 'main-ui'}
        try:
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as a, ClientSession(cookie_jar=CookieJar(unsafe=True)) as b:
                async with a.post(base + '/session', json={'claim': claim}, headers=headers) as r:
                    assert r.status == 200
                    assert 'HttpOnly' in r.headers['Set-Cookie']
                async with b.post(base + '/session', json={'claim': other_claim}, headers=headers) as r:
                    assert r.status == 200
                async with b.post(base + '/session', json={'claim': claim}, headers=headers) as r:
                    assert r.status == 403
                async with a.get(base + '/api/health') as r:
                    health = await r.json()
                    assert r.status == 200
                identity = {k: health[k] for k in ('api_version','server_instance_id','ui_version')}
                poll = {'X-Ohmni-API-Version': str(identity['api_version']), 'X-Ohmni-Server-Instance': identity['server_instance_id'], 'X-Ohmni-UI-Version': identity['ui_version']}
                path = '/api/projects/' + state['project_id']
                for client, allowed in [(a, True), (b, False)]:
                    async with client.get(base + path, headers=poll) as r:
                        assert r.status == (200 if allowed else 403)
                    async with client.get(base + '/api/jobs/' + state['job_id'], headers=poll) as r:
                        assert r.status == (200 if allowed else 403)
                async with a.get(base + '/api/projects', headers=poll) as r:
                    assert [p['project_id'] for p in (await r.json())['projects']] == [state['project_id']]
                brief = bridge.projects.revision(state['project_id'], state['revision_id'])['brief']
                brief = {**brief, 'project_name': 'Edited in main Ohmni'}
                async with a.post(base + path + '/revisions', json={**identity, 'brief':brief, 'base_revision_id':state['revision_id']}) as r:
                    assert r.status == 403  # CSRF guard
                async with a.post(base + path + '/revisions', json={**identity, 'brief':brief, 'base_revision_id':state['revision_id']}, headers={**headers,'Origin':'https://evil.example'}) as r:
                    assert r.status == 403
                async with a.post(base + path + '/revisions', json={**identity, 'brief':brief, 'base_revision_id':state['revision_id']}, headers=headers) as r:
                    assert r.status == 201
                    rev = (await r.json())['project']['revisions'][-1]
                async with a.post(base + path + '/revisions', json={**identity,'brief':brief,'base_revision_id':state['revision_id']},headers=headers) as r:
                    assert r.status == 409  # stale tab cannot replace newer choices
                # Fetch must see the revision saved in UI, not silently edit old work.
                send(bridge, chat, 'STATUS')
                with bridge.db() as db:
                    synced = bridge._load(db, owner)
                assert synced['revision_id'] == rev['revision_id'] and synced.get('job_id') is None
                with pytest.raises(AccessDenied):
                    bridge.connected.authorize(bridge.connected.session(next(c.value for c in b.cookie_jar if c.key == 'ohmni_workspace')), 'POST', path+'/revisions', {})
                # A real assistant service selects records; server archives its turn.
                class AnswerProvider:
                    def generate_structured(self, request, schema):
                        return IterationResponse(kind='answer', fact_ids=('brief.project_name',))
                bridge.assistant.provider = AnswerProvider()
                endpoint = path + '/revisions/' + rev['revision_id']
                async with a.post(base+endpoint+'/assistant', json={**identity,'message':'What is this board called?','parent_id':None},headers=headers) as r:
                    assert r.status == 200, await r.text()
                async with a.get(base+endpoint+'/history',headers=poll) as r:
                    history=await r.json()
                    assert history['messages'][-1]['message']=='What is this board called?'
                bridge.assistant._turns.clear()
                assert bridge.connected.history(state['project_id'],rev['revision_id'],'board')['messages'][-1]['turn']['facts'][0]['value']=='Edited in main Ohmni'
                async with a.get(base+'/api/projects/'+other_state['project_id']+'/revisions/'+other_state['revision_id']+'/history',headers=poll) as r:
                    assert r.status == 403
                async with a.post(base+'/api/plans/0000000000000000/confirm',json=identity,headers=headers) as r:
                    assert r.status == 403
        finally:
            await runner.cleanup()
            await transport.close()
            bridge.close()
    asyncio.run(run())


def test_viewer_history_migrates_once_and_read_token_cannot_claim_edit_access(tmp_path):
    from test_fetch_workspace import Teacher, prepared
    bridge, _, _, _, state, viewer_token = prepared(tmp_path)
    try:
        bridge.board_workspace.provider = Teacher()
        ref = bridge.board_workspace.read(viewer_token)['experience']['components'][0]['ref']
        bridge.board_workspace.teach(viewer_token, ref, 'My earlier viewer question')
        with pytest.raises(AccessDenied):
            bridge.connected.connect(claim=viewer_token)
        with bridge.db() as db:
            owner = db.execute('SELECT owner FROM sessions').fetchone()[0]
        claim = bridge.connected.issue(owner, state).split('connect=')[1]
        token, project = bridge.connected.connect(claim=claim)
        bridge.connected.connect(token, claim)
        rows = bridge.connected.history(project, state['revision_id'], 'component:' + ref)['messages']
        assert len(rows) == 1 and rows[0]['message'] == 'My earlier viewer question'
        # Paging preserves older conversations rather than silently truncating them.
        for n in range(60):
            bridge.connected.record(project, state['revision_id'], 'board', {'message': str(n), 'reply': 'saved'})
        latest = bridge.connected.history(project, state['revision_id'], 'board')
        earlier = bridge.connected.history(project, state['revision_id'], 'board', latest['before'])
        assert len(latest['messages']) == 50 and len(earlier['messages']) >= 10
        assert not {x['id'] for x in latest['messages']} & {x['id'] for x in earlier['messages']}
    finally:
        bridge.close()
