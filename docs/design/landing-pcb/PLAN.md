# OHMNI interactive PCB landing — implementation proposal

Version 1.1 · 9 October 2026 · Research and planning only

This proposal is for the owner's decision. Independent agent review is recorded in AUDIT.md; it is design review, not human authorization to implement or spend credits. No runtime files have been changed for this proposal.

## Decision

Build a carefully lit, interactive rendering of Ohmni's existing **Sense & control** board. Its physical materials, recognizable components, camera framing and response to a visitor should supply the visual impact. Keep Higgsfield optional, for a separately reviewed short promotional film after the real scene looks good.

**Do not fund Higgsfield for the core landing-page work yet.** The repository already contains the engine and board data needed for the recommended experience. A small browser rendering prototype and its visual review should establish whether any generated media adds value. A generative video cannot supply reliable part picking, arbitrary camera rotation or authoritative terminal geometry.

The first release consists of one improved landing hero, a poster from that exact scene, three guided subsystem selections, component inspection, controlled camera motion, accessible controls and a working fallback. It does not include a whole-site redesign, a rebuilt component library, new electrical models, an invented PCB, or a new hosting platform.

## What the visitor sees

The page opens with the existing Ohmni brand and navigation. On the left:

> **Build circuits.**  
> **Understand why.**
>
> Design a USB-powered ESP32 project. Explore its parts, follow its connections, and see what the checks establish.
>
> **Start building** · Explore demo

On the right, a single tangible board occupies approximately 60% of the desktop hero. A satin USB-C shell, processor module, small sensor, ceramic capacitors, dark resistors and tin contacts catch a broad studio reflection. The green solder mask stays dark enough to distinguish parts and fine board edges. The object is fully framed and visibly sits as one coherent assembly.

The first reveal is a small camera settle, at most 8 degrees over 800 ms, then the scene rests. Picking a part reveals one short explanation. The visible **Power / Compute / Sensor** controls highlight the corresponding real subsystem. An explicit **Show connections** action reveals its recorded copper connections. A short moving emphasis along those segments is optional and clearly described as a connection guide, not simulated current.

The memorable moment is selecting Power: the real USB connector and regulator become legible, the relevant recorded connections gain emphasis, and the explanation identifies their roles. The visitor can continue into the full demo using the existing action. No continuous light show is required to keep the page interesting.

### Composition wireframes

Desktop, target 1440×900 and 1280×800; maximum content width approximately 1320 px:

```text
ohmni                          Build  Components  Docs       Get started

Build circuits.               [One assembled PCB, full outline visible]
Understand why.               [Three-quarter view; neutral studio light]
                              [One selected part marker, when needed]
Short explanation.
[Start building] Explore demo [Power] [Compute] [Sensor] [Whole board]
                              Part: [All parts (29) — choose a part ▾]
                              USB power enters here…
                              [Show connections] [Learn about this part]
                              [Rotate left] [Rotate right] [Top] [Reset]
                              [Motion: on/off] [Replay introduction]
                              Saved example · illustrative component bodies

Existing learning / 3D / checks links, kept visually subordinate
```

Small screens: one column. Headline, explanation and both CTAs appear before the board. The board has a reserved aspect-ratio box followed by wrapping controls and the explanation in normal document flow. Never place text over a tiny board to imitate the desktop layout. At narrow widths there is no promise that all content fits in the first screen; it must remain readable and scroll naturally.

### Art direction and tokens

| Role | Proposed choice | Reason |
| --- | --- | --- |
| Page background | `#030810` | Retains the existing dark Ohmni identity. |
| Main text | `#F4F6FC` | Clear headline and control labels. |
| Secondary text | `#B4C0D3` | Readable explanation and source caption. |
| Solder-mask appearance | Existing approved green material; scene target near `#2F4F3A` | Tangible board surface. This is a lighting target, not an unreviewed shared MAT token change. |
| Metal appearance | Existing approved tin/metal tokens; neutral reflections near `#A9ACAF` | Distinguish stamped shell, solder, contacts and shield. |
| Interaction accent | `#03E8DE`, small areas only | Selected component/connection state; always accompanied by text or shape. |

Use the existing Segoe UI/system stack for this scoped change. Proposed type: headline 56–64 px desktop / 36–42 px mobile, body 18 px, controls and key explanatory text at least 16 px. Use fluid scaling, approximately 1.1 heading and 1.55 paragraph line height; no fixed-height text containers. Confirm contrast in the actual composite, including focus and disabled states.

