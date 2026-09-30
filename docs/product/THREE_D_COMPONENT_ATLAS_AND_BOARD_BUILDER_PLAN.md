# 3D component atlas and interactive board builder plan

**Status:** APPROVED by the human instruction “ok begin implementing.”  
**Scope:** `COMPONENT-ATLAS-BUILDER-1`  
**Approval record:** `.ai/approvals/COMPONENT-ATLAS-BUILDER-1.yaml`  
**Created:** 2026-09-30  
**Dependencies:** contracts and read-only learning may proceed independently;
real board editing retains the component-synthesis review prerequisite, active
catalog admission for imported parts, and reliable KiCad for final checks.

Implementation status and current limitations:
[COMPONENT_ATLAS_IMPLEMENTATION.md](COMPONENT_ATLAS_IMPLEMENTATION.md).

## 1. Product goal

Build one coherent place where a beginner can:

1. discover electronic parts through short, visual, story-like lessons;
2. rotate and inspect a focused 3D model;
3. understand what is known, assumed, illustrative, or unsupported;
4. see where a part appears on real generated boards;
5. drag an eligible part onto a board or reposition an existing part;
6. receive immediate placement feedback;
7. save the change only after authoritative checks pass; and
8. discard the whole experiment without changing the last saved revision.

The intended feel combines two interaction patterns:

- **Story discovery:** a focused sequence of full-screen component cards with
  progress, swipe/keyboard navigation, concise teaching, and a clear next step.
- **Live build mode:** a responsive board workspace with a component inventory,
  a placement ghost, snapping, rotation, collision feedback, undo/redo, and
  disposable draft sessions. It should feel direct like a creative building
  game while retaining electronics engineering authority on the server.

“Disposable” applies to the draft interaction, not to evidence or revision
history. A discarded draft leaves the source revision and artifacts unchanged.

## 2. What already exists

Ohmni does have a 3D visual library, but it is not yet the requested product.

### Existing reusable foundation

- `apps/web/visual-assets.js` contains **26 original procedural visual
  families**. They include leaded and leadless IC forms, connectors, cans,
  resistor-like bodies, inductors, switches, LEDs, sensors, regulators, an
  ESP32 module, USB-C, headers, and source-pad-driven actual-board families.
- Every visual family has a versioned `modelAssetId`, units, up axis, contact
  plane, source record, and an explicit `appearanceOnly` flag.
- `apps/web/visual-inventory.js` contains an educational reference inventory:
  **158 source inventory records**, **124 modeled bodies**, and **18 beginner
  family lessons**. The source identity and electrical functions remain unknown.
- `apps/web/visual-explorer.js` already renders a searchable component atlas,
  close-ups, family preview tiles, source/unknown disclosures, keyboard focus,
  and a dense educational board.
- `apps/web/visual-board-scene.js` maps real generated-board components to visual
  families while preserving artifact coordinates, source pads, rotations,
  sides, component references, footprint IDs, and artifact fingerprints.
- `BoardView` and `VisualRenderer` already provide orbit, zoom, pan, picking,
  focus, front/back views, reduced motion, WebGL fallback behavior, and resource
  disposal.
- The product UI already exposes a home-page component atlas and a separate 3D
  circuit lab for generated boards.
- The frontend suite tests visual source separation, family construction,
  source-pad contacts, picking, geometry immutability, accessibility behavior,
  resource disposal, and artifact identity.

### What does not exist

- No durable backend component-library API exists.
- The atlas is primarily an illustrative reference scene, not the authoritative
  catalog of parts a user may add to a project.
- The family grid is hidden inside the visual explorer and is not integrated
  with project choices or the board workspace.
- Users cannot drag a component or board feature onto a PCB.
- Users cannot move an existing component and save a new checked revision.
- Visual models do not establish footprint, pin map, electrical behavior,
  supplier identity, package dimensions, or design eligibility.
- No manufacturer STEP/GLB model pack is shipped. The generated PCB currently
  has no KiCad 3D model associations.
- There is no draft session, undo/redo command log, stale-revision protection,
  or explicit discard workflow for interactive edits.
- Adding a visual body cannot yet create or modify `CircuitIR`, placement,
  routing, or manufacturing artifacts.

The correct implementation extends the current renderer and catalog. It must
not create a second unconnected 3D system.

## 3. Non-negotiable trust boundary

The interface may feel immediate, but the frontend never becomes engineering
authority.

### Three kinds of library item

