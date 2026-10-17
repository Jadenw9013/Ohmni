#!/usr/bin/env python3
"""Network-disabled browser acceptance check for the saved demonstration.

The default offline host uses scripts/serve_offline_demo.py. --host-mode site
uses the real local app server with an isolated workspace and no model provider;
--host-mode static serves apps/web directly, as the frontend host does. Every
host binds an ephemeral 127.0.0.1 port, and browser requests elsewhere are blocked.

Checks recorded boards, download hashes, restore and delayed response behavior,
missing-file recovery, keyboard operation, desktop-to-mobile resizing and cold
mobile loads, and (for site/static) new-tab navigation without losing an unsaved
workspace draft. Nothing requests a generated board.

Layout is measured only after a bounded, observable readiness condition: every
board layer the view sizes in pixels (label overlay, fallback canvas) matches
the board canvas's current box. That condition is itself a step, and the
no-overflow assertion still runs (unchanged tolerance) whether or not it held.

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

# Narrow phone widths first; desktop is checked on the resize path and at load.
MOBILE_WIDTHS = (390, 375, 320)
DESKTOP = {"width": 1440, "height": 1000}
LAYOUT_READY_TIMEOUT_MS = 3000
KEYBOARD_TAB_LIMIT = 40

# Every absolutely positioned board layer is sized by BoardView in CSS pixels
# from the board canvas box. Ready means each visible layer matches that box.
LAYOUT_READY_JS = """() => {
    const board = document.querySelector('#board');
    if (!board || !board.parentElement) return false;
    const box = board.getBoundingClientRect();
    if (box.width <= 0 || box.height <= 0) return false;
    const layers = [...board.parentElement.querySelectorAll('canvas')]
        .filter((layer) => layer !== board && getComputedStyle(layer).display !== 'none');
    return layers.every((layer) => Math.abs(parseFloat(layer.style.width) - box.width) <= 0.5
        && Math.abs(parseFloat(layer.style.height) - box.height) <= 0.5);
}"""
PAGE_WIDTH_JS = """() => ({ viewport: document.documentElement.clientWidth,
    content: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) })"""


def wait_until(page, expression: str, seconds: float) -> bool:
    """Accept readiness only before the deadline, using process-side polling.

    In-page polling timers can be starved while the board animates on a loaded
    software-GL runner; a direct evaluation still answers.
    One evaluation cannot itself be interrupted here. A late answer fails;
    run_browser_acceptance.py supplies the outer 600-second process deadline if
    the browser stops answering altogether.
    """
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        ready = page.evaluate(expression)
        now = time.monotonic()
        if now >= deadline:
            return False
        if ready:
            return True
        page.wait_for_timeout(min(20, (deadline - now) * 1000))
    return False


def check_layout(page, label: str, step) -> bool:
    """Wait (bounded) for board layers to follow the board, then assert no overflow."""
    immediate = page.evaluate(PAGE_WIDTH_JS)
    started = time.monotonic()
    try:
        ready = wait_until(page, LAYOUT_READY_JS, LAYOUT_READY_TIMEOUT_MS / 1000)
    except Exception:  # noqa: BLE001 -- a page failure is a failed step
        ready = False
    waited = round((time.monotonic() - started) * 1000)
    step(f"{label}: board layers match the board size", ready,
         f"waited_ms={waited} limit_ms={LAYOUT_READY_TIMEOUT_MS}")
    dimensions = page.evaluate(PAGE_WIDTH_JS)
    fits = dimensions["content"] <= dimensions["viewport"] + 1
    step(f"{label}: no page overflow", fits,
         f"viewport={dimensions['viewport']} content={dimensions['content']} immediate_content={immediate['content']}")
    return ready and fits


def _tab_to(page, element_id: str) -> bool:
    for _ in range(KEYBOARD_TAB_LIMIT):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement && document.activeElement.id") == element_id:
            return True
    return False


def _keyboard_round(page, label: str, step) -> None:
    """Reach Show fault and Restore original by Tab; activate with Space and Enter."""
    page.evaluate("document.activeElement && document.activeElement.blur()")
    status = page.locator("#status")
    reached = _tab_to(page, "show-fault")
    if reached:
        page.keyboard.press("Space")
        status.filter(has_text="Showing the damaged copy").wait_for(timeout=15000)
    step(f"{label}: Tab reaches Show fault and Space shows the fault", reached
         and page.evaluate("document.body.dataset.showing") == "fault")
    reached = reached and _tab_to(page, "restore")
    focus_ready = False
    if reached:
        page.keyboard.press("Enter")
        _wait_original(page)
        page.locator("#show-good").wait_for(state="visible")
        focus_ready = wait_until(page, "() => document.activeElement && document.activeElement.id === 'show-good'", 5)
    focused = page.evaluate("document.activeElement && document.activeElement.id")
    step(f"{label}: Tab reaches Restore original and Enter restores with focus kept", reached and focus_ready
         and page.evaluate("document.body.dataset.showing") == "good" and focused == "show-good",
         f"focus={focused}")


def _download_matches(page, demo, path: Path) -> tuple[bool, str]:
    with page.expect_download() as info:
        page.locator("#download").click()
    info.value.save_as(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest == demo["download"]["sha256"], digest[:16]


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
    def main_ready(page):
        # Dynamic workspace bootstrap can continue after the document load and
        # the first idle gap. Do not navigate away while its modules are loading.
        page.evaluate("import('/main.js').then((m) => m.ready)")
        page.wait_for_load_state("networkidle")

    main_page = context.new_page()
    main_page.goto(origin + "/#workspace", wait_until="networkidle")
    main_ready(main_page)
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
    main_ready(page)
    page.locator("#home").wait_for(state="visible")
    page.wait_for_load_state("networkidle")
    step("demo return link opens the home page", urlsplit(page.url).fragment == "home")
    page.go_back(wait_until="networkidle")
    _wait_original(page)
    page.get_by_role("link", name="Start your own board", exact=True).click()
    main_ready(page)
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
    demo_url = origin + ("/" if args.host_mode == "offline" else "/hackathon-demo.html")
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

    check_layout(page, "desktop cold load", step)
    ok, digest = _download_matches(page, demo, args.evidence / "downloaded-package.zip")
    step("local package downloads with recorded hash", ok, digest)

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

    _keyboard_round(page, "desktop keyboard", step)

    # Desktop -> mobile on the live page, through original, fault and restore.
    for width in MOBILE_WIDTHS:
        page.set_viewport_size({"width": width, "height": 844})
        check_layout(page, f"resize to {width}px original", step)
    page.screenshot(path=str(args.evidence / "5-mobile-original.png"), full_page=True)
    page.locator("#show-fault").click()
    status.filter(has_text="Showing the damaged copy").wait_for()
    check_layout(page, f"{MOBILE_WIDTHS[-1]}px fault", step)
    page.screenshot(path=str(args.evidence / "5-mobile-fault.png"), full_page=True)
    page.locator("#restore").click()
    _wait_original(page)
    check_layout(page, f"{MOBILE_WIDTHS[-1]}px restored", step)
    page.locator("#show-fault").click()
    status.filter(has_text="Showing the damaged copy").wait_for()
    page.set_viewport_size(DESKTOP)
    check_layout(page, "resize back to desktop with fault shown", step)
    page.set_viewport_size({"width": MOBILE_WIDTHS[0], "height": 844})
    check_layout(page, f"resize to {MOBILE_WIDTHS[0]}px with fault shown", step)
    page.locator("#restore").click()
    _wait_original(page)
    page.close()

    for width in MOBILE_WIDTHS:
        _cold_mobile(context, demo_url, width, args, demo, controls, step)


def _cold_mobile(context, url: str, width: int, args, demo, controls, step) -> None:
    """A fresh page opened at phone width: layout, keyboard, download, recovery."""
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(url, wait_until="networkidle")
    _wait_original(page)
    label = f"cold {width}px"
    check_layout(page, f"{label} original", step)
    _keyboard_round(page, f"{label} keyboard", step)
    check_layout(page, f"{label} after keyboard restore", step)
    ok, digest = _download_matches(page, demo, args.evidence / f"downloaded-package-{width}.zip")
    step(f"{label}: package downloads with recorded hash", ok, digest)
    if width == MOBILE_WIDTHS[-1]:
        page.screenshot(path=str(args.evidence / f"6-cold-{width}.png"), full_page=True)
        controls["missing_demo"] = True
        page.reload(wait_until="networkidle")
        page.locator("#status").filter(has_text="The saved files could not load").wait_for()
        retry = page.locator("#retry-demo")
        box = retry.bounding_box()
        viewport = page.evaluate("document.documentElement.clientWidth")
        step(f"{label}: recovery control is visible and within the screen",
             retry.is_visible() and box is not None and box["x"] >= 0 and box["x"] + box["width"] <= viewport + 1,
             f"box={box} viewport={viewport}")
        dimensions = page.evaluate(PAGE_WIDTH_JS)
        step(f"{label}: unavailable state has no page overflow",
             dimensions["content"] <= dimensions["viewport"] + 1,
             f"viewport={dimensions['viewport']} content={dimensions['content']}")
        page.screenshot(path=str(args.evidence / f"6-cold-{width}-unavailable.png"), full_page=True)
        controls["missing_demo"] = False
        retry.click()
        _wait_original(page)
        step(f"{label}: recovery reload shows the original again", page.locator("#download").is_visible()
             and retry.is_hidden())
        check_layout(page, f"{label} after recovery", step)
    page.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chromium", help="Chromium executable (default: Playwright's)")
    parser.add_argument("--host-mode", choices=("offline", "site", "static"), default="offline")
    parser.add_argument("--evidence", type=Path, default=ROOT / "build" / "offline-demo-browser")
    args = parser.parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None

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
            if sync_playwright is None:
                raise RuntimeError("the playwright package is not installed")
            with sync_playwright() as playwright:
                # Every host but loopback also fails name resolution, beneath the request router.
                launch = {"args": ["--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"]}
                browser = playwright.chromium.launch(executable_path=args.chromium, **launch) if args.chromium \
                    else playwright.chromium.launch(**launch)
                browser_version = browser.version
                try:
                    context = browser.new_context(accept_downloads=True, service_workers="block",
                                                  viewport=DESKTOP)
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
                    try:
                        _exercise(context, origin, args, demo, controls, held, step)
                    except Exception:
                        # Keep what each open page showed when the check stopped.
                        for index, open_page in enumerate(context.pages):
                            try:
                                open_page.screenshot(path=str(args.evidence / f"failure-{index}.png"), full_page=True)
                            except Exception:  # noqa: BLE001, S110 -- evidence only; the failure is still recorded
                                pass
                        raise
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
