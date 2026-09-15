# VIS-REF-001 implementation handoff

Implemented W0–W7 for both integrated viewers. **Engineering and browser checks
are complete; human visual acceptance is pending.** The optional W8 output is
[a proposal only](W8_PROPOSAL.md). M10-T05 remains parked, and no electrical
design, firmware, simulation, supplier or deployment scope was added.

## Open the result on Windows

From `C:\Dev\hackathon`:

```powershell
.\.venv\Scripts\python.exe scripts\demo_server.py --host 127.0.0.1 --port 8767 --output-root out\visual-reference-browser
```

The local server was left running on port 8767 for this handoff. Open
`http://127.0.0.1:8767/`:

- **Actual board:** choose **Open the 3D circuit lab**. It loads the unchanged
  saved 29-component “Sense & control” design. Newly generated supported boards
  use the same renderer in the application.
- **Educational scene:** choose **Explore sample board**, or load
  `http://127.0.0.1:8767/#sample-board`. **Asset library** opens all 18 sample
  families; each tile opens a close-up. X01–X08 are surface-detail specimens,
  never extra components.
- **Internal proof:** `http://127.0.0.1:8767/#visual-proof` retains the five-object
  proof. This was captured before completing the library, not substituted for
  either deliverable.

The supplied reference package and `.codex/` are intentional untracked inputs
and remain untouched. Output captures and diagnostics are local ignored `out/`
artifacts. Nothing was pushed or deployed.

## What changed

The actual viewer now uses pinned **Three.js 0.180.0**, physically based
materials, procedural studio reflections, soft shadow mapping, separate metal
contacts, open connector housings, package bevels and actual pad/drill/copper
geometry. The existing BoardView camera, keyboard, learning and selection
contracts remain available, along with the Canvas 2D compatibility view.
Actual layers and component visibility can be inspected independently. Net
selection statically highlights matching artifact pads, tracks and vias,
including with reduced motion enabled.

The [KiCad GLB spike](GLB_SPIKE.md) found zero attached component models in the
actual PCB. Exported board geometry worked, but broad copper groups lacked
net/pad identity. A controlled model-association probe preserved `R1`; this was
not mistaken for complete model availability. The selected pipeline uses the
authoritative board projection with separately keyed procedural package
appearances, preserving source identity through every selectable assembly.

The dense educational explorer uses **124 illustrative bodies**, all
**158 inventory dispositions**, **18 sample family previews/close-ups**, and
26 reusable factories including the actual-board package variants. It contains
different IC forms, six headers, connector interiors, silver and navy cans,
colored passive banks, a real winding mesh, small packages, solder/contacts,
printed labels, board thickness, four large holes and 24 small surface rings.
The layout check finds no mutual package/lead XY bounds overlap; this is an
artistic composition check, not electrical clearance verification.

Search reaches tiny bodies and named parent subdetails. Selection resolves
leads, contacts and instanced submeshes to their parent. Orbit, zoom, front/back,
reset, explode/exact assembly reset, isolation, layer controls, family previews,
technical disclosures, reduced motion and context-loss fallback are integrated.
The final atlas framing uses more of the stage height while the actual board's
framing default remains unchanged.

## Truth, inventory and asset provenance

[VISUAL_COVERAGE.md](VISUAL_COVERAGE.md) records each of the 158 IDs:
124 bodies, 9 parent subdetails, 8 unresolved patches, 4 corner holes,
10 shared rendering features and 3 viewport-aid dispositions. The scene does
not assert 158 electrical components. Uncertain source objects retain UNKNOWN
identity/function; general family lessons do not establish their circuit role.

The sample persistently says **Reference-inspired educational model · not an
electrically verified design**. It has no authenticated netlist, verdict, BOM
price, manufacturing eligibility or export controls. Tampered illustrative
requests are rejected by the existing project/export boundaries.

Actual board geometry is **ARTIFACT_DERIVED**; package bodies and heights are
**PACKAGE_APPROXIMATION**; sample geometry is **ILLUSTRATIVE_ONLY**. No extra
real ICs, mounting holes, pours, traces or fabricated silkscreen were added.
The saved projection supplies no silkscreen primitives, so actual labels remain
a viewer overlay. The display thickness is not a verified manufacturing stackup.
Some source pad corner shape information is absent from the projection; display
tessellation is not a manufacturing geometry oracle.

