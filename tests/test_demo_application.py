"""End-user demo boundaries without duplicating backend engineering decisions."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from ohmni.application import DEMO_REQUEST
from ohmni.application.demo import current_pcb_policy
from scripts import demo_server as demo_server_module
from scripts.demo_server import (
    API_VERSION,
    DEMO_FIXTURE_ID,
    INITIALIZATION_FAILURE_MESSAGE,
    MAX_MODEL_REQUEST_CHARS,
    RUNTIME_FAILURE_MESSAGE,
    STARTUP_FAILURE_MESSAGE,
    STATIC_ASSETS,
    DemoHandler,
    DemoHTTPServer,
    DemoInitializationError,
    JobStore,
)


def _abortive_linger():
    """A zero-timeout SO_LINGER value in this platform's own struct layout.

    `struct linger` is two u_shorts on Windows and two ints everywhere else.
    Sending the wrong width is EINVAL, not a smaller option.
    """
    return struct.pack("hh" if os.name == "nt" else "ii", 1, 0)


def _await_terminal(store,job_id):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        job=store.get(job_id)
        if job["status"] in {"complete","failed"}:return job
        time.sleep(.01)
    return store.get(job_id)


def test_live_demo_endpoint_has_one_owner(tmp_path):
    first=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=JobStore(tmp_path/"first"));port=first.server_port;second=None
    try:
        if hasattr(socket,"SO_EXCLUSIVEADDRUSE"):
            assert not first.allow_reuse_address
            assert first.socket.getsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE)==1
        try:second=DemoHTTPServer(("127.0.0.1",port),DemoHandler,store=JobStore(tmp_path/"second"))
        except OSError:pass
        else:raise AssertionError("a second demo server unexpectedly claimed the live endpoint")
    finally:
        if second is not None:second.server_close()
        first.server_close()


def test_main_bind_failure_is_fixed_actionable_and_sanitized(monkeypatch,capsys):
    secret=r"API_KEY=bind-secret C:\Users\reviewer\private-endpoint"
    class BindFailure:
        def __init__(self,*_args,**_kwargs):raise OSError(secret)
    monkeypatch.setattr(demo_server_module,"DemoHTTPServer",BindFailure)
    assert demo_server_module.main(["--host","127.0.0.1","--port","8765"])==1
    captured=capsys.readouterr()
    assert captured.out==""
    lines=captured.err.splitlines()
    assert json.loads(lines[0])=={
        "api_version":API_VERSION,"component":"ohmni_demo","event":"server_bind_failed",
    }
    assert lines[1]==STARTUP_FAILURE_MESSAGE
    assert secret not in captured.err and "Traceback" not in captured.err


def test_main_separates_initialization_and_runtime_failures(monkeypatch,capsys):
    secret=r"API_KEY=lifecycle-secret C:\Users\reviewer\private-assets"
    class InitFailure:
        def __init__(self,*_args,**_kwargs):raise DemoInitializationError
    monkeypatch.setattr(demo_server_module,"DemoHTTPServer",InitFailure)
    assert demo_server_module.main([])==1
    captured=capsys.readouterr();lines=captured.err.splitlines()
    assert json.loads(lines[0])["event"]=="server_init_failed"
    assert lines[1]==INITIALIZATION_FAILURE_MESSAGE
    class RuntimeFailure:
        server_instance_id="1"*16;ui_version="2"*64
        def __init__(self,*_args,**_kwargs):self.closed=False
        def _job_diagnostic(self,event,**values):
            demo_server_module._diagnostic(
                event,api_version=API_VERSION,server_instance_id=self.server_instance_id,
                ui_version=self.ui_version,**values,
            )
        def serve_forever(self):raise OSError(secret)
        def server_close(self):self.closed=True
    monkeypatch.setattr(demo_server_module,"DemoHTTPServer",RuntimeFailure)
    assert demo_server_module.main([])==1
    captured=capsys.readouterr();lines=captured.err.splitlines()
    assert [json.loads(line)["event"] for line in lines[:-1]]==["server_ready","server_runtime_failed"]
    assert lines[-1]==RUNTIME_FAILURE_MESSAGE
    assert secret not in captured.err and "Traceback" not in captured.err


def test_server_snapshot_is_immutable_and_generation_specific(tmp_path):
    web_root=tmp_path/"web";web_root.mkdir()
    for name in STATIC_ASSETS:
        (web_root/name).write_bytes((demo_server_module.WEB_ROOT/name).read_bytes())
    first=DemoHTTPServer(("127.0.0.1",0),DemoHandler,web_root=web_root,store=JobStore(tmp_path/"first"))
    original=first.static_assets["/app.js"];first_version=first.ui_version
    thread=threading.Thread(target=first.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{first.server_port}"
    try:
        (web_root/"app.js").write_bytes(b"// changed after server initialization")
        with urlopen(base+"/app.js") as response:
            assert response.read()==original
            assert response.headers["x-ohmni-ui-version"]==first_version
        with pytest.raises(TypeError):first.static_assets["/app.js"]=b"mutated"
        second=DemoHTTPServer(("127.0.0.1",0),DemoHandler,web_root=web_root,store=JobStore(tmp_path/"second"))
        try:
            assert second.ui_version!=first_version
            assert second.static_assets["/app.js"]==b"// changed after server initialization"
            assert second.server_instance_id!=first.server_instance_id
            assert second.store is not first.store
        finally:second.server_close()
    finally:
        first.shutdown();first.server_close();thread.join(timeout=2)


def test_async_job_store_reports_actual_progress_without_premature_completion(tmp_path):
    finished=threading.Event()
    progress_value={"stage":"semantic","status":"RUNNING","percent":20,"label":"Checking","detail":{"checks":["original"]}}
    report_value={"result":{"status":"complete","checks":["original"]},"pcb":current_pcb_policy()}
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
    store.jobs[job_id]={"job_id":job_id,"status":"complete","progress":[],"report":{"project":{"status":"READY_FOR_MANUFACTURING_REVIEW"},"schematic":{"fingerprint":digest,"current":True},"pcb":{**current_pcb_policy(),"fingerprint":hashlib.sha256(pcb.read_bytes()).hexdigest(),"source_placed_pcb_fingerprint":hashlib.sha256(placed.read_bytes()).hexdigest(),"current":True},"release":{"status":"READY_FOR_MANUFACTURING_REVIEW","files":[{"relative_path":gerber.name,"sha256":hashlib.sha256(gerber.read_bytes()).hexdigest()}],"manifest":manifest_record,"current":True}},"error":None,"error_code":None}
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
                "error":"Demo pipeline failed","error_code":f"{boundary}_publication_failed" if boundary=="progress" else "pipeline_failed",
            }
    poisoned_id="c"*12;poisoned={};poisoned["self"]=poisoned
    store.jobs[poisoned_id]={"job_id":poisoned_id,"status":"running","progress":[poisoned],"report":None,"error":None,"error_code":None}
    recovered=store.get(poisoned_id)
    assert recovered=={
        "job_id":poisoned_id,"status":"failed","progress":[],"report":None,
        "error":"Demo pipeline failed","error_code":"job_state_invalid",
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
        {"job_id":job_id,"status":[],"progress":[],"report":None,"error":None,"error_code":None},
        {"job_id":job_id,"status":HostileStatus(),"progress":[],"report":None,"error":None,"error_code":None},
        {"job_id":"e"*12,"status":"running","progress":[],"report":None,"error":None,"error_code":None},
        {"job_id":job_id,"status":"complete","progress":[],"report":None,"error":None,"error_code":None},
        {"job_id":job_id,"status":"failed","progress":[],"report":None,"error":secret,"error_code":"pipeline_failed"},
        {"job_id":job_id,"status":"running","progress":[],"report":None,"error":None,"error_code":None,"extra":"unsafe"},
        {"job_id":job_id,"status":"failed","progress":[],"report":None,"error":"Demo pipeline failed","error_code":secret},
    )
    expected={"job_id":job_id,"status":"failed","progress":[],"report":None,"error":"Demo pipeline failed","error_code":"job_state_invalid"}
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
        "error":"Demo pipeline failed","error_code":"job_state_invalid",
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
    assert job["error_code"]=="pipeline_failed"
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
        assert job["error_code"]==(
            "progress_publication_failed" if boundary=="progress" else "pipeline_failed"
        )
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
        assert job["error_code"]=="worker_start_failed"
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
    assert job["error_code"]=="worker_start_failed"


def test_http_contract_binds_job_to_server_and_never_echoes_input(tmp_path,capsys):
    requests_seen=[]
    class Report:
        def model_dump(self,mode=None):return {"result":"canonical request accepted","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):requests_seen.append(request);assert request==DEMO_REQUEST;return Report()
    store=JobStore(tmp_path,Pipeline);server=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=store)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f"http://127.0.0.1:{server.server_address[1]}"
    identity={
        "api_version":API_VERSION,"server_instance_id":server.server_instance_id,
        "ui_version":server.ui_version,
    }
    poll_headers={
        "x-ohmni-api-version":str(API_VERSION),
        "x-ohmni-server-instance":server.server_instance_id,
        "x-ohmni-ui-version":server.ui_version,
    }
    secret=r"API_KEY=review-secret C:\Users\reviewer\private.kicad_pcb"
    def post(payload):
        data=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
        return urlopen(Request(f"{base}/api/demo",data=data,headers={"content-type":"application/json"},method="POST"))
    def rejected(payload,status,error):
        try:post(payload)
        except HTTPError as exc:
            body=exc.read().decode();assert exc.code==status and json.loads(body)=={"error":error}
            return body
        raise AssertionError("unsupported request unexpectedly accepted")
    try:
        with urlopen(f"{base}/api/health") as response:
            assert response.status==200
            # free_text advertises the capability, and says no on a server with
            # no model provider -- which this one is.
            assert json.loads(response.read())=={
                "status":"ready","fixture_id":DEMO_FIXTURE_ID,"free_text":False,**identity}
            assert response.headers["cache-control"]=="no-store"
            assert response.headers["x-ohmni-api-version"]==str(API_VERSION)
            assert response.headers["x-ohmni-server-instance"]==server.server_instance_id
            assert response.headers["x-ohmni-ui-version"]==server.ui_version
        with urlopen(f"{base}/") as response:
            assert response.status==200 and response.read()==server.static_assets["/index.html"]
            assert response.headers["cache-control"]=="no-store"
        assert secret not in rejected(f'{{"request":"{secret}'.encode(),400,"fixture_rejected")
        deep=b'{"request":'+(b'['*1200)+b'0'+(b']'*1200)+b'}'
        rejected(deep,400,"fixture_rejected")
        for payload in (
            {"request":secret},{"request":DEMO_REQUEST+" "},{},{"request":30},
            {"fixture_id":DEMO_FIXTURE_ID+"-mutated"},
            {"fixture_id":DEMO_FIXTURE_ID,"extra":"not allowed"},
            {"fixture_id":DEMO_FIXTURE_ID,"request":DEMO_REQUEST},
            {"request":DEMO_REQUEST,"extra":"not allowed"},
        ):rejected(payload,400,"fixture_rejected")
        rejected({**identity,"fixture_id":DEMO_FIXTURE_ID,"api_version":3},409,"api_version_mismatch")
        rejected({**identity,"fixture_id":DEMO_FIXTURE_ID,"server_instance_id":"0"*16},409,"server_instance_mismatch")
        rejected({**identity,"fixture_id":DEMO_FIXTURE_ID,"ui_version":"0"*64},409,"ui_version_mismatch")
        prefix=json.dumps({"request":DEMO_REQUEST})[:-1]
        for constant in ("NaN","Infinity","-Infinity","1e999"):
            rejected((prefix+f',"extra":{constant}'+'}').encode(),400,"fixture_rejected")
        assert not store.jobs
        original_get=store.get;cycle={};cycle["self"]=cycle
        store.get=lambda job_id:{"job_id":job_id,"unsafe":cycle}
        try:urlopen(Request(f"{base}/api/jobs/{'d'*12}",headers=poll_headers))
        except HTTPError as exc:
            body=exc.read().decode();assert exc.code==500 and json.loads(body)=={"error":"response_unavailable"}
        else:raise AssertionError("unsafe response unexpectedly serialized")
        finally:store.get=original_get
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
        store.get=delayed_get;server.handle_error=observed_handle_error
        client=socket.create_connection(server.server_address)
        client.sendall(b"GET /api/jobs/ffffffffffff HTTP/1.1\r\nHost: localhost\r\n\r\n")
        assert entered.wait(2)
        client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,_abortive_linger());client.close();release.set()
        assert handled.wait(2)
        store.get=original_get;server.handle_error=original_handle_error
        payloads=({"fixture_id":DEMO_FIXTURE_ID,**identity},{"fixture_id":DEMO_FIXTURE_ID},{"request":DEMO_REQUEST})
        for payload in payloads:
            with post(payload) as response:
                accepted=json.loads(response.read());assert response.status==202
                assert accepted.keys()=={"job_id","status","api_version","server_instance_id","ui_version"}
                assert accepted["status"]=="queued" and {key:accepted[key] for key in identity}==identity
            job=_await_terminal(store,accepted["job_id"])
            assert job["status"]=="complete" and job["report"]=={
                "result":"canonical request accepted","pcb":{**current_pcb_policy(),"current":False}}
            with urlopen(Request(f"{base}/api/jobs/{accepted['job_id']}",headers=poll_headers)) as response:
                published=json.loads(response.read())
            assert published["status"]=="complete" and {key:published[key] for key in identity}==identity
        assert requests_seen==[DEMO_REQUEST]*3
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    captured=capsys.readouterr()
    assert "Traceback" not in captured.err and "RecursionError" not in captured.err
    assert "ConnectionResetError" not in captured.err and "BrokenPipeError" not in captured.err
    assert secret not in captured.err and target_secret not in captured.err


def test_server_restart_rejects_stale_generation_and_old_job(tmp_path):
    class Report:
        def model_dump(self,mode=None):return {"result":"complete","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):return Report()
    first_store=JobStore(tmp_path/"first",Pipeline)
    first=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=first_store)
    port=first.server_port
    first_thread=threading.Thread(target=first.serve_forever,daemon=True);first_thread.start()
    first_base=f"http://127.0.0.1:{port}"
    first_identity={
        "fixture_id":DEMO_FIXTURE_ID,"api_version":API_VERSION,
        "server_instance_id":first.server_instance_id,"ui_version":first.ui_version,
    }
    request=Request(
        first_base+"/api/demo",data=json.dumps(first_identity).encode(),
        headers={"content-type":"application/json"},method="POST",
    )
    with urlopen(request) as response:job_id=json.loads(response.read())["job_id"]
    assert job_id in first_store.jobs
    old_headers={
        "x-ohmni-api-version":str(API_VERSION),
        "x-ohmni-server-instance":first.server_instance_id,
        "x-ohmni-ui-version":first.ui_version,
    }
    first.shutdown();first.server_close();first_thread.join(timeout=2)
    second_store=JobStore(tmp_path/"second",Pipeline)
    second=DemoHTTPServer(("127.0.0.1",port),DemoHandler,store=second_store)
    second_thread=threading.Thread(target=second.serve_forever,daemon=True);second_thread.start()
    second_base=f"http://127.0.0.1:{port}"
    try:
        assert second.server_instance_id!=first.server_instance_id
        assert not second_store.jobs and job_id not in second_store.jobs
        try:urlopen(Request(f"{second_base}/api/jobs/{job_id}",headers=old_headers))
        except HTTPError as exc:
            assert exc.code==409 and json.loads(exc.read())=={"error":"server_instance_mismatch"}
        else:raise AssertionError("stale server generation unexpectedly polled an old job")
        new_headers={
            "x-ohmni-api-version":str(API_VERSION),
            "x-ohmni-server-instance":second.server_instance_id,
            "x-ohmni-ui-version":second.ui_version,
        }
        try:urlopen(Request(f"{second_base}/api/jobs/{job_id}",headers=new_headers))
        except HTTPError as exc:
            assert exc.code==404 and json.loads(exc.read())=={"error":"job_not_found"}
        else:raise AssertionError("a restarted server unexpectedly retained an old job")
        for header,value,error in (
            ("x-ohmni-api-version","3","api_version_mismatch"),
            ("x-ohmni-server-instance","0"*16,"server_instance_mismatch"),
            ("x-ohmni-ui-version","0"*64,"ui_version_mismatch"),
        ):
            headers={**new_headers,header:value}
            try:urlopen(Request(f"{second_base}/api/jobs/{job_id}",headers=headers))
            except HTTPError as exc:
                assert exc.code==409 and json.loads(exc.read())=={"error":error}
            else:raise AssertionError(f"mismatched {header} unexpectedly reached the job store")
        with urlopen(second_base+"/") as response:
            assert response.headers["x-ohmni-server-instance"]==second.server_instance_id
            assert response.read()==second.static_assets["/index.html"]
    finally:
        second.shutdown();second.server_close();second_thread.join(timeout=2)


def test_job_start_unavailable_is_fixed_and_diagnostics_fail_safe(tmp_path,capsys,monkeypatch):
    secret=r"API_KEY=start-secret C:\Users\reviewer\private-worker"
    class BrokenStore(JobStore):
        def start(self,request):raise OSError(secret)
    store=BrokenStore(tmp_path);server=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=store)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    payload={
        "fixture_id":DEMO_FIXTURE_ID,"api_version":API_VERSION,
        "server_instance_id":server.server_instance_id,"ui_version":server.ui_version,
    }
    try:
        request=Request(base+"/api/demo",data=json.dumps(payload).encode(),headers={"content-type":"application/json"},method="POST")
        try:urlopen(request)
        except HTTPError as exc:
            assert exc.code==503 and json.loads(exc.read())=={"error":"job_start_unavailable"}
        else:raise AssertionError("failed store unexpectedly started a job")
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
    captured=capsys.readouterr()
    records=[json.loads(line) for line in captured.err.splitlines()]
    assert records[-1]["event"]=="job_start_unavailable"
    assert secret not in captured.err and "Traceback" not in captured.err
    class BrokenStderr:
        def write(self,_value):raise SystemExit(secret)
        def flush(self):raise SystemExit(secret)
    monkeypatch.setattr(demo_server_module.sys,"stderr",BrokenStderr())
    demo_server_module._diagnostic("server_runtime_failed",api_version=API_VERSION)


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
        "pcb":{**current_pcb_policy(),"fingerprint":hashlib.sha256(pcb.read_bytes()).hexdigest(),"source_placed_pcb_fingerprint":hashlib.sha256(placed.read_bytes()).hexdigest(),"current":True},
        "release":{"status":"READY_FOR_MANUFACTURING_REVIEW","files":[{"relative_path":gerber.name,"sha256":hashlib.sha256(gerber.read_bytes()).hexdigest()}],"manifest":{"relative_path":manifest.name,"sha256":hashlib.sha256(manifest.read_bytes()).hexdigest()},"current":True},
    },"error":None,"error_code":None}
    original_read=store.read_artifact
    def mutate_after_verified_read(request_job_id,name):
        state,data=original_read(request_job_id,name)
        if name=="golden.kicad_sch":schematic.write_bytes(b"changed after verified read")
        return state,data
    store.read_artifact=mutate_after_verified_read
    server=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=store)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base}/api/artifacts/{job_id}/golden.kicad_sch") as response:
            assert response.status==200 and response.read()==b"verified schematic"
            assert response.headers["x-content-type-options"]=="nosniff"
            assert response.headers["cache-control"]=="no-store"
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


def test_free_text_is_engineered_only_when_a_model_provider_is_configured(tmp_path):
    """Arbitrary text is a capability, not a contract loosening.

    With no provider configured there is nothing that could answer a request
    nobody scripted, so the fixture contract stays exactly as strict as it has
    always been. A configured provider adds one accepted payload shape; every
    identity check and bound still applies to it.
    """
    requests_seen=[]
    class Report:
        def model_dump(self,mode=None):return {"result":"accepted","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress,provider=None):self.provider=provider
        def run(self,destination,request):requests_seen.append((request,self.provider));return Report()
    def post(server,payload):
        return urlopen(Request(
            f"http://127.0.0.1:{server.server_address[1]}/api/demo",
            data=json.dumps(payload).encode(),
            headers={"content-type":"application/json"},method="POST",
        ))
    free_text="Build a USB-powered CO2 logger with a status light."
    provider=SimpleNamespace(name="configured provider")
    for name,configured in (("strict",None),("open",provider)):
        root=tmp_path/name;root.mkdir()
        store=JobStore(root,Pipeline,provider=configured)
        server=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=store)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        payload={"request":free_text,"api_version":API_VERSION,
                 "server_instance_id":server.server_instance_id,"ui_version":server.ui_version}
        try:
            # The page offers a request box only where one can be answered, so
            # health has to say which kind of server this is.
            with urlopen(f"http://127.0.0.1:{server.server_address[1]}/api/health") as response:
                assert json.loads(response.read())["free_text"] is (configured is not None)
            if configured is None:
                with pytest.raises(HTTPError) as excinfo:post(server,payload)
                assert excinfo.value.code==400
                assert json.loads(excinfo.value.read())=={"error":"fixture_rejected"}
                assert not store.jobs
                continue
            with post(server,payload) as response:
                assert response.status==202
                job_id=json.loads(response.read())["job_id"]
            assert _await_terminal(store,job_id)["status"]=="complete"
            for refused in ("   ","short","x"*(MAX_MODEL_REQUEST_CHARS+1),"drop\ttabs",30):
                with pytest.raises(HTTPError) as excinfo:post(server,{**payload,"request":refused})
                assert excinfo.value.code==400
                assert json.loads(excinfo.value.read())=={"error":"fixture_rejected"}
            with pytest.raises(HTTPError) as excinfo:post(server,{**payload,"ui_version":"0"*64})
            assert excinfo.value.code==409
            assert json.loads(excinfo.value.read())=={"error":"ui_version_mismatch"}
            with pytest.raises(HTTPError) as excinfo:post(server,{**payload,"extra":"not allowed"})
            assert excinfo.value.code==400
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)
    # The scripted fixture never became a model call, and the free-text job was
    # handed the exact text with the configured provider.
    assert requests_seen==[(free_text,provider)]


def test_a_missing_or_blank_key_configures_no_provider(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY",raising=False)
    assert demo_server_module._configured_provider() is None
    monkeypatch.setenv("ANTHROPIC_API_KEY","   ")
    assert demo_server_module._configured_provider() is None


def test_the_brief_endpoint_accepts_free_text_on_the_same_terms_as_a_run(tmp_path):
    """Same gate as /api/demo: a provider, or the fixture contract unchanged."""
    from ohmni.adapters.fakes import RecordingLlmProvider

    free_text="Build a USB-powered CO2 logger with a status light"
    provider=RecordingLlmProvider()
    provider.queue({"project_name":"CO2 logger","description":free_text,
                    "max_input_voltage_v":5.25,"target_logic_voltage_v":3.3})
    root=tmp_path/"brief";root.mkdir()
    store=JobStore(root,provider=provider)
    server=DemoHTTPServer(("127.0.0.1",0),DemoHandler,store=store)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_address[1]}"
    identity={"api_version":API_VERSION,"server_instance_id":server.server_instance_id,
              "ui_version":server.ui_version}
    def post(payload):
        return urlopen(Request(base+"/api/brief",data=json.dumps(payload).encode(),
                               headers={"content-type":"application/json"},method="POST"))
    try:
        with post({"request":free_text,**identity}) as response:
            payload=json.loads(response.read())
        assert response.status==200 and payload.keys()=={"brief","api_version","server_instance_id","ui_version"}
        assert any(free_text in line["value"] or line["value"]=="CO2 logger"
                   for line in payload["brief"]["asked_for"])
        assert not provider._queue
        # The scripted fixture still answers from the scripted responses.
        with post({"fixture_id":DEMO_FIXTURE_ID,**identity}) as response:
            assert json.loads(response.read())["brief"]["asked_for"]
        assert len(provider.calls)==1
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_a_demo_job_is_recorded_in_the_database_with_an_owner(tmp_path):
    """/api/demo used to leave its job belonging to nothing."""
    from ohmni.application import database

    class Report:
        def model_dump(self,mode=None):return {"result":"complete","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):return Report()
    store=JobStore(tmp_path,Pipeline)
    store.enable_persistence()
    job_id=store.start(DEMO_REQUEST)
    _await_terminal(store,job_id)

    owner=store.project_store.job_owner(job_id)
    assert owner["owner_user_id"]==database.LOCAL_USER_ID
    assert owner["project_id"]==database.DEMO_PROJECT_ID
    # The durable copy is the completed one, not the queued envelope it started as.
    assert store.project_store.job(job_id)["status"]=="complete"


def test_polling_serves_the_record_the_database_holds(tmp_path):
    class Report:
        def model_dump(self,mode=None):return {"result":"complete","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):return Report()
    store=JobStore(tmp_path,Pipeline)
    store.enable_persistence()
    job_id=store.start(DEMO_REQUEST)
    assert _await_terminal(store,job_id)["status"]=="complete"

    # Nothing is served from memory that the database does not also hold: drop
    # the row and the poll falls back to the live record rather than inventing
    # a status, which is what a store with no persistence does anyway.
    with store.project_store._connection() as db:
        db.execute("DELETE FROM jobs WHERE job_id=?",(job_id,))
    assert store.get(job_id)["status"]=="complete"


def test_a_job_whose_two_copies_disagree_is_retired_rather_than_served(tmp_path):
    """Neither copy can be trusted once they differ, so neither is published."""
    class Report:
        def model_dump(self,mode=None):return {"result":"complete","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):return Report()
    store=JobStore(tmp_path,Pipeline)
    store.enable_persistence()
    job_id=store.start(DEMO_REQUEST)
    _await_terminal(store,job_id)

    tampered={**store.project_store.job(job_id),"report":{"result":"not what ran"}}
    store.project_store.save_job(tampered)
    job=store.get(job_id)
    assert job["status"]=="failed" and job["error_code"]=="job_state_invalid"
    assert job["report"] is None and job["progress"]==[]
    # The retirement is durable: a restart does not resurrect the disagreement.
    restored=JobStore(tmp_path,Pipeline)
    restored.enable_persistence()
    assert restored.get(job_id)["status"]=="failed"


def test_a_store_without_persistence_still_serves_from_memory(tmp_path):
    """The pure tests and a store before enable_persistence run this path."""
    class Report:
        def model_dump(self,mode=None):return {"result":"complete","pcb":current_pcb_policy()}
    class Pipeline:
        def __init__(self,progress):pass
        def run(self,destination,request):return Report()
    store=JobStore(tmp_path,Pipeline)
    job_id=store.start(DEMO_REQUEST)
    assert store.project_store is None
    assert _await_terminal(store,job_id)["status"]=="complete"
