# Architecture

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
