# OHMNI landing PCB plan — independent review record

9 October 2026. Scope: research and planning only.

## Final decision

**PASS from all three independent reviewers. No unresolved blocking plan findings.**

Reviewed artifact: `PLAN.md`, version 1.1.

SHA-256: `1fa0d10cc0fcbf0b55e71ed031bcc193f79e3b494f525a483339a5b4b5a23cc3`

| Reviewer | Review scope | Final decision |
| --- | --- | --- |
| `pcb_ui_reviewer` | Art direction, visual hierarchy, camera, component appearance, concrete visual gates | PASS — planning quality |
| `pcb_ux_reviewer` | Keyboard/touch access, motion, navigation, failure states, source honesty and accessibility test plan | PASS — UX/accessibility plan quality |
| `pcb_architecture_audit` | Existing implementation, model/footprint joins, renderer adapter, loading, lifecycle, provenance and measurable acceptance | PASS — engineering planning review |

Each reviewer read the complete revised plan and independently verified the same hash. The reviews were performed by separate agents, not self-certification by the author. Agent review messages are preserved in the task history; the findings and decisions below are recorded here for durable reference.

Approval applies to the plan's coherence and readiness for the owner's decision. It does not approve unrendered visuals, establish measured performance, certify accessibility conformance, validate hardware, or authorize implementation, publishing or spending. The plan retains separate prototype, implementation and owner-review gates.

## Review cycle and resolved findings

Initial version 1.0 hash: `1045929c3c9063b7b0d3eef73d77008b650df8b755d421319a4fed0654176820`.

All three initial reviews returned **CHANGES_REQUIRED**. The author revised the plan rather than treating those results as approval.

| Finding | Raised by | Resolution in version 1.1 |
| --- | --- | --- |
| The board camera was incorrectly described as orthographic. | UI, engineering | Art direction now retains the actual perspective board pipeline. Camera/FOV tuning is a P1 visual decision; the component preview is a separate pipeline. |
| Canvas picking did not give keyboard users or small touch targets access to all 29 parts. | UI, UX | Native All parts selector shares selection state with picking, subsystem indication, inspector, connections and library action. R1 and J2 keyboard/touch cases are explicit acceptance tests. |
| Fallback promised functional explanations without an independent data path. | UX; UI clarification | A checked-in semantic projection is derived from and tested against the frozen reference. Its lightweight controller has no rendering imports. Live data, static snapshot, rejected snapshot, blocked bootstrap and no-JS states now have distinct behavior. |
| Camera, connection and lesson actions were ambiguous without live 3D or an individual selection. | UI, UX | Whole-board, subsystem, part and fallback availability is specified. Static mode exposes connection names, not a false copper overlay. Camera/replay controls are disabled with a reason. Unknown lesson matches become explicitly labelled library searches. |
| Session Motion Off must survive OS preference changes. | UX | Effective motion requires both no session Off and no OS reduced-motion request. OS changes never replay the entrance. |
| Retaining approximate bodies could bypass visual quality acceptance. | UI | U1, U3 and J1 require individual close-ups plus hero-scale review. Inadequate appearance stops integration until the smallest evidenced refinement is proposed. |
| There was no concrete renderer seam for the new model assembler. | Engineering | Optional instance-model resolver through the renderer factory preserves manifest transforms, stable identity and resource ownership; an optional hero context-loss hook selects the poster while lab defaults remain. |
| Footprint source identity and physical fit were conflated. | Engineering | Registry identity and derived land-projection hashes are distinguished from absent original footprint-file hashes. Contact overlap/hole alignment is checked separately from names, with explicit physical identities for repeated switch lands and preserved electrical grouping. |
| Direct lazy imports alone would leave eager transitive rendering dependencies on the CTA path. | Engineering | The complete import graph is in scope; home/CTA bootstrap must work while Three/model imports are blocked. Failed promises reset for bounded retries, disposed renderers are not cached, and late imports cannot mount after cancellation. |
| New root modules would not automatically participate in existing visual source hashing. | Engineering | Explicit inclusion-list changes and mutation-sensitive source-hash tests are specified. Poster output hashes remain separate to avoid a hash cycle. Old illustration contracts may be intentionally updated; engineering expectations remain protected. |

## Final reviewer statements

UI reviewer: “No blocking plan findings remain.” The art direction is specific, scope is bounded, and existing geometry/lighting provides a credible investigation path. Actual visual quality still requires the P1 evidence.

UX reviewer: “No remaining blocking UX findings.” The selector, independent semantic snapshot, input/motion behavior and failure-state checks address the previous gaps.

Engineering reviewer: “No outstanding engineering planning blockers.” All five technical findings are resolved; performance targets remain proposed and measurable, not claimed measurements.

## Evidence and limits

- Inspected local main `acdd7e37cf176bee066d0b768f9e327d3f228043` and fetched remote main `f1fb90c727b325b2656fdb1ecad6fdd8904c3073`. The relevant landing/render/server source files match across them. Implementation must recheck the then-current remote revision.
- Read the existing landing, source board, renderer, library binding conventions, delivery setup and earlier visual evidence. Inspected the current generated artwork locally.
- Reviewed primary Three.js, MDN, web.dev, W3C and Higgsfield documentation; source URLs and connector responses are in `RESEARCH.json`.
- Higgsfield read-only model discovery and price-only estimates returned 6.25 credits for a silent 5-second standard Kling 3.0 clip and 7.5 for pro. Two standard attempts plus one optional pro refinement total 20 credits at those quotes. No images were uploaded and no generation jobs were submitted. The actual prepared request must be requoted before any later purchase or submission.
- Browser automation could not initialize because of a local sandbox ACL helper failure. No live browser test, new visual prototype or implementation acceptance is claimed. The plan specifies the later browser/device evidence required.
- Only planning artifacts were written under `out/landing-pcb-plan/2026-10-09/`. Runtime source files, saved electrical artifacts and the parked behavior worktree were not edited. The main checkout remains clean; it is two commits behind the fetched remote.
- No runtime tests were run for this document-only work. Final artifact verification checks the reviewed plan hash, JSON readability, the quoted credit arithmetic and unchanged tracked files.

## Next boundary

The recommended next action, if the owner approves this direction, is P1: an isolated visual prototype from the saved board with physical-fit checks, selected component close-ups and a short deterministic motion capture. Core work requires no Higgsfield funding. Actual visual acceptance precedes integration; optional generated video remains a separate decision.
