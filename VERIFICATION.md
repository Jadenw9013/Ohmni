# Verification Strategy

> **Status: implemented.** 25 deterministic rules, in
> `src/ohmni/verifier/rules/`. Run `python -m ohmni rules` to list
> them and `python -m ohmni verify golden -v` to see them execute.

## Principle

Verification is the product.

The AI is useful only if its design decisions are inspectable and mechanically
checked.

## What a rule is

A rule is a **pure function of a circuit and a part catalog**. It may not call a
language model, open a socket, read a file, or look at the clock. That is
enforced by `tests/test_architecture.py`, not left to convention: the product's
claim is that its checks are deterministic and reproducible, and one
`import anthropic` inside a rule would quietly make that false.

Datasheet ingestion is upstream of this boundary. It may parse files and attach
machine-verified `Evidence` to `ComponentSpec`; electrical rules remain ignorant
of PDFs and consume only the same typed catalog contract as before.

## Rule outcomes

Every rule reports one of five outcomes. This is the most important addition to
the original strategy, which gave a rule only two possible results — it fired a
finding or it did not — making "I checked and it is fine" indistinguishable from
"I had no data, so I checked nothing".

| Outcome | Meaning |
|---|---|
| `PASS` | The rule ran and found nothing wrong. |
| `FAIL` | The rule ran and found something at WARNING or above. |
| `INSUFFICIENT_DATA` | The rule needed a fact it did not have. `missing_data` says which. |
| `NOT_APPLICABLE` | Nothing in this circuit is in scope for the rule. |
| `ERROR` | The rule raised. Its verdict is unavailable, **not** a pass. |

A rule never constructs its own outcome; `ResultBuilder` derives it from what
the rule actually did.

## Coverage

`VerificationReport.coverage` is the fraction of *applicable* rules that reached
a real verdict. `NOT_APPLICABLE` is excluded, so a board with no LEDs is not
penalised for the LED rule having nothing to say.

A report where seven rules returned `INSUFFICIENT_DATA` is presented as such,
not as a clean bill of health. Both the golden circuit and every broken variant
are asserted at 100% coverage, so a change that quietly stops a rule checking is
a test failure.

## Limitations

`PB-SPI-001` checks the bounded SPI topology: complete and correctly matched
clock/data connections, one controller, separate chip selects, high-impedance
peripheral MISO, and EEPROM deselection pull-ups. The ESP32 pin assignment is
an explicit supported synthesis policy. A pass does not verify firmware pin
configuration, timing, bus arbitration at runtime, or signal integrity.

Each rule records what a **pass from it does not establish**, and the report
aggregates them. The decoupling rule is the clearest case: a netlist can prove a
100 nF capacitor exists between VDD and GND, but it cannot prove the capacitor
is 2 mm from the pin — and placement is what makes decoupling work. So the rule
checks presence, states that it checked only presence, and leaves placement
`NOT_VERIFIED` until a board exists.

## Severity and the export gate

| Severity | Meaning | Blocks export |
|---|---|---|
| `CRITICAL` | May damage hardware; violates an absolute maximum rating | yes |
| `ERROR` | The board will not work as intended | yes |
| `WARNING` | Likely a problem, or a real risk we cannot fully check | no |
| `INFO` | Worth knowing; includes things we deliberately did not verify | no |

`ERROR` blocks alongside `CRITICAL`: exporting a design we know does not work,
labelled verified, would violate the hard target "unsupported claims marked
verified: 0". A user may still export the artifacts clearly marked unresolved —
that is a UI decision, not a change to this policy.

`python -m ohmni verify <fixture>` exits non-zero exactly when export is
blocked, so this is usable in CI on its own.

---

## The rules

### Layer 1 — identity

| Rule | Checks |
|---|---|
| `PB-ID-001` | Every part resolves to a catalog entry; placeholders are flagged |
| `PB-ID-002` | Every connection names a pin the part actually has |
| `PB-ID-003` | The chosen package is one the part is offered in; pin counts agree |
| `PB-ID-004` | Passives carry a value, in the right unit |
| `PB-ID-005` | Packages match the user's hand-soldering requirement |

