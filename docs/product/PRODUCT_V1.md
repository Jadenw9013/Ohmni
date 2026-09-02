# Ohmni v1 product definition

**Status:** PROPOSED. No milestone is approved by this document.
**Owns:** the v1 product contract, personas, supported envelope, project model,
and the boundary the model is allowed to operate inside.
**Depends on:** [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md) for every factual
claim about what exists today.

---

## 1. The product we are shipping

> **Ohmni turns a described idea into a small, real, checkable circuit board -
> and shows its work.**

The v1 contract, stated so it can be falsified:

**Ohmni v1 designs USB-powered ESP32 sensor and controller boards from a
description, verifies every electrical decision it can, names every decision it
cannot verify, and hands back KiCad and fabrication files you could actually
order - while teaching you what each decision meant.**

Everything in that sentence is a commitment we can test. Nothing in it is
"AI that can build any PCB."

### Why the contract is this narrow

The audit establishes the shape of the problem. Ohmni's *checking* stack is
broad and general; its *designing* stack does not exist. A wide product promise
would be carried entirely by the part of the system that is a fixture. Narrowing
to one MCU family and three board shapes makes the promise land on the part of
the system that is real, and makes "we got better" measurable.

### Core value proposition

Three claims, in priority order:

1. **It catches what you would have got wrong.** The verifier derives
   consequences from topology rather than matching patterns. Move a sensor to
   the wrong rail and it reports the cascade: absolute-maximum violation,
   voltage-domain crossing, pull-ups referenced to the wrong rail.
2. **It tells you what it did *not* check.** Five rule outcomes, reported
   coverage, per-rule limitations, and `UNSUPPORTED` subsystems that stay
   `UNSUPPORTED`. A pass that cannot prove decoupling *placement* says so.
3. **You end up understanding your board.** Every decision and every finding
   carries a five-field rationale record grounded in cited evidence.

### Why not ChatGPT or Claude plus KiCad

This is the question the product must answer in one screen. The honest answer is
not "the model is better." It is:

| | A general assistant + KiCad | Ohmni |
|---|---|---|
| Netlist correctness | Plausible prose; you verify | Derived, then checked by 24 pure rules that cannot be talked out of a verdict |
| Absolute max vs operating range | Frequently conflated | Separate types, separate severities, separate precedence |
| "Did it actually check that?" | Unanswerable | Five outcomes plus reported coverage; a rule with no data says so |
| Citations | Often invented | A citation is relocated in the source document or the claim drops to `UNKNOWN` |
| Artifacts | You draw the schematic and lay out the board | Fingerprinted `.kicad_sch`, routed `.kicad_pcb`, Gerbers, drill, manifest |
| Staleness | You track it | A changed input marks the release `STALE` automatically |

The moat is not generation. It is **the refusal to assert**. v1 must be shaped
so a user experiences that refusal as valuable rather than as a limitation.

### What Ohmni v1 promises

- Your board's electrical design is checked by 24 deterministic rules, and you
  can read every rule's outcome.
- Every number Ohmni states is `CATALOG_REPORTED`, `DATASHEET_SUPPORTED`,
  `CALCULATED`, `ASSUMED`, or `UNKNOWN` - and never silently upgraded.
- KiCad's own ERC and DRC run as an independent second opinion; their result is
  reported as-is, including when they disagree with Ohmni.
- You can download files that open in KiCad 10 and that a fab house accepts.
- If Ohmni cannot do what you asked, it says so and says why, before you invest
  time.

### What Ohmni v1 explicitly does NOT promise

- That the board will work. **No Ohmni-designed board has ever been fabricated
  or bench-tested.** Until [EVALUATION_PLAN.md](EVALUATION_PLAN.md) §"Hardware
  validation" completes, the product must not use words like "proven",
  "guaranteed", or "production-ready" anywhere in its interface.
- Signal integrity, EMC, RF, thermal, or mechanical behaviour. None are checked.
- Simulation. Not implemented.
- Accurate prices, stock, or lead times. Beta pricing is indicative and dated.
- Firmware. Ohmni produces hardware only.
- Any board outside the envelope in §4.
- Anything safety-critical. Ever.

## 2. Personas

Three, because a fourth adds no design decision.

### P1 - "Can code, has never made a board" **(the default persona)**

A software or CS person with a concrete project. Comfortable with types,
version control, compilers, and CI. Has never chosen a decoupling capacitor.
Owns a soldering iron of uncertain quality.

They need: translation from intent to parts; a reason to trust the output; a
path to a physical board; and to learn enough to modify it next time.

**Ohmni's default experience is designed for this person.** Reasoning:

- They already have the mental model that makes Ohmni legible. "The verifier
  blocked your export" is a type error. "Coverage was 92%" is a coverage report.
  "The release went `STALE`" is a cache invalidation. Every one of Ohmni's most
  unusual ideas has a direct analogue in their working life.
- They tolerate typed artifacts and structured output, which is what Ohmni
  actually produces.
- They have real projects, so the output has somewhere to go.

