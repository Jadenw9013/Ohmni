# Domain Model

> **Status: implemented.** This document describes the model as built, in
> `src/ohmni/domain/`. It replaces the original sketch, which could not
> express several of the checks `VERIFICATION.md` requires. The reasoning behind
> each change is in `PRE_IMPLEMENTATION_REVIEW.md` §3–§5 and `docs/DECISIONS.md`.

## Principles

1. **No engineering quantity is a bare string or a bare float.** Everything
   physical is a `Quantity` carrying its `Unit`, stored in canonical SI base
   units.
2. **Provenance is structural, not a label.** A claim's status is *derived* from
   the evidence attached to it and cannot be set directly.
3. **Facts about a part live apart from facts about an instance.** A resistor's
   resistance belongs to the instance; its package options belong to the part.
4. **Electrical properties are derived from topology, not declared.** Nothing
   can assert what voltage a net sits at.
5. **Configured interface mode belongs to the component instance.** Catalog pins
   retain their possible behavior; `ResolvedPinBehavior` derives the effective
   type from catalog roles plus `CircuitComponent.selected_interfaces`.
6. **Physical intent is not electrical intent.** Board constraints, footprints,
   pad bindings and placements live in `ohmni.physical`, outside `CircuitIR`.

---

## Units — `domain/units.py`

```python
class Unit(StrEnum):
    VOLT = "V"; AMPERE = "A"; OHM = "ohm"; FARAD = "F"; HENRY = "H"
    WATT = "W"; SECOND = "s"; HERTZ = "Hz"; CELSIUS = "degC"; METRE = "m"
    COUNT = "count"; RATIO = "ratio"

class Quantity(BaseModel):        # frozen, hashable
    value: float                  # always in the canonical base unit
    unit: Unit

class ValueRange(BaseModel):      # frozen
    minimum: Quantity | None
    typical: Quantity | None
    maximum: Quantity | None
```

`parse_quantity` accepts engineering notation — `"3V3"`, `"4k7"`, `"100nF"`,
`"250mA"`, `"4R7"`, `"22µF"` — and **refuses to guess a dimension** when the
text carries no unit and none was supplied.

`ValueRange` keeps *typical* separate from the limits, which is what lets the
verifier refuse to treat a typical value as a guarantee.

Comparison: `==`, `<`, `>` are exact and unit-checked; `is_close`, `at_most`,
`at_least` and `ValueRange.contains` take an explicit tolerance. See
`docs/DECISIONS.md` §8.

---

## Evidence — `domain/evidence.py`

Three concepts the original documents conflated (`PRE_IMPLEMENTATION_REVIEW.md`
§3.1):

```python
class EvidenceKind(StrEnum):      # where a fact came from
    DATASHEET, CALCULATION, SIMULATION, ERC, DRC, BENCH, HUMAN, CATALOG, ASSUMPTION

class ClaimStatus(StrEnum):       # how strongly one claim is supported (DERIVED)
    UNKNOWN, ASSUMED, CATALOG_REPORTED, CALCULATED, HUMAN_CONFIRMED,
    DATASHEET_SUPPORTED, SIMULATED, ERC_VERIFIED, DRC_VERIFIED, BENCH_VERIFIED

class SubsystemStatus(StrEnum):   # roll-up, per VERIFICATION.md
    VERIFIED, SIMULATED, PARTIALLY_VERIFIED, ASSUMED, NOT_VERIFIED, UNSUPPORTED
```

```python
class Evidence(BaseModel):        # frozen
    kind: EvidenceKind
    label: str
    source_id: str | None
    document: DocumentRef | None
    page: int | None
    snippet: str | None            # verbatim, for re-verification
    snippet_verified: bool | None   # None = not checked; False = check failed
    quantity: Quantity | None
    text_value: str | None
    detail: str | None              # for calculations: the formula and inputs
    recorded_at: datetime

    @property
    def status(self) -> ClaimStatus:   # derived; no setter
```

Per-kind validation is enforced:

| Kind | Requires |
|---|---|
| `DATASHEET` | document *or* `source_id`, a `page`, **and** a verbatim `snippet` |
| `CALCULATION` | `detail` showing the formula and inputs |
| `SIMULATION` / `ERC` / `DRC` | a run id |
| `BENCH` | a measurement id and a measured `quantity` |

A datasheet citation whose `snippet_verified` is `False` yields
`ClaimStatus.UNKNOWN`. **A failed citation supports nothing.**

