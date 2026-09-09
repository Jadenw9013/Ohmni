"""Typed parser for KiCad ERC JSON v1."""

from __future__ import annotations

import json
from pathlib import Path

from ...adapters import ToolStatus
from ...adapters.process import describe_exit
from ..models import ArtifactFingerprint, ErcFinding, ErcItem, ErcReport, ErcStatus, ErcWarningClass


class ErcReportParseError(ValueError):
    pass


def parse_erc_json(
    path: Path, *, artifact_fingerprint: ArtifactFingerprint, run_id: str,
    command: list[str], return_code: int, stdout: str = "", stderr: str = "",
) -> ErcReport:
    if type(return_code) is not int:
        raise ErcReportParseError("KiCad ERC returned no valid integer exit code")
    if return_code not in {0,5}:
        raise ErcReportParseError(f"KiCad ERC did not complete: {describe_exit(return_code)}. No report is accepted.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErcReportParseError(f"cannot read KiCad ERC JSON: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("sheets"), list):
        raise ErcReportParseError("KiCad ERC JSON must contain a sheets array")
    version = raw.get("kicad_version")
    if not isinstance(version, str):
        raise ErcReportParseError("KiCad ERC JSON is missing kicad_version")
    findings: list[ErcFinding] = []
    for sheet in raw["sheets"]:
        if not isinstance(sheet, dict) or not isinstance(sheet.get("violations", []), list):
            raise ErcReportParseError("invalid sheet entry in KiCad ERC JSON")
        for violation in sheet.get("violations", []):
            if not isinstance(violation, dict):
                raise ErcReportParseError("invalid violation entry in KiCad ERC JSON")
            severity = str(violation.get("severity", "unknown")).lower()
            if severity not in {"error","warning","exclusion"}:
                raise ErcReportParseError(f"unsupported KiCad ERC severity: {severity}")
            items = []
            for item in violation.get("items", []):
                pos = item.get("pos") if isinstance(item, dict) else None
                items.append(ErcItem(
                    description=str(item.get("description", "")),
                    uuid=item.get("uuid"),
                    x=pos.get("x") if isinstance(pos, dict) else None,
                    y=pos.get("y") if isinstance(pos, dict) else None,
                ))
            findings.append(ErcFinding(
                type=str(violation.get("type", "unknown")),
                severity=severity,
                description=str(violation.get("description", "")),
                excluded=severity == "exclusion",
                classification=_classify(str(violation.get("type", "unknown"))),
                sheet_path=str(sheet.get("path", "/")),
                items=items,
                raw=violation,
            ))
    active = [f for f in findings if not f.excluded]
    if (return_code==5 and not findings) or (return_code==0 and active and "--exit-code-violations" in command):
        raise ErcReportParseError("KiCad ERC exit code contradicts the reported violations")
    if any(f.severity == "error" for f in active):
        status = ErcStatus.FAIL
    elif any(f.severity == "warning" for f in active):
        status = ErcStatus.PASS_WITH_WARNINGS
    else:
        status = ErcStatus.PASS
    return ErcReport(
        status=status, tool_status=ToolStatus.OK, run_id=run_id,
        kicad_version=version, artifact_fingerprint=artifact_fingerprint,
        report_path=path.resolve(), command=command, return_code=return_code,
        stdout=stdout, stderr=stderr, findings=findings,
        ignored_checks=raw.get("ignored_checks", []),
    )


def _classify(finding_type: str) -> ErcWarningClass:
    if finding_type in {"lib_symbol_issues", "footprint_link_issues"}:
        return ErcWarningClass.LIBRARY_CONFIGURATION
    if finding_type in {"pin_to_pin", "power_pin_not_driven", "input_pin_not_driven", "unconnected_wire_endpoint"}:
        return ErcWarningClass.ELECTRICAL
    if finding_type in {"duplicate_reference", "missing_symbol", "different_unit_footprint"}:
        return ErcWarningClass.ARTIFACT_STRUCTURE
    return ErcWarningClass.UNKNOWN
