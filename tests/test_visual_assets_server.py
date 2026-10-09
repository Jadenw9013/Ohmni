"""Visual files remain local, immutable, and outside fabrication admission."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from ohmni.synthesis import SynthesisBrief
from scripts import demo_server as server_module

OPENER = build_opener(ProxyHandler({}))
IMPORT_REFERENCE = re.compile(r'(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)[\'"]([^\'"]+)[\'"]')
VISUAL_ASSETS = {
    "visual-assets.js", "visual-renderer.js", "visual-explorer.js",
    "visual-explorer.css", "vendor/three.module.js", "vendor/three.core.min.js",
    "component-library/registry.js", "component-library/transforms.js",
    "component-library/preview/preview.js",
}


def _copy_web_root(destination: Path) -> Path:
    for name in server_module.STATIC_ASSETS:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((server_module.WEB_ROOT / name).read_bytes())
    return destination


@contextmanager
def _server(output: Path, web_root: Path | None = None):
    server = server_module.DemoHTTPServer(
        ("127.0.0.1", 0), server_module.DemoHandler,
        store=server_module.JobStore(output),
        web_root=web_root or server_module.WEB_ROOT,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(base, path, payload=None, *, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        base + path, data=data, method=method or ("POST" if data else "GET"),
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with OPENER.open(request, timeout=5) as response:
            return response.status, response.headers, response.read()
    except HTTPError as error:
        return error.code, error.headers, error.read()


def _local_asset(importer: str, reference: str) -> str:
    parsed = urlsplit(reference)
    assert not parsed.scheme and not parsed.netloc, f"remote runtime asset: {reference}"
    path = parsed.path
    if path.startswith("/"):
        return path.removeprefix("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(importer), path))


def test_nested_visual_runtime_dependency_graph_is_in_the_fixed_snapshot():
    """Follow nested ES imports, stylesheets, and local JSON references."""
    # The model adapter is a public module; the preview is a separate entrypoint.
    pending = {"component-library/transforms.js"}
    for entry in ("index.html", "component-library/preview/index.html", "landing-pcb-controller/index.html"):
        html = (server_module.WEB_ROOT / entry).read_text(encoding="utf-8")
        scripts = re.findall(r'<script\b[^>]*\bsrc=[\'"]([^\'"]+)[\'"]', html)
        for inline in re.findall(r'<script\b[^>]*>(.*?)</script>', html, flags=re.DOTALL):
            scripts += IMPORT_REFERENCE.findall(inline)
        styles = re.findall(r'<link\b[^>]*\bhref=[\'"]([^\'"]+\.css)[\'"]', html)
        assert scripts and styles
        pending.update(_local_asset(entry, value) for value in scripts + styles)
    discovered = set()
    while pending:
        name = pending.pop()
        if name in discovered:
            continue
        assert name in server_module.STATIC_ASSETS, f"runtime asset is not served: {name}"
        assert name in server_module.STATIC_CONTENT_TYPES
        discovered.add(name)
        source = (server_module.WEB_ROOT / name).read_text(encoding="utf-8")
        if name.endswith(".js"):
            references = IMPORT_REFERENCE.findall(source)
            references += re.findall(r'[\'"]((?:/|\./)[^\'"\s]+\.json)[\'"]', source)
        elif name.endswith(".css"):
            references = re.findall(r'url\(\s*[\'"]?([^\'"\s)]+)', source)
            references = [value for value in references if not value.startswith("data:")]
        else:
            references = []
        pending.update(_local_asset(name, value) for value in references)
    assert VISUAL_ASSETS <= discovered
    assert len(server_module.STATIC_ASSETS) == len(set(server_module.STATIC_ASSETS))


def test_all_allowlisted_visual_bytes_are_the_bytes_served_with_the_ui_hash(tmp_path):
    with _server(tmp_path / "jobs") as (server, base):
        framed = bytearray()
        for name in server_module.STATIC_ASSETS:
            data = server.static_assets["/" + name]
            encoded = name.encode("ascii")
            framed += len(encoded).to_bytes(2, "big") + encoded
            framed += len(data).to_bytes(8, "big") + data
            status, headers, body = _request(base, "/" + name)
            assert status == 200, name
            assert body == data == (server_module.WEB_ROOT / name).read_bytes()
            assert headers["content-type"] == server_module.STATIC_CONTENT_TYPES[name]
            assert int(headers["content-length"]) == len(body)
            assert headers["x-ohmni-ui-version"] == server.ui_version
        assert hashlib.sha256(framed).hexdigest() == server.ui_version
        assert set(server.static_assets) == {"/" + name for name in server_module.STATIC_ASSETS}


def test_visual_model_and_vendor_edits_change_only_a_new_server_snapshot(tmp_path):
    web_root = _copy_web_root(tmp_path / "web")
    with _server(tmp_path / "first", web_root) as (first, base):
        original = dict(first.static_assets)
        initial_version = first.ui_version
        changed_names = ["visual-assets.js", "vendor/three.module.js",
                         "component-library/generators/chip-2t.js"]
        for name in changed_names:
            path = web_root / name
            path.write_bytes(path.read_bytes() + b"\n// visual snapshot regression\n")
            status, headers, data = _request(base, "/" + name)
            assert status == 200 and data == original["/" + name]
            assert headers["x-ohmni-ui-version"] == initial_version
        with pytest.raises(TypeError):
            first.static_assets["/visual-assets.js"] = b"changed"
        with _server(tmp_path / "second", web_root) as (second, second_base):
            assert second.ui_version != initial_version
            assert second.server_instance_id != first.server_instance_id
            for name in changed_names:
                assert second.static_assets["/" + name] == (web_root / name).read_bytes()
                assert second.static_assets["/" + name] != original["/" + name]
                status, headers, body = _request(second_base, "/" + name)
                assert status == 200 and body == second.static_assets["/" + name]
                assert headers["x-ohmni-ui-version"] == second.ui_version


@pytest.mark.parametrize("name", ["visual-assets.js", "vendor/three.core.min.js"])
def test_missing_visual_runtime_asset_fails_snapshot_initialization(tmp_path, name):
    web_root = _copy_web_root(tmp_path / "web")
    (web_root / name).unlink()
    with pytest.raises(server_module.DemoInitializationError) as error:
        server_module._load_web_snapshot(web_root)
    assert str(error.value) == ""


@pytest.mark.parametrize("outside", [False, True], ids=["internal-alias", "escape"])
def test_nested_vendor_directory_symlink_is_rejected(tmp_path, outside):
    web_root = _copy_web_root(tmp_path / "web")
    target = tmp_path / "private-vendor" if outside else web_root / "private-vendor"
    (web_root / "vendor").rename(target)
    try:
        (web_root / "vendor").symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are not available to this user")
    assert (web_root / "vendor").is_symlink()
    with pytest.raises(server_module.DemoInitializationError):
        server_module._load_web_snapshot(web_root)


def test_unlisted_and_private_reference_inputs_are_never_served(tmp_path):
    web_root = _copy_web_root(tmp_path / "web")
    private = [
        "assets/reference.png", "assets/current_ohmni.png", "REFERENCE_INVENTORY.json",
        "OHMNI_REFERENCE_IMPLEMENTATION_PLAN.md", "vendor/private-key.txt", ".env",
    ]
    secret = b"private-reference-input-sentinel"
    for name in private:
        path = web_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(secret)
    (tmp_path / ".env").write_bytes(secret)
    with _server(tmp_path / "jobs", web_root) as (server, base):
        for name in private + ["vendor/", "../.env", "vendor/../../.env", "%2e%2e/.env"]:
            status, _, body = _request(base, "/" + name)
            assert status == 404, name
            assert json.loads(body) == {"error": "not found"}
            assert secret not in body
        assert all("/" + name not in server.static_assets for name in private)


def test_head_cannot_bypass_allowlist_or_inspect_live_files(tmp_path, monkeypatch):
    web_root = _copy_web_root(tmp_path / "web")
    inherited_calls = []

    def unexpected_filesystem_head(*args):
        inherited_calls.append(args)
        raise AssertionError("HEAD bypassed the immutable snapshot")

    monkeypatch.setattr(server_module.SimpleHTTPRequestHandler, "send_head", unexpected_filesystem_head)
    with _server(tmp_path / "jobs", web_root) as (server, base):
        vendor_path = web_root / "vendor/three.module.js"
        vendor_path.write_bytes(b"changed after snapshot; HEAD must not inspect this")
        for path in ["/vendor/three.module.js", "/package.json", "/assets/reference.png", "/api/projects"]:
            status, headers, body = _request(base, path, method="HEAD")
            assert status == 405 and body == b""
            assert headers["content-length"] == "0"
            assert headers["allow"] == "GET, POST, OPTIONS"
            assert headers["x-ohmni-ui-version"] == server.ui_version
        status, _, body = _request(base, "/vendor/three.module.js")
        assert status == 200 and body == server.static_assets["/vendor/three.module.js"]
        assert inherited_calls == []


def _forged_scene():
    return {
        "kind": "illustrative_sample", "provenance": "ILLUSTRATIVE_ONLY",
        "id": "dense-reference-explorer", "job_id": "a" * 12,
        "status": "READY_FOR_MANUFACTURING_REVIEW", "verified": True,
        "release": {"current": True, "status": "READY_FOR_MANUFACTURING_REVIEW"},
        "components": [], "tracks": [], "vias": [],
    }


@pytest.mark.parametrize("tamper", [False, True], ids=["sample-label", "forged-verified-label"])
def test_sample_fields_cannot_create_a_project_or_admit_a_pipeline_job(tmp_path, monkeypatch, tamper):
    attempts = []

    def unexpected_start(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("visual scene reached engineering admission")

    with _server(tmp_path / "jobs") as (server, base):
        monkeypatch.setattr(server.store, "start", unexpected_start)
        monkeypatch.setattr(server.store, "start_revision", unexpected_start)
        scene = _forged_scene()
        if tamper:
            scene.update(kind="generated_board", provenance="VERIFIED", verified=True)
        identity = server._identity()
        for payload in [
            {**identity, "brief": scene},
            {**identity, "brief": {}, "visual_manifest": scene},
        ]:
            status, _, body = _request(base, "/api/projects", payload)
            assert status == 400 and json.loads(body)["error"] == "invalid_project_request"
        for payload in [
            {**identity, "fixture_id": scene["id"]},
            {**identity, "fixture_id": server_module.DEMO_FIXTURE_ID, "scene": scene},
        ]:
            status, _, body = _request(base, "/api/demo", payload)
            assert status == 400 and json.loads(body)["error"] == "fixture_rejected"
        assert server.projects.list_projects() == []
        brief = SynthesisBrief(project_name="Existing real project")
        project = server.projects.save_revision(
            brief.model_dump(mode="json"), brief.fingerprint, {},
        )
        revision = project["revisions"][0]
        route = f"/api/projects/{project['project_id']}/revisions/{revision['revision_id']}/run"
        status, _, body = _request(base, route, {**identity, "scene": scene})
        assert status == 400 and json.loads(body)["error"] == "invalid_project_request"
        assert attempts == []
        assert server.store.jobs == {}
        assert server.projects.get(project["project_id"])["revisions"][0]["job_id"] is None


def test_sample_ids_and_self_asserted_release_fields_cannot_download_fabrication(tmp_path):
    scene = _forged_scene()
    with _server(tmp_path / "jobs") as (server, base):
        for job_id in [scene["id"], scene["job_id"]]:
            for artifact in ["golden.kicad_pcb", "golden.kicad_sch", "build-package.zip"]:
                path = f"/api/artifacts/{job_id}/{artifact}"
                status, headers, body = _request(base, path + "?verified=true&current=true")
                assert status == 404 and json.loads(body) == {"error": "artifact unavailable"}
                assert headers.get("content-disposition") is None
                status, _, body = _request(base, path, {**server._identity(), **scene})
                assert status == 404 and json.loads(body) == {"error": "not found"}
        assert server.store.jobs == {}
        assert server.projects.list_projects() == []


@pytest.fixture
def controller_web_fixture(tmp_path):
    """HTTP fixtures allow work before final routed scene/posters are captured.

    Only these generated files may be substituted, in the temporary test root.
    The existing all-assets/dependency tests still require every real asset.
    """
    pending = {
        "landing-pcb-controller/candidate-board.json": b'{"kind":"HTTP_TEST_FIXTURE"}\n',
        "landing-pcb-controller/poster-desktop.webp": b"RIFF\x04\x00\x00\x00WEBP",
        "landing-pcb-controller/poster-mobile.webp": b"RIFF\x04\x00\x00\x00WEBP",
    }
    destination = tmp_path / "web"
    for name in server_module.STATIC_ASSETS:
        source, target = server_module.WEB_ROOT / name, destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes() if source.is_file() else pending[name])
    return destination


def test_controller_iframe_alias_and_exact_dependencies_are_served_with_correct_mime(tmp_path, controller_web_fixture):
    expected_types = {
        "index.html": "text/html; charset=utf-8",
        "prototype.css": "text/css; charset=utf-8",
        **{name: "text/javascript; charset=utf-8"
           for name in ("prototype.js", "models.js", "presentation.js", "projection.js")},
        "candidate-board.json": "application/json; charset=utf-8",
        "poster-desktop.webp": "image/webp", "poster-mobile.webp": "image/webp",
    }
    with _server(tmp_path / "jobs", controller_web_fixture) as (server, base):
        for name, mime in expected_types.items():
            path = "/landing-pcb-controller/" + name
            status, headers, body = _request(base, path)
            assert status == 200, path
            assert headers["content-type"] == mime
            assert body == server.static_assets[path]
            assert int(headers["content-length"]) == len(body)
            assert headers["x-ohmni-ui-version"] == server.ui_version
        for path in ("/landing-pcb-controller/", "/landing-pcb-controller/?embed=1"):
            status, headers, body = _request(base, path)
            assert status == 200
            assert headers["content-type"] == "text/html; charset=utf-8"
            assert body == server.static_assets["/landing-pcb-controller/index.html"]
        status, headers, body = _request(base, "/landing-pcb-presentation.js")
        assert status == 200 and body == server.static_assets["/landing-pcb-presentation.js"]
        assert headers["content-type"] == "text/javascript; charset=utf-8"
        status, _, body = _request(base, "/")
        assert status == 200 and body == server.static_assets["/index.html"]


def test_controller_candidate_and_posters_obey_the_immutable_ui_snapshot(tmp_path, controller_web_fixture):
    changed = ("landing-pcb-controller/index.html", "landing-pcb-controller/candidate-board.json",
               "landing-pcb-controller/poster-desktop.webp", "landing-pcb-controller/poster-mobile.webp",
               "landing-pcb-presentation.js")
    with _server(tmp_path / "first", controller_web_fixture) as (first, base):
        original = dict(first.static_assets)
        for name in changed:
            (controller_web_fixture / name).write_bytes(b"changed after server snapshot")
            status, headers, body = _request(base, "/" + name)
            assert status == 200 and body == original["/" + name]
            assert headers["x-ohmni-ui-version"] == first.ui_version
        assert _request(base, "/landing-pcb-controller/?embed=1")[2] == original["/landing-pcb-controller/index.html"]
        with _server(tmp_path / "second", controller_web_fixture) as (second, second_base):
            assert second.ui_version != first.ui_version
            for name in changed:
                assert _request(second_base, "/" + name)[2] == b"changed after server snapshot"


def test_controller_alias_never_expands_to_directory_or_live_file_access(tmp_path, controller_web_fixture):
    secret = b"private-controller-sentinel"
    (controller_web_fixture / "landing-pcb-controller/private.txt").write_bytes(secret)
    with _server(tmp_path / "jobs", controller_web_fixture) as (_, base):
        for path in ("/landing-pcb-controller", "/landing-pcb-controller//",
                     "/landing-pcb-controller/private.txt", "/landing-pcb-controller/../index.html",
                     "/landing-pcb-controller/%2e%2e/index.html", "/landing-pcb-controller/%252e%252e/index.html",
                     "/landing-pcb-controller/..%5cindex.html", "/landing-pcb-controller/models.js/extra",
                     "/landing-pcb-redesign/", "/landing-pcb-prototype/"):
            status, _, body = _request(base, path)
            assert status == 404, path
            assert json.loads(body) == {"error": "not found"}
            assert secret not in body
        status, headers, body = _request(base, "/landing-pcb-controller/?embed=1", method="HEAD")
        assert status == 405 and body == b""
        assert headers["allow"] == "GET, POST, OPTIONS"


@pytest.mark.parametrize("name", ["candidate-board.json", "poster-desktop.webp", "poster-mobile.webp"])
def test_controller_generated_assets_are_required_for_snapshot_startup(controller_web_fixture, name):
    (controller_web_fixture / "landing-pcb-controller" / name).unlink()
    with pytest.raises(server_module.DemoInitializationError):
        server_module._load_web_snapshot(controller_web_fixture)
