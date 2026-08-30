# Ohmni agent operating manual

Ohmni is an evidence-first AI electronics engineering mentor: **Build circuits.
Understand why.** The product turns typed requirements and verified component
evidence into deterministic semantic, schematic, PCB, routing, manufacturing,
and release artifacts. Start with [README.md](README.md),
[ARCHITECTURE.md](ARCHITECTURE.md), [VERIFICATION.md](VERIFICATION.md), and
[docs/DECISIONS.md](docs/DECISIONS.md); do not duplicate them here.

## Repository map

- `src/ohmni/domain`: typed electrical intent, evidence, reports, notebook events
- `src/ohmni/datasheet`: local PDF normalization and evidence re-verification
- `src/ohmni/verifier`: pure deterministic electrical verification
- `src/ohmni/generation`: provider-neutral structured proposals and bounded repair
- `src/ohmni/eda`: KiCad schematic/PCB compilers and ERC/DRC adapters
- `src/ohmni/physical`, `routing`: placement and deterministic copper routing
- `src/ohmni/manufacturing`, `bom`: fabrication release and prototype economics
- `src/ohmni/application`, `apps/web`: truthful end-user projection and local demo UI
- `tests`: pure, integration, slow-integration, and architecture tests
- `.ai`: development state, tasks, reviews, checkpoints, verification evidence
- `scripts`: repository-development and authoring helpers

## Canonical commands

Use the project virtual environment on Windows (`.venv/Scripts/python.exe`) or
an activated equivalent elsewhere.

```text
python scripts/project_status.py
python scripts/ai_state.py validate
python scripts/ai_state.py next
python scripts/verify.py fast
python scripts/verify.py integration
python scripts/verify.py full
python -m ruff check .                 # lint, when ruff is installed
python -m ohmni verify-all            # product fixture verification
```

No static type-checker or formatter is currently configured; do not claim one ran.

## Architectural invariants

- LLMs propose; evidence grounds; deterministic systems verify.
- Model output cannot create evidence, verified status, ERC/DRC, or supplier facts.
- Datasheet claims require deterministic source relocation and semantic support.
- `CircuitIR` is electrical intent. Schematic, placement, routing, fabrication,
  and their fingerprints are separate transformations with explicit lineage.
- KiCad ERC/DRC independently corroborate Ohmni checks; neither replaces them.
- `UNKNOWN` never silently becomes PASS, zero cost, or available inventory.
- Verification, routing, manufacturing, and BOM arithmetic have no model/network path.
- Supplier descriptions cannot override datasheet electrical truth.

## Git and worktree rules

Inspect status before work. Preserve unrelated changes. Never rewrite accepted
milestone history without explicit human instruction. Commit coherent verified
units and preserve rollback boundaries. Do not knowingly commit broken code except
under a separately human-approved checkpoint policy; normal checkpoints describe
uncommitted work in `.ai/checkpoint.yaml`.

## Autonomous execution and approval boundary

Follow [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md). An agent may execute only
`READY` tasks inside the currently **human-approved** scope, using deterministic
priority then task-ID ordering. It may propose future tasks and document risks.
It must not approve or begin a future product milestone, expand product scope, or
make a major unresolved product/architecture decision. Only a human may change a
scope from `PROPOSED` to `APPROVED`; approval requires `approved_by: human` and
durable evidence. With no approved scope, stop and request human approval.

For “Read the repository state and continue implementation”: inspect Git, run
`ai_state.py validate`, recover any `IN_PROGRESS` task/checkpoint, then run
`ai_state.py next`. Continue approved work until exhausted or a documented stop
condition occurs. Never infer authorization from a proposed backlog.
