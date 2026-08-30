# Architecture

Ohmni is an evidence-first AI electronics engineering mentor. The architecture
supports a path from idea and requirements through evidence-grounded circuit
design, verification, simulation, EDA artifacts, prototyping and learning. The
current MVP remains the low-voltage PCB vertical slice; this broader positioning
does not expand its implementation scope.

## High-level design

Frontend -> API -> Orchestrator -> Typed domain services -> EDA / simulation / verification tools

### Services

- Intent service
- Datasheet ingestion service
- Component knowledge service
- Part resolver
- Circuit planner
- Circuit verifier
- Schematic compiler
- Simulation runner
- Cost optimizer
- Lesson generator
- Artifact exporter

## Critical design rule

No important subsystem should pass unconstrained prose to another subsystem.

Use typed contracts.

Example flow:

`UserRequest`
-> `RequirementsSpec`
-> `ComponentSpec[]`
-> `ArchitectureProposal`
-> `CircuitIR`
-> `VerificationReport`
-> `SimulationReport`
-> `CostReport`
-> `ArtifactBundle`
-> `EngineeringNotebook`

Milestone 4 implements the first bounded generation slice. A provider-neutral
structured-output adapter may propose requirements, architecture, `CircuitIR`, and
typed repair operations. Catalog/pin validation and the deterministic verifier remain
the authority. Only an export-eligible semantic circuit reaches the KiCad compiler.

Physical intent is a separate pure layer: `BoardConstraints`, placements, footprint
and pad bindings never enter `CircuitIR`. The deterministic PCB adapter consumes the
verified circuit plus the exact schematic fingerprint, emits a fingerprinted two-layer
board, runs pure geometry rules, and then invokes KiCad DRC as an independent verifier.

## Recommended stack

Frontend:
- Next.js
- React
- Tailwind
- shadcn/ui optional

Backend:
- Python
- FastAPI
- Pydantic

Domain graph:
- NetworkX or custom graph model

EDA:
- KiCad CLI
- SKiDL or custom emitter
- optional Freerouting CLI

Simulation:
- ngspice

Datasheets:
- PyMuPDF
- structured extraction
- page-aware citations

Persistence:
- SQLite for hackathon
- PostgreSQL later

Async:
- start synchronous
- only add queueing if jobs become too slow

## LLM responsibilities

The LLM may:
- interpret intent
- extract candidate structured facts
- propose architecture
- suggest component alternatives
- propose repairs
- generate educational explanations

The LLM may not be final authority for:
- pin mappings
- voltage limits
- absolute maximum ratings
- MPN existence
- ERC / DRC results
- simulation output
- arithmetic
- lifecycle state
- real-time availability

## Provenance

Every extracted fact should store:

- source document id
- manufacturer
- part number
- datasheet revision
- page number
- source text snippet or structured region reference
- extraction confidence
- verifier status
