# Ohmni

**Build circuits. Understand why.**

Ohmni is an evidence-first AI electronics engineering mentor for people
building hardware. Instead of simply generating a finished circuit, it helps
users move from an idea through requirements, datasheets, component selection,
circuit design, verification, simulation, PCB design and physical prototyping,
while explaining the engineering behind important decisions.

The current MVP remains focused on low-voltage hobbyist MCU and sensor boards.
The broader product journey is:

`Idea -> Requirements -> Datasheets -> Circuit -> Verification -> Simulation -> PCB -> Prototype -> Learning`

## Core thesis

The system should not behave like an AI that confidently draws circuits from
prose. It should behave like an engineering mentor and compiler:

1. Understand the user's intent and constraints.
2. Ingest datasheets and extract structured component facts.
3. Build a semantic circuit representation.
4. Generate candidate designs.
5. Verify those designs with deterministic rules and simulation.
6. Optimize for hobbyist affordability, not just BOM price.
7. Explain every important decision using traceable evidence.
8. Export usable EDA artifacts.
9. Guide the user through prototype testing.

The Engineering Notebook records requirements, decisions, evidence,
calculations, simulations, verification results, alternatives, uncertainty and
lessons throughout that journey.

### Architectural rule

**LLM proposes. Datasheets ground. Deterministic rules verify. Simulation tests.
Hardware decides. The user learns.**

An LLM is never the electrical source of truth.

---

## Current status

The **deterministic foundation is built and proven**. No language model and no
external EDA tool is involved in anything below — that is the point. A verifier
whose correctness depends on a model would not be a verifier.

| | |
|---|---|
| Domain models | Pydantic v2, strict typing, `src/ohmni/domain/` |
| Verification rules | **24**, deterministic, independently testable |
| Part catalog | 9 parts, every fact carrying provenance |
| Fixtures | 1 golden circuit + **13** broken variants |
| Tests | **430**, tiered into fast, KiCad integration, and slow golden release checks |
| Golden circuit | no blocking findings, **100% rule coverage** |
| Broken variants | each caught by exactly the rule and severity it was built to trip |

Milestone 2 adds local PDF normalization, bounded candidate extraction,
independent citation and claim verification, and controlled evidence upgrades.
Deterministic KiCad 10 schematic emission and typed ERC ingestion are implemented.
Evidence-grounded structured circuit proposals and bounded semantic repair are implemented
with a deterministic scripted provider. Deterministic placed PCB emission and typed
KiCad DRC ingestion, bounded routing, manufacturability checks, identity-safe BOM
economics, assembly-risk classification, and KiCad fabrication release are implemented.
SPICE, live supplier pricing, ordering, and UI remain future work.
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

---

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
pip install -e ".[dev]"

pytest                          # fast/core tier
pytest -m integration           # bounded real-KiCad tests
pytest -m slow_integration      # full golden route/fabrication pipeline
pytest -o addopts="-q --strict-markers" # every tier
python -m ohmni verify-all # the whole fixture corpus, one line per case
```

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
2 mm from the pin, and placement is what makes decoupling work. So it says so,
and placement stays `NOT_VERIFIED`.

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

Low-voltage hobbyist MCU and sensor boards: ≤ 12 V DC, ESP32 / RP2040 / selected
STM32, I2C / SPI / UART / GPIO, USB-C 5 V sink, simple LDO and buck supplies,
2-layer, hand-solderable.

Explicitly out of scope, and refused rather than guessed at: mains, lithium
charging and protection, medical, automotive safety, RF-critical layout,
high-speed digital, high-power motor drives, safety-critical systems.

We would rather support ten circuit patterns extremely well than pretend to
support every PCB.

---

## Project docs

Start with `PRE_IMPLEMENTATION_REVIEW.md` — it records what was wrong or missing
in the original specification and what changed as a result.

| Document | |
|---|---|
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
