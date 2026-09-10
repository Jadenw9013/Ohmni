# Structured synthesis benchmark

M10 uses a frozen, agent-authored corpus of **60 structured configurations**
(20 per family) and **20 specific refusals**. Expected inventories, packages,
resolved sensor addresses, SPI chip-select slots and refusal codes were written
before running synthesis. Inputs and expectations have separate SHA-256 hashes.
The complete fixture is pinned by its raw byte hash in the harness.

The 60 cases cover **56 distinct resolved feature topologies**: 20 A1, 16 A2
and 20 A3. Four A2 cases deliberately revisit a feature topology with different
hand-soldering, voltage or budget preferences. This is not 60 distinct circuits
or a natural-language accuracy benchmark. Prose is context for typed inputs;
no blind human authoring, ambiguity handling or adversarial-language score is
claimed. Firmware, simulation and hardware operation remain unmeasured.

`A1-20` retains the configuration that failed in the browser: two BME280s and
one TMP102, all automatic addresses, with the LED and programming header.
It cannot be removed or reclassified because routing fails.

The separate **30-case supplemental safety corpus** covers all nine
`SafetyDomain` values and a 24 V DC input across each of the three families.
Its denominator is separate from the original 20 refusals. Both compiler and
real application paths must return the expected specific refusal, with zero
downstream schematic/native EDA attempts. A scoped canary records and blocks
downstream work if the application wrongly ignores a refusal. This establishes
the bounded refusal behavior, not comprehensive hardware safety validation.

Frozen files:

- `tests/fixtures/synthesis_benchmark.json`:
  `59509e67a669d21b989c17f186c2070318e41b8827ec88c2ab478a39b2ca848e`
- `tests/fixtures/synthesis_safety_benchmark.json`:
  `ba7de58e1674cfbce62c1bb5e1cce76cd5010b6aedc746016a325de7ad80a69c`

Validate the corpus without starting KiCad:

```text
.venv/Scripts/python.exe scripts/benchmark_synthesis.py --validate-corpus
.venv/Scripts/python.exe -m pytest tests/test_synthesis_benchmark.py
```

Run the full benchmark in a **new output directory**:

```text
.venv/Scripts/python.exe scripts/benchmark_synthesis.py --output build/m10-benchmark-run-01
```

On Windows, run real KiCad in normal execution with a fresh, normally accessible
output directory, not a sandbox-created artifact tree. Product adapters use the
guarded native subprocess wrapper. See `docs/KICAD_WINDOWS_DIAGNOSTICS.md`.

The default is two independent full product runs per accepted configuration.
Each invokes `ProjectPipeline` with the exact brief, then real ERC, generated
placement, bounded routing, independent checks, real DRC, manufacturing-profile
verification and fabrication export. No expected answer is passed to the
pipeline, and no manual placement or routing edits are permitted.

Use repeated `--case A1-20 --case A2-16` filters for diagnosis. Filtered runs
retain the fixed 60/20/30 denominators and explicitly do not evaluate milestone
gates. `--repetitions 1` is allowed for diagnosis but cannot establish
reproducibility. There is no resume or directory reuse: changed source, corpus,
tool configuration or benchmark policy requires a fresh run and output folder.

The harness writes `results.json` atomically before each attempt, at every
product progress update, and after every outcome. Every repetition has its own
directory. Failed and interrupted attempts retain diagnostics and raw artifact
hashes. The first-attempt success rate never improves when a later repetition
passes. A hard process termination may leave a RUNNING record; that is an
unfinished measurement, never a success. An orderly interruption is explicit.

The run records source and catalog bytes (including uncommitted changes), Git
HEAD for context, Python/dependency versions, KiCad version/executable hash,
manufacturing-profile hash and routing budget. Source/corpus changes abort the
run; previous results remain. A completed measurement is distinct from passing
the milestone gates: at least 54/60 first runs must reach current DRC 0/0 and a
passing manufacturing profile, all 20 core and all 30 supplemental refusals
must pass, and canonical reproducibility is reported separately. An incomplete
canonical-artifact comparison cannot be counted as reproducible.

Canonical comparisons preserve circuit electrical intent, actual schematic and
placed/routed PCB bytes, the complete placement solution including algorithm,
the actual placement request, and routing geometry/profile/statistics. The
CircuitIR comparison uses its existing electrical canonical form. The only
routing normalization removes timestamped events and replaces its absolute
`source_pcb_path` with the fixed placed-artifact filename. Its original native
hash remains bound to the fabrication manifest. No coordinates, widths, nets,
failures or route statistics are removed. Request, placement, circuit, routing,
report and fabrication lineage are rechecked against the retained files.

Timestamped reports and fabrication bytes are retained under
`raw_artifact_sha256`; they are not claimed to be byte-reproducible. Track length
and via count come from the product's emitted-PCB measurements. Manufacturing
profile and prices remain explicitly synthetic, and package readiness still
requires human manufacturing review.
