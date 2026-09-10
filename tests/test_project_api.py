"""Local editable projects: immutable revisions, durable jobs, and honest packages."""

from __future__ import annotations

import hashlib
import io
import json
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from ohmni.application.demo import current_pcb_policy
from ohmni.application.project_store import ProjectStore, ProjectWorkspaceInUseError
from ohmni.catalog import default_catalog
from ohmni.physical.models import PlacementRequest
from ohmni.physical.placement import GeneratedPlacement, generate_placement
from ohmni.synthesis import SynthesisBrief, synthesize_a1
from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore

OPENER = build_opener(ProxyHandler({}))


@contextmanager
def _server(output, store=None):
    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store or JobStore(output))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(base, path, payload=None, headers=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(base + path, data=body, headers=headers or {}, method="POST" if body else "GET")
    try:
        with OPENER.open(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def _wait(store, job_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = store.get(job_id)
        if job["status"] in {"complete", "failed"}:
            return job
        time.sleep(0.01)
    raise AssertionError("job did not terminalize")


def test_projects_create_revise_list_and_reopen_after_restart(tmp_path):
    original = SynthesisBrief(project_name="My room monitor").model_dump(mode="json")
    with _server(tmp_path) as (server, base):
        identity = server._identity()
        status, body = _request(base, "/api/projects", {**identity, "brief": original})
        assert status == 201
        project = body["project"]
        project_id = project["project_id"]
        first = project["revisions"][0]
        assert first["number"] == 1 and first["job_id"] is None
        assert first["brief_fingerprint"] == SynthesisBrief.model_validate(original).fingerprint
        assert first["preview"]["project_name"] == original["project_name"]
        changed = {**original, "project_name": "Desk monitor", "status_led_count": 0}
        status, body = _request(base, f"/api/projects/{project_id}/revisions", {**identity, "brief": changed})
        assert status == 201
        revisions = body["project"]["revisions"]
        assert revisions[0] == first
        assert revisions[1]["number"] == 2
        assert revisions[1]["brief_fingerprint"] != first["brief_fingerprint"]
        assert revisions[1]["brief"]["status_led_count"] == 0
        summaries = _request(base, "/api/projects")[1]["projects"]
        assert summaries[0]["name"] == "Desk monitor"
        assert summaries[0]["revision_count"] == 2
    with _server(tmp_path) as (restarted, base):
        assert restarted.server_instance_id != identity["server_instance_id"]
        status, body = _request(base, f"/api/projects/{project_id}")
        assert status == 200 and body["project"]["revisions"] == revisions
        status, body = _request(base, f"/api/projects/{project_id}/revisions", {**identity, "brief": original})
        assert status == 409 and body["error"] == "server_instance_mismatch"


def test_project_requests_refuse_unsupported_or_untyped_input_without_saving(tmp_path):
    with _server(tmp_path) as (server, base):
        identity = server._identity()
        status, body = _request(base, "/api/projects", {**identity, "brief": {"input_power": "mains"}})
        assert status == 422 and body["error"] == "project_refused"
        assert body["refusal"]["message"] and body["refusal"]["field_paths"]
        for brief in ({"include_programming_header": "false"}, {"status_led_count": "1"},
                      {"project_name": " "}, {"unknown": True}, {"project_name": "x" * 121}, []):
            status, body = _request(base, "/api/projects", {**identity, "brief": brief})
            assert status == 400 and body == {"error": "invalid_project_request"}
        status, body = _request(base, "/api/projects", {"brief": {}})
        assert status == 400
        status, body = _request(base, "/api/projects", {**identity, "brief": {}, "extra": True})
        assert status == 400
        status, body = _request(base, "/api/projects", headers={"X-Ohmni-UI-Version": "0" * 64})
        assert status == 409 and body["error"] == "ui_version_mismatch"
        assert _request(base, "/api/projects")[1]["projects"] == []


def test_revision_run_is_idempotent_and_completed_report_survives_restart(tmp_path, monkeypatch):
    from ohmni.application import projects

    calls = []

    class Report:
        def __init__(self, report):
            self.report = report

        def model_dump(self, mode=None):
            return self.report

    class Pipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, brief):
            calls.append((destination, brief.fingerprint))
            prepared, job_id, _ = _seed_package(destination.parent, destination.name, brief)
            return Report(prepared.jobs[job_id]["report"])

    monkeypatch.setattr(projects, "ProjectPipeline", Pipeline)
    with _server(tmp_path) as (server, base):
        identity = server._identity()
        project = _request(base, "/api/projects", {
            **identity, "brief": {"project_name": "persisted result"}
        })[1]["project"]
        project_id = project["project_id"]
        revision_id = project["revisions"][0]["revision_id"]
        run_path = f"/api/projects/{project_id}/revisions/{revision_id}/run"
        with ThreadPoolExecutor(max_workers=3) as pool:
            responses = list(pool.map(lambda _: _request(base, run_path, identity), range(3)))
        assert all(status == 202 for status, _ in responses)
        assert len({body["job_id"] for _, body in responses}) == 1
        job_id = responses[0][1]["job_id"]
        assert _wait(server.store, job_id)["status"] == "complete"
        assert len(calls) == 1
        saved = _request(base, f"/api/projects/{project_id}")[1]["project"]["revisions"][0]
        assert saved["job_id"] == job_id
    with _server(tmp_path) as (server, base):
        status, body = _request(base, f"/api/jobs/{job_id}")
        assert status == 200 and body["status"] == "complete"
        assert body["report"]["project"]["name"] == "persisted result"
        status, body = _request(base, run_path, server._identity())
        assert status == 202 and body["job_id"] == job_id and body["status"] == "complete"
        assert len(calls) == 1


def test_interrupted_job_fails_explicitly_and_admission_is_bounded(tmp_path, monkeypatch):
    store = JobStore(tmp_path, max_active_jobs=1)
    store.enable_persistence()
    monkeypatch.setattr(store, "_launch", lambda *args: None)
    job_id = store.start("first")
    with pytest.raises(RuntimeError, match="capacity"):
        store.start("second")
    restored = JobStore(tmp_path)
    restored.enable_persistence()
    job = restored.get(job_id)
    assert job["status"] == "failed" and job["error_code"] == "server_restarted"
    assert job["report"] is None and job["progress"] == []


@pytest.mark.parametrize("typed", [True, False])
@pytest.mark.parametrize("failure_code", ["routing_incomplete", "eda_tool_failed"])
def test_pipeline_failure_code_is_owned_persistent_and_retryable(tmp_path, monkeypatch, capsys, typed, failure_code):
    from ohmni.application import projects
    from ohmni.application.demo import EdaToolFailedError, RoutingIncompleteError

    base_error=RoutingIncompleteError if failure_code=="routing_incomplete" else EdaToolFailedError
    class Incomplete(base_error):
        def __str__(self):
            raise AssertionError("The API must never format a routing exception")

    class Pipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, brief):
            if typed:
                raise Incomplete("SECRET C:/private/path")
            error = RuntimeError("SECRET C:/private/path")
            error.code = failure_code
            raise error

    monkeypatch.setattr(projects, "ProjectPipeline", Pipeline)
    expected_code = failure_code if typed else "pipeline_failed"
    with _server(tmp_path) as (server, base):
        project = _request(base, "/api/projects", {**server._identity(), "brief": {}})[1]["project"]
        project_id = project["project_id"]
        revision_id = project["revisions"][0]["revision_id"]
        run_path = f"/api/projects/{project_id}/revisions/{revision_id}/run"
        job_id = _request(base, run_path, server._identity())[1]["job_id"]
        assert _wait(server.store, job_id)["status"] == "failed"
        status, failure = _request(base, f"/api/jobs/{job_id}")
        assert status == 200 and failure["error_code"] == expected_code
        assert failure["error"] == "Demo pipeline failed"
        assert failure["report"] is None and failure["progress"] == []
    with _server(tmp_path) as (server, base):
        status, failure = _request(base, f"/api/jobs/{job_id}")
        assert status == 200 and failure["error_code"] == expected_code
        assert failure["status"] == "failed"
        retry = _request(base, run_path, server._identity())[1]["job_id"]
        assert retry != job_id
        assert _wait(server.store, retry)["error_code"] == expected_code
        assert server.store.get(job_id)["error_code"] == expected_code
    captured = capsys.readouterr()
    assert "SECRET" not in captured.out + captured.err + json.dumps(failure)
    assert "C:/private" not in captured.out + captured.err + json.dumps(failure)


def test_live_workspace_cannot_be_recovered_by_another_server_and_failed_attempt_can_retry(tmp_path, monkeypatch):
    from ohmni.application import projects

    first_store = JobStore(tmp_path)
    monkeypatch.setattr(first_store, "_launch", lambda *args: None)
    with _server(tmp_path, first_store) as (server, base):
        project = _request(base, "/api/projects", {**server._identity(), "brief": {}})[1]["project"]
        project_id = project["project_id"]
        revision_id = project["revisions"][0]["revision_id"]
        path = f"/api/projects/{project_id}/revisions/{revision_id}/run"
        old_job_id = _request(base, path, server._identity())[1]["job_id"]
        with pytest.raises(ProjectWorkspaceInUseError):
            DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=JobStore(tmp_path))
        assert first_store.get(old_job_id)["status"] == "queued"

    class Report:
        def __init__(self, report):
            self.report = report

        def model_dump(self, mode=None):
            return self.report

    class Pipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, brief):
            prepared, job_id, _ = _seed_package(destination.parent, destination.name, brief)
            return Report(prepared.jobs[job_id]["report"])

    monkeypatch.setattr(projects, "ProjectPipeline", Pipeline)
    with _server(tmp_path) as (server, base):
        previous = server.store.get(old_job_id)
        assert previous["status"] == "failed" and previous["error_code"] == "server_restarted"
        status, body = _request(base, path, server._identity())
        assert status == 202 and body["job_id"] != old_job_id
        new_job_id = body["job_id"]
        assert _wait(server.store, new_job_id)["status"] == "complete"
        assert server.store.get(old_job_id) == previous
        revision = _request(base, f"/api/projects/{project_id}")[1]["project"]["revisions"][0]
        assert revision["job_id"] == new_job_id
        assert revision["brief_fingerprint"] == project["revisions"][0]["brief_fingerprint"]
        with server.projects._connection() as db:
            attempts = db.execute("SELECT * FROM revision_jobs ORDER BY attempt").fetchall()
        assert [attempt["job_id"] for attempt in attempts] == [old_job_id, new_job_id]
        assert all(attempt["revision_id"] == revision_id for attempt in attempts)


