# Independent audit: CS-T01 through CS-T04

Date: 2026-09-15. Reviewer: Codex, independent of the implementation author.
Verdict: **FINDINGS_OPEN — do not approve this checkpoint or start CS-T05.**

Reviewed the uncommitted implementation on `d7b1175`, not a release commit.
No product code was changed during this audit. Review records and isolated
reproduction artifacts were added. The original approval, historical verification
records, and unrelated changes were preserved.

## Results that were reproduced

| Check | Audit result |
|---|---|
| `python scripts/verify.py fast` | 1,633 passed, 46 deselected |
| `python scripts/verify.py integration` | 27 passed, 2 skipped, 1,650 deselected |
| `python scripts/verify.py workflow` | 11 passed |
| `python -m ruff check .` | Passed |
| `python -m ohmni verify-all` | All 14 fixtures behaved as intended |
| `python scripts/ai_state.py validate` | Passed after review-record updates; workflow checks rerun: 11 passed |
| Independent baseline reconstruction from the pinned PDF | 33/33 asset checks passed; pads measure 0.60 by 1.10 mm |
| Fresh standalone `component_cad_proof.py` | 33/33 asset checks passed; native corroboration failed in this sandbox: footprint export timed out, symbol export crashed after denied creation of `Documents/KiCad` |

The standalone proof's native-tool failure is an environment limitation, separate
from the reproduced verification defects. Its evidence is saved at
`out/component-synthesis-audit/proof/CS-T04_evidence.json`. An additional direct
pytest invocation hit inaccessible default temporary-directory setup; the
canonical workflow command subsequently passed all 11 tests.

These results establish that the existing test suite passes. They do not negate
the false-positive verification cases below. The audit inspected the supplied
source/footprint comparison image and confirmed the displayed table distinguishes
X, Contact Pad Width, from Y, Contact Pad Length.

The local reproduction script and machine-readable results are:

- `out/component-synthesis-audit/reproduce.py`
- `out/component-synthesis-audit/reproductions.json`
- Mutated proposal and standalone CAD artifacts in the same directory.

Run from the repository root with the project virtual environment:

```text
.venv/Scripts/python.exe out/component-synthesis-audit/reproduce.py
```

It reads the existing pinned corpus and writes only inside its audit output
directory. The negative probes intentionally demonstrate incorrect acceptance;
their successful execution is not a product validation pass. Asset hashes in
these probes are recomputed for each candidate artifact, exactly as for freshly
generated files. This tests engineering verification, not accidental detection
of an unchanged manifest hash. The stale-receipt probe uses full
`VerifiedConstraintSet.model_validate`, not Pydantic's unchecked `model_copy`.

## Findings

### CS-AUDIT-001 — HIGH: source checking trusts the model's dimension meaning

Affected: `src/ohmni/datasheet/constraint_verifier.py:687`, especially the mapping
at lines 1175–1184.

`verify_dimension` checks that `candidate.kind` belongs to the set of land
dimensions, then validates the proposed row label/symbol/value/column. It does
not establish that this row actually denotes that `DimensionKind`. The verified
constraint is subsequently built using the model's unchecked kind.

Reproduction: replace the length candidate with a second citation to the real
X/Contact Pad Width row, retaining its correct printed 0.60 mm value, but label
the candidate `land_pad_length`. Omit the optional overall-width and row-gap
claims; retain the genuine adjacent-gap arithmetic. All locators are valid,
source verification succeeds, and the generated 0.60 by 0.60 mm pads pass all 31
remaining asset checks. The original source's Y row prints 1.10 mm as pad length.
No source bytes or observations were modified.

This is precisely the wrong-but-consistent proposal the source gate was intended
to reject. Optional redundancy cannot substitute for semantic association.

Required correction: derive the engineering feature from a checked grammar's
row/symbol/drawing association, compare it to the candidate, and reject any
mismatch. Apply the same principle to other copied categorical fields, including
pin kind. Add the reproduced valid-row/wrong-kind case permanently to the corpus.

### CS-AUDIT-002 — HIGH: supported receipts are not bound to the accepted values

Affected: `src/ohmni/domain/component_synthesis.py:544` and
`src/ohmni/physical/component_asset_verifier.py:129`.

The verified-set validator checks receipt IDs, supported status, and document/
observation digests, but never compares a constraint's payload to the receipt's
`claim_hash`. The original checked candidate is not retained in a form that
allows this association to be recomputed. Asset verification trusts the existing
consistency receipts rather than recomputing their relationship to current facts.

Reproduction: serialize a genuinely verified set, change pad length to 0.60 mm,
overall width to 3.40 mm, and row gap to 2.20 mm; leave every original receipt
unchanged. Full model validation succeeds and newly generated CAD passes 33/33
asset checks. The old receipts still describe the old values.

Required correction: bind every accepted semantic value to a canonical checked
claim payload and its receipt, including identity, ordering, and pin semantics.
Reject mismatched payloads and stale rule versions at deserialization/use
boundaries. Arithmetic receipts must bind all input/output claim hashes. Do not
rely on frozen Python models as integrity protection across serialization.

### CS-AUDIT-003 — HIGH: the asset checker ignores geometry that changes copper