### P2 - Hobbyist / maker moving from breadboards to boards

Has built things on perfboard and dev boards. Knows what a resistor does; has
never run ERC. Wants a small custom board instead of a stack of modules.

They need: the envelope stated bluntly, hand-solderability respected, and cost
honesty. They are the most likely to *order* a board, which makes them the most
important audience for [hardware validation](EVALUATION_PLAN.md).

### P3 - Working engineer using Ohmni as a second opinion

Will not accept a 30-part catalog for design work. Might accept "check this
netlist" if the checks are ones they respect.

They are **not** a v1 target, but they are the highest-value *critic*. Their
adoption is a lagging signal that the verifier is good. Do not build features
for them in v1; do keep the CLI and JSON output usable so they can try it.

### Deliberately not a persona

**The true absolute beginner who does not know what a PCB is.** Ohmni's output
is a fabrication package. Someone at that starting point also needs to learn
ordering, assembly, soldering, and firmware before anything happens. We cannot
carry all of that in v1, and pretending otherwise produces a beautiful onboarding
flow that ends in a dead board and a lost user. The *teaching* is aimed at P1
and P2. The *reading level* stays low enough that a curious beginner is never
insulted or blocked by vocabulary - which is a different, achievable goal.

## 3. Supported use cases

**In scope for v1:**

- "A board that reads temperature and humidity over USB and blinks when it's
  too humid."
- "Same as the last one but with two sensors and no LED."
- "An ESP32 board with three status LEDs and a button, powered by USB-C."
- "Take my existing project, swap the sensor, tell me what changed."
- "I have this sensor's datasheet - can you use it?" *(from M11; see roadmap)*

**Explicitly out of scope, and refused rather than attempted:**

- Anything mains-powered, battery-charging, motor-driving, RF-transmitting,
  high-voltage, medical, automotive, or otherwise safety-relevant.
- More than 2 layers; more than roughly 40 components.
- High-speed digital, differential pairs, controlled impedance, analog
  precision, switching-regulator design.
- Boards whose value is mechanical (enclosures, connectors, form factor).
- Firmware, simulation, or reverse-engineering an existing board.
- "Make it like this product I saw."

## 4. The v1 design envelope

Stated as a contract the system can enforce, not as prose.

| Dimension | v1 envelope |
|---|---|
| Input power | USB-C 5 V sink only, no Power Delivery |
| Rails | One LDO-derived 3.3 V rail |
| MCU | **ESP32-WROOM-32E only** |
| Peripherals | I2C (up to 3 devices), SPI (up to 2 devices), GPIO in/out |
| Human I/O | LEDs with series resistors, momentary buttons, 1x6 programming header |
| Board | 2 layers, <= 100 x 70 mm, hand-solder preference honoured and reported |
| Components | Catalog parts only in v1; user-supplied parts from M11 within the supported package set |
| Packages | 0402/0603/0805 passives, SOT-23-3, SOT-23-5, SOIC-8, TSSOP-8/16, LGA-8, 1x6 THT header, USB-C 16P |
| Safety domains | **Zero.** Any detected domain is a hard refusal with an explanation. |

**One MCU is a deliberate, uncomfortable choice.** RP2040 needs QSPI flash, a
crystal, USB differential routing, and a considerably harder reference design;
STM32 multiplies the part-family problem. Adding either before the ESP32 path is
measured would spread thin capability across two families instead of making one
good. Revisit after the M13 evaluation thresholds are met.

### The three archetypes

An **archetype** is a typed template: a functional block graph with slots, plus
the rules for deriving required passives. It is the unit of generality in v1.

| ID | Archetype | Slots | Exercises |
|---|---|---|---|
| `A1` | **USB I2C sensor node** | 1-3 I2C peripherals, optional status LED | `PB-I2C-001/002/003`, `PB-PWR-001/003/004`, address-conflict detection |
| `A2` | **USB GPIO controller** | 1-4 LEDs, 1-2 buttons, optional header | `PB-LED-001`, `PB-PIN-002`, strapping-pin awareness |
| `A3` | **USB SPI peripheral node** | 1-2 SPI devices, optional I2C sensor | `PB-PIN-001` contention, chip-select handling |

Success across the archetypes means: from a plain-language request inside the
envelope, `>= 90%` of cases reach KiCad DRC 0/0 and a passing manufacturing
profile without human intervention, and `100%` of out-of-envelope requests are
refused with a reason. Thresholds live in
[EVALUATION_PLAN.md](EVALUATION_PLAN.md).

## 5. How designs get made: the central architectural recommendation

**The LLM must not emit a netlist.**

Today's scripted provider hides this decision. When the model becomes real, it
becomes the most consequential choice in the product.

**Recommendation: deterministic synthesis from archetype plus slots.**

```
user text
  -> [LLM]      typed Brief: RequirementsSpec + archetype + slot fills
  -> [gate]     safety-domain and envelope check (deterministic, final)
  -> [pure]     synthesiser expands archetype + slots -> CircuitIR
                (decoupling, pull-ups, LED resistors, CC resistors, straps
                 all DERIVED from catalog facts, not chosen by a model)
  -> [pure]     24-rule verification, bounded repair, ERC, placement,
                routing, DRC, manufacturing, release   [all unchanged]
```