def test_revision_numbers_remain_unique_under_concurrent_edits(tmp_path):
    store = ProjectStore(tmp_path)
    brief = SynthesisBrief()
    project = store.save_revision(brief.model_dump(mode="json"), brief.fingerprint, {"name": "preview"})
    project_id = project["project_id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: store.save_revision(
            brief.model_dump(mode="json"), brief.fingerprint, {"name": "preview"}, project_id
        ), range(8)))
    revisions = store.get(project_id)["revisions"]
    assert [revision["number"] for revision in revisions] == list(range(1, 10))
    assert len({revision["revision_id"] for revision in revisions}) == 9


def _seed_package(tmp_path, job_id="a" * 12, brief=None):
    directory = tmp_path / job_id
    fabrication = directory / "fabrication"
    fabrication.mkdir(parents=True)
    fingerprints = {}
    for name in ("golden.kicad_sch", "golden.kicad_pcb", "golden.placed.kicad_pcb"):
        data = f"checked {name}".encode()
        (directory / name).write_bytes(data)
        fingerprints[name] = hashlib.sha256(data).hexdigest()
    files = []
    for kind, extension in (("F.Cu", "gtl"), ("B.Cu", "gbl"), ("F.Mask", "gts"), ("B.Mask", "gbs"),
                            ("F.Silkscreen", "gto"), ("B.Silkscreen", "gbo"), ("Edge.Cuts", "gm1"), ("Drill", "drl")):
        name = "golden." + extension
        data = f"checked {kind}".encode()
        (fabrication / name).write_bytes(data)
        files.append({"relative_path": name, "sha256": hashlib.sha256(data).hexdigest(),
                      "size_bytes": len(data), "kind": kind})
    manifest = {"pcb_fingerprint": fingerprints["golden.kicad_pcb"],
                "schematic_fingerprint": fingerprints["golden.kicad_sch"],
                "files": files, "release_status": "ready_for_manufacturing_review"}
    if brief is not None:
        result = synthesize_a1(brief)
        placement = generate_placement(result.circuit, result.placement_request, default_catalog())
        manifest["circuit_fingerprint"] = result.circuit.content_hash
    package_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    manifest["package_fingerprint"] = package_hash
    data = json.dumps(manifest).encode()
    manifest_name = "ohmni-fabrication-manifest.json"
    (fabrication / manifest_name).write_bytes(data)
    report = {
        "project": {"name": "A reviewable board", "status": "READY_FOR_MANUFACTURING_REVIEW"},
        "schematic": {"fingerprint": fingerprints["golden.kicad_sch"], "current": True},
        "pcb": {**current_pcb_policy(),"fingerprint": fingerprints["golden.kicad_pcb"], "current": True,
                "source_schematic_fingerprint": fingerprints["golden.kicad_sch"],
                "source_placed_pcb_fingerprint": fingerprints["golden.placed.kicad_pcb"]},
        "release": {"status": "READY_FOR_MANUFACTURING_REVIEW", "current": True, "files": files,
                    "pcb_fingerprint": fingerprints["golden.kicad_pcb"], "package_fingerprint": package_hash,
                    "manifest": {"relative_path": manifest_name, "sha256": hashlib.sha256(data).hexdigest()}},
        "bom": {"lines": [{"references": ["U3"], "part": "BME280", "description": "=unsafe formula",
                           "quantity": 1, "unit_price": None, "knowledge": "UNKNOWN"}]},
        "assembly": {"risks": [], "limitations": ["Review the package before assembly."]},
        "experience": {"bring_up": [{"action": "Measure the sensor supply", "prediction": "3.3 V",
                                     "basis": "typed rail", "rule_id": "PB-PWR-001"}]},
        "limitations": ["Not bench verified."],
    }
    if brief is not None:
        report["mode"] = "bounded_synthesis"
        report["project"].update(name=brief.project_name, brief_fingerprint=brief.fingerprint,
                                 circuit_hash=manifest["circuit_fingerprint"],
                                 placement_request_fingerprint=placement.request_fingerprint)
        report["pcb"]["placement"] = {
            "algorithm": placement.algorithm, "request_fingerprint": placement.request_fingerprint,
            "constraints_hash": placement.board.content_hash,
            "metrics": placement.metrics.model_dump(mode="json"), "limitations": list(placement.limitations),
        }
        report["pcb"]["quality_metrics"] = {
            "constraints_hash": placement.board.content_hash,
            "source_pcb_fingerprint": fingerprints["golden.kicad_pcb"],
        }
    store = JobStore(tmp_path)
    store.jobs[job_id] = {"job_id": job_id, "status": "complete", "progress": [], "report": report,
                          "error": None, "error_code": None}
    return store, job_id, directory


