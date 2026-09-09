"""Frontend structure and dependency-free component behavior."""

import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).parents[1] / "apps" / "web"


def _read(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


class _Elements(HTMLParser):
    def __init__(self, html: str):
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def by_id(self, element_id):
        matches = [element for element in self.elements if element[1].get("id") == element_id]
        assert len(matches) == 1, f"expected one element with id={element_id!r}"
        return matches[0]


def _frontend_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in WEB_ROOT.glob("*.js"))


def test_the_first_screen_has_one_focused_accessible_start():
    page = _Elements(_read("index.html"))
    stages = ("describe", "agree", "design", "review", "build")
    for stage in stages:
        tag, attrs = page.by_id(stage)
        assert tag == "section"
        assert ("hidden" in attrs) is (stage != "describe")
        assert attrs.get("aria-labelledby"), f"{stage} needs an accessible heading"
        page.by_id(attrs["aria-labelledby"])
    tag, button = page.by_id("start-supported")
    assert tag == "button" and button.get("type") == "button"
    assert "disabled" not in button
    for stage in stages:
        assert any(tag == "button" and attrs.get("data-navigate") == stage
                   for tag, attrs in page.elements), f"{stage} needs keyboard-accessible navigation"


def test_the_entry_screen_identifies_the_bounded_project_and_saved_reference_scope():
    html = _read("index.html")
    page = _Elements(html)
    page.by_id("scope-note")
    scope = re.search(r'<[^>]+id="scope-note"[^>]*>(.*?)</[^>]+>', html, re.DOTALL)
    assert scope, "the entry screen needs its visible scope disclosure"
    text = re.sub(r"<[^>]+>", " ", scope.group(1)).lower()
    for boundary in ("supported", "usb-powered", "esp32", "bme280", "selected configuration"):
        assert boundary in text
    assert "actual checks" in text
    assert "assembly, programming, and hardware testing come next" in text
    tag, action = page.by_id("create-project")
    assert tag == "button" and action.get("type") == "button"
    assert "disabled" not in action
    assert "status light and programming connections" in html.lower()
    assert re.search(r'class="reference-provenance">Saved reference<', html)
    assert "Or run the fixed reference example" in html


def test_review_uses_accessible_tabs_and_a_separate_build_step():
    page = _Elements(_read("index.html"))
    for panel in ("board", "learn", "checks"):
        tabs = [attrs for tag, attrs in page.elements
                if tag == "button" and attrs.get("data-panel") == panel]
        panes = [attrs for _, attrs in page.elements if attrs.get("data-result-panel") == panel]
        assert len(tabs) == len(panes) == 1
        assert tabs[0].get("role") == "tab"
        assert panes[0].get("role") == "tabpanel"
        assert tabs[0].get("aria-controls") == panes[0].get("id")
        assert tabs[0].get("aria-selected") == str(panel == "board").lower()
        assert ("hidden" in panes[0]) is (panel != "board")
    for element_id, destination in (("open-build", "build"), ("back-to-board", "review")):
        tag, attrs = page.by_id(element_id)
        assert tag == "button" and attrs.get("data-navigate") == destination


def test_the_ui_never_overstates_what_was_established():
    text = _read("index.html").lower() + _frontend_source().lower()
    for overclaim in ("production ready", "production-ready", "guaranteed manufacturable",
                      "guaranteed to work", "proven to work", "fully verified"):
        assert overclaim not in text
    app = _frontend_source()
    # Not-yet-verified and unsupported reach the screen unchanged.
    assert "NOT_YET_VERIFIED" in app
    assert "not_verified" in app and "Not verified" in app


def test_the_frontend_computes_no_engineering_verdicts():
    """Statuses are rendered from the projection; none are decided here."""
    app = _read("app.js")
    assert "badge(stage.status)" in app and "badge(group.status)" in app
    assert "badge(rule.outcome)" in app and "badge(item.status)" in app
    # No comparison anywhere turns a measurement into a pass or a fail.
    for invented in ("=== \"PASS\"", "> 3.6", "< 3.6", "voltage >", "voltage <"):
        assert invented not in app


def test_the_client_stays_bound_to_one_server_generation():
    app = _frontend_source()
    assert "const API_VERSION = 2" in app
    assert '"/api/health"' in app and '"/api/brief"' in app and '"/api/demo"' in app
    assert '"X-Ohmni-Server-Instance"' in app and '"X-Ohmni-UI-Version"' in app
    assert "generation_mismatch" in app and "lost_job" in app


def test_every_executable_asset_is_served_by_the_demo_server():
    """A module the page imports but the server does not serve is a dead page."""
    import scripts.demo_server as server

    roots = set(re.findall(r'<script[^>]+src=[\'"]/([A-Za-z0-9._-]+\.js)[\'"]', _read("index.html")))
    assert roots, "the page must load its executable entry point"
    imported: set[str] = set()
    pending = set(roots)
    referenced_data: set[str] = set()
    while pending:
        name = pending.pop()
        if name in imported:
            continue
        assert name in server.STATIC_ASSETS, f"unserved browser module: {name}"
        imported.add(name)
        source = _read(name)
        dependencies = set(re.findall(r'(?:from\s*|import\s*)[\'"]\./([A-Za-z0-9._-]+\.js)[\'"]', source))
        pending.update(dependencies - imported)
        referenced_data.update(re.findall(r'[\'"](?:/|\./)([A-Za-z0-9._-]+\.json)[\'"]', source))
    assert {"board-view.js", "schematic-view.js"} <= imported
    assert referenced_data <= set(server.STATIC_ASSETS)
    for name in server.STATIC_ASSETS:
        assert (WEB_ROOT / name).is_file()
        assert name in server.STATIC_CONTENT_TYPES


def test_the_board_view_is_reachable_and_labelled_for_assistive_technology():
    html = _read("index.html")
    assert 'id="board-canvas"' in html
    assert "Drag to rotate" in html
    assert 'tabindex="0"' in html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_frontend_module_behavior():
    result = subprocess.run(
        ["node", "--test", *map(str, sorted((WEB_ROOT / "tests").glob("*.test.mjs")))],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False, shell=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# fail 0" in result.stdout
    passed = int(re.search(r"# pass (\d+)", result.stdout).group(1))
    assert passed >= 30, result.stdout
