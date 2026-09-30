# Component atlas implementation checkpoint

Scope: `COMPONENT-ATLAS-BUILDER-1`, approved by the user's instruction
“ok begin implementing.” The exact approval and prior component-synthesis
checkpoint are preserved in `.ai/approvals/COMPONENT-ATLAS-BUILDER-1.yaml`.

This is the current takeover document for the atlas work. The earlier
`CURRENT_STATE_DEEP_AUDIT_AND_HANDOFF.md` retains its pre-implementation baseline.
Read the ledger and this document together. Do not resume CS-T05 or real board
editing from an approval inferred from a screenshot or learning scene.

## Current checkpoint

| Task | Status | Implementation commit |
|---|---|---|
| CAB-T01 contracts | COMPLETE | `2c5e585` |
| CAB-T02 library API | COMPLETE | `972800d` |
| CAB-T03 stories | COMPLETE | `0f4c555` |
| CAB-T04 disposable sandbox | COMPLETE | `00fa538` |
| CAB-T05 real layout drafts | Unstarted; CS-T04 dependency incomplete | — |

The scope remains IN_PROGRESS. Task-level reviews were self-reviews; independent
scope acceptance has not happened. Existing CS-T01–T04 remain VERIFIED.

Final working-tree checks: **1,800 fast passed, 49 deselected (266.72 s)**;
**196 frontend passed, zero failures/skips (7.139 s)**; **11 workflow passed
(0.06 s)**; Ruff and `git diff --check` passed. Focused Python gates also passed:
77 contract tests, 68 architecture tests, 28 library tests, and the combined
40 library/static-server tests. These sets overlap; do not add their counts.
The working tree includes the preserved uncommitted CS work, so these are not
claims about a pristine checkout or fresh native KiCad results.

Approval, verification and takeover documents are separate from the product
commits. The mixed `.ai` ledger and workflow test edits remain in the working
tree to preserve the earlier uncommitted CS history; inspect them before any
bulk staging or cleanup.

## CAB-T01: backend contracts

`src/ohmni/domain/component_atlas.py` defines:

- Immutable visual provenance, dimensions, exact asset/footprint references and
  catalog reference projections. Dimensions remain illustrative. No GLB or
  manufacturer-accuracy claim is accepted by this first slice.
- Strict integer nanometre positions and millidegree angles. Coordinates are
  bounded to +/-500 mm; rotations use the canonical interval [0, 360 degrees).
  These are input bounds, not a claim that a placement fits a board.
- Discriminated commands for moving an existing component, proposing a supported
  addition, removing a draft addition, board features/keepouts, undo/redo and
  discard. Schema support is not execution support.
- Revision, artifact, catalog snapshot, sequence and workspace preconditions.
  The later service must obtain context from its store; it must never deserialize
  client context as authority.
- Conservative downstream invalidation: movement preserves electrical intent
  but invalidates physical outputs; electrical additions and history operations
  invalidate all outputs; discard does not mutate the base revision.

`current_library_eligibility` returns learn-only for seed and active records;
quarantined, revoked and unsupported records retain their restricted states.
It cannot return design eligibility until CS-T07/T08 admission is integrated.
Existing-component placement eligibility is still a contextual service check,
not a property conferred by the library record.

The immutable record's `content_sha256` binds its entire serialized content.
The asset reference's SHA-256 identifies its source bytes. Neither is an
evidence receipt or an electrical verdict. Copying a model with modified fields
revalidates its invariants, and receiving boundaries revalidate model instances.

## CAB-T02: read-only component library

`GET /api/components` joins a frozen copy of the seed catalog with a local visual
binding manifest and hashes of the actual served renderer/vendor bytes. The
response contains 12 parts, 19 package variants, exact catalog content revisions,
illustrative models for 10 parts, and explicit missing-model fallbacks for
MCP1700T-3302E-TT and TMP102AIDRLR. Footprint names and hand-solderability are
catalog-reported. Footprint geometry and pin-map revision fields remain absent.

