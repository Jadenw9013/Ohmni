# Ohmni UX audit and implementation handoff

Audit date: 2026-10-01. Baseline: `61d3832` plus the preserved CS working tree.
Scope: **UX-CLARITY-1**, explicitly approved by the user's UI/UX request.
This is a source review and local browser audit, not a user study or accessibility
conformance certification. Implementation results are in `UX_CLARITY_CHECKPOINT.md`.

## The product, in one screen

**Build circuits. Understand why.** Ohmni helps a programmer, student or curious
maker take a first step into electronics: choose a small USB-powered ESP32 project,
understand its components, and inspect the checks on the generated circuit.
The first visit must answer: what is this, can it help my idea, and what do I do next?

The default user can code but has not designed a board. A secondary user is learning
what components do without creating a project. An experienced engineer needs the
source evidence and exact artifacts, but those are a second layer of information.
Low vision, keyboard-only operation, touch, motion sensitivity and weak graphics
hardware are ordinary use cases, not optional modes added after design.

### Honest capability boundary

| User intent | Current experience |
|---|---|
| Start a project | Three supported families: sensors, buttons/lights, SPI memory; USB-powered ESP32 |
| Understand components | Catalog-backed learning library, artistic 3D package approximations |
| Try placement | Disposable layout practice, undo/redo/discard; no saved PCB modification |
| Inspect engineering | Actual generated results and their individual checks; unavailable checks remain unavailable |
| Order a working device | Not established. Routing/release limitations remain; no fabricated hardware validation |
| Identify an unknown image component | Appearance is insufficient; leave identity unknown |

Do not equate a polished model with a verified design. Do not advertise arbitrary
PCB generation, guaranteed downloads, firmware, simulation or working hardware.

## Evidence and audit method

Read `AGENTS.md`, `ARCHITECTURE.md`, `VERIFICATION.md`, `AI_WORKFLOW.md`, the product
definition and current atlas handoff. Inspected the live local first screen and
component dialog, plus HTML, CSS, routing, learning and project modules. The baseline
first screen contains a left journey sidebar, header, introductory title, component
CTA and a 124-body decorative board before the project starter. This is observed;
conversion and task-completion impacts below are hypotheses to validate with users.

## Six concerns reported by the user

### U01 — Reading text is too small (high)

Evidence: `styles.css` has many 14px navigation/help rules and a 15px welcome lede;
`component-stories.css` uses 13px model limits and source text. Body's nominal 18px
does not protect these overrides. Small text includes consequential limitations.

Solution: use a relative type scale, 18px-equivalent reading text and controls,
16px-equivalent secondary text, line height near 1.5–1.6, and short readable lines.
These sizes are this product's design choice, not a WCAG minimum font size. Respect
browser text preferences; do not disable zoom. Increase target size with the type.
Acceptance: inspect computed sizes, 320px layout and enlarged text, including dialogs
and error states. No clipped actions or hidden limits at 200% text enlargement.

### U02 — Everything competes for attention (high)

Evidence: `index.html#describe` mixes dense art, reference circuit, project creation,
saved projects, components and process explanation. Several actions say “explore”.

Solution: home explains the purpose; workbench starts or resumes a project; library
teaches parts. Use progressive disclosure for examples, source hashes and experimental
art. One dominant action per screen. Acceptance: project creation is visible before
any example board, and opening/closing an example never resets a user's project.

### U03 — Purpose and audience are unclear (high)

Evidence: “Your next little invention”, “guided electronics workspace” and “dense
board” describe atmosphere or appearance; neither explains the supported envelope.

Solution: lead with circuit learning, explicitly name the USB/ESP32 scope, explain
the result in plain language and show the next action. Avoid promising a working
device. Acceptance: five new users should explain purpose and scope after ten seconds;
target four correct explanations. This user study is still outstanding.

### U04 — No useful home landing page (high)

Evidence: `/` immediately mounts project navigation with four unavailable steps.