`PB-ID-002` is the anti-hallucination check for generated netlists: an invented
pin number is `CRITICAL`.

### Layer 2 — connectivity

| Rule | Checks |
|---|---|
| `PB-CONN-001` | Exactly one ground net |
| `PB-CONN-002` | Every ground pin reaches ground (including exposed pads) |
| `PB-CONN-003` | Every supply pin is fed by something that produces a voltage |
| `PB-CONN-004` | No net connects to only one pin |
| `PB-CONN-005` | Unconnected pins are accounted for |

`PB-CONN-005` decides what counts as expected from the *requirements*: a USB-C
receptacle on a power-only sink legitimately leaves D+/D− unconnected, and the
rule says so rather than hard-coding an exception for connectors.

### Layer 2 — pin semantics

| Rule | Checks |
|---|---|
| `PB-PIN-001` | No two devices drive one net push-pull |
| `PB-PIN-002` | Enable, reset and address-select pins are tied or driven |

`PB-PIN-001` groups by component, so paralleled output pins on one part are one
driver rather than a short. Open-drain outputs are excluded: two of them with a
pull-up is a correct I2C bus.

`PB-PIN-002` treats a boot-strap pin using its **documented internal pull** as an
`INFO` note rather than a defect, grouped one per component. An enable pin
leaning on a weak internal pull is still a `WARNING`.

### Layer 3 — electrical constraints

| Rule | Checks |
|---|---|
| `PB-PWR-001` | Every supply rail is inside its recommended operating range |
| `PB-PWR-002` | No net is driven by two different supplies |
| `PB-PWR-003` | Signals do not cross voltage domains without translation |
| `PB-PWR-004` | Supply pins have the decoupling their datasheet asks for |
| `PB-REG-001` | Regulator input is in range and leaves dropout headroom |
| `PB-REG-002` | The regulator can supply the load on its output |
| `PB-LED-001` | Every LED has a series current-limiting resistor |

**`PB-PWR-001` is where operating limits and absolute maximum ratings are kept
apart**, in this precedence:

1. above the absolute maximum → `CRITICAL` — the part may be destroyed;
2. outside the recommended operating range → `ERROR` — not specified to work;
3. nominal fine but the supply's tolerance leaves the range → `WARNING`.

Note what is *not* there: if the applied voltage is inside the recommended
operating range, an unknown absolute maximum is not missing data. Recommended
operating conditions sit inside the absolute maximum by construction, so there
is nothing left to check.

**`PB-REG-002` is careful about what it does not know.** A load sum built from
only the parts that publish a figure is a *lower bound*. If that lower bound
already exceeds capacity the answer is `FAIL` — definitive, because the unknowns
can only add. If it is under capacity but some parts publish nothing, the answer
is `INSUFFICIENT_DATA`. Silently summing the known parts and reporting a pass
would understate the load, which is how an undersized regulator reaches a board.

**`PB-LED-001` detects series elements topologically.** The signature is a
*private node*: a net touching exactly two pins, one of them the LED and the
other a resistor. A resistor elsewhere on the LED's net is not in series with it
and limits nothing. Current is then computed worst case, using the *minimum*
forward voltage, because that produces the highest current.

### Layer 4 — interface rules

| Rule | Checks |
|---|---|
| `PB-I2C-001` | Both bus lines have pull-ups |
| `PB-I2C-002` | Pull-ups go to the bus devices' interface rail, at a sane value |
| `PB-I2C-003` | No duplicate addresses; the declared address matches the strap wiring |
| `PB-UART-001` | No transmitter-to-transmitter; header orientation flagged for a human |
| `PB-USB-001` | A USB-C sink presents its own Rd on each of CC1 and CC2 |

I2C buses are derived from the **peripheral** side. A microcontroller GPIO is
only an I2C pin because firmware says so; a sensor's SDA pin is SDA in silicon.
Starting from the definite end avoids guessing.

`PB-I2C-003` derives the address from how the strap pin is actually wired and
compares it against the declared one. A declared address is an assertion; the
strap is the board.

