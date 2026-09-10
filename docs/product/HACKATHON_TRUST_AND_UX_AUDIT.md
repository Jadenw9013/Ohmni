# Ohmni: code correctness and first-use hackathon audit

Audited baseline: `df41225`. Audit completed 2026-09-05.

This is a recommendation report, not approval to implement a milestone. It complements
`HACKATHON_IMPROVEMENT_AUDIT.md`, which appeared in the shared workspace during this
audit. Concurrent changes to `.ai`, `src/ohmni/synthesis`, and tests are not evaluated
by this report. No product code was changed by this audit.

## Assessment

Ohmni has a substantial deterministic checking and compilation engine and a much
better teaching interface than its older capability audit describes. The five-stage
journey, interactive board, system flows, repair replay, guided tour, grouped checks,
confidence disclosures, and bring-up checklist already exist. Preserve them.

The biggest product gap at the audited baseline is meaningful user agency: the
request, circuit, placement, and demonstrated repair are authored in advance. The
biggest logical gap is that electrical checks do not establish that the circuit
fulfills the brief. The biggest credibility risks are specific holes in evidence
validation and the verified-export gate. The biggest beginner gap is the distance
between downloading a board design and making a device do something useful.

## What was checked

- Read source, tests, architecture, workflow, and proposed product documents.
- Three independent audit tracks covered backend correctness, UX, and delivery.
- `scripts/ai_state.py validate` passed at the baseline; the worktree began clean.
- Canonical `scripts/verify.py fast`: **483 passed, 10 deselected**, after rerunning
  outside the sandbox because pytest could not access its temporary/cache folders.
- KiCad doctor outside the sandbox: **10.0.5 available**. Standalone ngspice unavailable.
- Browser inspection covered entry, brief confirmation, progress, and failure UI.
- A complete real pipeline run on the audit server reached `complete`; its report
  recorded 19 parts, 21 schematic-check notes, no layout problems or missing
  connections, and nine manufacturing files. The completed result was inspected
  through the API after a browser-session interruption.
- Backend findings below include targeted in-memory reproductions. They are not
  claims that every issue is reachable through the current fixed-fixture UI.
- No new hardware was fabricated or measured. No novice user study or full
  integration test suite was performed. Passing tests describe the existing tested
  contract; they do not disprove the reproduced gaps below.

## Correctness fixes to protect the product's core claims

### 1. Make incomplete checks prevent a verified claim

**Confirmed defect.** Removing the BME280 current-limit facts leaves `PB-REG-002`
at `INSUFFICIENT_DATA` and coverage at 95.83%, yet `export_blocked` is false.
The orchestrator promotes an unblocked result to `SEMANTIC_VERIFIED`.

Evidence: [verification.py](../../src/ohmni/domain/verification.py), especially
`export_blocked` at line 246; [orchestrator.py](../../src/ohmni/generation/orchestrator.py),
line 105.

**Fix:** distinguish unresolved artifact export from eligibility to claim verified.
Required checks with insufficient data or execution errors must prevent the latter.
Validate that the required rule set was actually run; an empty report must not
establish completeness.

**Acceptance:** missing-current facts, a throwing rule, and an incomplete report
cannot receive semantic verified status. The UI identifies what is missing.

### 2. Remove evidence authority from model proposal schemas

**Confirmed defect at the provider boundary.** `CircuitProposal` embeds the full
`CircuitIR`, including nested evidence. A fabricated external-source citation with
an invented source ID and `snippet_verified=True` passes proposal and reference
validation and reports `DATASHEET_SUPPORTED` / machine-verified provenance.
The current scripted provider limits exposure; adding a live model would expose
this boundary to untrusted generated content.

Evidence: [models.py](../../src/ohmni/generation/models.py), line 110;
[patches.py](../../src/ohmni/generation/patches.py), line 12.

