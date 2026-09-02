# Ohmni evaluation and hardware validation plan

**Status:** PROPOSED. No milestone is approved by this document.
**Owns:** the pre-beta product benchmark, its acceptance thresholds, and the
physical hardware validation programme.
**Relationship to `EVALS.md`:** that document sketched a hackathon-era 10-20
task set and per-subsystem metrics. It remains valid as the *component* eval
philosophy and its hard targets (invented MPNs: 0) still hold. This document is
the **product** eval layer above it and takes precedence where they differ.

---

## 1. Why "tests pass" is not the bar

The repository runs 465 fast tests, a 14-fixture verifier corpus at 100%
coverage, real KiCad ERC and DRC, and a full slow-integration pipeline. All of
it passes. None of it establishes that Ohmni builds **what the user asked for**,
because there is currently exactly one request and it is a string constant.

The failure this plan exists to catch is specific and it is the one that would
hurt most:

> **A board that passes every check, exports cleanly, and does not do what the
> person wanted.**

Nothing in the current test suite could detect that. Two things can: a human
intent rubric (§3) and a physical board (§5).

## 2. The benchmark

**120 requests**, authored by hand, in the language a real user would use.
Stored as fixtures. Frozen once authored; growth happens by adding, never by
editing a case that failed.

| Set | Count | Composition | Correct behaviour |
|---|---|---|---|
| **In-envelope** | 60 | 20 per archetype (`A1` I2C sensor node, `A2` GPIO controller, `A3` SPI peripheral node) | Design it |
| **Ambiguous** | 30 | Underspecified in a way that changes the parts chosen | **Ask**, do not guess |
| **Out-of-envelope** | 20 | Mains, LiPo charging, motor drive, >12 V, RF, medical, automotive, 4-layer, high-speed, "make me a phone" | **Refuse**, with the specific reason |
| **Adversarial** | 10 | Prompt injection in the request; injection inside an uploaded PDF; contradictory constraints; a plausible but nonexistent MPN; a request that is 4000 words | Handle safely |

Each in-envelope case carries a hand-authored expectation: the `RequirementsSpec`
field values, the expected archetype, and the expected functional block set.
Each ambiguous case carries the question(s) a competent engineer would ask. Each
out-of-envelope case carries the domain that must be detected.

Writing these is roughly 2-3 days of work and it is the highest-leverage 3 days
in the whole plan, because every threshold below is meaningless without them.

## 3. Metrics and acceptance thresholds

Thresholds are gates for **entering closed beta**, not aspirations.

### Interpretation

| Metric | Threshold |
|---|---|
| Requirement field accuracy (in-envelope, per required field) | >= 95% |
| **Safety-relevant field accuracy** (input voltage, safety domain) | **100%** |
| Archetype selection correct | >= 95% |
| Slot fills valid (part exists, package supported) | 100% |
| Ambiguous cases that ask rather than assume | >= 90% |
| **Out-of-envelope detection recall** | **100%** - a miss is a safety event, not a quality metric |
| Out-of-envelope precision (no false refusals of valid requests) | >= 90% |
| Adversarial cases producing zero fabricated evidence | **100%** |

### Design

| Metric | Threshold |
|---|---|
| Invented MPNs | **0** (structurally impossible today; keep the guard) |
| Invented pins | **0** (`PB-ID-002`, `CRITICAL`) |
| Circuits structurally valid (referential integrity, catalog-only) | 100% |
| Reaches export-eligible within the repair budget | >= 90% |
| Repair convergence when the first attempt fails | >= 80%, zero oscillation |
| Required passives present without a rule having to demand them | >= 95% |

### Artifacts

| Metric | Threshold |
|---|---|
| KiCad schematic compiles | 100% |
| ERC blocking violations | **0** |
| PCB compiles (every footprint resolves) | 100% within the supported package set |
| Routing completes within its budget | >= 90% |
| DRC violations / unrouted on completed routes | **0 / 0** |
| Manufacturing profile passes | >= 95% |
| Release lineage current (no accidental `STALE`) | 100% |

### The metric that actually matters

| Metric | Threshold |
|---|---|
| **User-intent satisfaction** | median >= 4.0 / 5, no case below 2 |

**Method:** a hardware-literate rater who did not author the case, shown the
original request and the resulting schematic, BOM, and board - and **blind to
Ohmni's own verdict** - answers: *"If someone built this, would it do what they
asked?"* on a 1-5 scale, with a written reason for anything below 4.

Blindness matters. A rater who has already seen `PASS` will find reasons to
agree with it. This is the only metric in the plan capable of catching a
verified, useless board, and its cost is a few hours per benchmark run.

### Operational

| Metric | Threshold |
|---|---|
| p50 / p95 end-to-end runtime | <= 90 s / <= 300 s |
| Model cost per completed project | <= $0.50 |
| Model calls per completed project | <= 6 |
| Nondeterminism: same brief, two runs, identical `CircuitIR` hash | 100% (synthesis is pure; only interpretation may vary) |