Query parameters: `q` (up to 120 characters), `category`, `status` (`learn`,
`restricted`, `all`), `limit` (1–50), `offset`, and `snapshot`. Ordering is stable
by part ID then package name. Subsequent pages require the exact snapshot hash;
an old hash returns HTTP 409. Unknown/duplicate parameters and invalid bounds
return HTTP 400. Existing API/server/UI identity headers are supported. POST
does not create or modify components. A running server retains its initial
snapshot even when the underlying files change; restart loads a new snapshot.

All current records remain `LEARN_ONLY`. Restricted records are excluded by
default. Imported component admission is not wired into this endpoint yet, and
catalog lifecycle labels are not electrical admission decisions. The local
manifest's sample dimensions are artistic drawing inputs; package size
comparisons and exact-pad previews cannot use them as measurements.

## CAB-T03: component stories

The persistent **Components** header button and home **Explore components**
button open a modal over the current workspace. It provides deterministic
beginner ordering, search, labelled progress buttons, previous/next controls,
package selection, a rotatable illustration, catalog evidence summaries, source
details and explicit unknowns. Arrow keys navigate stories outside the canvas
and input fields; canvas arrows orbit. Horizontal touch swipes belong to the
text panel. There is no automatic story timer. The existing renderer supplies
reduced-motion and hidden-tab handling.

Network reads bind API/server/UI identity and library snapshot across pages.
Stale or invalid responses produce an explicit reload state. Closing cancels
pending reads and restores focus. Story changes reuse the renderer. Missing
models retain the complete text path. **Use in a project** stays disabled.

Browser observations include keyboard navigation, package changes, missing-model
fallback, a 390 x 844 viewport, Escape/focus restoration, and isolated 3D
rendering. An actual screen-reader application and physical phone were not
tested. Accessible names were inspected through the browser accessibility tree;
touch direction/cancellation is unit-tested. These are not substitutes for
CAB-T10's user/device evaluation.

## CAB-T04: disposable placement sandbox

Choose **Components → Try a layout**. The sandbox has a placement map and a
separate 3D preview using the same procedural assets. Drag from the inventory,
pick then tap the map, or use the numeric/keyboard controls. Existing scene
illustrations can be picked from the map or the **In this scene** list.

- 80 x 55 mm artistic scene; 0.25, 0.5 and 1 mm grids.
- Integer positions, quarter-turn rotation, front/back preview.
- Ghost feedback for sample-box overlap and scene bounds. Fit means only an
  artistic fit; electrical and manufacturing checks are unavailable.
- `R` rotates, `F` flips, arrows nudge, Shift increases the step, Enter places,
  and Escape cancels pickup before closing the sandbox.
- Numeric coordinates provide a non-spatial placement path.
- Undo/redo, removal and undoable reset. Discard clears items and history.
  Close and reload destroy the scene; reopening starts empty.
- Maximum 40 placed illustrations and 100 undo snapshots.
- Pointer movement changes only the ghost. The 3D scene rebuilds on a settled
  operation. Orbit gestures belong to the preview and cannot move a map item.

The sandbox modules have no fetch, storage or project API path. They do not
instantiate `DraftCommandRequest`, modify `CircuitIR`, create copper, or write
KiCad files. Sample-box overlap is not a physical component verifier. Opposite
sides may overlap in this educational scene; this says nothing about real
through-hole, keepout, body-height or fabrication constraints.

Real browser checks demonstrated keyboard placement, pointer drag-and-drop,
overlap rejection, out-of-bounds rejection, side preview, undo/redo and discard.
Unit tests check rotated bounds, exact history restoration, immutable state,
finite coordinates, scene/history limits and rejection of authority fields.

## What the next tasks must supply