**Fix:** accept a proposal-only schema with catalog/source identifiers. Resolve
evidence and approved supply facts inside trusted application code. Reject nested
evidence and verification flags at every depth, rather than only top-level fields.

**Acceptance:** adversarial proposals cannot create trusted citations or evidence
statuses through components, external sources, constraints, or other nested objects.

### 3. Verify what a datasheet number means

**Confirmed defect.** For the source text “Recommended operating conditions: VDD
1.71 V to 3.6 V,” a candidate maximum of 1.71 V and a candidate minimum of 3.6 V
both pass candidate verification. Number and rail presence are insufficient to
establish the number's role. This is a candidate-verification result; a later
merge can separately reject a conflict with an existing catalog value.

Evidence: [verify.py](../../src/ohmni/datasheet/verify.py), `_supports`, line 43.

**Fix:** bind the value to its row, rail, minimum/typical/maximum role, units, and
conditions. Retain table structure during normalization. Ambiguous text stays
unknown instead of being upgraded from token presence.

**Acceptance:** swapped bounds, neighboring rail values, mixed operating/absolute
ratings, and unrelated nearby numbers fail semantic support.

### 4. Bind the source document to the exact component

**Confirmed defect.** A matching 3.6 V claim whose document names
`TOTALLY-DIFFERENT-PART` can upgrade BME280 rail evidence, produce zero conflicts,
and replace its datasheet reference.

Evidence: [merge.py](../../src/ohmni/datasheet/merge.py), lines 9 and 87;
[pipeline.py](../../src/ohmni/datasheet/pipeline.py), line 41.

**Fix:** check manufacturer, part number, variant, and applicable revision before
merging. Family documents require an explicit variant mapping. Unknown identity
must remain unresolved.

**Acceptance:** the wrong part's PDF cannot upgrade evidence, even when it contains
the same voltage, pin label, or interface name.

### 5. Check whether the result fulfills the user's brief

**Confirmed defect.** The golden circuit still passes when requirements demand
`MCP1700-3302E` and prohibit `BME280`. Requirements validation checks availability
and contradictions, but does not establish fulfillment by the final circuit.

Evidence: [requirements.py](../../src/ohmni/generation/requirements.py), line 41;
[orchestrator.py](../../src/ohmni/generation/orchestrator.py), line 101.

**Fix:** add a requirement-to-design report with satisfied, violated, and unproven
states. Check parts, interfaces, functional blocks, input limits, assembly
requirements, and the defined budget. Distinguish mandatory constraints from
preferences. Recompute after every repair.

**Acceptance:** “Did it build what I asked?” is a visible checklist, and no mandatory
requirement can disappear behind a green electrical report. Unknown price remains
unknown rather than silently satisfying a budget.

### 6. Check the entire power path

**Confirmed gap.** Setting the golden circuit's external-source current limit to
10 mA still permits export while the regulator check reports a 502 mA load.
`ExternalSource.current_limit` exists but is not consumed by verification.

Evidence: [circuit.py](../../src/ohmni/domain/circuit.py), line 68;
[context.py](../../src/ohmni/verifier/context.py), line 470;
[regulator.py](../../src/ohmni/verifier/rules/regulator.py), line 245.

**Fix:** account for source capacity, regulator capacity, and derived branch loads.
Expose missing transient and thermal data separately. A simple source-to-load
diagram can explain why each limit matters without suggesting that nameplate
current headroom establishes thermal suitability.

**Acceptance:** an explicitly inadequate source is caught; adding LED/resistor
loads changes the power budget; unsupported thermal behavior stays unverified.

## Capabilities and learning that make the demonstration memorable

### 7. Let users make one meaningful design change

**Capability proposal; largest product payoff.** The baseline accepts one example
and replays a circuit and repair. Start with one deterministic USB sensor template
and two supported controls, such as sensor choice and status LED inclusion. Derive
parts and nets from the typed brief. Show the changed circuit, BOM, and checks.