All procedural packages, markings and studio lighting are original project
source. The repository has no declared license for these original assets;
their registry says **UNSPECIFIED**. The separately vendored Three.js modules
carry their upstream MIT license in `apps/web/vendor/THREE-LICENSE.txt`.
No KiCad model, external font, HDRI, texture or supplied reference image is
redistributed in the app. Private comparison HTML embeds the supplied reference
only under ignored `out/`, not the server's asset allowlist.

`visual-version.js` records SHA-256 hashes for models, inventory, renderer,
layers, actual model bindings and the pinned vendor files. Actual manifest IDs
include source artifact and visual hashes; sample IDs have their own
`ohmni:illustrative-reference:v1` namespace. Scoped LF attributes preserve
hashed source bytes across Windows checkouts. The server still snapshots a fixed
local asset allowlist and binds response bytes to UI/server identity. A discovered
inherited HEAD filesystem bypass was closed with a fixed 405 response.

## Source integrity

The final audit compared **22 recorded source files plus the saved preview**:
all 23 byte hashes match their prior baseline. Nine canonical fingerprint/policy
fields also match. No `src/ohmni` code or engineering artifacts changed.

| File | SHA-256 before and after |
| --- | --- |
| `circuit.json` | `137155eff5c52e397e313e46517fa12761760edd4c154617645c486f4c254a4b` |
| `golden.kicad_pcb` | `8ec92f595a26b5769e16186e32231332955db4411247973489abe6c9c9def4f8` |
| `apps/web/reference-board.json` | `951fc4724f3402d8d9b6a4418d6f90182447fb7c597ba18f20c2e966667cc98b` |

Full before/after values: `out/visual-reference/source-integrity-final.json`.
The actual board remains 29 parts, 21 nets, 132 pads, 452 track segments,
55 vias, 90 × 55 mm, two copper layers. Existing saved ERC warnings, partial
identity verification and simulation/bench limitations remain applicable.

## Verification and independent review

- Canonical fast gate: **1,477 passed, 44 deselected**, 250.08 seconds. The
  only later rendering adjustment increased the sample's framing margin;
  the complete frontend and browser suites were rerun on that final state.
- Full final frontend suite: **180 passed**, no failures/skips.
- Native KiCad golden A1 routing/DRC/manufacturing regression: **1 passed**,
  with KiCad 10.0.5 through the guarded runner. Expensive routing was not
  rerun for material or framing adjustments.
- Ruff: **passed**. Workflow validation and final workflow gate are recorded
  in `.ai/verification/VIS-T01.yaml`. No static type checker is configured or claimed.
- Real Edge browser acceptance: no JavaScript errors; 18 family close-ups;
  unchanged preview hash; static SDA GPU image changes and exact clear/reset;
  unchanged 124-owner count; explode/reset; scene separation; 390 × 844 reduced
  motion; local-only network; real WebGL context-loss fallback. A separate
  copied-fixture probe confirms missing visual bindings render a bounded
  placeholder while retaining the owner and source bytes.
- One focused independent final review, followed by targeted re-review of its
  two P2 findings. Static net highlighting and the unresolved-detail family
  close-up were fixed. The reviewer independently passed 10 correction tests,
  checked GPU pixels and X01 in a private browser, and found no remaining
  actionable findings in that correction scope.

The reviewer's provisional rubric is **22/24**: ten categories score 2;
surface detail and lighting score 1 because some pads/solder/printed details
remain schematic and shadows are comparatively hard. This engineering/art
review does **not** replace human visual acceptance or claim image identity.

Initial gate failures were fixed and retained in the verification history:
an old scope assertion, a context-construction listener leak on unavailable GPU,
and a static-asset snapshot test run during a changing candidate. The final
passing evidence supersedes those failed attempts.

## Measured rendering cost

Machine: Edge 153.0.4234.32, ANGLE Direct3D11, AMD Radeon(TM) Graphics
(0x000013C0), 1500 × 853 browser viewport, device scale 1.

