# Pre-Implementation Review

Status: complete
Date: 2026-08-28
Author: principal engineer (implementation agent)
Scope: review of the 14 specification documents prior to Phase 1 implementation.

This document records what I found wrong, ambiguous, or missing in the specification,
what I changed, and what remains an open risk. It is a working engineering document.
Where I deviate from the specification I say so explicitly.

---

## 1. Verdict

The specification is directionally right and unusually disciplined for a hackathon.
The central principle — *LLM proposes, datasheets ground, deterministic rules verify,
simulation tests, hardware decides, the user learns* — is the correct architecture for
this problem and I am not changing it.

The problems are in the **domain model**, not the philosophy. As written, the domain
model would let the system produce confident, unverifiable output. Roughly half of the
listed verification rules are **not implementable against the proposed types**, because
the types do not carry the facts the rules need. That is the most important finding here.

I corrected the domain model before writing verifier code, because a verifier built on an
under-specified model produces exactly the failure this product exists to prevent: a check
that appears to pass because it had nothing to check.

---

## 2. Environment findings

Probed on the actual development machine (Windows 11, 2026-08-28):

| Tool | Assumed by spec | Reality | Consequence |
|---|---|---|---|
| Python | 3.12+ | **3.13.3** present | OK |
| Pydantic v2 | required | **2.13.5** installed into `.venv` | OK |
| pytest | required | installed | OK |
| Node / npm | Next.js frontend | **22.16.0 / 11.6.2** | OK, deferred |
| `kicad-cli` | ERC/DRC integration | **was not installed**; installed during this review via winget (KiCad 10.0.5, user scope) | JSON ERC/DRC confirmed; see S1 |
| `ngspice` | simulation | **not installed, and no winget package exists** | Phase 6 is a genuine risk; see 6.2 |
| Java | Freerouting (later) | 25.0.2 present | fine, out of scope |
| git | — | present, but **repo was not initialised** | initialised as step 1 |

Network access to PyPI works.

**Correction to IMPLEMENTATION_PLAN.md:** the plan treats KiCad and ngspice as available
infrastructure. They were not. Both are now explicitly optional adapters, and *no demo
step may depend on either*. The deterministic verifier is the load-bearing verification
layer; KiCad ERC is corroboration, not the primary source of truth.

---

## 3. Contradictions found between documents

### 3.1 Three incompatible "evidence" taxonomies (most serious)

The documents define the same-sounding concept three different ways:

- `DOMAIN_MODEL.md` — `Evidence.source_type` in {datasheet, calculation, simulation, erc, drc, bench, human, catalog} and `Evidence.status` in {verified, inferred, unknown}
- `PRD.md` / `MASTER_BUILD_PROMPT.md` — claim labels {datasheet-backed, calculated, simulated, ERC/DRC verified, bench measured, human confirmed, assumed, unknown}
- `VERIFICATION.md` — subsystem labels {VERIFIED, SIMULATED, PARTIALLY VERIFIED, ASSUMED, NOT VERIFIED, UNSUPPORTED}

These are **three genuinely different concepts**, and collapsing them is how a system ends
up labelling an assumption as verified.

**Correction — three distinct types, implemented:**

1. `EvidenceKind` — *where a fact physically came from* (datasheet page, arithmetic, SPICE run, ERC run, bench measurement, human confirmation, catalog record, assumption).
2. `ClaimStatus` — *how strongly a single claim is supported*: `DATASHEET_SUPPORTED`, `CALCULATED`, `SIMULATED`, `ERC_VERIFIED`, `DRC_VERIFIED`, `BENCH_VERIFIED`, `HUMAN_CONFIRMED`, `ASSUMED`, `UNKNOWN`.
3. `SubsystemStatus` — the roll-up in `VERIFICATION.md`.

**`ClaimStatus` is derived from `EvidenceKind`, never set independently.** A model cannot
declare something `DATASHEET_SUPPORTED`; it can only attach a datasheet `Evidence` with a
document id, a page number and a verbatim snippet, and *the status follows from that*.
Enforced by a Pydantic validator, not by convention.

### 3.2 `Evidence.value: str | float | None`

This is precisely the ambiguous-string failure mode the brief forbids: `"3.3V"`, `"3V3"`,
`"3.3"` and `3.3` are four different things and none of them states a unit.

