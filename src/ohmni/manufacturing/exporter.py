"""Bounded KiCad fabrication export with portable integrity manifest."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from ..adapters.tools import find_kicad_cli
from ..domain import EngineeringEvent, EventKind
from ..eda.pcb_models import DrcReport, DrcStatus, PcbArtifact
from .models import (
    FabricationFile,
    FabricationPackage,
    ManufacturingFinding,
    ManufacturingProfile,
    ManufacturingReport,
    ManufacturingStatus,
    ReleaseStatus,
)


class FabricationExportError(RuntimeError):pass
@runtime_checkable
class FabricationExporter(Protocol):
    def export(self,pcb:PcbArtifact,drc:DrcReport,manufacturing:ManufacturingReport,profile:ManufacturingProfile,destination:Path)->FabricationPackage:...

class KiCadFabricationExporter:
    required_kinds: ClassVar[set[str]]={"F.Cu","B.Cu","F.Mask","B.Mask","F.Silkscreen","B.Silkscreen","Edge.Cuts","Drill"}
    def __init__(self,executable=None,timeout_seconds=60):self.executable=executable or find_kicad_cli();self.timeout_seconds=timeout_seconds
    def export(self,pcb,drc,manufacturing,profile,destination):
        events=[_event(pcb.circuit_content_hash,EventKind.FABRICATION_EXPORT_STARTED,"Fabrication export started",{"pcb_fingerprint":pcb.fingerprint.digest,"profile_fingerprint":profile.content_hash})]
        if not pcb.lineage_is_current:raise FabricationExportError("stale routed PCB lineage")
        if drc.status not in {DrcStatus.PASS,DrcStatus.PASS_WITH_WARNINGS} or drc.findings or drc.unconnected_items or drc.pcb_fingerprint!=pcb.fingerprint:raise FabricationExportError("clean DRC for exact routed PCB required")
        if not manufacturing.passed or manufacturing.routed_pcb_fingerprint!=pcb.fingerprint.digest or manufacturing.profile.content_hash!=profile.content_hash:raise FabricationExportError("manufacturing profile verification failed or stale")
        if not pcb.compilation.routing_verification or not pcb.compilation.routing_verification.passed:raise FabricationExportError("independent routing verification required")
        if not self.executable:raise FabricationExportError("kicad-cli unavailable")
        destination=destination.resolve();destination.mkdir(parents=True,exist_ok=True)
        commands=[[self.executable,"pcb","export","gerbers","--output",str(destination),"--layers","F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts",str(pcb.path)],[self.executable,"pcb","export","drill","--output",str(destination),"--format","excellon","--excellon-units","mm",str(pcb.path)]]
        for command in commands:
            result=subprocess.run(command,capture_output=True,text=True,check=False,shell=False,timeout=self.timeout_seconds)
            if result.returncode:raise FabricationExportError(f"KiCad fabrication export failed: {result.stderr}")
        files=[]
        for path in sorted(destination.iterdir(),key=lambda p:p.name):
            if path.is_file() and path.name!="ohmni-fabrication-manifest.json":files.append(FabricationFile(relative_path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size_bytes=path.stat().st_size,kind=_kind(path.name)))
        present={x.kind for x in files if x.size_bytes>0};missing=self.required_kinds-present
        if missing:raise FabricationExportError(f"required fabrication files missing or empty: {sorted(missing)}")
        for item in files:
            kind=EventKind.DRILL_FILE_GENERATED if item.kind=="Drill" else EventKind.GERBER_GENERATED
            events.append(_event(pcb.circuit_content_hash,kind,f"Fabrication file generated: {item.relative_path}",item.model_dump(mode="json")))
        drc_hash=hashlib.sha256(json.dumps({"pcb":drc.pcb_fingerprint.digest,"status":drc.status.value,"findings":[x.model_dump(mode="json") for x in drc.findings],"unrouted":[x.model_dump(mode="json") for x in drc.unconnected_items]},sort_keys=True,separators=(",",":")).encode()).hexdigest()
        portable={"ohmni_version":"0.1.0","circuit_fingerprint":pcb.circuit_content_hash,"schematic_fingerprint":pcb.schematic_fingerprint.digest,"pcb_fingerprint":pcb.fingerprint.digest,"routing_plan_fingerprint":pcb.routing_plan_fingerprint,"drc_fingerprint":drc_hash,"manufacturing_profile_fingerprint":profile.content_hash,"files":[x.model_dump(mode="json") for x in files],"release_status":ReleaseStatus.READY_FOR_MANUFACTURING_REVIEW.value,"limitations":["Requires human manufacturing review.","Not simulation, thermal, EMC/RF, assembly, or bench verified."]}
        package_hash=hashlib.sha256(json.dumps(portable,sort_keys=True,separators=(",",":")).encode()).hexdigest();portable["package_fingerprint"]=package_hash
        manifest=destination/"ohmni-fabrication-manifest.json";manifest.write_text(json.dumps(portable,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        events.extend([_event(pcb.circuit_content_hash,EventKind.FABRICATION_PACKAGE_COMPLETED,"Fabrication package completed",{"package_fingerprint":package_hash,"file_count":len(files)}),_event(pcb.circuit_content_hash,EventKind.RELEASE_READY_FOR_REVIEW,"Release ready for manufacturing review",{"package_fingerprint":package_hash})])
        integrity_findings=[ManufacturingFinding(rule_id="PB-MFG-009",status=ManufacturingStatus.PASS,subject="fabrication lineage",designed=pcb.fingerprint.digest,limit=pcb.fingerprint.digest,detail="fabrication inputs match the verified routed PCB"),ManufacturingFinding(rule_id="PB-MFG-010",status=ManufacturingStatus.PASS,subject="required fabrication files",designed=len(present),limit=len(self.required_kinds),detail="all required fabrication files are present and nonempty")]
        return FabricationPackage(directory=destination,source_pcb_path=pcb.path,source_pcb_fingerprint=pcb.fingerprint.digest,source_schematic_fingerprint=pcb.schematic_fingerprint.digest,routing_plan_fingerprint=pcb.routing_plan_fingerprint,drc_fingerprint=drc_hash,manufacturing_profile_fingerprint=profile.content_hash,files=files,manifest_path=manifest,package_fingerprint=package_hash,status=ReleaseStatus.READY_FOR_MANUFACTURING_REVIEW,verification_findings=integrity_findings,events=events)

def _kind(name):
    lower=name.lower()
    if lower.endswith(".gtl"):return "F.Cu"
    if lower.endswith(".gbl"):return "B.Cu"
    if lower.endswith(".gts"):return "F.Mask"
    if lower.endswith(".gbs"):return "B.Mask"
    if lower.endswith(".gto"):return "F.Silkscreen"
    if lower.endswith(".gbo"):return "B.Silkscreen"
    if lower.endswith(".gm1"):return "Edge.Cuts"
    if lower.endswith(".drl"):return "Drill"
    return "Metadata"

def _event(circuit_hash,kind,summary,payload):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit_hash,payload=payload)
