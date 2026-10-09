# Landing PCB: isolated visual proof

9 October 2026 · Branch `codex/landing-pcb` · Base `42961353c1b6f111c8a11c82aed5620f6f31ebb0`

**Status: implemented prototype, awaiting owner visual review. Final appearance and physical-fit acceptance remain open.** The production landing is unchanged. No Higgsfield uploads or generation jobs were made, and no credits were spent.

## Review it

Open the local preview at <http://127.0.0.1:8780/landing-pcb-prototype/>. It supports mouse orbit, all 29 parts through a native selector, explicit close-ups, top/side/underside views and an 800 ms camera reveal. Wheel and touch scrolling remain native. Motion preferences and graphics-failure states are covered by the scoped browser checks.

To restart the preview from this worktree, use the project Python environment:

```powershell
& C:/Dev/hackathon/.venv/Scripts/python.exe -m http.server 8780 --bind 127.0.0.1 --directory apps/web
```

Captures are in `out/landing-pcb/p1-final/`: desktop and mobile overview, side/top/underside, U1/U3/J1 close-ups, an additional frontal USB view, a no-finish comparison and `reveal.webm`. `capture.json` records camera settings, source hash, renderer counters and the actual browser/GPU. `poster-provenance.json` records separate source and output identities. The posters in the prototype are exported from the real scene, not generated artwork.

## What changed

- A separate prototype page establishes the proposed hierarchy and camera without changing the existing home page or its routes.
- The shared renderer has optional presentation settings, source-owned instance resolution and explicit hero failure hooks. Existing consumers retain their defaults.
- The camera faces the saved USB opening. Narrow studio reflections, faint deterministic finish textures, a quieter trace color and a separate underside-inspection fill make materials easier to read. Textures change appearance only; no displacement or component coordinates change.
- Instance ownership remains tied to the saved references. Bindings distinguish electrical numbers, repeated physical lands, mechanical holes, derived projections and missing source identities.
- The prototype has a real-scene poster, native component selection and text inspection after WebGL failure. These are scoped P1 behaviors; the full renderer-independent production bootstrap and semantic snapshot remain later work.
- Scene source hashing now includes the new presentation, binding, input and prototype source files. Poster hashes remain separate to prevent a provenance cycle.

No manufacturer details, labels, extra traces, components, antenna patterns, pin positions or simulated-current claims were added. Approved component-library material tokens are unchanged; the presentation palette is owned by the isolated scene.

## Independent review

| Review | Result | Practical meaning |
| --- | --- | --- |
| UI appearance | Ready for owner review; final visual acceptance open | Reflections, trace contrast, underside readability and cavity visibility improved. The close-ups still reveal simplified package models; this is not a finished premium hero. |
| UX, scoped browser checks | PASS, 10 checks | Keyboard selection, native wheel/emulated touch scrolling, motion-Off precedence, reduced motion, unavailable states, cancellation and 320 px reflow work in the tested desktop browser. |
| Engineering, focused suite | PASS, 42 tests | Optional defaults, ownership/disposal, immutable source, stable instance identity, gestures and failure handling have meaningful automated coverage. |

The first UI pass required changes because the object looked flat. The later pass confirms the reflection gradient survives with finish textures disabled, the USB shell has a real cavity and separate tongue, and the underside can be inspected. The first UX pass also caught a stale description after context loss; the revised selector updates the text independently of a disposed renderer.

There is no physical-phone, screen-reader or full accessibility-conformance claim. No full P2/P3 production integration, field performance or release acceptance is implied.

## Evidence and uncertainty

The unchanged saved artifact has 29 references and fingerprint `8ec92f595a26b5769e16186e32231332955db4411247973489abe6c9c9def4f8`. The current renderer reports **37,126 triangles and 77 draw calls** for the overview on AMD Radeon graphics through headless Microsoft Edge. These are complexity measurements, not a complete frame-pacing or mobile-performance certificate.

Desktop poster: **14,356 bytes**. Mobile poster: **5,442 bytes**. Both fit the proposed delivery budgets.

`scripts/report_landing_pcb_bindings.mjs` records all 29 refs, 36 conservative chip-contact overlap observations and six header tail/hole XY observations. All complete physical-fit results remain `NOT_ESTABLISHED`. An overlap observation is not a verified package/footprint binding. No library candidate becomes eligible merely because its nominal name matches; the prototype retains declared source-pad approximations.

Four saved LEDs contain a material source discrepancy: the old reference has pad 1 on the LED anode net and pad 2 on ground, while the newer approved catalog/package binding permutes those identities. The inventory records both without changing the saved geometry, electrical data or polarity labels. The preview adds no mark that falsely resolves this conflict.

The module and sensor retain simplified bodies. Module edge-contact seating and exact manufacturer likeness are not established. The connector has a cavity/tongue but lacks supported mating-contact detail. Those limits remain visible in the report rather than being hidden by material improvements.

## Recommended next refinement

Before calling this the finished landing graphic, the smallest useful geometry work is:

1. J1: obtain the exact connector's supported shell, tongue and mating-contact profile; verify the tongue position and add only evidenced contacts.
2. U1: verify the ESP32 module body, shield and edge-contact treatment against its specific source drawing/model. Keep the saved placement and lands fixed.
3. U3: source lid/port appearance if extreme sensor close-ups remain part of the intended experience.

This does not call for rebuilding all 180 models or changing the board layout. Owner assessment of the overview and U1/J1 close-ups comes before integration. Higgsfield remains a later, separately bounded comparison against these deterministic renders.

## Verification record

The first full-fast attempt was stopped after detecting that the shared virtual environment's editable install resolved `ohmni` from the main checkout. It is not reported as a valid worktree run. The corrected invocation sets `PYTHONPATH` to this worktree's `src` and records the resolved package path. Final results: **1,955 fast tests passed, 82 skipped, 49 deselected; 1,029 frontend tests passed; 12 workflow tests passed; 10 scoped browser checks passed.** Focused Ruff and diff checks also pass. Results and commit identity are recorded in `.ai/verification/LP-P1.yaml`; raw logs remain under `out/landing-pcb/`.

The prior behavior checkpoint, state and task records were preserved before parking CBH-STAGE6 for the user's new priority. No behavior stage was marked accepted as part of this work.
