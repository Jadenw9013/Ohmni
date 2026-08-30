"""End-user demo boundaries without duplicating backend engineering decisions."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

from scripts.demo_server import DemoHandler, JobStore


def test_async_job_store_reports_actual_progress_without_premature_completion(tmp_path):
    finished=threading.Event()
    class Report:
        def model_dump(self,mode=None):return {"release":{"status":"READY_FOR_MANUFACTURING_REVIEW"}}
    class Pipeline:
        def __init__(self,progress):self.progress=progress
        def run(self,destination,request):
            self.progress(SimpleNamespace(model_dump=lambda mode=None:{"stage":"semantic","status":"RUNNING","percent":20,"label":"Checking","detail":""}))
            finished.set();return Report()
    store=JobStore(tmp_path,Pipeline);job_id=store.start("supported request")
    assert finished.wait(timeout=2)
    for _ in range(100):
        job=store.get(job_id)
        if job["status"]=="complete":break
        finished.wait(.01)
    assert job["status"]=="complete"
    assert job["progress"][0]["status"]=="RUNNING"
    assert job["report"]["release"]["status"]=="READY_FOR_MANUFACTURING_REVIEW"


def test_artifact_download_freshness_is_hash_bound(tmp_path):
    job_id="a"*12;path=tmp_path/job_id/"golden.kicad_sch";path.parent.mkdir();path.write_text("exact")
    pcb=path.parent/"golden.kicad_pcb";pcb.write_text("pcb")
    placed=path.parent/"golden.placed.kicad_pcb";placed.write_text("placed")
    fabrication=path.parent/"fabrication";fabrication.mkdir();gerber=fabrication/"golden-F_Cu.gtl";gerber.write_text("gerber")
    digest=hashlib.sha256(path.read_bytes()).hexdigest();store=JobStore(tmp_path)
    store.jobs[job_id]={"status":"complete","report":{"schematic":{"fingerprint":digest,"current":True},"pcb":{"fingerprint":hashlib.sha256(pcb.read_bytes()).hexdigest(),"source_placed_pcb_fingerprint":hashlib.sha256(placed.read_bytes()).hexdigest(),"current":True},"release":{"files":[{"relative_path":gerber.name,"sha256":hashlib.sha256(gerber.read_bytes()).hexdigest()}],"current":True}}}
    state,data=store.read_artifact(job_id,"golden.kicad_sch")
    assert state=="current" and data==b"exact"
    fresh=store.get(job_id)
    assert fresh["report"]["pcb"]["current"] and fresh["report"]["release"]["current"]
    gerber.write_text("changed gerber")
    assert not store.get(job_id)["report"]["release"]["current"]
    gerber.write_text("gerber")
    placed.write_text("changed placed")
    assert not store.get(job_id)["report"]["pcb"]["current"]
    placed.write_text("placed")
    path.write_text("changed")
    assert data==b"exact"
    assert store.read_artifact(job_id,"golden.kicad_sch")==('stale',None)
    refreshed=store.get(job_id)
    assert not refreshed["report"]["schematic"]["current"]
    assert not refreshed["report"]["pcb"]["current"]
    assert store.read_artifact(job_id,"../golden.kicad_sch")==('unavailable',None)
    assert store.read_artifact(job_id,"missing.txt")==('unavailable',None)


def test_unexpected_worker_exception_becomes_safe_terminal_failure(tmp_path):
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):raise KeyError("sensitive-test-value")
    store=JobStore(tmp_path,Pipeline);job_id=store.start("supported request")
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        job=store.get(job_id)
        if job["status"]=="failed":break
        time.sleep(.01)
    assert job["status"]=="failed" and job["report"] is None and not job["progress"]
    assert "KeyError" in job["error"] and "sensitive-test-value" not in job["error"]


def test_http_download_serves_verified_buffer_and_rejects_alternate_paths(tmp_path):
    job_id="b"*12;directory=tmp_path/job_id;directory.mkdir()
    schematic=directory/"golden.kicad_sch";schematic.write_bytes(b"verified schematic")
    pcb=directory/"golden.kicad_pcb";pcb.write_bytes(b"verified pcb")
    placed=directory/"golden.placed.kicad_pcb";placed.write_bytes(b"verified placed")
    store=JobStore(tmp_path)
    store.jobs[job_id]={"status":"complete","report":{
        "schematic":{"fingerprint":hashlib.sha256(schematic.read_bytes()).hexdigest(),"current":True},
        "pcb":{"fingerprint":hashlib.sha256(pcb.read_bytes()).hexdigest(),"source_placed_pcb_fingerprint":hashlib.sha256(placed.read_bytes()).hexdigest(),"current":True},
        "release":{"files":[],"current":True},
    }}
    original_read=store.read_artifact
    def mutate_after_verified_read(request_job_id,name):
        state,data=original_read(request_job_id,name)
        if name=="golden.kicad_sch":schematic.write_bytes(b"changed after verified read")
        return state,data
    store.read_artifact=mutate_after_verified_read
    DemoHandler.store=store;server=ThreadingHTTPServer(("127.0.0.1",0),DemoHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base}/api/artifacts/{job_id}/golden.kicad_sch") as response:
            assert response.status==200 and response.read()==b"verified schematic"
            assert response.headers["x-content-type-options"]=="nosniff"
        store.read_artifact=original_read
        with urlopen(f"{base}/api/jobs/{job_id}") as response:
            refreshed=json.loads(response.read())
        assert not refreshed["report"]["schematic"]["current"]
        assert not refreshed["report"]["pcb"]["current"]
        for path in (
            f"/api/artifacts/{job_id}/missing.txt",
            f"/api/artifacts/{job_id}/%2e%2e%2fgolden.kicad_sch",
            f"/api/artifacts/{job_id}/golden.kicad_sch/extra",
            "/.git/config",
        ):
            try:urlopen(base+path)
            except HTTPError as exc:assert exc.code in {400,404}
            else:raise AssertionError(f"unsafe path unexpectedly served: {path}")
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
