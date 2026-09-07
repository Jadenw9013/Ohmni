# Ohmni

**Build circuits. Understand why.**

Ohmni helps you understand electronics by exploring a circuit, following its
connections, and seeing the evidence behind its design. The local prototype
walks through a **USB-powered ESP32 + BME280 room sensor**, from its project
brief to real KiCad schematic and PCB files.

**Start exploring immediately in the interactive 3D circuit lab, or run the
engineering pipeline to generate and inspect a fresh design.** No electronics
vocabulary, API key, or live language model is required for this demo.

The current interface runs one pre-authored reference project. Custom circuit
requests, editable designs, electrical simulation, and firmware generation are
future work. The design files and engineering checks are real; no physical
board has been built or bench-tested by this demo.

## Run it locally

You need **Python 3.12 or later** and a modern browser. Install **KiCad 10** for
the full schematic, routing, board-checking, and fabrication pipeline. The saved
3D reference lab can be explored without running those stages.

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/demo_server.py
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/demo_server.py
```

Open **[http://127.0.0.1:8765](http://127.0.0.1:8765)**. Keep the server terminal
open while using the page. There is no frontend build step, npm install,
external font service, or runtime CDN dependency. After installing the
dependencies and tools, the demo runs offline. Use `python -m ohmni doctor`
from an activated virtual environment to check whether KiCad is available.

If the port is already in use, stop the older server or choose another one:

```powershell
.\.venv\Scripts\python.exe scripts/demo_server.py --port 8876
```

Then open [http://127.0.0.1:8876](http://127.0.0.1:8876). Each server owns its
jobs and snapshots its UI assets at startup, so **restart the server after
changing frontend files** and reload the page. The interface marks older
results as stale instead of treating another server's artifacts as current.

## Your first few minutes

1. Choose **Open the 3D circuit lab** on the homepage. It opens a clearly marked
   saved reference immediately; no engineering run is needed.
2. Try **Watch assembly**, drag the board to rotate it, and scroll to zoom.
   **X-ray** reveals both copper layers. Use the separation slider to see the
   groups of parts that perform different jobs.
3. Take the **4-stop tour** through power, the processor, sensing, and external
   connections. Select a highlighted part, use **Inspect this part** for a
   close-up, and pick a connected net to highlight its copper.
4. Return to the homepage and choose **Start this project**. Review the fixed
   example brief, then select **Run the design checks**. Allow about 90 seconds;
   duration depends on the machine and the EDA tools.
5. Explore the completed board, the explanation of its repair, and **Checks &
   evidence**. **Build & export** provides the schematic and PCB downloads,
   manufacturing-file inventory, parts information, and bring-up guidance.

Generated artifacts are also written to `out/demo-jobs/<job-id>/`. The current
UI exposes the schematic and PCB downloads; it does not yet offer a complete
manufacturing-package download.

### A PCB you can explore

- Native WebGL renders teal solder mask, metallic connectors, beveled component
  bodies, solder details, surface reference labels, and lighting that changes
  as you orbit. A canvas compatibility renderer is available when WebGL is not.
- Assembly reveals and camera transitions make the board easier to inspect.
  Connection pulses highlight recorded copper; they do not simulate electricity.
- The homepage and lab use larger text, clear starting actions, responsive
  layouts, keyboard controls, and reduced-motion support.
- On a focused board, arrow keys rotate, `+` / `-` zoom, `[` / `]` select parts,
  `Enter` inspects, and `Home` fits the board. In the lab, `Escape` clears a
  selected part; a second press closes the dialog. Text buttons provide another
  route to every lesson part.

**Visualization boundary:** assembled footprint positions, pads, and copper
come from the compiled PCB artifact. Component bodies, heights, surface
finishes, and board thickness are illustrative, not manufacturer CAD or
mechanical measurements. System separation is a learning view, not a placement
change or an assembly procedure. Saved geometry never becomes a current run's
engineering result.

## Core thesis

The system should not behave like an AI that confidently draws circuits from
prose. It should behave like an engineering mentor and compiler:

1. Understand the user's intent and constraints.
2. Ingest datasheets and extract structured component facts.
3. Build a semantic circuit representation.
4. Generate candidate designs.
5. Verify those designs with deterministic rules and independent EDA checks.
6. Optimize for hobbyist affordability, not just BOM price.
7. Explain every important decision using traceable evidence.
8. Export usable EDA artifacts.
9. Guide the user through prototype testing.

The Engineering Notebook records requirements, decisions, evidence,
calculations, verification results, uncertainty, and explanations throughout
the implemented journey. Simulation remains planned.

### Architectural rule

**LLM proposes. Datasheets ground. Deterministic rules verify.
Hardware decides. The user learns.**

An LLM is never the electrical source of truth.

---

## Current status

The core electrical verifier is deterministic and runs without a language model
or an external EDA tool. The full demo additionally invokes **KiCad 10** for
independent schematic/PCB checks and fabrication artifacts. Its proposal and
repair sequence uses a scripted provider, not a live model.

| | |
|---|---|
| Domain models | Pydantic v2, strict typing, `src/ohmni/domain/` |
| Verification rules | **24**, deterministic, independently testable |
| Part catalog | 9 parts, every fact carrying provenance |
| Fixtures | 1 golden circuit + **13** broken variants |
| Tests | Python core, KiCad integration, and slow golden demo/release tiers; **87 frontend module tests** |
| Golden circuit | no blocking findings, **100% rule coverage** |
| Broken variants | each caught by exactly the rule and severity it was built to trip |

Milestone 2 adds local PDF normalization, bounded candidate extraction,
independent citation and claim verification, and controlled evidence upgrades.
Deterministic KiCad 10 schematic emission and typed ERC ingestion are implemented.
Evidence-grounded structured circuit proposals and bounded semantic repair are implemented
with a deterministic scripted provider. Deterministic placed PCB emission and typed
KiCad DRC ingestion, bounded routing, manufacturability checks, identity-safe BOM
economics, assembly-risk classification, and KiCad fabrication release are implemented.
The redesigned workbench exposes the engineering notebook, repair,
verification ladder, interactive PCB learning lab, artifacts, BOM economics,
assembly risk, and release status.
SPICE, live supplier pricing, ordering, and arbitrary-hardware UI remain future work.
See `IMPLEMENTATION_PLAN.md` for the status table.

```powershell
python -m ohmni compile-schematic golden
python -m ohmni erc golden
python -m ohmni verify golden --eda
python -m ohmni design-fixture golden_request
python -m ohmni compile-pcb golden
python -m ohmni drc golden
python -m ohmni route golden
python -m ohmni manufacture-check golden
python -m ohmni bom golden
python -m ohmni cost golden --quantity 1
python -m ohmni release golden
```

The last verified reference run produced **19 components, 296 copper segments,
and 9 manufacturing files**, with zero reported KiCad DRC violations or
unconnected items. Its **21 schematic warnings remained visible**. These are
results for this fixture and its synthetic manufacturing profile, not a
guarantee that fabricated hardware will work.

---

## Development checks

With the project virtual environment activated:

```bash
pytest                          # fast/core tier
pytest -m integration           # bounded real-KiCad tests
pytest -m slow_integration      # full golden route/fabrication pipeline
pytest -o addopts="-q --strict-markers" # every tier
python -m ohmni verify-all # the whole fixture corpus, one line per case
```

Node.js is only needed to run the frontend module tests; it is not required to
serve or use the application:

```bash
node --test apps/web/tests/*.test.mjs
```

The tests cover engineering status preservation, server identity and stale
downloads, navigation, authoritative geometry boundaries, learning feedback,
selection, camera/assembly animation, reduced motion, and renderer cleanup.
See [the frontend redesign notes](docs/product/FRONTEND_REDESIGN.md) and
[the PCB lab verification record](docs/product/PCB_LEARNING_LAB.md) for the
implementation and browser checks.

## AI-assisted development operations

Fresh coding-agent sessions start with [AGENTS.md](AGENTS.md), then run:

```text
python scripts/project_status.py
python scripts/ai_state.py validate
python scripts/ai_state.py next
```

The `.ai/` control plane records approved work, task/review state, verification
evidence, and recovery checkpoints. Product milestones require explicit human
approval; agents may propose future work but cannot approve or begin it. See
[docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) and the
[independent review protocol](docs/AI_REVIEW_PROTOCOL.md).


### Try it

```bash
python -m ohmni doctor              # what external tools are actually present
python -m ohmni rules               # the 24 deterministic rules
python -m ohmni parts               # the part catalog
python -m ohmni ingest-datasheet sensor.pdf --part BME280
python -m ohmni verify golden       # the reference circuit
python -m ohmni verify golden -v    # ...listing every rule's outcome
python -m ohmni verify sensor_on_5v # a circuit with the sensor on 5 V
python -m ohmni verify golden --json
```

`verify` exits non-zero exactly when the design cannot be exported as verified,
so it is usable in CI as-is.

---

## What the verifier actually does

Move the environmental sensor from the 3.3 V rail to 5 V and ask:

```
$ python -m ohmni verify sensor_on_5v

summary : 11 findings (2 critical, 6 error, 1 warning, 2 info); coverage 100%; export BLOCKED

CRITICAL PB-PWR-001: U3 rail VDD exceeds the absolute maximum rating [U3, VBUS]
    Net 'VBUS' can reach 5.25 V, above the absolute maximum of 4.3 V for BME280
    rail VDD. This is not an out-of-spec operating point; it is the voltage at
    which the part may be permanently damaged. The recommended operating range
    is 1.71 V .. 1.8 V (typ) .. 3.6 V.
    fix: Move U3 rail VDD to a rail within 1.71 V .. 1.8 V (typ) .. 3.6 V.
    evidence (CATALOG_REPORTED): USB VBUS voltage at a downstream port = 4.75 V to 5.25 V [VBUS p.171]
    evidence (CATALOG_REPORTED): BME280 VDD absolute maximum rating = 4.3 V [BME280 p.12]
    evidence (CALCULATED): Voltage applied to U3 rail VDD = 5 V (derived from net
                           'VBUS', driven by external usb_vbus)

ERROR PB-PWR-003: Net 'SCL' joins pins in different voltage domains [U1, U3, SCL]
    Pins on 'SCL' are referenced to supplies between 3.3 V and 5 V:
    U1.36 (IO22) referenced to 3.3 V (3V3); U3.4 (SCK) referenced to 5 V (VBUS)...

ERROR PB-I2C-002: I2C SDA is pulled up to the wrong rail [R4, U3, 3V3, SDA]
    R4 pulls 'SDA' up to '3V3' at 3.3 V, but the devices on this bus run their
    interface at 5 V...
```

One wiring change; the verifier derives the whole cascade of consequences. That
is not pattern matching — it follows the topology.

### Four properties worth pointing at

**Voltage is derived, never declared.** Nothing anywhere lets a caller assert
what voltage a net sits at. It is computed from what drives the net: a declared
external source, or a regulator's output pin. `PinSpec.voltage_domain` from the
original spec was deliberately removed, because it was a fact a model could
assert its way out of. Rename the 5 V rail to `3V3_SAFE` and the critical
finding above is unchanged — there is a test for exactly that.

**"I could not check this" is a distinct outcome.** Rules report `PASS`, `FAIL`,
`INSUFFICIENT_DATA`, `NOT_APPLICABLE` or `ERROR`, and reports state their own
coverage. Without that, a rule that had no data is indistinguishable from one
that checked and passed — which is the failure this product exists to prevent.

**A pass says what it did not establish.** The decoupling rule can prove a
100 nF capacitor exists between VDD and ground. It cannot prove the capacitor is
2 mm from the pin, and placement is what makes decoupling work. That semantic
check says so instead of claiming a placement result. The later physical-layout
stage checks placement separately against the compiled board geometry.

**Claim status is derived from evidence, not set.** Nothing — including a model —
can declare a value "datasheet supported". It can only attach an `Evidence`, and
a datasheet citation without a document, page and verbatim snippet fails
validation. A citation checked against its source and *not found* downgrades the
claim to `UNKNOWN`: a failed citation supports nothing.

---

## The golden circuit

An ESP32 environmental logger: USB-C 5 V in, a 3.3 V rail, an ESP32-WROOM-32E, a
BME280 on I2C, a status LED, and a programming header. Two layers,
hand-solderable preference, roughly $20.

Real parts, real numbers. The verifier derives, among other things:

- LED current — `(3.35 V − 1.8 V) / 330 Ω = 4.7 mA`, worst case, against a 20 mA rating
- regulator load — `502 mA` of the AP2112K's `600 mA` (16% headroom)
- dropout headroom — `4.75 V − 3.35 V = 1.4 V` against a 250 mV requirement

It also reports three things a mentor should mention and a lint tool would not:
the BME280's LGA package is not really hand-solderable; the status LED sits on a
strapping pin, as on real ESP32 boards; and the UART header's orientation cannot
be settled from a netlist and needs human confirmation.

The 13 broken variants each change **one** thing: sensor on 5 V, missing I2C
pull-ups, missing decoupling, LED with no resistor, duplicate I2C address,
undersized regulator, missing USB-C CC resistors, floating enable, one CC
resistor shared between both pins, a package the part is not made in, pull-ups to
the wrong rail, a ground pin on a power net, and a connection to a pin that does
not exist.

---

## Scope

The current UI supports the fixed ESP32/BME280 example described above. The
broader proposed product targets low-voltage hobbyist MCU and sensor boards:
≤ 12 V DC, ESP32 / RP2040 / selected STM32, I2C / SPI / UART / GPIO, USB-C 5 V
sink, simple LDO and buck supplies, and two-layer boards. This is a product
direction, not a list of available UI templates.

Live supplier prices, ordering, firmware, SPICE, manufacturer STEP models, and
bench measurements are not provided. Prices and the manufacturing profile are
synthetic fixtures, and unknown costs remain unknown. Package-based assembly
guidance does not guarantee that every part is suitable for hand soldering.

Explicitly out of scope, and refused rather than guessed at: mains, lithium
charging and protection, medical, automotive safety, RF-critical layout,
high-speed digital, high-power motor drives, safety-critical systems.

We would rather support ten circuit patterns extremely well than pretend to
support every PCB.

---

## Project docs

For **product** questions — what the proposed Ohmni v1 would include, who it is
for, and what must be true before a closed beta — start with
[docs/product/](docs/product/README.md). It also records an evidence-backed
audit of what is real today versus what is a fixture.

For **engineering history**, start with `PRE_IMPLEMENTATION_REVIEW.md` — it
records what was wrong or missing in the original specification and what
changed as a result.

| Document | |
|---|---|
| **`docs/product/`** | **The v1 product contract, UX architecture, deployment, evaluation and roadmap. Start here for product questions.** |
| [Frontend redesign](docs/product/FRONTEND_REDESIGN.md) | Workbench flow, readability, accessibility, and verification |
| [Interactive PCB learning lab](docs/product/PCB_LEARNING_LAB.md) | 3D rendering, learning interactions, display limits, and tests |
| `PRE_IMPLEMENTATION_REVIEW.md` | Findings, corrections, open risks, spikes |
| `docs/DECISIONS.md` | Decision records for the choices that had alternatives |
| `PRD.md` | Product requirements |
| `MVP_SCOPE.md` | What the MVP does and does not support |
| `ARCHITECTURE.md` | Services and typed contracts |
| `DOMAIN_MODEL.md` | The model as built |
| `AGENT_DESIGN.md` | Orchestration stages and the repair loop |
| `VERIFICATION.md` | The 24 rules, outcomes, coverage, the export gate |
| `EVALS.md` | Golden tasks, metrics, hard targets |
| `EDGE_CASES.md` | What goes wrong in the real world |
| `SECURITY.md` | Untrusted datasheets, command execution, safety policy |
| `IMPLEMENTATION_PLAN.md` | Phase status |
| `REPO_STRUCTURE.md` | Layout and enforced dependency direction |
| `MASTER_BUILD_PROMPT.md` | The original brief |
