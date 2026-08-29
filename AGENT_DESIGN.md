# Agent Design

## Do not build an agent swarm

Use one orchestrator with specialized deterministic services.

Avoid:
- agents debating each other
- unconstrained planner loops
- free-form state transfer
- repeated self-reflection without external evidence

## Recommended orchestration stages

### 1. Requirement Interpreter
Input:
- natural-language request

Output:
- `RequirementsSpec`

### 2. Datasheet Extractor
Input:
- PDF pages

Output:
- `ComponentSpec`

Constraints:
- all safety-critical facts require evidence
- unknown values remain null
- never infer a nonexistent pin

### 3. Architecture Planner
Input:
- requirements
- known component specs

Output:
- architecture blocks
- candidate components
- constraints

### 4. Circuit Planner
Input:
- architecture
- verified specs

Output:
- `CircuitIR`

### 5. Verifier
Deterministic.

Runs:
- voltage-domain checks
- pin-role checks
- required passives
- bus checks
- power estimates
- package binding
- basic topology rules

### 6. Repair Planner
Input:
- structured verifier failures

Output:
- proposed IR patch

Must not directly mutate files.

### 7. Compiler
Converts IR into KiCad/SKiDL artifacts.

### 8. Lesson Generator
Only generates lessons from verified event logs.

It should not invent engineering explanations unsupported by evidence.

## Repair loop

Maximum 3-5 iterations.

Pseudo-flow:

```text
generate circuit
run verifier
if pass -> continue
if fail:
    send structured failures to repair planner
    apply typed patch
    run verifier again
if still failing after max attempts:
    stop and surface unresolved failure
```

Never silently continue after critical validation failure.
