"""Real browser selection and teaching over the real private HTTP gateway."""
import asyncio
import os
import threading

import pytest
from test_fetch_workspace import Teacher, prepared


def test_generated_board_selection_teaching_and_expired_link_in_browser(tmp_path):
    pytest.importorskip('aiohttp')
    playwright = pytest.importorskip('playwright.sync_api')
    from ohmni.integrations.fetch_ai.http import start_gateway

    bridge, _, _, _, _, token = prepared(tmp_path)
    teacher = Teacher()
    bridge.board_workspace.provider = teacher
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    runner, client = asyncio.run_coroutine_threadsafe(start_gateway(bridge, 0, 1), loop).result(10)
    base = f'http://127.0.0.1:{runner.addresses[0][1]}'
    try:
        with playwright.sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as exc:
                if os.environ.get('OHMNI_REQUIRE_BROWSER') == '1':
                    raise
                pytest.skip(f'Browser unavailable: {type(exc).__name__}')
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/workspace/#access=' + token)
            page.locator('#parts button').first.wait_for()
            page.locator('#parts button').first.click()
            ref = page.locator('#parts button').first.get_attribute('data-ref')
            page.locator('[data-question]').first.click()
            page.locator('#send').click()
            page.locator('.message.assistant').wait_for()
            assert teacher.requests[-1].data['component'] == ref
            assert 'Interactive 3D' in page.locator('.visual-mode-note').inner_text()
            page.locator('#parts button').nth(1).click()
            assert page.locator('.message').count() == 0
            page.locator('#parts button').first.click()
            assert page.locator('.message.assistant').count() == 1
            page.reload()
            page.locator('#parts button').first.click()
            assert page.locator('.message.assistant').count() == 1
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors
            page.goto(base + '/workspace/#access=' + 'z' * 43)
            page.reload()
            page.locator('#error').wait_for(state='visible')
            assert 'expired' in page.locator('#error').inner_text()
            browser.close()
    finally:
        async def close():
            await runner.cleanup()
            await client.close()
        asyncio.run_coroutine_threadsafe(close(), loop).result(10)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(10)
        bridge.close()