**Correction:** a `Quantity` value object carrying a float in a **canonical SI base unit**
plus an explicit `Unit` enum, with parsing for engineering notation (`4k7`, `100n`, `3V3`,
`1.8 V`) and tolerance-aware comparison helpers. `Evidence` carries an optional `Quantity`
and an optional verbatim `snippet`. No electrical quantity is a bare string anywhere in
the domain.

### 3.3 `DOMAIN_MODEL.md` references types it never defines

`DesignRule`, `CircuitConstraint`, `EvidenceLink`, `CircuitComponent`, `Net` are all
referenced and never defined. `MASTER_BUILD_PROMPT.md` additionally requires
`VerificationReport`, `SimulationReport`, `CostReport`, `EngineeringNotebook`; the brief
also requires `DecisionRecord` and `EngineeringEvent`, which appear in no document.

Also: `DOMAIN_MODEL.md` says `CircuitConstraint`, the brief says `DesignConstraint`.
**Resolved as `DesignConstraint`** (the brief wins); the other name is dropped.

### 3.4 `CircuitIR` has no identity or provenance of its own

There is no id, no version, no hash. The repair loop in `AGENT_DESIGN.md` mutates the IR,
and `EDGE_CASES.md` explicitly worries about "repair loop oscillates between two designs" —
which is undetectable without a content hash.

**Correction:** `CircuitIR` carries `ir_id`, `revision`, and a `content_hash` over its
canonical form. The repair loop refuses a patch whose result hashes to a previously seen
state. Oscillation becomes a *detected, reported* condition rather than a timeout.

---

## 4. Dangerous assumptions in the specification

### 4.1 `PinSpec.voltage_domain: str | None` — declared, not derived

A hand-labelled voltage-domain string is a fact the LLM can simply assert. If the model
writes `voltage_domain="3V3"` on a pin physically wired to the 5 V rail, every
voltage-domain check passes and the board is destroyed.

**Correction — derive, do not declare.** Net voltage is *computed* from what drives the
net: a regulator output pin contributes its datasheet output voltage; a declared external
source (USB VBUS) contributes its nominal and tolerance; ground is 0 V. Pins are then
checked against the **derived** net voltage. A pin's voltage domain is never an input to
the check. `PinSpec` keeps a `supply_rail` link (which internal rail powers this pin) —
that is a datasheet fact, not an assertion about the circuit.

This single change is what makes the voltage rules trustworthy rather than decorative.

### 4.2 Flat supply-voltage fields cannot express real parts

`ComponentSpec.supply_voltage_min_v / _max_v / absolute_max_voltage_v` assumes one supply
domain per part. The golden fixture's own sensor (BME280) has **two** independent supply
domains (VDD 1.71–3.6 V, VDDIO 1.2–3.6 V) with different limits. A level shifter has two by
definition. The proposed model cannot represent the demo circuit.

**Correction:** `ComponentSpec.supply_rails: list[SupplyRail]`, each with its own
recommended operating min/typ/max, **separate** absolute maximum, and current draw.
`PinSpec.supply_rail` names which rail a pin belongs to. Single-rail parts are the
one-element case.

### 4.3 Absolute maximum vs recommended operating conditions

`VERIFICATION.md` requires that "absolute maximum never used as target operating point",
but the model has one abs-max scalar and no way to distinguish a *supply* abs max from an
*I/O pin* abs max. In practice I/O abs max is frequently expressed **relative to the
supply** ("VDD + 0.3 V"), which no scalar can encode.

**Correction:** `SupplyRail.absolute_max` for supplies; `PinSpec.absolute_max` **and**
`PinSpec.absolute_max_above_supply` (offset form) for pins. Rules evaluate whichever is
available and report `INSUFFICIENT_DATA` when neither is — see 5.1.

### 4.4 "Required decoupling" cannot be fully checked from a netlist

Decoupling correctness is *placement* correctness. A netlist can prove a 100 nF capacitor
exists between VDD and GND; it cannot prove it sits 2 mm from the pin. Reporting this rule
as a clean PASS overstates what was verified — a direct violation of the product's own hard
target "unsupported behavior marked verified: 0".

**Correction:** the decoupling rule verifies *presence and count per power pin only*, and
its result carries that limitation explicitly. Placement stays `NOT_VERIFIED` until a board
exists and layout review runs. The report surfaces this rather than hiding it.

### 4.5 UART TX/RX orientation is genuinely ambiguous

`VERIFICATION.md` lists "TX -> RX" as a deterministic rule. For a programming header it is
not deterministic: header silkscreen conventions differ (host-perspective vs
device-perspective) and both wirings ship in real products.

