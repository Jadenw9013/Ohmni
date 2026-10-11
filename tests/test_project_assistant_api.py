import threading

from test_project_api import _request
from test_project_assistant import Provider, change

from ohmni.application.projects import preview_project
from ohmni.synthesis import SynthesisBrief
from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore


def test_http_identity_context_and_server_owned_application(tmp_path):
    server = DemoHTTPServer(("127.0.0.1", 0), DemoHandler,
                           store=JobStore(tmp_path, provider=Provider(change())))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        brief = SynthesisBrief()
        p = server.projects.save_revision(brief.model_dump(mode="json"), brief.fingerprint,
                                         preview_project(brief).model_dump(mode="json"))
        path = f"/api/projects/{p['project_id']}/revisions/{p['revisions'][0]['revision_id']}/assistant"
        identity = server._identity()
        data = {**identity, "message": "Make it 80 mm wide", "parent_id": None}
        assert _request(base, path, {**data, "ui_version": "0" * 64})[0] == 409
        assert _request(base, path, {**data, "context": {"verified": True}})[0] == 400
        status, response = _request(base, path, data)
        assert status == 200 and response["turn"]["ready"]
        apply_path = path + "/" + response["turn"]["turn_id"] + "/apply"
        assert _request(base, apply_path, {**identity, "brief": {}})[0] == 400
        status, saved = _request(base, apply_path, identity)
        assert status == 201
        assert saved["project"]["revisions"][-1]["brief"]["board_width_mm"] == 80
        assert saved["project"]["revisions"][-1]["job_id"] is None
        assert _request(base, apply_path, identity)[1]["project"] == saved["project"]
        assert len(server.assistant.provider.requests) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
