"""Local browser regression: real generation, controlled progress, offline assistant."""
import json
import threading

import pytest


@pytest.mark.integration
def test_build_motion_and_prefixed_board_chat(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    from ohmni.adapters.tools import find_kicad_cli
    from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore
    from scripts.verify_hackathon_demo import kicad_version

    executable = find_kicad_cli()
    if not executable or kicad_version(executable) != "10.0.5":
        pytest.skip("requires KiCad 10.0.5")

    class Provider:
        def generate_structured(self, request, schema):
            assert request.request_type == "project_iteration"
            if "80" in request.data["messages"][-1]:
                brief = {**request.data["context"]["brief"], "board_width_mm": 80}
                return schema.model_validate({"kind": "change", "proposal": {
                    "brief": brief, "stated": [], "questions": []}})
            return schema.model_validate({"kind": "answer", "fact_ids": ["report.bom.parts"]})

    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler,
                           store=JobStore(tmp_path / "workspace", provider=Provider()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    mode = {"value": "running"}
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                origin = f"http://127.0.0.1:{server.server_address[1]}"
                page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())

                def progress(route):
                    response = route.fetch()
                    body = response.json()
                    if mode["value"]:
                        body.update(status=mode["value"], report=None, error="Demo pipeline failed" if mode["value"] == "failed" else None,
                            error_code="eda_tool_failed" if mode["value"] == "failed" else None,
                            progress=[{"stage": "routing", "label": "Drawing the copper connections",
                                "status": "RUNNING", "detail": "Finding paths between your components.", "percent": 40}])
                    route.fulfill(response=response, json=body)

                page.route("**/api/jobs/*", progress)
                page.goto(origin + "/#workspace")
                page.locator('[data-starter-family="a2_usb_gpio_controller"]').first.click()
                page.get_by_role("button", name="Generate my board", exact=True).click()
                page.wait_for_function("document.querySelector('#design').dataset.buildState === 'running'")
                assert page.locator("#progress-track").get_attribute("aria-valuenow") == "40"
                assert "Server responding" in page.locator("#build-connection-status").inner_text()
                signal = page.locator(".signal").first
                assert signal.evaluate("e => getComputedStyle(e).animationPlayState") == "running"
                page.locator("#build-motion").click()
                assert signal.evaluate("e => getComputedStyle(e).animationPlayState") == "paused"
                page.locator("#build-motion").click()
                page.screenshot(path=str(tmp_path / "build-desktop.png"), full_page=True)
                page.emulate_media(reduced_motion="reduce")
                assert signal.evaluate("e => getComputedStyle(e).animationName") == "none"
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(tmp_path / "build-mobile.png"), full_page=True)
                page.emulate_media(reduced_motion="no-preference")
                mode["value"] = "failed"
                page.locator("#run-error").wait_for(state="visible")
                assert signal.evaluate("e => getComputedStyle(e).animationPlayState") == "paused"
                assert page.locator("#error-back").is_visible()
                assert "build stopped" in page.locator("#build-connection-status").inner_text()
                # Resume polling the actual completed run by reopening its saved revision.
                mode["value"] = None
                page.set_viewport_size({"width": 1440, "height": 1000})
                page.reload()
                page.locator("[data-project-open]").first.click()
                page.get_by_role("button", name="Open this revision's run", exact=True).click()
                page.locator("#review").wait_for(state="visible", timeout=240000)
                page.set_viewport_size({"width": 390, "height": 844})
                chat = page.locator("#result-assistant")
                field = chat.locator("textarea")
                field.fill("What parts are used?")
                chat.get_by_role("button", name="Send", exact=False).click()
                chat.get_by_text("Parts used in this board", exact=True).wait_for()
                assert "ESP32" in chat.inner_text()
                assert field.input_value() == ""
                assert not chat.locator('[id$="assistant-apply"]').is_visible()
                width = field.bounding_box()["width"]
                assert width > chat.bounding_box()["width"] * .75
                page.screenshot(path=str(tmp_path / "chat-mobile.png"), full_page=True)
                field.fill("Make the board 80 mm wide")
                chat.get_by_role("button", name="Send", exact=False).click()
                chat.get_by_text("After: 80", exact=True).wait_for()
                assert chat.locator('[id$="assistant-apply"]').is_visible()
                assert chat.locator('[id$="assistant-apply"]').evaluate("e => e.closest('.assistant-thread') === null")
                pid = page.request.get(origin + "/api/projects").json()["projects"][0]["project_id"]
                saved = page.request.get(origin + "/api/projects/" + pid).json()["project"]
                assert len(saved["revisions"]) == 1 and saved["revisions"][0]["brief"]["board_width_mm"] == 100
                page.set_viewport_size({"width": 1440, "height": 1000})
                chat.evaluate("e => window.scrollTo(0, window.scrollY + e.getBoundingClientRect().top - 160)")
                page.wait_for_function("document.querySelector('#result-assistant').getBoundingClientRect().top >= 100")
                chat.screenshot(path=str(tmp_path / "chat-desktop.png"))
                assert not errors
                (tmp_path / "browser-evidence.json").write_text(json.dumps({
                    "progress_percent": 40, "motion_pause": True, "reduced_motion": True,
                    "error_stops_motion": True, "mobile_no_overflow": True,
                    "assistant_answer": True, "review_before_apply": True,
                    "provider": "fixture-no-network", "page_errors": errors}))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.integration
def test_planning_feedback_and_clarification_hint(tmp_path):
    from test_conversation import output
    from test_conversation_api import server_at

    playwright = pytest.importorskip("playwright.sync_api")
    release = threading.Event()
    with server_at(tmp_path / "workspace") as (server, origin):
        def proposal(request, schema):
            assert release.wait(15)
            return output(questions=["USB power only is supported. Is that acceptable?"])
        server.planner.provider.generate_structured = proposal
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1100, "height": 900})
                page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())
                page.goto(origin + "/#workspace")
                page.locator("#free-text-request").fill("A USB temperature board with one light")
                page.locator("#start-free-text").click()
                page.locator("#conversation-activity").wait_for(state="visible")
                page.wait_for_function("document.querySelector('#conversation-elapsed').textContent !== '0s elapsed'")
                assert "Preparing" in page.locator("#conversation-activity-label").inner_text()
                page.screenshot(path=str(tmp_path / "planning.png"), full_page=True)
                release.set()
                page.locator("#conversation-confirm-hint").wait_for(state="visible")
                assert page.locator("#conversation-confirm").is_disabled()
                assert "Generation is paused: answer" in page.locator("#conversation-confirm-hint").inner_text()
                assert not page.locator("#conversation-activity").is_visible()
                page.locator("#conversation-confirm-hint").scroll_into_view_if_needed()
                page.screenshot(path=str(tmp_path / "clarification.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            finally:
                release.set()
                browser.close()