`PB-UART-001` is the honest one. Header silkscreen convention genuinely differs
between products, and both wirings ship. Where a UART reaches a bare header the
rule states the convention it assumed and asks for confirmation, rather than
reporting a false pass. **`UNKNOWN` is a successful answer.**

### Layers 5 and 6 — EDA and simulation

KiCad schematic ERC is implemented as an independent external verifier. The
compiler emits a fingerprinted KiCad 10 schematic, the bounded CLI adapter runs
`kicad-cli sch erc` with JSON output, and a typed parser maps the result into an
additional `KICAD-ERC` rule result without replacing semantic verification.
Unavailable, malformed, crashed, or stale-artifact runs never become PASS.

SPICE remains unimplemented; its subsystem reads `UNSUPPORTED`. An empty finding
list from a check that never ran must never look like a clean result.

## PCB verification

Physical verification checks footprint/pad overlap, outline containment, edge
clearance, measured capacitor distance, connector edge accessibility and complete
pin-to-pad/net binding (`PB-PCB-001` through `006`). Bounds include rotated pads,
asymmetric footprint origins and the separately pinned full ESP32 body.
Proximity constraints can measure actual pad-to-pad distance; they do not infer
capacitor ownership from a shared power net.

`PB-PCB-008` reports malformed or unsupported geometry/constraints as ERROR.
`009` through `013` evaluate envelope separation, fixed poses, allowed regions,
orientation and component exclusion from declared keepouts. Every requested
constraint produces a finding with its ID. ERROR, FAIL and empty reports cannot
pass. Antenna exclusion is a geometric policy with explicit source/compatibility
assumptions, not an RF result. Copper validity belongs to the routing verifier;
the physical checker no longer reports a fictitious no-copper PASS after routing.

KiCad DRC is a separate typed external report tied to the exact PCB SHA-256 and
source schematic SHA-256. A placed board is still unrouted and cannot be released
as connected. Only the separately routed artifact is eligible for routing DRC.

---

## Verification status taxonomy

Each subsystem is rolled up to one of `VERIFIED`, `SIMULATED`,
`PARTIALLY_VERIFIED`, `ASSUMED`, `NOT_VERIFIED`, `UNSUPPORTED`.

The ordering is deliberate: a subsystem with any blocking finding is
`NOT_VERIFIED` even if most of its rules passed; one where some rules could not
run, or that has warnings, is `PARTIALLY_VERIFIED`. Only "every applicable rule
ran and passed" earns `VERIFIED`.

## Fail-closed rules

Critical and error findings block a verified export. A user may export an
incomplete artifact only if the UI clearly marks it unresolved and the system
does not represent it as validated.

## Regression policy

Every electrical bug found becomes a permanent fixture variant in
`src/ohmni/fixtures/` and a case in `tests/test_fixtures.py`, asserting the
specific rule and severity that should catch it. `python -m ohmni verify-all`
runs the whole corpus in one line of output per case.

## Routing verification

`PB-ROUTE-001` through `PB-ROUTE-008` check complete physical-pad connectivity,
cross-net shorts, net/lineage validity, board bounds, widths, via geometry,
obstacles, and bounded via use. Repeated lands with the same electrical pin
number each require a connection; terminal names in a proposed plan cannot hide
an unconnected switch leg. Per-net widths are verified alongside the profile.
`009` rejects unresolved routing failures, and `010` checks declared copper
keepouts on both layers. Deadline/cancellation failure preserves an incomplete
plan and blocks release; the verifier has no clock dependency.
The corrected golden routed artifact passes these rules
and KiCad 10.0.5 DRC with zero findings and zero unrouted items. This does not
establish signal integrity, thermal behavior, EMC, RF behavior,
manufacturability, or bench operation.
## Manufacturing verification

PB-MFG-001 through PB-MFG-008 check track width, clearance, via/drill geometry,
board dimensions, layer count, edge clearance, footprint provenance, and the
supported feature subset against a selected profile. PB-MFG-009 and PB-MFG-010
verify exact release lineage and required nonempty fabrication outputs.
Manufacturing PASS means the board fits the stated profile within implemented
checks; it does not prove fabrication, assembly, thermal, EMC/RF, or bench
success. Dimensional findings report their explicit margin.

