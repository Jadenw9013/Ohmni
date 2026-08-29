# Decision records

Choices made during implementation where more than one option was reasonable.
Each says what was decided, what it was chosen over, and what would make us
revisit it.

| # | Decision | Status |
|---|---|---|
| [1](#1-evidence-kind-claim-status-and-subsystem-status-are-three-types) | Evidence kind, claim status and subsystem status are three types, not one | Accepted |
| [2](#2-net-voltage-is-derived-from-drivers-never-declared) | Net voltage is derived from drivers, never declared | Accepted |
| [3](#3-rules-have-five-outcomes-and-reports-state-coverage) | Rules have five outcomes and reports state coverage | Accepted |
| [4](#4-one-installable-package-under-src) | One installable package under `src/`, not loose `packages/` modules | Accepted |
| [5](#5-custom-kicad-emitter-with-global-labels-and-inline-symbols) | Custom KiCad emitter with global labels and inline symbols, not SKiDL | Accepted, pending spike S1 |
| [6](#6-first-spice-target-is-a-dc-operating-point) | First SPICE target is a DC operating point, not an LDO transient | Accepted, pending spike S2 |
| [7](#7-hand-entered-catalog-facts-are-catalog_reported) | Hand-entered catalog facts are `CATALOG_REPORTED`, never `DATASHEET_SUPPORTED` | Accepted |
| [8](#8-quantity-equality-is-exact-engineering-comparison-is-not) | `Quantity` equality is exact; engineering comparison is explicit | Accepted |

---

## 1. Evidence kind, claim status and subsystem status are three types

**Status:** Accepted

### Context

The specification documents describe what sounds like one concept in three
ways. `DOMAIN_MODEL.md` has `Evidence.source_type` plus a `status` of
verified/inferred/unknown. `PRD.md` lists claim labels (datasheet-backed,
calculated, simulated, ...). `VERIFICATION.md` lists subsystem labels (VERIFIED,
PARTIALLY VERIFIED, ...). Collapsing them into one enum is how an assumption
ends up labelled as verified.

### Decision

Three separate types:

- `EvidenceKind` — where a fact physically came from.
- `ClaimStatus` — how strongly one claim is supported. **Derived** from the
  evidence attached to it, via a property with no setter.
- `SubsystemStatus` — the roll-up a subsystem carries in a report.

`ClaimStatus` cannot be set directly by anything, including a language model. A
model can only attach an `Evidence`, and `Evidence` validates the fields its
kind requires: a datasheet citation without a document, a page and a verbatim
snippet fails validation.

### Consequences

- A fabricated "this is datasheet-backed" claim is a validation error rather
  than a plausible string.
- `Evidence.snippet_verified = False` — a citation checked against the source
  and not found — downgrades the claim to `UNKNOWN`. A failed citation supports
  nothing.
- The seed catalog necessarily reads as `CATALOG_REPORTED`. See decision 7.

### Revisit if

Claims start needing to *combine* evidence rather than take the strongest single
piece — two independent measurements that agree, for instance.

---

## 2. Net voltage is derived from drivers, never declared

**Status:** Accepted

### Context

`DOMAIN_MODEL.md` puts `voltage_domain: str | None` on `PinSpec`. That makes a
pin's voltage domain something a caller asserts. If a model writes
`voltage_domain="3V3"` on a pin physically wired to the 5 V rail, every
voltage-domain check passes and the hardware is destroyed.

### Decision

Voltage is computed, in `VerificationContext._derive_net_voltages`:

1. Ground nets are 0 V by definition.
2. A net with a declared `ExternalSource` (USB VBUS, a battery) takes its
   voltage. This is the one legitimate declaration: nothing on the board
   produces it.
3. A net carrying a regulator's `POWER_OUT` pin takes that regulator's datasheet
   output voltage.
4. Two drivers at different voltages on one net is recorded as a *conflict*, not
   resolved by picking the first.

A component's rail voltage follows the chain: rail name → the part's own power
pins for that rail → the nets they sit on → those nets' drivers. An I/O pin's
logic domain is the voltage of the rail its datasheet says references it.

`PinSpec.supply_rail` remains, because "VDDIO references these pins" is a fact
about the *part*, not an assertion about the board.

### Consequences

- Renaming a net changes nothing. `tests/test_verifier_semantics.py` asserts
  that calling the 5 V rail `3V3_SAFE` still produces the absolute-maximum
  violation, and that renaming `3V3` to `POTATO` still derives 3.3 V.
- Voltage rules only work for parts the catalog describes. An unresolved part
  produces `INSUFFICIENT_DATA`, which is the honest answer.
- Adding a new class of power source means teaching the derivation about it, not
  adding a field to the IR.

### Revisit if

We need rails whose voltage depends on external component values, such as an
adjustable regulator set by a feedback divider. That is a derivation extension,
not a return to declarations.

---

## 3. Rules have five outcomes and reports state coverage

**Status:** Accepted

### Context

As specified, every verification rule had two possible results: it produced a
finding or it did not. That makes "I checked this and it is fine"
indistinguishable from "I had no data, so I checked nothing". For a product
whose entire claim is that its verification is trustworthy, this is the worst
available defect, and it was latent in the specification.

### Decision

`RuleOutcome` has five values: `PASS`, `FAIL`, `INSUFFICIENT_DATA`,
`NOT_APPLICABLE`, `ERROR`.

- A rule that lacks a fact records it in `missing_data` and the builder derives
  `INSUFFICIENT_DATA`. A rule cannot construct its own outcome.
- A rule that raises is caught and reported as `ERROR` with its traceback. One
  broken rule does not stop the run, and does not silently vanish either.
- `VerificationReport.coverage` is the fraction of *applicable* rules that
  reached `PASS` or `FAIL`. `NOT_APPLICABLE` is excluded, so a board with no
  LEDs is not penalised for the LED rule having nothing to say.
- `RuleResult.limitations` records what a pass does **not** establish. The
  decoupling rule uses it to state that presence was checked and placement was
  not.

### Consequences

- The golden circuit and every broken variant are asserted to reach 100%
  coverage. A change that quietly makes a rule stop checking fails the tests.
- Reports are longer and less flattering. That is the intent.
- `AP2112K-3.3TRG1` has no absolute-maximum input voltage in the catalog and the
  golden circuit still reaches full coverage, because a voltage inside the
  recommended operating range cannot violate an absolute maximum. Claiming
  missing data there would be false modesty.

### Revisit if

Coverage needs weighting — some rules matter far more than others, and a flat
fraction treats them alike.

---

## 4. One installable package under `src/`

**Status:** Accepted

### Context

`REPO_STRUCTURE.md` proposes `packages/domain/`, `packages/verifier/` and so on
as directories of bare `.py` files with no packaging metadata. On Windows in
particular that means `sys.path` manipulation, imports that work from one
directory and not another, and no way to `pip install` the project.

### Decision

One installable package at `src/proofboard/`, with a single `pyproject.toml`.
The document's boundaries are preserved as Python subpackages: `domain`,
`verifier`, `catalog`, `adapters`, `fixtures`. `apps/web/` is retained for the
Next.js frontend when it arrives.

The dependency-direction rule from `REPO_STRUCTURE.md` — domain imports no
infrastructure — is now **enforced** by `tests/test_architecture.py`, which
parses each module's imports rather than trusting the convention. The same test
asserts that no verification rule imports a model SDK, the network, the
filesystem or the clock.

### Consequences

- `pip install -e .` works; tests and the CLI run from anywhere.
- An architecture violation is a red test, not a code-review observation.
- `REPO_STRUCTURE.md` has been updated to match.

### Revisit if

The project genuinely splits into separately versioned distributions. Nothing in
the MVP needs that.

---

## 5. Custom KiCad emitter with global labels and inline symbols

**Status:** Accepted, pending spike S1

### Context

`ARCHITECTURE.md` proposes "SKiDL or custom emitter". Two risks: SKiDL resolves
symbols against *installed* KiCad symbol libraries, whose names differ across
KiCad 7/8/9/10, and library-name drift is a silent demo-day failure. And
`kicad-cli sch erc` needs a real `.kicad_sch`, which is usually assumed to
require both symbol placement and wire geometry.

### Decision

Drop SKiDL. Write a custom emitter behind the `KicadTool` adapter, with two
choices that remove most of the risk:

- **Connect by label, not by wire.** KiCad resolves connectivity through global
  labels as well as drawn wires. Placing components on a plain grid with one
  global label per net is valid KiCad, is fully ERC-checkable, and removes wire
  routing from the generator entirely. Sheet readability is explicitly traded
  for correctness in the MVP.
- **Emit self-contained schematics.** A `.kicad_sch` embeds every symbol it uses
  in its own `lib_symbols` block, so emitting our own symbol definitions inline
  removes the dependency on installed libraries and their version-specific
  names.

`PinElectricalType` already uses KiCad's exact pin-type vocabulary, so our
contention rules and KiCad ERC agree by construction and the emitter needs no
lossy translation.

### Verified so far

`kicad-cli` 10.0.5 is installed and confirmed to support `sch erc --format
json`, `pcb drc --format json` and `--exit-code-violations`.
`python -m proofboard doctor` reports this.

### Still open (spike S1)

Whether a hand-emitted `.kicad_sch` with inline `lib_symbols` and global-label
connectivity is accepted and ERC-checked by KiCad 10.

### Consequences

Generated schematics will be ugly. They will be correct, and ERC will run. Until
S1 lands, `KicadCli.run_erc` returns `UNAVAILABLE`, never an empty pass.

---

## 6. First SPICE target is a DC operating point

**Status:** Accepted, pending spike S2

### Context

`IMPLEMENTATION_PLAN.md` says "simulate the power section first". Simulating an
LDO without a vendor model means inventing a behavioural model and then
presenting its output as if it validated the regulator. The result looks
authoritative and means nothing — precisely the failure this product exists to
prevent.

### Decision

The first simulation target is a **DC operating-point solve of the LED branch
and any resistor dividers**.

The reason is not that it is easier. The system already computes the LED current
by `CALCULATED` evidence — `(3.35 V − 1.8 V) / 330 Ω = 4.7 mA` — and a SPICE
solve reaches the same number by an independent method. Two independent methods
agreeing is real corroboration. A transient plot from a model we invented is
theatre.

Power-rail transient simulation moves behind a behavioural model that is
explicitly labelled as such: `SimulationRun.model_fidelity` is a required field
with values `vendor_model`, `behavioural_approximation` or `ideal_components`.

### Environment finding

There is no standalone `ngspice` on this machine and no winget package for it.
KiCad ships ngspice as `ngspice.dll` — a shared library for its internal
simulator, not a CLI. `python -m proofboard doctor` reports the library path it
found.

### Still open (spike S2)

Whether to drive KiCad's bundled shared library, or vendor the official ngspice
Windows build.

### Consequences

No demo step depends on simulation. `UnavailableSpice` returns `UNAVAILABLE` and
produces no evidence, and the simulation subsystem reads `UNSUPPORTED`. When
simulation does land, its first job is to disagree with arithmetic we already
trust — which is the only way to find out that one of them is wrong.

---

## 7. Hand-entered catalog facts are `CATALOG_REPORTED`

**Status:** Accepted

### Context

The seed catalog needed real numbers for the ESP32-WROOM-32E, AP2112K-3.3,
MCP1700-3302E and BME280 before any PDF ingestion exists. Those numbers were
entered by hand from manufacturer datasheets.

`datasheet_evidence()` requires a **verbatim snippet** from a cited page. A
snippet written from memory rather than copied from the document is a fabricated
citation — exactly the failure `EDGE_CASES.md` lists under "invented citations"
and `EVALS.md` targets at zero.

### Decision

Seed catalog facts use `catalog_evidence()`: kind `CATALOG`, status
`CATALOG_REPORTED`, carrying the `DocumentRef` and page number so a human can
check them, and a `detail` string stating plainly that the snippet was not
captured and the citation is not machine-verified.

Three further rules:

- Values that could not be stated with confidence are **absent**, not guessed.
  The AP2112's absolute-maximum input voltage is `None`.
- Deliberate conservative estimates use `assumed_evidence()` and read as
  `ASSUMED`. The BME280's 1 mA supply-current figure is one of these.
- `tests/test_catalog.py` asserts that **no** catalog entry claims
  `DATASHEET_SUPPORTED` or `provenance_machine_verified`.

### Consequences

- `CATALOG_REPORTED` ranks below `DATASHEET_SUPPORTED`, so reports honestly show
  that nothing has been verified against a real PDF yet.
- When ingestion lands, these claims upgrade to `DATASHEET_SUPPORTED` with
  machine-verified citations, and the user *sees the status change*. That is a
  better demonstration of the product's thesis than starting with the strong
  label and hoping nobody checks.
- This is risk R4 in `PRE_IMPLEMENTATION_REVIEW.md`: the numbers themselves may
  still be wrong. They are labelled as claims, and every one carries a page a
  reviewer can turn to.

---

## 8. `Quantity` equality is exact; engineering comparison is not

**Status:** Accepted

### Context

`Quantity` is a frozen, hashable value object. Making `==` tolerant would break
the hash/equality contract. But `parse_quantity("100nF")` computes `100 × 1e-9`,
which differs from the literal `1e-7` in the last bit — so exact equality is the
wrong tool for comparing engineering values.

This was found by a test, not by reasoning: an assertion that a parsed value
equalled a constructed one failed.

### Decision

- `==`, `<`, `>`, `<=`, `>=` are exact and unit-checked. They never apply
  tolerance.
- `is_close`, `at_most` and `at_least` take an explicit `rel_tol`, defaulting to
  `1e-9`.
- `ValueRange.contains` is boundary-inclusive through `at_most`/`at_least`.

A rule author therefore has to *choose*, visibly, in the rule. A datasheet limit
of exactly 3.6 V is not violated by a value that reaches 3.6 V through
arithmetic.

### Consequences

- Every limit comparison in the rules goes through the tolerant methods.
- `ValueRange` and `NetVoltage` expose `nominal`, `worst_case_high` and
  `worst_case_low` as **properties on both**. They were briefly a method on one
  and a property on the other, and two rules silently compared a bound method
  against a float. `tests/test_units.py` now asserts the symmetry.