Remove the current screen blend, violet board lighting, emissive perimeter, fog, giant floating labels and gradient headline emphasis from the hero. Keep brand/logo assets and the lower page structure. One broad neutral key, a weaker cool fill and a restrained rim reflection should reveal geometry without clipping the metal to white. Use existing color management and tone mapping correctly. Color textures use sRGB; roughness/normal data do not. [Three.js color management](https://threejs.org/manual/pages/color-management.html)

Begin camera tuning near 30° azimuth and 40° elevation. Retain the existing perspective board pipeline initially (`VisualRenderer` uses `PerspectiveCamera`, with projection updates shared with the picking math). Tune framing/FOV in P1 and judge by the visible USB opening, module top and board edge; do not assume the component-preview camera is the board camera. Frame the complete board with 8–10% clear space and a stable target; the camera values are visual starting points, not dimensional facts. No shallow depth of field or bloom in the interactive release: small parts must remain inspectable.

## What is actually available

Read-only repository inspection used local main `acdd7e3` and fetched origin/main `f1fb90c`. The relevant landing, renderer and server files do not differ between those revisions. The newer behavior work is outside this redesign. Recheck both revisions and Git status before implementation; preserve the unrelated `.gitattributes` change in the old behavior worktree.

| Observed foundation | Evidence | Consequence |
| --- | --- | --- |
| Current hero is a generated 1536×1024 PNG, 1,923,602 bytes, with HTML callouts | `apps/web/index.html:33`, `landing.css`, `docs/product/UX_REFERENCE_LANDING_CHECKPOINT.md` | Replace the illustration and its treatment. Adding animation to it would preserve the underlying problems. |
| Saved board contains 29 components, 21 nets, 452 track segments, 55 vias, 90×55 mm | `apps/web/reference-board.json`, `docs/PCB_EXPLORER.md` | Use the existing reproducible board as the scene source. |
| Data records captured source/check metadata dated 2026-09-14 | `reference-board.json.source` | A saved example is not a fresh engineering run. Keep the source disclosure. |
| Existing board view supports selection, camera movement, reduced motion and disposal | `board-view.js`, `reference-preview.js` | Add a landing presentation/controller; do not create a second general-purpose board engine. |
| Existing Three renderer has PBR, procedural studio reflections, tone mapping and soft shadows | `visual-renderer.js:42–88` | Rendering improvements are feasible without buying media or introducing another framework. |
| Library has 180 data-driven component models but board rendering uses older approximate families | `component-library/README.md`, `visual-board-scene.js:4–16` | Exact package/model binding is an explicit implementation step. |
| Current board view captures touch and wheel gestures | `board-view.js:128`, `238–251` | A landing-specific input policy is mandatory. |
| Current entry imports already bring in Three and library generator code eagerly | `app.js:10`, `index.html:238–240`, `component-stories.js` | A new lazy hero alone will not reduce the initial code graph. Profile and fix the entry imports. |
| Static publishing currently has no build/install step | `vercel.json`; `scripts/demo_server.py:84,211` | Ship local browser modules and explicit static assets, MIME types and source hashes. |

The current physical scene explicitly lacks silkscreen primitives. Do not paint invented reference labels onto the board as if they came from the PCB. DOM inspection labels can be sourced from the actual component references. Body sizes/finishes and stack-up remain illustrative wherever the source says so.

## Board/model assembly contract

Freeze the chosen reference artifact identity in the hero manifest: `8ec92f595a26b5769e16186e32231332955db4411247973489abe6c9c9def4f8`. If the reference is intentionally regenerated later, repeat binding and acceptance checks against its new identity.

Reuse its placement, component IDs, pad/hole coordinates, copper, via positions and actual system membership unchanged. Improve visual bodies through a small explicit binding table. Each row records catalog ID, footprint ID, the available source geometry registry fingerprint, a separately named hash of the extracted physical-land projection, library model ID/source revision or approximation asset, contact-to-land/electrical-number mapping where supported, transform/frame, LOD and remaining uncertainty. The saved JSON has no per-component original footprint-file SHA: never label a new projection hash as that missing source hash. If a library validator requires an unavailable revision identity, do not manufacture it or claim that validator passed; retain the declared approximation until the required evidence is available.

Inspect these nine visible families, covering all 29 instances:

| References | Source part/package | Proposed geometry handling |
| --- | --- | --- |
| R1–R5, R10–R13, R20, R21 | 0805 resistors | Reuse chip-family model only after actual 0805 profile and pad mapping match. |
| C1–C7 | 0805 ceramic capacitors | Same explicit package binding; material stays ceramic. |
| D1–D4 | Green 0805 LEDs | LED lens and polarity mark; preserve the approved catalog-to-package polarity permutation. |
| J1 | USB-C HRO TYPE-C-31-M-12 footprint | Cavity/lip/tongue quality pass; accept a library connector only if the specific variant/footprint agrees. |
| J2 | Vertical 1×6, 2.54 mm header | Use the six-position variant with explicit pin mapping and board-tail convention. |
| SW1, SW2 | 6 mm through-hole buttons | Match the actual footprint and terminal layout, not just the nominal body size. |
| U2 | AP2112K-3.3TRG1, SOT-23-5 | Five-lead body with explicit package mapping; do not apply MCP1700 or another regulator's electrical pin order. |
| U1 | ESP32-WROOM-32E module | Retain or refine the existing named approximation until a specific module model and binding are evidenced. No generic QFP replacement. |
| U3 | BME280, Bosch LGA-8, 2.5×2.5 mm | Retain/refine a declared body approximation if no matching library model exists; do not substitute a similar QFN. |

All29 visible refs must be accounted for, including support parts. No decorative components, duplicate connectors, extra boards, invented mounting holes or brighter invented copper may be added for density. Approximate bodies may be visually improved within their recorded envelope, with uncertainty retained; dimensional or terminal changes require evidence and are a separate decision.

Use the existing `placeInViewer` and revision-specific footprint validator where applicable. Identity/name validation is separate from physical-fit validation: independently check transformed contact surfaces overlap their intended lands at the documented seating height, or that through-hole tails align with their holes and fit their geometry. Record tolerances from the source/geometry representation. Do not require coincident contact and land centers: for example, the library's 0805 resistor contacts are at ±0.825 mm while saved R1 lands are at ±0.9125 mm. A centered pad-distance assertion would wrongly reject a potentially valid overlap. Neither a matching label nor an overlapping bounding box is sufficient evidence of correct fit.

For symmetric resistors/capacitors, model terminal numbers 1/2 describe a canonical visual convention, not electrical polarity. For SW1/SW2, four physical lands carry repeated electrical numbers `1,1,2,2`; represent a physical land by stable `(ref, source land index, electrical pad number)` identity, and validate each physical contact independently while retaining its electrical grouping. The current unique terminal-to-pad validator cannot establish that four-contact mapping. Add a separate physical-land adapter/check or retain the declared approximation; never weaken the existing electrical identity rules to make this case pass.

The library and current renderer have different bottom-side conventions; apply exactly one agreed coordinate transform, test top/bottom rotation and named terminals independently, and never stack mirror operations accidentally. Models remain separate from footprint/pad geometry. Own each cloned material/geometry or use explicit shared ownership so disposing the hero cannot dispose the library or lab.

Approximation is an honest engineering fallback, not automatic visual acceptance. U1 (ESP32), U3 (BME280) and J1 (USB-C) require individual neutral-light close-ups and a composed hero-scale capture in P1. If their existing recorded envelopes cannot deliver convincing shapes/materials at the intended focus level, stop integration and propose the smallest evidenced geometry refinement. Do not hide poor close-up quality behind an attractive overview or substitute an incompatible package.

Prefer LOD1 across the board; LOD2 only for a selected or close-up hero-visible part if measurements allow. Use repeated geometry/instancing where it preserves per-instance picking IDs. The initial scope is the hero's families, not improving all 180 components.

## Interaction and state specification

| Action | Defined behavior |
| --- | --- |
| Start building / Get started | Existing new-project editor route and semantics; no project or run is created merely by loading or touching the hero. |
| Explore demo | Existing saved-example disclosure and circuit lab. Preserve history, unsaved workbench state and focus return. |
| Power / Compute / Sensor | Select recorded system membership (`power`, `compute`, `sense`), highlight real refs, show one short HTML explanation and optionally a bounded camera focus. These replace the old callouts' immediate catalog navigation; the new action is explicitly labelled as selecting the board region. |
| Whole board | Clear selection and restore the composed overview. |
| Click/tap a component | Select that actual ref; show recorded name and purpose. A hit always resolves through stable ref/instance ownership. |
| Part: All parts (29) | A compact native HTML select lists every ref with its human-readable name, including support parts and I/O. It shares selection state with mesh picking, subsystem buttons, inspector, connections and Learn. It is keyboard/touch usable without a canvas and stays available in validated static-snapshot mode. Selecting a system clears the individual-part option; selecting a part updates the system indication without changing that part selection. |
| Hover | Subtle outline/name preview only; no camera move, moving parts, focus jump, modal or required information exclusive to hover. |
| Show connections | Toggle recorded nets/tracks associated with the selected part/system, with textual net names and an adjacent “Connection guide; not a simulation” explanation. No animation if source connections cannot be validated. |
| Learn about this part | Explicit secondary action opens the existing library search/lesson for the selected identity; uncertain library matches are described, not silently identified. |
| Desktop drag | Local pointer-driven orbit, interrupted cleanly on pointer cancel/blur. Wheel keeps normal page scrolling. Do not add camera movement tied to page scroll or free cursor movement. |
| Rotate left/right, Top, Reset | Native HTML buttons give a non-drag equivalent. Buttons rotate 15° per press or restore a defined pose. Keyboard uses those controls and the existing bounded canvas shortcuts when focused; Tab always exits. |
| Touch | Inline board accepts tap selection; one-finger pan and browser pinch zoom remain native. No inline touch-drag orbit in release 1. Use the visible view buttons or open the full demo for its deliberate 3D viewport controls. |
| Motion toggle | Defaults to OS preference. Off stops decorative camera transitions, pulses and replay; pose/selection changes become immediate. Effective motion requires both no explicit session Off and no OS reduced-motion request. Explicit Off remains off across later OS changes. An OS change to reduced motion stops movement immediately; an OS change back never replays the entrance. The visible session control cannot override an active OS reduced-motion request. |
| Replay introduction | User-triggered replay of the 800 ms settle, disabled with an explanatory label when motion is off. No automatic continuous turntable. |

All controls use ordinary buttons and accessible names; selection uses `aria-pressed` where appropriate. Positive state is indicated by border/shape/text as well as color. Polite live-region announcements occur on completed selection changes, never on hover or every animation frame. Do not assign `role=application` to the page. Do not move keyboard focus when the canvas renders or the poster is replaced. The caption and inspector are HTML.

**Action availability is explicit.** Whole-board state offers the overview and Explore demo; Show connections asks the visitor to choose a part/system rather than lighting every net, and Learn about this part is unavailable with that short explanation. Subsystem state offers member refs and textual net names, with a guide overlay only when live geometry is validated; Learn requires an individual part. Individual-part state offers its recorded connection names and the existing matching library/search action. If no exact library lesson is known, label the action **Search component library**, prefill the recorded name, and avoid promising an exact lesson. A part with no recorded connections says so and disables that action. In static-snapshot mode, the action is labelled **Show connection names**; it never promises a copper overlay. If neither the live data nor the independent saved snapshot is usable, disable data-dependent controls with an explanation and retain the readable summary.

Proposed caption: **Saved example · illustrative component bodies**. “Design details” discloses capture date, source fingerprints, package uncertainty and recorded checks. Connection-guide copy remains visible while that overlay is enabled. Existing actual check results remain discoverable in the demo; no green “verified” badge is introduced by the hero.

### Loading and motion lifecycle

1. HTML copy/actions and the reserved-size poster appear immediately. A small home bootstrap installs navigation and CTA handlers without importing a renderer or model module. Start building and Explore demo do not await the hero initializer. HTML defaults show a readable static summary and an honest note that interactive tools require JavaScript to finish loading; enhancement-only controls are hidden/disabled until their handlers exist. A no-JS or blocked-bootstrap page must not display apparently working dead buttons. Keep ordinary navigation links usable.
2. Check in a small, renderer-independent semantic snapshot generated from the frozen reference: all 29 refs/names, system membership, connection names, source identity and explicitly authored descriptive copy. Embed the projection in home HTML with native selector/summary markup so a blocked reference JSON does not remove textual exploration. An authoring script and deterministic test compare it with the frozen source; identify it as a derived saved snapshot, not fresh validation. The small controller validates its schema and expected identity before enabling inspection. If it is absent/rejected, retain only the static summary and explain that part inspection is unavailable. Fetch and validate the full reference only for live geometry; do not combine mismatched live data with the saved snapshot. On mobile or reduced-data mode prefer the poster and an explicit **Enable 3D** button. Do not infer unavailable network preferences as permission to transfer a large video.
3. Create at most one active hero renderer. Replace the poster only after a correct first rendered frame. If ready within 2 s of page start, on a visible desktop with motion allowed and no prior interaction, the 800 ms settle may play; otherwise show the final pose immediately. Never move late while the visitor is already reading or navigating.
4. Cancel decorative motion on selection, direct input, route leave, modal opening, background tab or reduced-motion change. A selected explanation stays still. Connection emphasis runs for at most 1.2 s after an explicit action and then becomes a static highlighted path.
5. Render on demand after settling; no ongoing rAF loop while idle. Pause before the hero leaves the viewport. Dispose owned resources/listeners/observers on unmount or when the lab needs the active renderer; abort pending work and ignore stale completion callbacks. Returning home must not replay the entrance automatically.
6. Context loss, a missing renderer/model module, rejected live data or shader failure keeps/restores the exact-scene poster. With a valid independent snapshot, keep the Part selector, descriptions, library search and connection names; disable camera/replay controls with “3D view unavailable.” With a blocked full reference JSON, label this as saved-snapshot inspection; live geometry/overlays stay unavailable. With no valid snapshot, data-dependent inspection stays unavailable. A bounded Retry can recreate one renderer; after two failed retries stay in static mode. If a poster variant fails, try the other responsive still once, then retain a reserved neutral region and summary. No-JS/bootstrap failure follows the static HTML state in item 1, not a false promise of working inspection.

Cache successful module/data loads, never disposed renderer instances. Reset a failed launcher promise for a deliberate bounded retry. If imports finish after route cancellation, they may remain cached but must not mount anything. The hero's context-loss hook must choose this poster fallback; the board view's current compatibility-canvas fallback remains the default for existing lab consumers.

Rendering on demand avoids wasting power on an unchanged view. [Three.js guidance](https://threejs.org/manual/pages/rendering-on-demand.html) Motion preferences also apply to interaction-triggered animation; the AAA criterion is an additional design target, not a claim that every part of the site conforms at AAA. [W3C animation guidance](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)

## Implementation map

Proposed new filenames are targets for a future implementation, not files already built:

| Unit | Location / change | Responsibility and boundary |
| --- | --- | --- |
| Hero composition | `apps/web/index.html`, `landing.css` | Replace PNG/halo/fixed leaders with poster/canvas stage and accessible controls. Scope CSS under home. Keep workbench styles untouched. |
| Controller | new `apps/web/landing-pcb.js` | State machine for loading, selection, motion, fallback and route lifecycle; no project writes, no simulation calls. |
| Static semantic projection | new authoring helper and embedded snapshot/HTML in `index.html` | Generate refs/system/net names from the frozen source, keep authored explanations separate, and verify the checked-in projection matches that source. This small inspection/startup path must not import Three. |
| Model assembly | new `apps/web/landing-pcb-models.js` and generated binding manifest | Narrow model loading and explicit ref/footprint/model joins; no eager `loadFullLibrary()` for the hero. |
| Camera/input | `board-view.js` | Optional hero input policy, cancellable bounded camera behavior and context-loss callback; existing lab defaults retained and tested. |
| Presentation/model seam | `visual-renderer.js`, hero `rendererFactory` | Add an optional instance-model resolver supplied through the existing renderer factory. Today `setScene()` unconditionally calls `createAsset(entry.family, ...)`; the resolver replaces only the visual body for an eligible manifest entry, preserving source transforms, stable picking identity, overlays and explicit resource ownership. Missing/ineligible bindings follow the declared approximation policy. Default lab rendering remains unchanged. Add optional hero lighting/quality settings and owned material clones. |
| Geometry projection | `visual-board-scene.js` | Preserve authoritative projection. If binding extension is necessary, add an explicit optional adapter instead of changing source coordinates. |
| Entry loading | `app.js`, `home.js`, entry scripts, library launcher | Make home navigation/CTA initialization independent of renderer modules, including transitive edges such as `app.js → reference-preview.js → circuit-lab.js → board-view.js → Three`. Move lab/library/visual-explorer rendering behind cached async launchers at their actual use boundaries, with failure UI, deliberate retries and cancellation. Measure the complete import graph. |
| Poster and provenance | new `apps/web/landing-pcb-poster-*` + source manifest | Desktop/mobile responsive stills from the approved live scene. Record source artifact, visual hash, camera, renderer and export settings. |
| Static delivery | `scripts/demo_server.py`, `vercel.json` verification | Add assets/MIME allowlist entries; retain immutable UI identity, local imports and cache validation. Check production compression rather than assuming dev-server transfer size. |
| Reproducibility | `scripts/prepare_visual_assets.py`, focused frontend/source tests | Extend its explicit root-file inclusion list to cover new `landing-pcb*.js`, scene binding inputs, presets and semantic-projection authoring inputs; they are not automatically included by the existing library glob. Test that a scene-affecting input change alters the visual source hash. Record poster output hashes separately from source hashes to avoid a derivation cycle. Record fixed camera/export settings. Update intentionally replaced hero contracts, including old mandatory `landing-board.png` assertions; preserve engineering expectations. |

No React, React Three Fiber, GSAP, WebGPU rewrite, external runtime asset CDN or general glTF pipeline is required by this scope. The existing vanilla modules and pinned Three version are the starting point. Do not replace shared tokens globally to make one hero brighter. Propose any genuinely needed new approved material token separately; scene-local lighting and non-destructive material presentation are preferred.

The same old PNG also appears in the brief-editor masthead (`index.html:148`). Once the hero poster passes review, replace that secondary decorative use with the same still so the rejected illustration does not persist one click later. Do not add another renderer there.

## Performance contract

These are proposed acceptance budgets, not measurements or guarantees. Establish a named-machine baseline before the first rendering change. Historical desktop evidence of 37,126 triangles / 77 calls for an older actual-board scene is a feasibility clue only; it measured neither the new scene nor mobile GPU time. The current two Three modules total 720,032 raw bytes, so a “tiny lazy component” claim would be misleading.

| Budget / check | Initial target and measurement |
| --- | --- |
| Initial poster | ≤250 KB desktop and ≤120 KB mobile delivered asset; responsive dimensions reserved before load. Confirm quality at actual hero size. |
| Hero-specific transfer | ≤600 KB compressed for new/selected hero code/data/textures excluding the already-existing shared engine; report the engine separately and total page transfer. No all 180 data fetches to render 29 refs. |
| Page load | Target LCP ≤2.5 s, CLS ≤0.1 and interaction latency ≤200 ms; compare five cold runs against unchanged baseline under a recorded throttling profile. Report lab interaction measurements separately from field INP. |
| Render complexity | Initial cap 100 draw calls and 60k visible triangles for the whole hero at default pose; measure current Three renderer counters. Reduce unnecessary detail before relaxing a cap. |
| Frame pacing | During a defined 10 s scripted orbit, desktop p95 frame interval ≤20 ms; named representative physical mobile device ≤33 ms. Report browser/GPU, viewport, DPR, median, p95 and traces. Emulation is not physical mobile evidence. |
| GPU cost | Pixel ratio cap 1.5 initially desktop / 1 mobile; at most one shadow-casting key, 1024 shadow map initially; update shadow maps only when necessary. Measure rather than assuming triangles alone predict cost. |
| Idle/hidden | Zero continually scheduled scene frames after transitions settle or when hidden; no cumulative event listeners or GPU resources through 20 home↔lab cycles. Measure stabilized resource counts/heap after warmup. |
| Responsiveness | Touch page scroll remains native; primary actions respond during asset loading/compilation; camera/picking work is bounded. |

If a target fails, record the result and choose the lower tier: reduce shadows/DPR/detail, then offer poster plus Enable 3D. Do not call a failed gate passed by changing the threshold. A budget change requires explicit review of the measurement and tradeoff.

Core Web Vitals field thresholds are evaluated at the 75th percentile; a local test is not field certification. [web.dev](https://web.dev/articles/vitals) General WebGL guidance supports bounding resources and disposing them promptly. [MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices)

## Where Higgsfield fits, and what funding buys

Read-only model discovery confirms `kling3_0` supports start/end image roles, 3–15 s durations, 16:9 / 9:16 / 1:1, standard/pro/4k modes and silent output. The connector's parameter names are the ones to use; the public API documents similar image-to-video capability but is a separate interface. [Higgsfield API documentation](https://open.higgsfield.ai/models/kling-video/v3.0/std/image-to-video/api-reference)

This confirms capability, not PCB accuracy. Start/end frames constrain a video but do not establish preserved intermediate pin counts, labels, copper topology or geometry. A movie remains pixels; adding hotspots over it cannot make it an orbitable CAD object.

### Recommended optional experiment, after the real scene is approved

1. Export start/end stills from the accepted board/camera; keep the clean renders and source hashes as the baseline. Use only owner-approved reference media. No image upload or generation was performed in this planning phase.
2. Request one silent 5 s, 16:9 standard clip with a very small camera move and neutral studio lighting. Keep object silhouette/count/placement/markings constant. Do not request a circuit being invented, a flying assembly, electron simulation or a redesign of the PCB.
3. Compare against a deterministic 5 s recording from the actual WebGL scene. Inspect frame strips plus full playback for warping, topology changes, unstable labels, flicker, specular crawl and loop seams. The deterministic version is available without Higgsfield credits.
4. If the first result is promising, allow one alternative. If both have structural artifacts, stop the experiment. If one is materially better, optionally spend on one pro refinement. Never re-submit after an ambiguous tool timeout until its original job status is resolved.
5. Use a keeper only for an explicitly opened promotional clip or later launch material. It is not the landing's interactive canvas, fallback poster or electrical evidence. A decorative generated-film label belongs with the optional player. It must not delay home loading; no autoplay audio, no overlay hotspots implying real picking.

Suggested future prompt, not submitted: “Single rigid assembled PCB from the supplied reference. Preserve the outline, exact component arrangement and all visible connector geometry throughout. Neutral studio product lighting, satin metal reflections, dark green solder mask, restrained slow camera shift. No new parts, no floating layers, no glowing board perimeter, no morphing, no generated text, no audio.” A prompt is a request, never a guarantee that the model obeys it.

### Price-only preflight recorded on 9 October 2026

| Configuration | Returned estimate | Planned cap |
| --- | --- | --- |
| Kling 3.0 standard, 5 s, 16:9, sound off, count 1 | 6.25 credits | Up to 2 exploratory clips = 12.5 credits. |
| Kling 3.0 pro, 5 s, 16:9, sound off, count 1 | 7.5 credits | At most 1 refinement after a successful standard result. |
| Maximum proposed experiment | 20 credits from those quotes | Zero spend until the owner explicitly approves the experiment and current quote. |

No jobs were submitted by those estimates; reference images were omitted so there were no uploads. These are generation-credit estimates, not a subscription/dollar-price or a guarantee about available credit-pack size. Requote the actual prepared request and check any parameter adjustments before buying or submitting. The quotes do not validate generation readiness. Do not buy a plan solely on this calculation.

The core scene therefore has **zero Higgsfield dependency and zero planned Higgsfield spend**. It still requires engineering and review time. No promise of unlimited/free generation is made.

## Build order and review gates

“Properly the first time” means resolving the risky visual/interaction choices in a bounded prototype before integrating them, with explicit fallback and test criteria. It does not mean claiming a complex visual implementation needs no iteration.

| Phase | Concrete deliverable | Exit condition |
| --- | --- | --- |
| P0 — this proposal | Research, file-level plan, cost bounds and independent UI/UX/engineering critiques | All required plan findings resolved; owner decides whether to implement. No funding required. |
| P1 — isolated visual proof | Branch/worktree from current remote main; fixed artifact/model binding inventory; single scene; default/side/underside captures plus U1/U3/J1 close-ups; exact-scene poster; 800 ms motion recording | Correct identity and independent physical-fit checks; coherent assembly. UI reviewer and owner judge real materials/camera at target size. Retained approximations must pass the same visible-quality gate; otherwise propose the smallest evidenced refinement before integration. |
| P2 — interaction proof | Three subsystem buttons, all-parts selector, picking, HTML inspector, static semantic projection, gesture policy and reduced-motion states in an isolated development preview | UX reviewer can accomplish the same task by mouse, keyboard and touch, including R1 and J2 selection without mesh picking. Fallback remains useful; no project/network-generation side effects. |
| P3 — integration | Home lifecycle, cached imports, static delivery, poster swap, existing CTAs/library/demo, secondary PNG replacement | Existing home/workbench/library behavior remains correct; no duplicate renderers, stale requests, route/focus regressions or changed engineering data. |
| P4 — release evidence | Desktop/mobile stills, motion videos, failure-state captures, browser tests, performance traces, source/model manifest and change review | Automated checks pass plus separate UI and UX review of actual implementation evidence. Owner sees final preview before merge/deployment. |
| P5 — optional Higgsfield pilot | Two standard attempts and at most one pro refinement, only if separately authorized | Frame-by-frame visual audit demonstrates useful improvement over deterministic capture within the approved credit cap. Failure does not block the core hero. |

At implementation start, recheck Git and workflow ledger; create a new `codex/landing-pcb` worktree from the current fetched main, record the owner's actual implementation approval, and isolate this work from parked behavior tasks. Reconcile stale workflow records conservatively; do not mark their electrical stages accepted as a side effect. Commit separate rollback units: bindings/prototype, input/lifecycle, integration, final verification. Publishing and merging follow the owner's later instruction.

## Acceptance checklist that reviewers must use

1. **Visual:** one coherent board; no added decorative geometry; visible connector cavity and contact surfaces; distinct metal/epoxy/ceramic/mask; no floating terminals, intersecting shells, z-fighting, clipped highlights or alias shimmer during approved motion. Screenshot review at 1440×900, 1280×800, 768 px, 390 px, 320 px. Material comparison includes neutral-light close-ups, not only a flattering hero crop.
2. **Identity:** all 29 refs appear once; package/footprint binding inventory matches the frozen source and distinguishes original identities from derived projection hashes. Validate contact/land overlap or hole alignment independently of identity/name checks, including the repeated switch pad numbers. Rotation cases 0/90/180/270° and bottom-side mirror tests use independent expected coordinates; no double mirroring. Selected mesh/ref matches the HTML inspector and system membership.
3. **Interaction:** Power/Compute/Sensor/Whole board, all 29 selector options, picking, connections, library action and reset/replay/motion have the specified live/static/unavailable states. Test keyboard-only selection of R1 and J2, and equivalent touch selection without needing tiny mesh targets. No hover-only content or loop that resumes itself after Off or an OS preference change. Pointer cancellation and rapid selection/navigation are tested.
4. **Accessibility:** keyboard-only end-to-end, screen-reader smoke test, visible focus/selected state, ordinary HTML explanations; target 44×44 px touch controls as a product choice. AA target-size minimum is 24 px with exceptions; 44 px is not misrepresented as that requirement. [W3C targets](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
5. **Reflow:** 320 CSS px and 200% text enlargement without clipped controls or horizontal reading scroll ; 400% page zoom on a 1280 px desktop for reflow; touch/pinch/browser zoom intact. Camera viewport remains framed while text grows. [W3C reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
6. **Motion:** OS preference before and during session, explicit off, offscreen/background tab, modal open and route return. First reveal ≤1 s then rest; no flash/strobe. If future automatic motion exceeds 5 s, a persistent Pause/Stop control is required; hover/focus-only pausing is insufficient. [W3C pause guidance](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)
7. **Failure/startup:** separately block full reference JSON, Three, model module, home bootstrap and poster variants; reject the embedded semantic snapshot; lose WebGL context or fail shaders; simulate slow loading, retry twice and leave during initialization. With rendering modules blocked, Start building still opens the editor and Explore demo still navigates to its truthful unavailable/retry state. With reference JSON blocked, the valid saved snapshot supports textual part/connection inspection but no live geometry. With bootstrap blocked/no JS, readable HTML and honest disabled/hidden enhancement controls remain. Error handling must not retry endlessly, mount after cancellation or display an incorrect previously selected model.
8. **Performance:** report complete dependency graph and cold transfer bytes, real Three counters, frame pacing, teardown/resource stability and physical mobile evidence. If a physical device is unavailable, that gate remains explicitly unverified; emulation still covers layout/input as far as it can.
9. **Regression:** all frontend tests; focused home/board/visual-source/static-server/entry-contract tests; source generator checks; required repository fast/workflow checks sequentially, respecting existing test-run constraints. Verify no changes to reference artifact/check data, manufacturing outputs or source statuses. Do not modify frozen expectations to hide failures.
10. **Truthfulness:** saved-design and package-body scope visible; connection animation described as teaching visualization; no simulator, check or manufacturing claims created by shading or motion. Higgsfield media, if later used, has separate provenance and no authority over board data.

## Review decision and remaining uncertainty

Reviewers must issue PASS or CHANGES_REQUIRED against the frozen PLAN.md hash recorded in AUDIT.md. Their approval means the plan is coherent and implementable within stated gates. It is not approval of pixels that have not yet been rendered, evidence of hardware validation, physical-device testing, user taste, or permission to spend money.

Open implementation uncertainties are bounded: exact compatible models for the USB connector/module/sensor; measured quality of refined family geometry; the real import/network/render budget on target devices; and whether any generative film survives structural review. Each has a stated investigation phase and fallback. No missing value is silently filled from a guessed datasheet.

Research sources and read-only connector quote receipts are preserved in RESEARCH.json. Independent findings, resolutions and exact reviewed-file hashes are preserved in AUDIT.md.