**Correction:** the rule emits an explicit `HUMAN_CONFIRMED`-seeking finding stating the
convention it assumed, rather than a false PASS. This is a good demonstration of the
product thesis: *`UNKNOWN` is a successful answer.*

### 4.6 Prompt-injection defence is stated but not specified

`SECURITY.md` correctly says datasheets are untrusted, but says nothing about how *invented
citations* are caught. A model that fabricates `page 8, "VDD 1.71-3.6 V"` for a page that
says no such thing defeats the entire evidence model.

**Correction (new requirement, added to the plan):** every datasheet-sourced claim must
carry a **verbatim snippet**, and ingestion **re-verifies that the snippet actually occurs
in the extracted text of the cited page**. Failures downgrade the claim to `UNKNOWN` and
raise an event. This is deterministic, cheap, and closes the invented-citation hole.
Extraction output is additionally scanned for imperative instruction patterns and always
passed as delimited data, never in an instruction position.

---

## 5. Missing requirements

### 5.1 There is no way to say "this rule could not run"

Every listed verification rule has exactly two documented outcomes: it fires a finding or
it does not. So a rule that lacked the data to check anything is indistinguishable from a
rule that checked and passed. For an evidence-first product this is the worst possible
defect, and it is latent in the spec as written.

**Correction — `RuleOutcome` has five values:** `PASS`, `FAIL`, `INSUFFICIENT_DATA`,
`NOT_APPLICABLE`, `ERROR`. `VerificationReport` reports **coverage** (how many applicable
rules could actually execute) alongside pass/fail. A report where seven rules returned
`INSUFFICIENT_DATA` is presented as such, not as a clean bill of health.

### 5.2 Passives have no identity model, but "invented MPNs: 0" is a hard target

A 4.7 kΩ 0805 resistor has no meaningful MPN at design time, yet the target forbids
inventing one.

**Correction:** `ComponentSpec.part_id` (catalog key, always present) is separated from
`ComponentSpec.mpn` (a real orderable part number, **nullable**), with `is_generic`.
Generic passives are honestly modelled as generic classes; nothing is invented.

### 5.3 Instance values vs part facts are conflated

A resistor's resistance belongs to the *instance*; its package options belong to the
*part*. The spec has only `ComponentSpec`.

**Correction:** `CircuitComponent` (instance: reference designator, chosen package, value,
selected I2C address) is separate from `ComponentSpec` (part facts with provenance).
`CircuitIR` carries topology and part references; the catalog carries facts. The package
consistency rule is exactly the check that an instance's chosen package is one the part
actually offers.

### 5.4 I2C address modelling is absent

"Duplicate I2C addresses" is listed as a rule, but no type holds an address, and real
sensors have address *options* selected by strapping a pin (BME280: 0x76/0x77 via SDO).

**Correction:** `ComponentSpec.i2c_addresses: list[I2CAddressOption]` (address plus the pin
strap that selects it); `CircuitComponent.selected_i2c_address`. The rule checks duplicates
*per bus*, and reports `INSUFFICIENT_DATA` when a device on the bus declares no address
rather than silently passing.

### 5.5 No net-level connectivity primitives

None of the documents require the basics that catch most real errors: nets with a single
connection, unconnected pins, more than one ground net, power pins with no source.

**Correction:** a `connectivity` rule family added ahead of the more sophisticated
electrical rules.

### 5.6 `RequirementsSpec.interfaces: list[str]` / `required_components: list[str]`

Stringly typed; `"i2c"`, `"I2C"`, `"I²C"` and `"iic"` are four different values.
**Correction:** an `Interface` enum plus a free-text `notes` field for genuinely unmodelled
requirements. Same treatment for `PinRole` and `PinElectricalType`.

### 5.7 `PinElectricalType` should match KiCad's vocabulary

Our verifier and KiCad ERC both check output contention. If they use different pin-type
vocabularies they will disagree, and reconciling two disagreeing verifiers mid-demo is a
bad place to be.

**Correction:** `PinElectricalType` is defined as KiCad's exact set (`power_in`,
`power_out`, `input`, `output`, `bidirectional`, `tri_state`, `passive`, `open_collector`,
`open_emitter`, `unspecified`, `no_connect`, `free`). Our contention matrix and KiCad's then
agree by construction, and the compiler needs no lossy translation.

---

## 6. External-tool findings and corrections

