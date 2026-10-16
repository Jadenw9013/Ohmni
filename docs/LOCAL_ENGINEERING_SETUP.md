# Local engineering tools and verification

Every teammate must install tools on their own machine. Pulling Git does not
install KiCad, ngspice, Python packages, browser binaries or Docker. Do not copy
another person's venv, secrets or active project database.

Use [teammate setup](TEAM_SETUP.md) for Python and platform basics, then follow
this guide. The October Fetch scope and assistant assignments are in the
[hackathon guide](hackathon/FETCH_AI_IMPLEMENTATION_PLAN.md).

## Required versions and smallest installation

| Component | Version used here | Needed for |
|---|---|---|
| Python | 3.13.16; use the 3.13 series | Backend and Fetch development; avoid 3.14 for uAgents |
| KiCad with symbol and footprint libraries | **10.0.5** | Fresh qualified PCB builds |
| ngspice console executable | **42** | Supported simulation tests; optional for Fetch's board workflow |
| MCP SDK | **2.2.0**, project extra | Existing local semantic MCP server/tests |
| Playwright | **1.56.0**, project extra | Real-browser rehearsal; install matching Chromium too |
| uAgents | **0.26.1**, locally checked | Planned Fetch adapter; no agent runtime exists yet |
| Docker Desktop | Installed and running, if using containers | Alternative pinned Linux KiCad execution |

Freerouting is not required: Ohmni has its own router. Missing ngspice does not
block the Fetch board workflow, but it blocks simulation checks. Docker is not
required when the native tools pass. Do not install the latest KiCad/ngspice and
assume they satisfy the repository's version gates.

## Install Python dependencies in this checkout

From the repository root, use one command to create/check `.venv`, install the
declared dev/MCP/browser/Fetch extras, install Chromium and run readiness checks.
Activation is not required:

macOS/Linux:

```sh
python3.13 scripts/setup_hackathon.py
```

Windows PowerShell:

```powershell
py -3.13 scripts/setup_hackathon.py
```

Reruns reuse `.venv`. An incompatible or incomplete environment is refused rather
than overwritten. `--skip-browser` skips Chromium download/check for backend-only
work. `--board` additionally requires native KiCad 10.0.5. Setup does not install
native tools or start an agent/server. Use `--check` for verification without
package/browser installation. Native installation instructions follow below.

If doing the Python steps manually in an activated venv:

```sh
python -m pip install -e '.[dev,mcp,browser,fetch]'
python -m playwright install chromium
python -m pip check
python scripts/hackathon_preflight.py --fetch --browser
```

PowerShell users can run these with `.\.venv\Scripts\python.exe` and use double
quotes for `".[dev,mcp,browser,fetch]"`. No provider key is needed for these checks.
The `fetch` extra pins uAgents 0.26.1 and uagents-core 0.4.12, matching the locally
checked combination. These direct pins do not lock all transitive dependencies;
run `pip check` and preserve a verified environment snapshot for handoff.
One integration owner changes the pins. The ACP specification needs handlers for both ChatMessage and
ChatAcknowledgement. An empty Protocol fails verification. Do not run a copied
registration example simply to test package import: constructing an Agent can
attempt ledger discovery, and running it can register an identity.

## Install KiCad on macOS

