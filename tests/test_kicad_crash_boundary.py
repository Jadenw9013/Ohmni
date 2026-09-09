"""Native exits and stale JSON never become a successful engineering check.

Every subprocess in this file is stubbed; no installed KiCad process is run.
"""

import json
import subprocess
from types import SimpleNamespace

import pytest

from ohmni.eda.kicad import KiCadCliAdapter, KiCadPcbCompiler, KiCadSchematicCompiler
from ohmni.eda.kicad.parser import ErcReportParseError, parse_erc_json
from ohmni.eda.kicad.pcb_parser import DrcReportParseError, parse_drc_json
from ohmni.eda.models import ArtifactFingerprint
from ohmni.physical.placement import generate_placement
from ohmni.synthesis import SynthesisBrief, synthesize

FP=ArtifactFingerprint(digest="a"*64)


def _payload(kind,severity=None):
    findings=[] if severity is None else [{"type":"test","severity":severity,"description":"test"}]
    return ({"kicad_version":"10.0.5","sheets":[{"violations":findings}]} if kind=="erc" else
            {"kicad_version":"10.0.5","violations":findings,"unconnected_items":[]})


def _parse(kind,path,code):
    kwargs={"run_id":"stub","command":["kicad-cli","--exit-code-violations"],"return_code":code}
    return (parse_erc_json(path,artifact_fingerprint=FP,**kwargs) if kind=="erc" else
            parse_drc_json(path,pcb_fingerprint=FP,schematic_fingerprint=FP,**kwargs))


@pytest.mark.parametrize("kind",["erc","drc"])
@pytest.mark.parametrize("code",[1,2,3,4,6,-11,-1073741819,3221225477])
def test_crash_exit_cannot_accept_even_fresh_valid_clean_json(tmp_path,kind,code):
    path=tmp_path/"clean.json";path.write_text(json.dumps(_payload(kind)))
    with pytest.raises((ErcReportParseError,DrcReportParseError),match="did not complete") as caught:
        _parse(kind,path,code)
    if code in {-1073741819,3221225477}:assert "0xC0000005" in str(caught.value)


@pytest.mark.parametrize("kind",["erc","drc"])
@pytest.mark.parametrize("code,severity,expected",[(0,None,"pass"),(5,"warning","pass_with_warnings"),
    (5,"error","fail"),(5,None,None),(0,"warning",None),(0,"error",None),(0,"unknown",None)])
def test_documented_success_and_violation_exits_match_report(tmp_path,kind,code,severity,expected):
    path=tmp_path/"check.json";path.write_text(json.dumps(_payload(kind,severity)))
    if expected is None:
        with pytest.raises((ErcReportParseError,DrcReportParseError)):_parse(kind,path,code)
    else:
        assert _parse(kind,path,code).status.value==expected


@pytest.fixture(scope="module")
def compiled_artifacts(tmp_path_factory,catalog):
    destination=tmp_path_factory.mktemp("crash-boundary")
    result=synthesize(SynthesisBrief(status_led_count=0,include_programming_header=False))
    board=generate_placement(result.circuit,result.placement_request,catalog).board
    schematic=KiCadSchematicCompiler(catalog).compile(result.circuit,destination/"source.kicad_sch")
    pcb=KiCadPcbCompiler(catalog).compile(result.circuit,schematic,board,destination/"source.kicad_pcb")
    return {"erc":schematic,"drc":pcb}