### 6.1 KiCad schematic generation — the largest technical risk, and its mitigation

`ARCHITECTURE.md` proposes "SKiDL or custom emitter". Two problems:

1. **SKiDL** resolves symbols against *installed KiCad symbol libraries*, adding a hard
   dependency on library names that differ across KiCad 7/8/9/10. Library-name drift is a
   silent demo-day failure mode.
2. `kicad-cli sch erc` requires a real `.kicad_sch`. Generating one is usually assumed to
   require symbol placement *and wire geometry*, which is where naive generators fail.

**Correction — two decisions that remove most of this risk:**

- **Connect by label, not by wire.** KiCad resolves connectivity through global and
  hierarchical labels as well as wires. Emitting components on a plain grid with a global
  label per net is valid KiCad, is fully ERC-checkable, and removes wire-routing geometry
  from the generator entirely. Sheet readability is secondary to correctness for the MVP;
  this is an explicit, documented trade.
- **Emit self-contained schematics.** A `.kicad_sch` embeds every symbol it uses in its own
  `lib_symbols` block. Emitting our own symbol definitions inline removes the dependency on
  installed symbol libraries and their version-specific names. *To be confirmed against the
  installed KiCad 10 — spike S1.*

`kicad-cli sch erc --format json` and `kicad-cli pcb drc --format json` provide the
machine-readable output the spec assumes. Confirming this on the installed version is S1.

**SKiDL is dropped** in favour of a custom emitter behind the `KicadTool` adapter.

### 6.2 ngspice

No package manager on this machine provides ngspice, and KiCad ships it as a *shared
library* for its internal simulator rather than as a CLI. Options: (a) drive KiCad's
bundled ngspice shared library, or (b) vendor the official ngspice Windows build. Both are
spikes; neither is on the critical path.

**Correction to scope — first simulation target changed.** `IMPLEMENTATION_PLAN.md` says
"simulate the power section first". Simulating an LDO without a vendor model produces a
result that *looks* authoritative and means nothing — the exact failure this product exists
to avoid.

The first SPICE target is instead a **DC operating-point solve of the LED branch and any
resistor dividers**, because it independently reproduces a value the system already obtained
by `CALCULATED` evidence. Agreement between two independent methods is real evidence; a
transient plot from an invented LDO model is theatre. Power-rail transient simulation moves
behind a *behavioural model, explicitly labelled as behavioural*.

### 6.3 PDF extraction

`PyMuPDF` is the best tool for page-level provenance with text bounding boxes, but it is
**AGPL-3.0**. That is a licensing decision, not a technical one, and worth making
deliberately rather than by accident. Permissive alternatives: `pypdfium2` (Apache/BSD) and
`pdfplumber` (MIT). Flagged for a human decision; either path fits behind the
`DatasheetExtractor` adapter with no change to business logic.

### 6.4 Freerouting

Out of MVP scope per the brief. Java 25 is present, so it stays viable later. No work now.

---

## 7. Unnecessary complexity to remove

- **`packages/` with bare modules and no packaging metadata** (`REPO_STRUCTURE.md`) causes
  `sys.path` problems on Windows and cannot be installed or imported cleanly.
  **Correction:** one installable package at `src/ohmni/` with a single
  `pyproject.toml`. Subpackages preserve the document's dependency-direction rule
  (`domain` imports nothing from infrastructure), and the rule is now *enforceable by an
  import test* rather than aspirational. `apps/web/` is retained for Next.js.
- **`docker-compose.yml`, SQLite/Postgres persistence** — nothing in the MVP vertical slice
  needs a database. Files on disk suffice. Deferred.
- **NetworkX as a dependency** — the graph operations needed (adjacency, net membership,
  degree, series-path detection) are a few dozen lines against our own IR and avoid an
  infrastructure import in the domain layer. Deferred until an algorithm justifies it.

---

## 8. Unresolved risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | KiCad `.kicad_sch` emission harder than expected (format drift in v10) | ERC layer lost | Deterministic verifier is independent and remains the primary evidence; ERC degrades to `UNSUPPORTED` |
| R2 | ngspice unavailable at demo time | Simulation layer lost | Simulation is corroborative only; adapter returns `UNSUPPORTED` cleanly; cached golden result as a documented fallback |
| R3 | Datasheet extraction accuracy on real PDFs | Wrong facts enter the catalog | Snippet re-verification (4.6); unknown stays null; human review step in the UI |
| R4 | Component facts hand-encoded by me are wrong | Verifier is confidently wrong | Every catalog fact carries a datasheet page citation and is reviewable; catalog entries are treated as claims, not truth |
| R5 | Repair-loop oscillation | Demo hangs | Content-hash cycle detection plus a strict severity-weighted improvement requirement |
| R6 | PyMuPDF AGPL licensing | Legal, not technical | Flagged for human decision; adapter isolates it |