Solution: dedicated home surface and navigable workbench, concise product proposition,
one primary start action, optional learning path, three real project families, and a
short explanation of checks and remaining human work. No fake testimonials or metrics.
Acceptance: home/workbench Back and Forward work without losing in-memory edits.

### U05 — 3D needs purpose and visual quality (medium)

Evidence: the largest visual shows 124 bodies and 18 families without relating them
to a beginner's task. Visual density is being mistaken for product capability.

Solution: give one known component room to breathe; switch between processor, sensor
and USB connector using named buttons and a short role explanation. Models come from
the existing snapshot-bound library; orbit is user controlled. Keep model approximation
visible and text available when rendering fails. Acceptance: library failure cannot
invent a model; reduced-motion preference prevents automatic movement; controls work
without precise canvas picking.

### U06 — PCB feels hardcoded and unidentified parts undermine trust (high)

Evidence: `visual-inventory.js` is an authored illustration; `reference-board.json` is
a saved artifact; `project-workbench.js` makes real saved configurations. Presenting
these together conceals their different origins. Some art identities are unresolved.

Solution: remove the art board from the default journey; label the saved example as
an example, and put real configuration first. Use catalog identity only when present;
retain unknowns in experimental art rather than guessing. Distinguish artistic shape,
catalog fact and actual verification. Acceptance: a known part name never implies
manufacturer-accurate geometry; no imported-part admission or saved placement writes.
Accurate package CAD and electrical admission remain CAB/CS work, outside this UI fix.

## Eight additional findings

### A01 — Navigation does not match browser expectations (high)

Evidence: `app.js` switches hidden stages; the brand links to `#top`, not a home
experience. Home and workspace have no distinct URL state.

Solution: use stable home/workbench hashes with Back/Forward handling, document titles,
focus on the destination heading, and preserve the mounted workbench. Do not serialize
unsaved electrical drafts into URLs. Acceptance: repeated Home/Workbench/Back/Forward
does not call create-project or lose the current form. Deeper project/run routes are
future work; do not imply refresh restores unsaved fields.

### A02 — Nested scrolling burdens magnification and keyboard use (high)

Evidence: `.story-details` has its own max-height and scroll area inside a height-limited
dialog; the sidebar is constrained to viewport height. Enlarged text multiplies scroll
regions and makes the footer hard to find.

Solution: one document/dialog scroll owner; let the story text expand; switch grids to
one column at narrow effective widths; let navigation scroll instead of clipping.
Acceptance: 320px and enlarged-text views retain close/previous/next controls and wrap
long catalog IDs. The spatial sandbox may scroll internally but its controls must not.

### A03 — Small story selectors depend on precision (medium)

Evidence: progress is twelve flexible, unnamed visually, 24px-high bars. On a 320px
screen each bar can be below 24px wide. A current part is only distinguished visually.

Solution: retain accessible labels and current state, provide generous previous/next
actions, and give selectors at least 44px targets with wrapping. WCAG AA minimum is
24px subject to exceptions; 44px is our more forgiving design target. Acceptance:
target bounding boxes inspected at narrow widths; keyboard navigation remains possible.

### A04 — Premature unavailable actions feel like broken software (medium)

Evidence: home shows disabled future stages; stories show a disabled “Use in a project”
beside implementation language (“electrical admission”).

Solution: keep future stages inside the workbench, explain library capabilities in
plain language, remove the dead call-to-action, and offer the functioning layout
practice action. Clearly say practice layouts are discarded and cannot edit a project.
Acceptance: no enabled control promises unsupported insertion, and no warning disappears
from source details. Later insertion must be unlocked by real server eligibility.

### A05 — Lessons begin with catalog jargon instead of component purpose (medium)

Evidence: the resistor description begins “Resistance is an instance value, not a part
fact”; connector titles are raw uppercase IDs. These are data-model explanations.

