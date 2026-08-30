"""Typed parser for KiCad DRC JSON v1."""

from __future__ import annotations

import json
from pathlib import Path

from ...adapters import ToolStatus
from ..models import ArtifactFingerprint
from ..pcb_models import DrcFinding, DrcFindingClass, DrcItem, DrcReport, DrcStatus


class DrcReportParseError(ValueError): pass


def _classify(kind: str) -> DrcFindingClass:
    if "clearance" in kind: return DrcFindingClass.CLEARANCE
    if kind in {"unconnected_items","unrouted"}: return DrcFindingClass.UNROUTED
    if "edge" in kind: return DrcFindingClass.EDGE
    if "courtyard" in kind or "overlap" in kind: return DrcFindingClass.COURTYARD
    if kind in {"shorting_items","solder_mask_bridge"}: return DrcFindingClass.CONNECTIVITY
    if "footprint" in kind: return DrcFindingClass.FOOTPRINT
    if "connect" in kind: return DrcFindingClass.CONNECTIVITY
    if "drill" in kind or "hole" in kind: return DrcFindingClass.DRILL
    if "track" in kind: return DrcFindingClass.TRACK
    if "via" in kind: return DrcFindingClass.VIA
    return DrcFindingClass.OTHER


def _finding(value) -> DrcFinding:
    if not isinstance(value,dict): raise DrcReportParseError("invalid DRC finding")
    items=[]
    for item in value.get("items",[]):
        if not isinstance(item,dict): raise DrcReportParseError("invalid DRC item")
        pos=item.get("pos")
        items.append(DrcItem(description=str(item.get("description","")),uuid=item.get("uuid"),x=pos.get("x") if isinstance(pos,dict) else None,y=pos.get("y") if isinstance(pos,dict) else None))
    severity=str(value.get("severity","unknown")).lower();kind=str(value.get("type","unknown"))
    return DrcFinding(type=kind,severity=severity,description=str(value.get("description","")),classification=_classify(kind),excluded=severity=="exclusion",items=items,raw=value)


def parse_drc_json(path:Path,*,pcb_fingerprint:ArtifactFingerprint,schematic_fingerprint:ArtifactFingerprint,run_id:str,command:list[str],return_code:int,stdout:str="",stderr:str="")->DrcReport:
    try: raw=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise DrcReportParseError(f"cannot read KiCad DRC JSON: {exc}") from exc
    if not isinstance(raw,dict) or not isinstance(raw.get("violations"),list) or not isinstance(raw.get("unconnected_items"),list): raise DrcReportParseError("KiCad DRC JSON must contain violations and unconnected_items arrays")
    version=raw.get("kicad_version")
    if not isinstance(version,str): raise DrcReportParseError("KiCad DRC JSON missing kicad_version")
    violations=[_finding(x) for x in raw["violations"]];unconnected=[_finding(x) for x in raw["unconnected_items"]];active=[x for x in violations+unconnected if not x.excluded]
    if any(x.severity=="error" for x in active): status=DrcStatus.FAIL
    elif any(x.severity=="warning" for x in active): status=DrcStatus.PASS_WITH_WARNINGS
    else: status=DrcStatus.PASS
    return DrcReport(status=status,tool_status=ToolStatus.OK,run_id=run_id,kicad_version=version,pcb_fingerprint=pcb_fingerprint,source_schematic_fingerprint=schematic_fingerprint,report_path=path.resolve(),command=command,return_code=return_code,stdout=stdout,stderr=stderr,findings=violations,unconnected_items=unconnected,ignored_checks=raw.get("ignored_checks",[]))
