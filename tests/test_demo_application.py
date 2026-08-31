"""End-user demo boundaries without duplicating backend engineering decisions."""

from __future__ import annotations

import hashlib
import json
import socket
import struct
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ohmni.application import DEMO_REQUEST
from scripts.demo_server import DemoHandler, DemoHTTPServer, JobStore


def _await_terminal(store,job_id):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        job=store.get(job_id)
        if job["status"] in {"complete","failed"}:return job
        time.sleep(.01)
    return store.get(job_id)


def test_async_job_store_reports_actual_progress_without_premature_completion(tmp_path):
    finished=threading.Event()
    progress_value={"stage":"semantic","status":"RUNNING","percent":20,"label":"Checking","detail":{"checks":["original"]}}
    report_value={"result":{"status":"complete","checks":["original"]}}
    class Report:
        def model_dump(self,mode=None):return report_value
    class Pipeline:
        def __init__(self,progress):self.progress=progress
        def run(self,destination,request):
            self.progress(SimpleNamespace(model_dump=lambda mode=None:progress_value))
            finished.set();return Report()
    store=JobStore(tmp_path,Pipeline);job_id=store.start("supported request")
    assert finished.wait(timeout=2)
    for _ in range(100):
        job=store.get(job_id)
        if job["status"]=="complete":break
        finished.wait(.01)
    assert job["status"]=="complete"
    assert job["progress"][0]["status"]=="RUNNING"
    assert job["report"]["result"]["status"]=="complete"
    progress_value["detail"]["checks"].append("source mutation")
    report_value["result"]["checks"].append("source mutation")
    job["progress"][0]["detail"]["checks"].append("snapshot mutation")
    job["report"]["result"]["checks"].append("snapshot mutation")
    fresh=store.get(job_id)
    assert fresh["progress"][0]["detail"]["checks"]==["original"]
    assert fresh["report"]["result"]["checks"]==["original"]
    store._fail(job_id)
    assert store.get(job_id)["status"]=="complete"


def test_artifact_download_freshness_is_hash_bound(tmp_path):
    job_id="a"*12;path=tmp_path/job_id/"golden.kicad_sch";path.parent.mkdir();path.write_text("exact")
    pcb=path.parent/"golden.kicad_pcb";pcb.write_text("pcb")
    placed=path.parent/"golden.placed.kicad_pcb";placed.write_text("placed")
    fabrication=path.parent/"fabrication";fabrication.mkdir();gerber=fabrication/"golden-F_Cu.gtl";gerber.write_text("gerber")
    manifest=fabrication/"ohmni-fabrication-manifest.json";manifest.write_text("manifest")
    digest=hashlib.sha256(path.read_bytes()).hexdigest();store=JobStore(tmp_path)
    manifest_record={"relative_path":manifest.name,"sha256":hashlib.sha256(manifest.read_bytes()).hexdigest()}
    store.jobs[job_id]={"job_id":job_id,"status":"complete","progress":[],"report":{"project":{"status":"READY_FOR_MANUFACTURING_REVIEW"},"schematic":{"fingerprint":digest,"current":True},"pcb":{"fingerprint":hashlib.sha256(pcb.read_bytes()).hexdigest(),"source_placed_pcb_fingerprint":hashlib.sha256(placed.read_bytes()).hexdigest(),"current":True},"release":{"status":"READY_FOR_MANUFACTURING_REVIEW","files":[{"relative_path":gerber.name,"sha256":hashlib.sha256(gerber.read_bytes()).hexdigest()}],"manifest":manifest_record,"current":True}},"error":None}
    state,data=store.read_artifact(job_id,"golden.kicad_sch")
    assert state=="current" and data==b"exact"
    fresh=store.get(job_id)
    assert fresh["report"]["pcb"]["current"] and fresh["report"]["release"]["current"]
    assert fresh["report"]["release"]["status"]=="READY_FOR_MANUFACTURING_REVIEW"
    gerber.write_text("changed gerber")
    stale=store.get(job_id)["report"]
    assert not stale["release"]["current"] and stale["release"]["status"]=="STALE"
    assert stale["project"]["status"]=="STALE"
    gerber.write_text("gerber")
    assert store.get(job_id)["report"]["release"]["status"]=="READY_FOR_MANUFACTURING_REVIEW"
    manifest.write_text("changed manifest")
    stale=store.get(job_id)["report"]
    assert not stale["release"]["current"] and stale["release"]["status"]=="STALE"
    manifest.write_text("manifest")
    manifest.unlink()
    assert store.get(job_id)["report"]["release"]["status"]=="STALE"
    manifest.write_text("manifest")
    store.jobs[job_id]["report"]["release"].pop("manifest")
    assert store.get(job_id)["report"]["release"]["status"]=="STALE"
    store.jobs[job_id]["report"]["release"]["manifest"]=manifest_record
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


