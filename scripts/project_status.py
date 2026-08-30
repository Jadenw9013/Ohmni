#!/usr/bin/env python3
"""Print the concise, repository-derived Ohmni development status."""

from __future__ import annotations

from ai_state import git_dirty_files, git_head, load_control_plane, next_task, recovery_state


def main() -> int:
    control = load_control_plane()
    dirty = git_dirty_files(control.root)
    task, reason = next_task(control)
    recovery, recovery_detail = recovery_state(control)
    latest = control.state["latest_product_milestone"]
    last_verification = control.state.get("last_verification") or {}
    last_review = control.state.get("last_review") or {}
    print("OHMNI DEVELOPMENT STATUS\n")
    print(f"Repository HEAD: {git_head(control.root)}")
    print(f"Recorded baseline: {control.state['baseline']['commit']}")
    print(f"Latest product milestone: {latest['id']} @ {latest['commit']} - {latest['title']}")
    print(f"Working tree: {'dirty (' + str(len(dirty)) + ' paths)' if dirty else 'clean'}")
    print(f"Approved product scope: {control.state.get('approved_product_scope') or 'none'}")
    print(f"Active task: {control.state.get('active_task') or 'none'}")
    print(f"Next executable product task: {task['id'] if task else 'none'}")
    if not task:
        print(f"Next-task reason: {reason}")
    print(f"Blocked tasks: {len(control.state.get('blocked_tasks', []))}")
    print(f"Last verification: {last_verification.get('id', 'none')} @ {last_verification.get('commit', 'none')}")
    print(f"Last independent review: {last_review.get('status', 'none')} (independent={last_review.get('independent', False)})")
    print(f"Recovery: {recovery} - {recovery_detail}")
    status = "AWAITING HUMAN MILESTONE APPROVAL" if not control.state.get("approved_product_scope") else control.state["status"]
    print(f"\nStatus: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