---

## 9. Technical spikes required

- **S1 — KiCad CLI** (blocking Phase 5, not Phase 1). **Half done.**
  *Confirmed:* `kicad-cli` 10.0.5 is installed and supports `sch erc --format json`,
  `pcb drc --format json` and `--exit-code-violations`. `python -m ohmni doctor`
  reports it. *Still open:* whether a hand-emitted `.kicad_sch` with inline `lib_symbols`
  and global-label connectivity is accepted and ERC-checked.
- **S2 — ngspice** (blocking Phase 6). **Diagnosed, not resolved.** Confirmed that no
  standalone `ngspice` exists on this machine, that winget has no package for it, and that
  KiCad ships it as `ngspice.dll` — a shared library for its internal simulator, not a CLI.
  The choice is therefore: drive that shared library, or vendor the official Windows build.
- **S3 — PDF extraction** (blocking Phase 2): confirm page-accurate text with coordinates on
  one real sensor datasheet, and confirm snippet re-verification works against it.
- **S4 — Symbol/footprint binding**: whether inline symbols suffice for ERC, or KiCad
  libraries must be present after all. Folded into S1.

None of S1–S4 block the first milestone, and none of them did.

---

## 10. Final recommended implementation order

Deviations from `IMPLEMENTATION_PLAN.md` are marked **[changed]**.

1. **Repo + toolchain foundation** — git init, `pyproject.toml`, `src/` layout, pytest. **[changed: single installable package]**
2. **Units and quantities** — `Unit`, `Quantity`, parsing, tolerance-aware comparison. **[new: not in the plan, and everything else depends on it]**
3. **Evidence model** — `EvidenceKind`, `Evidence`, derived `ClaimStatus`, `Claim`.
4. **Component model** — `PinSpec`, `SupplyRail`, `ComponentSpec`, `I2CAddressOption`, packages.
5. **Requirements model** — `RequirementsSpec`, `Interface`.
6. **Circuit IR** — `CircuitComponent`, `Net`, `DesignConstraint`, `CircuitIR` + content hash.
7. **Verification model** — `Severity`, `RuleOutcome`, `VerificationFinding`, `RuleResult`, `VerificationReport` with coverage. **[changed: `RuleOutcome` / coverage added]**
8. **Events** — `EngineeringEvent`, `DecisionRecord`.
9. **Part catalog** — JSON-backed, every fact carrying provenance, behind a `PartCatalog` adapter.
10. **Golden fixture** — ESP32-WROOM-32E environmental logger, known-good `CircuitIR`.
11. **Deterministic verifier** — rule registry, derived net-voltage analysis, then the rule families.
12. **Broken fixture variants** — one per rule; permanent regression tests.
13. **Adapter interfaces + fakes** — `LlmProvider`, `DatasheetExtractor`, `PartCatalog`, `KicadTool`, `SpiceTool`, `Router`.
14. — milestone 1 ends here —
15. Spike S1, then KiCad emitter + ERC.
16. Spike S3, then datasheet ingestion with snippet re-verification.
17. LLM-proposed `CircuitIR` behind schema validation, plus repair loop with cycle detection.
18. Spike S2, then DC operating-point simulation. **[changed: was LDO transient]**
19. Costing, notebook, teaching UI.

---

## 11. Golden fixture: parts chosen and why

Real, currently-purchasable, hand-solderable parts. No invented MPNs.

