# Technical Debt & AI Handoff (GPT-6)

This document tracks the temporary patches, architectural shortcuts, and deferred features implemented during the rapid LLM integration and deployment sprint. It is intended for a future agent (e.g., GPT-6) to systematically refactor.

## 1. Autorouting (Freerouting Integration)
**The Patch:** `src/ohmni/routing/freerouting.py` was built but deliberately left **disconnected** from the orchestration pipeline.
**The Reason:** 
1. `kicad-cli` (v10) cannot export Specctra `.dsn` files via CLI (it is GUI only), meaning Freerouting has no input.
2. Directly merging Freerouting's `.ses` output into the PCB violates Ohmni's "evidence-first" invariant (`AGENTS.md`), because it introduces copper traces that Ohmni's deterministic verifier never checked.
**The Proper Fix:** Ohmni must export its own `.dsn` file directly from its internal state. It must then parse Freerouting's `.ses` output back into Ohmni's `RoutingPlan` format, pass it through `verify_routing()` for mathematical corroboration, and *then* export it to the final KiCad board.

## 2. SPICE Simulation (Ngspice Subprocess)
**The Patch:** `src/ohmni/eda/simulation.py` invokes `ngspice` via a subprocess CLI call (`ngspice -b <file.cir>`).
**The Reason:** It was the fastest way to parse operating points (node voltages) without dealing with complex C-bindings across different operating systems.
**The Proper Fix:** Refer to "Spike S2" in the codebase. KiCad usually ships `ngspice` as a shared library (`ngspice.dll` or `libngspice.dylib`), not a CLI. The adapter should be refactored to use `ctypes` (or a library like `PySpice`) to bind directly to the shared library. This removes the requirement for the user to manually install the standalone `ngspice` CLI on Windows/Mac.

## 3. The `.env` Loader Hack
**The Patch:** A 9-line manual `.env` file parser was injected at the top of `scripts/demo_server.py`.
**The Reason:** To allow local developers to test with `ANTHROPIC_API_KEY` securely without needing to install new dependencies (`python-dotenv`) across the entire frozen environment.
**The Proper Fix:** Migrate configuration management to `pydantic-settings` or officially add `python-dotenv` to `pyproject.toml`. Remove the manual string-parsing hack at the top of the demo server.

## 4. Pytest Sandbox Permissions
**The Patch:** `scripts/verify.py` was modified to use `_writable_basetemp()` and `_writable_cache()`, which silently fall back to `tempfile.mkdtemp()` if the hardcoded `build/pytest` directory throws a permission error.
**The Reason:** CI and local sandboxes had conflicting ownership of the `build/` directory, preventing the test suite from running.
**The Proper Fix:** Ensure the test runner cleans up these temporary directories after execution. Currently, if the fallback triggers, it will leave abandoned `ohmni-pytest-*` folders in the OS temp directory.

## 5. LLM Cost & Model Management
**The Patch:** The AI adapter heavily leans on `claude-sonnet-5` for all requests. 
**The Reason:** Sonnet is fast and cheap for structured JSON responses.
**The Proper Fix:** `docs/product/DEPLOYMENT_PLAN.md` dictates a multi-model strategy where cheap models handle proposals, but heavy models (like Opus) handle datasheet PDF extraction and verification. The provider layer should be refactored to dynamically route requests to different models based on the task complexity.

## 6. SPICE Transients and Unmodeled Devices
**The Patch:** Transient simulation graphs are built in the frontend UI, and .tran stimulus code exists, but it silently skips generating the graph for the default demo.
**The Reason:** The generated netlist contains unmodeled devices (e.g. the 3V3 voltage regulator). Ngspice correctly rejects this. We cannot simply strip the regulator, or the 3V3 rail will float, rendering the simulation mathematically meaningless.
**The Proper Fix:** Ohmni needs to dynamically inject behavioural SPICE models (.model or .subckt) for voltage regulators and other complex ICs before running the transient analysis. This guarantees the SPICE simulation represents real electrical behaviour rather than a flat line.