def test_build_package_contains_exact_release_and_actionable_honest_handoff(tmp_path):
    store, job_id, directory = _seed_package(tmp_path)
    state, data = store.read_build_package(job_id)
    assert state == "current"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        assert len(names) == 15
        assert {"report.json", "bom.csv", "ASSEMBLY-AND-BRINGUP.md", "golden.placed.kicad_pcb"} <= set(names)
        assert archive.read("golden.kicad_pcb") == (directory / "golden.kicad_pcb").read_bytes()
        assert archive.read("fabrication/golden.drl") == (directory / "fabrication/golden.drl").read_bytes()
        guide = archive.read("ASSEMBLY-AND-BRINGUP.md").decode()
        assert "Firmware is not included" in guide and "synthetic" in guide
        assert "Measured result: __________" in guide and "Not bench verified." in guide
        bom = archive.read("bom.csv").decode("utf-8-sig")
        assert "'=unsafe formula" in bom and "UNKNOWN" in bom
    with _server(tmp_path, store) as (_, base), OPENER.open(
        f"{base}/api/artifacts/{job_id}/build-package.zip"
    ) as response:
        assert response.headers["content-type"] == "application/zip"
        assert zipfile.is_zipfile(io.BytesIO(response.read()))


@pytest.mark.parametrize("target", ["golden.kicad_sch", "golden.kicad_pcb", "golden.placed.kicad_pcb",
                                    "fabrication/golden.gtl", "fabrication/ohmni-fabrication-manifest.json"])
