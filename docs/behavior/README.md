# Component behavior data

`COMPONENT_BEHAVIOR_SPEC.md` is the research baseline. Its 66 canonical YAML
classes and 180-row master table are projected into typed JSON under
`src/ohmni/behavior/data/` by:

```text
python scripts/generate_behavior_records.py --write
python scripts/generate_behavior_records.py --check
```

Reviewed corrections live in `docs/behavior/gapfill/`; the generator records a
SHA-256 source anchor for the specification and every gap-fill input. The
runtime loader validates those anchors, every generated class link, and every
referenced bench path. Missing or changed evidence fails loading instead of
silently weakening a record.

The files under `bench/` and their ngspice 42 measurements are imported
research evidence. Stage 1 does not rerun them. A future run may be claimed
only after the executable responds to `ngspice -v` and its version is recorded
with the new output.
