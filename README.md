# Ohmni

**Build circuits. Understand why.**

Ohmni is an AI electronics engineering mentor. It turns supported product ideas
into inspectable circuit plans, KiCad schematics, routed boards and manufacturing
artifacts. **LLMs propose; evidence grounds; deterministic systems verify.**
Each result says which checks actually ran and what remains unknown. A software
check is not a hardware bench test or a guarantee that a board is ready to build.

## Start here

| Your goal | Start with |
|---|---|
| See the product without accounts or native tools | Saved demo below |
| Develop with teammates | [Setup guide](docs/TEAM_SETUP.md) |
| Give a coding AI useful context | [AI teammate handoff](docs/AI_TEAMMATE_HANDOFF.md) and [AGENTS.md](AGENTS.md) |
| Understand the engineering boundaries | [Architecture](ARCHITECTURE.md), [verification](VERIFICATION.md), [decisions](docs/DECISIONS.md) |
| Find current approved work | `.ai/state.yaml`, then `python scripts/ai_state.py next` |

## October 2026 hackathon

Start with the [Fetch.ai implementation and setup guide](docs/hackathon/FETCH_AI_IMPLEMENTATION_PLAN.md)
for the weekend scope, local commands, integration checklist and fallback.
The Fetch adapter is not implemented yet. Paper redesign and new Sentry prize work
are deferred; the existing disabled telemetry core remains available.
See [research and readiness](docs/hackathon/RESEARCH_AND_READINESS.md) for eligibility
and submission details, and [assistant coordination](docs/hackathon/ASSISTANT_WORKFLOW.md)
for Codex, Claude and Antigravity assignments. Run `python scripts/hackathon_preflight.py`
from the project venv for a local setup check.
Every teammate should follow the [engineering tool setup](docs/LOCAL_ENGINEERING_SETUP.md)
for the pinned native tools and run the included verification after pulling.
Start with `python3.13 scripts/setup_hackathon.py` on macOS/Linux or
`py -3.13 scripts/setup_hackathon.py` on Windows. This prepares `.venv` and checks
dependencies without starting an agent. Use the [troubleshooting guide](docs/hackathon/TROUBLESHOOTING.md)
and [submission template](docs/hackathon/SUBMISSION_TEMPLATE.md) during the event.
Once tools are installed, run `python scripts/rehearse_hackathon.py` from the venv
for one fresh local demo readiness report, including board and browser checks.

## Five-minute saved demo

Install Git and Python 3.12 or newer (3.13 is used by CI), then:

```text
git clone https://github.com/Jadenw9013/Ohmni.git
cd Ohmni
python scripts/serve_offline_demo.py
```

On Windows, use `py -3.13` if `python` is unavailable; on macOS/Linux use
`python3.13`. Open **http://127.0.0.1:8765/**. Stop with Ctrl+C.
No pip install, API key, KiCad, ngspice, Node or cloud account is needed for this
path. All required saved-demo assets are committed.

This replays a saved board, a deliberately damaged copy and its recorded DRC
finding, and the restored original. It does **not** generate a new board or run
live simulation. [Hosting and rehearsal details](docs/hackathon/DEMO_SITE_INTEGRATION.md).

## Local development

Use the [copyable OS-specific commands](docs/TEAM_SETUP.md#development-setup).
The short version, after creating and activating a virtual environment, is:

```text
python -m pip install -e ".[dev]"
python scripts/ai_state.py validate
python scripts/demo_server.py
```

Open **http://127.0.0.1:8765/#workspace**. Guided setup and saved-demo exploration
work without a provider key; free-text AI planning requires a separately supplied
Anthropic key and can incur charges. New board generation needs KiCad. Installing
the Python package does not install native EDA tools.

## What is supported today

- Three bounded USB-powered ESP32 families: I2C sensors, buttons/lights, and SPI
  peripherals. Free text is translated into supported choices, not arbitrary
  electronics. Battery-powered designs and arbitrary component admission are not
  implied by the chat UI.
- Deterministic electrical rules, placement/routing checks and independent KiCad
  ERC/DRC. Fabrication downloads remain tied to the recorded checks and lineage.
- SPICE for supported component bindings and analyses. Missing models block a
  simulation; **not every generated board can be simulated as a whole**.
- A vanilla JavaScript workspace and 3D board explorer; local SQLite persistence.
- Fabrication assumptions and example BOM prices can be synthetic. There is no
  pick-and-place/CPL export or automatic firmware generation. Saved results are
  not physical measurements.

See the [PCB explorer guide](docs/PCB_EXPLORER.md) for the landing board's scope.
The [product documents](docs/product/README.md) describe proposed work; they are
not evidence that those features are implemented or approved.

## Built at LA AI Hackathon 2026

Ohmni existed before AI Hackathon 2026 by LA Hacks (October 17-18, 2026). Every
feature described above this section is pre-existing work. Only the features
listed here were built during the event, and only these should be judged.

<!-- Fill in during the event: feature, what it does, and the commits or PR that built it. -->

- _Nothing yet. This list is filled in during the event._

## Contributing and AI tools

Follow [the teammate workflow](docs/TEAM_SETUP.md#working-together). Work on a
branch from current `origin/main`, preserve others' changes, and open a PR.
Do not commit secrets, private datasheets, local databases or generated receipts.

The optional [MCP server](docs/MCP_SERVER.md) requires `pip install -e ".[dev,mcp]"`.
It exposes the catalog and deterministic semantic verifier over local stdio;
it does not run AI, KiCad or SPICE. Coding assistants should first read
[AGENTS.md](AGENTS.md), not infer permission from a roadmap or an MCP connection.

## Repository housekeeping

- `src/ohmni/` and `apps/web/` contain the runtime; `scripts/` contains authoring,
  verification and rehearsal entrypoints. A script without imports is not
  necessarily unused: many are launched directly.
- `docs/`, `.ai/`, root implementation proposals and `ohmni_reference_visual_plan/`
  retain design history or evidence. Use the Start here links above for current
  onboarding; historical proposals do not authorize new work.
- The landing prototype/redesign directories remain test inputs and visual
  fingerprint dependencies. They are not interchangeable with the current
  controller landing page. Do not delete them just because they look old.
- The saved demo under `apps/web/hackathon-demo/` is a published copy of
  `examples/hackathon-demo/`, maintained by `scripts/sync_hackathon_demo.mjs`.
  Keep both: one serves the browser; the other preserves the source bundle.
- `.venv/`, `node_modules/`, `build/`, local `.worktrees/` and OS metadata are local
  development files, not files to transfer to a teammate. Some files under `out/`
  are deliberately tracked evidence despite the ignore rule; do not bulk-delete
  that directory or run `git clean -fdx` to tidy a working machine.

The unused 1.92 MB `apps/web/landing-board.png` concept image was retired after
its UI replacement. Historical checkpoint mentions remain historical; retrieve
it from Git history if needed. Its obsolete server startup requirement was
removed with it. No saved project, research source or behavior receipt was removed.

## License

Ohmni is released under the [MIT License](LICENSE). Bundled third-party files keep
their own licenses, for example `apps/web/vendor/THREE-LICENSE.txt`,
`apps/web/vendor/SENTRY-LICENSE.txt`, and the KiCad library footprints copied
under `fixtures/` and `examples/`, which remain under the KiCad libraries' license.
