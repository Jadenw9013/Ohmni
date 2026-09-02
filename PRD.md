> **Superseded as the product contract.** This document is the hackathon-era
> PRD and is retained as a historical record. The canonical v1 product
> definition is [docs/product/PRODUCT_V1.md](docs/product/PRODUCT_V1.md);
> see [docs/product/](docs/product/README.md) for the full package. Where the
> two disagree, `docs/product/` wins.

# Product Requirements Document

## Product name

**Ohmni**

Tagline: **Build circuits. Understand why.**

Category: **Evidence-first AI electronics engineering mentor**

The name combines *Ohm* and *Omni*: electronics fundamentals with a broader
environment for understanding, designing, verifying and eventually testing
hardware.

## Problem

Existing AI PCB tools often optimize for speed or automation, but hobbyists also need:

- understandable explanations
- affordable component choices
- confidence that niche parts are being interpreted correctly
- transparent sourcing from datasheets
- explicit uncertainty
- low-cost prototyping
- guidance during real-world testing

A novice may receive a plausible schematic without understanding why it works, what assumptions were made, or which parts were actually verified.

## Target user

Primary:
- hobbyist electronics builders
- students
- makers
- software engineers learning hardware
- first-time PCB designers

Secondary:
- educators
- prototyping teams
- robotics clubs
- small startups doing early hardware experiments

## Jobs to be done

Users should be able to:

1. Describe a board they want to build.
2. Upload unfamiliar component datasheets.
3. See structured requirements extracted from their request.
4. See component choices and alternatives.
5. Learn the relevant electronics concepts during the process.
6. Generate a circuit with traceable evidence.
7. Verify the design with deterministic rules.
8. Simulate supported subsystems.
9. Review cost and manufacturability tradeoffs.
10. Export usable design artifacts.
11. Follow a guided prototype test plan.

## Differentiator

The product is not primarily an AI PCB generator. PCB generation is one major
capability in a larger hardware engineering and learning workflow.

It is an **evidence-first AI electronics engineering mentor**.

Every engineering claim should be labeled as one of:

- datasheet-backed
- calculated
- simulated
- ERC/DRC verified
- bench measured
- human confirmed
- assumed
- unknown

## Success metrics

Hackathon demo success:

- user can upload a component datasheet
- structured specs are extracted with page references
- a supported board can be generated
- no unresolved critical verifier failures remain
- all selected parts resolve to known MPNs or user-provided components
- the user sees at least three meaningful educational explanations
- BOM cost is shown with assumptions
- exported artifacts can be opened in KiCad
- final report distinguishes verified from unverified behavior

## Non-goals

- fully autonomous professional PCB engineering
- replacing an experienced electrical engineer
- validating arbitrary safety-critical hardware
- universal analog design
- perfect physical layout
- complete mixed-signal or RF correctness