Evidence: [index.html](../../apps/web/index.html), line 48;
[fixtures.py](../../src/ohmni/generation/fixtures.py), line 38;
[demo.py](../../src/ohmni/application/demo.py), line 39.

**Acceptance:** a judge changes a supported input and obtains a different valid
design; identical briefs reproduce identical intent hashes. Natural-language
interpretation can follow the schema fixes and should resolve into these same
bounded controls. Concurrent synthesis work was not reviewed in this audit.

### 8. Make placement and component support match the editable design space

**Capability proposal; prerequisite for broadening item 7.** All current positions
come from a golden coordinate table. Adding catalog JSON alone does not provide
footprint, placement, routing, and manufacturing support.

Evidence: [placement.py](../../src/ohmni/eda/kicad/placement.py), line 12;
[footprints.py](../../src/ohmni/physical/footprints.py), line 1.

**Fix:** build deterministic placement rules for the few offered configurations
and expose only parts whose full path works. Prefer a handful of complete,
testable variants over a large catalog of unusable choices.

**Acceptance:** every selectable combination compiles and either routes within
budget or returns a precise incomplete result. Never imply that the golden board's
clean DRC proves arbitrary placement quality.

### 9. Make first use explain the deliverable and offer a real correction path

**Observed mismatch.** The user selects an example, but Agree says “Straight from
what you wrote” and “go back and say so.” There is no text entry or correction
control. The homepage promises a monitor and manufacturing files; beginners still
need assembly and programming to get readings.

Evidence: [app.js](../../apps/web/app.js), line 264;
[index.html](../../apps/web/index.html), line 32;
[PRODUCT_V1.md](PRODUCT_V1.md), persona discussion around line 132.

**Fix:** lead with “Design a small circuit board, see how it works, and get files
to have it made.” Label example-derived requirements as examples. Use plain-language
editable choices and an immediate preview. State what happens after download and
the tools/assembly difficulty before the user commits to building.

**Acceptance:** in 30 seconds, a new user can say what Ohmni produces, what action
they can take, and whether they are exploring a design or building hardware.

### 10. Link the board, schematic, checks, and source evidence

**UX proposal using existing data.** The component projection has evidence status,
but selected-part rendering does not expose the associated source claims and
checks. Evidence disclosure is concentrated in the repair panel. The schematic
also exposes button-like symbols without matching selection behavior.

Evidence: [product.py](../../src/ohmni/application/product.py), line 721;
[app.js](../../apps/web/app.js), lines 495, 670, and 905;
[schematic-view.js](../../apps/web/schematic-view.js), line 106.

**Fix:** selecting a part anywhere selects it everywhere. Offer four short answers:
what it does, why it was chosen, what was checked, and where the facts came from.
Open the actual source page/excerpt when available; keep catalog-only references
plainly labeled. Make this work with a keyboard and a parts-list alternative.

**Acceptance:** without knowing a reference designator, a newcomer can select
“temperature sensor” and trace its supply limit to its source and check result.

### 11. Turn the existing broken fixtures into a consequence laboratory

**High-impact, bounded proposal.** There are already 13 broken variants and a repair
replay. Let the user choose a few safe virtual faults: wrong sensor rail, missing
pull-up, or missing LED resistor. Show the exact affected circuit, finding cascade,
and before/after values. Use a deliberately limited repair planner or clearly label
authored repair demonstrations; do not imply an arbitrary repair agent exists.

Evidence: [fixtures](../../src/ohmni/fixtures);
[orchestrator.py](../../src/ohmni/generation/orchestrator.py), line 110;
[app.js](../../apps/web/app.js), line 624.

**Acceptance:** three distinct injected faults produce their own actual findings
and explanations. An unsupported repair is explicitly refused. A “predict what
happens” prompt helps users learn through a consequence they can inspect.

### 12. Deliver one usable build package