Solution: show a plain-language role first, retain exact part identity below it, and
move raw catalog description/evidence receipts into an expandable source section.
Do not replace limits or invent ratings. Acceptance: electrical specifications still
come only from evidence; unknown parts fall back to exact catalog identity.

### A06 — Graphics cost is paid before the user chooses to explore (medium)

Evidence: `attach()` initializes the reference preview eagerly and the inline explorer
initializer creates a second board on home. Multiple scenes cost memory and distract.

Solution: initialize saved preview on disclosure, dense art on explicit request; use
one hero renderer at a time and dispose when leaving home. Pause animation on invisibility
and honor reduced motion. Acceptance: repeated navigation does not accumulate canvases;
network/model errors leave meaningful text. Low-end physical-device profiling remains
necessary; FPS targets without measurements would be invented.

### A07 — Local persistence expectations are too easy to miss (high)

Evidence: “Projects saved on this local server” appears below the project pitch, while
layout discard semantics live in a separate dialog. Users may expect cloud sync or
automatic saving when navigating away.

Solution: place local-save explanation beside the project action; distinguish saved
project revisions from disposable practice. Home navigation must preserve an open form.
Acceptance: copy explicitly says no cloud sync and unsaved edits do not survive reload;
do not introduce localStorage persistence of engineering intent as an ad hoc fix.

### A08 — Loading failures need a nearby recovery path (medium)

Evidence: existing library dialog has loading/retry handling, but this must extend to
the new landing model; an empty canvas would look like an unimplemented feature. The
saved example and project server have different availability and must not be conflated.

Solution: independent loading, missing-model and failure states with a local retry;
keep primary project and text learning content usable. Announce concise status changes
without reading the entire panel every orbit frame. Acceptance: rejected fetch and
missing model tests, identity mismatch rejection, and visible fallback; do not retry
indefinitely or reinterpret errors as a loaded/verified model.

## Design direction and simplification decisions

Palette: paper `#ffffff`, cool canvas `#f5f8fb`, ink `#142c3a`, action blue `#2159e8`,
deep action `#1744ba`, component green `#247659`. Keep warning/error colors semantic.
Typography: local Bahnschrift/Aptos Display for large concise headings; Segoe UI for
reading and controls, system fallbacks. No downloaded fonts or decorative microtext.

```
Home:       brand                   Workbench | Learn components
            clear promise           one large named 3D component
            scope + Start a project  role buttons + orbit control
            what you can make       what checks can/cannot establish
Workbench:  compact journey          start/resume project
                                    optional saved example / practice
```

Left-aligned copy, generous vertical space and a memorable physical component rather
than a dashboard of decorative cards. Reviewed against the brief: rejected a giant
dense-board hero and feature-card grid because they reproduce the clutter being fixed.
Use motion to explain the selected component, never to imply electricity is simulated.

## Standards used (design targets, not a conformance claim)

- [W3C Resize Text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html):
  preserve content/functionality at 200% text resizing.
- [W3C Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html):
  reading content should reflow at 320 CSS pixels; spatial CAD is a distinct case.
- [W3C Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html):
  at least 4.5:1 normal text, with relevant exceptions for large text.
- [W3C Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html):
  24 CSS pixel minimum or qualifying spacing/exception; our primary controls target 44px.
- [W3C Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html):
  allow motion to be disabled. This AAA criterion informs the design, not a claimed rating.

## Takeover priorities after this slice

1. Review the checkpoint's actual implemented/partial matrix and exact test results.
2. Independently test screen reader announcements, 200% browser text enlargement,
   reduced motion and low-end touch hardware; conduct the five-person comprehension test.
3. Address deeper project routes, refresh/unsaved-edit recovery and project-form jargon
   as bounded UX follow-ups. Validate save-state semantics before adding autosave.
4. Resolve existing CS/CAB engineering gates before promising real drag-to-PCB editing.
5. Keep saved-example checks separate from current-run checks and release eligibility.
6. Measure task completion (start, save, identify a failing check), not dwell time on art.