Use the official **10.0.5** release, not Homebrew's current unpinned cask. This
Apple silicon machine passed the native harness using the universal installer.
Get it from the [official release](https://github.com/KiCad/kicad-source-mirror/releases/tag/10.0.5).
The exact download is
[kicad-unified-universal-10.0.5.dmg](https://github.com/KiCad/kicad-source-mirror/releases/download/10.0.5/kicad-unified-universal-10.0.5.dmg).

Verified SHA256:

```text
9399e18609c6b94e708b375bb88455b94c55653ec427b81023d71ae42217d681
```

1. Verify the downloaded image with `shasum -a 256` and compare the value above.
2. Open the image and copy its entire **KiCad folder** into `/Applications`.
   Keep all bundled apps and libraries; copying only `kicad-cli` is insufficient.
3. Run the installed CLI directly:

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli version
```

It must print `10.0.5`. Ohmni detects this standard location even without a PATH
entry. For convenient shell access, add the following to the current shell;
optionally retain it in your shell startup file:

```sh
export PATH="/Applications/KiCad/KiCad.app/Contents/MacOS:$PATH"
```

Keep enough free disk space for the 1.4 GB download and roughly 4.8 GB installed
folder. Eject the image and remove only your downloaded installer after verifying
installation. Do not delete unrelated applications or existing Docker data to
make room automatically.

## Install ngspice 42 on macOS when simulation is needed

The current Homebrew formula may supply another version. The procedure below
builds the pinned official source with XSPICE and CIDER. It requires Apple's
command line developer tools (`clang`, `make`, `bison`, `flex`). Use
`xcode-select --install` if they are missing and complete Apple's installer.

Use a new temporary build directory and install into your home directory:

```sh
mkdir -p /tmp/ohmni-ngspice42
cd /tmp/ohmni-ngspice42
curl --fail --location --retry 3 https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/old-releases/42/ngspice-42.tar.gz -o ngspice-42.tar.gz
echo '737fe3846ab2333a250dfadf1ed6ebe1860af1d8a5ff5e7803c772cc4256e50a  ngspice-42.tar.gz' | shasum -a 256 -c -
tar -xzf ngspice-42.tar.gz
cd ngspice-42
./configure --prefix="$HOME/.local/opt/ngspice42" --without-x --with-readline=no --enable-xspice --enable-cider --disable-debug
make -j4 CXXFLAGS='-O2 -Wno-invalid-specialization'
make install
export PATH="$HOME/.local/opt/ngspice42/bin:$PATH"
ngspice -v
```

Stop if checksum verification or a build step fails. The compiler flag suppresses
an error from an older bundled C++ type-trait specialization under the current
Apple compiler; it does not replace the simulator version or modify its source.
This build passed the repository's real simulation integration test on this Mac.
Retain the PATH addition in your shell startup file if you need it across sessions.
Return to the repo root before running project commands.

## Windows and Linux alternatives

For Windows, install KiCad 10.0.5 and its libraries from the same official release
page, choosing the installer for your architecture. Restart the shell, then use
the native tool discovery checks in teammate setup. Do not copy the macOS binary
or its paths. Use the project's Windows venv executable for all Python commands.

For pinned Linux KiCad execution, start Docker Desktop or your Docker daemon,
confirm `docker info` succeeds, and use the existing wrapper from a POSIX shell:

```sh
scripts/run_in_kicad_image.sh python3 scripts/verify_hackathon_demo.py --attempts 1
```

On Windows, use a configured WSL environment for that POSIX wrapper; a Windows
Python installation does not automatically exist inside WSL. Choose one environment
and keep its venv/output separate. The wrapper installs dependencies inside its
container and needs network access. The image's distro ngspice is not the pinned
42: use the existing production Dockerfile for that separate simulation path,
or qualify a native ngspice 42 installation. Do not treat the plain KiCad image
as a qualified simulation environment.

The production Dockerfile has additional behavior receipt inputs; it is not the
minimum tool bootstrap. Do not start a full production build/deployment just to
verify KiCad. Native setup on this Mac was verified; the container path was not
rerun during this setup because disk space is limited.

## Verify before taking a coding assignment

From the activated repo venv:

```sh
python -m pip check
python scripts/hackathon_preflight.py --board
python -m ohmni doctor
python scripts/verify_hackathon_demo.py --attempts 1
python scripts/rehearse_core_demo.py --output build/local-core-rehearsal
```

Preflight exit 0 is local setup only. The board harness must separately report
PASS with 18/18 checks. The browser rehearsal must report PASS for all three
families, downloads, navigation and recovery. These are no-key local checks.
Do not run `rehearse_live_plan.py` as part of setup: that is a separately authorized
paid-model rehearsal.

For simulation, also run:

```sh
python -m pytest tests/test_simulation.py tests/test_spice_model_boundary.py -m 'integration or simulation_integration' -rs
```

Read the counts and skips. Doctor exits successfully even when tools are absent;
inspect each status. Keep command output, versions and the generated summaries
for your handoff. Never claim that installing tools qualifies a live Fetch agent.

## Local setup results on October 16

Base: `527bc9dc`, synchronized with `origin/main`; local preparation edits applied.

- Apple silicon macOS, Python 3.13.16, KiCad 10.0.5 and ngspice 42 detected.
- Docker Desktop started; daemon reported 29.4.3. No container image was pulled.
- Project dev/MCP/browser extras and matching Chromium installed; `pip check` passed.
- uAgents 0.26.1 installed; ACP handler/schema verification passed without starting
  or registering an agent. Live Agentverse and ASI:One remain unverified.
- Fresh board harness: 1/1 attempts, 18/18 checks, 5.5 seconds.
- Core browser rehearsal: all three starter families and recovery passed in 51.2
  seconds, zero provider calls and zero external requests.
- Focused planner/MCP/demo/discovery tests: 92 passed, 1 deselected. After adding
  the Fetch SDK, repeated MCP/planner/discovery checks: 54 passed.
- Real simulator integration: 1 passed, 91 deselected.

Local machine evidence is under ignored `build/hackathon-ready-native/`,
`build/local-setup-core-rehearsal/`, `build/local-setup-preflight.json` and
`build/local-setup-python-packages.txt`. Those files do not arrive through Git;
each teammate should generate their own evidence.
