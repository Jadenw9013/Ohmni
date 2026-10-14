#!/usr/bin/env python3
"""Network-disabled browser acceptance check for the saved demonstration.

The default offline host uses scripts/serve_offline_demo.py. --host-mode site
uses the real local app server with an isolated workspace and no model provider;
--host-mode static serves apps/web directly, as the frontend host does. Every
host binds an ephemeral 127.0.0.1 port, and browser requests elsewhere are blocked.

Checks recorded boards, download hashes, restore and delayed response behavior,
missing-file recovery, mobile layout, and (for site/static) new-tab navigation
without losing an unsaved workspace draft. Nothing requests a generated board.

Requires the optional `playwright` Python package and a Chromium build
(PLAYWRIGHT_BROWSERS_PATH or --chromium). Exit 0 only if every step passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.serve_offline_demo import CAPTURE, make_server


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def _server(host_mode: str, scratch: Path):
    if host_mode == "offline":
        return make_server(0)
    if host_mode == "static":
        return ThreadingHTTPServer(("127.0.0.1", 0), partial(
            QuietStaticHandler, directory=str(ROOT / "apps" / "web")))
    from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore
    return DemoHTTPServer(("127.0.0.1", 0), DemoHandler,
                          store=JobStore(scratch / "jobs", provider=None))


def _wait_original(page):
    page.locator("#status").filter(has_text="Showing the original board").wait_for(timeout=15000)
    page.wait_for_load_state("networkidle")


def _site_entry(context, origin: str, step):
    main_page = context.new_page()
    main_page.goto(origin + "/#workspace", wait_until="networkidle")
    main_page.locator(".app-layout").wait_for(state="visible")
    request = main_page.locator("#free-text-request")
    draft = "Unsaved browser acceptance draft: an ESP32 button board."
    # Both isolated hosts honestly hide AI entry without a provider. Seed the
    # existing input's in-memory draft as test setup; do not advertise a fake
    # capability or submit it. Navigation must preserve it regardless of visibility.
    request.evaluate("""(element, value) => {
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
    }""", draft)
    main_page.locator('.sidebar-tools a[href="#home"]').click()
    main_page.locator("#home").wait_for(state="visible")
    with main_page.expect_popup() as opened:
        main_page.locator("[data-home-demo]").first.click()
    page = opened.value
    _wait_original(page)
    step("landing demo opens separately and preserves the seeded unsaved draft",
         request.input_value() == draft and urlsplit(main_page.url).fragment == "home"
         and page.evaluate("window.opener === null"))

    page.get_by_role("link", name="Back to Ohmni", exact=True).click()
    page.locator("#home").wait_for(state="visible")
    page.wait_for_load_state("networkidle")
    step("demo return link opens the home page", urlsplit(page.url).fragment == "home")
    page.go_back(wait_until="networkidle")
    _wait_original(page)
    page.get_by_role("link", name="Start your own board", exact=True).click()
    page.locator(".app-layout").wait_for(state="visible")
    page.wait_for_load_state("networkidle")
    step("demo build link opens the workspace", urlsplit(page.url).fragment == "workspace")
    page.go_back(wait_until="networkidle")
    _wait_original(page)

    main_page.locator(".home-start").click()
    main_page.locator(".app-layout").wait_for(state="visible")
    main_page.locator('details:has(a[href="/hackathon-demo.html"]) > summary').click()
    with main_page.expect_popup() as opened:
        main_page.get_by_role("link", name="Open saved demo (new tab)", exact=True).click()
    workspace_demo = opened.value
    _wait_original(workspace_demo)
    step("workspace demo link also preserves the seeded unsaved draft",
         request.input_value() == draft and urlsplit(main_page.url).fragment == "workspace"
         and workspace_demo.evaluate("window.opener === null"))
    workspace_demo.close()
    return page


def _exercise(context, origin: str, args, demo, controls, held, step):
    if args.host_mode == "offline":
        page = context.new_page()
        page.goto(origin + "/", wait_until="networkidle")
        _wait_original(page)
        step("offline host hides unavailable site navigation", page.locator("#site-navigation").is_hidden())
    else:
        page = _site_entry(context, origin, step)
        step("hosted demo has site navigation", page.locator("#site-navigation").is_visible())
    status = page.locator("#status")
    report = page.locator("#report").text_content()
    step("original board loads from local saved files", "Original board" in report and "PASS" in report
         and page.locator("#download").is_visible())
    renderer = page.locator("#board").get_attribute("data-renderer")
    step("saved board has an available canvas renderer", bool(renderer), f"renderer={renderer}")
    step("saved-run label is visible", "Saved successful run" in page.locator(".banner").inner_text()
         and "Nothing on this page is generated" in page.locator("#notice").inner_text())
    page.screenshot(path=str(args.evidence / "1-original.png"), full_page=True)

    with page.expect_download() as info:
        page.locator("#download").click()
    saved = args.evidence / "downloaded-package.zip"
    info.value.save_as(saved)
    digest = hashlib.sha256(saved.read_bytes()).hexdigest()
    step("local package downloads with recorded hash", digest == demo["download"]["sha256"], digest[:16])

    for round_number in (1, 2):
        page.locator("#show-fault").click()
        status.filter(has_text="Showing the damaged copy").wait_for(timeout=15000)
        report = page.locator("#report").text_content()
        ok = ("Damaged copy" in report and "FAIL" in report and "NOT CHECKED" in report
              and "Missing connection" in report and demo["fault"]["snapshot_sha256"] in report
              and not page.locator("#download").is_visible())
        step(f"fault shows its own DRC failure (round {round_number})", ok)
        if round_number == 1:
            page.screenshot(path=str(args.evidence / "2-fault.png"), full_page=True)
        page.locator("#restore").click()
        _wait_original(page)
        report = page.locator("#report").text_content()
        focused = page.evaluate("document.activeElement && document.activeElement.id")
        step(f"restore returns the original (round {round_number})",
             "Original board" in report and demo["good"]["board"]["artifact_fingerprint"] in report
             and page.locator("#download").is_visible() and focused == "show-good", f"focus={focused}")

    # Hold the damaged file, then force a competing selection to exercise the
    # selection token even though ordinary UI controls prevent concurrent clicks.
    page.reload(wait_until="networkidle")
    _wait_original(page)
    controls["hold_fault"] = True
    page.locator("#show-fault").click()
    deadline = time.monotonic() + 10
    while not held and time.monotonic() < deadline:
        page.wait_for_timeout(50)
    step("board controls are disabled while the file is pending", bool(held) and all(
        page.locator(selector).is_disabled() for selector in ("#show-good", "#show-fault", "#restore")))
    page.evaluate("document.querySelector('#show-good').disabled = false")
    page.locator("#show-good").click()
    _wait_original(page)
    released = bool(held)
    if released:
        with page.expect_response(lambda response: response.url.endswith("diagnostic-fault.kicad_pcb")):
            held.pop().continue_()
    page.wait_for_timeout(1000)
    controls["hold_fault"] = False
    report = page.locator("#report").text_content()
    step("late fault response cannot replace the original", released and "Original board" in report
         and page.evaluate("document.body.dataset.showing") == "good",
         "fault response delivered after the original was shown" if released else "fault request never held")
    page.screenshot(path=str(args.evidence / "3-restored.png"), full_page=True)

    controls["missing_demo"] = True
    page.reload(wait_until="networkidle")
    status.filter(has_text="The saved files could not load").wait_for()
    step("missing demo metadata leaves controls disabled and offers recovery",
         all(page.locator(selector).is_disabled() for selector in ("#show-good", "#show-fault", "#restore"))
         and page.locator("#download").is_hidden() and page.locator("#retry-demo").is_visible()
         and page.evaluate("document.body.dataset.showing") == "none")
    page.screenshot(path=str(args.evidence / "4-unavailable.png"), full_page=True)
    controls["missing_demo"] = False
    page.locator("#retry-demo").click()
    _wait_original(page)
    step("reload recovers once saved metadata is available", page.locator("#download").is_visible()
         and page.locator("#retry-demo").is_hidden() and not page.locator("#show-fault").is_disabled())

    page.set_viewport_size({"width": 390, "height": 844})
    for name in ("original", "fault"):
        if name == "fault":
            page.locator("#show-fault").click()
            status.filter(has_text="Showing the damaged copy").wait_for()
        dimensions = page.evaluate("""() => ({ viewport: document.documentElement.clientWidth,
            content: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) })""")
        step(f"mobile {name} view has no page overflow", dimensions["content"] <= dimensions["viewport"] + 1,
             f"viewport={dimensions['viewport']} content={dimensions['content']}")
        page.screenshot(path=str(args.evidence / f"5-mobile-{name}.png"), full_page=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chromium", help="Chromium executable (default: Playwright's)")
    parser.add_argument("--host-mode", choices=("offline", "site", "static"), default="offline")
    parser.add_argument("--evidence", type=Path, default=ROOT / "build" / "offline-demo-browser")
    args = parser.parse_args(argv)
    from playwright.sync_api import sync_playwright

    demo = json.loads((CAPTURE / "demo.json").read_text(encoding="utf-8"))
    args.evidence.mkdir(parents=True, exist_ok=True)
    external, failures, errors, steps, expected_failures = [], [], [], [], []
    browser_version = None

    def step(name: str, ok: bool, detail: str = "") -> None:
        steps.append({"step": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'} {name} {detail}")

    with TemporaryDirectory(prefix="ohmni-browser-check-") as scratch:
        server = _server(args.host_mode, Path(scratch))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        port = server.server_address[1]
        origin = f"http://127.0.0.1:{port}"
        controls = {"hold_fault": False, "missing_demo": False}
        held, injected = [], set()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=args.chromium) if args.chromium \
                    else playwright.chromium.launch()
                browser_version = browser.version
                try:
                    context = browser.new_context(accept_downloads=True, service_workers="block",
                                                  viewport={"width": 1440, "height": 1000})
                    context.set_default_timeout(15000)
                    context.set_default_navigation_timeout(20000)

                    def route(route, request):
                        parts = urlsplit(request.url)
                        if parts.scheme not in {"http", "https"} or parts.netloc != f"127.0.0.1:{port}":
                            if parts.scheme not in {"data", "blob"}:
                                external.append(request.url)
                            return route.abort("internetdisconnected")
                        if parts.path == "/hackathon-demo/demo.json" and controls["missing_demo"]:
                            injected.add(request)
                            return route.fulfill(status=404, content_type="text/plain", body="Injected missing capture")
                        if parts.path.endswith("diagnostic-fault.kicad_pcb") and controls["hold_fault"]:
                            held.append(route)
                            return None
                        return route.continue_()

                    def failed(request, description, status=None):
                        # A static frontend intentionally has no API. Record these
                        # startup 404s separately; do not exempt asset or demo failures.
                        static_api = (args.host_mode == "static" and status == 404
                                      and urlsplit(request.url).path.startswith("/api/"))
                        (expected_failures if request in injected or static_api else failures).append(description)

                    context.route("**/*", route)
                    context.on("requestfailed", lambda request: failed(
                        request, f"{request.failure} {request.url}"))
                    context.on("response", lambda response: response.status >= 400 and failed(
                        response.request, f"{response.status} {response.url}", response.status))
                    context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
                    _exercise(context, origin, args, demo, controls, held, step)
                finally:
                    browser.close()
        except Exception as error:  # noqa: BLE001 -- any harness error records FAIL, never success
            step("browser acceptance completes", False, f"{type(error).__name__}: {error}")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    step("no external request was attempted", not external, f"{external[:3]}")
    step("no unexpected local request failed", not failures, f"{failures[:3]}")
    step("no page errors", not errors, f"{errors[:3]}")
    passed = all(item["status"] == "PASS" for item in steps)
    (args.evidence / "browser-check.json").write_text(json.dumps(
        {"status": "PASS" if passed else "FAIL", "host_mode": args.host_mode, "browser_version": browser_version, "steps": steps,
         "external_requests": external, "failed_requests": failures, "page_errors": errors,
         "expected_failed_requests": expected_failures}, indent=2) + "\n", encoding="utf-8")
    print("PASS" if passed else "FAIL", f"evidence: {args.evidence}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