`Claim` bundles a value with its evidence; its status is the strongest attached.
With no evidence the answer is `UNKNOWN`, which is a successful result.

---

## Component facts — `domain/component.py`

```python
class ComponentSpec(BaseModel):
    part_id: str                    # catalog key, always present
    mpn: str | None                 # real orderable part number; None if generic
    manufacturer: str | None
    category: ComponentCategory
    is_generic: bool
    lifecycle: Lifecycle
    packages: list[PackageOption]
    pins: list[PinSpec]
    supply_rails: list[SupplyRail]
    interfaces: list[Interface]
    i2c_addresses: list[I2CAddressOption]
    regulator: RegulatorSpec | None
    led: LedSpec | None
    decoupling_rules: list[DecouplingRule]
    design_rules: list[DesignRule]
    datasheet: DocumentRef | None
    evidence: list[Evidence]
```

`part_id` and `mpn` are separate so that a generic 4.7 kΩ resistor can exist
without inventing a part number — `EVALS.md` targets invented MPNs at zero.
A non-generic part with no MPN fails validation.

### `SupplyRail` — replaces the flat supply fields

```python
class SupplyRail(BaseModel):
    name: str
    operating: ValueRange           # recommended operating conditions
    absolute_max: Quantity | None   # separate, and never a design target
    absolute_min: Quantity | None
    current_typical: Quantity | None
    current_max: Quantity | None    # peak draw; used for regulator sizing
    evidence: list[Evidence]
```

A part has a *list* of rails. The original single
`supply_voltage_min_v/max_v/absolute_max_voltage_v` triple could not represent
the golden fixture's own sensor: the BME280 has VDD (1.71–3.6 V) and VDDIO
(1.2–3.6 V) as independent domains. A validator rejects an operating maximum
above the absolute maximum.

### `PinSpec`

```python
class PinSpec(BaseModel):
    number: str
    name: str
    roles: list[PinRole]
    electrical_type: PinElectricalType     # KiCad's exact vocabulary
    supply_rail: str | None                # which rail references this pin
    absolute_max: Quantity | None
    absolute_max_above_supply: Quantity | None   # the "VDD + 0.3 V" form
    must_not_float: bool | None            # None -> derived from roles
    internal_pull: Literal["up","down","none"] | None
    evidence: list[Evidence]
```

Two deliberate absences and one deliberate addition:

- **`voltage_domain` is gone.** It was a fact a model could assert. Domain is
  derived from topology instead (`docs/DECISIONS.md` §2).
- **`absolute_max_above_supply`** exists because datasheets usually state I/O
  limits relative to the supply, which no scalar can encode.
- **`electrical_type` uses KiCad's vocabulary** (`power_in`, `power_out`,
  `input`, `output`, `bidirectional`, `tri_state`, `passive`,
  `open_collector`, `open_emitter`, `unspecified`, `no_connect`, `free`) so our
  contention rules and KiCad ERC agree by construction.

---

## Requirements — `domain/requirements.py`

```python
class RequirementsSpec(BaseModel):
    project_name: str
    description: str
    max_input_voltage: Quantity
    target_logic_voltage: Quantity | None
    budget_usd: float | None
    max_board_layers: int = 2
    hand_solderable: bool = True
    min_package_pitch_mm: float | None
    interfaces: list[Interface]                    # enum, not strings
    functional_requirements: list[FunctionalRequirement]
    required_part_ids: list[str]
    prohibited_part_ids: list[str]
    safety_domains: list[SafetyDomain]             # non-empty -> no verified claim
    assumptions: list[str]
    notes: str | None
```

`is_supported_scope` implements the MVP gate from `MVP_SCOPE.md`: ≤ 12 V DC and
no safety domains.

---

## Circuit IR — `domain/circuit.py`

```python
class CircuitIR(BaseModel):
    ir_id: str
    name: str
    revision: int
    parent_hash: str | None
    components: list[CircuitComponent]
    nets: list[Net]
    constraints: list[DesignConstraint]
    design_assumptions: list[str]

    def canonical_form(self) -> dict          # stable ordering, bookkeeping stripped
    @property
    def content_hash(self) -> str             # sha256 over the canonical form
```

```python
class CircuitComponent(BaseModel):   # an INSTANCE
    ref: str                          # "U1", "R3"
    part_id: str
    package: str | None
    value: Quantity | None            # passives: the actual value
    selected_i2c_address: int | None
    placeholder: bool

class Net(BaseModel):
    name: str
    kind: NetKind                     # POWER | GROUND | SIGNAL
    connections: list[PinRef]
    external_source: ExternalSource | None   # the only legitimate declaration
```