**Confirmed handoff gap.** The browser lists fabrication outputs but links only
the `.kicad_sch` and `.kicad_pcb`. The server allowlist contains only these two
files. Gerbers and drills cannot be obtained through the advertised browser flow.

Evidence: [app.js](../../apps/web/app.js), line 870;
[demo_server.py](../../scripts/demo_server.py), lines 26 and 251.

**Fix:** add “Download build package” with hash-checked fabrication files, manifest,
KiCad sources, BOM CSV, an assembly map, and a short guide identifying what to open
versus what to send to a fabricator. Include placement export only when actually
supported and validated. KiCad already supports manufacturing export commands;
see the [official KiCad 10 CLI documentation](https://docs.kicad.org/10.0/en/cli/cli.html).

**Acceptance:** a new user obtains the complete validated package entirely from
the page; stale or missing files cannot be packaged as current.

### 13. Make the physical board self-explanatory

**Output gap.** The compiler emits hidden reference/value text on `F.Fab`, pads,
and courtyards; it does not provide the visible component references, pin labels,
and orientation markings a novice assembler needs.

Evidence: [pcb_compiler.py](../../src/ohmni/eda/kicad/pcb_compiler.py), line 169.

**Fix:** add readable references, connector pin labels, polarity and pin-one marks,
board/version labels, and a matching printable assembly drawing. Derive labels
from the actual pin map and check their placement and fabrication clearances.

**Acceptance:** someone can identify components and connector orientation from the
board and assembly guide without the designer explaining it aloud.

### 14. Close the loop from board files to a working room sensor

**Capability proposal; separate scope choice.** Bring-up says “Scan the sensor bus”
and “Read the sensor,” but supplies no executable firmware/flashing path or place
to record measurements. Firmware is explicitly excluded from the proposed v1
contract, so this is a deliberate change to that contract if selected.

Evidence: [product.py](../../src/ohmni/application/product.py), line 1086;
[PRODUCT_V1.md](PRODUCT_V1.md), line 85.

**Fix:** for this one board, provide a tested firmware example tied to its pin map,
programming instructions, expected serial output, and guided measurement capture.
Show a real board's readings and predicted-versus-measured results when available.
Development-board validation must be labeled separately from validation of an
Ohmni-fabricated board.

**Acceptance:** a tester follows the guide to obtain a real sensor reading and
records which hardware was used. If fabrication cannot fit the schedule, show that
remaining step explicitly instead of claiming a physically validated product.

## Reliability and evaluation needed for an unaided demonstration

### 15. Reveal useful results while routing continues

**Interaction gap.** The report is published only after the whole pipeline finishes.
The initial orchestrator call includes semantic checks and schematic ERC while the
page still says it is reading requirements. Routing occupies one opaque call
between 40% and 75%.

Evidence: [demo.py](../../src/ohmni/application/demo.py), lines 174, 190, and 222;
[app.js](../../apps/web/app.js), line 388.

**Fix:** publish immutable stage results and accurate stage events. Let users inspect
the repair and schematic while PCB generation runs. Add elapsed time, bounded job
duration, and cancellation outside the pure deterministic engine.

**Acceptance:** measure time to the first useful engineering result separately from
total run time. A proposed hackathon target is a useful check/repair explanation
within 15 seconds on the actual demo machine; validate before advertising it.

### 16. Recover from temporary connection loss without erasing completed work

**Source-confirmed defect.** One failed health check hides Review and Build. A later
successful check returns true but never restores those sections.

Evidence: [app.js](../../apps/web/app.js), `beginCompletionMonitor`, line 411.

**Fix:** preserve the completed result with a disconnected/freshness indicator.
Disable only actions whose current validity cannot be established. Retry with
backoff, restore on matching identity, and handle a changed server identity
explicitly.

**Acceptance:** one failed poll followed by a healthy response leaves the result
readable and restores eligible actions without a restart or rerun.

### 17. Save runs and bound concurrent work

**Technical gaps.** Jobs live in a process-local dictionary, every start launches a
daemon thread, and the page has no saved project/run URL. Restart loses report
discoverability even when files remain on disk.

Evidence: [demo_server.py](../../scripts/demo_server.py), lines 168–179 and 229;
[app.js](../../apps/web/app.js), state around line 61.

**Fix:** use a small durable local store and a run URL, with interrupted-job status,
recent runs, and artifact retrieval. Add a bounded worker queue and duplicate-start
handling. A hackathon does not require a full accounts platform to get these benefits.

**Acceptance:** refresh mid-run, reopen a completed run, and restart the server
without losing the result. Ten simultaneous starts produce a bounded queue rather
than ten competing routing jobs.

### 18. Explain setup and failures inside the product

**Observed failure experience.** Health advertises ready without checking whether
KiCad can execute. A tool failure becomes generic `pipeline_failed`, drops progress,
and tells the user to inspect a terminal. The sandboxed audit run demonstrated this;
KiCad worked and the full pipeline completed after running outside the sandbox.

Evidence: [demo_server.py](../../scripts/demo_server.py), lines 183, 225, and 414;
[app.js](../../apps/web/app.js), error copy near line 37.

**Fix:** add tool/output-directory preflight, sanitized stage-specific errors,
retained earlier verified outputs, and direct actions such as retrying a failed
stage or opening setup instructions. Preserve sensitive-data sanitization.

**Acceptance:** missing KiCad, an ERC timeout, and a routing failure each explain
what happened, what is still available, and what the user should do next.

### 19. Test the actual first-use promise

**Evaluation gap.** CI runs the fast suite. Existing frontend tests provide useful
coverage, but mocked DOM/source assertions cannot prove the canvas interactions,
downloads, recovery, keyboard experience, or novice comprehension work.

Evidence: [ci.yml](../../.github/workflows/ci.yml), line 8;
[view-model.test.mjs](../../apps/web/tests/view-model.test.mjs), line 93;
[test_demo_ui.py](../../tests/test_demo_ui.py), line 91.

**Fix:** add a dedicated real-browser demo gate with a pinned tool environment and
bounded full pipeline check. Include download, refresh, reconnect, keyboard use,
and a narrow viewport. Ask five people unfamiliar with the project to complete
the flow without narration; record hesitation points and task outcomes.

**Acceptance:** all five can identify what the board does, one check, one limitation,
and the next physical step. Treat this as a proposed usability gate, not as a study
already performed. Report multiple generated configurations separately from
mutations of the one golden circuit.

## Recommended sequence

1. Close the reproduced trust and requirements gaps (1–6), with targeted regression
   tests, before exposing live model output or uploaded component evidence.
2. Make the current demo finish cleanly: package download, recovery, preflight,
   and early results (12, 15–18). These are bounded improvements with immediate value.
3. Build one real interaction loop: bounded editable brief plus compatible placement
   (7–8), or the smaller consequence laboratory (11) if synthesis cannot fit the
   schedule. Use the improved first-use explanation and linked evidence (9–10).
4. Complete the physical handoff and validate with people (13–14, 19). Fabrication
   lead time can run in parallel once an independently reviewed design is suitable.

Do not make a general chat interface, a huge catalog, new MCU families, or a broad
cloud platform prerequisites for the next compelling demonstration. A narrow design
change that produces an inspected artifact is a stronger measurable milestone.

## Proposed unaided first-run journey

1. **Understand:** “Design a small room-sensor board and learn how it works.” Show
   the finished-board preview and explain what the download contains.
2. **Choose:** select an example and change one supported property in plain language.
3. **Confirm:** show a short editable brief, with assumptions visually distinct.
4. **See a consequence:** immediately show an actual check, finding, or repair.
5. **Explore:** select the affected part and follow its function, numbers, and source.
6. **Finish:** offer one build-package download and one next physical action.

The success condition is observable: the user can explain the result and take the
next step without a presenter supplying missing context.
