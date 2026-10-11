# Component synthesis support and operation

Component synthesis is a bounded, evidence-first import path. It can turn an
exact supported manufacturer document and package selection into immutable
KiCad assets, checked electrical claims and a catalog revision. A proposed
value, matching-looking drawing or successful CAD render is never sufficient by
itself. Source association, emitted bytes, admission rules and native-tool
reports are separate gates.

## Supported envelope

- The automated source grammar recognizes the pinned Microchip land-pattern
  and pin-function table layout used by the MCP73831 SOT-23-5 proof.
- A separately pinned MCP1700 SOT-23 document is held out from parser
  development. Its relevant drawing exceeds the bounded vector-rule limit and
  is rejected before extraction. This is a tested fail-closed case, not support
  for that document or part.
- Reusable rectangular dual-row, QFN and QFP asset compilers are covered by
  deterministic data-row and mutation tests. This does not admit an arbitrary
  part in those families without its own verified source record and electrical
  claims.
- LM317DCYR adds a source-bound TI DCY/SOT-223 record, explicit OUTPUT tab,
  adjustable-divider checks and one exact TI PSpice compatibility result.
- Catalog activation requires every profile fact and applicable rule to pass.
  Simulation eligibility remains separate from CAD and routing eligibility.

Image-only drawings outside the implemented grammar, BGA, arbitrary custom
pads, undocumented exposed-pad or paste policies, RF/high-speed behavior,
switch-mode control loops and unknown electrical profiles remain unsupported.

## Reproduce the acceptance evidence

Use the repository virtual environment from the repository root:

```powershell
.venv\Scripts\python.exe scripts\acquire_corpus.py
.venv\Scripts\python.exe scripts\component_cad_proof.py --out build/component-synthesis/cad
.venv\Scripts\python.exe scripts\component_synthesis_acceptance.py `
  --cad-evidence build/component-synthesis/cad/CS-T04_evidence.json `
  --out build/component-synthesis/acceptance
.venv\Scripts\python.exe scripts\verify.py full
.venv\Scripts\python.exe scripts\verify.py integration
.venv\Scripts\python.exe scripts\verify.py slow
.venv\Scripts\python.exe -m ohmni verify-all
.venv\Scripts\python.exe -m ruff check .
```

The acquisition script accepts only the pinned manufacturer bytes. The CAD
proof reparses generated symbol and footprint bytes, exports real KiCad SVGs,
and runs connected ERC/DRC harnesses. The acceptance script verifies the
declared corpus selectors, prior stage records, exact source digest, portable
LM317 library hashes and restart reconstruction. It writes
`acceptance-report.json`; ignored build output is evidence for that run and is
not a source-controlled claim.

For the LM317 simulation test, set `OHMNI_NGSPICE` to the ngspice-42 console
executable and `OHMNI_LM317_MODEL` to the exact `LM317_TRANS.LIB` whose SHA-256
is recorded in `src/ohmni/catalog/data/synthesis/lm317-dcy.json`.

## Reading the result

`PASS` means every declared gate for the exact recorded inputs completed. A
missing source, missing tool, stale hash, skipped required proof or failed
native command makes the acceptance run incomplete or failed. It is never
converted into a pass.

The user-visible artifacts are the source-bound receipt data, KiCad footprint
and symbol SVGs, portable library manifest, capability states and limitations.
They establish traceability and exact artifact identity. They do not establish
general extraction accuracy, IPC compliance, solder-joint reliability,
manufacturability, firmware behavior, thermal performance, EMC/RF behavior or
successful hardware operation.

The machine-readable case inventory is
`tests/corpus/component_synthesis_acceptance.json`. It names the positive gates
and defined negative corpus used for the zero-false-admission claim. That claim
is limited to those cases and does not imply a zero error rate on unseen PDFs.
