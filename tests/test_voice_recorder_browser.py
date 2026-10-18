"""Real generated recorder through the main connected UI and Fetch orchestration.

Provider outputs are deterministic test doubles; rendering, HTTP, persistence,
revision validation, PCB generation and simulation are production code.
"""
import asyncio
import os
import threading
from uuid import uuid4

import pytest
from test_connected_browser import frontend_server
from test_fetch_bridge import confirm_code, owner_key, send, setup

from ohmni.application.conversation import BoardPlan
from ohmni.application.projects import ProjectPipeline
from ohmni.integrations.fetch_ai.bridge import ChatBridge
from ohmni.integrations.fetch_ai.workspace import TeachingAnswer
from ohmni.synthesis.a4 import recorder_brief


@pytest.mark.kicad
@pytest.mark.slow_integration
def test_recorder_fetch_main_ui_teaching_simulation_editing_and_restart(tmp_path):
    pytest.importorskip('aiohttp')
    playwright=pytest.importorskip('playwright.sync_api')
    from ohmni.adapters.tools import find_kicad_cli
    from ohmni.integrations.fetch_ai.http import start_gateway
    if find_kicad_cli() is None:pytest.skip('KiCad unavailable')
    bridge,provider,jobs,clock=setup(tmp_path)
    bridge.budget.monotonic=lambda:clock[0]
    jobs.output_root=tmp_path;jobs.set_diagnostic=lambda _callback:None
    provider.generate_structured=lambda request,schema:BoardPlan(brief=recorder_brief())
    session=str(uuid4())
    proposal=send(bridge,session,'Build a mono voice recorder with microphone and microSD')
    assert '32000' in proposal and jobs.starts==0
    assert 'queued' in send(bridge,session,'CONFIRM '+confirm_code(bridge,session))
    owner=owner_key('signed-agent',session)
    with bridge.db() as db:state=bridge._load(db,owner)
    report=ProjectPipeline().run(tmp_path/'real-recorder',recorder_brief()).model_dump(mode='json')
    jobs.items[state['job_id']].update(status='complete',report=report)
    assert report['pcb']['violations']==report['pcb']['unrouted']==0
    teaching=[]
    class Teacher:
        def generate_structured(self,request,schema):
            teaching.append(request)
            return TeachingAnswer(explanation='This microphone supplies digital audio to the ESP32. The saved firmware uses GPIO16 for its data input. Physical audio testing is pending.',
                source_ids=['component','recorder'],unknowns=['Acoustic quality is unmeasured.'],next_questions=['How is sound saved?'])
    class Assistant:
        def generate_structured(self,request,schema):
            brief={**request.data['context']['brief']}
            if '48' in request.data['messages'][-1]:brief['recorder_sample_rate_hz']=48000
            else:brief['recorder_max_seconds']=60
            return schema.model_validate({'kind':'change','proposal':{'brief':brief,'stated':[],'questions':[]}})
    bridge.board_workspace.provider=Teacher();bridge.assistant.provider=Assistant()
    loop=asyncio.new_event_loop();thread=threading.Thread(target=loop.run_forever,daemon=True);thread.start()
    runner,client=asyncio.run_coroutine_threadsafe(start_gateway(bridge,0,1),loop).result(10)
    front,transport=asyncio.run_coroutine_threadsafe(frontend_server(f'http://127.0.0.1:{runner.addresses[0][1]}'),loop).result(10)
    base=f'http://127.0.0.1:{front.addresses[0][1]}';bridge.connected.main_url=base
    claim=bridge.connected.issue(owner,state).split('connect=')[1]
    try:
        with playwright.sync_playwright() as p:
            try:browser=p.chromium.launch()
            except Exception:
                if os.environ.get('OHMNI_REQUIRE_BROWSER')=='1':raise
                pytest.skip('Chromium unavailable')
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.add_init_script('window.OHMNI_CONNECTED_LOCAL=true')
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/#connect='+claim)
            page.locator('#review').wait_for(state='visible',timeout=20000)
            page.locator('#tab-checks').click()
            panel=page.locator('#recorder-panel')
            assert 'Synthetic recording finalized' in panel.inner_text()
            panel.locator('select').select_option('card_removed')
            assert 'Modeled error: card removed' in panel.inner_text()
            page.locator('#tab-board').click()
            # Select the actual microphone in the generated board's systems list.
            for button in page.locator('#systems [data-system-select]').all():
                button.click()
                if page.locator('#systems [data-ref="MIC1"]').is_visible():break
            page.locator('#systems [data-ref="MIC1"]').click()
            assert 'ADAFRUIT_3421' in page.locator('#selection').inner_text()
            tutor=page.locator('#component-tutor')
            tutor.locator('textarea').fill('How does this microphone record my voice?')
            tutor.get_by_role('button',name='Ask Ohmni',exact=True).click()
            tutor.locator('.assistant-reply').wait_for()
            assert teaching[-1].data['sources']['recorder']['value']['gpio']['din']==16
            assert teaching[-1].data['sources']['brief']['value']['recorder_sample_rate_hz']==32000
            page.screenshot(path=str(tmp_path/'recorder-main-desktop.png'),full_page=True)
            page.reload();page.locator('[data-project-open]').first.click()
            page.get_by_role('button',name="Open this revision's run",exact=True).click()
            page.locator('#review').wait_for(state='visible')
            for button in page.locator('#systems [data-system-select]').all():
                button.click()
                if page.locator('#systems [data-ref="MIC1"]').is_visible():break
            page.locator('#systems [data-ref="MIC1"]').click()
            tutor.locator('.assistant-reply').wait_for()
            assert 'How does this microphone record my voice?' in tutor.inner_text()
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(tmp_path/'recorder-main-mobile.png'),full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            chat=page.locator('#result-assistant')
            chat.locator('textarea').fill('Change recording to 48 kHz')
            chat.locator('button[type=submit]').click()
            chat.get_by_role('button',name='Save changes as a new revision',exact=True).click()
            page.locator('#agree').wait_for(state='visible')
            latest=bridge.projects.get(state['project_id'])['revisions'][-1]
            assert latest['brief']['recorder_sample_rate_hz']==48000 and latest['job_id'] is None
            assert jobs.starts==1
            assert '48000 Hz' in send(bridge,session,'SIMULATE normal')
            assert 'buffer_overflow' in send(bridge,session,'SIMULATE slow card')
            # Fetch edits the same revision and requires explicit confirmation.
            clock[0]+=61
            assert 'Changes proposed' in send(bridge,session,'Limit recording to 60 seconds')
            assert len(bridge.projects.get(state['project_id'])['revisions'])==2
            send(bridge,session,'CONFIRM '+confirm_code(bridge,session))
            revisions=bridge.projects.get(state['project_id'])['revisions']
            assert len(revisions)==3 and jobs.starts==2
            assert revisions[-1]['brief']['recorder_max_seconds']==60
            assert revisions[-1]['brief']['recorder_sample_rate_hz']==48000
            assert revisions[0]['job_id']==state['job_id']
            assert not errors
            browser.close()
    finally:
        async def cleanup():
            await front.cleanup();await transport.close();await runner.cleanup();await client.close()
        asyncio.run_coroutine_threadsafe(cleanup(),loop).result(10);loop.call_soon_threadsafe(loop.stop);thread.join(5)
        bridge.close()
    reopened=ChatBridge(tmp_path,provider,'https://agent.example',jobs=jobs,clock=lambda:clock[0])
    try:
        assert len(reopened.projects.get(state['project_id'])['revisions'])==3
        assert '48000 Hz' in send(reopened,session,'SIMULATE normal')
        history=reopened.connected.history(state['project_id'],state['revision_id'],'component:MIC1')['messages']
        assert history[-1]['message']=='How does this microphone record my voice?'
    finally:reopened.close()
