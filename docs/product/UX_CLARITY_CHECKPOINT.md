# UI/UX implementation checkpoint

Scope: **UX-CLARITY-1 / UX-T01**. Human approval is preserved in
`.ai/approvals/UX-CLARITY-1.yaml`, along with the prior atlas checkpoint.
Read [the audit](UX_CLARITY_AUDIT.md) for all fourteen findings and their reasoning.

## What changed

- A dedicated landing page explains the purpose, intended user and supported projects.
  Its primary action opens the existing real project editor.
- Home/workbench navigation preserves the mounted editor; Back/Forward switch surfaces.
  The site tells users that unsaved fields are lost on reload and saved revisions are local.
- Three named catalog-backed specimens replace the dense art board on the landing page.
  The models are existing artistic library assets, not newly verified CAD. Switching,
  optional orbit, rotation/pause and text/device/network fallbacks are implemented.
- Reading text and controls default to 18px, introductory copy to about 22px, using
  relative units. Legacy secondary text rules across workbench, stories and art explorer
  were raised. Spatial schematic/canvas labels still use their existing drawing scale.
- The project starter comes first in the workbench. Saved example and experimental
  art are optional disclosures; the saved preview initializes when opened.
- Stories explain what parts do before showing catalog internals. Exact IDs and source
  descriptions remain accessible. The unavailable insertion button is removed, while
  temporary layout practice remains available and explicitly separate from saved boards.
- Story selectors have 44px targets and wrap. Dialog text has one scroll owner. Mobile
  and enlarged-text overflow found during this pass was corrected without clipping it.

## Finding disposition

“Implemented” describes the code change, not proof that it solves every user's problem.

| Findings | Disposition | Remaining work |
|---|---|---|
| U01 readability | Implemented relative reading scale | Screen-reader/OS text preference checks; CAD label zoom UX |
| U02 clutter | Implemented home/workbench separation and disclosures | Simplify deeper project options after user testing |
| U03 purpose, U04 landing | Implemented | Ten-second comprehension study with five newcomers |
| U05 3D | Implemented named specimens and motion controls | Higher-fidelity licensed CAD, real-device performance measurements |
| U06 credibility | Presentation corrected; engineering remains open | CS/CAB accuracy/admission gates; unidentified art remains unknown |
| A01 navigation | Implemented home/workbench Back/Forward | Deep project/run URLs and refresh recovery |
| A02 scrolling, A03 targets | Implemented | Independent assistive-technology and physical touch checks |
| A04 dead actions, A05 jargon | Implemented in stories | Guided project-form explanation improvements |
| A06 graphics overhead | Rendering reduced/lazy | Modules still imported; bundle and low-end GPU profiling |
| A07 persistence | Clear copy and preserved in-memory navigation | Unsaved reload warning/recovery needs a bounded follow-up |
| A08 recovery | Home retry/device/missing-model fallback implemented | Broader offline and saved-example retry UX |

## Verification

Final command results and implementation commit are recorded in
`.ai/verification/UX-T01.yaml`. Raw local logs are in `build/ux-*.txt` (ignored,
not a portable handoff artifact). Do not treat the initial failed harness run as a pass.

| Gate | Final result |
|---|---|
| `python scripts/verify.py fast` | 1,800 passed; 49 deselected; 268.63s |
| `node --test --test-reporter=spec apps/web/tests/*.test.mjs` | 205 passed; 0 failed/skipped; 6.782s |
| `python scripts/verify.py workflow` | 11 passed; 0.40s (rerun after ledger closure separately recorded) |
| `python -m ruff check .` | All checks passed |
| `git diff --check` | Passed; existing CRLF conversion warnings only |

An initial Node run failed 27 workbench tests because its fake document manufactured
a non-DOM `#home` node. The fixture now explicitly omits home and the new dedicated
landing harness exercises its own behavior. Final tests include nine new home tests,
including valid/restricted/missing models, retry, late responses, motion and rendering
failure. Test responses are scripted; no live model evaluation was used.

Browser observations:

- Default desktop and 320px viewport: landing and project editor fit horizontally.
- A named unsaved project input survived Home/Workbench and Back/Forward navigation.
- Processor/USB model selection changed the bound part and visible explanation;
  rotation/pause updated its state; keyboard interaction focused the model canvas.
- At 320px, all twelve story targets measured 44×44px; the dialog fit without a second
  horizontal reading scroll region; story text uses normal dialog scrolling.
- The saved example had no renderer before opening its disclosure and a Three renderer
  afterwards. Main landing text, secondary copy, model note and primary action measured
  contrast ratios of 14.47, 6.55, 6.14 and 5.74 respectively against their backgrounds;
  this is a focused measurement, not a whole-site contrast certification.
- A separate preview copied the final assets and doubled the root font from 18px to
  36px. This exposed and verified fixes to headline, circuit-strip and summary wrapping.
  At 320px with doubled text, home and project editor document width was 305px (the
  remaining 15px is the scrollbar). The component dialog fit at desktop and 320px.
- This is a controlled text-size stress test, not proof of all browser zoom settings.
  The in-app browser did not change zoom in response to its browser shortcut.

No live provider, deployment, paid infrastructure or engineering generation job ran.
No new KiCad/electrical/CAD correctness result is claimed for this presentation change.
The pre-existing CS working tree and CAB-T05 prerequisite holds remain intact.

## Changed files owned by this slice

Product/UI:
`apps/web/index.html`, `home.js`, `home.css`, `styles.css`, `component-stories.js`,
`component-stories.css`, `visual-explorer.css`, `app.js`, `project-workbench.js`;
`scripts/demo_server.py` only adds immutable static assets/content type.

Tests: `apps/web/tests/home.test.mjs`, `apps/web/tests/view-model.test.mjs`.
The latter marks the landing absent in its workbench-only fake DOM; all existing
workbench assertions remain. The new landing harness tests its own failure/lifecycle
paths. `tests/test_ai_workflow.py` adds approval assertions while retaining prior ones.

Documentation: this checkpoint, `UX_CLARITY_AUDIT.md`, product `README.md`.
Workflow: UX approval/verification plus updates to `.ai/state.yaml`, `tasks.yaml`,
`reviews.yaml`, `checkpoint.yaml`. These four ledger files and the workflow test already
contained unrelated CS/CAB changes; preserve their mixed working-tree ownership.

## Exact takeover procedure

1. Inspect Git status. Read AGENTS, AI_WORKFLOW, this checkpoint, the audit and UX
   verification record. Run `ai_state.py validate` before selecting any next task.
2. Treat product code in the UX implementation commit as the reviewed self-contained
   unit; do not wholesale stage the existing CS/ledger changes.
3. For preview: use `DemoHTTPServer` on localhost with `JobStore` and no provider. Static
   assets are snapshotted at startup; restart the server after edits. Current normal
   preview is `http://127.0.0.1:8766/`. The temporary 8767 text-stress server is test-only.
4. Run Node tests and the Python fast gate. Never run canonical `fast` and `workflow`
   together: both use `build/pytest`. The server tests can use a separate basetemp.
5. Next recommended UX work: independently evaluate comprehension, assistive technology,
   device performance and deep project navigation before expanding the visual experience.
6. Do not unblock CS-T05 or CAB-T05, activate imported components, or infer hardware
   validation from this UI pass. Follow their original prerequisite review/commit gates.

## Self-review limits

This pass has code tests and local browser evidence, not an independent UX/accessibility
review, external usability study, fabricated-board validation, measured low-end device
benchmark or a claim of WCAG conformance. Those gaps are deliberately still visible.