def test_unexpected_worker_exception_becomes_safe_terminal_failure(tmp_path,caplog,monkeypatch,capsys):
    touched=[]
    class Hostile:
        def __str__(self):touched.append("str");raise SystemExit("sensitive-test-value")
        def __repr__(self):touched.append("repr");raise SystemExit("sensitive-test-value")
    class CustomDict(dict):
        def items(self):touched.append("items");raise SystemExit("sensitive-test-value")
    class CustomList(list):pass
    cycle={};cycle["cycle"]=cycle
    invalid_values=(
        [],
        CustomDict(result="unsafe"),
        {"nested":Hostile()},
        {"nested":CustomList(["unsafe"])},
        cycle,
        {"number":float("nan")},
        {"number":float("inf")},
    )
    class SafeReport:
        def model_dump(self,mode=None):return {"result":"must not publish"}
    def pipeline_for(boundary,value):
        class Pipeline:
            def __init__(self,progress):self.progress=progress
            def run(self,destination,request):
                if boundary=="progress":
                    self.progress(SimpleNamespace(model_dump=lambda mode=None:value));return SafeReport()
                self.progress(SimpleNamespace(model_dump=lambda mode=None:{"stage":"semantic","status":"RUNNING"}))
                return SimpleNamespace(model_dump=lambda mode=None:value)
        return Pipeline
    for boundary in ("progress","report"):
        for value in invalid_values:
            store=JobStore(tmp_path,pipeline_for(boundary,value))
            job=_await_terminal(store,store.start("supported request"))
            assert job=={
                "job_id":job["job_id"],"status":"failed","progress":[],"report":None,
                "error":"Demo pipeline failed",
            }
    poisoned_id="c"*12;poisoned={};poisoned["self"]=poisoned
    store.jobs[poisoned_id]={"job_id":poisoned_id,"status":"running","progress":[poisoned],"report":None,"error":None}
    recovered=store.get(poisoned_id)
    assert recovered=={
        "job_id":poisoned_id,"status":"failed","progress":[],"report":None,
        "error":"Demo pipeline failed",
    }
    recovered["progress"].append({"unsafe":"snapshot mutation"})
    assert store.jobs[poisoned_id]["progress"]==[]
    assert store.get(poisoned_id)["progress"]==[]
    secret=r"API_KEY=status-secret C:\Users\reviewer\private-board.kicad_pcb";hook_calls=[]
    monkeypatch.setattr(threading,"excepthook",lambda args:hook_calls.append(args))
    class HostileStatus:
        def __hash__(self):touched.append("status-hash");raise SystemExit(secret)
        def __eq__(self,other):touched.append("status-eq");raise SystemExit(secret)
        def __str__(self):touched.append("status-str");raise SystemExit(secret)
        def __repr__(self):touched.append("status-repr");raise SystemExit(secret)
    envelope_store=JobStore(tmp_path)
    job_id="d"*12
    invalid_records=(
        {"job_id":job_id,"status":[],"progress":[],"report":None,"error":None},
        {"job_id":job_id,"status":HostileStatus(),"progress":[],"report":None,"error":None},
        {"job_id":"e"*12,"status":"running","progress":[],"report":None,"error":None},
        {"job_id":job_id,"status":"complete","progress":[],"report":None,"error":None},
        {"job_id":job_id,"status":"failed","progress":[],"report":None,"error":secret},
        {"job_id":job_id,"status":"running","progress":[],"report":None,"error":None,"extra":"unsafe"},
    )
    expected={"job_id":job_id,"status":"failed","progress":[],"report":None,"error":"Demo pipeline failed"}
    for invalid in invalid_records:
        envelope_store.jobs[job_id]=invalid
        envelope_store._fail(job_id)
        stored=envelope_store.jobs[job_id];recovered=envelope_store.get(job_id)
        assert stored==expected and recovered==expected and stored is not invalid and recovered is not stored
        assert recovered["progress"] is not stored["progress"]
        assert envelope_store.read_artifact(job_id,"golden.kicad_sch")==('unavailable',None)
        assert envelope_store.get(job_id)==expected
    class PoisonPipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):
            with envelope_store.lock:envelope_store.jobs[next(iter(envelope_store.jobs))]["status"]=HostileStatus()
            return SafeReport()
    envelope_store=JobStore(tmp_path,PoisonPipeline)
    assert _await_terminal(envelope_store,envelope_store.start("supported request"))=={
        "job_id":next(iter(envelope_store.jobs)),"status":"failed","progress":[],"report":None,
        "error":"Demo pipeline failed",
    }
    assert not touched and not hook_calls and "sensitive-test-value" not in caplog.text and secret not in caplog.text
    captured=capsys.readouterr();assert "Traceback" not in captured.err and secret not in captured.err