Affected: `src/ohmni/eda/kicad/component_asset_parser.py:166` and
`src/ohmni/physical/component_asset_verifier.py:192`, `:388`.

The parser reads pad rotation, but dimension/clearance checks use unrotated
axis-aligned sizes. Unknown pad fields are ignored. Graphics on copper layers
are parsed or skipped without being included in the copper checks.

Three independent serialized-file mutations pass 33/33 checks:

- Rotate all 0.60 by 1.10 mm pads by 90 degrees. Measured rotations are 90, but
  the check still uses width 0.60 along the row. The actual rectangular envelopes
  overlap because their rotated width is 1.10 mm against 0.95 mm center pitch.
- Add `solder_mask_margin -0.4` to each pad. The parser drops the override and
  the report still says copper, mask, and paste openings are explicit.
- Add an F.Cu graphic line across the bottom pad row. No check examines the
  added copper when asserting that lands are separate.

Required correction: allowlist the exact supported syntax and reject everything
outside it, or preserve and verify its full geometry/semantics. For the current
unrotated SMD subset, reject nonzero rotation rather than silently measuring it
as zero. Include applicable copper primitives, mask/paste overrides, pad shape
parameters, and graphic stroke extents. Each mutation requires a regression.

### CS-AUDIT-004 — MEDIUM: old SVGs can falsely corroborate a new tool run

Affected: `src/ohmni/eda/kicad/component_harness.py:60`, especially lines 79–80.

After a successful exit, the harness accepts any existing SVG of at least 200
bytes in the output directory. It neither isolates this invocation's outputs nor
requires the expected symbol/footprint output name. It can attach a current input
artifact hash to an unrelated older render.

Reproduction: place an unrelated old SVG in the destination and mock a process
that exits zero without creating files. `export_symbol_svg` returns `status=ok`
and `corroborated=True` for a nonexistent requested symbol.

Required correction: use a fresh per-run directory, require exact expected
outputs, validate actual SVG structure/content, and ensure input identity remains
unchanged across execution. Test preexisting unrelated/stale output, zero-output
success, and input replacement.

### CS-AUDIT-005 — MEDIUM: recordings can be relabeled as responses to new inputs

Affected: `scripts/record_component_extraction.py:44` and the corpus replay helper.

The recording script computes a fingerprint from today's instructions, parser,
and rendered images, then assigns that fingerprint to an unchanged historical
proposal and its original provenance. There is no new provider invocation or
immutable original request fingerprint to establish that the model saw those
inputs. The replay helper recommends this rebinding when a recording is stale.

This is acceptable for a clearly labeled scripted fixture, but not evidence of
a recorded response to an exact multimodal request. It undermines the claimed
stale-input check and can hide changes to model instructions/rendering.

Required correction: retain original request/schema/model/render identities with
the response. Changed inputs must require a genuine new evaluation or an explicit
conversion to a scripted test fixture, with extraction fidelity unevaluated.
The default offline tests may use scripted proposals; they must label them so.

### CS-AUDIT-006 — MEDIUM: PDF bounds are enforced after expensive operations

Affected: `src/ohmni/datasheet/pdf.py:236` and surrounding observation extraction.

`get_pixmap()` and PNG compression run before page/pixel dimensions are validated;
`get_text()` and `get_drawings()` materialize data before count limits are tested.
The parser runs in-process without a wall-clock/memory-limited worker. A small
PDF with a very large page or expensive compressed content can consume resources
before the advertised bound rejects it. Individual long tokens are also silently
truncated with `[:200]`, contrary to the no-partial-observation contract.

Required correction: preflight page/render pixel and aggregate budgets, enforce
limits in an isolated bounded worker, and reject oversize tokens explicitly.
Test rejection before raster allocation with mocked oversized pages and bounded
worker timeout/failure cases. No intentionally resource-exhausting PDF was run
during this audit.

## Remaining acceptance gaps

- Live Anthropic vision remains untested as already recorded in CS-T02-R01.
  This audit made no model API calls and did not inspect or change credentials.
- The new native harness only renders standalone libraries. The approved plan's
  connected schematic/PCB ERC/DRC harness for the generated component is absent.
  Passing the repository's other ERC/DRC integration cases does not exercise
  these new assets in that harness. Implement it or obtain an explicit scope
  amendment before claiming that planned acceptance criterion complete.
- CI currently runs `verify.py fast` without acquiring the manufacturer corpus
  or preparing replay fixtures. Source-dependent tests skip when inputs are
  absent. Add a required, reproducible corpus gate; keep general offline tests
  separate so a green CI run cannot stand in for this evidence gate.
- Verification is against uncommitted work. Snapshot hashes accompany this
  audit; final acceptance still needs a coherent commit and fresh verification.

## What should happen next

Repair the source-meaning and receipt-binding defects first, then the serialized
geometry checks and native-output freshness. Add these exact counterexamples as
failing regressions before implementation changes. Address the extraction bounds
and recording provenance, then rerun the checkpoint and independent review.

The existing positive example and much of the architectural separation are
useful foundations. However, the reproduced false-positive checks defeat the
core evidence-first acceptance condition. CS-T05 must remain unstarted; no
catalog, routing, SPICE, deployment, or manufacturer-compliance capability is
approved by this audit.
