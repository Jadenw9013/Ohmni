"""Main page (not the old viewer): claim, board, saved chat, edits and reload."""
import asyncio
import json
import os
import threading
from pathlib import Path

import pytest
from test_fetch_workspace import Teacher, prepared


async def frontend_server(gateway):
    """Local equivalent of Vercel's static hosting plus /connected rewrite."""
    from aiohttp import ClientSession, web

    from scripts.demo_server import STATIC_ASSETS, WEB_ROOT
    client = ClientSession()
    async def handle(request):
        if request.path.startswith('/connected/'):
            async with client.request(request.method,gateway+request.rel_url.path_qs,
                                      data=await request.read(),headers={k:v for k,v in request.headers.items() if k.lower() not in {'host','content-length'}}) as response:
                return web.Response(status=response.status,body=await response.read(),headers={k:v for k,v in response.headers.items() if k.lower() not in {'transfer-encoding','content-length','content-encoding'}})
        name=request.path.lstrip('/') or 'index.html'
        if name not in STATIC_ASSETS:
            raise web.HTTPNotFound()
        return web.FileResponse(WEB_ROOT/name)
    app=web.Application();app.router.add_route('*','/{path:.*}',handle)
    runner=web.AppRunner(app);await runner.setup();await web.TCPSite(runner,'127.0.0.1',0).start()
    return runner,client


def test_main_ui_claim_saved_board_component_chat_and_edit(tmp_path):
    pytest.importorskip('aiohttp')
    playwright=pytest.importorskip('playwright.sync_api')
    from ohmni.integrations.fetch_ai.http import start_gateway
    bridge,_,jobs,_,state,_=prepared(tmp_path)
    jobs.output_root=tmp_path
    jobs.set_diagnostic=lambda _callback:None
    report=jobs.items[state['job_id']]['report']
    good=json.loads((Path(__file__).parents[1]/'examples/hackathon-demo/demo.json').read_text())['good']
    # Saved visual fixture supplies geometry; minimal non-engineering sections
    # exercise the full main-page transport without running native tools in CI.
    good.update(headline='Saved Fetch board',subhead='Browser regression fixture',stages=[],grouping=[],
                repair={'happened':False,'headline':'No repair in this UI fixture'},
                check_sections=[],confidence={'checked':[],'not_verified':[]},
                bring_up=[],tour={'steps':[],'narration_source':'test fixture'},
                schematic={'artifact_fingerprint':'a'*64,'connection_method':'global_labels','net_names':[],'symbols':[]})
    report.update(experience=good,release={'current':True,'status':'READY_FOR_MANUFACTURING_REVIEW','files':[]},economics={})
    bridge.board_workspace.provider=Teacher()
    class AssistantProvider:
        def generate_structured(self, request, schema):
            if 'rename' in request.data['messages'][-1].lower():
                return schema.model_validate({'kind':'change','proposal':{'brief':{**request.data['context']['brief'],'project_name':'My edited Fetch board'},'stated':[],'questions':[]}})
            return schema.model_validate({'kind':'answer','fact_ids':['brief.project_name']})
    bridge.assistant.provider=AssistantProvider()
    loop=asyncio.new_event_loop();thread=threading.Thread(target=loop.run_forever,daemon=True);thread.start()
    runner,client=asyncio.run_coroutine_threadsafe(start_gateway(bridge,0,1),loop).result(10)
    front,front_client=asyncio.run_coroutine_threadsafe(frontend_server(f'http://127.0.0.1:{runner.addresses[0][1]}'),loop).result(10)
    base=f'http://127.0.0.1:{front.addresses[0][1]}'
    bridge.connected.main_url=base
    with bridge.db() as db:owner=db.execute('SELECT owner FROM sessions').fetchone()[0]
    claim=bridge.connected.issue(owner,state).split('connect=')[1]
    try:
        with playwright.sync_playwright() as p:
            try:browser=p.chromium.launch()
            except Exception:
                if os.environ.get('OHMNI_REQUIRE_BROWSER')=='1':raise
                pytest.skip('Chromium is unavailable')
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.add_init_script('window.OHMNI_CONNECTED_LOCAL=true')
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base+'/#connect='+claim)
            try: page.locator('#review').wait_for(state='visible',timeout=20000)
            except Exception:
                print('PAGE ERRORS', errors, page.locator('body').inner_text()[-12000:])
                raise
            assert 'connect=' not in page.url
            assert page.locator('[data-project-open]').count()==1
            page.locator('#systems [data-system-select]').first.click()
            page.locator('#systems [data-ref]').first.click()
            tutor=page.locator('#component-tutor')
            tutor.locator('textarea').fill('Explain this part on my board')
            tutor.get_by_role('button',name='Ask Ohmni',exact=True).click()
            tutor.locator('.assistant-reply').wait_for()
            selected=page.locator('#selection .part-id').inner_text()
            chat=page.locator('#result-assistant')
            chat.locator('textarea').fill('What is this board called?')
            chat.locator('button[type=submit]').click()
            chat.get_by_text('What is this board called?',exact=True).first.wait_for()

            page.reload()
            page.locator('[data-project-open]').first.click()
            page.get_by_role('button',name="Open this revision's run",exact=True).click()
            page.locator('#review').wait_for(state='visible')
            page.locator('#systems [data-system-select]').first.click()
            page.locator('#systems [data-ref]').first.click()
            assert page.locator('#selection .part-id').inner_text()==selected
            tutor.locator('.assistant-reply').wait_for()
            assert 'Explain this part on my board' in tutor.inner_text()
            assert 'What is this board called?' in chat.inner_text()
            # New connection link to same project retains its durable chat.
            new_claim=bridge.connected.issue(owner,state).split('connect=')[1]
            page.goto(base+'/#connect='+new_claim)
            page.locator('#review').wait_for(state='visible')
            page.locator('#systems [data-system-select]').first.click()
            page.locator('#systems [data-ref]').first.click()
            tutor.locator('.assistant-reply').wait_for()
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(tmp_path/'main-connected-mobile.png'),full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            chat.locator('textarea').fill('Rename my project to My edited Fetch board')
            chat.locator('button[type=submit]').click()
            chat.get_by_role('button',name='Save changes as a new revision',exact=True).click()
            page.locator('#agree').wait_for(state='visible')
            assert len(bridge.projects.get(state['project_id'])['revisions'])==2
            latest=bridge.projects.get(state['project_id'])['revisions'][-1]
            assert latest['job_id'] is None
            assert latest['brief']['project_name']=='My edited Fetch board'
            # Explicit generation acts on the new revision; original job stays intact.
            page.get_by_role('button',name='Generate my board',exact=True).click()
            page.locator('#design').wait_for(state='visible')
            page.wait_for_function("document.querySelector('#design').dataset.buildState === 'running'")
            assert jobs.starts==2
            assert bridge.projects.get(state['project_id'])['revisions'][0]['job_id']==state['job_id']
            # New projects use the same connected gateway and merged planning UI.
            page.locator('#sidebar-new-project').click()
            page.locator('#free-text-request').fill('Build a USB-powered ESP32 sensor board')
            page.locator('#start-free-text').click()
            page.locator('#conversation-confirm:not([disabled])').wait_for(timeout=20000)
            assert page.locator('#conversation-plan').is_visible()
            assert not errors, errors
            browser.close()
    finally:
        async def close():
            await front.cleanup();await front_client.close();await runner.cleanup();await client.close()
        asyncio.run_coroutine_threadsafe(close(),loop).result(15)
        loop.call_soon_threadsafe(loop.stop);thread.join(10);bridge.close()
