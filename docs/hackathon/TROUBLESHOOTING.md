# Hackathon setup and demo troubleshooting

Start from the repository root. Use the checkout's `.venv` Python, not whichever
interpreter an editor happens to select. Commands below assume the venv is active;
Windows can use `.\.venv\Scripts\python.exe` explicitly.

## Fast diagnosis

```sh
python scripts/setup_hackathon.py --check --board
python -m ohmni doctor
python -m pip check
python scripts/ai_state.py validate
```

The setup command installs nothing in `--check` mode. It requires the pinned
Fetch/MCP packages and, unless skipped, the matching Chromium executable. It
does not establish an agent connection or execute a board build. Read warnings
even when it exits 0. See [engineering setup](../LOCAL_ENGINEERING_SETUP.md) for
the actual native installers and [team setup](../TEAM_SETUP.md) for platform details.

## Environment problems

| Symptom | Check | Recovery |
|---|---|---|
| Python 3.14 or unsupported interpreter | `python --version` | Run `python3.13 scripts/setup_hackathon.py` or `py -3.13 scripts/setup_hackathon.py`; select `.venv` in the editor |
| Existing venv has wrong Python or is incomplete | Run setup; it refuses to overwrite it | Stop its processes, rename `.venv` to preserve it, then rerun with Python 3.13 |
| Packages missing or wrong SDK pin | `python scripts/hackathon_preflight.py --fetch` | Rerun setup without `--check`; install the declared extras together |
| Dependency conflict | `python -m pip check` | Use a fresh venv; record the error before changing pins; one integration owner changes dependencies |
| pip download fails | Read the install error; check network/proxy and free disk | Retry when connectivity is restored; do not disable certificate checks or silently skip dependencies |
| Chromium missing | `python scripts/hackathon_preflight.py --browser` | `python -m playwright install chromium`; Linux may require `python -m playwright install --with-deps chromium` |
| Backend-only machine cannot install Chromium | No browser work assigned | Use setup `--skip-browser`; browser acceptance still needs another qualified host |
| Disk fills during setup | Check free disk | Remove only your disposable downloads/build outputs after preserving needed evidence; never automatically prune others' Docker data |
| Windows activation blocked | Shell execution policy message | Use `.\.venv\Scripts\python.exe` directly; activation is optional |
| WSL cannot see Windows Python | `python --version` inside WSL | Install Python within WSL or use native PowerShell consistently; do not mix venvs |

## Native engineering problems

| Symptom | Check | Recovery |
|---|---|---|
| KiCad unavailable | `python -m ohmni doctor` | Install complete KiCad 10.0.5 with libraries; restart shell or use its standard installation location |
| Board harness returns BLOCKED | Inspect its summary and CLI version | Use pinned 10.0.5; do not change the expected version just to pass |
| KiCad missing symbol or footprint libraries | Inspect ERC/DRC report and install layout | Install the complete distribution, not a copied executable; keep warnings visible |
| ngspice unavailable or version differs | `ngspice -v` and doctor | Install console ngspice 42; follow the macOS compiler workaround in engineering setup |
| Doctor says Freerouting unavailable | Existing router is Ohmni's own | No action required for the hackathon workflow |
| Docker command exists but daemon is unavailable | `docker info` | Start Docker Desktop/daemon; CLI installation alone is insufficient |
| Plain KiCad image fails simulation version checks | `ngspice -v` inside that environment | That image is not the pinned simulation environment; use qualified native 42 or the separate production image path |
| Build reports incomplete routing or failed ERC/DRC | Actual job reports | Preserve failure and limitations; use a known qualified configuration or saved fallback, never relabel it PASS |

## Local server and workspace problems

The normal workspace uses `http://127.0.0.1:8765/#workspace`. The saved demo can
run separately with `python scripts/serve_offline_demo.py --port 8766`.

- **Port already in use:** inspect which process owns it. On macOS/Linux use
  `lsof -nP -iTCP:8765 -sTCP:LISTEN`; on Windows use
  `Get-NetTCPConnection -LocalPort 8765 -State Listen`. Stop only your known
  server, or run the saved fallback on 8766. Do not kill arbitrary Python processes.
- **Workspace lock or database busy:** stop the previous owner process. Give each
  concurrent checkout its own absolute `OHMNI_OUTPUT_DIR` before starting the server.
  Do not remove a live lock file or share a SQLite workspace between assistants.
- **Old UI/server identity mismatch:** restart the local server from the intended
  checkout and reload the local page. Preserve drafts first. A Vercel preview can
  call production; use localhost during development.
- **AI unavailable:** guided setup and saved demos still work. For authorized live
  AI, the demo server reads root `.env`; check filename and variable names without
  printing secrets. Other entry points do not automatically load `.env`.
- **Budget rejection or provider failure:** keep the refusal visible and use guided
  recovery. Do not bypass admission limits or repeatedly retry paid requests.
- **Stopped or interrupted job:** inspect its recorded state and start a new attempt
  only when needed. Reopening a saved run is different from generating a new board.

## Fetch issues to test during the hackathon

The Fetch runtime is intentionally not implemented yet. These are acceptance
checks for that future work, not claims that commands or endpoints already exist.

- Installed SDK does not mean registered agent. Test a real ASI:One tool round trip.
- An empty ACP protocol fails verification; handlers must cover both message and
  acknowledgement types in the pinned specification.
- A local SDK example may attempt ledger discovery during Agent construction.
  Use protocol/schema-only checks for offline preparation; do not run registration
  examples with real credentials as an installation test.
- If discovery fails, check the running agent, registration, profile and quotas.
  Test direct selection separately from ordinary discovery.
- If confirmation loses context, inspect stored sender/session ownership and plan
  state; do not assume chat history is automatic.
- If long jobs time out in chat, use the tested progress/status design. Never
  claim an acknowledgement is a completed engineering run.

Use the reduction gates in the [implementation plan](FETCH_AI_IMPLEMENTATION_PLAN.md).
For handoff, report the exact command, interpreter/tool versions, sanitized error,
branch/commit and next action. Never include keys, seeds or private user requests.
