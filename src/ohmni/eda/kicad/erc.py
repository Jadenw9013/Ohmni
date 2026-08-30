"""Bounded subprocess adapter for KiCad schematic ERC."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from ...adapters import ToolStatus
from ...adapters.tools import find_kicad_cli
from ...domain import EngineeringEvent, EventKind, Evidence, EvidenceKind
from ..models import ErcReport, ErcStatus, SchematicArtifact
from ..pcb_models import DrcReport, DrcStatus, PcbArtifact
from .parser import ErcReportParseError, parse_erc_json
from .pcb_parser import DrcReportParseError, parse_drc_json


class KiCadCliAdapter:
    def __init__(self, executable: str | None = None, *, timeout_seconds: int = 60) -> None:
        self.executable = executable or find_kicad_cli()
        self.timeout_seconds = timeout_seconds

    def run_erc(self, artifact: SchematicArtifact, report_path: Path | None = None) -> ErcReport:
        if not artifact.is_current:
            report = self._failure(artifact, ErcStatus.STALE_ARTIFACT, ToolStatus.FAILED,
                                   "artifact hash changed after compilation")
            report.events = [self._event(artifact, EventKind.ARTIFACT_INVALIDATED,
                                         "Schematic artifact changed before ERC", "erc-not-run")]
            return report
        if self.executable is None:
            return self._failure(artifact, ErcStatus.UNAVAILABLE, ToolStatus.UNAVAILABLE,
                                 "kicad-cli is unavailable")
        report_path = (report_path or artifact.path.with_suffix(".erc.json")).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        run_id = hashlib.sha256(
            f"{artifact.fingerprint.digest}:kicad-erc".encode()
        ).hexdigest()[:16]
        command = [
            self.executable, "sch", "erc", "--format", "json", "--severity-all",
            "--exit-code-violations", "--output", str(report_path), str(artifact.path),
        ]
        started = self._event(artifact, EventKind.ERC_STARTED, "KiCad ERC started", run_id)
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=self.timeout_seconds,
                check=False, shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            report = self._failure(artifact, ErcStatus.ERROR, ToolStatus.FAILED, str(exc))
            report.command = command
            report.events = [started]
            return report
        if not artifact.is_current:
            report = self._failure(artifact, ErcStatus.STALE_ARTIFACT, ToolStatus.FAILED,
                                   "artifact changed while ERC was running")
            report.command = command
            report.return_code = completed.returncode
            report.events = [started, self._event(artifact, EventKind.ARTIFACT_INVALIDATED,
                                                   "Schematic artifact changed during ERC", run_id)]
            return report
        try:
            report = parse_erc_json(
                report_path, artifact_fingerprint=artifact.fingerprint, run_id=run_id,
                command=command, return_code=completed.returncode,
                stdout=completed.stdout, stderr=completed.stderr,
            )
        except ErcReportParseError as exc:
            report = self._failure(artifact, ErcStatus.ERROR, ToolStatus.FAILED, str(exc))
            report.command = command
            report.return_code = completed.returncode
            report.stdout = completed.stdout
            report.stderr = completed.stderr
            report.events = [started]
            return report
        report.evidence = [Evidence(
            kind=EvidenceKind.ERC, label="KiCad schematic ERC",
            source_id=run_id,
            text_value=report.status.value,
            detail=f"KiCad {report.kicad_version}; artifact sha256={artifact.fingerprint.digest}",
        )]
        events = [started, self._event(artifact, EventKind.ERC_COMPLETED, "KiCad ERC completed", run_id)]
        for index, finding in enumerate(report.findings):
            events.append(self._event(
                artifact, EventKind.ERC_VIOLATION_FOUND,
                f"KiCad ERC: {finding.description}", run_id,
                payload={"index": index, "type": finding.type, "severity": finding.severity},
            ))
        report.events = events
        return report

    def run_drc(self, artifact: PcbArtifact, report_path: Path | None = None) -> DrcReport:
        if not artifact.lineage_is_current:
            return DrcReport(status=DrcStatus.STALE_ARTIFACT,tool_status=ToolStatus.FAILED,run_id="drc-not-run",pcb_fingerprint=artifact.fingerprint,source_schematic_fingerprint=artifact.schematic_fingerprint,stderr="PCB or source schematic artifact hash changed after compilation")
        if self.executable is None:
            return DrcReport(status=DrcStatus.UNAVAILABLE,tool_status=ToolStatus.UNAVAILABLE,run_id="drc-not-run",pcb_fingerprint=artifact.fingerprint,source_schematic_fingerprint=artifact.schematic_fingerprint,stderr="kicad-cli is unavailable")
        report_path=(report_path or artifact.path.with_suffix(".drc.json")).resolve();report_path.parent.mkdir(parents=True,exist_ok=True)
        run_id=hashlib.sha256(f"{artifact.fingerprint.digest}:kicad-drc".encode()).hexdigest()[:16]
        command=[self.executable,"pcb","drc","--format","json","--severity-all","--exit-code-violations","--output",str(report_path),str(artifact.path)]
        started=self._pcb_event(artifact,EventKind.DRC_STARTED,"KiCad DRC started",run_id)
        try: completed=subprocess.run(command,capture_output=True,text=True,timeout=self.timeout_seconds,check=False,shell=False)
        except (OSError,subprocess.SubprocessError) as exc:
            return DrcReport(status=DrcStatus.ERROR,tool_status=ToolStatus.FAILED,run_id=run_id,pcb_fingerprint=artifact.fingerprint,source_schematic_fingerprint=artifact.schematic_fingerprint,command=command,stderr=str(exc),events=[started])
        if not artifact.lineage_is_current:
            return DrcReport(status=DrcStatus.STALE_ARTIFACT,tool_status=ToolStatus.FAILED,run_id=run_id,pcb_fingerprint=artifact.fingerprint,source_schematic_fingerprint=artifact.schematic_fingerprint,command=command,stderr="PCB or source schematic changed during DRC",events=[started])
        try: report=parse_drc_json(report_path,pcb_fingerprint=artifact.fingerprint,schematic_fingerprint=artifact.schematic_fingerprint,run_id=run_id,command=command,return_code=completed.returncode,stdout=completed.stdout,stderr=completed.stderr)
        except DrcReportParseError as exc:
            return DrcReport(status=DrcStatus.ERROR,tool_status=ToolStatus.FAILED,run_id=run_id,pcb_fingerprint=artifact.fingerprint,source_schematic_fingerprint=artifact.schematic_fingerprint,command=command,return_code=completed.returncode,stdout=completed.stdout,stderr=str(exc),events=[started])
        report.evidence=[Evidence(kind=EvidenceKind.DRC,label="KiCad PCB DRC",source_id=run_id,text_value=report.status.value,detail=f"KiCad {report.kicad_version}; PCB sha256={artifact.fingerprint.digest}")]
        events=[started,self._pcb_event(artifact,EventKind.DRC_COMPLETED,"KiCad DRC completed",run_id)]
        for i,finding in enumerate(report.findings+report.unconnected_items): events.append(self._pcb_event(artifact,EventKind.DRC_FINDING_RECORDED,f"KiCad DRC: {finding.description}",run_id,{"index":i,"type":finding.type,"severity":finding.severity}))
        report.events=events;return report

    @staticmethod
    def _failure(artifact, status, tool_status, detail):
        return ErcReport(
            status=status, tool_status=tool_status, run_id="erc-not-run",
            artifact_fingerprint=artifact.fingerprint, stderr=detail,
        )

    @staticmethod
    def _event(artifact, kind, summary, run_id, payload=None):
        identity = f"{run_id}:{kind.value}:{summary}:{payload!r}"
        return EngineeringEvent(
            event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],
            kind=kind, summary=summary,
            circuit_content_hash=artifact.circuit_content_hash,
            payload=payload or {"run_id": run_id, "artifact_sha256": artifact.fingerprint.digest},
        )

    @staticmethod
    def _pcb_event(artifact,kind,summary,run_id,payload=None):
        identity=f"{run_id}:{kind.value}:{summary}:{payload!r}"
        return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=artifact.circuit_content_hash,payload=payload or {"run_id":run_id,"pcb_sha256":artifact.fingerprint.digest})
