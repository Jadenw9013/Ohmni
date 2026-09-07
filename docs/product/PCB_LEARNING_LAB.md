# Interactive PCB learning lab

## Scope and authorization

On 2026-09-06 the user requested GPT-6 ultra for PCB 3D visuals that are
“super cool and super functional” and make users “more engaged with the learning
aspect.” This authorizes the richer display and learning interactions described
here, within the existing local prototype. The renderer and a focused learning
review were delegated to `gpt-6-astra` with `ultra` reasoning.

The subsequent request, “can you make the pcb way more realistic and give it
some animations?”, authorizes the second display pass: solder-mask finishes,
beveled bodies, metallic solder and connector details, and user-controlled
assembly and camera animations.

The M9 electrical projection remains authoritative. This work introduces an
explicitly labelled **illustrative display layer** for component bodies and
heights; it does not claim manufacturer CAD accuracy or update any engineering
measurement, connectivity, evidence, or verdict.

## User experience

- The opening page shows the saved PCB as a lit 3D object. **Open the 3D circuit
  lab** starts an immediate, full-size learning experience without a job wait.
- Four discovery stops come from the saved design's own system records. Each
  explains a system, highlights its actual members, and invites the user to
  select a highlighted part. The equivalent text buttons work without spatial
  precision or prior component knowledge.
- Selecting a component exposes its recorded identity and connected nets. A net
  button highlights exactly that net's copper. Pulses are labelled as a visual
  guide, not electrical simulation, propagation timing, or current direction.
- Orbit, X-ray, labels, top view, reset, and system separation help explain the
  same artifact from different perspectives. Motion respects reduced-motion
  preferences. Closing the lab stops its motion.
- **Watch assembly** replays a bounded, interruptible transition from the
  existing separated-system display to the exact assembled board. The scrubber
  stays synchronized. This is a visual explanation, not an assembly procedure.
- Tour stops move the camera to the system's actual members. **Inspect this
  part** moves closer to a selected component; **Fit whole board** recovers the
  overview. Front/back/top presets move smoothly and snap under reduced motion.
- The completed board workspace gets the same display controls and discovery
  panel, while retaining its engineering checks, evidence, schematic, and exports.
- A persistent saved-reference marker and expandable visualization limits
  distinguish earlier geometry from current output and illustration from
  engineering measurements.

## Code boundaries

`board-model.js` remains the pure, authoritative scene adapter. The renderer
consumes its footprints, tracks, pads, vias, and explicit memberships. Display
meshes and lighting are separate from the engineering model.

`learning-model.js` checks source consistency and produces lesson cards from
system descriptions, component names, and explicit member lists. It checks both
artifact and routing fingerprints for a saved reference. A discovery match is
set membership, not an electrical verdict. Component-purpose prose is not
promoted into a system lesson.

`circuit-lessons.js` owns lesson navigation, local discovery progress, selection,
and net buttons. `circuit-lab.js` owns the accessible native dialog and its lazy
viewer. `board-controls.js` owns presentation controls. New modules remain local
allowlisted assets covered by the server's UI fingerprint.

## Verification record

Learning-model boundary tests cover artifact/routing lineage, invalid or
duplicate references, inconsistent systems and anchors, nonexistent flow nets,
non-reference fixtures, source immutability, and the shipped preview. Renderer,
integration, and browser verification are recorded below.

The first integrated 3D run, `52b1e9bb2502`, completed through the browser on
2026-09-06. The generated board and schematic downloads were exposed with a
9-file manufacturing inventory. KiCad reported zero DRC violations and zero
unconnected items. The saved-reference lab and the completed current board
both initialized the WebGL renderer and their discovery controls.

Final verification after the realism and readability passes:

- **87 frontend tests passed**, including exact assembled-scene recovery,
  interruption, reduced motion, camera settling, backward keyboard selection,
  Escape-to-close behavior, and avoiding animation work when copper is hidden.
- **495 pytest tests passed, 10 deselected**, with an isolated
  `build/pytest-pcb-realism-0906` temporary directory and no shared cache.
- The final markup passed all **9 targeted UI tests**. Ruff passed for the
  changed Python server and UI tests; `git diff --check` passed.
- The display mesh has **42,528 vertices**, with three GPU draw batches per
  normal frame. Camera motion reuses buffers. Only the bounded assembly reveal
  rebuilds meshes, at most 30 times per second. This is a mesh budget, not a
  measured frame-rate guarantee across devices.
- Browser checks confirmed native WebGL and distinct teal mask/silver materials,
  assembly completion and scrubber synchronization, direct 3D picking, correct
  and wrong-system discovery feedback, net highlighting and X-ray, and the
  Escape sequence: clear selection, then close the modal and restore launch focus.
  Reopening reused one overlay. Desktop 1440×1000 and 1280×720 and phone
  390×844 layouts were inspected; the phone landing and lab had no horizontal
  overflow, and desktop lab controls remained reachable.
- Final browser job **`c21dca04e8fb`** completed using the final asset snapshot
  `34dca3de670707c75dd25cade4acbac9577bd730b63d48630d6df8b0ba9748d5`.
  It retained 19 components, 296 copper segments, 9 manufacturing files, and
  zero KiCad DRC violations/unconnected items. Its 21 schematic warnings,
  unsupported checks, synthetic economics, and untested-hardware status remained
  visible. Generated-board tests covered front/top synchronization, restoring
  copper from a lesson net, manual-flow exit from a lesson, reset, and actual
  schematic/PCB export links.

Before publishing to `main`, the exact staged files were exported with
`git checkout-index` into an isolated directory, without the concurrent
synthesis/workflow changes. That publication snapshot passed **484 Python
tests, 10 deselected**, and **87 frontend tests**. The earlier 495-test result
above describes the shared working directory. Staged whitespace checks passed.

## Limits

This does not provide STEP models, real component heights, a layer stack-up,
electrical simulation, firmware, live supplier data, or bench measurements. A
decorative material or moving highlight cannot turn an unknown into a pass.