CAB-T05 and CAB-T06 supply persistence, command replay,
validation, rerouting and actual revision changes. CAB-T07 consumes the completed
component-admission and dynamic-project path for additions.

CAB-T05 must stay unstarted until its dependency CS-T04 is COMPLETE. CS-T01–T04
remain VERIFIED with the previous review/commit holds. The new scope does not
close those findings. CAB-T07 additionally requires CS-T07 and CS-T08. The
full atlas/builder scope is not COMPLETE; independent final review is CAB-T10.

No new HTTP endpoint, interactive canvas action, project mutation, model import,
admission store or geometry verifier is present in CAB-T01. Native KiCad and
live model evaluation are not needed for these pure contracts. Their historical
failures and unevaluated states remain unchanged.

Future handlers must check idempotency before sequence validation: the same key
and identical payload returns the original result; the same key with different
bytes conflicts. Checking request identity is a precondition, never permission
to execute or evidence that a draft is valid.

## Verification and continuation

Run the focused tests with:

```text
.venv/Scripts/python.exe -m pytest tests/test_component_atlas_contracts.py tests/test_architecture.py -o "addopts=-q --strict-markers" -o cache_dir=build/pytest-cab-cache --basetemp build/pytest-cab-focused
.venv/Scripts/python.exe scripts/verify.py workflow
.venv/Scripts/python.exe scripts/verify.py fast
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe scripts/ai_state.py validate
node --test apps/web/tests/*.test.mjs
```

Run canonical Python tiers sequentially: they share `build/pytest`. An early
parallel fast/workflow run collided with that directory. The failed results
and clean reruns are retained in `.ai/verification/CAB-T01.yaml`.

The local server freezes static assets on startup. Restart it after editing UI
files and then reload the browser; a browser reload alone cannot load newer
files from an already-running server. This session's smoke workspace was
`build/cab-ui-preview`, with an explicit provider-free `JobStore`.

The ledger and `.ai/verification/CAB-T01.yaml` through `CAB-T04.yaml` record
actual results, commands, source hashes, commits and limits. Task-level
self-review is recorded as such. Independent final acceptance remains required
by CAB-T10 before the scope can become COMPLETE. CAB-T02 depends on verified,
committed completion of CAB-T01, not an additional independent review gate.

Review should specifically try to forge eligibility, substitute footprint/asset
revisions, submit changed model copies, inject client PASS/evidence fields,
replay stale commands, and omit downstream invalidations.

## Files and ownership

| Area | Files |
|---|---|
| Pure contracts | `src/ohmni/domain/component_atlas.py` |
| Library projection | `src/ohmni/application/component_library.py` |
| Read API and fixed asset snapshot | `scripts/demo_server.py` |
| Local visual bindings | `apps/web/component-visuals.json` |
| Stories | `apps/web/component-stories.js`, `component-stories.css`, `index.html` |
| Learning sandbox | `apps/web/component-sandbox.js`, `sandbox-model.js` |
| Python regressions | `tests/test_component_atlas_contracts.py`, `test_component_library.py`, workflow approval assertions |
| Frontend regressions | `apps/web/tests/component-library.test.mjs`, `component-stories.test.mjs`, `sandbox-model.test.mjs` |
| Execution records | `.ai/approvals/COMPONENT-ATLAS-BUILDER-1.yaml`, `.ai/tasks.yaml`, `.ai/state.yaml`, `.ai/checkpoint.yaml`, `.ai/reviews.yaml`, CAB verification records |

No deployment, paid provisioning or live model call was made. Native KiCad
was not invoked for the learning-only slices. Its previous availability issues
remain unresolved. The scene has no manufacturer model pack, measured package
dimensions, verified pad preview, electrical admission or SPICE validation.

Before broader release, complete the device/user/performance work in CAB-T10,
improve beginner explanations beyond technical seed-catalog descriptions, and
review the existing Three.js environment-blur clipping warnings. Do not present
these implementation tests as physical hardware validation or IPC compliance.
