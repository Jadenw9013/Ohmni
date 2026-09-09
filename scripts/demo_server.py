#!/usr/bin/env python3
"""Serve the local Ohmni deterministic demo with asynchronous real pipeline jobs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import socket
import sys
import threading
import uuid
import zipfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import unquote, urlsplit

from ohmni.application import DEMO_REQUEST, DemoPipeline, preview_brief
from ohmni.application.project_store import (
    PROJECT_ID_PATTERN,
    ProjectStore,
    ProjectWorkspaceInUseError,
    ProjectWorkspaceLock,
)

ROOT=Path(__file__).resolve().parents[1];WEB_ROOT=ROOT/"apps"/"web";OUTPUT_ROOT=ROOT/"out"/"demo-jobs"
ARTIFACT_SECTIONS={"golden.kicad_sch":"schematic","golden.kicad_pcb":"pcb"}
JOB_ID_PATTERN=re.compile(r"^[0-9a-f]{12}$")
INSTANCE_ID_PATTERN=re.compile(r"^[0-9a-f]{16}$")
UI_VERSION_PATTERN=re.compile(r"^[0-9a-f]{64}$")
API_VERSION=2
DEMO_FAILURE_MESSAGE="Demo pipeline failed"
DEMO_FIXTURE_ID="esp32-bme280-environmental-logger"
INVALID_PATH_MESSAGE="invalid path"
UNAVAILABLE_RESPONSE_MESSAGE="response_unavailable"
BRIEF_UNAVAILABLE_MESSAGE="brief_unavailable"
STARTUP_FAILURE_MESSAGE="Ohmni demo could not start. Stop any existing demo server or retry with a different --port."
INITIALIZATION_FAILURE_MESSAGE="Ohmni demo could not initialize its fixed local assets. Restore the repository files and retry."
RUNTIME_FAILURE_MESSAGE="Ohmni demo stopped unexpectedly. Restart the server and reload the browser."
WORKSPACE_IN_USE_MESSAGE="Ohmni workspace is already in use. Stop its local server before opening the same workspace again."
JOB_RECORD_FIELDS={"job_id","status","progress","report","error","error_code"}
JOB_STATUSES={"queued","running","complete","failed"}
TERMINAL_JOB_STATUSES={"complete","failed"}
JOB_FAILURE_CODES={"worker_start_failed","pipeline_failed","progress_publication_failed","job_state_invalid","server_restarted"}
STATIC_ASSETS=("index.html","app.js","view-model.js","board-model.js","board-view.js",
               "schematic-view.js","client-contract.js","reference-preview.js",
               "board-renderer-geometry.js","board-renderer-webgl.js","board-controls.js",
               "learning-model.js","circuit-lessons.js","circuit-lab.js",
               "project-workbench.js","project-contract.js",
               "reference-board.json","styles.css")
STATIC_CONTENT_TYPES={
    "index.html":"text/html; charset=utf-8",
    "styles.css":"text/css; charset=utf-8",
    "reference-board.json":"application/json; charset=utf-8",
    **{name:"text/javascript; charset=utf-8" for name in STATIC_ASSETS if name.endswith(".js")},
}
DIAGNOSTIC_EVENTS={
    "server_ready","server_bind_failed","server_init_failed","server_runtime_failed",
    "request_runtime_failed","request_rejected","job_queued","worker_started","job_running",
    "job_completed","job_failed","job_start_unavailable","brief_unavailable",
}
REJECTION_CODES={
    "fixture_rejected","api_version_mismatch","server_instance_mismatch",
    "ui_version_mismatch","job_not_found",
}
MAX_JSON_DEPTH=64


class DemoInitializationError(RuntimeError):
    """Fixed marker for local fixture initialization failures."""


def _diagnostic(event,**values):
    """Write one owned JSON diagnostic without ever formatting untrusted values."""
    try:
        if type(event) is not str or event not in DIAGNOSTIC_EVENTS:return
        record={"component":"ohmni_demo","event":event}
        instance_id=values.get("server_instance_id")
        if type(instance_id) is str and INSTANCE_ID_PATTERN.fullmatch(instance_id):
            record["server_instance_id"]=instance_id
        ui_version=values.get("ui_version")
        if type(ui_version) is str and UI_VERSION_PATTERN.fullmatch(ui_version):
            record["ui_version"]=ui_version
        api_version=values.get("api_version")
        if type(api_version) is int and api_version==API_VERSION:
            record["api_version"]=api_version
        job_id=values.get("job_id")
        if type(job_id) is str and JOB_ID_PATTERN.fullmatch(job_id):record["job_id"]=job_id
        error_code=values.get("error_code")
        if type(error_code) is str and error_code in JOB_FAILURE_CODES:
            record["error_code"]=error_code
        rejection_code=values.get("rejection_code")
        if type(rejection_code) is str and rejection_code in REJECTION_CODES:
            record["rejection_code"]=rejection_code
        sys.stderr.write(json.dumps(record,separators=(",",":"),sort_keys=True)+"\n")
        sys.stderr.flush()
    except BaseException:  # noqa: BLE001 - diagnostics must never affect server state
        return


def _load_web_snapshot(web_root):
    try:
        root=web_root.resolve()
        assets={}
        digest=hashlib.sha256()
        for name in STATIC_ASSETS:
            path=root/name
            if path.is_symlink():raise OSError
            resolved=path.resolve()
            if resolved.parent!=root or not resolved.is_file():raise OSError
            data=resolved.read_bytes()
            assets["/"+name]=data
            encoded=name.encode("ascii")
            digest.update(len(encoded).to_bytes(2,"big"));digest.update(encoded)
            digest.update(len(data).to_bytes(8,"big"));digest.update(data)
        return MappingProxyType(assets),digest.hexdigest()
    except BaseException:  # noqa: BLE001 - initialization never inspects the failure
        raise DemoInitializationError from None


def _owned_json_value(value,depth=0,seen=None):
    value_type=type(value)
    if value is None or value_type in {str,bool,int}:return value
    if value_type is float:
        if not math.isfinite(value):raise ValueError
        return value
    if value_type not in {dict,list}:raise TypeError
    if depth>=MAX_JSON_DEPTH:raise ValueError
    if seen is None:seen=set()
    identity=id(value)
    if identity in seen:raise ValueError
    seen.add(identity)
    try:
        if value_type is list:return [_owned_json_value(item,depth+1,seen) for item in value]
        result={}
        for key,item in value.items():
            if type(key) is not str:raise TypeError
            result[key]=_owned_json_value(item,depth+1,seen)
        return result
    finally:seen.discard(identity)


def _owned_json_object(value):
    if type(value) is not dict:raise TypeError
    result=_owned_json_value(value)
    json.dumps(result,allow_nan=False)
    return result


def _owned_job_record(value,job_id):
    job=_owned_json_object(value)
    if set(job)!=JOB_RECORD_FIELDS:raise ValueError
    if type(job["job_id"]) is not str or job["job_id"]!=job_id:raise ValueError
    status=job["status"]
    if type(status) is not str or status not in JOB_STATUSES:raise ValueError
    progress=job["progress"];report=job["report"];error=job["error"];error_code=job["error_code"]
    if type(progress) is not list or any(type(item) is not dict for item in progress):raise ValueError
    if status in {"queued","running"}:
        if report is not None or error is not None or error_code is not None:raise ValueError
    elif status=="complete":
        if type(report) is not dict or error is not None or error_code is not None:raise ValueError
    elif (
        progress or report is not None or type(error) is not str or error!=DEMO_FAILURE_MESSAGE
        or type(error_code) is not str or error_code not in JOB_FAILURE_CODES
    ):raise ValueError
    return job


def _reject_json_constant(_value):
    raise ValueError


class JobStore:
    def __init__(self,output_root:Path=OUTPUT_ROOT,pipeline_factory=DemoPipeline,*,max_active_jobs=2):
        self.output_root=output_root;self.pipeline_factory=pipeline_factory;self.jobs={};self.lock=threading.Lock();self._diagnostic=None
        self.project_store=None;self.max_active_jobs=max_active_jobs
    def enable_persistence(self):
        """Attach local persistence once, recovering interrupted jobs explicitly."""
        with self.lock:
            if self.project_store is not None:return
            durable=ProjectStore(self.output_root)
            for job_id,record in durable.load_jobs():
                if not JOB_ID_PATTERN.fullmatch(job_id):continue
                try:record=_owned_job_record(record,job_id)
                except (TypeError,ValueError):record=self._failure_record(job_id)
                if record["status"] not in TERMINAL_JOB_STATUSES:
                    record=self._failure_record(job_id,"server_restarted")
                    durable.save_job(record)
                self.jobs.setdefault(job_id,record)
            self.project_store=durable
            for job_id in self.jobs:self._persist_locked(job_id)
    def _persist_locked(self,job_id):
        if self.project_store is None:return True
        try:self.project_store.save_job(_owned_job_record(self.jobs[job_id],job_id));return True
        except BaseException:  # noqa: BLE001 - disk failures cannot leave a false completed job
            self.jobs[job_id]=self._failure_record(job_id)
            try:self.project_store.save_job(self.jobs[job_id])
            except BaseException:self._emit("job_failed",job_id,"job_state_invalid")  # noqa: BLE001
            return False
    def _admit_locked(self):
        active=sum(self._validated_job_locked(key)["status"] not in TERMINAL_JOB_STATUSES for key in self.jobs)
        if active>=self.max_active_jobs:raise RuntimeError("local job capacity reached")
    @staticmethod
    def _queued_record(job_id):
        return {"job_id":job_id,"status":"queued","progress":[],"report":None,"error":None,"error_code":None}
    def set_diagnostic(self,diagnostic):self._diagnostic=diagnostic
    def stop(self):
        """Terminalize active attempts before releasing the workspace lease."""
        with self.lock:active=[key for key in self.jobs if self._validated_job_locked(key)["status"] not in TERMINAL_JOB_STATUSES]
        for job_id in active:self._fail(job_id,"server_restarted")
    def _emit(self,event,job_id,error_code=None):
        try:
            if self._diagnostic is not None:self._diagnostic(event,job_id=job_id,error_code=error_code)
        except BaseException:return  # noqa: BLE001 - diagnostics must never affect job state
    def start(self,request:str)->str:
        job_id=uuid.uuid4().hex[:12]
        with self.lock:
            self._admit_locked()
            self.jobs[job_id]=self._queued_record(job_id)
            if not self._persist_locked(job_id):raise RuntimeError("local job persistence unavailable")
        self._launch(job_id,request)
        return job_id
    def start_revision(self,project_id,revision_id):
        """Reuse active/complete attempts; a failed attempt can be retried."""
        from ohmni.application.projects import ProjectPipeline
        from ohmni.synthesis import SynthesisBrief

        if self.project_store is None:raise RuntimeError("local project persistence unavailable")
        with self.lock:
            revision=self.project_store.revision(project_id,revision_id)
            if revision is None:return None
            previous_job_id=revision["job_id"]
            if previous_job_id is not None:
                if previous_job_id not in self.jobs:raise ValueError("stored revision job unavailable")
                previous=self._validated_job_locked(previous_job_id)
                if previous["status"]!="failed":return previous_job_id
                if not self._persist_locked(previous_job_id):raise RuntimeError("local job persistence unavailable")
            brief=SynthesisBrief.model_validate(revision["brief"])
            if brief.fingerprint!=revision["brief_fingerprint"]:raise ValueError("stored brief changed")
            self._admit_locked()
            job_id=uuid.uuid4().hex[:12];record=self._queued_record(job_id)
            claimed=self.project_store.claim_job(project_id,revision_id,record,previous_job_id)
            if claimed!=job_id:return claimed
            self.jobs[job_id]=record
        self._launch(job_id,brief,ProjectPipeline)
        return job_id
    def _launch(self,job_id,request,pipeline_factory=None):
        self._emit("job_queued",job_id)
        try:
            args=(job_id,request) if pipeline_factory is None else (job_id,request,pipeline_factory)
            threading.Thread(target=self._run,args=args,daemon=True).start()
        except BaseException:  # noqa: BLE001 - the launch boundary must always terminalize the job
            self._fail(job_id,"worker_start_failed")
    @staticmethod
    def _failure_record(job_id,error_code="job_state_invalid"):
        return {"job_id":job_id,"status":"failed","progress":[],"report":None,"error":DEMO_FAILURE_MESSAGE,"error_code":error_code}
    def _validated_job_locked(self,job_id):
        try:job=_owned_job_record(self.jobs[job_id],job_id)
        except BaseException:job=self._failure_record(job_id)  # noqa: BLE001 - never inspect an invalid envelope
        self.jobs[job_id]=job
        return job
    def _fail(self,job_id,error_code="job_state_invalid"):
        changed=False
        with self.lock:
            job=self._validated_job_locked(job_id)
            if job["status"] in TERMINAL_JOB_STATUSES:return
            self.jobs[job_id]=self._failure_record(job_id,error_code);changed=True
            self._persist_locked(job_id)
        if changed:self._emit("job_failed",job_id,error_code)
    def _run(self,job_id,request,pipeline_factory=None):
        self._emit("worker_started",job_id)
        def progress(event):
            try:
                value=_owned_json_object(event.model_dump(mode="json"))
                became_running=False
                with self.lock:
                    job=self._validated_job_locked(job_id)
                    if job["status"] not in TERMINAL_JOB_STATUSES:
                        became_running=job["status"]!="running"
                        job["progress"].append(value);job["status"]="running"
                        self._persist_locked(job_id)
                if became_running:self._emit("job_running",job_id)
            except BaseException:  # noqa: BLE001 - progress is an untrusted publication boundary
                self._fail(job_id,"progress_publication_failed")
        try:
            with self.lock:
                if self._validated_job_locked(job_id)["status"] in TERMINAL_JOB_STATUSES:return
            report=(pipeline_factory or self.pipeline_factory)(progress).run(self.output_root/job_id,request)
            with self.lock:
                if self._validated_job_locked(job_id)["status"] in TERMINAL_JOB_STATUSES:return
            value=_owned_json_object(report.model_dump(mode="json"))
            if pipeline_factory is not None:
                # Project workers cannot publish a report for another input,
                # even if the returned envelope otherwise looks well-formed.
                lineage=self._project_lineage(job_id,value)
                if lineage is None or lineage["brief_fingerprint"]!=request.fingerprint:raise ValueError
            with self.lock:
                job=self._validated_job_locked(job_id)
                if job["status"] not in TERMINAL_JOB_STATUSES:
                    job.update(status="complete",report=value);completed=self._persist_locked(job_id)
                else:completed=False
            if completed:self._emit("job_completed",job_id)
        except BaseException:  # noqa: BLE001 - the worker boundary must always terminalize the job
            self._fail(job_id,"pipeline_failed")
    def _snapshot(self,job_id):
        with self.lock:
            if job_id not in self.jobs:return None
            return _owned_json_object(self._validated_job_locked(job_id))
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
        try:return self._read_artifact_snapshot(job_id,name,self._snapshot(job_id))
        except BaseException:return "unavailable",None  # noqa: BLE001 - never expose artifact-boundary failures
    def read_build_package(self,job_id):
        """Zip only captured, hash-matching bytes from one current release."""
        try:return self._build_package_snapshot(job_id)
        except BaseException:return "unavailable",None  # noqa: BLE001 - never disclose disk or report failures
    def _project_lineage(self,job_id,report,manifest=None):
        from ohmni.synthesis import SynthesisBrief, synthesize_a1

        lineage=self.project_store.job_revision(job_id) if self.project_store is not None else None
        if lineage is None:
            if report.get("mode")=="bounded_synthesis":raise ValueError("project revision unavailable")
            return None
        brief=SynthesisBrief.model_validate(lineage["brief"])
        project=report["project"]
        if (brief.fingerprint!=lineage["brief_fingerprint"]
                or project.get("brief_fingerprint")!=brief.fingerprint
                or project.get("name")!=brief.project_name
                or report.get("mode")!="bounded_synthesis"):
            raise ValueError("project report does not match saved revision")
        circuit_hash=project.get("circuit_hash")
        if not isinstance(circuit_hash,str) or not UI_VERSION_PATTERN.fullmatch(circuit_hash):raise ValueError
        synthesis=synthesize_a1(brief)
        if not synthesis.accepted or synthesis.circuit.content_hash!=circuit_hash:
            raise ValueError("project circuit does not match saved input")
        if manifest is None:
            directory=self._job_directory(job_id)
            item=report["release"]["manifest"]
            if directory is None or item["relative_path"]!="ohmni-fabrication-manifest.json":raise ValueError
            state,data=self._read_matching(directory/"fabrication"/item["relative_path"],item["sha256"],directory/"fabrication")
            if state!="current":raise ValueError("project manifest unavailable")
            manifest=json.loads(data)
        if (manifest.get("circuit_fingerprint")!=circuit_hash
                or manifest.get("pcb_fingerprint")!=report["pcb"]["fingerprint"]
                or manifest.get("schematic_fingerprint")!=report["schematic"]["fingerprint"]):
            raise ValueError("project fabrication does not match report")
        return lineage
    def _build_package_snapshot(self,job_id):
        job=self.get(job_id)
        if not job or job["status"]!="complete":return "unavailable",None
        report=job["report"];release=report.get("release",{})
        if release.get("current") is not True:return "stale",None
        if release.get("status")!="READY_FOR_MANUFACTURING_REVIEW":return "unavailable",None
        directory=self._job_directory(job_id)
        if directory is None:return "unavailable",None
        captured={}
        for name in ARTIFACT_SECTIONS:
            state,data=self._read_artifact_snapshot(job_id,name,job)
            if state!="current":return state,None
            captured[name]=data
        pcb=report["pcb"];schematic=report["schematic"]
        if (release.get("pcb_fingerprint")!=pcb["fingerprint"]
                or pcb.get("source_schematic_fingerprint")!=schematic["fingerprint"]):
            return "stale",None
        placed=pcb.get("source_placed_pcb_fingerprint")
        if not isinstance(placed,str) or not UI_VERSION_PATTERN.fullmatch(placed):return "unavailable",None
        state,data=self._read_matching(directory/"golden.placed.kicad_pcb",placed,directory)
        if state!="current":return state,None
        captured["golden.placed.kicad_pcb"]=data
        fabrication=directory/"fabrication"
        for item in [*release["files"],release["manifest"]]:
            name=item["relative_path"]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}",name):return "unavailable",None
            archive_name="fabrication/"+name
            if archive_name in captured:return "unavailable",None
            state,data=self._read_matching(fabrication/name,item["sha256"],fabrication)
            if state!="current":return state,None
            captured[archive_name]=data
        manifest=json.loads(captured["fabrication/ohmni-fabrication-manifest.json"])
        lineage=self._project_lineage(job_id,report,manifest)
        if (manifest.get("pcb_fingerprint")!=pcb["fingerprint"]
                or manifest.get("schematic_fingerprint")!=schematic["fingerprint"]
                or manifest.get("files")!=release["files"]
                or manifest.get("release_status")!="ready_for_manufacturing_review"):
            return "stale",None
        package_fingerprint=manifest.pop("package_fingerprint",None)
        manifest_digest=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if package_fingerprint!=manifest_digest or package_fingerprint!=release.get("package_fingerprint"):
            return "stale",None
        captured["report.json"]=(json.dumps(report,indent=2,allow_nan=False)+"\n").encode("utf-8")
        if lineage is not None:
            captured["confirmed-brief.json"]=(json.dumps(lineage["brief"],indent=2,sort_keys=True)+"\n").encode("utf-8")
            revision={key:value for key,value in lineage.items() if key!="brief"}
            revision.update(job_id=job_id,circuit_fingerprint=report["project"]["circuit_hash"],
                            package_fingerprint=package_fingerprint)
            captured["project-revision.json"]=(json.dumps(revision,indent=2,sort_keys=True)+"\n").encode("utf-8")
        captured["bom.csv"]=_build_bom_csv(report).encode("utf-8-sig")
        captured["ASSEMBLY-AND-BRINGUP.md"]=_build_guide(report).encode("utf-8")
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            for name,data in captured.items():archive.writestr(name,data)
        return "current",buffer.getvalue()
    def _release_file_current(self,parent,item,expected_name=None):
        if parent is None or not isinstance(item,dict):return False
        relative=item.get("relative_path");expected=item.get("sha256")
        if not isinstance(relative,str) or Path(relative).name!=relative:return False
        if expected_name is not None and relative!=expected_name:return False
        if not isinstance(expected,str) or not re.fullmatch(r"[0-9a-f]{64}",expected):return False
        return self._read_matching(parent/relative,expected,parent)[0]=="current"
    def get(self,job_id):
        try:
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
            project_current=True
            try:self._project_lineage(job_id,report)
            except (ValueError,KeyError,TypeError,OSError):project_current=False
            pcb_current=pcb_file_current and schematic_current and placed_current and project_current
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
        except BaseException:return self._failure_record(job_id)  # noqa: BLE001 - polling must fail closed


def _build_bom_csv(report):
    """Keep missing prices blank and prevent spreadsheet formula interpretation."""
    output=io.StringIO(newline="")
    writer=csv.writer(output)
    fields=("references","part","description","package","quantity","evidence_status",
            "unit_price","knowledge","purchase_quantity","purchase_cost")
    writer.writerow((*fields,"pricing_source"))
    for item in report["bom"]["lines"]:
        values=[]
        for field in fields:
            value=item.get(field)
            if isinstance(value,list):value="; ".join(str(part) for part in value)
            if isinstance(value,str) and value.lstrip().startswith(("=","+","-","@")):
                value="'"+value
            values.append(value)
        writer.writerow((*values,"SYNTHETIC FIXTURE - NOT LIVE SUPPLIER DATA"))
    return output.getvalue()


def _build_guide(report):
    lines=["# Assembly and bring-up", "", str(report["project"]["name"]), "",
           "This package contains the exact checked design and fabrication files from this run.",
           "It is ready for human manufacturing review. No physical board has been built or measured.", "",
           "## Before ordering", "",
           "- The manufacturing profile and all supplied prices are synthetic; obtain a fabricator review and current quotes.",
           "- Electrical checks use bundled catalog facts. Seed datasheet claims have not been machine re-verified against their source PDFs.",
           "- Review the schematic, PCB, report.json, component orientations, and assembly risks below.",
           "- Firmware is not included. This release does not build, flash, or simulate MCU code.",
           "- USB-C provides power; it does not add a USB programming interface.",
           "- Confirm programming access in the schematic. An omitted programming header means no supplied programming connector.",
           "- Where provided, use the programming connections with an appropriate 3.3 V logic adapter and reviewed firmware.",
           "- These checks do not establish thermal, RF, EMC, signal-integrity, or physical operating behavior.", "",
           "## Assembly guidance", ""]
    for risk in report.get("assembly",{}).get("risks",[]):
        refs=", ".join(risk.get("references",[]))
        lines.append(f"- {refs} ({risk.get('package','unknown package')}): {risk.get('difficulty','UNKNOWN')}. {risk.get('detail','')}")
    for limitation in report.get("assembly",{}).get("limitations",[]):lines.append(f"- {limitation}")
    lines.extend(["", "## Bring-up checklist", "",
                  "These are planned measurements, not recorded results. Check the exact schematic before applying power.", ""])
    for index,step in enumerate(report.get("experience",{}).get("bring_up",[]),1):
        lines.append(f"{index}. {step['action']}")
        if step.get("prediction") is not None:lines.append(f"   Expected from the design: {step['prediction']}")
        if step.get("basis"):lines.append(f"   Basis: {step['basis']}")
        if step.get("rule_id"):lines.append(f"   Check: {step['rule_id']}")
        lines.append("   Measured result: __________  Date: __________")
    lines.extend(["", "## Verification and limitations", ""])
    for stage in report.get("verification_ladder",[]):
        lines.append(f"- {stage['stage']}: {stage['status']}. {stage.get('detail','')}")
    for limitation in report.get("limitations",[]):lines.append(f"- {limitation}")
    return "\n".join(lines)+"\n"


class DemoHTTPServer(ThreadingHTTPServer):
    def __init__(self,server_address,handler_class,*,store=None,web_root=WEB_ROOT):
        self.workspace_lock=None
        try:
            self.server_instance_id=uuid.uuid4().hex[:16]
            self.static_assets,self.ui_version=_load_web_snapshot(web_root)
            self.store=store if store is not None else JobStore()
            self.store.set_diagnostic(self._job_diagnostic)
        except DemoInitializationError:raise
        except BaseException:raise DemoInitializationError from None  # noqa: BLE001 - never inspect initialization failures
        # Claim the endpoint before touching durable state. A failed bind must
        # neither recover jobs nor obscure the existing endpoint error contract.
        super().__init__(server_address,handler_class)
        try:
            self.workspace_lock=ProjectWorkspaceLock(self.store.output_root)
            self.store.enable_persistence()
            self.projects=self.store.project_store
        except ProjectWorkspaceInUseError:
            self.server_close()
            raise
        except BaseException:  # noqa: BLE001 - release endpoint and lease after failed initialization
            self.server_close()
            raise DemoInitializationError from None
    def server_close(self):
        try:super().server_close()
        finally:
            if self.workspace_lock is not None:
                try:self.store.stop()
                finally:self.workspace_lock.close();self.workspace_lock=None
    def _identity(self):
        return {
            "api_version":API_VERSION,
            "server_instance_id":self.server_instance_id,
            "ui_version":self.ui_version,
        }
    def _job_diagnostic(self,event,**values):
        _diagnostic(
            event,api_version=API_VERSION,server_instance_id=self.server_instance_id,
            ui_version=self.ui_version,**values,
        )
    def server_bind(self):
        if os.name=="nt":
            self.allow_reuse_address=False
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()
    def handle_error(self,_request,_client_address):
        self._job_diagnostic("request_runtime_failed")


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(WEB_ROOT),**kwargs)
    def log_message(self,_format,*_args):return
    def end_headers(self):
        self.send_header("cache-control","no-store")
        self.send_header("x-ohmni-api-version",str(API_VERSION))
        self.send_header("x-ohmni-server-instance",self.server.server_instance_id)
        self.send_header("x-ohmni-ui-version",self.server.ui_version)
        super().end_headers()
    def _json(self,value:Any,status=HTTPStatus.OK):
        try:body=json.dumps(_owned_json_object(value),allow_nan=False).encode()
        except BaseException:  # noqa: BLE001 - response values are another untrusted serialization boundary
            self.server._job_diagnostic("request_runtime_failed")
            body=b'{"error":"response_unavailable"}';status=HTTPStatus.INTERNAL_SERVER_ERROR
        self.send_response(status);self.send_header("content-type","application/json");self.send_header("content-length",str(len(body)));self.end_headers();self.wfile.write(body)
    def _reject(self,error,status):
        self.server._job_diagnostic("request_rejected",rejection_code=error)
        return self._json({"error":error},status)
    def _request_contract_error(self,payload):
        if payload=={"fixture_id":DEMO_FIXTURE_ID} or payload=={"request":DEMO_REQUEST}:return None
        if set(payload)!={"fixture_id","api_version","server_instance_id","ui_version"}:
            return "fixture_rejected"
        fixture_id=payload["fixture_id"]
        if type(fixture_id) is not str or fixture_id!=DEMO_FIXTURE_ID:return "fixture_rejected"
        api_version=payload["api_version"]
        if type(api_version) is not int or api_version!=API_VERSION:return "api_version_mismatch"
        server_instance_id=payload["server_instance_id"]
        if type(server_instance_id) is not str or server_instance_id!=self.server.server_instance_id:
            return "server_instance_mismatch"
        ui_version=payload["ui_version"]
        if type(ui_version) is not str or ui_version!=self.server.ui_version:return "ui_version_mismatch"
        return None
    def _poll_contract_error(self):
        api_version=self.headers.get("x-ohmni-api-version")
        if api_version is not None and api_version!=str(API_VERSION):return "api_version_mismatch"
        instance_id=self.headers.get("x-ohmni-server-instance")
        if instance_id is not None and instance_id!=self.server.server_instance_id:
            return "server_instance_mismatch"
        ui_version=self.headers.get("x-ohmni-ui-version")
        if ui_version is not None and ui_version!=self.server.ui_version:return "ui_version_mismatch"
        return None
    def _owned_request_payload(self):
        """Decode a request body into an owned value, or fail closed."""
        length=int(self.headers.get("content-length","0"))
        if length<0 or length>16_384:raise ValueError
        return _owned_json_object(json.loads(self.rfile.read(length) or b"{}",parse_constant=_reject_json_constant))

    def _project_payload(self,fields):
        try:payload=self._owned_request_payload()
        except BaseException:  # noqa: BLE001 - JSON decoding must fail closed
            self._reject("invalid_project_request",HTTPStatus.BAD_REQUEST);return None
        expected={"api_version","server_instance_id","ui_version",*fields}
        if set(payload)!=expected:
            self._reject("invalid_project_request",HTTPStatus.BAD_REQUEST);return None
        for field,code in (("api_version","api_version_mismatch"),
                           ("server_instance_id","server_instance_mismatch"),
                           ("ui_version","ui_version_mismatch")):
            actual=payload[field];expected_value=self.server._identity()[field]
            if type(actual) is not type(expected_value) or actual!=expected_value:
                self._reject(code,HTTPStatus.CONFLICT);return None
        return payload

    def _post_project(self,project_id=None):
        from ohmni.application.projects import ProjectRefusalError, preview_project
        from ohmni.synthesis import SynthesisBrief

        payload=self._project_payload({"brief"})
        if payload is None:return
        try:
            # JSON strict mode accepts enum names and JSON arrays, without
            # turning strings such as "false" or "1" into typed options.
            if type(payload["brief"]) is not dict:raise ValueError
            brief=SynthesisBrief.model_validate_json(json.dumps(payload["brief"]),strict=True)
            if not brief.project_name.strip() or len(brief.sensors)>4:raise ValueError
            preview=_owned_json_object(preview_project(brief).model_dump(mode="json"))
        except ProjectRefusalError as refusal:
            return self._json({"error":"project_refused","refusal":refusal.refusal.model_dump(mode="json")},HTTPStatus.UNPROCESSABLE_ENTITY)
        except (ValueError,TypeError):return self._reject("invalid_project_request",HTTPStatus.BAD_REQUEST)
        except BaseException:  # noqa: BLE001 - application failures never leak server details
            return self._json({"error":"project_unavailable"},HTTPStatus.SERVICE_UNAVAILABLE)
        try:
            project=self.server.projects.save_revision(brief.model_dump(mode="json"),brief.fingerprint,preview,project_id)
            if project is None:return self._json({"error":"project_not_found"},HTTPStatus.NOT_FOUND)
            return self._json({"project":project,**self.server._identity()},HTTPStatus.CREATED)
        except BaseException:  # noqa: BLE001 - persistence errors never become successful saves
            return self._json({"error":"project_unavailable"},HTTPStatus.SERVICE_UNAVAILABLE)

    def _post_revision_run(self,project_id,revision_id):
        payload=self._project_payload(set())
        if payload is None:return
        try:
            job_id=self.server.store.start_revision(project_id,revision_id)
            if job_id is None:return self._json({"error":"revision_not_found"},HTTPStatus.NOT_FOUND)
            job=self.server.store.get(job_id)
            if job is None:raise ValueError
            return self._json({"job_id":job_id,"status":job["status"],**self.server._identity()},HTTPStatus.ACCEPTED)
        except BaseException:  # noqa: BLE001 - bounded admission and persistence can refuse a launch
            return self._json({"error":"job_start_unavailable"},HTTPStatus.SERVICE_UNAVAILABLE)

    def _sensor_exercise(self,*,answer=False):
        from ohmni.application.diagnostics import evaluate_sensor_exercise, sensor_exercise

        payload=self._project_payload({"choice"}) if answer else None
        if answer and payload is None:return
        try:
            if answer:
                choice=payload["choice"]
                if type(choice) is not str or choice not in {"leave_5v","move_vdd","move_both"}:raise ValueError
                result={"result":evaluate_sensor_exercise(choice)}
            else:result={"exercise":sensor_exercise()}
            return self._json({**result,**self.server._identity()})
        except ValueError:return self._json({"error":"invalid_exercise_choice"},HTTPStatus.BAD_REQUEST)
        except BaseException:  # noqa: BLE001 - exercise evidence failures fail closed
            return self._json({"error":"exercise_unavailable"},HTTPStatus.SERVICE_UNAVAILABLE)

    def do_POST(self):
        if self.path=="/api/projects":return self._post_project()
        if self.path=="/api/exercises/sensor-rail":return self._sensor_exercise(answer=True)
        revision_path=re.fullmatch(r"/api/projects/([0-9a-f]{16})/revisions",self.path)
        if revision_path:return self._post_project(revision_path[1])
        run_path=re.fullmatch(r"/api/projects/([0-9a-f]{16})/revisions/([0-9a-f]{16})/run",self.path)
        if run_path:return self._post_revision_run(run_path[1],run_path[2])
        if self.path=="/api/brief":return self._post_brief()
        if self.path!="/api/demo":return self._json({"error":"not found"},HTTPStatus.NOT_FOUND)
        try:payload=self._owned_request_payload()
        except BaseException:return self._reject("fixture_rejected",HTTPStatus.BAD_REQUEST)  # noqa: BLE001 - JSON decoding must fail closed
        error=self._request_contract_error(payload)
        if error is not None:return self._reject(error,HTTPStatus.BAD_REQUEST if error=="fixture_rejected" else HTTPStatus.CONFLICT)
        try:
            job_id=self.server.store.start(DEMO_REQUEST)
            if type(job_id) is not str or not JOB_ID_PATTERN.fullmatch(job_id):raise ValueError
        except BaseException:  # noqa: BLE001 - request threads must not leak failures
            self.server._job_diagnostic("job_start_unavailable")
            return self._json({"error":"job_start_unavailable"},HTTPStatus.SERVICE_UNAVAILABLE)
        self._json({"job_id":job_id,"status":"queued",**self.server._identity()},HTTPStatus.ACCEPTED)
    def _post_brief(self):
        """Interpret the supported request into a brief, before any engineering.

        Bound to the same fixture, API, instance and UI contract as job
        creation, so a stale page cannot show a brief from another generation.
        """
        try:payload=self._owned_request_payload()
        except BaseException:return self._reject("fixture_rejected",HTTPStatus.BAD_REQUEST)  # noqa: BLE001 - JSON decoding must fail closed
        error=self._request_contract_error(payload)
        if error is not None:return self._reject(error,HTTPStatus.BAD_REQUEST if error=="fixture_rejected" else HTTPStatus.CONFLICT)
        try:brief=_owned_json_object(preview_brief(DEMO_REQUEST).model_dump(mode="json"))
        except BaseException:  # noqa: BLE001 - request threads must not leak failures
            self.server._job_diagnostic("brief_unavailable")
            return self._json({"error":BRIEF_UNAVAILABLE_MESSAGE},HTTPStatus.SERVICE_UNAVAILABLE)
        return self._json({"brief":brief,**self.server._identity()})

    def do_GET(self):
        try:request_path=unquote(urlsplit(self.path).path,errors="strict")
        except BaseException:return self._json({"error":INVALID_PATH_MESSAGE},HTTPStatus.BAD_REQUEST)  # noqa: BLE001 - request targets must fail closed
        if request_path=="/api/health":
            return self._json({"status":"ready","fixture_id":DEMO_FIXTURE_ID,**self.server._identity()})
        if request_path=="/api/projects" or request_path.startswith("/api/projects/"):
            error=self._poll_contract_error()
            if error is not None:return self._reject(error,HTTPStatus.CONFLICT)
            try:
                if request_path=="/api/projects":
                    return self._json({"projects":self.server.projects.list_projects(),**self.server._identity()})
                project_id=request_path.removeprefix("/api/projects/")
                project=self.server.projects.get(project_id) if PROJECT_ID_PATTERN.fullmatch(project_id) else None
                if project is None:return self._json({"error":"project_not_found"},HTTPStatus.NOT_FOUND)
                return self._json({"project":project,**self.server._identity()})
            except BaseException:  # noqa: BLE001 - never disclose persistence failures
                return self._json({"error":"project_unavailable"},HTTPStatus.SERVICE_UNAVAILABLE)
        if request_path=="/api/exercises/sensor-rail":
            error=self._poll_contract_error()
            if error is not None:return self._reject(error,HTTPStatus.CONFLICT)
            return self._sensor_exercise()
        if request_path.startswith("/api/jobs/"):
            job_id=request_path.removeprefix("/api/jobs/")
            if "/" in job_id:return self._json({"error":"invalid job path"},HTTPStatus.BAD_REQUEST)
            error=self._poll_contract_error()
            if error is not None:return self._reject(error,HTTPStatus.CONFLICT)
            try:
                job=self.server.store.get(job_id)
                if job is None:return self._reject("job_not_found",HTTPStatus.NOT_FOUND)
                published=_owned_json_object(job);published.update(self.server._identity())
            except BaseException:  # noqa: BLE001 - polling must fail closed
                self.server._job_diagnostic("request_runtime_failed")
                return self._json({"error":UNAVAILABLE_RESPONSE_MESSAGE},HTTPStatus.INTERNAL_SERVER_ERROR)
            return self._json(published)
        if request_path.startswith("/api/artifacts/"):
            parts=request_path.split("/")
            if len(parts)!=5:return self._json({"error":"invalid artifact path"},HTTPStatus.BAD_REQUEST)
            error=self._poll_contract_error()
            if error is not None:return self._reject(error,HTTPStatus.CONFLICT)
            job_id,name=parts[3],parts[4]
            if name=="build-package.zip":state,data=self.server.store.read_build_package(job_id)
            else:state,data=self.server.store.read_artifact(job_id,name)
            if state in {"unavailable","missing"}:return self._json({"error":"artifact unavailable"},HTTPStatus.NOT_FOUND)
            if state!="current" or data is None:return self._json({"error":"artifact is stale or not associated with this report"},HTTPStatus.CONFLICT)
            content_type="application/zip" if name=="build-package.zip" else "application/octet-stream"
            self.send_response(HTTPStatus.OK);self.send_header("content-type",content_type);self.send_header("x-content-type-options","nosniff");self.send_header("content-disposition",f'attachment; filename="{name}"');self.send_header("content-length",str(len(data)));self.end_headers();self.wfile.write(data);return
        asset_path="/index.html" if request_path=="/" else request_path
        data=self.server.static_assets.get(asset_path)
        if data is None:return self._json({"error":"not found"},HTTPStatus.NOT_FOUND)
        name=asset_path.removeprefix("/")
        self.send_response(HTTPStatus.OK);self.send_header("content-type",STATIC_CONTENT_TYPES[name]);self.send_header("content-length",str(len(data)));self.end_headers();self.wfile.write(data)


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--host",default="127.0.0.1");parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--output-root",type=Path,default=OUTPUT_ROOT,
                        help="Local project database and artifacts; one active server per directory.")
    args=parser.parse_args(argv)
    server=None
    try:
        args.output_root.mkdir(parents=True,exist_ok=True)
    except BaseException:  # noqa: BLE001 - initialization diagnostics cannot inspect failures
        _diagnostic("server_init_failed",api_version=API_VERSION)
        print(INITIALIZATION_FAILURE_MESSAGE,file=sys.stderr,flush=True)
        return 1
    try:
        server=DemoHTTPServer((args.host,args.port),DemoHandler,store=JobStore(args.output_root))
    except ProjectWorkspaceInUseError:
        _diagnostic("server_init_failed",api_version=API_VERSION)
        print(WORKSPACE_IN_USE_MESSAGE,file=sys.stderr,flush=True)
        return 1
    except DemoInitializationError:
        _diagnostic("server_init_failed",api_version=API_VERSION)
        print(INITIALIZATION_FAILURE_MESSAGE,file=sys.stderr,flush=True)
        return 1
    except OSError:
        _diagnostic("server_bind_failed",api_version=API_VERSION)
        print(STARTUP_FAILURE_MESSAGE,file=sys.stderr,flush=True)
        return 1
    except BaseException:  # noqa: BLE001 - construction diagnostics cannot inspect failures
        _diagnostic("server_init_failed",api_version=API_VERSION)
        print(INITIALIZATION_FAILURE_MESSAGE,file=sys.stderr,flush=True)
        return 1
    try:
        print(f"Ohmni demo: http://{args.host}:{args.port}",flush=True)
        server._job_diagnostic("server_ready")
        server.serve_forever()
    except KeyboardInterrupt:pass
    except BaseException:  # noqa: BLE001 - runtime diagnostics cannot inspect failures
        server._job_diagnostic("server_runtime_failed")
        print(RUNTIME_FAILURE_MESSAGE,file=sys.stderr,flush=True)
        return 1
    finally:
        if server is not None:
            try:server.server_close()
            except OSError:pass
    return 0
if __name__=="__main__":raise SystemExit(main())