| Item state | User experience | Permitted action |
|---|---|---|
| `LEARN_ONLY` | Inspect, rotate, compare, save to a learning collection | May enter only the disposable educational sandbox. Cannot enter a real project. |
| `PLACEMENT_ELIGIBLE` | Represents an existing component already in the current `CircuitIR` and compiled footprint set | May reposition/rotate within a draft. Cannot change its pins, nets, package, or identity. |
| `DESIGN_ELIGIBLE` | Active admitted catalog revision with required electrical profile, footprint, pin map, evidence coverage, and supported synthesis role | May be proposed as a new component through a typed design operation, then checked server-side. |

An item can also be `QUARANTINED`, `REVOKED`, or `UNSUPPORTED`. Those states are
visible and never become addable because a model looks plausible.

### Two different drag operations

1. **Move an existing board component.** This changes physical placement only.
   Electrical intent and connectivity remain unchanged. Placement, routing,
   DRC, manufacturing, and downstream fingerprints become stale.
2. **Add a new component.** This changes project intent and `CircuitIR`. The
   user must choose a supported function or resolve a typed requirement. The
   server synthesizes the electrical addition, then reruns semantic, schematic,
   placement, routing, ERC/DRC, and release gates as applicable.

A canvas drop alone never means “electrically connected.” A new item appears as
a **candidate** until its supported role and connections are resolved.

### Board features

The first release may support these non-component items:

- admitted test points;
- mounting holes with explicit plated/non-plated type and keepout;
- fiducials with an explicit manufacturing profile;
- board keepout regions;
- notes and visual measurements that never enter fabrication.

Do not initially make traces, vias, copper pours, arbitrary pads, antennas, or
untyped decorative geometry draggable. Those require separate electrical or
manufacturing contracts and can easily imply correctness they do not have.

## 4. User experience

### 4.1 Entry points

The atlas is cross-cutting and should not become another numbered engineering
stage. Add it in four places:

1. **Home:** rename the current dense-board feature to **Explore components**.
   Offer “Start a 60-second tour” and “Open the full atlas.”
2. **Project brief:** show a compact **Parts for this board** strip containing
   only supported choices relevant to the selected family.
3. **Board review:** add **Edit layout** beside the existing front/back/reset
   controls. It opens build mode for existing components.
4. **Build & export:** each part card links to its atlas detail, evidence, and
   exact board location.

Add a persistent **Components** button in the workspace header. It opens a
drawer over the current stage without changing or discarding project state.

### 4.2 Story discovery mode

The story deck is an educational navigation layer over authoritative records,
not a social feed.

Each story contains:

- a large isolated 3D model with drag-to-orbit and tap-to-pause motion;
- family and part name, package, and category;
- a 10–20 second “what it does” explanation;
- one construction detail to inspect;
- one “what we do not know” disclosure;
- evidence badge: `SOURCE_VERIFIED`, `CATALOG_REPORTED`, `ASSUMED`,
  `ILLUSTRATIVE`, or `UNSUPPORTED`;
- a footprint/pad view toggle;
- “used on these boards” examples derived from real project records;
- “compare package sizes” using only dimensional records with known provenance;
- `Learn`, `See on board`, and, when eligible, `Use in project` actions.

Story queues should be deterministic and explainable:

- **On your board** — existing components in signal-flow order;
- **Start here** — resistor, capacitor, LED, button, connector, regulator,
  controller, sensor;
- **Package shapes** — 0805, SOT-23-5, SOIC, LGA, module, through-hole;
- **Power path** — parts from source to regulated rail;
- **Recently admitted** — only active catalog revisions;
- **Needs evidence** — educational records that demonstrate honest unknowns.

Desktop supports click, wheel, arrow keys, and visible previous/next buttons.
Touch supports horizontal swipe. Progress segments are buttons with labels, not
color-only indicators. Motion pauses when the tab is hidden and respects
`prefers-reduced-motion`.

### 4.3 Live build mode

#### Desktop layout

Use a three-pane workspace:

```text
┌──────────────────────┬────────────────────────────────┬─────────────────────┐
│ Component inventory  │  Interactive board             │ Selection / checks  │
│ Search and filters   │  Ghost, grid, clearances       │ Identity, role,     │
│ Story preview        │  front/back, move, rotate      │ evidence, problems  │
└──────────────────────┴────────────────────────────────┴─────────────────────┘
│ Undo  Redo  Discard draft        Validate draft       Save new revision    │
└─────────────────────────────────────────────────────────────────────────────┘
```

The inventory separates:

