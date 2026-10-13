# Ohmni Paper frontend plan and AI handoff

Status: **PROPOSED. Research and documentation only; implementation is not authorized.**

Audited: 2026-10-13. Repository: fetched `origin/main` at
`7f91881d65a4823c1f77b664e6b37bf97e36c8f4` (PR #68).
Research branch: `codex/paper-frontend-plan`.
Input: owner's `Paper_Frontend_Rebuild_Proposal_Ohmni.md`, dated October 12.
Input SHA-256: `441c2255e9954eb4b4bb3995338511a3d5ee675f090fb5f4a688ecc0aa69f68c`.

This replaces that proposal's technical recommendations. It preserves the
project's [operating rules](AGENTS.md), [security policy](SECURITY.md),
[workflow](docs/AI_WORKFLOW.md), and engineering authority. It does not approve
the proposed product roadmap, Paper setup, a paid plan, deployment, or Sentry.

## 1. Architectural recommendation

Use Paper to design a coherent electronics workbench, then migrate its
presentation into the existing application in small, tested sections. Keep
vanilla JavaScript, the current request/state controllers, contract validators,
and board renderer. A framework rewrite is not a prerequisite for good design.

The defining experience is: **describe an idea, review the proposed choices,
watch actual checks, inspect the resulting board, understand the limits.**
The board and its explanation should be the memorable visual feature. Paper's
value is a shared, reviewable design system and complete state designs; decorative
shaders are optional and outside the initial implementation.

Design the entire journey so it remains coherent. Ship it as successive vertical
slices, not a replacement application assembled from static canvas exports.
Do not delete prototypes, rewrite networking, introduce React/Tailwind, or move
all CSS at the same time as changing the experience.

## 2. Authority and first actions for the next AI

The owner explicitly said **not to implement yet**. This file is preparation.
Only after a later explicit implementation instruction:

1. Inspect Git status/worktrees; fetch latest `origin/main`; start an isolated
   `codex/` branch, never `codex/behavior-*`. Never push or merge main.
2. Read the `.ai` ledger and preserve unrelated BM-T02 battery-motion work and
   all other agents' changes. Record the new human authorization under the
   existing workflow before activating a task. Do not infer approval from this file.
3. Recheck the integration map and capability limits against the new revision.
   `origin/main`, the owner's local main, and the running preview may differ.
4. Leave `src/ohmni/behavior/`, `tools/behavior_audit/`, `docs/behavior/`,
   `out/component-behavior/`, and `scripts/generate_behavior_*` untouched.
5. Use separate PRs for the units below, each based on latest main after its
   prerequisite merges. Preserve rollback boundaries and run the required suites.
6. Get approval before costs, account/trial activation, paid model calls, or
   product behavior outside the explicitly approved presentation scope.

No Paper MCP capability is exposed in this session. No Paper installation,
account access, canvas creation, export, or round-trip test was performed.
This audit is code/source research, not a live usability study or a deployed UI test.

## 3. Proposal audit: corrections that change the plan

Severity here concerns the proposed approach, not a claim of a new production bug.
Function names are more durable than line numbers; evidence refers to the baseline above.

| Priority | Original claim or instruction | Verified correction and resulting decision |
|---|---|---|
| HIGH | Hand-write the fetch/state layer again; port only validators | The main flow uses `mountConversation`, `mountProjectWorkbench`, `mountProjectAssistant`, and `projectRequest`. Retain those controllers. `/api/brief` and `/api/demo` describe the legacy example, not the whole product. |
| HIGH | HTML/CSS canvas means no translation | Paper's HTML importer drops selector styles/classes and transforms inputs to visual frames. Canvas fidelity does not establish semantic forms, event behavior, or accessibility. Implement semantic HTML in the existing app. [P3] |
| HIGH | Delete old landing directories first | Tests import the redesign model/candidate; visual-manifest tooling references both prototype directories. Their presence in the deployment is not evidence of first-load transfer. Defer removal to a separate dependency audit. |
| HIGH | Add new frontend modules while leaving the backend completely untouched | `STATIC_ASSETS` and `STATIC_CONTENT_TYPES` in `scripts/demo_server.py` explicitly register served files. Reuse existing served paths initially, or separately approve manifest-only additions. Never silently weaken serving. |
| MEDIUM | No board keyboard path | `board-view.js` already handles arrows, zoom, Home, brackets, Enter and Escape; `board-controls.js` exposes help, and component-list buttons select parts. Audit discoverability and real assistive use. |
| MEDIUM | AI input silently disappears | `revealFreeText` in `app.js` displays unavailable/connectivity explanations and opens guided setup. Preserve this recovery while improving its layout. |
| MEDIUM | No loading states | Conversation/assistant controllers already expose busy states, pending text and disabled actions; `renderProgress` displays server progress and explanations. Improve their clarity; never invent progress. |
| MEDIUM | 40 frontend tests | There are 38 test files at this baseline. The actual audit run executed **1,088 passing test cases**. File counts and test counts are different. |
| MEDIUM | Only a 20-second timeout | `projectRequest` defaults to 20 seconds; planning and assistant calls explicitly use 90 seconds. Some legacy direct fetches still lack that wrapper. Do not replace known behavior with a blanket shorter timeout. |
| MEDIUM | Restart loses all jobs | Persistence restores records and marks interrupted queued/running jobs `server_restarted`. Identity and artifact-current checks still matter. Do not promise either total loss or seamless continuation. |
| MEDIUM | Every response JSON has identity; UI hash covers all files | Some error bodies are exactly `{error}`; headers carry identity. `ui_version` hashes the server's allowlisted startup assets. It is not a comparison with the browser's own loaded bytes. |
| MEDIUM | Dozens of sequential requests and 2.2 MB parse prove the bottleneck | These require a browser waterfall/profile. Some library fetches run in parallel; dialog data is lazy. Raw disk size is not transferred bytes or measured parse time. |
| MEDIUM | Paper cannot collaborate or address multiple files | Official sources describe multiplayer and desktop tabs with agent work across files. Use one writer per artboard as our coordination policy, not a claimed product limitation. [P4, P5] |
| MEDIUM | Pro and `LAHACKS26` activation are mandatory | Free access has a finite MCP allowance. The promotion and challenge terms are unverified. Try a small budgeted feasibility test first; no automatic upgrade. [P6] |

The proposal correctly identifies visual inconsistency, dense information,
stylesheet overlap, and the need for mobile and accessibility checks. These are
useful design hypotheses. A source count alone does not prove a usability defect,
and a passing test suite alone does not prove a good experience.

## 4. Paper capability and evidence boundary

Verified from official sources on the audit date:

- Windows x64 is offered, alongside macOS ARM and Linux packages. The download
  page lists desktop 0.5.15; recheck installed version at setup. [P1]
- Current MCP docs recommend the Desktop-provided CLI using stdio and document
  Codex support. Older localhost HTTP remains supported. Use the installed setup
  panel and discovered schemas; never assume a fixed tool count or parameters. [P2]
- September's build log reports browser WebMCP; this does not establish that the
  current Codex session can use it. Desktop is the proposed route, not a statement
  that all browser agent workflows are impossible. [P5]
- HTML import has explicit translation limits. Exported React/CSS/Tailwind is
  implementation input, not a working accessible application. [P3, P5]
- Tokens include colors, spacing and typography. Multiple theme modes and shared
  token libraries remain roadmap items; copies across files are not synchronized. [P7]
- Real-time collaboration and multiple desktop tabs are documented. Confirm
  actual target file/frame IDs before any write. [P4, P5]
- Pricing lists 100 MCP calls/week free and 1M/week Pro; monthly Pro is $20 per
  editor, with a yearly discount. Account entitlements and promotion validity
  were not tested. Recheck checkout and renewal terms before owner-approved use. [P6]

Paper is a design-time dependency only. Production must work without a Paper
account, MCP server, iframe embed, or Paper network request. Do not claim there
is no platform-specific document model or that an editable canvas round-trips
losslessly to the application.

Imported image URLs can result in assets being uploaded to Paper. Use only
approved public repository assets or synthetic, clearly labelled design fixtures.
Do not import live project histories, private boards, provider responses, secrets,
or copyrighted private datasheet bundles. Never expose an API publicly or loosen
production CORS to make a design import work. [P3, P8]

## 5. Design direction: a clear electronics workbench

The proposed visual direction is **a precise instrument workspace with a patient
mentor beside it**. Retain Ohmni's dark blue identity and readable scale; reduce
repeated gradients, oversized explanatory panels, and equal-weight controls.
Use the real board as the main visual. This is a design recommendation requiring
review of actual Paper frames, not an approved final appearance.

### Layout and content hierarchy

- Persistent project sidebar: New project, recent projects, Components, Home.
  Do not invent an account/avatar, private user history, cloud sync or notifications.
  The project list is server-local, not a personal account boundary.
- One main work area. Before a board exists, use a legible centered conversation
  column. Once a result exists, let the board use the space and put contextual
  explanation in an adjacent panel. Preserve the current project/revision identity.
- One prominent next action for the current state. Secondary actions are visible
  but quieter. Advanced settings and raw evidence remain accessible disclosures.
- Text entry has a real label, visible boundary and focus state. Examples are
  selectable suggestions, never pre-filled text masquerading as user input.
- Keep a clear distinction between user's request, AI proposal, saved revision,
  running attempt and checked result. Avoid one long transcript that obscures them.
- Render only returned messages, structured proposals and saved facts. Do not
  invent assistant replies or a two-sided transcript when the API does not supply one.
- Use the same action wording throughout the flow. No generic “Continue” when
  “Review plan”, “Generate board”, or “Save as new revision” is more accurate.

```text
Desktop: describe/review                 Desktop: inspect a result
┌──────────────┬────────────────────┐    ┌──────────────┬────────────────────┐
│ New project  │ Project + revision │    │ Projects     │ Project + revision │
│ Projects     │                    │    │             ├────────────┬───────┤
│              │ Idea / questions   │    │             │ Real board │ Part  │
│ Components   │ Proposed plan      │    │ Components  │ + controls │ facts │
│ Home         │ Composer + action  │    │ Home        │            │ Ask   │
└──────────────┴────────────────────┘    └──────────────┴────────────┴───────┘
Mobile: navigation drawer; one content column; board, part facts and controls
remain reachable in normal reading order. No permanently squeezed inspector.
```

### Tokens and components

Begin with existing `styles.css` tokens instead of replacing the palette blindly:
canvas `#030810`, surface `#091424`, raised surface `#101f34`, text `#f4f6fc`,
secondary text `#bfcee2`, action `#55d9ff`. Preserve separate pass/warn/fail/unknown
tokens and status text; brand color must not imply an engineering verdict.
These are current values, not newly certified final combinations.

Keep the existing system font stack for the initial slice. Define a deliberate
relative type scale around the current 18px reading size, body line-height around
1.5–1.6, and a 65–75-character reading measure. System fonts are not inherently
unprofessional. A custom font is optional later, with a license, self-hosted
fallback and measured loading impact.

Use a small spacing scale (4/8/12/16/24/32/48px expressed appropriately in rem),
clear input borders, restrained radii, and consistent focus indicators. This is
an initial design proposal; validate it against real content at enlarged text.

Design reusable **patterns**, not a new JavaScript component framework:
action button, text composer, request/answer block, plan summary, pending state,
recovery message, result badge, disclosure, project item, board toolbar and dialog.
For each, document default/focus/disabled/pending/error states and actual HTML role.
Do not assume Paper has production-ready component-instance semantics.

## 6. Journey and state coverage

Keep current internal stage IDs (`describe`, `agree`, `design`, `review`, `build`)
unless a later separately tested navigation change requires otherwise. Visible
language can be simpler. The matrix below is the design contract, not new API logic.

| Surface/state | Main content and action | Recovery/back behavior | Truth constraint |
|---|---|---|---|
| New project | Obvious labelled composer, three supported examples; Plan my board | Home, projects, guided setup | Do not advertise unsupported circuit families |
| Planning | Preserved request; “Preparing your plan”; busy controls | Back to idea/guided route where existing controller permits | Navigation does not cancel server work or billing |
| Clarification | AI question and answer field; Update my plan | Original request and guided setup remain accessible | No save or build before ready and confirmed |
| Plan ready | Concise features plus suggested assumptions; Generate my board | Change something / detailed settings | Checks have not run; confirm exact reviewed fingerprint |
| Planner unavailable | Request preserved; guided setup and Retry AI planning | Back to idea | Do not show internal exception/provider text or fake success |
| Guided project | Familiar form in same shell; save/review controls | Back to idea or current saved revision | Unsaved edits cannot be treated as the generated revision |
| Saving/starting | Distinct saving versus starting status; guard double submission | Reopen saved project on ambiguous outcome | Do not automatically replay a POST after timeout |
| Build running | Current stage, its explanation, actual progress and revision | Back to project / projects | Back is navigation, not cancellation; no fabricated ETA |
| Connection paused | Existing run retained; Reconnect to this run | Back to project | Reconnect polls; it must not silently create another run |
| Build failed | Fixed reason, available recovery; Retry this revision when valid | Back to project to change choices | Failure has not released fabrication files |
| Server changed | Explain result currency and available recovery | Existing generation-bound recovery | Do not rewrite identity to make stale artifacts downloadable |
| Result ready | Board, readable summary of passed/failed/unknown checks | Back to plan/project; inspect part and ask | Completion is not blanket hardware or manufacturability proof |
| Board unavailable | Textual part list and checks; renderer fallback | View controls and return navigation | Rendering failure does not change verification results |
| Ask/change result | Scoped question, answer/evidence or proposed diff | New question; dismiss proposal | Confirm creates a new revision; does not mutate old evidence |
| Export | Available files and limits; download only when eligible/current | Back to board/project | Use existing release and artifact-current gates |
| Saved projects | Existing server-local list, empty/loading/failure states | New project / refresh / reopen | No login or private-user claim |
| Components/dialogs | Consistent shell, search, model + source limits | Close, Escape, restore trigger focus | Illustrative models and practice layouts remain separate |

“Go back” must retain existing in-memory request/form state wherever the controller
already does. Test browser Back/Forward separately: current hashes cover broad
surfaces, not a durable URL for every project/revision/substep. Do not promise deep
links, full chat persistence or unsaved reload recovery without new implementation.
No redesign may silently add a server-side cancel endpoint or durable browser storage.

Use a skeleton only for content whose shape is already known, such as a project
list. For planning and routing, show a truthful text status. Never animate a
percentage toward success while the server is stalled. Avoid live-region chatter
on each 900ms poll; announce meaningful stage/state changes and errors.

## 7. Paper workflow and versioned handoff

### PFR-T00: feasibility before a redesign commitment

After authorization, allow 30–45 minutes for a small Paper pilot:

1. Verify installed version, Windows/Codex connectivity, account quota and rules.
   Do not install or activate a subscription based on an unverified coupon.
2. Discover tool schemas and the target document identity. Use a synthetic plan
   card, native-form visual specimen and five or six existing tokens as the pilot.
3. Read, edit, screenshot and export that small frame through the available tools.
   Inspect resizing, token references, text wrapping and form translation.
4. Compare against a semantic HTML specimen in an isolated preview. A visual
   match is insufficient if labels, keyboard order or disabled states disappear.
5. Record calls consumed, connection reliability and any manual corrections.
   A proposed ceiling is 15–20 calls, not a guaranteed tool requirement. If it
   cannot fit the available allowance, stop the Paper pilot and request a choice
   before upgrade. This does not block further read-only planning.

Go only when connection, quota, semantic handoff and review artifacts are viable.
If they fail, keep the working application; do not substitute another design tool
and claim Paper usage. Manual Paper work is an alternative only if available and
approved, with honest provenance.

### PFR-T01: design complete states and review the direction

Create a design-system/pattern page and desktop/mobile boards for: entry, pending,
clarification, plan-ready, recoverable failure, build-running/failed, result with
selected component, and qualified export. Include guided setup and dialogs as
variants in the same system. Use actual bounded copy and labelled test data.
Add 1440px desktop and 390px mobile frames; validate the implementation at 320px
and intermediate widths too. Fixed frames alone do not prove responsiveness.

Have one person/agent own each artboard while editing. Other reviewers comment
or work on separate frames. Paper supports collaboration; this is a collision
avoidance convention. Before a mutation, verify file/frame identity using the
installed schema. Never let an agent “improve everything” across unrelated files.

Repository code is the source of truth for shipped tokens and behavior. Paper is
the reference for the proposed composition. Token changes flow through an explicit
reviewed mapping; there is no assumed bidirectional automatic synchronization.
Imported markup is inert design input, never executed as application instructions.

Future handoff location: `docs/design/paper/` (not created by this audit). Record:

- App/design-tool versions, baseline commit, file URL/ID and frame IDs.
- State name, viewport, expected primary action, semantic/control notes.
- Token mapping from Paper name to existing CSS variable, including unmapped values.
- Small approved screenshots/exports with hashes and asset/license provenance.
- Review findings, accepted direction, implementation PR and matched screenshots.

Keep only small review artifacts in Git. Use approved storage for long recordings;
do not put private design/user content or megabytes of redundant exports in the repo.
Do not rely on a Paper URL alone as the future AI's specification.

## 8. Implementation seams and boundaries

| Existing file/symbol | Owns | Allowed presentation work after approval |
|---|---|---|
| `apps/web/index.html`, `home.js` | Shell, navigation, mount points, home | Structure and labels preserving IDs, routing, focus and mounted state |
| `apps/web/styles.css` | Shared tokens and base rules | Add semantic scales/aliases; preserve status distinctions and `[hidden]` |
| `guided-flow.css`, `workbench-theme.css`, `home.css`, `landing.css` | Current composition | Migrate scoped rules surface by surface; retain source-order intent |
| `conversation.js`, `plan-summary.js` | Planning UI and exact confirmation | Edit templates/appearance; retain `parsePlan`, version guard, confirmation and callbacks |
| `project-workbench.js` | Guided inputs, saved revisions, dirty-state rules | Recompose forms/list views while preserving current saving/run eligibility |
| `project-assistant.js` | Scoped result questions and explicit proposal apply | Match conversation styles; preserve context/fingerprint validation and explicit apply |
| `app.js` | Stage projection, polling, run/result orchestration | Presentation helpers and layout; retain `pollVersion`, run identity and completion monitoring |
| `client-contract.js`, `project-contract.js` | API validation and request behavior | Reuse in place. No rewritten copy or parallel client |
| `view-model.js` | Escaping, outcome and release projection | Reuse; never infer pass/download eligibility in templates |
| `board-view.js`, `board-controls.js`, renderer modules | Geometry, interaction and lifecycle | Preserve renderer; style surrounding controls; separately test any new control |
| `component-stories.js/.css`, `visual-explorer.js/.css` | Library and practice surfaces | Later consistency pass; maintain model-status and practice boundaries |

Keep event listeners, input names, `data-*` hooks and native semantics unless a
replacement has direct regression coverage. Do not remount the board during
polling, selection, or inspector updates. Maintain disposal, hidden-view behavior,
reduced motion, fallback rendering and the selected part.

Do not make DOM snapshot tests pass merely by updating expected markup. Test what
the person can do and what the server receives: exact confirmation, no unintended
save/run, stale reply rejection and release eligibility.

### CSS migration policy

Start in existing served files. Inventory tokens and selectors used by the pilot;
record an owner for each migrated pattern. Preserve `.primary`/`.secondary` hooks
where behavior or tests expect them. Use low-specificity scoped rules and semantic
variables; remove obsolete rules only after the affected surface is verified.

Do not add a new layered stylesheet underneath unchanged unlayered CSS and expect
it to win: normal unlayered declarations outrank normal layered declarations. [W1]
Keep the existing cascade initially. A complete `@layer` migration, file
consolidation, build pipeline and utility framework are separate optional tasks.
Do not fight inheritance with escalating `!important` rules.

### Requests, errors and recovery

Reuse `projectRequest`, `parsePlan`, `parseTurn`, `parseProjectEnvelope`, `parseJob`
and existing identity handling. Preserve the 90-second planning/assistant timeout
and current polling cadence in this visual milestone. Fixing legacy timeouts or
adding backoff can be proposed separately, with duplicate-request and late-result tests.

Cancelling a local view only invalidates late responses where currently supported;
it does not prove server cancellation. Retry planning can incur a new model request.
Do not add automatic POST retries, optimistic saving, fabricated chat streaming,
an invented support code, or exposure of raw backend exceptions.

The current app has no user-account authorization boundary. Default CORS is
permissive when `ALLOWED_ORIGINS` is unset; production configuration was not
inspected. Existing job-admission/concurrency bounds are not per-user spend limits.
Frontend disablement is not abuse protection. These are deployment constraints,
not reasons to insert backend security changes into a visual PR.

## 9. Performance, accessibility and deployment gates

### Measure before changing loading

Record cold-load requests, transfer sizes, long tasks, first usable composer and
board interaction on a stated browser/device/network profile. Compare three runs
before/after using the same conditions. Repository file size is only inventory.

The landing iframe is eager. Investigate its cost without assuming `loading=lazy`
solves an above-the-fold embed. If an approved later optimization is needed, a
sized poster with explicit “Explore the demo board” can defer renderer startup.
That changes the experience and needs its own acceptance, focus and fallback tests.

Use LCP ≤2.5s, INP ≤200ms and CLS ≤0.1 as external reference goals, not already
achieved claims. Field thresholds concern the 75th percentile; a lab check does
not establish field INP or real-user performance. [W2] The baseline comparison
must show no material regression before optional visual effects ship.

Avoid extra WebGL shaders in the initial workbench. The board already uses GPU
resources. Any later shader must have a static fallback, motion preference and
visibility handling, bounded pixel density, proper disposal and separate profiling.
No animation may represent actual current flow or engineering checks unless the
underlying projection supports that meaning.

### Accessibility and novice testing

Target WCAG 2.2 AA for the rebuilt surfaces; do not claim whole-product compliance
from unit tests or automated scans. Test these requirements in the browser:

- Real labels and controls; visible focus, logical order, native keyboard operation,
  error association, meaningful headings and status announcements.
- 4.5:1 normal-text contrast; 3:1 for applicable large text and essential UI
  boundaries/focus graphics. Outcome meaning must also appear in text. [W3]
- At least the applicable 24×24 CSS-pixel target/spacing requirement; choose 44×44
  for main touch controls as our usability target, not a claim that AA requires 44. [W4]
- 320 CSS-pixel reflow and 200% text resize/400% browser zoom checks. The spatial
  board/table may require two dimensions, but surrounding controls and explanation
  must reflow without clipped actions. [W5]
- Keyboard selection, camera controls, part-list inspection, Escape, dialog focus
  restoration and drawer behavior. Also test single-pointer alternatives to
  dragging; keyboard support alone does not satisfy that requirement. [W6]
- Sticky composers, headers and drawers must not entirely obscure focused controls;
  our design goal is full visibility. Check this with the mobile keyboard open. [W7]
- Reduced-motion and forced-colors checks, loading/failed WebGL, virtual keyboard
  on mobile, long project names, multi-line questions and large error messages.
- Screen-reader pass on the target Windows browser with NVDA, plus physical touch
  when available. Record unavailable checks rather than declaring them passed.

Run a small uncoached study with three adult newcomers. Ask them to describe a
supported board, identify what the AI assumed, go back and change a choice,
recover from an unavailable planner, inspect a part and explain what a result
does not prove. Record completion, wrong turns and misunderstandings; require no
critical mistake or moderator rescue before claiming improved usability. This is
formative evidence, not statistical proof or a tested claim about fifth graders.

### Static serving and matched deployment

Vercel currently serves `apps/web` with empty install/build commands and rewrites
`/api/*` to Fly. A bare npm import or Tailwind class without generated CSS will
not work just because a dependency was installed.

The initial slice deliberately reuses existing allowlisted filenames. If new
assets/modules become necessary, a manifest/content-type-only change in
`scripts/demo_server.py` must be explicitly included in approved scope. It is a
serving compatibility edit, not permission to change API or engineering behavior.
Do not skip it, serve arbitrary filesystem paths or waive identity checks.

Restart the local backend after asset edits; it serves an immutable startup
snapshot. Where visual source hashes change but pinned vendor files do not, use
`scripts/prepare_visual_assets.py --source-only` and inspect the generated diff.
The command without that flag also recopies vendor files and needs its installed
dependencies. Do not hand-edit identity to suppress failures.

For deployment, verify frontend and backend include the same intended allowlisted
asset revision. Health-token agreement alone cannot prove browser-byte agreement.
Compare deployed static assets/hashes and run an actual compatible flow, then
exercise an old tab across redeploy. Keep the last known-good paired revision for
rollback. Deployment itself remains owner-authorized work, not part of this audit.

## 10. Delivery units, estimates and cut line

The original 6–10 hours is not a reliable estimate for a complete rewrite plus
responsive/accessibility verification. Use the pilot's measured pace to revise
these engineering estimates. Waiting for review/merges and provisioning is additional.

| Proposed unit | Scope and gate | Estimate |
|---|---|---|
| PFR-T00 | Tool/quota/semantic handoff pilot; no upgrade without owner | 30–45 min |
| PFR-T01 | Tokens, pattern sheet, complete state map; review representative desktop/mobile direction | 1.5–2.5 h |
| PFR-T02 | PR: existing shell + composer + clarification + plan + recovery + guided visual continuity | 2–3 h |
| PFR-T03 | PR: activity, result/inspector, assistant and export consistency, retaining renderer and gates | 2–3 h |
| PFR-T04 | Mandatory browser/newcomer QA and evidence; separate fixes PR if findings remain; optional further dialogs/landing polish | 1.5–2.5 h |

Total planning estimate: **7.5–12 hours of focused work**, plus reviews and any
required environment repair. A smaller first slice can fit roughly 4–6 hours;
do not call that a complete frontend redesign. Finishing T02 must leave the old
downstream flow fully working. Cut optional shaders, custom fonts, light mode,
prototype cleanup and framework migration before cutting recovery or test coverage.

The preferred hackathon story is a demonstrably clearer end-to-end experience.
Schedule feature freeze with time for one real demo rehearsal and recovery test.
Do not assume Sentry plus this work automatically fits the weekend.

Sentry and Paper are independent design concerns but overlap in `app.js`,
`index.html`, assets and tests. If both are later approved, give each PR explicit
file ownership; sequence changes to shared files and rebase from merged main.
Do not put observability hooks into arbitrary generated templates. Coordinate
with the proposed Sentry plan without implementing or approving it implicitly.

## 11. Verification matrix and commands

| Gate | Required evidence before marking the implementation verified |
|---|---|
| Contract integrity | Existing validators and exact confirmation preserved; malformed/unknown data never rendered as valid |
| Request races | New project during planning, late replies, repeated confirm, stale identity and dirty revisions do not overwrite current work |
| Recovery | Provider/network failure, timeout, failed save/start, routing/KiCad failure, interrupted job and reconnect paths tested distinctly |
| Result truth | Checks/unknowns/source status remain explicit; sample board cannot masquerade as generated result; stale exports stay unavailable |
| Conversation | Questions remain scoped to the revision; applying a proposal requires confirmation and new checks |
| Renderer | Selection/camera survives UI updates; keyboard/touch alternatives, fallback, reduced motion and disposal tested |
| Visual system | Compared desktop/mobile states, long copy, contrast/focus and intermediate widths; no missing stylesheet/module |
| Real browser | Actual focus/layout/navigation assertions; fake-DOM Node tests alone are insufficient |
| Release | Same intended asset revision on static/backend serving, old-tab recovery, no bad MIME or unresolved imports |
| Demo | Clearly labelled fixture versus live engineering run; no paid call without approval |

Relevant existing tests include `conversation.test.mjs`, `project-workbench.test.mjs`,
`project-assistant.test.mjs`, `entry-page.test.mjs`, `home.test.mjs`,
`board-motion.test.mjs`, `component-stories.test.mjs`, `visual-version.test.mjs`,
and backend UI/static/operability tests. Locate exact current filenames before
editing; keep meaningful coverage, not obsolete markup expectations.

Canonical commands from the implementation worktree (Windows shown):

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
C:\Dev\hackathon\.venv\Scripts\python.exe scripts/ai_state.py validate
C:\Dev\hackathon\.venv\Scripts\python.exe scripts/verify.py workflow
C:\Dev\hackathon\.venv\Scripts\python.exe scripts/verify.py fast
npm.cmd --prefix apps/web test
git diff --check
```

Run Python verification tiers sequentially: they share test temporary paths.
Use the configured virtualenv or equivalent, not an assumed globally installed
Python. Add focused browser checks and existing static-serving tests for changed
assets. Run integration when compatibility/engineering-adjacent changes warrant
it; do not label a fixture or pure Node test a completed native-tool pipeline.

Keep a repeatable local fixture harness for visual states, visibly labelled
**UI test fixture — not engineering evidence**. A successful fixture result may
exercise UI logic but cannot substantiate live verification or release claims.
No public fault-injection endpoint. Save viewport, scenario, actual outcome,
commit and screenshot references in the future design handoff.

## 12. Hackathon and spend questions still open

Official Paper sources support the design workflow; they do not establish the
specific `LAHACKS26` promotion, four-seat entitlement, Paper judging rubric or
prize terms. Verify the sponsor brief before relying on them. A discount or
trial can have renewal terms; owner approval is required before activation.

Event rules permit existing open-source work while evaluating newly added work,
but the public rules include an April deadline inconsistent with the October
event. Obtain organizer clarification and preserve a pre-event baseline. [E1]
Do not claim automatic eligibility because a frontend was rewritten; declare
pre-existing Ohmni features and preparation separately from event work.

Proposed judging evidence: same-task before/after journey, Paper frames/tokens,
one actual agent design edit, the corresponding application screen, keyboard
recovery, and an honest real-or-fixture-labelled board inspection. Record design
decisions and what improved. No unsupported claim that shaders are required to win.

## 13. Sources and independent review

Use exact official docs and repository code ahead of community tutorials or
marketing shorthand. Features/pricing are dated observations, not permanent facts.

- [P1: Paper downloads](https://paper.design/downloads).
- [P2: Paper MCP setup and design-to-code guidance](https://paper.design/docs/mcp).
- [P3: HTML import translation and image handling](https://paper.design/docs/paste/html).
- [P4: Paper's documented multiplayer support](https://paper.design/compare/pencil).
- [P5: Paper build log, including browser WebMCP and desktop tabs](https://paper.design/build-log).
- [P6: Pricing and MCP allowances](https://paper.design/pricing), [subscription terms](https://paper.design/legal/tos).
- [P7: Tokens and roadmap limitations](https://paper.design/docs/tokens).
- [P8: Privacy policy](https://paper.design/legal/privacy).
- [W1: CSS cascade layers](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@layer).
- [W2: Core Web Vitals thresholds and measurement basis](https://web.dev/articles/defining-core-web-vitals-thresholds).
- [W3: Text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
- [W4: Minimum target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
- [W5: Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [resize text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html).
- [W6: Dragging alternatives](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html).
- [W7: Focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).
- [E1: Event rules](https://la-ai-hackathon-2026.devpost.com/rules), [organizer site](https://ai.lahacks.com/).

Review status: independent repository, primary-source and UX/accessibility audits
identified the corrections incorporated above. All three final document reviews
passed with no remaining BLOCKER/HIGH findings. Their clarifications about actual
transcript data, focused controls and visual-manifest regeneration are incorporated.
An additional adversarial review using `gpt-6-astra` at `ultra` reasoning also
passed with no BLOCKER/HIGH findings; its clarification that QA is mandatory
even when a separate fixes PR is unnecessary is incorporated.
These reviews assess this plan only; they do not approve implementation or certify
future accessibility, performance, Paper connectivity or sponsor eligibility.

Documentation audit validation at the baseline above:

| Check | Actual result |
|---|---|
| `ai_state.py validate` | Passed; ledger unchanged |
| `verify.py workflow` | 12 passed |
| `verify.py fast` | 2,439 passed, 86 skipped, 62 deselected |
| Frontend Node suite | 1,088 passed, no failures or skips |
| Local Markdown links, source labels, code fences, diff whitespace | Passed |

Only this plan and its documentation-index link changed. These results establish
the existing code baseline; no Paper-based UI has been implemented or tested.

## 14. Copyable next-agent handoff

> Read `PAPER_FRONTEND_IMPLEMENTATION_PLAN.md`, `AGENTS.md`, `SECURITY.md` and the
> `.ai` ledger. This is a researched proposal, not implementation authorization.
> Check for a later explicit owner instruction. Preserve unrelated work and the
> protected behavior paths; fetch latest origin/main and branch independently.
> Revalidate the actual chat/project controllers and static asset registration.
> Run the small Paper feasibility gate before committing to its design workflow.
> Use public/synthetic content only. Keep existing vanilla JS controllers,
> validators, confirmation/fingerprint rules, renderer and release gates.
> Design complete states; migrate presentation one tested vertical slice at a time.
> Do not delete prototype assets, rewrite fetch/state logic, add a framework,
> activate paid services or assume exported canvas inputs remain accessible forms.
> Verify keyboard, touch, mobile, failures, stale state and browser behavior in
> addition to existing suites. Keep fixture and live claims distinct. Deliver
> reviewable PRs; never merge main. Record remaining limitations and decisions.