def test_expected_worker_exception_never_discloses_local_path(tmp_path,caplog):
    private_path=r"C:\Users\reviewer\private-board.kicad_pcb"
    class Pipeline:
        def __init__(self,progress):self.progress=progress
        def run(self,destination,request):
            self.progress(SimpleNamespace(model_dump=lambda mode=None:{"stage":"semantic","status":"RUNNING"}))
            raise FileNotFoundError(private_path)
    store=JobStore(tmp_path,Pipeline)
    job=_await_terminal(store,store.start("supported request"))
    assert job["status"]=="failed" and job["report"] is None and not job["progress"]
    assert job["error"]=="Demo pipeline failed"
    assert private_path not in caplog.text and private_path not in json.dumps(job)


def test_exception_string_failure_still_becomes_terminal(tmp_path,capsys,monkeypatch):
    secret=r"API_KEY=base-secret C:\Users\reviewer\private-board.kicad_pcb";hook_calls=[]
    monkeypatch.setattr(threading,"excepthook",lambda args:hook_calls.append(args))
    touched=[]
    class BrokenString(BaseException):
        def __str__(self):touched.append("str");raise SystemExit("format-failed")
        def __repr__(self):touched.append("repr");raise SystemExit("repr-failed")
    def pipeline_for(boundary):
        class Pipeline:
            def __init__(self,progress):self.progress=progress
            def run(self,destination,request):
                if boundary=="worker":raise BrokenString(secret)
                if boundary=="progress":
                    self.progress(SimpleNamespace(model_dump=lambda mode=None:(_ for _ in ()).throw(BrokenString(secret))))
                    return SimpleNamespace(model_dump=lambda mode=None:{"result":"must not publish"})
                self.progress(SimpleNamespace(model_dump=lambda mode=None:{"stage":"semantic","status":"RUNNING"}))
                return SimpleNamespace(model_dump=lambda mode=None:(_ for _ in ()).throw(BrokenString(secret)))
        return Pipeline
    for boundary in ("worker","progress","report"):
        store=JobStore(tmp_path,pipeline_for(boundary));job=_await_terminal(store,store.start("supported request"))
        assert job["status"]=="failed" and job["report"] is None and not job["progress"]
        assert job["error"]=="Demo pipeline failed"
    assert not touched and not hook_calls and secret not in json.dumps(job)
    captured=capsys.readouterr();assert "Traceback" not in captured.err and "format-failed" not in captured.err


def test_worker_launch_failures_create_pollable_terminal_jobs(tmp_path,monkeypatch,caplog):
    class BrokenLaunch(BaseException):
        def __str__(self):raise SystemExit("launch formatter escaped")
        def __repr__(self):raise SystemExit("launch repr escaped")
    class ConstructionFailure:
        def __init__(self,*args,**kwargs):raise BrokenLaunch()
    class StartFailure:
        def __init__(self,*args,**kwargs):pass
        def start(self):raise BrokenLaunch()
    store=JobStore(tmp_path)
    for worker in (ConstructionFailure,StartFailure):
        monkeypatch.setattr("scripts.demo_server.threading.Thread",worker)
        job_id=store.start("supported request");job=store.get(job_id)
        assert job["job_id"]==job_id and job["status"]=="failed" and job["report"] is None
        assert job["error"]=="Demo pipeline failed"
    assert not caplog.records


