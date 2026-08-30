#!/usr/bin/env python3
"""Serve the local Ohmni deterministic demo with asynchronous real pipeline jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ohmni.application import DEMO_REQUEST, DemoPipeline

ROOT=Path(__file__).resolve().parents[1];WEB_ROOT=ROOT/"apps"/"web";OUTPUT_ROOT=ROOT/"out"/"demo-jobs"


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
            with self.lock:self.jobs[job_id].update(status="failed",error=str(exc))
    def get(self,job_id):
        with self.lock:return json.loads(json.dumps(self.jobs.get(job_id))) if job_id in self.jobs else None
    def artifact_is_current(self,job_id,name,path):
        job=self.get(job_id)
        if not job or job["status"]!="complete" or not path.is_file():return False
        expected={"golden.kicad_sch":job["report"]["schematic"]["fingerprint"],"golden.kicad_pcb":job["report"]["pcb"]["fingerprint"]}.get(name)
        return bool(expected) and hashlib.sha256(path.read_bytes()).hexdigest()==expected


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
        if self.path.startswith("/api/jobs/"):
            job=self.store.get(self.path.removeprefix("/api/jobs/"));return self._json(job if job else {"error":"job not found"},HTTPStatus.OK if job else HTTPStatus.NOT_FOUND)
        if self.path.startswith("/api/artifacts/"):
            parts=self.path.split("/")
            if len(parts)!=5:return self._json({"error":"invalid artifact path"},HTTPStatus.BAD_REQUEST)
            job_id,name=parts[3],parts[4];job=self.store.get(job_id)
            if not job or job["status"]!="complete":return self._json({"error":"artifact unavailable"},HTTPStatus.NOT_FOUND)
            base=(self.store.output_root/job_id).resolve();path=(base/name).resolve()
            if path.parent!=base or not path.is_file():return self._json({"error":"artifact not found"},HTTPStatus.NOT_FOUND)
            if not self.store.artifact_is_current(job_id,name,path):return self._json({"error":"artifact is stale or not associated with this report"},HTTPStatus.CONFLICT)
            data=path.read_bytes();self.send_response(HTTPStatus.OK);self.send_header("content-type","application/octet-stream");self.send_header("content-disposition",f'attachment; filename="{path.name}"');self.send_header("content-length",str(len(data)));self.end_headers();self.wfile.write(data);return
        super().do_GET()


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8765);args=parser.parse_args(argv)
    OUTPUT_ROOT.mkdir(parents=True,exist_ok=True);DemoHandler.store=JobStore();server=ThreadingHTTPServer((args.host,args.port),DemoHandler);print(f"Ohmni demo: http://{args.host}:{args.port}")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0
if __name__=="__main__":raise SystemExit(main())
