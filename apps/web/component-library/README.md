# OHMNI component library

180 entries, OHM-001 through OHM-180. The source is the repository-root
`PCB_COMPONENT_3D_LIBRARY_SPEC.md`. Proposed OHM-201+ entries are excluded.

## Use and layout

`full-registry.js` loads the ten datasets and dispatches to the existing family
registries. `loadFullLibrary()` and `createFullComponent(library, id, {lod})`
are the unified API. The preview URL is `/component-library/preview/index.html?all=1`;
`?stage=1` through `?stage=5` and `?group=a` through `?group=e` remain available.

- `data/`: raw entry fields, source references/hashes, parameters and profiles.
- `generators/`: family geometry plus shared lead, shell, shape and instancing helpers.
- `*-registry.js`: validation, supported variants, dispatch and model metadata.
- `materials.js`: previously approved tokens; `completion-materials.js`: additions.
- `transforms.js`: FCO calculation, explicit footprint bindings and viewer placement.
- `preview/`: renderer-backed model inspection and contact sheets.
- `../tests/component-3d-*.test.mjs`: geometry, source, orientation and completeness tests.

## Add or revise a data record

Edit the approved specification, then the relevant `scripts/import_*_spec.py`
authoring adapter. Completion groups use `import_completion_spec.py` and the
`component_*_profiles.py` adapters. Run the importer, then its `--check` mode.
Reuse an existing family profile for new sizes; add a generator only for a new
geometry family. Coordinates and dimensions belong in the profile, not in an
entry-ID branch in a generator. Add independent expected contact coordinates,
numbering/pin-1 tests, bounds checks and a visual capture. A new ID outside the
approved 180 requires an explicit revision of the completeness contract.

Preserve raw `status` and source fields. `implementation_status: IMPLEMENTED`
means code exists; it never means source dimensions or footprint fit were
verified. Missing noncritical appearance details are tagged
`COSMETIC_PROVISIONAL`, with their value and derivation, and included in
`library_metadata.uncertain_values`. They must stay within the sourced envelope
and cannot move terminals, holes, pin 1 or the mating direction. Conflicts are
explicit records. No electrical admission or automatic footprint binding follows
from a successful render.

## Geometry, LOD and materials

Canonical geometry uses millimetres, XY board plane, +Z up, board top at Z=0,
and the specified footprint-center origin (FCO). Source inconsistencies in FCO
are retained and disclosed; they are not silently recentered. Metadata keeps
all terminal names and contact positions at LOD0, LOD1 and LOD2. LOD0 simplifies
repetition while keeping recognition; LOD1 is the visual-review default; LOD2
uses finer curves and supported detail. Optional unsourced details remain omitted
and are listed in the final report. Marks and printed faces are separate decals.

Use exact `MAT_*` tokens and a scene-owned material factory. Approved materials
are unchanged. Completion additions and provisional FR4 hues are listed in the
completion report. Translucent surfaces remain raycastable and keep component
ownership; transparency does not remove picking geometry. Repeated terminals,
balls and LCD pixels use instancing where appropriate. UUIDs are excluded from
determinism comparisons.

## Footprints and board/viewer adapters

Models and electrical footprints remain separate. `footprintFCO` takes actual
pad/hole extents and an explicit `OHMNI_Y_UP` or `KICAD_Y_DOWN` frame.
`validateFootprintBinding` requires exact component/model/spec/footprint revision
identities, an explicit transform, and a complete named terminal-to-pad mapping.
Binding records do not certify fit.

`placeInViewer` wraps canonical geometry: front models move to +board_thickness/2;
back models move to -board_thickness/2 and use scale(-1,1,-1), preserving the
viewer’s X-flip convention. Placement rotation is applied by the wrapper;
canonical local contacts and geometry stay unchanged. THT tails follow entry
overrides (for example SIP 2.29 mm and trimmer 3.81 mm), otherwise the library’s
board/tail convention.

## Verify and review

Run `node --test apps/web/tests/*.test.mjs`, `python scripts/verify.py full`,
`python -m ruff check .`, and every importer with `--check`. Use the project
virtual environment and set PYTHONPATH to this worktree’s `src` on Windows.
Refresh visual fingerprints with `scripts/prepare_visual_assets.py --source-only`.
Restart the demo server after edits because it snapshots its static asset set.
`scripts/component_completion_capture.cjs` captures a group;
`scripts/component_library_full_capture.cjs` captures all 180.

Completion outputs are in `out/component-library/completion/`; durable gate and
render-hash records are in `.ai/verification/`. The complete coverage, uncertainty,
conflict, material and cosmetic-default tables are produced by
`scripts/component_library_report.mjs`.
