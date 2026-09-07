# Ohmni workbench redesign

## Authorization and scope

Approved by: human, in the current Codex conversation on 2026-09-05.

Approval evidence: “can we first start by you completely redesigning and
restructuring the frontend and UI by scratch?” followed by “go”.

This authorizes rebuilding the existing local prototype's presentation and
navigation. It does not approve future synthesis, deployment, or engineering
milestones. Concurrent M10 work and its `.ai` records are separate.

## Experience

The visual direction is a bright electronics studio: cobalt, copper accents,
large display typography, a persistent workbench sidebar, and a real circuit
board as the opening illustration. No external fonts, image service, frontend
framework, or build step is required.

The five workspaces are:

1. **Start a project.** Explain the product, scope, example, and expected output.
   Explore a saved board by system before starting the actual run.
2. **Project brief.** Distinguish the example's requirements, design choices,
   and assumptions. Explain that editing the example is not implemented.
3. **Design activity.** Show actual backend progress, a current step, useful
   explanations during routing, and actionable failure/reconnection states.
4. **Explore the board.** Separate the board, learning, and evidence into tabs.
   Expand component groups, select parts, follow connections, replay the repair,
   and explore the schematic-to-board transformation.
5. **Build & export.** Provide the actual KiCad downloads, manufacturing file
   inventory, component purposes, assembly guidance, and derived bench checks.

Only available workspaces can be opened. Navigation displays one stage at a
time and moves focus to its heading. Result tabs support arrow keys, Home, and
End. Board controls work by keyboard; components also have a text-based route.
Layouts cover desktop, compact sidebar, and phone breakpoints. Reduced-motion
preferences are respected.

The saved preview carries explicit source fingerprints and a reference label.
It is never treated as a fresh run or used to invent a verdict. Completed
results remain readable during connection loss, with downloads disabled until
the same server returns. A new server cannot make old files current.

## Frontend structure

- `apps/web/index.html`: semantic workspaces, navigation, and static onboarding.
- `apps/web/styles.css`: design tokens, components, states, and responsive layout.
- `apps/web/app.js`: journey state, projections, controls, and recovery.
- `apps/web/client-contract.js`: strict API shape and server identity checks.
- `apps/web/reference-preview.js`: isolated onboarding preview controller.
- `apps/web/reference-board.json`: previously generated geometry and descriptions.
- Existing `board-model.js`, `board-view.js`, `schematic-view.js`, and
  `view-model.js` retain their engineering-data and rendering boundaries.
- The demo server explicitly serves and fingerprints the new static assets.

## Verification

- Fast pytest selection: **495 passed, 10 deselected**, using an isolated
  `build/pytest-ui-redesign-0905` temporary directory and no shared cache.
  The canonical wrapper first encountered a Windows permission error while
  cleaning its shared `build/pytest` folder; no application assertion failed.
- Frontend Node suite: **43 passed**, including navigation gating, exclusive
  panels, unchanged engineering statuses, and connection/download behavior.
- Targeted frontend Python checks: **9 passed** after final interaction fixes.
- Ruff passed for the changed Python server and UI tests. The browser smoke
  script passed Node's syntax check and was updated for the new workspaces.
- Actual browser verification uses the local demo server and real KiCad
  pipeline. Completed job `3847fed2d005` produced 19 placed components, 296
  copper segments, 9 fabrication files, and zero KiCad DRC problems or missing
  connections. Its 21 schematic warnings remained visible.
- Browser checks covered brief submission, completion, expandable systems,
  part selection, front/back/copper/reset controls, connection tracing, repair
  replay, schematic-to-board animation, keyboard tab navigation, keyboard
  schematic selection, a board download, help, and disconnected/changed-server
  states. Desktop (1440), compact sidebar (920), and phone (390) layouts were
  inspected. Phone review, learning, checks, and export panels had no document
  horizontal overflow; every transformed part remained inside its stage.
- Secondary text tokens meet at least 4.65:1 contrast on the main light surfaces.
  This is a targeted contrast check, not a complete accessibility certification.

## Readability and first-impression pass — 2026-09-06

The user supplied a screenshot and requested a more attractive main page,
explicitly noting that “the words are too small to read” and that the page
should grasp attention immediately. This authorizes the subsequent layout and
typography revision within the same local frontend scope.

The opening page now leads with “Build a real circuit. Understand every part.”
and a dominant board preview. Its lab entry sits above the canvas, so a visitor
can immediately explore without running the engineering pipeline. A separate,
roomier project starter explains the fresh design run. A short three-step path
replaces the generic feature grid, and prototype scope stays visible beside the
starter.

Body text is 17px, introductory copy 18px, and secondary UI text generally 14px
or larger. The lab lessons use 17px descriptions. Navigation, controls, contrast,
phone wrapping, and the available canvas area were adjusted together. The teal
PCB is separated from a neutral navy studio background.

The final markup passed all 9 UI structure tests. The integrated implementation
passed 87 frontend tests and 495 pytest tests (10 deselected). Browser inspection
covered the landing and lab at desktop/phone sizes and a complete generated
design. The detailed results are recorded in [PCB_LEARNING_LAB.md](PCB_LEARNING_LAB.md).

The exact staged publication snapshot was then tested independently of the
concurrent synthesis/workflow changes: **484 Python tests passed, 10 deselected**,
and **87 frontend tests passed**. The earlier 495-test result is from the shared
working directory, not the isolated publication snapshot.

## Remaining product boundaries

The prototype still runs one pre-authored ESP32/BME280 reference project.
Custom requirements, editable designs, firmware generation, a complete
manufacturing-package download, live supplier prices, and bench verification
are not supplied by this redesign. The interface makes these limits visible
where they affect the user's next action.
