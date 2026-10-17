# PCB product reliability audit — 17 October 2026

The audit uses ordinary requests, not the qualified presentation prompt. A successful
run means a fresh PCB, native KiCad checks, and a downloadable package matching the
confirmed brief. It does not mean an assembled, programmed, physically tested device.

## What actually failed

- All six initial production planning probes returned HTTP 200 but stopped on
  clarification questions. Clear temperature/humidity, LED and memory requests
  triggered unnecessary reconfirmation or part-number questions.
- The planner invented a 70 mm minimum for a 50 mm sensor board. The native engine
  actually completed the same board at 50 × 50 mm.
- New projects silently requested hand soldering. The BME280 package could not
  meet that preference, creating a violated requirement after generation.
- The default controller at 50 × 50 mm failed placement at capacitor C5. Greedy
  anchor placement consumed the space needed for mandatory nearby decoupling.
- Temperature-only and temperature-plus-memory plans choosing TMP102 failed
  routing. A diagnostic placement experiment then reached native DRC, exposing
  an additional fixed conflict: the package has 0.15 mm pad gaps but the current
  PCB clearance rule requires 0.20 mm. That experiment is not a released fix.
- A rechargeable Bluetooth key tracker and a smell-identification board require
  hardware/functions beyond the currently implemented families. Generating a
  sensor board is not a substitute for fulfilling those requests.

The original production website room-temperature/humidity test did complete and
actually download a package (job `fc87ed82c354`), after an unnecessary clarification.
The audit therefore distinguishes planning friction, a real native failure, and
unsupported goals rather than treating every failure as an unavailable AI service.

## Changes

- Use family defaults for ordinary engineering choices, preserve explicit user
  requirements and ask about genuine conflicts rather than reconfirming the request.
- Remove the unrequested hand-soldering preference from new family defaults.
  Display assembly guidance before generation. Explicit hand-soldering requests
  that conflict with catalog guidance still require resolution.
- Run deterministic placement before confirmation. If placement fails, test
  larger dimensions with the same parts and offer an actually fitting alternative;
  do not promise routing success or automatically change the user's dimensions.
- Retry failed greedy placement once with mandatory nearby support components
  placed immediately after their anchors. Keep previously successful layouts and
  all spacing/proximity rules unchanged. Record the fallback algorithm in lineage.
- Prefer BME280 for temperature requests while TMP102 is incompatible with current
  rules. Explicit TMP102 choices receive a pre-build refusal explaining the
  clearance conflict and asking whether BME280 is acceptable. Its catalog/editor
  entry remains available for inspecting old projects, with the limitation shown;
  it is not release-ready. No DRC exclusions or clearance reductions were added.
- Show the supported product envelope at idea entry. Explain that BME280 measures
  temperature/humidity/pressure, not gases, smell or air quality.

## Real tests

The same paid-model requests were repeated against the changed local server:

| Ordinary request | Result after changes |
| --- | --- |
| A board to measure the temperature of my room, powered from my laptop. | Ready, confirmed, built, downloaded |
| I need two buttons and a light connected to a small computer board. | Ready, confirmed, built, downloaded |
| I want to save temperature readings to memory on a USB-powered board. | Ready, confirmed, built, downloaded |
| A USB temperature and humidity monitor small enough to fit in a 50 mm square case. | Ready at 50 × 50 mm, confirmed, built, downloaded |
| A rechargeable Bluetooth tracker for my keys. | Clarification; unsupported hardware not silently removed |
| USB-C board to tell different smells apart. | Clarification; no smell sensor fabricated |

Each of the four successful HTTP flows saved the exact reviewed brief and produced
20 files: schematic, placed/routed PCB, nine fabrication files plus their manifest,
report, BOM, placement lineage, confirmed brief, revision receipt and bring-up notes.
Every fabrication file's bytes and SHA-256 matched the manifest. Native default
and 50 mm family matrices also completed all three families after the placement fix.

Reproducible offline/native regressions:

```sh
python -m pytest -q tests/test_conversation.py tests/test_generated_placement.py
python -m pytest -q -m integration tests/test_product_audit_native.py
npm --prefix apps/web test
python scripts/verify.py fast
```

The native regression matrix includes a room monitor, 50 mm controller,
temperature-plus-memory board and 50 mm room monitor. It runs the real pipeline,
including release gates; no stubbed native success is used.

Private/local evidence is under `build/product-audit/` (ignored): planning before/
after JSON, planned-build receipts and ZIPs, native matrix logs, test/deployment
logs and browser screenshots. Do not commit agent download capabilities or keys.
Production follow-up results and exact source commit are recorded in
`.ai/verification/PPA-T01.yaml`.

## Remaining quality work

1. Qualify the entire selectable part/count/address/board-size matrix with native
   builds. A catalogued part and a placement preview do not establish routability.
   TMP102 requires an explicitly reviewed manufacturing-policy/package solution.
2. Evaluate many ordinary prompt variations and conversational corrections with a
   permitted paid provider. Four positive examples establish those examples, not
   universal natural-language reliability.
3. Add board-level firmware and physical bring-up separately. A board with EEPROM
   does not store readings until software performs acquisition and writes.
4. Keep showing UNKNOWN results for unverified budget, RF, thermal and physical
   behavior; manufacturing readiness is not proof that every user goal is met.