- **On this board** — movable existing components;
- **Can add** — active `DESIGN_ELIGIBLE` parts supported by the selected family;
- **Learn only** — visible but disabled for real-board drops;
- **Board features** — only explicitly supported mechanical/manufacturing items.

#### Drag interaction

1. Pointer down or keyboard **Pick up** creates a local drag preview.
2. The preview follows a board-plane ray intersection, snaps to the selected
   grid, and displays the exact X/Y/rotation/side.
3. Fast local geometry checks display:
   - board bounds;
   - component overlap;
   - keepout intersection;
   - connector/antenna edge rules available in the current placement request;
   - a visible `UNKNOWN` when a rule cannot be evaluated locally.
4. Green means “locally eligible for server validation,” not PASS. Red means the
   known local geometry is invalid. Amber means unresolved or server-only.
5. Drop creates a draft command. It does not mutate the saved revision.
6. The server evaluates the command and returns authoritative findings.
7. A new component opens **Connect this part**, showing only supported roles and
   choices. Freehand net invention is outside the initial release.
8. **Validate draft** runs all invalidated deterministic stages.
9. **Save new revision** is enabled only when the recorded release policy allows
   it. The old revision remains immutable.

#### Minecraft-like directness without hidden authority

- Show a translucent block-like placement ghost.
- Snap to 0.25, 0.5, or 1.0 mm grids.
- `R` rotates; `F` requests a side change when the footprint supports it;
  arrow keys move by one grid unit; Shift moves by ten.
- Show clearance halos and keepouts as overlays.
- Draw a temporary ratline only from server-supplied connectivity.
- Update a small status strip continuously: `Fits`, `Needs server check`,
  `Collision`, `Outside board`, `Rule unknown`, or `Not addable`.
- Support multistep undo/redo through explicit commands.
- Provide **Reset placement** for one item and **Discard draft** for the session.
- Never write copper, reroute, or claim DRC continuously while the pointer moves.
  Full routing and native checks begin only after a settled draft request.

#### Mobile and accessibility

HTML drag-and-drop is not sufficient because it is weak on touch and keyboard.
Use Pointer Events plus an explicit command path:

- Tap an item, choose **Add to board**, then tap a board location.
- A bottom sheet exposes coordinates, rotation, side, and nudge controls.
- Keyboard users can pick up, move, rotate, drop, cancel, undo, and inspect every
  item without the canvas.
- A text placement table mirrors every draft component and validation result.
- Screen-reader announcements describe the selected item, proposed coordinates,
  local state, and authoritative server result.
- Cancellation always returns focus to the originating item.

## 5. Data contracts

### 5.1 Visual asset record

Create a backend-owned record; do not derive electrical eligibility from the
JavaScript registry.

```text
VisualAssetRecord
  asset_id                 stable namespace
  revision                 immutable revision
  content_sha256           exact shipped bytes or procedural source bundle
  representation_grade     ILLUSTRATIVE_FAMILY | ARTIFACT_BOUND |
                           MANUFACTURER_MODEL | VERIFIED_GENERATED
  format                   PROCEDURAL_THREE | GLB
  units                    mm
  up_axis                  z
  contact_plane_mm         0
  origin_policy            footprint origin / declared transform
  dimensions               values plus evidence status and source receipts
  contact_basis            NONE | ILLUSTRATION_PARAMETERS | SOURCE_PADS
  model_source             project / manufacturer / upstream library
  license                  identifier, attribution, redistribution decision
  limitations              explicit user-visible strings
  lods                     optional immutable lower-detail asset revisions
```

Do not ship raw STEP to the browser. A reviewed offline pipeline may convert a
licensed source model to bounded GLB, normalize units/axis/origin, compute
bounds, reject external URIs/scripts/extensions, and record hashes. Procedural
families remain the fallback.

### 5.2 Component reference record

```text
ComponentReferenceRecord
  catalog_part_id
  catalog_revision
  display_name
  category
  package_variant
  footprint_revision
  visual_asset_revision
  visual_transform
  pin_map_revision
  evidence_summary
  design_eligibility
  supported_roles[]
  supported_project_families[]
  assembly_guidance_status
  lifecycle_status          QUARANTINED | ACTIVE | REVOKED
```

The binding must be exact by admitted revision. Part-name similarity, package
name similarity, or model appearance cannot select a footprint or visual model.

### 5.3 Draft command log

```text
BoardDraft
  draft_id
  project_id
  base_revision_id
  base_artifact_fingerprint
  owner_workspace_id
  sequence
  status                    OPEN | VALIDATING | VALID | INVALID |
                            COMMITTED | DISCARDED | STALE
  commands[]
  invalidated_stages[]
  latest_validation_id
```

