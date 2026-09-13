# Ohmni: AI-Driven Electronics Engineering Mentor

**Build circuits. Understand why.**

Ohmni is an evidence-first AI electronics mentor that turns a typed product idea into a verified, manufacturable circuit board. Instead of just generating code or text, Ohmni generates **physical hardware files** (KiCad schematics, routed PCBs, Gerbers) and verifies every single electrical decision using deterministic physics and math.

> **The Architectural Rule:** *LLMs propose. Deterministic systems verify.* 
> Ohmni solves AI hardware hallucinations by forcing the LLM (Claude 3.5 Sonnet) to operate inside a strict sandbox. If the LLM proposes wiring a 3.3V sensor to a 5V rail, the deterministic verifier catches it, fails the build, and forces the LLM to correct its schematic via a bounded retry loop.

## 🚀 Key Features

*   **Dynamic AI Generation (Claude 3.5 Sonnet):** Type a prompt like *"Build me an ESP32 sensor board with two I2C temp sensors"* and the AI will autonomously design the circuit.
*   **Physics Sandbox (SPICE):** Ohmni automatically extracts a SPICE netlist from the generated schematic and runs a transient physics analysis (`ngspice`). The frontend features a built-in oscilloscope UI so users can watch their virtual power rails stabilize in real-time.
*   **Automated KiCad EDA:** Ohmni acts as a headless CAD engineer, driving `kicad-cli` via subprocesses to compile schematics, place components, route copper, and run independent Electrical Rules Checks (ERC) and Design Rules Checks (DRC).
*   **Interactive 3D Lab:** A custom WebGL frontend allows users to inspect the generated board in 3D, view X-rays of the copper layers, and click components to see the exact datasheet evidence justifying the AI's design choices.
*   **Cost-Aware & Stateful:** Tracks LLM token usage/costs internally, auto-recovers from JSON schema failures, and uses a local SQLite database for persistent user projects.

## 🛠 Tech Stack
*   **Backend Engine:** Python 3.12+, Pydantic, SQLite3, `ngspice`
*   **EDA / Hardware:** KiCad 10 (CLI headless automation)
*   **AI Provider:** Anthropic API (`claude-sonnet-5`)
*   **Frontend:** Vanilla JS, HTML/CSS (Zero heavy framework dependencies, inline SVG plotting)
*   **Deployment:** Docker, Fly.io (Backend + Persistent Volumes), Vercel (Frontend CDN)

## 💻 Running it Locally

You need **Python 3.12+** and **KiCad 10** installed on your machine to run the full verification and fabrication pipeline.

1. **Clone and Install:**
```bash
git clone https://github.com/Jadenw9013/Ohmni.git
cd Ohmni
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# macOS/Linux
source .venv/bin/activate
pip install -e ".[dev]"
```

2. **Set your API Key:**
Create a `.env` file in the root directory and add your Anthropic API key to unlock the AI generator:
```text
ANTHROPIC_API_KEY=sk-ant-yourkeyhere
```
*(If no key is provided, the server gracefully falls back to a deterministic offline demo).*

3. **Start the Server:**
```bash
python scripts/demo_server.py
```
Open **[http://127.0.0.1:8765](http://127.0.0.1:8765)** in your browser to start designing! 

To verify your system has all the required EDA tools installed, you can run:
`python -m ohmni doctor`

## 🧠 Future Roadmap (V2)
The local [semantic MCP server](docs/MCP_SERVER.md) exposes capabilities, catalog
discovery and deterministic circuit verification to MCP clients. Install with
`pip install -e ".[mcp]"` and launch `python -m ohmni.mcp_server`.

See `docs/product/V2_COMMERCIALIZATION_HANDOFF.md` for the roadmap on parametric 3D enclosure generation, automated firmware co-design, and real-time supply chain BOM optimization.