def test_build_package_refuses_any_changed_source_or_release_file(tmp_path, target):
    store, job_id, directory = _seed_package(tmp_path)
    (directory / target).write_bytes(b"changed after verification")
    state, data = store.read_build_package(job_id)
    assert state == "stale" and data is None


def test_build_package_refuses_missing_files_and_mismatched_lineage(tmp_path):
    store, job_id, directory = _seed_package(tmp_path)
    report = store.jobs[job_id]["report"]
    report["release"]["pcb_fingerprint"] = "0" * 64
    assert store.read_build_package(job_id) == ("stale", None)
    report["release"]["pcb_fingerprint"] = report["pcb"]["fingerprint"]
    (directory / "fabrication/golden.drl").unlink()
    assert store.read_build_package(job_id)[1] is None
    assert store.read_build_package("../" + job_id)[1] is None


def test_personal_build_package_includes_saved_input_and_refuses_changed_revision_binding(tmp_path):
    brief = SynthesisBrief(project_name="My revision", status_led_count=0)
    store, job_id, _ = _seed_package(tmp_path, brief=brief)
    durable = ProjectStore(tmp_path)
    project = durable.save_revision(brief.model_dump(mode="json"), brief.fingerprint, {})
    revision_id = project["revisions"][0]["revision_id"]
    durable.claim_job(project["project_id"], revision_id, JobStore._queued_record(job_id))
    durable.save_job(store.jobs[job_id])
    store.project_store = durable
    state, data = store.read_build_package(job_id)
    assert state == "current"
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        saved = json.loads(archive.read("confirmed-brief.json"))
        revision = json.loads(archive.read("project-revision.json"))
        assert saved == brief.model_dump(mode="json")
        assert revision["revision_id"] == revision_id and revision["job_id"] == job_id
        assert revision["brief_fingerprint"] == SynthesisBrief.model_validate(saved).fingerprint
        assert revision["circuit_fingerprint"] == synthesize_a1(brief).circuit.content_hash
        request_bytes = archive.read("placement-request.json")
        placement_bytes = archive.read("placement.json")
        request = PlacementRequest.model_validate_json(request_bytes)
        placement = GeneratedPlacement.model_validate_json(placement_bytes)
        assert request.content_hash == placement.request_fingerprint == revision["placement_request_fingerprint"]
        assert request.circuit_content_hash == placement.circuit_content_hash == revision["circuit_fingerprint"]
        assert placement.board.content_hash == revision["board_constraints_hash"]
        assert placement.algorithm == revision["placement_algorithm"]
        assert revision["placement_documents"] == {
            "placement-request.json": hashlib.sha256(request_bytes).hexdigest(),
            "placement.json": hashlib.sha256(placement_bytes).hexdigest(),
        }
    report = store.jobs[job_id]["report"]
    report["project"]["brief_fingerprint"] = "0" * 64
    assert store.read_build_package(job_id) == ("unavailable", None)
    assert store.get(job_id)["status"] == "failed"


