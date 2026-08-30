"""End-user demo boundaries without duplicating backend engineering decisions."""

from __future__ import annotations

import hashlib
import threading
from types import SimpleNamespace

from scripts.demo_server import JobStore


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
    path=tmp_path/"job"/"golden.kicad_sch";path.parent.mkdir();path.write_text("exact")
    digest=hashlib.sha256(path.read_bytes()).hexdigest();store=JobStore(tmp_path)
    store.jobs["job"]={"status":"complete","report":{"schematic":{"fingerprint":digest},"pcb":{"fingerprint":"b"*64}}}
    assert store.artifact_is_current("job","golden.kicad_sch",path)
    path.write_text("changed")
    assert not store.artifact_is_current("job","golden.kicad_sch",path)