| Ref | Part | Why |
|---|---|---|
| U1 | **ESP32-WROOM-32E** module | Castellated, hand-solderable, 3.3 V only, with real strapping-pin and current requirements. Avoids the bare-chip-vs-module confusion `EDGE_CASES.md` warns about. Its high RF-transmit peak current makes regulator sizing a *real* check, not a toy one. |
| U2 | **AP2112K-3.3TRG1** LDO | SOT-23-5, 600 mA, 2.5–6 V in. Genuinely adequate for U1 — so the good fixture passes for a real reason. |
| U3 | **BME280** | The canonical I2C environmental sensor. Two independent supply domains (VDD / VDDIO) — exactly the case the original flat model could not represent. Address options 0x76/0x77 via the SDO strap. Recommended 1.71–3.6 V with a separate absolute maximum, so a 5 V miswiring is a *true* abs-max violation rather than merely out of spec. |
| J1 | USB-C 16-pin sink receptacle | CC1/CC2 each need a 5.1 kΩ Rd to GND. Omitting them is the most common real-world USB-C hobbyist bug and makes an excellent deterministic rule. |
| J2 | 1x6 2.54 mm header | Programming/debug: 3V3, GND, TXD, RXD, EN, IO0. |
| D1 | Green LED + series resistor | Current-limiting arithmetic that SPICE can later independently corroborate. |

Broken variants target one rule each: sensor on the 5 V rail (abs-max violation), missing
I2C pull-ups, missing decoupling, LED with no series resistor, duplicate I2C address,
undersized regulator, missing USB-C CC resistors, floating EN pin.

All numeric part facts are recorded in the catalog with the datasheet page they came from,
and are treated as claims subject to review (risk R4), not as ground truth.

---

## 12. What I am explicitly not doing

Per the brief and confirmed by this review: no autonomous layout, no routing, no live
distributor APIs, no agent swarm, no vector database, no auth, no deployment
infrastructure, no frontend polish, no bench instrument automation, and no LLM integration
at all until the deterministic path is proven end to end.

---

## 13. First milestone: what was built

Added after implementation, so this document records outcomes as well as intentions.

| | |
|---|---|
| Domain models | `src/ohmni/domain/` — units, evidence, component, requirements, circuit, verification, events |
| Verification rules | 24, deterministic, in five of the six layers `VERIFICATION.md` names |
| Part catalog | 9 parts, every fact carrying provenance and a page reference |
| Fixtures | 1 golden circuit, 13 broken variants, exported to JSON as the regression corpus |
| Tests | 314, running in under a second, with no external tool or network access |
| CLI | `python -m ohmni {verify, verify-all, rules, parts, doctor}` |

Results: the golden circuit reaches **100% rule coverage with no blocking findings**; each
of the 13 broken variants is caught by **exactly** the rule and severity it was built to
trip, all at 100% coverage.

### Corrections made during implementation, beyond those planned above

- **§4.3 needed a further refinement.** A voltage inside the recommended operating range
  cannot violate an absolute maximum, since operating conditions sit inside abs max by
  construction. So a missing abs-max figure is *not* missing data in that case, and
  reporting `INSUFFICIENT_DATA` there would be false modesty. This is what lets the golden
  fixture reach full coverage without me inventing an AP2112 figure I could not source.
- **`ValueRange` and `NetVoltage` had to expose the same accessors the same way.** They were
  briefly a method on one type and a property on the other; two rules silently compared a
  bound method against a float and crashed. The verifier reported both as
  `RuleOutcome.ERROR` rather than as passes, which is the design working. Both are now
  properties, and a test asserts the symmetry.
- **`Quantity.__eq__` is exact, and that is load-bearing.** `parse_quantity("100nF")`
  computes `100 × 1e-9`, which differs from the literal `1e-7` in the last bit. Every limit
  comparison in the rules goes through `at_most` / `at_least` / `is_close` with an explicit
  tolerance. Recorded as `docs/DECISIONS.md` §8.
- **Boot-strap pins were initially reported as floating.** ESP32 strapping pins have
  documented internal pulls and leaving them unconnected is ordinary. The catalog now
  records `internal_pull`, and `PB-PIN-002` reports one grouped `INFO` per component rather
  than five errors. A pin that genuinely has no internal pull — the module's EN — is still
  an `ERROR`.
- **USB-C VBUS pins are `PASSIVE`, not `POWER_OUT`.** A receptacle does not generate VBUS;
  the net's declared `ExternalSource` is what says it is 5 V. Four paralleled power outputs
  on one net read as driver contention.
- **`__main__.py` ran the CLI on import**, so anything walking the package executed it. The
  architecture test caught this, which is the argument for having it.

### What is now enforced rather than merely documented

`tests/test_architecture.py` parses every module's imports and fails if the domain layer
reaches for infrastructure, or if any verification rule imports a model SDK, the network,
the filesystem or the clock. It also asserts that verifying the same circuit twice produces
an identical report, and that every rule named in `VERIFICATION.md` and
`MASTER_BUILD_PROMPT.md` is actually registered.