def _personal_package(tmp_path):
    brief = SynthesisBrief(project_name="Geometry-bound revision")
    store, job_id, directory = _seed_package(tmp_path, brief=brief)
    durable = ProjectStore(tmp_path)
    project = durable.save_revision(brief.model_dump(mode="json"), brief.fingerprint, {})
    revision_id = project["revisions"][0]["revision_id"]
    durable.claim_job(project["project_id"], revision_id, JobStore._queued_record(job_id))
    durable.save_job(store.jobs[job_id])
    store.project_store = durable
    return store, job_id, directory, project["project_id"], revision_id


@pytest.mark.parametrize("field,missing", [
    (("project", "placement_request_fingerprint"), True),
    (("project", "placement_request_fingerprint"), False),
    (("pcb", "placement"), True),
    (("pcb", "placement", "request_fingerprint"), False),
    (("pcb", "placement", "constraints_hash"), False),
    (("pcb", "placement", "algorithm"), False),
    (("pcb", "quality_metrics", "constraints_hash"), False),
    (("pcb", "quality_metrics", "source_pcb_fingerprint"), False),
])
def test_old_or_mismatched_personal_geometry_retires_publication_and_every_download(tmp_path, field, missing):
    store, job_id, directory, _, _ = _personal_package(tmp_path)
    report = store.jobs[job_id]["report"]
    target = report
    for key in field[:-1]:
        target = target[key]
    if missing:
        del target[field[-1]]
    else:
        target[field[-1]] = "0" * 64
    before = (directory / "golden.kicad_pcb").read_bytes()
    job = store.get(job_id)
    assert job["status"] == "failed" and job["error_code"] == "job_state_invalid"
    assert job["report"] is None and job["progress"] == []
    assert store.read_artifact(job_id, "golden.kicad_pcb")[1] is None
    assert store.read_artifact(job_id, "golden.kicad_sch")[1] is None
    assert store.read_build_package(job_id)[1] is None
    # Retiring publication does not rewrite historical copper or invent fresh
    # report metadata. The failure survives recovery as a retryable attempt.
    assert (directory / "golden.kicad_pcb").read_bytes() == before
    restored = JobStore(tmp_path)
    restored.enable_persistence()
    assert restored.get(job_id) == job


