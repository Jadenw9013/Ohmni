# Next Implementation Steps: Product Readiness

Based on the Ohmni v1 product contract (`docs/product/PRODUCT_V1.md`) and the recent LLM and SPICE integrations, the backend is functional but missing critical enterprise and reliability features to be considered "product-ready".

The following work items must be implemented to elevate Ohmni from a hackathon prototype to a resilient, production-ready sandbox.

## 1. LLM Reliability and Cost Governance
Currently, the `AnthropicProvider` immediately raises a `StructuredGenerationError` if the model hallucinates a bad schema, and there are no financial safeguards against runaway loops.

**Tasks:**
*   **Bounded Schema Retries:** Update `AnthropicProvider.generate_structured()` to catch Pydantic `ValidationError`s. If a validation error occurs, automatically retry (up to 3 times), appending the validation error message to the prompt so the model can correct its own JSON structure.
*   **Token & Cost Tracking:** Extend the `LlmCallRecord` model in `src/ohmni/generation/models.py` to include `model_id`, `input_tokens`, and `output_tokens`. Update `AnthropicProvider` to parse the `usage` block from the Anthropic API response and record these metrics.
*   **Model Optimization:** Switch the default model from `claude-opus-5` to `claude-3-5-sonnet-20240620` (as proposed in `DEPLOYMENT_PLAN.md` §3) to dramatically reduce inference costs while maintaining structured output quality.

## 2. Stateful Sessions & Database
Currently, the backend writes job artifacts to flat files in the Fly.io volume (`/data/demo-jobs`). There is no concept of user ownership, meaning any user can overwrite or view the demo job.

**Tasks:**
*   **SQLite Integration:** Introduce a lightweight SQLite database (`/data/ohmni.sqlite3`) using `sqlite3` or `SQLAlchemy`.
*   **Data Models:** Create tables for `User`, `Project`, and `GenerationRun`. 
*   **API Updates:** Update `scripts/demo_server.py` so the `/api/demo` endpoint generates a unique `job_id` and associates the resulting `DesignReport` and manufacturing artifacts (Gerbers, netlists) with that specific database record, serving them via `/api/jobs/<job_id>`.

## 3. Autorouting Integration
Ohmni successfully places components and verifies connections, but the `Router` protocol in `src/ohmni/adapters/fakes.py` currently returns `UnavailableRouter` for many operations, meaning the board's copper traces aren't physically drawn for new designs.

**Tasks:**
*   **Freerouting CLI Wrapper:** Implement a `FreeroutingAdapter` (similar to `NgspiceAdapter`) that calls the open-source Freerouting CLI to automatically route the KiCad PCB (`.kicad_pcb`).
*   **Integration:** Wire the router into `src/ohmni/generation/orchestrator.py` right before the DRC checks, so the exported manufacturing files contain fully routed copper traces.

## 4. Enhanced SPICE Transients (Educational Value)
The newly added `NgspiceAdapter` calculates the static DC operating point (node voltages). To fulfill the educational "mentor" role, it needs to show dynamic behavior.

**Tasks:**
*   **Transient Analysis:** Extend `SpiceTool` to support transient analysis (`.tran`). 
*   **Graphing Data:** Return the time-series voltage data in the `SimulationRun` model so the frontend can render a graph showing power supply voltage stabilizing over time.

---
**Instructions for Claude Code:**
Read this document and tackle **Phase 1 (LLM Reliability and Cost Governance)** first, as it is the most critical for immediate platform stability. Run `python scripts/verify.py fast` after your changes.