## Component synthesis verification

Imported-component checks run in a fixed order, and the order is the claim.

**Source first.** `CS-SOURCE` relocates every proposed claim in the document
itself, using the tables' own printed column rules: a value is supported only
when it is printed in the claimed row, under the claimed dimension symbol, in
the claimed MIN/NOM/MAX column, under the units the table declares, on the
recommended land pattern page for the selected package. Finding the same number
elsewhere fails.

*What a row means comes from the grammar, never from the proposal.* Reading the
right number out of the right row says nothing about whether that row denotes
the feature the proposal called it, and an independent audit demonstrated the
gap: a candidate citing the genuine "Contact Pad Width (X5) / X / 0.60" row and
labelling it `land_pad_length` passed every value check and produced 0.60 by
0.60 mm lands from a document that prints 1.10 mm. `LAND_ROW_MEANINGS` maps each
supported printed row to the feature it denotes, a mismatch is rejected, and a
row the grammar does not map has no established meaning at all. Terminal kinds
are derived the same way, from the printed symbol and function text.

*A receipt is bound to the value it describes.* Every accepted value recomputes
a canonical claim payload and must match the hash its receipt recorded, and
every receipt must carry the current checker version. Without this, a verified
set could be serialised, edited, and revalidated with the original receipts
still attached -- which the same audit demonstrated. Arithmetic cross-checks
additionally bind the claim hashes of all three operands, so a relation cannot
outlive a change to any value it related. The binding is recomputed at the point
of use, not inherited from whoever constructed the object. A pin is supported only inside its own package column; an em
dash means that package has no such pin and the number is not inherited from a
neighbouring column. `CS-SOURCE-CONSISTENCY` additionally checks the arithmetic
the drawing prints about itself, so a single misread digit breaks a relation.
`CS-ORIENTATION` derives pad topology from the drawn lands and requires at least
two printed pin labels to confirm the traversal, because one label cannot
distinguish a clockwise sequence from a counter-clockwise one.

**Then CAD, measured independently.** `CS-PIN`, `CS-DIMENSION`, `CS-ORIENTATION`,
`CS-GEOMETRY` and `CS-LINEAGE` compare measurements parsed out of the emitted
`.kicad_mod` and `.kicad_sym` bytes against the verified source constraints, not
against the generator's own objects and not against the model's JSON. A mutation
that changes the model's claim and the generated footprint together still fails,
because the source check consults neither.

The parser is an *allowlist*. Silently ignoring a construct is indistinguishable
from reading it and finding nothing wrong, so anything the parser does not model
makes the file invalid rather than measured as if it were absent. Concretely: a
`solder_mask_margin` override is refused rather than dropped while the report
goes on calling mask openings explicit; a rotated pad is refused because every
dimension and clearance check measures an axis-aligned envelope, and rotating a
0.60 by 1.10 mm land by 90 degrees puts 1.10 mm of copper across a 0.95 mm
pitch; and a graphic on a copper layer is refused because copper outside the
lands is not modelled. All three passed every check before an audit found them.

`CS-KICAD` asks KiCad to load and render the artifacts, *and* to run ERC on a
generated schematic that uses the symbol and DRC on a generated board that uses
the footprint. Reports bind to the exact artifact and design SHA-256. An
unavailable, crashed or empty run is not a pass, and neither is an existing SVG
found in the output directory: the destination must be empty before the run, the
output must be named for the artifact requested, it must parse as a drawn SVG,
and the input must hash the same afterwards. The connected harness is one
component with labelled pins on a rectangular outline, so a violation is
attributable to the asset; the isolated-pin-label violations such a harness
necessarily produces are recorded rather than hidden.

An empty asset report is never a pass, and neither is a report with any
non-pass finding.

### What a passing component-synthesis result does not establish

