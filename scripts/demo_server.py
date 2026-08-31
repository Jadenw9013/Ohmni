#!/usr/bin/env python3
"""Serve the local Ohmni deterministic demo with asynchronous real pipeline jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import threading
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from ohmni.application import DEMO_REQUEST, DemoPipeline

ROOT=Path(__file__).resolve().parents[1];WEB_ROOT=ROOT/"apps"/"web";OUTPUT_ROOT=ROOT/"out"/"demo-jobs"
ARTIFACT_SECTIONS={"golden.kicad_sch":"schematic","golden.kicad_pcb":"pcb"}
JOB_ID_PATTERN=re.compile(r"^[0-9a-f]{12}$")
DEMO_FAILURE_MESSAGE="Demo pipeline failed"
INVALID_REQUEST_MESSAGE="invalid request"
TERMINAL_JOB_STATUSES={"complete","failed"}


class JobStore:
    def __init__(self,output_root:Path=OUTPUT_ROOT,pipeline_factory=DemoPipeline):self.output_root=output_root;self.pipeline_factory=pipeline_factory;self.jobs={};self.lock=threading.Lock()
    def start(self,request:str)->str:
        job_id=uuid.uuid4().hex[:12]
        with self.lock:self.jobs[job_id]={"job_id":job_id,"status":"queued","progress":[],"report":None,"error":None}
        try:threading.Thread(target=self._run,args=(job_id,request),daemon=True).start()
        except Exception:  # noqa: BLE001 - the launch boundary must always terminalize the job
            self._fail(job_id)
        return job_id
    def _fail(self,job_id):
        with self.lock:
            job=self.jobs[job_id]
            if job["status"] not in TERMINAL_JOB_STATUSES:job.update(status="failed",report=None,error=DEMO_FAILURE_MESSAGE)
    def _run(self,job_id,request):
        def progress(event):
            value=event.model_dump(mode="json")
            with self.lock:
                job=self.jobs[job_id]
                if job["status"] not in TERMINAL_JOB_STATUSES:job["progress"].append(value);job["status"]="running"
        with self.lock:
            if self.jobs[job_id]["status"] in TERMINAL_JOB_STATUSES:return
        try:
            report=self.pipeline_factory(progress).run(self.output_root/job_id,request)
            value=report.model_dump(mode="json")
            with self.lock:
                job=self.jobs[job_id]
                if job["status"] not in TERMINAL_JOB_STATUSES:job.update(status="complete",report=value)
        except Exception:  # noqa: BLE001 - the worker boundary must always terminalize the job
            self._fail(job_id)
    def _snapshot(self,job_id):
        with self.lock:return json.loads(json.dumps(self.jobs.get(job_id))) if job_id in self.jobs else None
    def _job_directory(self,job_id):
        if not JOB_ID_PATTERN.fullmatch(job_id):return None
        try:root=self.output_root.resolve();directory=(root/job_id).resolve()
        except (OSError,RuntimeError):return None
        return directory if directory.parent==root and directory.name==job_id else None
    @staticmethod
    def _expected_digest(job,name):
        try:expected=job["report"][ARTIFACT_SECTIONS[name]]["fingerprint"]
        except (KeyError,TypeError):return None
        return expected if isinstance(expected,str) and re.fullmatch(r"[0-9a-f]{64}",expected) else None
    @staticmethod
    def _read_matching(path,expected,parent):
        try:
            if path.is_symlink():return "unavailable",None
            resolved=path.resolve()
            if resolved.parent!=parent or not resolved.is_file():return "missing",None
            data=resolved.read_bytes()
        except (OSError,RuntimeError):return "missing",None
        return ("current",data) if hashlib.sha256(data).hexdigest()==expected else ("stale",None)
    def _read_artifact_snapshot(self,job_id,name,job):
        if name not in ARTIFACT_SECTIONS or not job or job.get("status")!="complete":return "unavailable",None
        directory=self._job_directory(job_id);expected=self._expected_digest(job,name)
        if directory is None or expected is None:return "unavailable",None
        return self._read_matching(directory/name,expected,directory)
    def read_artifact(self,job_id,name):
        return self._read_artifact_snapshot(job_id,name,self._snapshot(job_id))
    def _release_file_current(self,parent,item,expected_name=None):
        if parent is None or not isinstance(item,dict):return False
        relative=item.get("relative_path");expected=item.get("sha256")
        if not isinstance(relative,str) or Path(relative).name!=relative:return False
        if expected_name is not None and relative!=expected_name:return False
        if not isinstance(expected,str) or not re.fullmatch(r"[0-9a-f]{64}",expected):return False
        return self._read_matching(parent/relative,expected,parent)[0]=="current"
    def get(self,job_id):
        job=self._snapshot(job_id)
        if not job or job.get("status")!="complete":return job
        report=job.get("report")
        if not isinstance(report,dict):return job
        schematic_state,_=self._read_artifact_snapshot(job_id,"golden.kicad_sch",job)
        pcb_state,_=self._read_artifact_snapshot(job_id,"golden.kicad_pcb",job)
        schematic_current=schematic_state=="current";pcb_file_current=pcb_state=="current"
        schematic=report.get("schematic");pcb=report.get("pcb")
        if isinstance(schematic,dict):schematic["current"]=schematic_current
        placed_expected=pcb.get("source_placed_pcb_fingerprint") if isinstance(pcb,dict) else None
        placed_current=True
        directory=self._job_directory(job_id)
        if placed_expected is not None and directory is not None:
            placed_current=self._read_matching(
                directory/"golden.placed.kicad_pcb",placed_expected,directory,
            )[0]=="current"
        pcb_current=pcb_file_current and schematic_current and placed_current
        if isinstance(pcb,dict):pcb["current"]=pcb_current
        fabrication=directory/"fabrication" if directory is not None else None
        release=report.get("release")
        if isinstance(release,dict):
            files=release.get("files")
            files_current=isinstance(files,list) and bool(files) and all(
                self._release_file_current(fabrication,item) for item in files
            )
            manifest_current=self._release_file_current(
                fabrication,release.get("manifest"),"ohmni-fabrication-manifest.json",
            )
            release_current=pcb_current and files_current and manifest_current
            release["current"]=release_current
            if not release_current:
                release["status"]="STALE"
                project=report.get("project")
                if isinstance(project,dict):project["status"]="STALE"
        return job

class DemoHandler(SimpleHTTPRequestHandler):
    store:JobStore
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(WEB_ROOT),**kwargs)
    def _json(self,value:Any,status=HTTPStatus.OK):
        body=json.dumps(value).encode();self.send_response(status);self.send_header("content-type","application/json");self.send_header("content-length",str(len(body)));self.send_header("cache-control","no-store");self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.path!="/api/demo":return self._json({"error":"not found"},HTTPStatus.NOT_FOUND)
        try:
            length=int(self.headers.get("content-length","0"))
            if length<0 or length>16_384:raise ValueError
            payload=json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload,dict):raise TypeError
            raw_request=payload.get("request",DEMO_REQUEST)
            if not isinstance(raw_request,str):raise TypeError
            request=raw_request.strip()
        except (TypeError,ValueError):return self._json({"error":INVALID_REQUEST_MESSAGE},HTTPStatus.BAD_REQUEST)
        if not request or len(request)>4000:return self._json({"error":"request must contain 1 to 4000 characters"},HTTPStatus.BAD_REQUEST)
        self._json({"job_id":self.store.start(request),"status":"queued"},HTTPStatus.ACCEPTED)
    def do_GET(self):
        request_path=unquote(urlsplit(self.path).path)
        if request_path.startswith("/api/jobs/"):
            job_id=request_path.removeprefix("/api/jobs/")
            if "/" in job_id:return self._json({"error":"invalid job path"},HTTPStatus.BAD_REQUEST)
            job=self.store.get(job_id);return self._json(job if job else {"error":"job not found"},HTTPStatus.OK if job else HTTPStatus.NOT_FOUND)
        if request_path.startswith("/api/artifacts/"):
            parts=request_path.split("/")
            if len(parts)!=5:return self._json({"error":"invalid artifact path"},HTTPStatus.BAD_REQUEST)
            job_id,name=parts[3],parts[4];state,data=self.store.read_artifact(job_id,name)
            if state in {"unavailable","missing"}:return self._json({"error":"artifact unavailable"},HTTPStatus.NOT_FOUND)
            if state!="current" or data is None:return self._json({"error":"artifact is stale or not associated with this report"},HTTPStatus.CONFLICT)
            self.send_response(HTTPStatus.OK);self.send_header("content-type","application/octet-stream");self.send_header("x-content-type-options","nosniff");self.send_header("cache-control","no-store");self.send_header("content-disposition",f'attachment; filename="{name}"');self.send_header("content-length",str(len(data)));self.end_headers();self.wfile.write(data);return
        super().do_GET()


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8765);args=parser.parse_args(argv)
    OUTPUT_ROOT.mkdir(parents=True,exist_ok=True);DemoHandler.store=JobStore();server=ThreadingHTTPServer((args.host,args.port),DemoHandler);print(f"Ohmni demo: http://{args.host}:{args.port}")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0
if __name__=="__main__":raise SystemExit(main())
