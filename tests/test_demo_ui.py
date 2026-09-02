"""Frontend structure and dependency-free component behavior."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).parents[1] / "apps" / "web"


def _read(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


def test_the_first_screen_asks_the_user_what_they_want_to_build():
    html = _read("index.html")
    text = html.lower()
    assert "what do you want to build?" in text
    # The user's idea is the entry point, not the pipeline.
    assert text.index("what do you want to build?") < text.index('id="agree"')
    assert "you do not need" in text and "electronics vocabulary" in text
    for stage in ("describe", "agree", "design", "review", "build"):
        assert f'id="{stage}"' in html


def test_unsupported_projects_are_offered_honestly_rather_than_hidden():
    html = _read("index.html")
    assert html.count("Not built yet") == 3
    assert "Available now" in html
    # The one unsupported case that is unsupported on purpose says why.
    assert "safety-relevant design" in html


def test_the_ui_never_overstates_what_was_established():
    text = _read("index.html").lower() + _read("app.js").lower()
    for overclaim in ("production ready", "production-ready", "guaranteed manufacturable",
                      "guaranteed to work", "proven to work", "fully verified"):
        assert overclaim not in text
    app = _read("app.js")
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
    app = _read("app.js")
    assert "const API_VERSION = 2" in app
    assert '"/api/health"' in app and '"/api/brief"' in app and '"/api/demo"' in app
    assert '"X-Ohmni-Server-Instance"' in app and '"X-Ohmni-UI-Version"' in app
    assert "generation_mismatch" in app and "lost_job" in app


def test_every_executable_asset_is_served_by_the_demo_server():
    """A module the page imports but the server does not serve is a dead page."""
    import scripts.demo_server as server

    imported = set(re.findall(r'from\s+"\./([A-Za-z0-9._-]+\.js)"', _read("app.js")))
    imported |= set(re.findall(r'from\s+"\./([A-Za-z0-9._-]+\.js)"', _read("board-view.js")))
    imported |= set(re.findall(r'from\s+"\./([A-Za-z0-9._-]+\.js)"', _read("schematic-view.js")))
    assert imported, "app.js is expected to import the visualization modules"
    assert imported <= set(server.STATIC_ASSETS)
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
        ["node", "--test", "apps/web/tests/view-model.test.mjs", "apps/web/tests/board-model.test.mjs"],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False, shell=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# fail 0" in result.stdout
    passed = int(re.search(r"# pass (\d+)", result.stdout).group(1))
    assert passed >= 30, result.stdout