Why not "the LLM proposes `CircuitIR` and the verifier catches mistakes":

- A 20-part board is a 51-net graph. One wrong pin is `CRITICAL`. The current
  repair vocabulary is a single operation, `move_pin`. Convergence from a
  model-authored netlist would be poor and, worse, non-deterministic.
- It makes evaluation nearly meaningless: a failure could be the model, the
  prompt, the catalog, or the rules, and you cannot tell which.
- It contradicts the repository's own best idea. Net voltage is *derived*
  because a declared voltage is a fact a model can assert its way out of. A
  netlist is the same kind of fact. **Derive it.**

The model's job becomes: understand a person, pick a template, fill slots from a
closed set. That is a job LLMs are genuinely good at and that can be measured
per-field. The circuit becomes a *consequence* of the brief, which is exactly
what makes "change the brief, watch the board change" a coherent product.

Deferred, not rejected: model-proposed `CircuitIR` for shapes no archetype
covers. Revisit only once archetype synthesis clears its thresholds and the
repair vocabulary is richer than `move_pin`.

## 6. Where the model is allowed, and where it is prohibited

The repository already enforces most of this with `tests/test_architecture.py`.
That enforcement must be extended to every module added from M10 onward.

**Permitted:**

- Natural language to typed `Brief` (requirements, archetype, slots).
- Natural language to a *typed proposed change* to an existing brief.
- Classifying a request as outside the envelope, **as a suggestion**; the
  deterministic gate is what actually refuses.
- Datasheet candidate-fact extraction, as an implementation of the existing
  `CandidateExtractor` protocol - output still independently relocated in the
  source and semantically supported before it becomes evidence.
- Phrasing an explanation from a typed rationale record.

**Prohibited, structurally:**

- Netlists, pin mappings, or any edit to `CircuitIR` outside the typed patch
  vocabulary.
- Creating evidence, setting claim status, or asserting verification.
- Arithmetic of any kind: currents, voltages, dropout, cost, coverage.
- ERC/DRC results, MPN existence, lifecycle, stock, price.
- Any pass/fail verdict.
- Any decision inside a `SafetyDomain`.

Operational requirements - provider abstraction, structured outputs, retries,
cost caps, prompt/model versioning, context selection, privacy - are specified
in [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) §"Production model strategy".

## 7. The project model

The product needs an object model; the demo has none. This one reuses the
lineage philosophy that already works.

```
User
 └── Project                    mutable: name, archetype, owner, archived
      ├── Brief (versioned)     immutable, append-only; the single source of intent
      │    ├── RequirementsSpec with per-field provenance and origin
      │    ├── slot fills
      │    └── assumptions, each explicitly confirmed or auto-applied
      ├── ComponentOverlay      project-scoped parts added from datasheets (M11)
      └── DesignRun (versioned) immutable; bound to exactly one Brief version
           ├── CircuitIR             + content hash
           ├── VerificationReport[]  the repair ladder, every attempt kept
           ├── SchematicArtifact     + fingerprint, ERC report
           ├── PcbArtifact           placed + routed, + fingerprints
           ├── RoutingPlan           + verification report
           ├── DRC report, ManufacturingReport
           ├── Bom, CostReport, AssemblyReport
           └── FabricationPackage    + status: DRAFT | READY_FOR_REVIEW | STALE
```

Design rules:

- **A `Brief` version is immutable.** Editing creates a new version. This is
  what makes "compare versions" and "what did my change do?" tractable.
- **A `DesignRun` is immutable and names its `Brief` version.** Re-running a
  brief produces a new run; the old one stays downloadable.
- **Staleness is derived, never stored as a flag.** The existing fingerprint
  chain already does this; the product surfaces it as "this download no longer
  matches your current design."
- **Artifacts are content-addressed** by the SHA-256 the system already
  computes, so storage deduplicates for free and a download URL is verifiable.

The user must be able to: create a project; leave and return; see every previous
run; edit the brief and see exactly which stages became invalid; compare two
runs; download any run's artifacts; and delete a project and everything in it.

## 8. Document ownership

| Question | Document |
|---|---|
| What exists today, with evidence | [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md) |
| What we are shipping and to whom | this document |
| What the user does, sees, and learns | [UX_ARCHITECTURE.md](UX_ARCHITECTURE.md) |
| How it runs, safely, for real users | [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) |
| How we know it works | [EVALUATION_PLAN.md](EVALUATION_PLAN.md) |
| In what order, and what we refuse to build | [ROADMAP.md](ROADMAP.md) |

This package supersedes `PRD.md` and `MVP_SCOPE.md` as the product contract.
Those remain as historical hackathon-era records. `ARCHITECTURE.md`,
`DOMAIN_MODEL.md`, `VERIFICATION.md`, `SECURITY.md`, and `docs/DECISIONS.md`
remain authoritative for the system as built and are not restated here.