- **Not IPC compliance.** The result is datasheet and land-pattern geometric
  conformance within the implemented subset. IPC-7351 is no longer maintained
  and IPC-7352 is a design guideline; matching a pitch establishes neither.
  The emitted courtyard is the verified land extent plus a declared policy
  margin, not a standards-derived courtyard excess.
- **Not manufacturability.** Solder joint reliability, paste volume, stencil
  design, thermal performance and assembly yield are outside these checks.
- **Not electrical behaviour.** Symbol pins are emitted with electrical type
  `unspecified`. A checked pin table row establishes the printed name and
  function; it establishes no operating limit, absolute maximum rating, internal
  connection or behaviour. Electrical profiles are a separate later gate.
- **Not a package body.** When only the recommended land table was read, no
  silkscreen body or fabrication outline is emitted, and the artifact says so.
- **Not simulation.** No model is ingested by these checks; simulation reads
  `UNSUPPORTED` until its own separate gate.
- **Not catalog admission.** Geometric conformance does not make a part eligible
  for a design. Admission evaluates the required-fact matrix separately, and
  `not report.export_blocked` alone is never sufficient.
- **Not a zero error rate on arbitrary PDFs.** Two layout grammars are
  implemented. Any other page shape returns `UNSUPPORTED_SOURCE` and quarantines
  the import rather than degrading to a fuzzy text search.
- **Not a recorded provider response.** The pinned proposal fixture is labelled
  `reconstructed`, not `recorded`. Its request identity was rebuilt from the
  current code and the pinned source the day *after* the provider call, so it
  cannot witness what the model was sent — the argument that the inputs are
  byte-identical is recorded with it, but an argument is not a capture. A
  `recorded` label requires a `captured_at_call_time` identity written during a
  live invocation, which needs the live path in CS-T02-R01. The fixture is a
  valid offline input; extraction fidelity against a live provider is
  UNEVALUATED. The label is carried to the caller by
  `RecordedVisionProvider.replayed_fidelity`, asserted by the corpus tests, and
  written into `CS-T04_evidence.json`, so the durable record states what the
  replayed proposal is. No gate refuses a non-`recorded` fixture, because the
  offline suite is built on one.
- **Resource isolation is bounded, not sandboxed, and it is opt-in.**
  Observation extraction preflights page dimensions, render pixels and
  content-stream size before anything expensive is allocated, and rejects an
  over-long token rather than truncating it. It *can* run in an isolated child
  (`datasheet/isolated_observations.py`) that the parent bounds by wall clock
  and that caps its own address space — read back from the kernel, not echoed
  from the request — before the parser is imported. A worker that times out,
  crashes, returns nothing, returns a bundle for another document, omits a
  requested page, or returns an image that does not match the digest the bundle
  records is an error, never an empty observation.

  What this does **not** establish:
  - It is a resource bound, not a security sandbox. The child keeps the parent's
    filesystem and network access, there is no seccomp/AppContainer confinement,
    and the cap bounds memory rather than CPU or disk. It bounds a decompression
    bomb; it does not contain a parser exploit. The document digest is computed
    inside the child, so the substitution check defends against the wrong file
    being read, not against a subverted worker.
  - **The isolated path has one caller.** `scripts/component_cad_proof.py` is
    the only one. `scripts/record_component_extraction.py`,
    `scripts/component_cad_evidence_images.py` and every test fixture still use
    `BoundedObservationExtractor` in process. Isolation is available, not the
    default.
  - **`ohmni ingest-datasheet` is not covered at all.** The user-facing command
    (`cli.py:cmd_ingest_datasheet`) runs `DatasheetPipeline(PyMuPdfExtractor(),
    …)` in process, with no address-space cap, no wall clock, and none of the
    observation preflights. That is the command a user points at an untrusted
    PDF, and bringing it under these bounds is not in CS-T01–CS-T04.
  - The two mechanisms bound different quantities under the same byte count: a
    Windows job object caps committed process memory, POSIX `RLIMIT_AS` caps
    virtual address-space reservation. Only the Windows behaviour has been
    observed here; the POSIX path runs in CI on `ubuntu-latest` but is not
    reported in this record.
