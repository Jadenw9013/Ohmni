# Pre hackathon setup verification

Prepared October 16, 2026 on main baseline `527bc9dc`, with local uncommitted
preparation changes. Owner-authorized scope: setup tooling, a dependency extra,
submission/handoff templates and troubleshooting. Actual Fetch runtime work
remains reserved for the hackathon. No push, deployment or registration was performed.

## Implemented

- `scripts/setup_hackathon.py`: create/reuse `.venv`, install the declared extras
  and Chromium, check dependencies, validate the ledger and run local preflight.
- `fetch` extra: uAgents 0.26.1 and uagents-core 0.4.12. No agent entry point added.
- Strict preflight switches for Fetch/MCP dependencies and browser prerequisites.
- New submission, handoff and troubleshooting documents linked from entry points.
- CI job for a fresh Linux backend setup and focused tests, without agent startup.

## Local verification

| Check | Result |
|---|---|
| `python scripts/setup_hackathon.py --board` | PASS in the existing macOS checkout; installed extras, checked Chromium and native KiCad |
| `python scripts/setup_hackathon.py --check --board` | PASS without package/browser installation |
| `python scripts/setup_hackathon.py --check --skip-browser` | PASS for backend-only checks |
| Fresh macOS checkout with a newly created venv, `python3.13 scripts/setup_hackathon.py --skip-browser` | PASS; all 9 focused tests also passed in that venv |
| `python -m pytest tests/test_hackathon_setup.py` | 9 passed |
| Ruff on setup/preflight scripts and focused tests | PASS |
| `python scripts/ai_state.py validate` | VALID; no interrupted task |
| Local Markdown targets and `git diff --check` | PASS |
| `python scripts/verify.py fast` | 2733 passed, 101 skipped, 65 deselected; 5 dependency deprecation warnings |

Focused cases cover refusal of incompatible/missing environments, no installs in
check mode, dependency/browser install failure, backend-only setup, strict SDK
version checking, Windows paths with spaces and installed ACP handler/schema
compatibility. The ACP smoke check does not construct or start an Agent.

## Limits

The bootstrap passed with both the existing venv and a fresh macOS checkout/venv,
but not a fresh Windows install. Fresh Linux setup is configured in CI but cannot be claimed
passed until that workflow runs. Direct SDK pins are not a complete transitive
dependency lock. Native tool qualification remains separate from setup success;
earlier local engineering results are in [engineering setup](../LOCAL_ENGINEERING_SETUP.md).

The project-license warning remains visible. No license was selected, account
activated, model call made or actual Fetch integration implemented by this task.
