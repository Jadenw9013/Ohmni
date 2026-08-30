#!/usr/bin/env python3
"""Validate and query Ohmni's repository-resident AI development state.

The ``.yaml`` files intentionally use JSON syntax, which is valid YAML 1.2 and
keeps this development tool dependency-free. This module is not part of the
installable Ohmni product package.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALID_TASK_STATUSES = {
    "PROPOSED", "APPROVED", "READY", "IN_PROGRESS", "IMPLEMENTED",
    "VERIFIED", "BLOCKED", "COMPLETE", "CANCELLED",
}
EXECUTABLE_STATUSES = {"APPROVED", "READY"}
BLOCKING_SEVERITIES = {"BLOCKER", "HIGH"}
RESOLVED_FINDING_STATUSES = {"FIXED", "INVALID_WITH_EVIDENCE", "ACCEPTED_RISK"}


class StateError(ValueError):
    """The repository control plane is internally inconsistent."""


@dataclass(frozen=True)
class ControlPlane:
    root: Path
    state: dict[str, Any]
    task_data: dict[str, Any]
    review_data: dict[str, Any]
    milestone_data: dict[str, Any]

    @property
    def tasks(self) -> dict[str, dict[str, Any]]:
        return {task["id"]: task for task in self.task_data.get("tasks", [])}

    @property
    def scopes(self) -> dict[str, dict[str, Any]]:
        return {scope["id"]: scope for scope in self.task_data.get("scopes", [])}


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"missing control-plane file: {path.relative_to(path.parents[1])}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"invalid JSON-compatible YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StateError(f"{path} must contain an object")
    return value


def load_control_plane(root: Path = ROOT) -> ControlPlane:
    ai = root / ".ai"
    return ControlPlane(
        root=root,
        state=_load(ai / "state.yaml"),
        task_data=_load(ai / "tasks.yaml"),
        review_data=_load(ai / "reviews.yaml"),
        milestone_data=_load(ai / "milestones.yaml"),
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False, shell=False
    )


def git_commit_exists(root: Path, commit: str) -> bool:
    return _git(root, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0


def git_head(root: Path) -> str:
    result = _git(root, "rev-parse", "--short", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def git_dirty_files(root: Path) -> list[str]:
    result = _git(root, "status", "--porcelain")
    return [line[3:] for line in result.stdout.splitlines() if len(line) >= 4]


def dependency_complete(task: dict[str, Any], tasks: dict[str, dict[str, Any]]) -> bool:
    return all(dep in tasks and tasks[dep]["status"] == "COMPLETE" for dep in task.get("dependencies", []))


def executable_tasks(control: ControlPlane) -> list[dict[str, Any]]:
    scope_id = control.state.get("approved_product_scope")
    if not scope_id:
        return []
    scope = control.scopes.get(scope_id)
    if not scope or scope.get("status") not in {"APPROVED", "IN_PROGRESS"}:
        return []
    if scope.get("approved_by") != "human" or not scope.get("approval_evidence"):
        return []
    tasks = control.tasks
    candidates = [
        task for task in tasks.values()
        if task.get("scope") == scope_id
        and task.get("status") in EXECUTABLE_STATUSES
        and not task.get("blockers")
        and dependency_complete(task, tasks)
    ]
    return sorted(candidates, key=lambda task: (-int(task.get("priority", 0)), task["id"]))


def next_task(control: ControlPlane) -> tuple[dict[str, Any] | None, str]:
    if control.state.get("active_task"):
        return None, f"active task {control.state['active_task']} must be recovered or completed"
    if not control.state.get("approved_product_scope"):
        return None, "no human-approved product milestone"
    candidates = executable_tasks(control)
    if not candidates:
        return None, "approved scope has no dependency-satisfied unblocked task"
    return candidates[0], ""


def recovery_state(control: ControlPlane) -> tuple[str, str]:
    active = control.state.get("active_task")
    in_progress = [task for task in control.tasks.values() if task.get("status") == "IN_PROGRESS"]
    checkpoint = _load(control.root / ".ai" / "checkpoint.yaml")
    if not active and not in_progress:
        return "NONE", "no interrupted task"
    if len(in_progress) != 1 or not active or in_progress[0]["id"] != active:
        return "INCONSISTENT", "active-task summary and IN_PROGRESS task ledger disagree"
    task = in_progress[0]
    if checkpoint.get("active_task") != active:
        return "INCONSISTENT", "checkpoint does not identify the active task"
    dirty = git_dirty_files(control.root)
    completed = task.get("implementation", {}).get("completed_at_commit")
    record = task.get("verification", {}).get("record")
    if completed and record and not dirty:
        return "RECONCILE", "work appears committed and verified; reconcile interrupted ledger update"
    if dirty:
        return "RESUME", "uncommitted work exists; inspect checkpoint and resume the active task"
    if checkpoint.get("last_failure"):
        return "DEBUG", "checkpoint records a failure; reproduce it before changing tasks"
    return "RESUME", "active work has no completion evidence; inspect recent commits and resume"


def validate(control: ControlPlane, *, check_git: bool = True) -> list[str]:
    errors: list[str] = []
    tasks = control.tasks
    scopes = control.scopes
    if len(tasks) != len(control.task_data.get("tasks", [])):
        errors.append("duplicate task ID")
    in_progress = [task["id"] for task in tasks.values() if task.get("status") == "IN_PROGRESS"]
    if len(in_progress) > 1:
        errors.append(f"multiple IN_PROGRESS tasks: {in_progress}")
    active = control.state.get("active_task")
    if active and active not in tasks:
        errors.append(f"active task does not exist: {active}")
    elif active and tasks[active].get("status") != "IN_PROGRESS":
        errors.append(f"active task {active} is not IN_PROGRESS")
    if bool(active) != bool(in_progress):
        errors.append("state active_task and task-ledger IN_PROGRESS state disagree")
    for task in tasks.values():
        task_id = task.get("id", "<missing>")
        if task.get("status") not in VALID_TASK_STATUSES:
            errors.append(f"{task_id}: invalid status {task.get('status')}")
        if task.get("scope") not in scopes:
            errors.append(f"{task_id}: missing scope {task.get('scope')}")
        for dependency in task.get("dependencies", []):
            if dependency not in tasks:
                errors.append(f"{task_id}: nonexistent dependency {dependency}")
        if (
            task.get("status") == "READY"
            and all(dep in tasks for dep in task.get("dependencies", []))
            and not dependency_complete(task, tasks)
        ):
            errors.append(f"{task_id}: READY with incomplete dependency")
        if task.get("status") == "COMPLETE":
            record = task.get("verification", {}).get("record")
            if not record or not (control.root / record).is_file():
                errors.append(f"{task_id}: COMPLETE without verification record")
            if not task.get("implementation", {}).get("completed_at_commit"):
                errors.append(f"{task_id}: COMPLETE without implementation commit")
            review = task.get("review", {})
            if review.get("required") and review.get("status") != "PASSED":
                errors.append(f"{task_id}: COMPLETE without required passed review")
    approved = control.state.get("approved_product_scope")
    if approved:
        scope = scopes.get(approved)
        if not scope:
            errors.append(f"approved product scope does not exist: {approved}")
        elif scope.get("approved_by") != "human" or not scope.get("approval_evidence"):
            errors.append(f"approved product scope lacks human approval evidence: {approved}")
    expected_ready = [task["id"] for task in executable_tasks(control)]
    if control.state.get("next_ready_tasks", []) != expected_ready:
        errors.append("state next_ready_tasks disagrees with deterministic task ledger")
    expected_blocked = sorted(
        task["id"] for task in tasks.values()
        if task.get("status") == "BLOCKED" or task.get("blockers")
    )
    if sorted(control.state.get("blocked_tasks", [])) != expected_blocked:
        errors.append("state blocked_tasks disagrees with task ledger")
    findings = control.review_data.get("findings", [])
    for scope in scopes.values():
        if scope.get("status") == "COMPLETE":
            open_blocking = [
                finding["id"] for finding in findings
                if finding.get("scope") == scope["id"]
                and finding.get("severity") in BLOCKING_SEVERITIES
                and finding.get("status") not in RESOLVED_FINDING_STATUSES
            ]
            if open_blocking:
                errors.append(f"{scope['id']}: COMPLETE with open blocking findings {open_blocking}")
    baseline = control.state.get("baseline", {}).get("commit")
    if check_git and (not baseline or not git_commit_exists(control.root, baseline)):
        errors.append(f"baseline commit is missing: {baseline}")
    return errors


def _cmd_validate(control: ControlPlane) -> int:
    errors = validate(control)
    if errors:
        print("INVALID AI DEVELOPMENT STATE")
        for error in errors:
            print(f"- {error}")
        return 1
    recovery, detail = recovery_state(control)
    print("VALID AI DEVELOPMENT STATE")
    print(f"Recovery: {recovery} - {detail}")
    return 0


def _cmd_next(control: ControlPlane) -> int:
    task, reason = next_task(control)
    if task:
        print(f"NEXT: {task['id']} - {task['title']}")
        return 0
    print("NO EXECUTABLE TASK")
    print(f"Reason: {reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "next", "recovery"))
    args = parser.parse_args(argv)
    try:
        control = load_control_plane()
        if args.command == "validate":
            return _cmd_validate(control)
        if args.command == "next":
            return _cmd_next(control)
        status, detail = recovery_state(control)
        print(f"{status}: {detail}")
        return 1 if status == "INCONSISTENT" else 0
    except StateError as exc:
        print(f"INVALID AI DEVELOPMENT STATE\n- {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
