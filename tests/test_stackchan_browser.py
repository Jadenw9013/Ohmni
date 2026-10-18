"""Real browser: the main workspace's opt-in desk-robot link (STACKCHAN-TUTOR-1, ST-T02).

A stand-in companion listens on the fixed loopback port. The page must send only a
read-only board context, carry out view-only commands through existing UI paths,
route questions through the existing teach route, and refuse everything else.
"""
import asyncio
import json
import os
import socket
import threading
from pathlib import Path

import pytest
from test_connected_browser import frontend_server
from test_fetch_workspace import Teacher, prepared

ROBOT_PORT = 8770


async def stand_in_companion(inbox: asyncio.Queue, outbox: asyncio.Queue):
    from aiohttp import WSMsgType, web

    async def handle(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await inbox.put({"type": "origin", "origin": request.headers.get("Origin")})

        async def pump():
            while True:
                await ws.send_str(json.dumps(await outbox.get()))

        sender = asyncio.ensure_future(pump())
        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    await inbox.put(json.loads(message.data))
        finally:
            sender.cancel()
        return ws

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", ROBOT_PORT).start()
    return runner


def _port_free(port):
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


def test_workspace_robot_link_context_view_commands_and_tutor(tmp_path):
    pytest.importorskip("aiohttp")
    playwright = pytest.importorskip("playwright.sync_api")
    if not _port_free(ROBOT_PORT):
        pytest.skip("a desk-robot companion is already using the loopback port")
    from ohmni.integrations.fetch_ai.http import start_gateway

    bridge, _, jobs, _, state, _ = prepared(tmp_path)
    jobs.output_root = tmp_path
    jobs.set_diagnostic = lambda _callback: None
    report = jobs.items[state["job_id"]]["report"]
    good = json.loads((Path(__file__).parents[1] / "examples/hackathon-demo/demo.json").read_text())["good"]
    first_ref = good["components"][0]["ref"]
    good.update(headline="Saved Fetch board", subhead="Robot link browser fixture", stages=[], grouping=[],
                repair={"happened": False, "headline": "No repair in this UI fixture"},
                check_sections=[], confidence={"checked": [], "not_verified": []}, bring_up=[],
                tour={"narration_source": "deterministic_projection_not_a_language_model", "steps": [
                    {"step_id": "overview", "title": "What you built", "narration": "A saved board.", "focus": "board",
                     "system": None, "flow_id": None, "component_refs": [first_ref], "net_names": [], "facts": []}]},
                schematic={"artifact_fingerprint": "a" * 64, "connection_method": "global_labels", "net_names": [], "symbols": []})
    report.update(experience=good, release={"current": True, "status": "READY_FOR_MANUFACTURING_REVIEW", "files": []}, economics={})
    bridge.board_workspace.provider = Teacher()

    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    inbox, outbox = asyncio.Queue(), asyncio.Queue()
    run = lambda coro, t=10: asyncio.run_coroutine_threadsafe(coro, loop).result(t)
    robot = run(stand_in_companion(inbox, outbox))
    runner, client = run(start_gateway(bridge, 0, 1))
    front, front_client = run(frontend_server(f"http://127.0.0.1:{runner.addresses[0][1]}"))
    base = f"http://127.0.0.1:{front.addresses[0][1]}"
    bridge.connected.main_url = base
    with bridge.db() as db:
        owner = db.execute("SELECT owner FROM sessions").fetchone()[0]
    claim = bridge.connected.issue(owner, state).split("connect=")[1]

    def receive(kind, timeout=20):
        async def wait():
            while True:
                message = await inbox.get()
                if message.get("type") == kind:
                    return message
        return run(asyncio.wait_for(wait(), timeout), timeout + 5)

    def command(message):
        run(outbox.put(message))
        while True:
            reply = receive("result")
            if reply.get("id") == message["id"]:
                return reply

    try:
        with playwright.sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                if os.environ.get("OHMNI_REQUIRE_BROWSER") == "1":
                    raise
                pytest.skip("Chromium is unavailable")
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.add_init_script("window.OHMNI_CONNECTED_LOCAL=true")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/#connect=" + claim)
            page.locator("#review").wait_for(state="visible", timeout=20000)

            button = page.locator("#robot-link")
            assert button.inner_text() == "Desk robot: off"
            assert inbox.empty(), "nothing connects before the user opts in"
            button.click()
            assert receive("origin")["origin"] == base
            context = receive("context")
            page.wait_for_function("document.querySelector('#robot-link').textContent === 'Desk robot: connected'")
            assert context["job_id"] == state["job_id"]
            assert context["project_id"] == state["project_id"]
            assert {c["ref"] for c in context["components"]} == {c["ref"] for c in good["components"]}
            assert context["tour"][0]["component_refs"] == [first_ref]
            serialized = json.dumps(context).lower()
            for secret in ("access", "connect=", "token", "http://", "https://", claim.lower()):
                assert secret not in serialized, f"no tokens or links leave the page ({secret})"

            assert command({"type": "command", "id": 1, "name": "focus", "args": {"ref": first_ref}})["ok"]
            assert first_ref in page.locator("#selection .part-id").inner_text()
            assert command({"type": "command", "id": 2, "name": "trace", "args": {"ref": first_ref}})["ok"]
            assert command({"type": "command", "id": 3, "name": "camera", "args": {"preset": "back"}})["ok"]
            assert command({"type": "command", "id": 4, "name": "tour", "args": {"index": 0}})["data"] == {"title": "What you built"}
            assert command({"type": "command", "id": 50, "name": "isolate", "args": {"ref": first_ref}})["ok"]
            page.locator("#robot-show-all").wait_for(state="visible", timeout=5000)
            assert command({"type": "command", "id": 5, "name": "isolate", "args": {"ref": None}})["ok"]
            page.locator("#robot-show-all").wait_for(state="hidden", timeout=5000)

            answer = command({"type": "command", "id": 6, "name": "ask", "args": {"ref": first_ref, "question": "What does this part do?"}})
            assert answer["ok"], answer
            assert "recorded role" in answer["data"]["explanation"]
            assert answer["data"]["unknowns"] == ["Physical operation has not been measured."]
            page.locator("#component-tutor .assistant-reply").wait_for()
            assert "What does this part do?" in page.locator("#component-tutor").inner_text(), "the question is saved in the page tutor"

            for refused in ({"type": "command", "id": 7, "name": "run", "args": {}},
                            {"type": "command", "id": 8, "name": "focus", "args": {"ref": "NOPE99"}},
                            {"type": "command", "id": 9, "name": "camera", "args": {"preset": "side"}}):
                assert command(refused)["ok"] is False
            assert jobs.starts == 1, "no command started a build"

            page.locator("#systems [data-system-select]").first.click()
            page.locator("#systems [data-ref]").first.click()
            while (selected := receive("selected"))["by"] != "user":
                assert selected["by"] == "robot"  # earlier robot-driven selections, never unlabeled
            assert selected["ref"]
            button.click()
            page.wait_for_function("document.querySelector('#robot-link').textContent === 'Desk robot: off'")
            assert not errors, errors
            browser.close()
    finally:
        async def close():
            await front.cleanup()
            await front_client.close()
            await runner.cleanup()
            await client.close()
            await robot.cleanup()
        run(close(), 15)