def test_stale_completed_geometry_can_retry_without_first_polling(tmp_path, monkeypatch):
    store, job_id, _, project_id, revision_id = _personal_package(tmp_path)
    del store.jobs[job_id]["report"]["pcb"]["placement"]
    store.project_store.save_job(store.jobs[job_id])
    launched = []
    monkeypatch.setattr(store, "_launch", lambda *args: launched.append(args))
    next_job = store.start_revision(project_id, revision_id)
    assert next_job != job_id and len(launched) == 1
    assert store.get(job_id)["status"] == "failed"
    assert store.get(next_job)["status"] == "queued"
    assert store.project_store.revision(project_id, revision_id)["job_id"] == next_job
    with store.project_store._connection() as db:
        attempts = db.execute("SELECT job_id FROM revision_jobs ORDER BY attempt").fetchall()
    assert [attempt["job_id"] for attempt in attempts] == [job_id, next_job]


def test_current_geometry_is_cached_immutably_and_recomputed_after_store_restart(tmp_path, monkeypatch):
    from scripts import demo_server

    derive = demo_server._derive_project_geometry
    calls = []
    def counted(brief_json):
        calls.append(brief_json)
        return derive(brief_json)
    monkeypatch.setattr(demo_server, "_derive_project_geometry", counted)
    store, job_id, _, _, _ = _personal_package(tmp_path)
    assert store.get(job_id)["status"] == "complete"
    assert store.get(job_id)["report"]["pcb"]["current"] is True
    assert store.read_artifact(job_id, "golden.kicad_pcb")[0] == "current"
    assert store.read_build_package(job_id)[0] == "current"
    assert len(calls) == 1 and store._expected_project_geometry.cache_info().hits >= 3
    assert store._expected_project_geometry.cache_info().maxsize == 128
    expected = store._expected_project_geometry(calls[0])
    assert isinstance(expected, tuple) and isinstance(expected.request_bytes, bytes)
    with pytest.raises(AttributeError):
        expected.constraints_hash = "0" * 64
    restored = JobStore(tmp_path)
    restored.enable_persistence()
    assert restored.get(job_id)["status"] == "complete" and len(calls) == 2


@pytest.mark.parametrize("wrong_field", [
    ("project", "brief_fingerprint"), ("project", "circuit_hash"),
    ("project", "placement_request_fingerprint"), ("pcb", "placement", "constraints_hash"),
    ("pcb", "placement", "algorithm"), ("pcb", "placement"),
])
def test_project_worker_cannot_publish_report_for_different_input(tmp_path, monkeypatch, wrong_field):
    from ohmni.application import projects

    class Report:
        def __init__(self, report):
            self.report = report

        def model_dump(self, mode=None):
            return self.report

    class Pipeline:
        def __init__(self, progress):
            pass

        def run(self, destination, brief):
            prepared, job_id, _ = _seed_package(destination.parent, destination.name, brief)
            report = prepared.jobs[job_id]["report"]
            target = report
            for key in wrong_field[:-1]:
                target = target[key]
            target[wrong_field[-1]] = "0" * 64
            return Report(report)

    monkeypatch.setattr(projects, "ProjectPipeline", Pipeline)
    with _server(tmp_path) as (server, base):
        project = _request(base, "/api/projects", {**server._identity(), "brief": {}})[1]["project"]
        revision_id = project["revisions"][0]["revision_id"]
        path = f"/api/projects/{project['project_id']}/revisions/{revision_id}/run"
        job_id = _request(base, path, server._identity())[1]["job_id"]
        job = _wait(server.store, job_id)
        assert job["status"] == "failed" and job["report"] is None
        assert job["error_code"] == "pipeline_failed"


def test_exercise_endpoint_runs_actual_verifier_and_does_not_save_a_project(tmp_path):
    with _server(tmp_path) as (server, base):
        identity = server._identity()
        status, body = _request(base, "/api/exercises/sensor-rail")
        assert status == 200 and {item["id"] for item in body["exercise"]["choices"]} == {
            "leave_5v", "move_vdd", "move_both"
        }
        wrong = _request(base, "/api/exercises/sensor-rail", {**identity, "choice": "move_vdd"})[1]["result"]
        fixed = _request(base, "/api/exercises/sensor-rail", {**identity, "choice": "move_both"})[1]["result"]
        assert wrong["correct"] is False and fixed["correct"] is True
        assert wrong["after"]["circuit_hash"] != fixed["after"]["circuit_hash"]
        assert fixed["evidence"] and fixed["limitation"]
        assert _request(base, "/api/projects")[1]["projects"] == []
        status, body = _request(base, "/api/exercises/sensor-rail", {**identity, "choice": "invented"})
        assert status == 400 and body["error"] == "invalid_exercise_choice"