@pytest.mark.parametrize("kind",["erc","drc"])
@pytest.mark.parametrize("code,write_new",[(0,False),(3221225477,False),(3221225477,True)])
def test_adapter_removes_old_pass_before_launch_and_retains_failed_exit(tmp_path,monkeypatch,compiled_artifacts,kind,code,write_new):
    from ohmni.eda.kicad import erc
    path=tmp_path/f"check.{kind}.json";path.write_text(json.dumps(_payload(kind)))
    calls=[]
    def native(command,*,timeout):
        calls.append(command)
        assert timeout==3 and not path.exists()
        if write_new:path.write_text(json.dumps(_payload(kind)))
        return SimpleNamespace(returncode=code,stdout="native stdout",stderr="native stderr")
    monkeypatch.setattr(erc,"run_tool",native)
    report=getattr(KiCadCliAdapter(executable="stub-only",timeout_seconds=3),f"run_{kind}")(
        compiled_artifacts[kind],path)
    assert len(calls)==1 and report.status.value=="error" and report.tool_status.value=="failed"
    assert report.return_code==code and report.stdout=="native stdout"
    assert "native stderr" in report.stderr and not report.evidence
    if code==3221225477:assert "0xC0000005" in report.stderr
    assert not any(event.kind.value.endswith("completed") for event in report.events)


@pytest.mark.parametrize("kind",["erc","drc"])
def test_timeout_cannot_reuse_old_successful_json(tmp_path,monkeypatch,compiled_artifacts,kind):
    from ohmni.eda.kicad import erc
    path=tmp_path/"old.json";path.write_text(json.dumps(_payload(kind)))
    def native(command,*,timeout):
        assert not path.exists()
        raise subprocess.TimeoutExpired(command,timeout)
    monkeypatch.setattr(erc,"run_tool",native)
    report=getattr(KiCadCliAdapter(executable="stub-only"),f"run_{kind}")(compiled_artifacts[kind],path)
    assert report.status.value=="error" and not report.evidence and not path.exists()


@pytest.mark.parametrize("kind",["erc","drc"])
def test_report_path_cannot_delete_input_artifact(monkeypatch,compiled_artifacts,kind):
    from ohmni.eda.kicad import erc
    def native(*_args,**_kwargs):raise AssertionError("unsafe report path reached subprocess")
    monkeypatch.setattr(erc,"run_tool",native)
    artifact=compiled_artifacts[kind];before=artifact.path.read_bytes()
    report=getattr(KiCadCliAdapter(executable="stub-only"),f"run_{kind}")(artifact,artifact.path)
    assert report.status.value=="error" and artifact.path.read_bytes()==before


@pytest.mark.parametrize("status,tool_status,exception",[("error","failed","tool"),
    ("unavailable","unavailable","tool"),("fail","ok","circuit"),("fail","failed","circuit")])
def test_application_keeps_tool_failures_distinct_from_completed_circuit_violations(status,tool_status,exception):
    from ohmni.adapters import ToolStatus
    from ohmni.application.demo import EdaToolFailedError, require_eda_check
    from ohmni.eda.models import ErcStatus
    report=SimpleNamespace(status=ErcStatus(status),tool_status=ToolStatus(tool_status))
    with pytest.raises(RuntimeError) as caught:require_eda_check(report,"ERC")
    assert isinstance(caught.value,EdaToolFailedError) is (exception=="tool")


def test_personal_project_preserves_native_diagnostics_without_starting_placement(tmp_path,monkeypatch):
    from ohmni.application import projects
    from ohmni.application.demo import EdaToolFailedError
    from ohmni.eda.models import ErcReport
    def check(artifact):
        return ErcReport(status="error",tool_status="failed",run_id="stub-native-crash",
            artifact_fingerprint=artifact.fingerprint,return_code=3221225477,
            stderr="exit 0xC0000005 (access violation)")
    monkeypatch.setattr(projects,"KiCadCliAdapter",lambda:SimpleNamespace(run_erc=check))
    def placement_forbidden(*_args,**_kwargs):raise AssertionError("placement ran after failed ERC tool")
    monkeypatch.setattr(projects,"generate_placement",placement_forbidden)
    with pytest.raises(EdaToolFailedError):projects.ProjectPipeline().run(tmp_path,SynthesisBrief())
    saved=json.loads((tmp_path/"erc-report.json").read_text())
    assert saved["return_code"]==3221225477 and saved["status"]=="error"
    assert "0xC0000005" in saved["stderr"] and not (tmp_path/"golden.kicad_pcb").exists()
