# Ohmni visualization architecture

**Status:** implemented in Milestone 9 for the supported deterministic project.
**Owns:** how authoritative engineering state reaches the screen, what the
renderer is allowed to draw, and the migration path to richer 3D.

**2026-09-06 display evolution:** the user has authorized richer 3D and interactive
learning. See [PCB_LEARNING_LAB.md](PCB_LEARNING_LAB.md) for the new renderer and
explicitly labelled illustrative component bodies/heights. The M9 choices below
record the original implementation; the engineering projection and membership
boundaries remain unchanged.

The governing rule, and the reason this document exists:

> **The frontend visualizes state. It never derives engineering truth.**

Not a single PASS, FAIL, voltage, current, coordinate, or net membership is
computed in the browser. If a pixel is on the screen, a typed Python report put
it there.

---

## 1. The pipeline

```
  verified subsystem reports          (verifier, eda, routing, manufacturing, bom)
        │
        │  ohmni.application.systems     derive functional grouping + flows
        │  ohmni.application.product     project geometry, brief, checks, tour
        ▼
  ProductExperience   (Pydantic, one JSON document)
        │
        │  HTTP: GET /api/jobs/<id> → report.experience
        ▼
  apps/web
    board-model.js    pure transforms: no engineering decisions
    board-view.js     3D projection + raster
    schematic-view.js 2D schematic
    app.js            journey state, rendering, disclosure
```

`ohmni.application` was already the truthful projection boundary
(`ARCHITECTURE.md`, "End-user application boundary"). M9 keeps that boundary and
adds a second projection beside `demo.py`: `product.py` answers "what does a
person read?" where `demo.py` answers "what did the pipeline do?".

## 2. What the geometry is derived from

Every visual element traces to a compiled artifact. Nothing is invented, and
`_board_geometry` raises rather than render if the lineage does not match.

| On screen | Source | Type |
|---|---|---|
| Board outline | `BoardConstraints.outline` | `width_mm`, `height_mm` |
| Component position | `ComponentPlacement` | `x_mm`, `y_mm`, `rotation_deg`, `side` |
| Component body size | `FootprintDefinition` | `width_mm`, `height_mm` |
| Pads | `FootprintDefinition.pads` | per-pad `x/y/width/height/kind/shape` |
| Pad net | `PcbCompilationReport.pad_bindings` | `net_name` per pad |
| Copper tracks | `PcbCompilationReport.emitted_tracks` | exact emitted segment endpoints, layer, width |
| Vias | `PcbCompilationReport.emitted_vias` | position, diameter, drill, layer pair |
| Nets | `CircuitIR.nets` | names, kinds, pin membership |
| Schematic symbols | `CompilationReport.symbol_bindings` | position, size, per-pin position and net |
| Statuses | typed reports | copied verbatim, never recomputed |

Three integrity checks run before any geometry is emitted, so a stale or
mismatched artifact fails loudly instead of rendering a plausible lie:

- the compiled artifact fingerprint must equal the artifact's own fingerprint;
- the constraints hash must equal the board's;
- the routing-plan fingerprint must match, and the emitted track and via counts
  must equal the compiled copper statistics.

### The one thing that is not derived

**Board thickness.** Ohmni does not model stack-up anywhere. The 3D view
extrudes the board by a constant, and the projection marks it:

```python
DISPLAY_BOARD_THICKNESS_MM = 1.6
thickness_is_display_only: bool = True
```

The interface says so where it shows the board edge. Component *height* is
likewise not modelled; parts are drawn as flat bodies at their true footprint
outline rather than extruded to a guessed height. Drawing an ESP32 module 3 mm
tall because that "looks right" would be exactly the class of invention this
product exists to avoid.

## 3. Why the renderer has no dependencies

The brief preferred Three.js or React Three Fiber. The investigation found
against both, for reasons specific to this repository:

| Constraint | Consequence |
|---|---|
| `apps/web` has **no build step and no npm dependencies** — `package.json` contains only a test script | R3F requires React and a bundler. Adding both is a larger change than the visualization itself. |
| `demo_server.py` serves an **immutable snapshot of an allowlisted asset set**, hashed to a `ui_version` that binds client and server generation | A vendored 600 KB library becomes part of that snapshot and its integrity story. |
| The frontend is covered by `node --test` on pure ES modules | A WebGL renderer cannot be unit-tested in that harness; a pure projection can. |
| The board is a **planar object**: an extruded rectangle with flat parts, flat copper and cylindrical vias | It needs perspective, depth ordering and hit-testing, none of which require a GPU. |

**Decision: a dependency-free renderer.** `board-view.js` implements a small
camera (yaw, pitch, zoom, pan), projects millimetre coordinates through a
perspective matrix, sorts faces back-to-front, and rasterizes to a 2D canvas.
About 400 lines, no dependencies, deterministic, and the projection math is unit
tested.

**What this buys:** rotate, zoom, pan, flip to the back, per-component hit
testing, layer visibility, net and system highlighting, and an exploded view —
the full interaction list — at zero dependency cost.

**What it gives up:** real lighting, shadows, materials, anti-aliased curves,
and any path to STEP models without replacing the rasterizer.

### Migration path to WebGL

The renderer is split so the trade is reversible:

```
  board-model.js   → scene graph: typed meshes in board millimetre space
                     (pure, tested, renderer-agnostic)
  board-view.js    → camera + rasterizer + hit testing
                     (the only file that touches a canvas)
```