Initial commands:

```text
MoveExisting(component_ref, x_nm, y_nm, rotation_mdeg, side)
AddSupported(role_id, catalog_part_revision, requested_location)
RemoveDraftAddition(draft_component_id)
AddMountingFeature(feature_revision, x_nm, y_nm, rotation_mdeg)
SetBoardKeepout(points_nm)
Undo(sequence)
Redo(sequence)
DiscardDraft
```

Use integer nanometres and millidegrees at the API boundary. The browser may
display millimetres/degrees but must not become the canonical rounding authority.

## 6. API and service design

Suggested read endpoints:

```text
GET /api/component-library
GET /api/component-library/{catalog_part_id}/{revision}
GET /api/component-library/{catalog_part_id}/{revision}/visual
GET /api/projects/{project_id}/revisions/{revision_id}/builder-capabilities
```

Suggested draft endpoints:

```text
POST   /api/projects/{project_id}/revisions/{revision_id}/drafts
GET    /api/projects/{project_id}/drafts/{draft_id}
POST   /api/projects/{project_id}/drafts/{draft_id}/commands
POST   /api/projects/{project_id}/drafts/{draft_id}/validate
POST   /api/projects/{project_id}/drafts/{draft_id}/commit
DELETE /api/projects/{project_id}/drafts/{draft_id}
```

Every mutation includes:

- expected base revision and artifact fingerprint;
- monotonically increasing sequence number;
- idempotency key;
- exact catalog and asset revisions;
- one typed command;
- client UI version for diagnostics, never authority.

Reject stale bases with a conflict that offers **Discard**, **Open latest**, or
**Fork from this revision**. Never merge placement or electrical commands
silently.

The library service may read admitted catalog snapshots. Verification,
placement, routing, manufacturing, and BOM arithmetic retain no model/network
path.

## 7. Validation and invalidation

### Moving an existing component invalidates

- placement report and placement fingerprint;
- routing plan and routed PCB;
- physical checks that depend on position;
- DRC and manufacturing outputs;
- reference-board projection and build package.

It does not change `CircuitIR`, semantic connectivity, or source evidence.

### Adding a component invalidates

- confirmed requirements affected by the new role;
- `CircuitIR` and semantic report;
- schematic, ERC, placement, routing, DRC;
- BOM/economics/manufacturing and every downstream artifact;
- educational flows and component explanations.

### Validation ladder

1. Schema and revision identity.
2. Catalog lifecycle and design eligibility.
3. Supported-role and family compatibility.
4. Semantic electrical verification.
5. Deterministic placement checks.
6. Schematic compilation and ERC.
7. Bounded routing and independent route verification.
8. PCB compilation, parsed-byte checks, and DRC.
9. Manufacturing profile and release eligibility.

The UI shows each stage independently. A quick local fit check must never be
displayed as equivalent to the full ladder.

## 8. UI module boundaries

Extend the existing modules as follows:

| Module | Responsibility |
|---|---|
| `visual-assets.js` | Continue to construct versioned appearance-only procedural models. No eligibility logic. |
| `visual-renderer.js` | Render procedural assets and later vetted GLB nodes; expose board-plane ray intersection and selected-object transform previews. |
| `board-view.js` | Camera, picking, ghost preview, overlays, and accessible interaction callbacks. It does not mutate project state. |
| `component-atlas-model.js` | Pure formatting/filtering of server-owned library records and story queues. |
| `component-atlas.js` | Story deck, search, filters, detail panel, and eligibility actions. |
| `board-builder-model.js` | Pure draft reducer, undo/redo projection, invalidation display, and conflict handling. |
| `board-builder.js` | Pointer/keyboard orchestration, inventory drawer, draft commands, and server validation requests. |
| `client-contract.js` | Validate library/draft response versions and server identity. |
| Python library projection | Join active catalog revisions, visual bindings, evidence summaries, and supported roles. |
| Python draft service | Own base revisions, command sequence, validation, persistence, commit, and discard. |

Do not place drag mutation code inside `visual-explorer.js`; it is an educational
view and currently guarantees that its sample is never sent to project APIs.

## 9. Implementation tasks

The human approved this plan and CAB-T01 through CAB-T10 are recorded in
`.ai/tasks.yaml`. Approval does not complete their dependencies. The ledger owns
the current status and execution order; the acceptance criteria below remain
the implementation contract.

