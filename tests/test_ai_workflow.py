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


def test_repository_product_scope_matches_human_approval():
    root=Path(__file__).resolve().parents[1]
    state=json.loads((root/".ai"/"state.yaml").read_text())
    tasks=json.loads((root/".ai"/"tasks.yaml").read_text())
    milestones=json.loads((root/".ai"/"milestones.yaml").read_text())
    assert state["latest_product_milestone"]["id"]=="M9"
    assert state["latest_product_milestone"]["status"]=="COMPLETE"
    # Visual and release approval preserve the real board and parked M10 benchmark.
    for scope in tasks["scopes"]:
        assert scope["approved_by"]=="human" and scope["approval_evidence"]
        if scope["id"] in {"VIS-REF-001", "DEPLOY-1", "COMPONENT-SYNTHESIS-1", "COMPONENT-ATLAS-BUILDER-1", "UX-CLARITY-1", "REPO-READY-1", "COMPONENT-3D-STAGE1", "COMPONENT-3D-STAGE2"}:
            assert scope["status"] in {"APPROVED", "IN_PROGRESS", "REVIEW", "VERIFIED", "COMPLETE"}
        else:
            expected="IN_PROGRESS" if scope["id"]=="M10" else "COMPLETE"
            assert scope["status"]==expected, scope["id"]
    assert state["approved_product_scope"]=="COMPONENT-3D-STAGE2"
    stage1=json.loads((root/".ai/approvals/COMPONENT-3D-STAGE1.yaml").read_text())
    assert stage1["approved_by"]=="human"
    assert len(stage1["component_ids"])==20
    assert {"OHM-004", "OHM-014", "OHM-023", "OHM-041", "OHM-043"} <= set(stage1["component_ids"])
    assert "Stage 2" in stage1["non_goals"]
    stage2=json.loads((root/".ai/approvals/COMPONENT-3D-STAGE2.yaml").read_text())
    assert stage2["approved_by"]=="human"
    assert len(stage2["component_ids"])==21
    assert "Stage 3" in stage2["non_goals"]
    publication=json.loads((root/".ai/approvals/REPO-READY-1.yaml").read_text())
    assert publication["approved_by"]=="human"
    assert "if its clean push to main" in publication["instructions"]
    assert any("do not begin CS-T05 or CAB-T05" in item for item in publication["boundaries"])
    ux=json.loads((root/".ai/approvals/UX-CLARITY-1.yaml").read_text())
    assert ux["approved_by"]=="human"
    assert "UI/UX" in ux["instruction"]
    assert ux["preserved_previous_checkpoint"]["active_task"] is None
    atlas=json.loads((root/".ai/approvals/COMPONENT-ATLAS-BUILDER-1.yaml").read_text())
    assert atlas["approved_by"]=="human"
    assert atlas["instruction"]=="ok begin implementing"
    assert atlas["plan_document"]=="docs/product/THREE_D_COMPONENT_ATLAS_AND_BOARD_BUILDER_PLAN.md"
    assert atlas["preserved_previous_checkpoint"]["active_task"] is None
    addition=next(task for task in tasks["tasks"] if task["id"]=="CAB-T07")
    assert {"CS-T07", "CS-T08"} <= set(addition["dependencies"])
    synthesis=json.loads((root/".ai/approvals/COMPONENT-SYNTHESIS-1.yaml").read_text())
    assert synthesis["approved_by"]=="human"
    assert "HUMAN APPROVAL: I approve COMPONENT-SYNTHESIS-1" in synthesis["instruction"]
    assert synthesis["plan_document"]=="COMPONENT_SYNTHESIS_PLAN.md"
    # The approval binds every stated support boundary; none of them is optional.
    assert any("never become PASS" in item for item in synthesis["binding_constraints"])
    assert any("CS-T07" in item for item in synthesis["binding_constraints"])
    assert synthesis["execution_instruction"]["session_stop_after"]=="CS-T04"
    deployment=json.loads((root/".ai/approvals/DEPLOY-1.yaml").read_text())
    assert deployment["approved_by"]=="human"
    assert deployment["instruction"]=="go a head push deploy"
    visual=json.loads((root/".ai/approvals/VIS-REF-001.yaml").read_text())
    assert visual["approved_by"]=="human" and visual["approved_implementation"]=="W0-W7"
    assert visual["planning_only"]=="W8" and visual["plan_sha256"]
    assert "HUMAN APPROVAL: VIS-REF-001" in visual["instruction"]
    explorer=json.loads((root/".ai/approvals/PCB-EXPLORER-1.yaml").read_text())
    assert explorer["approved_by"]=="human"
    assert explorer["functional_choice"]=="ESP32 sensor-and-controller board"
    parked=next(task for task in tasks["tasks"] if task["id"]=="M10-T05")
    assert parked["status"]=="BLOCKED" and parked["blockers"]
    approval=json.loads((root/".ai/approvals/MCP-SEMANTIC-1.yaml").read_text())
    assert "NO_PATH" in json.dumps(approval["preserved_m10_t05_checkpoint"])
    # A session may be between completed units; any active task must belong to
    # the approved scope rather than pinning this approval test to one task.
    if state["active_task"] is not None:
        current=next(task for task in tasks["tasks"] if task["id"]==state["active_task"])
        assert current["scope"]==state["approved_product_scope"]
        assert current["status"]=="IN_PROGRESS"
    active=milestones["active_product_milestone"]
    assert active["id"]=="M10" and active["status"]=="IN_PROGRESS"
    assert active["approved_by"]=="human" and active["approval_evidence"]
    # A completed task whose review was required must carry a passed review.
    for task in tasks["tasks"]:
        if task["status"]=="COMPLETE" and task.get("review",{}).get("required"):
            assert task["review"]["status"]=="PASSED", task["id"]
    # M11 onwards stay proposed and unapproved until a human says otherwise.
    later={f"M{n}" for n in range(11,16)}
    assert all(item["id"] not in later for item in tasks["scopes"]+tasks["tasks"])
    proposed=milestones["proposed_product_milestones"]
    assert {item["id"] for item in proposed}==later
    assert all(item["status"]=="PROPOSED" and item["approved_by"] is None for item in proposed)
