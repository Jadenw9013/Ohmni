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

## Contributing and AI tools

Follow [the teammate workflow](docs/TEAM_SETUP.md#working-together). Work on a
branch from current `origin/main`, preserve others' changes, and open a PR.
Do not commit secrets, private datasheets, local databases or generated receipts.

The optional [MCP server](docs/MCP_SERVER.md) requires `pip install -e ".[dev,mcp]"`.
It exposes the catalog and deterministic semantic verifier over local stdio;
it does not run AI, KiCad or SPICE. Coding assistants should first read
[AGENTS.md](AGENTS.md), not infer permission from a roadmap or an MCP connection.
