# Ohmni: competitive research and product strategy

**Research date:** September 8, 2026.

**Status:** PROPOSED recommendations, not an approved implementation scope.

**Repository baseline:** `04531cd2dd829e2bd31954362aa97f8094b41caa` on `main`.

This report combines official product documentation, one closely related research
preprint, and inspection of Ohmni's code. Competitor capabilities are documented
claims, not results of hands-on comparative testing. No claim is made about their
market share, learning efficacy, or independent engineering accuracy. Untracked
synthesis work and concurrent workflow changes are not counted as shipped.

## 1. Recommended direction

**Help someone who can code become capable of designing, explaining, and bringing
up their first custom sensor board.** Make each project a sequence of useful
decisions with visible consequences and a physical outcome.

The intended experience is:

**Choose a project → predict → change something → inspect the result → explain
why → build and measure → adapt it for your own use.**

The competitive research suggests that attractive 3D, AI chat, and generated
schematics are increasingly expected capabilities. Ohmni's best opportunity is
the combination of accessible learning, inspectable engineering evidence, and a
completed physical project. This is a positioning hypothesis to test with users;
the research does not establish that no competitor offers that combination.

Start with software-literate hardware beginners and makers moving from modules
to a PCB. Use beginner-readable language throughout. Supporting every novice,
school classroom, and professional engineering team simultaneously would create
conflicting workflows and support requirements.

The existing [product proposal](PRODUCT_V1.md) already identifies this initial
audience and bounded design synthesis. The main proposed additions here are
assessed learning, a working firmware path, and carefully scoped simulation.
Firmware and simulation are explicitly outside that proposal's current envelope;
they need a subsequent product decision before implementation. This report does
not silently revise that contract or approve its milestones.

## 2. Who is building adjacent tools?

### Learning, experimentation, and the transition to hardware