### CAB-T01 — freeze contracts and eligibility states

**Goal:** define immutable visual records, exact catalog bindings, draft
commands, invalidation rules, and user-visible statuses.

**Acceptance:** architecture tests prove visual data cannot grant design
eligibility; `LEARN_ONLY` and quarantined assets fail closed; records carry
source/license/hash/limitations; integer coordinate rules are fixed.

### CAB-T02 — backend component-library projection

**Goal:** expose a read-only API joining the existing visual registry with
server-owned catalog snapshots and evidence summaries.

**Acceptance:** deterministic pagination/search/filtering; exact snapshot hash;
no client-supplied evidence; twelve current catalog records represented; missing
visuals use an explicit fallback; revoked/quarantined items remain visible only
under appropriate filters and cannot be added.

### CAB-T03 — story discovery experience

**Goal:** make the atlas a first-class home/header experience with deterministic
story queues and accessible navigation.

**Acceptance:** desktop, touch, keyboard, screen-reader, reduced-motion, and
renderer-fallback paths; story facts match backend records; every unknown and
illustrative limitation is visible; no project mutation occurs.

### CAB-T04 — disposable placement sandbox

**Goal:** implement drag/tap/keyboard placement on a non-project sandbox using
the existing procedural assets.

**Acceptance:** snapping, rotate, side preview, collision/out-of-bounds states,
undo/redo/reset/discard, mobile controls, and zero saved-project writes. Reload
or discard destroys the sandbox unless the user explicitly saves a learning
scene separate from engineering projects.

### CAB-T05 — existing-component layout drafts

**Goal:** move and rotate components already present in an immutable project
revision.

**Acceptance:** server-owned `BoardDraft`; stale-base conflicts; complete
physical invalidation; no changed nets/pads/parts; deterministic command replay;
discard leaves source bytes unchanged; committing creates a new revision.

### CAB-T06 — authoritative placement validation and reroute

**Goal:** validate a settled layout draft through placement, routing, parsed
artifact checks, ERC/DRC where applicable, manufacturing profile, and lineage.

**Acceptance:** deliberately overlapping/out-of-bounds/keepout/antenna-edge
placements fail; unavailable KiCad remains unavailable; routing failures remain
explicit; generated artifacts bind the draft and base fingerprints; no old
download remains enabled after an edit.

### CAB-T07 — supported component addition

**Goal:** let users drag a `DESIGN_ELIGIBLE` part into a supported project role.

**Dependencies:** component admission gates equivalent to CS-T07 and the dynamic
project/resume path equivalent to CS-T08.

**Acceptance:** drop creates a candidate; role resolution precedes electrical
addition; one admitted component traverses semantic, schematic, ERC, placement,
routing, DRC, manufacturing, learning projection, restart, and download with
exact lineage; unsupported roles and negative requests cannot bypass admission.

### CAB-T08 — mechanical board features

**Goal:** add typed mounting holes, test points, fiducials, and keepouts.

**Acceptance:** each feature has a source/profile basis, exact fabrication
semantics, independent parsed-byte checks, and mutation tests. Decorative models
cannot create fabrication features.

### CAB-T09 — vetted external 3D assets and LOD

**Goal:** add manufacturer or upstream models only where identity, transform,
license, and redistribution are resolved.

**Acceptance:** bounded offline conversion, exact hashes, no external runtime
fetches, origin/pad alignment tests, top/bottom/rotation/repeated-instance tests,
license manifest, procedural fallback, and measured browser memory/load budgets.

### CAB-T10 — acceptance and product evaluation

**Goal:** complete usability, accessibility, performance, safety, and independent
review gates.

**Acceptance:** held-out user tasks cover discovery, placement, cancellation,
conflict recovery, invalid geometry, supported addition, and exact revision
history; independent review has no open blocker/high finding; all canonical
tiers pass with current KiCad; documentation and UI state all limits.

## 10. Verification strategy

### Deterministic unit tests

- library filtering never changes eligibility;
- story ordering is stable and derived from explicit records;
- coordinate snapping and rotation use integer canonical values;
- command replay produces the same draft fingerprint;
- undo/redo restores exact command-state hashes;
- discard leaves the base revision and artifacts byte-identical;
- visual asset mismatch cannot select a footprint;
- a moved component retains exact part, pad, and net identity;
- every edit invalidates the correct downstream stages.

### Adversarial tests

