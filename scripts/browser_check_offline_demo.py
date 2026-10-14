#!/usr/bin/env python3
"""Network-disabled browser acceptance check for the offline saved demonstration.

Starts scripts/serve_offline_demo.py on an ephemeral 127.0.0.1 port, opens a
fresh Chromium context in which every request to any other host is aborted,
then: loads the original board, downloads the saved package and checks its
hash, shows the fault, restores the original twice, and proves a delayed
response for an earlier choice cannot replace the current selection.

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
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.serve_offline_demo import CAPTURE, make_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chromium", help="Chromium executable (default: Playwright's)")
    parser.add_argument("--evidence", type=Path, default=ROOT / "build" / "offline-demo-browser")
    args = parser.parse_args(argv)
    from playwright.sync_api import sync_playwright

    demo = json.loads((CAPTURE / "demo.json").read_text(encoding="utf-8"))
    server = make_server(0)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{port}"
    args.evidence.mkdir(parents=True, exist_ok=True)
    external, failures, errors, steps = [], [], [], []

    def step(name: str, ok: bool, detail: str = "") -> None:
        steps.append({"step": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        print(f"{'PASS' if ok else 'FAIL'} {name} {detail}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium) if args.chromium \
            else playwright.chromium.launch()
        context = browser.new_context(accept_downloads=True, service_workers="block")
        hold = {"fault": False}
        held: list = []

        def route(route, request):
            parts = urlsplit(request.url)
            if parts.scheme not in {"http", "https"} or parts.netloc != f"127.0.0.1:{port}":
                if parts.scheme not in {"data", "blob"}:
                    external.append(request.url)
                return route.abort("internetdisconnected")
            if parts.path.endswith("diagnostic-fault.kicad_pcb") and hold["fault"]:
                held.append(route)  # answered later, after the original is showing again
                return None
            return route.continue_()

        context.route("**/*", route)
        page = context.new_page()
        page.on("requestfailed", lambda request: failures.append(request.url))
        page.on("response", lambda response: response.status >= 400 and failures.append(
            f"{response.status} {response.url}"))
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(origin + "/", wait_until="networkidle")
        status = page.locator("#status")
        status.filter(has_text="Showing the original board").wait_for(timeout=15000)
        report = page.locator("#report").text_content()
        step("original board loads offline", "Original board" in report and "PASS" in report
             and page.locator("#download").is_visible())
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
            status.filter(has_text="Showing the original board").wait_for(timeout=15000)
            report = page.locator("#report").text_content()
            focused = page.evaluate("document.activeElement && document.activeElement.id")
            step(f"restore returns the original (round {round_number})",
                 "Original board" in report and demo["good"]["board"]["artifact_fingerprint"] in report
                 and page.locator("#download").is_visible() and focused == "show-good", f"focus={focused}")

        # Hold the damaged board's file, switch back to the original, then
        # release the held response so it really arrives after the original.
        page.reload(wait_until="networkidle")
        status.filter(has_text="Showing the original board").wait_for(timeout=15000)
        hold["fault"] = True
        page.locator("#show-fault").click()
        deadline = time.monotonic() + 10
        while not held and time.monotonic() < deadline:
            page.wait_for_timeout(50)
        page.evaluate("document.querySelector('#show-good').disabled = false")
        page.locator("#show-good").click()
        status.filter(has_text="Showing the original board").wait_for(timeout=15000)
        released = bool(held)
        if released:
            with page.expect_response(lambda response: response.url.endswith("diagnostic-fault.kicad_pcb")):
                held.pop().continue_()
        page.wait_for_timeout(1000)
        hold["fault"] = False
        report = page.locator("#report").text_content()
        step("late fault response cannot replace the original", released and "Original board" in report
             and page.evaluate("document.body.dataset.showing") == "good",
             "fault response delivered after the original was shown" if released else "fault request never held")
        page.screenshot(path=str(args.evidence / "3-restored.png"), full_page=True)
        browser.close()
    server.shutdown()
    step("no external request was attempted", not external, f"{external[:3]}")
    step("no local request failed", not failures, f"{failures[:3]}")
    step("no page errors", not errors, f"{errors[:3]}")
    passed = all(item["status"] == "PASS" for item in steps)
    (args.evidence / "browser-check.json").write_text(json.dumps(
        {"status": "PASS" if passed else "FAIL", "steps": steps, "external_requests": external,
         "failed_requests": failures, "page_errors": errors}, indent=2) + "\n", encoding="utf-8")
    print("PASS" if passed else "FAIL", f"evidence: {args.evidence}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
