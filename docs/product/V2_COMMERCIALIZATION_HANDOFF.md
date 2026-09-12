# V2 Commercialization Handoff (Directive for GPT-6)

**Target Audience:** Future AI Agents (GPT-6 Astra, Claude 4, etc.)
**Objective:** Evolve Ohmni from a Hackathon PoC into a commercial, sales-ready enterprise hardware generation platform.
**Invariant Reminder:** Before beginning any work, read `AGENTS.md`. The core philosophy—"LLMs propose, Deterministic Systems verify"—must never be violated. Never replace a deterministic KiCad/SPICE check with an LLM hallucination.

---

## The Current State ("The Sandbox")
Ohmni v1 successfully proves that an AI can generate structured intent, which is then deterministically verified via semantic math checks, SPICE DC operating point simulation, and KiCad ERC/DRC. However, it currently outputs bare PCB files for a limited set of ESP32 profiles.

To become a commercial product, Ohmni must output a **complete, manufacturable, and deployable product pipeline**, not just a bare circuit board.

## Strategic Roadmap for V2

### 1. Supply Chain & Economic Routing (The "Sales-Ready" Leap)
Enterprise customers do not want a circuit board they cannot build.
*   **Live BOM Sourcing:** Integrate with Octopart, DigiKey, or Mouser APIs. 
*   **Lifecycle Awareness:** The AI must penalize or reject components marked as NRND (Not Recommended for New Designs) or Out of Stock.
*   **Cost Optimization:** Implement an optimization loop where the AI redesigns the board to meet a user's strict BOM cost target (e.g., "Design this sensor node for under $4.00 at 10,000 units").

### 2. Full-Stack Product Synthesis (Hardware + Software + Mechanical)
A PCB is useless without firmware and a case.
*   **Parametric Mechanical CAD:** The pipeline must export the PCB's exact 3D dimensions (including port placements like USB-C) and dynamically generate a 3D-printable/injection-moldable enclosure (STEP/STL formats) using Python CAD libraries (e.g., CadQuery, Build123d).
*   **Firmware Co-Design:** Because Ohmni maps the semantic intent (e.g., "I2C Temp Sensor on GPIO 18"), you must generate the corresponding ESP-IDF C++ or Zephyr RTOS firmware that initializes the hardware perfectly. Return a flashable `.bin` or source tree alongside the Gerber files.

### 3. Multimodal Component Generation
Currently, Ohmni relies on pre-existing library parts or text-based extractions.
*   **Vision-to-EDA:** Utilize native multimodal vision capabilities to ingest raw 100-page manufacturer PDF datasheets. 
*   **Autonomous Footprints:** Read mechanical drawings from the PDF and output IPC-compliant KiCad footprints (`.kicad_mod`) and symbols (`.kicad_sym`). 
*   **Verification:** Write deterministic geometric checks to ensure the generated footprint matches IPC-7351 standards before allowing it into the library.

### 4. Advanced Physics & High-Speed EDA
Move beyond simple DC SPICE.
*   **Signal & Power Integrity (SI/PI):** Integrate field solvers to check impedance matching for high-speed traces (e.g., USB 2.0/3.0, RF antennas).
*   **Thermal Simulation:** Integrate a solver (like OpenFOAM or Elmer) to simulate heat dissipation for voltage regulators and power MOSFETs to ensure the board won't melt the generated plastic enclosure.
*   **True Autorouting:** Replace the current DeterministicRouter with a fully autonomous, constraint-driven router that handles differential pairs, length matching, and copper pours for ground planes.

### 5. Enterprise Infrastructure & Scale
The current SQLite and synchronous HTTP requests will not scale to hundreds of engineers.
*   **Asynchronous EDA Pipeline:** EDA tasks (routing, SPICE, rendering) are heavy. Refactor the backend to use a message queue (Celery/Redis) so jobs are processed asynchronously, providing WebSockets or polling for UI progress updates.
*   **Team Workspaces & RBAC:** Implement enterprise SSO (Auth0/SAML), Role-Based Access Control, and team-level project sharing by upgrading the database layer to PostgreSQL.

---

**Final Instruction for the AI:** 
Do not attempt to build all of this in one prompt. Begin by reading `ARCHITECTURE.md` and the existing verification pipeline. Tackle **Section 2 (Firmware Co-Design)** and **Section 1 (Supply Chain)** first, as they provide the most immediate commercial value.

### 6. Model Context Protocol (MCP) Integration
Ohmni's ultimate commercial form is not just a standalone web app, but a backend verification engine for native AI agents. The industry standard for AI-EDA orchestration is MCP.
*   **MCP Server Implementation:** Package Ohmni's deterministic pipeline (semantic math checks, SPICE physics simulation, and headless KiCad routing) as a standard MCP Server.
*   **Native GPT-6 Astra Integration:** This allows advanced agents like GPT-6 Astra to natively connect to Ohmni. Astra can orchestrate the high-level hardware design locally, while strictly calling Ohmni's MCP tools to verify the physics and generate the final Gerbers, thereby preventing hardware hallucinations and matching the community's 'predictable tools' strategy.