That last one is worth calling out. Because the design is *derived* from the
brief rather than generated, an identical confirmed brief must produce a
bit-identical circuit. If it does not, something non-deterministic has leaked
into the synthesis path, and the whole verification story weakens.

## 4. Running it

- **Harness:** `scripts/eval.py`, reusing the existing fixture and CLI plumbing.
  Emits per-case JSON plus a summary table.
- **Cadence:** full benchmark before any milestone completion from M10 onward;
  the 20 out-of-envelope cases on every commit that touches interpretation or
  the safety gate.
- **Regression policy:** extend the existing rule - *every electrical bug found
  becomes a permanent fixture variant* - to cover **product** bugs. Every
  benchmark failure becomes a permanent case. Cases are added, never edited to
  pass.
- **Reporting:** results recorded as commit-bound evidence under
  `.ai/verification/`, matching the existing convention, so a threshold claim is
  always tied to a commit.

## 5. Physical hardware validation

Everything above is still simulation of a sort. `SubsystemStatus` has no value
for bench measurement other than `NOT_VERIFIED`, and it is currently correct.

**Gate: until this programme completes, no Ohmni surface - product, README, or
marketing - may use "proven", "guaranteed", "validated", or "production-ready".
"Checked, not proven" is the strongest available phrasing.**

### Prerequisite

`prototype_profile()` is synthetic. **Replace it with a real, provenance-bearing
`ManufacturingProfile` built from the chosen fabricator's published capability
document** before ordering anything. Otherwise the manufacturing PASS is checking
the board against a profile we invented.

### Scope

- **3 designs**, one per archetype, chosen from actual benchmark output - not
  hand-tuned for the occasion.
- **5 boards per design** = 15 boards per spin.
- **Budget for 2 spins.** A first spin that fails is information, not failure;
  a plan with no second spin is a plan that will quietly relabel failures.
- Cost: a 2-layer 100 x 70 mm order of 5 is roughly $10-30 per design plus
  shipping. Components for 15 boards, a few hundred dollars. This is cheap
  relative to what it settles.

### Fabrication

One house (JLCPCB or PCBWay), 1.6 mm FR-4, HASL or ENIG, 6/6 mil design rules -
matching the real profile exactly. Order from the Gerbers Ohmni produced, with
no manual edits. **If a file needs hand-fixing to be accepted, that is a
finding**, and it is recorded as one.

### Assembly

3 of 5 hand-soldered, 2 by hot air or reflow. This directly tests
`classify_assembly`, which predicts the BME280's LGA-8 as
`REFLOW_RECOMMENDED` - a prediction that has never been checked against a human
with an iron.

### Bring-up sequence

Performed in this order, recorded per board, **with Ohmni's prediction written
down before each measurement**:

| # | Step | Ohmni's prediction |
|---|---|---|
| 1 | Visual inspection; continuity; **VBUS-to-GND short check before applying power** | no short |
| 2 | Current-limited 5 V bench supply at 100 mA; measure input current | within regulator + load estimate |
| 3 | Measure the 3.3 V rail | ~3.35 V (`AP2112K` output, `CALCULATED`) |
| 4 | Measure dropout headroom at load | 1.4 V against a 250 mV requirement |
| 5 | Measure LED current | 4.7 mA worst case, 20 mA rating |
| 6 | I2C bus scan | the address `PB-I2C-003` derived from the strap wiring |
| 7 | Read the sensor; sanity-check the values | plausible ambient readings |
| 8 | **UART header orientation** | `UNKNOWN` - `PB-UART-001` explicitly refused to decide. Record which convention was correct. |

Step 8 is the most interesting row in the table. It is the one place the system
said "I cannot settle this from a netlist, a human must confirm" - and the bench
is where we find out whether that refusal was wise or merely timid.

### Metrics

| Metric | Definition | Target |
|---|---|---|
| **First-spin functional yield** | boards that power up and read their sensor / boards assembled | **>= 80% on spin 1** |
| Prediction accuracy | measured vs Ohmni's derived value, per quantity | within stated tolerance for **100%** of `CALCULATED` values, or a recorded rule gap |
| Design defects | issues traceable to the design Ohmni produced | **0 critical** |
| Rule gaps | real problems no rule caught | each becomes a new rule **and** a fixture |
| Assembly prediction accuracy | did the difficulty classification match reality | qualitative, recorded |
| Fabrication acceptance | orders accepted without manual file edits | 100% |

### Defect tracking

Every defect gets: a stable id, the board and design, symptom, root cause
classified as **design / Ohmni rule gap / fabrication / assembly / firmware**,
whether any Ohmni check should have caught it, and the resulting rule or fixture.
Rule gaps are the valuable ones - they are the only way the verifier learns
something the fixtures could not teach it.

### Deliverable

A published **predicted-vs-measured table**. Not a claim, a table. It is the
single most credible artifact this project could produce, it is the thing that
distinguishes Ohmni from every tool that generates a plausible board, and it
cannot be faked.
