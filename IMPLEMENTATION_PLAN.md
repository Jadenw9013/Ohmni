# Implementation Plan

> **Progress.** Phases 0, 1 and 3 are complete, plus the adapter interfaces from
> the "external integrations" requirement. The order below has changed in two
> places, both marked **[changed]**, with reasoning in
> `PRE_IMPLEMENTATION_REVIEW.md` and `docs/DECISIONS.md`.
>
> | Phase | Status |
> |---|---|
> | 0. Lock the demo | done - ESP32-WROOM-32E environmental logger |
> | 1. Domain foundation | done - `src/ohmni/domain/`, 314 tests |
> | 2. Datasheet ingestion | done - local PDF parsing, bounded extraction, independent evidence verification |
> | 3. Deterministic verifier | done - 24 rules, golden + 13 broken fixtures |
> | 4. Circuit generation (LLM) | not started - deliberately last |
> | 5. KiCad integration | not started - `kicad-cli` 10.0.5 confirmed, spike S1 open |
> | 6. Simulation | not started - **[changed]** target is now a DC operating point |
> | 7. BOM and cost | not started |
> | 8. Teaching UI | not started |
> | 9. Demo hardening | not started |
>
> Phase 3 was pulled ahead of Phase 2 on purpose: the verifier is the product's
> load-bearing claim, and building it first meant the fixtures could prove it
> works before any model or PDF was involved.

## Phase 0: lock the demo

Before coding, choose exactly one golden board.

Recommended:
- ESP32
- USB-C 5 V power
- 3.3 V regulator
- I2C environmental sensor
- status LED
- programming header

## Phase 1: domain foundation - DONE

Built:
- Pydantic v2 models under `src/ohmni/domain/`
- typed units (`Quantity`, `ValueRange`, engineering-notation parsing)
- evidence model with per-kind provenance validation and derived claim status
- circuit IR with content hashing for repair-loop cycle detection
- verification result format with five rule outcomes and reported coverage

Added beyond the plan, because everything else depended on it: a units layer.
No engineering quantity anywhere is a bare string or a bare float.

## Phase 2: datasheet ingestion

Status: **DONE.** Implemented as separate parsing, candidate extraction,
source-relocation, semantic-support and catalog-merge stages. The initial
extractor is deterministic and deliberately bounded; no LLM or network is
required. Scanned PDFs report unsupported rather than invoking OCR.

Build:
- PDF upload
- page extraction
- structured facts
- provenance references
- extraction review UI

Start with one known sensor datasheet.

## Phase 3: deterministic verifier - DONE

24 rules across identity, connectivity, pin semantics, electrical and interface
layers. Every check named here and in `MASTER_BUILD_PROMPT.md` is implemented and
covered by a fixture; see `VERIFICATION.md` for the full table.

Proven against a golden ESP32 circuit (no blocking findings, 100% coverage) and
13 broken variants, each caught by exactly the rule and severity it was built to
trip. `python -m ohmni verify-all`.

This is higher priority than layout, and was also pulled ahead of Phase 2.

## Phase 4: circuit generation

LLM outputs typed `CircuitIR`.

Compiler converts IR into schematic representation.

## Phase 5: KiCad integration

Add:
- project generation (custom emitter, **not SKiDL** - see `docs/DECISIONS.md` §5)
- ERC CLI
- DRC CLI if board exists
- parsed structured output

Confirmed on the development machine: `kicad-cli` 10.0.5 supports
`sch erc --format json`, `pcb drc --format json` and `--exit-code-violations`.
Spike S1 remains: whether a hand-emitted `.kicad_sch` using inline `lib_symbols`
and global-label connectivity is accepted and ERC-checked.

## Phase 6: simulation **[changed]**

Simulate a **DC operating point** first - the LED branch and any resistor
dividers - not the power section.

An LDO simulated without a vendor model needs an invented behavioural model, and
presenting its output as validation is exactly the failure this product exists
to prevent. The LED branch is different: the system already computes its current
by `CALCULATED` evidence, so a SPICE solve reaching the same number is genuine
corroboration by an independent method.

ngspice is **not installed** and has no winget package. KiCad ships it as
`ngspice.dll`, a shared library rather than a CLI, so this needs spike S2. See
`docs/DECISIONS.md` §6.

## Phase 7: BOM and cost

Start simple:
- local part catalog JSON
- optional live supplier API

Compute:
- unit cost
- quantity
- MOQ
- supplier count
- estimated shipping
- manufacturing difficulty score

## Phase 8: teaching UI

For every decision render:

- what changed
- why
- evidence
- alternatives
- verification
- short lesson

## Phase 9: demo hardening

Create:
- known-good cached datasheet
- seeded reference design
- graceful offline path
- saved demo artifact
- precomputed simulation result backup

## Suggested 48-hour breakdown

### Hours 0-4
- repo setup
- domain models
- reference design
- UI skeleton

### Hours 4-12
- PDF extraction
- component structured data
- evidence UI

### Hours 12-20
- CircuitIR
- verifier
- repair loop

### Hours 20-28
- KiCad artifact generation
- ERC integration

### Hours 28-34
- ngspice
- BOM/cost

### Hours 34-40
- educational notebook
- polish

### Hours 40-48
- evals
- bug fixes
- demo rehearsal
- backup demo
