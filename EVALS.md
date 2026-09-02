> **Component-level evals.** This document remains valid for per-subsystem
> extraction, generation, EDA and cost metrics, and its hard targets still
> hold. The **product** benchmark that gates closed beta - 120 user requests,
> acceptance thresholds, the blind human intent rubric, and physical hardware
> validation - lives in
> [docs/product/EVALUATION_PLAN.md](docs/product/EVALUATION_PLAN.md).

# Evaluation Plan

## Build evals before expanding scope

A project like this can appear impressive while being electrically wrong.

## Golden tasks

Create 10-20 small reference tasks.

Examples:
1. MCU + I2C temperature sensor
2. MCU + SPI flash
3. MCU + UART header
4. USB-C powered 3.3 V sensor board
5. sensor requiring external pull-ups
6. component with 1.8 V-only logic
7. duplicate I2C addresses
8. wrong regulator choice
9. missing decoupling
10. package mismatch

## Metrics

### Extraction
- pin extraction accuracy
- operating voltage accuracy
- absolute-max distinction accuracy
- datasheet citation coverage
- hallucinated fields

### Circuit generation
- valid component identifiers
- valid net graph
- critical rule violations
- missing required passives
- invalid voltage connections

### EDA
- artifact parses
- ERC criticals
- DRC criticals
- missing footprints

### Cost
- unresolved BOM items
- stale prices
- unavailable parts
- supplier split count

### Trust
- unsupported claims marked verified
- false-positive verification rate
- unknowns surfaced honestly

## Hard targets

- invented MPNs: 0
- critical voltage violations: 0
- critical ERC violations in final demo: 0
- datasheet-backed claims with source: 100%
- unsupported behavior marked verified: 0

## Regression testing

Every bug discovered during development becomes a permanent regression case.
