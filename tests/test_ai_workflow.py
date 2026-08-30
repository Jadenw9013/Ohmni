"""Behavioral tests for the repository development control plane."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.ai_state import ControlPlane, executable_tasks, next_task, recovery_state, validate


def task(task_id="M8-T01",status="READY",priority=10,dependencies=None,scope="M8"):
    return {
        "id":task_id,"scope":scope,"milestone":"M8","title":task_id,"status":status,
        "priority":priority,"dependencies":dependencies or [],"goal":"test",
        "acceptance_criteria":["works"],"verification":{"required":["unit_tests"],"record":None},
        "implementation":{"started_at_commit":None,"completed_at_commit":None},
        "review":{"required":True,"status":"PENDING","independent":False},"blockers":[],
    }


def control(tmp_path:Path,tasks=None,approved="M8",active=None,scope_status="APPROVED",findings=None):
    (tmp_path/".ai"/"verification").mkdir(parents=True,exist_ok=True)
    checkpoint={"active_task":active,"last_failure":None}
    (tmp_path/".ai"/"checkpoint.yaml").write_text(json.dumps(checkpoint))
    state={"baseline":{"commit":"a"*40},"approved_product_scope":approved,"active_task":active,"next_ready_tasks":[],"blocked_tasks":[]}
    scope={"id":"M8","type":"product_milestone","status":scope_status,"approved_by":"human","approval_evidence":"human instruction"}
    cp=ControlPlane(tmp_path,state,{"scopes":[scope],"tasks":tasks or []},{"findings":findings or []},{})
    cp.state["next_ready_tasks"]=[item["id"] for item in executable_tasks(cp)]
    cp.state["blocked_tasks"]=sorted(item["id"] for item in cp.tasks.values() if item["status"]=="BLOCKED" or item["blockers"])
    return cp


def test_valid_state_passes(tmp_path):
    cp=control(tmp_path,[task()])
    assert validate(cp,check_git=False)==[]


def test_missing_active_task_and_two_active_tasks_fail(tmp_path):
    cp=control(tmp_path,[task("A",status="IN_PROGRESS")],active="MISSING")
    errors=validate(cp,check_git=False)
    assert any("does not exist" in error for error in errors)
    cp=control(tmp_path,[task("A",status="IN_PROGRESS"),task("B",status="IN_PROGRESS")],active="A")
    assert any("multiple IN_PROGRESS" in error for error in validate(cp,check_git=False))


def test_invalid_dependency_and_ready_with_unfinished_dependency_fail(tmp_path):
    cp=control(tmp_path,[task("A",dependencies=["MISSING"])])
    assert any("nonexistent dependency" in error for error in validate(cp,check_git=False))
    cp=control(tmp_path,[task("A",status="IMPLEMENTED"),task("B",dependencies=["A"])])
    assert any("READY with incomplete dependency" in error for error in validate(cp,check_git=False))


def test_complete_requires_commit_verification_and_review(tmp_path):
    completed=task(status="COMPLETE")
    cp=control(tmp_path,[completed])
    errors=validate(cp,check_git=False)
    assert any("verification record" in error for error in errors)
    assert any("implementation commit" in error for error in errors)
    assert any("passed review" in error for error in errors)


def test_proposed_task_never_executable_and_no_approved_scope_returns_none(tmp_path):
    cp=control(tmp_path,[task(status="PROPOSED")])
    assert executable_tasks(cp)==[]
    cp=control(tmp_path,[task()],approved=None)
    selected,reason=next_task(cp)
    assert selected is None and reason=="no human-approved product milestone"


def test_approval_requires_human_evidence(tmp_path):
    cp=control(tmp_path,[task()]);cp.task_data["scopes"][0]["approved_by"]="agent"
    cp.state["next_ready_tasks"]=[]
    assert executable_tasks(cp)==[]
    assert any("human approval evidence" in error for error in validate(cp,check_git=False))


def test_selection_is_priority_then_stable_id(tmp_path):
    cp=control(tmp_path,[task("M8-T03",priority=20),task("M8-T02",priority=20),task("M8-T01",priority=10)])
    assert [item["id"] for item in executable_tasks(cp)]==["M8-T02","M8-T03","M8-T01"]
    selected,_=next_task(cp)
    assert selected["id"]=="M8-T02"


def test_blocking_review_findings_prevent_complete_scope(tmp_path):
    finding={"id":"M8-R01","scope":"M8","severity":"HIGH","status":"OPEN"}
    cp=control(tmp_path,[task(status="VERIFIED")],scope_status="COMPLETE",findings=[finding])
    assert any("open blocking findings" in error for error in validate(cp,check_git=False))
    cp.review_data["findings"][0]["status"]="FIXED"
    assert not any("open blocking findings" in error for error in validate(cp,check_git=False))


def test_reviewer_unavailable_is_honest_and_cannot_complete_required_review(tmp_path):
    completed=task(status="COMPLETE")
    completed["implementation"]["completed_at_commit"]="b"*40
    completed["verification"]["record"]=".ai/verification/M8-T01.yaml"
    completed["review"]["status"]="UNAVAILABLE"
    cp=control(tmp_path,[completed])
    (tmp_path/".ai"/"verification"/"M8-T01.yaml").write_text("{}")
    assert any("required passed review" in error for error in validate(cp,check_git=False))


def test_stale_in_progress_detects_resume_reconcile_and_inconsistency(tmp_path):
    active=task(status="IN_PROGRESS")
    cp=control(tmp_path,[active],active=active["id"])
    with patch("scripts.ai_state.git_dirty_files",return_value=["src/change.py"]):
        assert recovery_state(cp)[0]=="RESUME"
    active["implementation"]["completed_at_commit"]="b"*40
    active["verification"]["record"]=".ai/verification/M8-T01.yaml"
    with patch("scripts.ai_state.git_dirty_files",return_value=[]):
        assert recovery_state(cp)[0]=="RECONCILE"
    cp.state["active_task"]="OTHER"
    assert recovery_state(cp)[0]=="INCONSISTENT"


def test_repository_bootstrap_has_no_approved_product_work():
    root=Path(__file__).resolve().parents[1]
    state=json.loads((root/".ai"/"state.yaml").read_text())
    assert state["latest_product_milestone"]["id"]=="M7"
    assert state["latest_product_milestone"]["commit"]=="43ffac5"
    assert state["approved_product_scope"] is None
