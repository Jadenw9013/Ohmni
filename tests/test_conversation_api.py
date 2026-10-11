"""HTTP identity, server-owned confirmation and exact revision-run handoff."""
import threading
from contextlib import contextmanager

from test_conversation import Provider, output
from test_project_api import _request, _wait

from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore


@contextmanager
def server_at(path):
    store = JobStore(path, provider=Provider(output()))
    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler, store=store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_plan_confirm_is_identity_bound_and_ignores_no_client_edits(tmp_path, monkeypatch):
    with server_at(tmp_path) as (server, base):
        identity = server._identity()
        data = {**identity, "message": "A USB temperature and humidity board", "parent_id": None}
        assert _request(base, "/api/project-plans", {**data, "ui_version": "0"*64})[0] == 409
        status, body = _request(base, "/api/project-plans", data)
        assert status == 200
        plan = body["plan"]
        path = f"/api/project-plans/{plan['plan_id']}/confirm"
        assert _request(base, path, {**identity, "brief": plan["brief"]})[0] == 400
        assert _request(base, path, {**identity, "server_instance_id": "0"*16})[0] == 409
        status, body = _request(base, path, identity)
        assert status == 201
        project = body["project"]
        revision = project["revisions"][0]
        assert revision["brief_fingerprint"] == plan["brief_fingerprint"]
        assert _request(base, path, identity)[1]["project"]["project_id"] == project["project_id"]
        launched = []
        def start(project_id, revision_id):
            launched.append((project_id, revision_id))
            return "abcdef123456"
        monkeypatch.setattr(server.store, "start_revision", start)
        monkeypatch.setattr(server.store, "get", lambda _: {"status": "queued"})
        assert _request(base, f"/api/projects/{project['project_id']}/revisions/{revision['revision_id']}/run", identity)[0] == 202
        assert launched == [(project["project_id"], revision["revision_id"])]
        assert len(server.planner.provider.requests) == 1


def test_a_configured_model_never_enters_the_saved_revision_pipeline(tmp_path, monkeypatch):
    from ohmni.application.projects import ProjectPipeline

    invoked = []
    def run(self, destination, brief):
        invoked.append(brief)
        raise RuntimeError("intentional stop before native tools")
    monkeypatch.setattr(ProjectPipeline, "run", run)
    with server_at(tmp_path) as (server, _base):
        plan = server.planner.propose("A USB temperature and humidity board")
        project = server.planner.confirm(plan["plan_id"])
        revision = project["revisions"][0]
        job_id = server.store.start_revision(project["project_id"], revision["revision_id"])
        assert _wait(server.store, job_id)["status"] == "failed"
        assert len(invoked) == 1
        assert invoked[0].fingerprint == revision["brief_fingerprint"]
        assert len(server.planner.provider.requests) == 1
