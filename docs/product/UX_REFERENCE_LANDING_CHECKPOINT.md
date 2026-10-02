# Reference-led landing rebuild

Date: 2026-10-02. Task: **UX-T02** in human-approved `UX-CLARITY-1`.
Approval: `.ai/approvals/UX-REFERENCE-1.yaml`. This supersedes the light landing
described by UX-T01; its workbench readability fixes and engineering boundaries remain.

## Visual brief and implementation

The user supplied a specific dark PCB landing reference and explicitly requested a
rebuild to match it. The implemented composition uses:

- Near-black `#030810`, white `#f4f6fc`, cyan `#03e8de`, blue `#32b9ff`, violet
  `#a36aff` and muted readable text `#b4c0d3`.
- A compact three-part header, large left-aligned headline, cyan/violet final line,
  two primary hero actions, a dominant isometric board and three lower feature cards.
- Segoe UI/system typography, 18px reading text, secondary copy approximately 16–17px.
  The user's reference takes precedence over the earlier light/minimal visual direction.
- A one-second entrance for the board under `prefers-reduced-motion: no-preference`;
  hover motion is similarly gated. No automatic looping animation or landing WebGL scene.
- Live HTML text and real buttons rather than baking the screenshot into the page.

## Functional behavior

| Control | Actual destination |
|---|---|
| Build | Existing workbench, preserving its mounted state |
| Get started / Start building | Existing new-project editor |
| Explore demo / Interactive 3D design | Saved circuit disclosure, then existing 3D circuit lab |
| Learn / Guidance as you learn | Component story library |
| Sensor / Compute / Power callouts | Library filtered to BME280 / ESP32 / USB-C |
| Docs | Accessible modal with a short product guide |
| Real engineering checks | Explanation of evidence, outcomes and remaining testing |
| Know the limits | Scope, local storage and illustration limitations |

“Explore demo” replaces the reference's “Watch demo” because this is a real interactive
saved circuit, not a video. No simulated video or placeholder link was introduced.
The guide modal closes on Escape and returns focus to the launching control.

## Artwork provenance and limits

`apps/web/landing-board.png` is a **generated raster concept illustration**, not an
interactive CAD model, sourced component identity or proof of a working circuit.
The caption makes that distinction; the demo opens the existing circuit data separately.
The callouts are entry points into known catalog lessons, not image-based identification.

One built-in image-generation request used the user's screenshot as visual reference.
No engineering model/provider evaluation ran, and no paid infrastructure was provisioned.
The prompt requested the board only, without page text, callout boxes or logos, against
a near-black background. The generated original is retained at:

`C:/Users/wongj/.codex/generated_images/01a0a5f5-8594-7643-b36c-3a8fef354f1f/exec-ceabd0ba-004a-424a-9049-24713c4398a4.png`

The workspace asset is the exact copied PNG, 1536×1024, 1,923,602 bytes. It is served
from the immutable local static snapshot with `image/png`; its bytes participate in
the UI identity. A future responsive/compressed derivative should preserve provenance.
The image generation charge was not queried; no claim of a zero-cost call is made.

## Code ownership

- `index.html`: reference composition and functional entry points.
- `landing.css`: dark landing, callouts, mobile layout and reduced-motion treatment.
- `home.css`: retains the shared workbench readability fixes, removing obsolete light
  landing selectors.
- `home.js`: lightweight navigation and accessible explanatory guides. The old specimen
  renderer lifecycle is removed from home; interactive components remain in the library.
- `app.js`: shared lazy reference loader and demo opening; retry allowed after failed load.
- `component-stories.js`: optional initial search from an entry point's component query.
- `demo_server.py`: adds the local stylesheet and PNG to its immutable asset allowlist.
- Home tests now cover the current navigation/guide/artwork contract. Nine obsolete
  specimen-home tests were replaced by six relevant tests; the existing library/renderer
  tests still cover model binding and geometry authority separation.

## Verification and takeover

Exact final counts, hashes and commit are in `.ai/verification/UX-T02.yaml`.
The test counts include the preserved uncommitted component-synthesis working tree.

Observed in the browser:

- Reviewed composition at the reference's 1435×780 viewport.
- At 390px: document client/scroll width both 375px. At 320px: both 305px;
  the 15px difference is the browser scrollbar. No horizontal page overflow.
- At 320px, Docs dialog client/scroll width both 246px; Escape restored Docs focus.
- Sensor callout yielded `BME280`, then `1 of 1: Environment sensor`.
- Explore demo opened the real circuit-lab dialog with `#workspace` and saved-example open.
- Start building opened the project editor; Home/Build retained its unsaved name.
- Doubled root text exposed hero/callout overlap. Flexible wrapping fixed it:
  client/scroll widths both1265px at1280px and305px at320px. The test used copied
  assets with a36px root, not native browser zoom. Final mobile labels use full-width rows.
- No runtime console errors observed during the inspected flows.

Implementation commit: `4bf53ef`. Gates:202 Node tests;1800 fast tests,49 deselected
(259.51s);40 focused server/library tests (8.99s);11 workflow tests (0.39s);Ruff and
diff checks passed. Fast ran before final CSS-only refinements, which were covered
by subsequent browser/static-server checks. Focused pytest emitted one cache-write
permission warning. The subsequent matching workbench is documented in
[UX-T03](UX_WORKBENCH_THEME_CHECKPOINT.md).

Tests and screenshots do not constitute independent UX acceptance or physical-device
accessibility certification. The artwork is an aesthetic reference; no CAD, electrical,
IPC, SPICE or hardware-validation status changed. Existing CS/CAB holds remain intact.

To continue: read AGENTS, the ledger and this checkpoint. Run `ai_state.py validate`.
Keep the pre-existing CS changes and mixed ledger edits separate. Preview on localhost
with a provider-free `JobStore`; restart the server after changes because assets are
snapshotted at startup. Do not run canonical `fast` and `workflow` concurrently.
