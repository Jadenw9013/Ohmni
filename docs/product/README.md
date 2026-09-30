# Ohmni product definition

The canonical product layer for Ohmni v1. Created 2026-09-01 against commit
`d7b836e`, after M8 completed and before any M9 scope exists.

**The v1 contract and roadmap below remain PROPOSED.** No milestone is approved by these documents.
Per `docs/AI_WORKFLOW.md`, only a human may move a scope from `PROPOSED` to
`APPROVED`.

Later implementation notes record separately authorized work. See
[Personal sensor projects](PERSONAL_PROJECTS.md) for the implemented A1 unit
and its limits; it does not mark the broader roadmap complete. The audit and
market research documents retain the dates and baselines they evaluated.

For the current repository state, open gaps, verification results, and exact AI
takeover instructions, read
[CURRENT_STATE_DEEP_AUDIT_AND_HANDOFF.md](CURRENT_STATE_DEEP_AUDIT_AND_HANDOFF.md).
It records the pre-atlas implementation baseline. For the subsequent approved
atlas work, read [COMPONENT_ATLAS_IMPLEMENTATION.md](COMPONENT_ATLAS_IMPLEMENTATION.md).
The development ledger under `.ai/` remains the execution authority.

| Document | Owns | Read it when |
|---|---|---|
| [CURRENT_STATE_DEEP_AUDIT_AND_HANDOFF.md](CURRENT_STATE_DEEP_AUDIT_AND_HANDOFF.md) | Current as-built audit, open findings, priorities, and AI takeover procedure | Starting or resuming work in the current repository |
| [THREE_D_COMPONENT_ATLAS_AND_BOARD_BUILDER_PLAN.md](THREE_D_COMPONENT_ATLAS_AND_BOARD_BUILDER_PLAN.md) | Approved component stories and board-builder plan; current progress in [implementation checkpoint](COMPONENT_ATLAS_IMPLEMENTATION.md) | Implementing the component library under its ledger gates |
| [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md) | Historical 2026-09-01 capability baseline: real vs fixture vs absent | Comparing the pre-M9 baseline with later implementation |
| [PRODUCT_V1.md](PRODUCT_V1.md) | The v1 contract, personas, design envelope, archetypes, project model, model boundary | Deciding what we are shipping and to whom |
| [UX_ARCHITECTURE.md](UX_ARCHITECTURE.md) | Journey, information architecture, disclosure, interaction model, component onboarding, the learning product | Designing or building any user-facing surface |
| [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) | Runtime architecture, production model strategy, supply data, security/licensing/legal, observability | Making it run for real users, safely |
| [EVALUATION_PLAN.md](EVALUATION_PLAN.md) | The 120-case product benchmark, thresholds, and physical hardware validation | Deciding whether it works |
| [ROADMAP.md](ROADMAP.md) | M9-M15, P0-P3 prioritisation, what to stop building, product SWOT and risks | Deciding what to do next, and what not to do |

## Relationship to the existing documents

This package is the product contract. It **supersedes** `PRD.md` and
`MVP_SCOPE.md`, which remain as historical hackathon-era records, and it sits
**above** `EVALS.md` and `SWOT.md`, which remain valid at the component level.

It does **not** restate or override the system-as-built documents, which stay
authoritative in their own areas:

- `ARCHITECTURE.md` — services and typed contracts
- `DOMAIN_MODEL.md` — the model as built
- `VERIFICATION.md` — the 24 rules, outcomes, coverage, the export gate
- `SECURITY.md` — trust boundaries and safety policy
- `docs/DECISIONS.md` — decision records
- `docs/AI_WORKFLOW.md` — the development control plane and approval boundary

Where this package proposes a change to one of those (for example, PostgreSQL
rather than SQLite, or a React SPA rather than Next.js SSR), it says so and
gives the reason. Those changes take effect only when the corresponding
milestone is approved and implemented.

## Historical baseline summary

The paragraph below describes the 2026-09-01 pre-M9 baseline. It is retained to
explain the proposed v1 documents and is not a current capability statement.

Ohmni today is an unusually rigorous **deterministic PCB verification and
compilation engine**, wrapped in a one-button demo of a single pre-authored
board. The verification, evidence, and lineage layers are real, general, and
genuinely defensible. The design layer — requirements interpretation, circuit
synthesis, placement — does not exist; it is a scripted replay. The product
problem is not "what feature next"; it is that the demo makes the pipeline look
like the product, when the pipeline is the least differentiated part. v1 should
narrow hard to USB-powered ESP32 sensor and controller boards, derive circuits
from typed briefs rather than generating them, and make the refusal to assert
something a user experiences as valuable rather than as a limitation.
