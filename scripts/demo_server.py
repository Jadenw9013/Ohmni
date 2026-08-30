#!/usr/bin/env python3
"""Serve the local Ohmni deterministic demo with asynchronous real pipeline jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
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
LOGGER=logging.getLogger(__name__)


class JobStore:
    def __init__(self,output_root:Path=OUTPUT_ROOT,pipeline_factory=DemoPipeline):self.output_root=output_root;self.pipeline_factory=pipeline_factory;self.jobs={};self.lock=threading.Lock()
    def start(self,request:str)->str:
        job_id=uuid.uuid4().hex[:12]
        with self.lock:self.jobs[job_id]={"job_id":job_id,"status":"queued","progress":[],"report":None,"error":None}
        threading.Thread(target=self._run,args=(job_id,request),daemon=True).start();return job_id
    def _run(self,job_id,request):
        def progress(event):
            with self.lock:self.jobs[job_id]["progress"].append(event.model_dump(mode="json"));self.jobs[job_id]["status"]="running"
        try:
            report=self.pipeline_factory(progress).run(self.output_root/job_id,request)
            with self.lock:self.jobs[job_id].update(status="complete",report=report.model_dump(mode="json"))
        except (OSError, RuntimeError, ValueError) as exc:
            with self.lock:
                self.jobs[job_id].update(status="failed",error=str(exc))
        except Exception as exc:
            LOGGER.exception("unexpected demo pipeline failure for job %s", job_id)
            with self.lock:
                self.jobs[job_id].update(
                    status="failed",
                    error=f"Unexpected demo pipeline failure ({type(exc).__name__})",
                )
    def _snapshot(self,job_id):
        with self.lock:return json.loads(json.dumps(self.jobs.get(job_id))) if job_id in self.jobs else None
    def _job_directory(self,job_id):
        if not JOB_ID_PATTERN.fullmatch(job_id):return None
        root=self.output_root.resolve();directory=(root/job_id).resolve()
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
        except OSError:return "missing",None
        return ("current",data) if hashlib.sha256(data).hexdigest()==expected else ("stale",None)
    def _read_artifact_snapshot(self,job_id,name,job):
        if name not in ARTIFACT_SECTIONS or not job or job.get("status")!="complete":return "unavailable",None
        directory=self._job_directory(job_id);expected=self._expected_digest(job,name)
        if directory is None or expected is None:return "unavailable",None
        return self._read_matching(directory/name,expected,directory)
    def read_artifact(self,job_id,name):
        return self._read_artifact_snapshot(job_id,name,self._snapshot(job_id))
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
        files_current=True
        fabrication=directory/"fabrication" if directory is not None else None
        release=report.get("release")
        for item in release.get("files",[]) if isinstance(release,dict) else []:
            relative=item.get("relative_path");expected=item.get("sha256")
            if not fabrication or not isinstance(relative,str) or Path(relative).name!=relative or not isinstance(expected,str):
                files_current=False;break
            if self._read_matching(fabrication/relative,expected,fabrication)[0]!="current":
                files_current=False;break
        if isinstance(release,dict) and "current" in release:
            release["current"]=pcb_current and files_current
        return job

class DemoHandler(SimpleHTTPRequestHandler):
    store:JobStore
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(WEB_ROOT),**kwargs)
    def _json(self,value:Any,status=HTTPStatus.OK):
        body=json.dumps(value).encode();self.send_response(status);self.send_header("content-type","application/json");self.send_header("content-length",str(len(body)));self.send_header("cache-control","no-store");self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.path!="/api/demo":return self._json({"error":"not found"},HTTPStatus.NOT_FOUND)
        try:
            length=int(self.headers.get("content-length","0"));payload=json.loads(self.rfile.read(min(length,16_384)) or b"{}");request=str(payload.get("request",DEMO_REQUEST)).strip()
            if not request or len(request)>4000:raise ValueError("request must contain 1 to 4000 characters")
        except (ValueError,json.JSONDecodeError) as exc:return self._json({"error":str(exc)},HTTPStatus.BAD_REQUEST)
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