Connectivity lives on nets as a list of `PinRef`. A pin belongs to exactly one
net or to none, which removes the class of bug where a pin's idea of its net and
the net's idea of its members disagree.

`content_hash` was added because `AGENT_DESIGN.md` has a repair loop and
`EDGE_CASES.md` warns about it oscillating between two designs — undetectable
without one. `CircuitPatch` / `CircuitPatchOp` give the repair planner a typed
edit format so it never mutates state directly.

The model validates **internal referential integrity only** — unique refs,
unique net names, every `PinRef` naming a component that exists, no pin on two
nets. Whether those pins exist *on the real part* needs the catalog and is
therefore rule `PB-ID-002`, not a model validator: the domain layer does not
reach for infrastructure.

---

## Verification — `domain/verification.py`

```python
class Severity(StrEnum):    INFO, WARNING, ERROR, CRITICAL
class RuleOutcome(StrEnum): PASS, FAIL, INSUFFICIENT_DATA, NOT_APPLICABLE, ERROR
class RuleCategory(StrEnum):
    IDENTITY, CONNECTIVITY, PIN_SEMANTICS, ELECTRICAL, INTERFACE,
    THERMAL, EDA, SIMULATION

BLOCKING_SEVERITIES = frozenset({Severity.ERROR, Severity.CRITICAL})
```

```python
class RuleResult(BaseModel):
    rule_id: str; title: str; category: RuleCategory
    outcome: RuleOutcome
    findings: list[VerificationFinding]
    examined: list[str]        # what the rule actually looked at
    missing_data: list[str]    # why it could not decide
    limitations: list[str]     # what a PASS does NOT establish
    notes: list[str]
    error_text: str | None

class VerificationReport(BaseModel):
    report_id, circuit_ir_id, circuit_content_hash, circuit_revision, generated_at
    results: list[RuleResult]
    subsystem_status: dict[str, SubsystemStatus]

    findings, counts_by_severity, coverage, export_blocked, limitations   # computed
```

`RuleOutcome` and `coverage` are the additions that matter. Without them, a rule
that had no data to check with is indistinguishable from one that checked and
passed. See `docs/DECISIONS.md` §3.

`VerificationFinding.finding_id` is a deterministic hash of the rule plus what it
points at, so the same defect produces the same id across runs.

---

## Events and decisions — `domain/events.py`

```python
class EngineeringEvent(BaseModel):
    event_id: str; kind: EventKind; summary: str; occurred_at: datetime
    circuit_content_hash: str | None
    related_components / related_nets / related_finding_ids: list[str]
    payload: dict; evidence: list[Evidence]

class DecisionRecord(BaseModel):
    decision_id, requirement, decision, rationale
    evidence: list[Evidence]
    alternatives: list[Alternative]
    tradeoffs: list[str]
    verified_by_rule_ids: list[str]
    lesson: Lesson | None
    @property status -> ClaimStatus     # derived from evidence

class Lesson(BaseModel):
    topic: str; body: str
    derived_from_event_ids: list[str]
    evidence: list[Evidence]
```

`Lesson` validates that at least one of `derived_from_event_ids` or `evidence` is
non-empty, and `EngineeringNotebook` validates that every cited event id is
actually in the notebook. A lesson about a repair that never happened is a
validation error rather than a plausible paragraph — which is the structural form
of `AGENT_DESIGN.md`'s "it should not invent engineering explanations".

---

## Types the original document referenced but never defined

`DesignRule`, `EvidenceLink`, `CircuitComponent` and `Net` were referenced but
undefined. `CircuitConstraint` (this document) and `DesignConstraint` (the build
prompt) were the same type under two names.

Resolved as: `DesignConstraint` (the build prompt's name wins), `DesignRule` and
`DecouplingRule` for datasheet-stated guidance, `CircuitComponent` and `Net` as
above. `EvidenceLink` was dropped — evidence is attached directly to the thing it
supports, so a separate link type had nothing to do.

## Routing model

`RoutingProfile` records two-layer prototype defaults and provenance.
`RoutingPlan` is fingerprinted from placed-PCB lineage, profile, ordered nets,
tracks, and vias. Routing cannot mutate `CircuitIR`, placement, or schematic
connectivity.