| Tool | Documented experience | Useful lesson for Ohmni |
|---|---|---|
| **Tinkercad Circuits** | Starter circuits, virtual wiring, Arduino/micro:bit activities, block or text code, and simulation. Its teaching guide documents Arduino code export. [Getting started](https://images.tinkercad.com/jl5ii4oqrdmc/1eTWASZYKjnMX9u5ioLh8Y/bb2dfb24cfc4bd66adc485baaecedf97/Tinkercad_Getting_Started_Guide_ISTE.pdf), [teaching guide](https://images.tinkercad.com/jl5ii4oqrdmc/4sMFqe3rDlbUymJt0I4yh/85a4487f7fe274e74c19870ae4679fc1/tinkercad-guides_circuits-Printable.pdf) | Begin with a working example that can immediately be changed. Let unfamiliar symbols arrive alongside recognizable physical objects. |
| **Wokwi** | ESP32 firmware execution, serial output and debugging; a logic analyzer can export VCD traces. Its docs explicitly describe very limited analog simulation. [ESP32 guide](https://docs.wokwi.com/guides/esp32), [logic analyzer](https://docs.wokwi.com/parts/wokwi-logic-analyzer), [analog boundary](https://docs.wokwi.com/chips-api/analog) | Give users observable program behavior. Firmware emulation and electrical validation need separate labels and acceptance criteria. Exact compatibility with Ohmni's sensor/module must be evaluated. |
| **Falstad / CircuitJS** | Editable example circuits with voltage coloring, current animation, waveform scopes, pause/reset, and shareable circuits. The documentation describes numerical and convergence limitations. [Overview](https://falstad.com/circuit/doc/overview.html) | A visual becomes useful when changing a value changes a supported, observable result. A pretty animation without a model is a different kind of illustration. |
| **PhET Circuit Construction Kit: DC** | Build circuits, use meters, switch between lifelike and schematic representations, and reason about relationships and measurements. Its accessible interface includes keyboard controls. [Learning goals](https://phet.colorado.edu/en/simulations/circuit-construction-kit-dc?locale=en), [accessible simulation](https://phet.colorado.edu/sims/html/circuit-construction-kit-dc/latest/circuit-construction-kit-dc_en.html?screens=2) | Ask users to predict and explain. Provide a usable learning path through ordinary controls as well as the canvas. |
| **Fritzing** | Synchronized breadboard, schematic, and PCB views connect prototyping to layout. Its release notes document simulation and manufacturing exports; August 2026 notes include transient-simulation fixes. [Project views](https://fritzing.org/learning/get-started/project-view), [1.0.0 release](https://blog.fritzing.org/2023/06/15/fritzing-1-0-0), [1.0.8 release](https://blog.fritzing.org/2026/08/12/fritzing-1-0-8) | Make the transition between representations continuous. Users should recognize their circuit after switching to a schematic or PCB. |
| **CircuitVerse** | Interactive digital logic, timing diagrams, reusable subcircuits, saved projects, forks, and sharing. [Features](https://docs.circuitverse.org/chapter1/chapter1-keyfeatures/) | A progression of reusable exercises can give people a reason to return and create increasingly complex projects. Its documented digital-logic scope does not establish analog or ESP32 support. |

### AI-assisted design and engineering workflows

| Tool | Documented experience | Useful lesson for Ohmni |
|---|---|---|
| **Cirkit Designer** | Browser wiring, contextual AI help, code generation, Arduino/ESP32/Pico simulation, project sharing, documentation, and browser flashing. Simulation coverage is explicitly per part. [Product](https://www.cirkitdesigner.com/), [simulation support](https://www.cirkitdesigner.com/docs/guides/simulation-support) | This is a close comparator for the beginner embedded-project journey. Close the change/run/observe/build loop. A large part library alone does not establish simulation coverage. |
| **Flux** | Browser schematic/PCB editing, collaboration, manufacturing exports, and AI routing. Auto-Layout supports iteration review, explicit apply, rollback, and protection of existing traces; its docs describe scope and convergence limits. [PCB editor](https://docs.flux.ai/reference/reference-pcb-editor), [Auto-Layout](https://docs.flux.ai/tutorials/auto-layout), [exports](https://docs.flux.ai/reference/data-portability) | Show exactly what an AI proposal changes and let the user review it. Save useful candidates and bound job cost. Older Copilot descriptions should not be used to claim that Flux lacks routing. |
| **Circuit Mind / ACE** | Engineering architecture and constraints become candidate schematics and BOMs, with size/cost/power tradeoffs and analysis reports. [Product](https://www.circuitmind.io/product) | Ask what the board must do and expose meaningful tradeoffs before asking users to choose individual parts. |
| **Quilter** | Starts with an existing schematic and board constraints, automates placement/routing, and returns candidates in native ECAD formats, including KiCad. Its workflow retains engineer review and iteration. [Product and workflow](https://www.quilter.ai/product) | Preserve standard CAD interchange, explicit constraints, and reviewable alternatives. Automated routing does not remove the need for design review. |
| **tscircuit** | React/TypeScript circuit authoring, schematic/PCB/3D previews, reusable packages, Git-oriented visual review, and fabrication/KiCad outputs. Documents a SPICE simulation CLI. [Framework](https://tscircuit.com/), [simulation](https://docs.tscircuit.com/command-line/tsci-simulate) | Reusable, parameterized circuit blocks and understandable revision differences are valuable foundations. Study the architecture without assuming a wholesale migration would improve Ohmni. |

The May 31, 2026 **pcbGPT** preprint is particularly close to Ohmni's technical
thesis: grounded natural-language requirements, component search, datasheet
knowledge, executable circuit descriptions, checking, editable KiCad schematics,
and iterative web interaction. The authors describe reviewable schematic drafts
and retain expert review. It is a research comparator, not evidence of a mature
hosted product. [Primary paper](https://arxiv.org/abs/2606.01188)

My inference from these sources: selling only "AI designs a PCB" provides weak
differentiation. A more useful promise to test is **"Make your first custom board,
understand your choices, and know what to test when it arrives."**

## 3. What Ohmni actually has, and where the experience stops

The existing foundation is substantive: typed circuit intent; 24 deterministic
electrical rules; source-evidence machinery; independent KiCad ERC/DRC; routed
artifacts with lineage; and an interactive PCB explorer with accessible controls.
The [README](../../README.md) accurately distinguishes saved geometry, generated
artifacts, illustrative animation, and physical measurements.

The user-facing pipeline still accepts one pre-authored ESP32/BME280 project.
Users cannot yet express a supported variation, save a personal design, execute
firmware, or observe their physical board through Ohmni. Generated fabrication
files exist, but the interface only downloads the schematic and PCB. Catalog
evidence, supplier information, and manufacturing assumptions have different
levels of support; the existence of the evidence engine must not imply that all
demo catalog facts have been machine-verified. The shipped demo reports no bench
verification; no physical measurements were found in the inspected implementation.

The current tour records exploration, which is correctly labeled. Clicking four
systems is not evidence that someone can explain or modify a circuit. This is
the central educational gap to address.

### Concrete code findings

Line references below describe the inspected baseline. These are static review
findings; no new runtime tests were performed for this report.

| Finding | Evidence | Consequence and required change |
|---|---|---|
| Fixed project and authored layout assumptions | `src/ohmni/application/demo.py:39`, `:176`, `:185`; `apps/web/app.js:281` | Replace the demo-only path with a typed editable archetype and deterministic expansion. Untracked synthesis work is not yet an integrated product capability. |
| Incorrect instructional role inference | `src/ohmni/application/product.py:629`, `:643`, `:665`; saved `apps/web/reference-board.json` | USB-C configuration resistors receive a generic current-limiter explanation; sensor text can include pull-ups as reporting destinations. Derive explicit roles and use reviewed rationale records everywhere. |
| Empty-via manufacturing failure | `src/ohmni/manufacturing/rules.py:23`; `src/ohmni/routing/models.py:118`, `:178` | `min()` over an empty via list raises instead of reporting an appropriate non-applicable result. A valid new board shape can break a fixture-shaped assumption. Add representative expansion cases. |
| In-memory jobs, no restart recovery | `scripts/demo_server.py:170`, `:183`; `apps/web/app.js:49` | Persist project versions, jobs, stage outputs, and artifact references. Distinguish reconnecting to a run from creating another run. |
| No ownership or authorization | `scripts/demo_server.py:39`, `:420`, `:433` | Instance identity binds UI/report generations; artifact hashes guard stale file downloads. Neither authenticates users. Add ownership checks to every project, job, and artifact operation before hosting personal projects. |
| Per-request execution without a durable queue | `scripts/demo_server.py:178`, `:393` | Add admission limits, idempotency, deadlines, cancellation, and recoverable worker leases. Existing router search limits do not supply a complete job lifecycle. |
| Engineering tools share the server OS context | `scripts/demo_server.py:219`; `src/ohmni/eda/kicad/erc.py:44` | Separate API and engineering workers with resource and filesystem isolation. Retain existing subprocess timeouts and `shell=False`. |
| Incomplete downloadable handoff | `scripts/demo_server.py:26`; `apps/web/app.js:969` | Provide a complete manifest-bound release bundle, including required fabrication and assembly information. |
| Seed evidence and synthetic economics | `src/ohmni/catalog/data/parts/BME280.json:143`; `src/ohmni/bom/service.py:25`; `src/ohmni/manufacturing/models.py:28` | Curate source-backed parts and a real fabrication profile. Timestamp supplier data and preserve unknown prices and availability. |
| Production release checks lag the local test suite | `.github/workflows/ci.yml:17`; `pyproject.toml:26`; `scripts/demo_server.py:70` | CI runs the fast gate. Add reproducible real-EDA and browser release checks, operational metrics, and exercised recovery procedures. Existing structured lifecycle logs are useful foundations. |

## 4. Sixteen major improvements, in a useful order

### Product and learning

1. **Make one project truly editable.** Start with the USB sensor archetype:
   curated sensor selection, optional LED, and supported board constraints.
   Confirm a typed brief, derive the circuit, show a before/after comparison,
   and invalidate every dependent artifact after an accepted edit. The user must
   see a meaningful design change, not a text field that still returns the demo.

2. **Deliver a first success within the opening minute.** Lead with a concrete
   outcome such as a room monitor. Offer a short guest exercise with one obvious
   action and a visible explanation. Introduce "PCB" and "schematic" at the point
   they become useful. Save signup for saving work. Test this unaided rather
   than assuming larger typography solved onboarding.

3. **Connect the same circuit across every view.** Selecting a sensor should
   identify its function, schematic symbol, physical package, pins, nets, and
   evidence. Preserve selection when switching views. Add a simple functional
   diagram before a full breadboard editor; synchronized data is the essential
   capability, and another drawing editor is a substantial separate project.

4. **Turn the 3D board into an investigation surface.** Guided actions should
   reveal a real relationship: trace a supply to its regulator, inspect both
   ends of a connection, or locate a future measurement point. Support compare,
   reset, focus, keyboard actions, and reduced motion. Keep topology animation,
   calculated quantities, simulation output, and bench measurements visibly
   distinct. Thermal colors and moving particles require an identified model
   if they are presented as physical results.

5. **Teach through prediction and repair.** Build short exercises around the
   existing golden/broken fixture corpus. Ask what changes when a sensor is on
   the wrong rail, then let users diagnose and repair a constrained variation.
   Offer graduated hints, an explanation, and a different transfer question.
   Store objective-level progress; count successful reasoning, not clicks.

6. **Add a tutor that can demonstrate its answer.** The tutor receives the
   current revision, selected part, checked facts, and lesson objective. It can
   highlight a net, open an evidence span, explain a computed result, or propose
   a typed edit. Review the change before applying it. Missing evidence remains
   missing; fluent prose cannot supply a verdict. An unconstrained chat panel
   would add much less value.

7. **Make explanations technically dependable.** Fix the role-inference bugs
   before adding narration. Create structured records for function, requirement,
   calculation, evidence, limitation, and review status. Reuse them in inspectors,
   lessons, reports, and tutor responses. Have a hardware reviewer check the
   initial curriculum and turn every discovered error into a regression case.

8. **Introduce simulation in separate, tested slices.** First evaluate analog
   blocks with suitable models and known reference results; ngspice is one
   integration candidate with a documented netlist/model/analysis pipeline.
   Separately evaluate supported MCU firmware emulation. Publish a per-part and
   per-peripheral coverage matrix, including assumptions and unsupported
   behavior. Do not promise that a firmware simulator predicts regulator
   behavior, physical damage, or whole-board operation. [ngspice documentation](https://ngspice.sourceforge.io/docs.html)

9. **Complete the firmware and physical bring-up path.** Ship a reviewed
   reference program, pinned build, programming instructions, and live readings
   for the exact supported board. The present USB-C power connector does not
   provide the programming flow; the six-pin header and required adapter need
   an explicit walkthrough. Record measured rails, power consumption, and sensor
   behavior against the exact board/firmware revision. This is a proposed scope
   extension, with build and hardware validation work of its own.

10. **Make the build handoff usable without the authors.** Download one coherent
    bundle: KiCad sources, fabrication files, BOM, supported placement data,
    assembly drawing, manifest, reviewed firmware reference, and bring-up guide.
    Explain assembly difficulty and required tools before ordering. Use a real
    documented fabrication profile and dated purchasable parts; include shipping
    and assembly in cost estimates when available, and name missing amounts.

### Reliability, reuse, and growth

11. **Create a small curated component platform.** Prefer roughly 20–30 useful,
    well-supported parts to thousands of incomplete entries. Version pin maps,
    packages, footprints, source spans, model coverage, and reviewer provenance.
    Test supported combinations and explicit refusals. Bring-your-own-datasheet
    onboarding follows this foundation; it needs ambiguity review and an isolated
    parser, not just a file-upload control.

12. **Let people keep, compare, and reuse their work.** Add durable projects,
    brief revisions, undo/fork, run history, and immutable release snapshots.
    Highlight which requirements, parts, wires, findings, and costs changed.
    Introduce private reviewer links with explicit access control. Broader public
    sharing can follow once attribution, moderation, and support are workable.

13. **Build a reliable hosted execution service.** Use a small API, managed
    identity, PostgreSQL for projects and a durable queue, private artifact
    storage, and isolated engineering workers. Include tenant authorization,
    job budgets, duplicate-submit protection, cancellation, worker recovery,
    and persisted partial results. The existing [deployment proposal](DEPLOYMENT_PLAN.md)
    is a starting point, not an implemented platform or a reason to introduce
    distributed infrastructure prematurely.

14. **Prove that the output satisfies the request.** Implement and extend the
    existing proposed [evaluation plan](EVALUATION_PLAN.md): valid, ambiguous,
    unsupported, and adversarial requests; independent intent review; real EDA
    checks; missing-model/data cases; and multiple physical board designs.
    Include no-via and alternate-package routes. Keep electrical coverage,
    simulation coverage, manufacturing checks, and measured hardware behavior
    separate. Zero DRC errors is not evidence that the board meets its purpose.

15. **Operate it as a service users can depend on.** Pin build environments and
    release artifacts; measure queue time, stage duration, failure/retry rates,
    and cost per successful project. Test restore and rollback. Add dependency
    readiness, useful error reports, data export/deletion, retention policies,
    and dependency/asset license review. Release checks should exercise real
    KiCad and the browser journey, not only unit tests.

16. **Build a reason to return, then test a business.** Offer a connected ladder:
    understand an LED/button circuit, diagnose a sensor board, customize a
    supported project, then bring up a personal revision. Preserve learning and
    project progress together. Test demand through a small maker/university
    pilot before building classrooms or a marketplace. Potential paid value is
    additional projects, dependable build support, or instructor feedback;
    willingness to pay and delivery cost are unvalidated hypotheses.

## 5. Three demonstrations that would make the product memorable

### A. "I changed it, and I understand what happened"

The learner chooses a supported sensor variation. Ohmni previews changed parts
and connections, explains the associated constraint, rebuilds the artifacts,
and preserves the previous revision. A follow-up asks the learner to explain
one consequence without revealing the answer. This requires editable synthesis
and a revision model; it is not supported by today's demo.

### B. "I found and repaired the fault"

Present a controlled faulty circuit from the verifier corpus. The learner makes
a prediction, inspects the relevant net and cited limit, and chooses a repair.
The backend computes the result. After success, a different example checks
transfer. The central interaction is discovering a cause, not watching an
automatic repair replay. Simulation is optional for this initial exercise.

### C. "The real board agrees—or teaches us something new"

Show a physically built board beside its design revision. The app identifies
test points, receives or records measurements, and compares them with declared
expectations and tolerances. Any disagreement becomes a finding and a lesson.
Live data, calculated expectations, and recorded demonstrations carry distinct
labels. Begin with a reviewed reference program and known hardware setup.

These demonstrations connect the current visual work to agency, reasoning, and
physical evidence. Their effectiveness should be judged in user sessions.

## 6. Sequence work by evidence, not feature count

| Stage | Deliverable | Exit evidence |
|---|---|---|
| **1. A deeper hackathon experience** | Correct explanations; one guided fault exercise; linked schematic/PCB/evidence selection; a clear first action. | Five unfamiliar users can state the board's purpose, complete the exercise, explain one check and one limitation, and identify their next action unaided. |
| **2. A personal project** | One editable archetype, version history, typed changes, dependency invalidation, and complete artifact download. | Different supported briefs produce meaningfully different, reviewable circuits. Reload/restart does not lose a project. Invalid or ambiguous inputs are handled explicitly. |
| **3. A working physical reference** | Reviewed BOM/profile, firmware/programming path, assembled boards, and recorded bring-up. Start procurement planning alongside stage 2. | Independent assembly from the exported package; documented measurements, failures, fixes, and limitations. Budget for revision rather than assuming the first spin succeeds. |
| **4. An invited hosted beta** | Durable bounded jobs, ownership checks, isolated workers, reproducible release checks, operational monitoring and recovery. | Tenant isolation tests, failure/restart/cancel/load exercises, successful restore, and a completed representative engineering benchmark. |
| **5. Measured expansion** | Two additional archetypes, evaluated simulation slices, more lessons; educational organization features only if pilot demand supports them. | New projects retain existing reliability and learning outcomes; supported component/model coverage is published. |

No calendar estimate is justified without team size, hardware review capacity,
budget, and access to fabrication/testing. The existing M10–M15 proposals supply
useful engineering structure; refresh their historical assumptions and map the
approved work onto that structure instead of creating a competing milestone
system. A frontend framework migration should have its own demonstrated benefit.

## 7. What "ready" should mean

Distinguish **a reliable hosted beta** from **hardware proven within a stated
test envelope**. Neither establishes unrestricted production electronics design.

Proposed acceptance measures, not current achievements:

- **First-use understanding:** in an initial five-person study, everyone can
  explain the product and next action; observe where they need external help.
  Follow with a larger pilot before generalizing from that small sample.
- **Learning:** compare before/after reasoning, then an unseen transfer task.
  Track hint dependence and delayed recall. Tour completion alone is not a win.
- **Product usefulness:** measure independent project completion, meaningful
  edits, return to a saved project, and successful physical bring-up.
- **Engineering:** preserve the existing proposed 120-request benchmark, add
  coverage for each new archetype/model, and use independent intent review.
  Passing a finite test corpus is an observed result, not a universal guarantee.
- **Operations:** demonstrate two-user isolation, restart recovery, bounded
  concurrency, effective cancellation, restore, and rollback. Establish latency
  and cost budgets from pilot measurements and the existing evaluation targets.
- **Physical evidence:** use the existing proposed three-design validation
  program with multiple boards per design and allowance for a second spin.
  Record all failures, tested conditions, and unmeasured behavior.

For customer discovery, recruit a small cohort of software students or makers
with a real desired sensor project. Observe an unaided session and follow up
after a week. Interview potential instructors separately: learner enthusiasm
does not establish a department's willingness to buy. Do not infer retention,
revenue, or educational effectiveness from competitor feature lists.

The recommended next implementation unit is **one editable sensor project with
a guided diagnostic exercise, trustworthy explanations, saved revisions, and a
complete build handoff**. It reuses Ohmni's strongest existing engineering and
creates a concrete basis for deciding which broader capabilities deserve work.