`buildScene(board, options)` returns plain geometry — quads, discs, line
segments — each tagged with `ref`, `net`, `layer`, and `system`. Swapping in
Three.js means writing a second consumer of the same scene graph and vendoring
the library into `STATIC_ASSETS`. Nothing in the projection, the interaction
model, or the tests changes. Richer component models arrive as a per-package
mesh table keyed by `footprint_id`, alongside the pad geometry already keyed the
same way.

### Depth ordering

A planar board breaks a naive painter's algorithm: the substrate is one large
polygon whose mean depth is the board's centre, so a component near the far edge
sorts *behind* it and vanishes. Primitives therefore carry a **band** — far
face, substrate, near face, decided by the sign of `z` against the camera pitch
— and are sorted by `(band, depth)`. Flipping to the back swaps which side is
occluded. `bandOf` is unit tested against exactly that failure.

### Framing

Perspective foreshortening means a tilted board's projected extent is not
predictable from its millimetre bounds. `frame()` runs two passes: set a
plausible focal length, then measure what the corners actually project to and
correct zoom and pan from the measurement.

## 4. Event-driven visualization

Animations are not hand-scripted against the golden fixture. They are driven by
the structured records the projection emits, so the same code animates any
future project.

| Record | Drives |
|---|---|
| `stages[]` — eight terminal stage cards | the Design stage timeline |
| `repair.steps[]` — keyed sequence with `component_refs` and `net_names` | the repair replay: each step highlights exactly the parts and nets it names |
| `flows[].stages[]` — ordered, each naming real nets and pins | "Show me how this works": each step highlights **only its own** refs and nets. The union of a whole flow is often most of the board, which lights everything and therefore explains nothing. |
| `systems[]` + `grouping[]` | "Explode my board": components translate away from the board centroid, grouped by system |
| `tour.steps[]` — ordered, each with `focus`, refs and nets | the guided walkthrough |

A visual highlight is always a **set membership test** against refs or net names
the backend supplied. The frontend never decides that a component is part of the
power system, that a track belongs to a net, or that a repair touched a pin.

### Terminal state

Acceptance criterion 9 — a finished project must never look like it is still
running — is handled structurally rather than by styling. `stages[]` is
projected only for a **completed** run, and every card carries a settled
outcome (`DONE`, `FOUND_PROBLEM`, `FIXED`, `PASS_WITH_WARNINGS`, …). There is no
`RUNNING` value in the completed projection to render, so a historical progress
event cannot leak into the result view. Live progress events remain a separate
channel used only while a job is actually in flight.

## 5. Functional grouping and flows

`ohmni/application/systems.py`. Grouping is a presentation, so it is derived,
documented, and carries its own justification.

**Anchors** come from part category, with one topological exception: a connector
is a power anchor only when a net it sits on declares an `ExternalSource` — a
fact the circuit states rather than a guess from the part's name.

**Everything else attaches** to the anchor it shares its most *local* net with.
A net with ≤ 4 pins wires a component to something specific; a 14-pin supply
rail does not. Where only a shared rail is available, the passive attaches to
the physically **nearest** anchor — which is the same distance the layout rule
`PB-PCB-004` already measures, and the reason decoupling works at all.

Every grouping carries a `basis` string that the interface shows on request:

```
R4  sense    wired to U3 on SDA, a 3-pin net
C2  power    on shared net 3V3; placed 4.0 mm from U2, the nearest part it can serve
```

**Flows** are read straight off the netlist and are emitted only when the
topology they describe exists. The I2C flow is derived from the **peripheral**
side — a sensor's SDA pin is SDA in silicon, whereas an MCU GPIO is only I2C
because firmware says so — matching the verifier's own reasoning in
`PB-I2C-001..003`. Each flow names real nets, real pins, and real refs, so
highlighting is exact.

## 6. Guided tour and the LLM contract

M9 ships a **deterministic** tour. `GuidedTour.narration_source` is literally
`deterministic_projection_not_a_language_model`, and the interface says the
walkthrough is generated from the project's own data. Nothing pretends to be
live AI.

The contract is shaped for the model that will eventually write the narration:

```python
class TourStep:
    step_id: str
    title: str
    narration: str          # today: written by the projection
    focus: str              # board | flow | repair | systems | confidence
    component_refs: list[str]
    net_names: list[str]
    facts: list[str]        # the authoritative input a model would receive
```

When narration becomes generated, a provider replaces `narration` **only**.
`facts`, `component_refs`, and `net_names` continue to come from the projection,
so the model can phrase the tour but cannot change what the board is, invent a
component, or claim a verification result. That is the same boundary
`AGENTS.md` already states: the model proposes, deterministic systems verify.

## 7. Frontend module boundaries

| Module | May do | Must never do |
|---|---|---|
| `view-model.js` | format statuses, money, readiness labels | decide a status |
| `board-model.js` | build a scene graph from projected geometry; pure | read the DOM, compute nets, infer membership |
| `board-view.js` | camera, projection, raster, hit testing | change geometry, fabricate a coordinate |
| `schematic-view.js` | lay out projected symbol geometry | infer connectivity |
| `app.js` | journey state, rendering, disclosure, highlighting | compute any engineering value |

`tests/test_architecture.py` enforces the Python side of this boundary. The
frontend side is enforced by tests over the pure modules plus review.

## 8. What is deliberately not built

- **Photorealistic or STEP-based component models.** The data does not exist.
- **Component height.** Not modelled; not guessed.
- **Copper pour / ground plane rendering.** The compiler emits no zones.
- **Silkscreen artwork.** Only reference designators are emitted.
- **Animated morph from schematic symbol to footprint.** The transition
  communicates the concept with a cross-fade and a position tween between two
  *real* layouts. A literal morph would imply a geometric relationship that
  does not exist.
- **Live LLM narration.** Deferred, with the contract above already in place.