def test_launch_failure_is_absorbing_if_worker_already_started(tmp_path,monkeypatch):
    entered=threading.Event();release=threading.Event();returned=threading.Event();dumped=threading.Event();real_thread=threading.Thread
    class Report:
        def model_dump(self,mode=None):dumped.set();return {"result":"should not publish"}
    class Pipeline:
        def __init__(self,progress):self.progress=progress
        def run(self,destination,request):
            self.progress(SimpleNamespace(model_dump=lambda mode=None:{"stage":"semantic","status":"RUNNING"}))
            entered.set();release.wait(2);returned.set();return Report()
    class StartsThenRaises:
        def __init__(self,*args,**kwargs):self.worker=real_thread(*args,**kwargs)
        def start(self):self.worker.start();assert entered.wait(2);raise RuntimeError("launch failed after start")
    monkeypatch.setattr("scripts.demo_server.threading.Thread",StartsThenRaises)
    store=JobStore(tmp_path,Pipeline);job_id=store.start("supported request")
    assert store.get(job_id)["status"]=="failed"
    release.set();assert returned.wait(2) and not dumped.is_set()
    job=store.get(job_id)
    assert job["status"]=="failed" and not job["progress"] and job["report"] is None
    assert job["error"]=="Demo pipeline failed"


def test_malformed_post_body_never_echoes_input(tmp_path,capsys):
    class Report:
        def model_dump(self,mode=None):return {"result":"canonical request accepted"}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):assert request==DEMO_REQUEST;return Report()
    DemoHandler.store=JobStore(tmp_path,Pipeline);server=DemoHTTPServer(("127.0.0.1",0),DemoHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f"http://127.0.0.1:{server.server_address[1]}"
    secret=r"API_KEY=review-secret C:\Users\reviewer\private.kicad_pcb"
    try:
        malformed=f'{{"request":"{secret}'.encode()
        request=Request(f"{base}/api/demo",data=malformed,headers={"content-type":"application/json"},method="POST")
        try:urlopen(request)
        except HTTPError as exc:
            body=exc.read().decode();assert exc.code==400 and json.loads(body)=={"error":"invalid request"}
        else:raise AssertionError("malformed request unexpectedly accepted")
        assert secret not in body
        deep=b'{"request":'+(b'['*1200)+b'0'+(b']'*1200)+b'}'
        request=Request(f"{base}/api/demo",data=deep,headers={"content-type":"application/json"},method="POST")
        try:urlopen(request)
        except HTTPError as exc:
            body=exc.read().decode();assert exc.code==400 and json.loads(body)=={"error":"invalid request"}
        else:raise AssertionError("deep request unexpectedly accepted")
        assert not DemoHandler.store.jobs
        for payload in ({"request":secret},{"request":DEMO_REQUEST+" "},{},{"request":30}):
            unsupported=Request(f"{base}/api/demo",data=json.dumps(payload).encode(),headers={"content-type":"application/json"},method="POST")
            try:urlopen(unsupported)
            except HTTPError as exc:
                body=exc.read().decode();assert exc.code==400 and json.loads(body)=={"error":"invalid request"}
            else:raise AssertionError("unsupported request unexpectedly accepted")
            assert secret not in body and not DemoHandler.store.jobs
        prefix=json.dumps({"request":DEMO_REQUEST})[:-1]
        for constant in ("NaN","Infinity","-Infinity","1e999"):
            nonfinite=Request(f"{base}/api/demo",data=(prefix+f',"extra":{constant}'+'}').encode(),headers={"content-type":"application/json"},method="POST")
            try:urlopen(nonfinite)
            except HTTPError as exc:
                body=exc.read().decode();assert exc.code==400 and json.loads(body)=={"error":"invalid request"}
            else:raise AssertionError("nonfinite JSON unexpectedly accepted")
            assert not DemoHandler.store.jobs
        original_get=DemoHandler.store.get;cycle={};cycle["self"]=cycle
        DemoHandler.store.get=lambda job_id:{"job_id":job_id,"unsafe":cycle}
        try:urlopen(f"{base}/api/jobs/{'d'*12}")
        except HTTPError as exc:
            body=exc.read().decode();assert exc.code==500 and json.loads(body)=={"error":"response unavailable"}
        else:raise AssertionError("unsafe response unexpectedly serialized")
        finally:DemoHandler.store.get=original_get
        target_secret="API_KEY=request-target-secret-C-Users-reviewer-private.kicad_pcb"
        target=f"http://[::1/?{target_secret}"
        with socket.create_connection(server.server_address) as client:
            client.sendall(f"GET {target} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode())
            response=b""
            while chunk:=client.recv(4096):response+=chunk
        headers,body=response.split(b"\r\n\r\n",1)
        assert b" 400 " in headers.splitlines()[0]
        assert json.loads(body)=={"error":"invalid path"} and target_secret.encode() not in body
        entered=threading.Event();release=threading.Event();handled=threading.Event()
        original_handle_error=server.handle_error
        def delayed_get(job_id):entered.set();release.wait(2);return original_get(job_id)
        def observed_handle_error(request,address):handled.set();return original_handle_error(request,address)
        DemoHandler.store.get=delayed_get;server.handle_error=observed_handle_error
        client=socket.create_connection(server.server_address)
        client.sendall(b"GET /api/jobs/ffffffffffff HTTP/1.1\r\nHost: localhost\r\n\r\n")
        assert entered.wait(2)
        client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack("hh",1,0));client.close();release.set()
        assert handled.wait(2)
        DemoHandler.store.get=original_get;server.handle_error=original_handle_error
        canonical=Request(f"{base}/api/demo",data=json.dumps({"request":DEMO_REQUEST}).encode(),headers={"content-type":"application/json"},method="POST")
        with urlopen(canonical) as response:
            accepted=json.loads(response.read());assert response.status==202
        job=_await_terminal(DemoHandler.store,accepted["job_id"])
        assert job["status"]=="complete" and job["report"]=={"result":"canonical request accepted"}
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    captured=capsys.readouterr()
    assert "Traceback" not in captured.err and "RecursionError" not in captured.err
    assert "ConnectionResetError" not in captured.err and "BrokenPipeError" not in captured.err
    assert secret not in captured.err and target_secret not in captured.err


def test_http_download_serves_verified_buffer_and_rejects_alternate_paths(tmp_path):
    job_id="b"*12;directory=tmp_path/job_id;directory.mkdir()
    schematic=directory/"golden.kicad_sch";schematic.write_bytes(b"verified schematic")
    pcb=directory/"golden.kicad_pcb";pcb.write_bytes(b"verified pcb")
    placed=directory/"golden.placed.kicad_pcb";placed.write_bytes(b"verified placed")
    fabrication=directory/"fabrication";fabrication.mkdir()
    gerber=fabrication/"golden-F_Cu.gtl";gerber.write_bytes(b"verified gerber")
    manifest=fabrication/"ohmni-fabrication-manifest.json";manifest.write_bytes(b"verified manifest")
    store=JobStore(tmp_path)
    store.jobs[job_id]={"job_id":job_id,"status":"complete","progress":[],"report":{
        "project":{"status":"READY_FOR_MANUFACTURING_REVIEW"},
        "schematic":{"fingerprint":hashlib.sha256(schematic.read_bytes()).hexdigest(),"current":True},
        "pcb":{"fingerprint":hashlib.sha256(pcb.read_bytes()).hexdigest(),"source_placed_pcb_fingerprint":hashlib.sha256(placed.read_bytes()).hexdigest(),"current":True},
        "release":{"status":"READY_FOR_MANUFACTURING_REVIEW","files":[{"relative_path":gerber.name,"sha256":hashlib.sha256(gerber.read_bytes()).hexdigest()}],"manifest":{"relative_path":manifest.name,"sha256":hashlib.sha256(manifest.read_bytes()).hexdigest()},"current":True},
    },"error":None}
    original_read=store.read_artifact
    def mutate_after_verified_read(request_job_id,name):
        state,data=original_read(request_job_id,name)
        if name=="golden.kicad_sch":schematic.write_bytes(b"changed after verified read")
        return state,data
    store.read_artifact=mutate_after_verified_read
    DemoHandler.store=store;server=DemoHTTPServer(("127.0.0.1",0),DemoHandler)
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
        assert not refreshed["report"]["release"]["current"]
        assert refreshed["report"]["release"]["status"]=="STALE"
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
