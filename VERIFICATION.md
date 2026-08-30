# Verification Strategy

> **Status: implemented.** 24 deterministic rules, in
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

Ohmni's initial physical layer implements seven bounded rule IDs: footprint
overlap, outline containment, edge clearance, measured decoupling distance,
connector edge accessibility, complete pin-to-pad binding, and routed-copper
reference integrity. The current compiler intentionally emits no tracks, so
PB-PCB-007 reports that unknown routed references are impossible rather than
claiming routing adequacy.

KiCad DRC is a separate typed external report tied to the exact PCB SHA-256 and
source schematic SHA-256. The golden placed board currently reports 51 real
unrouted connections. This is a truthful DRC failure, not a disguised pass.

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

`PB-ROUTE-001` through `PB-ROUTE-008` check complete pad connectivity,
cross-net shorts, net/lineage validity, board bounds, widths, via geometry,
obstacles, and bounded via use. The golden routed artifact passes these rules
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
