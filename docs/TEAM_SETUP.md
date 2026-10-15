# Teammate setup

Run commands from the repository root. Use a full Git clone, not a source ZIP or
shallow clone: the development ledger verifies historical commit references.
Do not copy another person's `.venv`, `.env`, `out/` or database.

## Choose the smallest setup you need

| Work | Requirements |
|---|---|
| Saved board demo | Git, Python 3.12+; no package install |
| Python/backend development | Python 3.13 recommended, isolated venv, `[dev]` extra |
| Frontend development/tests | Above for local API; Node 22 (CI) or newer for tests; no root npm build |
| Browser acceptance | `[dev,browser]`, matching Playwright Chromium |
| New board generation | KiCad CLI and its libraries; current CI image is KiCad 10.0.5 |
| Supported SPICE simulation | ngspice 42 console executable on PATH |
| Semantic MCP server | `[dev,mcp]`; no API key |

Python declares >=3.12; CI currently exercises 3.13 on Linux. Setup is checked
locally on Windows 11 and on macOS 26 (Apple silicon, Homebrew Python 3.13); see
[platform differences](#platform-differences) for what behaves differently on macOS.
Dependencies in `pyproject.toml` include ranges, so Python installs are not a fully
locked environment. Telemetry/MCP/Playwright SDKs are pinned; the browser bundle
has its own npm lockfile. Record versions when reporting a setup failure.

## Development setup

First clone (or fetch and create your branch if already cloned):

```text
git clone https://github.com/Jadenw9013/Ohmni.git
cd Ohmni
git fetch origin
git switch -c team/your-name-task origin/main
```

### Windows PowerShell

Install Python 3.13 and Git. These commands avoid activation-policy problems:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/ai_state.py validate
.\.venv\Scripts\python.exe scripts/project_status.py
.\.venv\Scripts\python.exe scripts/demo_server.py
```

### macOS or Linux

Install Python 3.13 and Git through your OS/package manager. On macOS with
Homebrew: `brew install python@3.13 node` (Git comes with the Xcode command line
tools). Some Linux installations also need the matching Python `venv` package.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/ai_state.py validate
.venv/bin/python scripts/project_status.py
.venv/bin/python scripts/demo_server.py
```

Open http://127.0.0.1:8765/#workspace. Ctrl+C stops the server. To use another
port: append `--port 8766`. Keep the default loopback host for local development.
In the rest of this guide, `python` means your venv Python (use its explicit path
or activate it). A successful startup is not proof that AI or native tools work.

## Credentials and configuration

No secret is required for the saved demo or offline tests. For authorized live
AI planning only, copy `.env.example` to `.env` and set your own
`ANTHROPIC_API_KEY`. The name must be exactly `.env` in the repository root:

- macOS: Finder hides and resists dot-files, so create it from the terminal with
  `cp .env.example .env` and edit it with `open -e .env` or your editor
  (Cmd+Shift+. shows hidden files in Finder). A file saved as `env` is neither
  loaded nor gitignored.
- Windows: Notepad may save `.env.txt`; choose "All files" as the type, or run
  `Copy-Item .env.example .env` and `notepad .env`. File Explorer hides
  extensions by default, so check the real name with `Get-ChildItem -Force`.

A UTF-8 byte-order mark and CRLF line endings are accepted. The test suite clears
`ANTHROPIC_API_KEY` for every test, so a local `.env` never reaches a live provider. Never paste it into a prompt, screenshot, issue or PR.
Obtain team credentials privately from the owner; don't reuse deployment secrets.

Only `scripts/demo_server.py` reads the root `.env`. Shell variables take
precedence. Its parser accepts plain `NAME=value` lines, **without quotes, shell
expansion or `export` prefixes**. `.env.local` is not loaded. Other CLI commands
do not automatically load `.env`; supply needed variables in their environment.
`OHMNI_ANTHROPIC_MODEL` is optional; leave it unset to use the code's default.
`OHMNI_OUTPUT_DIR` changes server storage (default `out/demo-jobs`). Use an
absolute local directory if overriding it, and a different one for each worktree.

Native-tool discovery uses PATH and supported fallback locations. The old
`OHMNI_KICAD_CLI`/`OHMNI_NGSPICE` example variables do not configure the current
discovery functions; put the executable directories on PATH instead.

Telemetry stays disabled by default. Do not enable Sentry, send paid model
requests, run a release/deploy command or test a production API without owner
approval. Vercel preview API rewrites can reach the production backend; a preview
URL is not an isolated test environment. Use localhost for development checks.

## Native tools: optional until your task needs them

Install KiCad with its standard symbol/footprint libraries, not just a copied
`kicad-cli` binary. Install ngspice's console executable for simulation work.
Add their executable directories to PATH and restart your shell. Check:

```text
kicad-cli --version
ngspice -v
python -m ohmni doctor
```

`doctor` reports availability; it returns success even when optional tools are
missing. Read each tool's status. An installed tool is not proof that a particular
board can route, pass ERC/DRC, or simulate. ngspice analyses are version-gated to
42. The bounded real-board CI gate uses KiCad 10.0.5.

For parity with the Linux KiCad gate, a POSIX shell with Docker can run:

```sh
scripts/run_in_kicad_image.sh python3 scripts/verify_hackathon_demo.py --attempts 1 --output-root build/team-kicad
```

This downloads a large container and packages, writes local outputs, and may take
several minutes. On Windows use WSL with Docker integration and a clone inside
WSL; do not reuse the Windows venv there. Do not run cloud deployment to install
a local tool. The saved demo needs none of these native dependencies.

## Checks before a PR

```text
python scripts/ai_state.py validate
python scripts/verify.py workflow
python scripts/verify.py fast
```

Run heavy suites serially. `fast` is offline but takes several minutes and may
honestly skip source/native-tool checks. A green fast suite is not a full EDA pass.
For frontend changes, with Node 22 installed:

PowerShell:
```powershell
$testFiles = @(Get-ChildItem apps/web/tests/*.test.mjs | Sort-Object Name | ForEach-Object FullName)
if ($testFiles.Count -eq 0) { throw 'No frontend tests found' }
node --test @testFiles
```

POSIX:
```sh
node --test apps/web/tests/*.test.mjs
```

For real browser acceptance:
```text
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium
python scripts/run_browser_acceptance.py --output build/browser-acceptance
```

On Linux CI uses `python -m playwright install --with-deps chromium` to install
OS libraries too (may require elevated OS package installation). Checks block
external traffic and use synthetic telemetry, but installing packages needs network.

Additional gates, depending on the change:

- `python scripts/acquire_corpus.py`, then `python scripts/verify.py corpus`:
  downloads and hash-checks the public pinned source corpus. It is distinct from
  the private behavior archive; see `docs/behavior/SOURCE_ARCHIVE.md` read-only.
  Missing or changed sources are a blocker, never permission to replace hashes.
- `python scripts/verify.py integration`, `simulation`, or `full`: native/tool and
  source prerequisites apply. Report skips and unavailable gates explicitly.
- `npm ci --prefix scripts/telemetry-browser --no-audit --no-fund`, then
  `node scripts/telemetry-browser/build.mjs --check`: check the committed SDK bundle.

CI configuration is authoritative: `.github/workflows/ci.yml`. No type checker or
formatter is configured. Don't claim a full verification from only lint or startup.

## Platform differences

| Area | Windows | macOS | Linux |
|---|---|---|---|
| Venv Python | `.venv\Scripts\python.exe` | `.venv/bin/python` | `.venv/bin/python` |
| Isolated datasheet worker memory cap | Job object | **Unavailable**: worker refuses to parse | `RLIMIT_AS` |
| KiCad parity gate | WSL + Docker | Docker | Docker or native |

macOS reserves hundreds of GiB of virtual address space in every process and
rejects any smaller `RLIMIT_AS`, and it offers no other per-process memory cap.
The isolated datasheet observation worker (used by
`scripts/component_cad_proof.py`) therefore fails closed on macOS with "refused to
parse unbounded". In `fast`, the tests that need a successfully bounded parse are
skipped on macOS and `TestMacOSFailsClosed` checks the refusal instead. Run
datasheet-isolation work on Windows, Linux, or in the Docker image. The demo
server, saved demo and the rest of the suite are unaffected.

Node's default test reporter changed in newer releases, so the frontend test
wrapper and CI pin `--test-reporter=tap`; any Node 22 or newer works.

## Working together

1. Agree on a bounded task and file ownership. Read `AGENTS.md` and the current
   `.ai` records before editing. Proposed backlog is not authorization.
2. Fetch latest `origin/main`; branch from it. Each teammate uses their own clone
   or worktree and venv. Never reset or stash another person's changes.
3. Keep behavior paths owner-coordinated: `src/ohmni/behavior/`,
   `tools/behavior_audit/`, `docs/behavior/`, `out/component-behavior/`, and
   `scripts/generate_behavior_*`. Obtain an explicit assignment before editing.
4. The shared ledger has one IN_PROGRESS slot. Coordinate with the owner before
   changing it; don't race another agent to overwrite `.ai/state.yaml` or approvals.
5. Run relevant checks, inspect `git diff --check` and staged filenames, and open
   a PR. Never push/merge main or deploy on behalf of another teammate.
6. Include scope, test results/skips, known limits and the next handoff in the PR.
   Resolve ledger conflicts semantically; never accept one side blindly.

For coding assistants, use [the handoff prompt](AI_TEAMMATE_HANDOFF.md).

## Troubleshooting

| Symptom | Next step |
|---|---|
| `No module named ohmni` | Run pip through this clone's venv Python and install `-e ".[dev]"`. Check `python -c "import ohmni; print(ohmni.__file__)"` points here. |
| PowerShell blocks activation | Use `.venv\Scripts\python.exe` directly; don't relax system-wide policy. |
| Missing historical commit in ledger | Use a full clone, or `git fetch --unshallow` for a shallow clone. |
| Port already in use | Choose `--port 8766`; don't kill another teammate's server. |
| AI unavailable | Confirm the server's local `.env`/shell configuration privately. Guided setup and saved demo remain separate alternatives; don't repeatedly retry a paid endpoint. |
| KiCad checks unavailable | Read `doctor`, check PATH and KiCad libraries; do not bypass release checks. |
| ngspice wrong version | Install/select console version 42; don't relabel a newer version's output. |
| TLS error during Git fetch/push on Windows | Retry `git -c http.sslBackend=openssl fetch origin`; never disable certificate verification. |
| Private behavior sources absent | Ask the owner for the private bundle; don't publish copyrighted datasheets. |
| Worktree tests use another checkout | Create a separate venv per worktree and reinstall editable dependencies there. |
| AI unavailable although `.env` exists | Check the exact name (`ls -a` / `Get-ChildItem -Force`): `env` or `.env.txt` is not loaded. |
| macOS datasheet tests skipped / worker "refused to parse unbounded" | Expected; see [platform differences](#platform-differences). |
| Homebrew `node` fails with `Library not loaded` after installing another Node | `brew upgrade node` relinks it against the updated shared library. |