- relabel an illustrative model as an active component;
- keep the same model name while changing its hash;
- bind a visually similar package to the wrong footprint;
- change visual dimensions while retaining evidence receipts;
- submit client-side PASS states;
- drop outside the board or across a keepout;
- overlap rotated components;
- reuse a stale base revision;
- reorder/duplicate command sequence numbers;
- revoke a part while a draft is open;
- lose KiCad or time out routing during validation;
- import GLB with external resources, extreme bounds, invalid units, or an
  unsupported extension.

All must fail closed or produce a typed unresolved state.

### Browser and accessibility tests

- pointer, touch, keyboard, and text-table placement produce the same command;
- story controls have labels and deterministic focus order;
- reduced motion eliminates automatic transitions;
- Escape cancels pickup before closing the drawer;
- renderer loss preserves all text and placement controls;
- mobile bottom sheet never covers the selected position/status;
- discard and save are visually and semantically distinct;
- stale results disable every old artifact download;
- no drag action fires from orbit/pan gestures.

### Native and end-to-end tests

- move an existing component, reroute, and obtain current ERC/DRC evidence;
- reject deliberate overlap and wrong keepout placement;
- add one admitted component through the full pipeline;
- restart the server and recover the exact open draft or committed revision;
- compare emitted PCB bytes against the draft command lineage;
- verify process cancellation leaves no KiCad/router descendants.

## 11. Performance budgets

Measure on named desktop and mobile-class devices; do not claim universal frame
rates.

Initial targets:

- first story interaction available within 1.5 s from cached local assets;
- atlas metadata under 250 KiB compressed for the initial active catalog;
- no individual browser GLB over 1 MiB without an explicit exception;
- at most 40 visible high-detail component instances before LOD/instancing;
- pointer-move work contains no API calls and no mesh rebuild for unchanged
  family geometry;
- draft command response under 150 ms for persistence/schema checks;
- local fit feedback within one animation frame on the acceptance devices;
- authoritative validation remains asynchronous with visible stage progress and
  explicit timeouts.

If a device misses the measured target, reduce LOD/shadows or use the text/table
builder. Never remove evidence or validation to improve frame time.

## 12. Analytics and product evaluation

For the local prototype, keep analytics local and aggregate only with explicit
user consent in a later hosted product.

Useful events:

- story opened/completed/skipped;
- evidence details opened;
- `Use in project` attempted and eligibility result;
- pickup/drop/cancel;
- local invalid-placement reason;
- draft validate/discard/commit;
- undo/redo;
- renderer fallback;
- successful keyboard-only task.

Evaluate with at least five beginners and three experienced PCB users. Core
tasks:

1. find a regulator and explain what is known versus illustrative;
2. locate that regulator on a generated board;
3. move an existing LED without changing its electrical connection;
4. discover and correct an invalid overlap;
5. discard an experiment and confirm the original revision remains;
6. add one supported part and understand why connection/verification is still
   required.

Measure task completion, incorrect confidence, time to recover, accidental save,
and whether users understand that local green placement is not final DRC.

## 13. Rollout sequence

1. **Read-only atlas:** promote the existing family catalog and bind it to
   backend records.
2. **Story discovery:** ship the beginner learning flow with no project writes.
3. **Disposable sandbox:** prove direct manipulation, touch, keyboard, discard,
   and performance without engineering mutation.
4. **Existing-part layout drafts:** enable safe physical edits and immutable new
   revisions.
5. **Full validation/rerouting:** connect settled drafts to deterministic/native
   gates.
6. **Supported additions:** only after component admission and dynamic project
   integration are complete.
7. **Mechanical features and vetted GLB:** expand after the core workflow is
   measured and independently reviewed.

Each step can ship independently without pretending the next step exists.

## 14. Dependencies and approval boundary

- CAB-T01 began after durable human approval. CS-T01–T04 remain `VERIFIED`,
  uncommitted, and awaiting independent re-review. Their completion gates have
  not been bypassed by the new approval.
- CS-T05 through CS-T08 already own reusable CAD assets, admission, and dynamic
  component integration. This plan must consume those outcomes rather than
  duplicate or bypass them.
- M10-T05 remains blocked, and native KiCad is currently unreliable in this
  environment. Real board-edit acceptance cannot proceed without current native
  checks.
- Manufacturer/upstream model redistribution requires explicit license and
  provenance review.
- The approval authorizes implementation under these gates. Deployment and paid
  infrastructure remain outside scope.

CAB-T01 is the first implementation task. Story discovery and the disposable
sandbox follow its contracts. Independent final review is CAB-T10's gate.
Real drag-to-add remains gated until
the catalog admission and dynamic project paths are complete.