| Scene | Render surface | Triangles | Draw calls |
| --- | --- | ---: | ---: |
| Actual board | 1068 × 558 | 37,126 | 77 |
| Dense sample | 1126 × 603 | 235,542 | 648 |

The 90-frame orbit measurement had a **16.7 ms median RAF interval** and
**16.8 ms p95**. CPU submission/render was **5.4 ms median, 6.2 ms p95**.
Exact final timings are in
`out/visual-reference/browser-evidence.json`; these are CPU timings, not GPU
timer-query measurements. Performance on other GPUs is unmeasured. Low GPU
load mode disables shadows and caps pixel ratio; unavailable/lost WebGL uses
the existing simpler 2D view.

The nine measured visual/runtime JS files total **902,333 raw bytes** and
**222,158 bytes if gzip-compressed locally**. This includes 720,032 bytes of
Three.js. The demo currently serves raw bytes; the gzip number is a packaging
measurement, not claimed HTTP compression. Existing application modules, CSS
and the board projection are additional. No downloaded geometry or textures
are needed at runtime.

## Browser screenshots and comparison

All paths below are beneath `C:\Dev\hackathon\out\visual-reference\`.
They are actual browser captures, not image-model output. Whole-board source
captures use 1500 × 853; comparison pages scale each image equally.

| Evidence | Local file |
| --- | --- |
| Four-panel comparison | `comparison.html`, `screenshots/comparison.png` |
| Actual before/after | `screenshots/actual-before-after.png` |
| Reference versus educational scene | `screenshots/reference-comparison.png` |
| Original actual viewer | `screenshots/00-actual-before.png` |
| Early five-object proof | `screenshots/01-five-object-proof.png` |
| Actual board after | `screenshots/10-actual-after.png` |
| Actual package macros | `screenshots/actual-J1-macro.png`, `actual-U1-macro.png`, `actual-SW1-macro.png`, `actual-J2-macro.png` |
| Actual SDA / underside / mask | `screenshots/13-actual-sda-highlight.png`, `11-actual-underside.png`, `12-actual-copper-layer.png` |
| Dense educational scene | `screenshots/20-dense-sample.png` |
| IC leads / header contacts | `screenshots/30-ic-leads.png`, `31-header-contacts.png` |
| Silver/navy cans, banded/tan bodies | `screenshots/32-silver-can.png` through `35-tan-passive.png` |
| Coil / shell / small-part list | `screenshots/36-winding.png` through `38-small-part-list.png` |
| Explode / holes / underside | `screenshots/39-exploded.png` through `41-sample-underside.png` |
| Complete asset library | `screenshots/43-complete-library.png` |
| All 18 family macros | `screenshots/family-*.png`, including `family-unresolved_patch.png` |
| Compact reduced motion / fallback | `screenshots/50-compact-reduced-motion.png`, `51-context-loss-fallback.png` |

## Reproduce assets and checks

Committed local modules are sufficient to run the demo offline. To refresh
the pinned vendor bundle after an intentional source edit:

```powershell
npm --prefix apps/web ci --ignore-scripts --no-audit --no-fund
.\.venv\Scripts\python.exe scripts\prepare_visual_assets.py
node --test apps/web/tests/*.test.mjs
.\.venv\Scripts\python.exe scripts\verify.py fast
.\.venv\Scripts\python.exe -m ruff check .
```

Restart the local server after asset changes because it intentionally serves an
immutable snapshot. The browser runner uses an installed Playwright package and
Microsoft Edge (set `OHMNI_BROWSER_CHANNEL` for another installed channel):

```powershell
$env:OHMNI_PLAYWRIGHT_MODULE='C:/Users/wongj/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
node scripts/visual_acceptance.cjs http://127.0.0.1:8767 out/visual-reference
```

Commit-bound gate/review records and final repository state are in
`.ai/verification/VIS-T01.yaml`, `.ai/reviews.yaml`, and `.ai/state.yaml`.
The task remains VERIFIED pending the owner's screenshot comparison; no agent
has marked the visual result human-accepted.
