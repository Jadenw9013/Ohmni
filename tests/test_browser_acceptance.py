"""Real-Chromium regressions for saved-demo and telemetry smoke readiness.

The layout check in scripts/browser_check_offline_demo.py waits for a bounded,
observable readiness condition and then keeps its no-overflow assertion. These
tests prove the wait cannot turn persistent overflow into a pass.

They need the optional Playwright package and a Chromium build. Without them the
tests skip locally; with OHMNI_REQUIRE_BROWSER=1 (set by the CI browser job) a
missing browser fails instead of skipping.
"""

from __future__ import annotations

import json
import os
import time
from types import SimpleNamespace

import pytest

from scripts import browser_check_offline_demo as checker
from scripts import smoke_browser_telemetry as telemetry_smoke

REQUIRED = os.environ.get("OHMNI_REQUIRE_BROWSER") == "1"


def _unavailable(reason: str):
    if REQUIRED:
        pytest.fail(f"browser acceptance required but unavailable: {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="module")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _unavailable("playwright is not installed")
    with sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except Exception as error:  # noqa: BLE001 -- a missing browser is reported, not hidden
            _unavailable(f"chromium could not launch: {type(error).__name__}")
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    context.route("**/*", lambda route: route.abort("internetdisconnected"))
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


# Mirrors the demo page's structure: a fluid board canvas with an absolutely
# positioned label overlay that a ResizeObserver sizes in CSS pixels.
PAGE = """<!doctype html><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{margin:0}} .stage{{position:relative}} #board{{width:100%;height:300px;display:block}}</style>
<div class="stage"><canvas id="board"></canvas></div>
<script>
const board = document.querySelector('#board');
const overlay = document.createElement('canvas');
overlay.style.position = 'absolute'; overlay.style.left = '0px'; overlay.style.top = '0px';
board.parentElement.appendChild(overlay);
function sync() {{
  const box = board.getBoundingClientRect();
  overlay.style.width = box.width + 'px'; overlay.style.height = box.height + 'px';
}}
sync();
{observer}
{extra}
</script>"""

FOLLOWS = "new ResizeObserver(sync).observe(board);"


def _steps():
    recorded = []

    def step(name, ok, detail=""):
        recorded.append((name, ok, detail))

    return recorded, step


def _resize_and_check(page, html):
    page.set_content(html)
    page.set_viewport_size({"width": 320, "height": 700})
    recorded, step = _steps()
    result = checker.check_layout(page, "probe", step)
    return result, {name.split(": ", 1)[1]: (ok, detail) for name, ok, detail in recorded}


def test_overlay_that_follows_the_board_passes_after_resize(page, monkeypatch):
    # Release the pending overlay update only after the initial measurement.
    # A fixed 200 ms timer can fire before that measurement on a busy runner,
    # making an otherwise correct readiness check fail intermittently.
    evaluate = page.evaluate
    released = False

    def measure_then_release(expression):
        nonlocal released
        result = evaluate(expression)
        if expression == checker.PAGE_WIDTH_JS and not released:
            released = True
            evaluate("requestAnimationFrame(sync)")
        return result

    monkeypatch.setattr(page, "evaluate", measure_then_release)
    result, steps = _resize_and_check(page, PAGE.format(observer="", extra=""))
    assert result is True
    assert steps["board layers match the board size"][0] is True
    ok, detail = steps["no page overflow"]
    assert ok is True and "viewport=320 content=320" in detail
    # The pre-readiness measurement shows the transient this condition waits out.
    assert "immediate_content=1440" in detail


def test_overlay_that_never_follows_fails_both_readiness_and_overflow(page):
    result, steps = _resize_and_check(page, PAGE.format(observer="", extra=""))
    assert result is False
    assert steps["board layers match the board size"][0] is False
    ok, detail = steps["no page overflow"]
    assert ok is False and "viewport=320 content=1440" in detail


def test_persistent_overflow_elsewhere_still_fails_when_layers_are_ready(page):
    wide = ("const wide = document.createElement('div'); wide.style.width = '500px';"
            "wide.style.height = '10px'; document.body.appendChild(wide);")
    result, steps = _resize_and_check(page, PAGE.format(observer=FOLLOWS, extra=wide))
    assert result is False
    assert steps["board layers match the board size"][0] is True
    ok, detail = steps["no page overflow"]
    assert ok is False and "content=500" in detail


def test_one_pixel_beyond_the_tolerance_fails(page):
    wide = ("const wide = document.createElement('div'); wide.style.width = '322px';"
            "wide.style.height = '10px'; document.body.appendChild(wide);")
    result, steps = _resize_and_check(page, PAGE.format(observer=FOLLOWS, extra=wide))
    assert result is False
    assert steps["no page overflow"][0] is False


def test_readiness_wait_is_bounded(page, monkeypatch):
    monkeypatch.setattr(checker, "LAYOUT_READY_TIMEOUT_MS", 300)
    started = time.monotonic()
    result, steps = _resize_and_check(page, PAGE.format(observer="", extra=""))
    elapsed = time.monotonic() - started
    assert result is False and elapsed < 5
    assert "limit_ms=300" in steps["board layers match the board size"][1]


def test_missing_browser_fails_the_whole_check(tmp_path):
    # An unlaunchable browser is a FAIL with exit 1, never a skipped green.
    code = checker.main(["--chromium", str(tmp_path / "no-such-chromium"),
                         "--evidence", str(tmp_path / "evidence")])
    assert code == 1
    report = json.loads((tmp_path / "evidence" / "browser-check.json").read_text())
    assert report["status"] == "FAIL"
    assert any(item["step"] == "browser acceptance completes" and item["status"] == "FAIL"
               for item in report["steps"])


def test_telemetry_smoke_waits_for_rendered_brief_after_initial_enabled_button(page):
    page.set_content("""<button id="start-supported">Start</button>
        <section id="agree" hidden><div id="brief"></div>
        <button id="confirm-brief">Confirm</button></section>
        <script>
        document.querySelector('#start-supported').onclick = () => {
            document.querySelector('#start-supported').disabled = true;
            window.finishBrief = () => {
                document.querySelector('#brief').innerHTML = '<p>Loaded brief</p>';
                document.querySelector('#agree').hidden = false;
                document.querySelector('#start-supported').disabled = false;
            };
        };
        </script>""")
    page.locator("#start-supported").click()
    # This is the previous condition: it passes while the brief is still pending.
    assert page.evaluate("!document.querySelector('#confirm-brief').disabled") is True
    assert page.locator("#agree").is_hidden()
    page.evaluate("setTimeout(window.finishBrief, 300)")
    telemetry_smoke.wait_for_brief_ready(page)
    assert page.locator("#agree").is_visible()
    assert page.locator("#brief").inner_text() == "Loaded brief"
    assert page.locator("#start-supported").is_enabled()


def test_telemetry_smoke_disabled_confirmation_still_fails_within_bound(page, monkeypatch):
    from playwright.sync_api import TimeoutError as BrowserTimeout

    page.set_content("""<button id="start-supported">Start</button>
        <section id="agree"><div id="brief"><p>Loaded brief</p></div>
        <button id="confirm-brief" disabled>Confirm</button></section>""")
    monkeypatch.setattr(telemetry_smoke, "BRIEF_READY_TIMEOUT_MS", 300)
    started = time.monotonic()
    with pytest.raises(BrowserTimeout):
        telemetry_smoke.wait_for_brief_ready(page)
    assert time.monotonic() - started < 5


def test_telemetry_smoke_response_wait_requires_expected_post_and_origin():
    origin = "http://127.0.0.1:8000"
    for url, method, expected in (
        (origin + "/api/brief", "POST", True),
        (origin + "/api/brief", "OPTIONS", False),
        (origin + "/api/brief", "GET", False),
        ("http://127.0.0.1:8001/api/brief", "POST", False),
    ):
        response = SimpleNamespace(url=url, request=SimpleNamespace(method=method))
        assert telemetry_smoke.is_post_response(response, origin, "/api/brief") is expected
