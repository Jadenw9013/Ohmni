# Unified Ohmni studio design

Date: 2026-10-02. Task **UX-T03**, within human-approved `UX-CLARITY-1`.
Approval: `.ai/approvals/UX-WORKBENCH-1.yaml`. Implementation: `19ce9bf`.
Predecessor: [reference-led landing](UX_REFERENCE_LANDING_CHECKPOINT.md), UX-T02,
implementation commit `4bf53ef`.

## What changed

The human requested that the remaining pages match the dark landing and supplied
a project-brief reference. The implementation carries the near-black/navy surfaces,
cyan/violet accents, readable pale text, outlined controls and selected-card glow
through the existing experience. It does not adopt the reference's invented user
profile, notifications or unconditional “Ready to generate” badge.

| Surface | Treatment |
|---|---|
| Start and saved projects | Shared logo, dark sidebar, clear current step, consistent project cards and primary action |
| Project brief | Board illustration beside the heading, three selectable family cards, outlined form, separate confirmation and build-limit cards |
| Activity and failures | Same surfaces and typography; progress and errors still come from the actual job |
| Board, explanation and evidence tabs | Dark panels, clear selected tabs, readable semantic outcome colors |
| Build and export | Consistent cards, warning treatment and disabled download controls |
| Component stories and practice layout | Dark dialogs, inputs and previews; temporary-scene boundaries retained |
| Circuit lab | Matching logo and navy 3D backdrop; header and lesson panes reflow for enlarged text |
| Experimental atlas | Shared surface, text, input and warning tokens; model geometry unchanged |

Reading text stays 18px by default. The project-brief reference's smaller labels
were not copied. Mobile family cards and form columns wrap according to available
space. Decorative artwork is hidden in the narrow brief to prioritize the form.
The duplicated visible “Your board features” introduction is now screen-reader-only;
the section still has an accessible heading. Actual unsaved/saved status remains visible.

The evidence panel's decorative, always-green tick was replaced with a neutral
information mark. Outcome badges still show their actual values. The palette change
does not modify evidence, verification, geometry, routing or release decisions.

## Ownership and maintenance

- `apps/web/styles.css`: shared semantic palette and migrated light surfaces/text.
- `apps/web/workbench-theme.css`: reference-led composition, cards, controls and reflow.
- `apps/web/component-stories.css`, `visual-explorer.css`: learning surfaces use the shared tokens.
- `apps/web/index.html`: theme loading, shared branding and illustrative brief masthead.
- `apps/web/project-workbench.js`: presentation wrappers only; save/run behavior unchanged.
- `apps/web/visual-renderer.js`: navy scene background only; lighting, models and ownership unchanged.
- `apps/web/visual-version.js`: refreshed source identity after the renderer change.
- `scripts/demo_server.py`: adds the stylesheet to the immutable asset snapshot.
- `apps/web/tests/theme.test.mjs`: checks actual palette values for normal-text contrast,
  including links and pass/warn/fail surfaces. It is not a full accessibility audit.

Use shared tokens for new UI. Keep status colors distinct from the cyan/violet brand
gradient, preserve visible status text, and never style an unavailable action as ready.
Run `scripts/prepare_visual_assets.py` after changing hashed visual source files;
the Node suite deliberately failed until this manifest was refreshed.

The brief reuses the landing's generated PNG with a visible concept-illustration
caption. No additional image generation or engineering model call was made in UX-T03.
UX-T02 made one image-generation call, documented in its checkpoint. The picture
does not identify the current circuit's components or establish CAD correctness.

## Verification

Exact counts, source hashes, implementation commit and commands are recorded in
`.ai/verification/UX-T03.yaml`. Counts describe the working tree with preserved
uncommitted CS and workflow changes, not a clean isolated checkout.

- Fast suite: **1800 passed, 49 deselected, 260.47s**. This ran before the final
  CSS lab-reflow, decorative SVG and scene-background refinements; final Node,
  focused UI/server tests and browser inspection cover those presentation changes.
- Node: **203 passed, 0 failed, 0 skipped, 6.549s**, including the palette guard.
- Workflow: **11 passed, 0.44s** before ledger closure; closure is recorded separately.
- Ruff and `git diff --check`: passed.
- Focused UI/static-server/library: **49 passed, 1 cache-write permission warning, 16.27s**.
- Workflow after ledger closure: **11 passed, 0.08s**; `ai_state.py validate` passed;
  `ai_state.py next` reported no executable task.

Browser observations:

1. Inspected project brief at 1488px; no horizontal page overflow. Unsaved generation
   was disabled. Saving revision 1 enabled it; changing width to 101mm disabled it again.
   The saved test project lives only in `build/ux-reference-preview`.
2. Inspected start, component library, activity/failure and the saved circuit lab.
   Inspected result, evidence, explanation and export screens with the labeled UI fixture.
3. Mobile result/explanation/export: 320px viewport, document client/scroll both305px.
4. Doubled root text, 18 to 36px: project form at320px remained305px wide; at1280px
   remained1265px wide. Library and practice dialogs each had303px client/scroll width
   at320px. Story selectors remained44x44px.
5. Enlarged circuit-lab inspection exposed an unreadably narrow lesson column and
   overflowing logo. Fixed with font-relative flex wrapping, an auto-height header,
   normal-flow board metadata and a separate canvas height. At1280px, the dialog's
   client/scroll widths were1238px and the lesson pane stacked at1223px wide.
6. Final normal-size circuit lab used the current logo, navy renderer backdrop and
   shared controls; dialog client/scroll widths both1393px. No console errors observed.

## Real run versus visual fixture

The real provider-free reference run on8766 failed with **`pipeline_failed`** after
writing `build/ux-reference-preview/19455a1ef861/golden.kicad_sch`. No completed
engineering result was available. The exact backend cause was not diagnosed in
this presentation task. This is a failure, never a successful KiCad or release check.

Result/export visual inspection used a separate loopback server on8767, with a
conspicuous **UI TEST FIXTURE — simulated report, not engineering evidence** banner.
Its data was extracted from the existing `view-model.test.mjs` fixture. Release
currency was deliberately false: all three download links stayed disabled with no
href. This fixture does not demonstrate a working engineering run.

The enlarged-text preview on8768 used a copied asset tree with root font225%.
That checks text reflow, not native browser zoom. Temporary tabs and servers were
closed afterwards. The normal8766 preview uses the real application and its own
temporary local data; no fixture pipeline was installed in product code.

Artifacts retained under ignored `build/`: `ux-workbench-*.txt` verification logs,
`ux-workbench-fixture-report.json`, `ux-workbench-fixture-server.py`, fixture asset
copies and temporary SQLite state. The main generated illustration is committed
at `apps/web/landing-board.png`.

## Takeover and limits

Read AGENTS, `docs/AI_WORKFLOW.md`, the ledger and these UX checkpoints first.
Run `ai_state.py validate` before continuing. Restart the preview after source
changes: the server snapshots all assets on startup. Canonical fast/workflow tests
share a temporary directory and must run sequentially.

UX-T02 and UX-T03 are presentation task units with self-review. Scope-level
independent accessibility and newcomer evaluation remain outstanding. No screen
reader, physical touch device or low-end GPU certification is claimed. The complete
experimental atlas was not manually retested at every viewport. The live engineering
failure above needs a separate diagnostic follow-up before claiming end-to-end success.

Existing CS/CAB gates, including the CS-T04 COMPLETE prerequisite, remain unchanged.
No imported component activation, real PCB insertion, IPC/SPICE claim, deployment
or infrastructure provisioning occurred. Preserve unrelated uncommitted work.
