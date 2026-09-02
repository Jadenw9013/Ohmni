# Ohmni roadmap to closed beta

**Status: every milestone below is PROPOSED.** None is approved. Per
`docs/AI_WORKFLOW.md`, only a human may transition a scope from `PROPOSED` to
`APPROVED`, and approval requires `approved_by: human` plus durable evidence.
This document is a recommendation, not authorisation.

**Owns:** milestone sequencing, prioritisation, what we stop building, and the
product risk assessment.

---

## 1. Sequencing logic

Four dependencies drive the whole order:

1. You cannot design the experience until you know what product you are
   shipping. → contract first.
2. You cannot evaluate generality until designs are actually generated. →
   synthesis before evals.
3. You cannot run a closed beta without persistence, accounts, and isolation. →
   platform before users.
4. **Fabrication has multi-week lead times.** → hardware validation starts in
   parallel, not at the end.

That last one is the main scheduling insight in this document. Waiting until
after M13 to order boards adds four to six weeks of pure calendar time to beta
for no benefit, when a design good enough to fabricate exists at the end of M10.

---

## M9 — Product contract and experience architecture

**Objective.** Make the product legible. Replace the pipeline-shaped demo with a
project-shaped experience over the *existing* single archetype, with no new
engineering capability underneath.

**User value.** A person who is not an electronics engineer can understand what
Ohmni did, what it checked, what it did not check, and what to do next.

**Deliverables.**
- This documentation package accepted as the product contract.
- `apps/web` rebuilt on the five-stage spine (Describe / Agree / Design /
  Review / Build) with the Parts and History drawers.
- Notebook collapsed from 513 raw events to ~12 user-meaningful milestones with
  full drill-down; raw stream retained and exportable.
- Verification ladder rewritten in user-subsystem language; `UNSUPPORTED` rows
  explained rather than merely displayed.
- The four disclosure affordances (`why?` / `evidence` / `show the numbers` /
  `rules`) implemented consistently.
- Rationale record type; the first ~8 authored lessons (one per pipeline stage).
- The two human checkpoints: brief confirmation, fabrication acknowledgement.
- `application` layer reshaped to project / brief / run, still fixture-backed.

**Dependencies.** Completion of the in-flight `M8-REGRESSION-2` scope.

**Non-goals.** Dynamic generation. Accounts. Cloud. Any LLM. New rules.

**Acceptance.** Five people who are not electronics engineers each read a
completed project unaided and correctly state: what the board does, one thing
Ohmni checked, one thing it did not check, and what to do next. Zero unexplained
acronyms above the fold. The Brief is presented as an object, not a magic string.

**Risks.** A rewrite of `apps/web` risks losing the truthfulness invariants
hardened across M8 and its regression scopes - the frontend must keep computing
no verdicts of its own. Mitigation: keep `view-model.js`'s no-verdict discipline
and the existing frontend tests as a hard gate.

**Required before beta.** Yes.

---

## M10 — Deterministic bounded design synthesis

**Objective.** User intent → typed brief → archetype + slots → **derived**
`CircuitIR`, across three archetypes, with the scripted provider removed from
the product path.

**User value.** Ohmni builds *your* board rather than replaying one board.

**Deliverables.**
- `ohmni.synthesis`: archetype templates, slot resolution, and derivation of
  required passives (decoupling, pull-ups, LED resistors, CC resistors, straps)
  **from catalog facts**.
- **A placement engine** replacing the hard-coded coordinate table:
  constraint-driven, deterministic, honouring edge and near-component
  constraints.
- Catalog expansion to ~30 curated parts; footprint set expanded to cover the
  full supported package list. *(Today 8 of 16 catalog package entries cannot be
  PCB-compiled.)*
- Safety-domain classifier plus a deterministic refusal path that produces an
  explanation, not a schema error.
- Router wall-clock budget with a truthful `ROUTING_INCOMPLETE` outcome.
- Brief entry as a **structured typed form** — so M10 is provably correct with
  no model involved.
- Fixture-specific code paths removed from `application` and `cli`.

**Dependencies.** M9 (the brief object must exist).

**Non-goals.** LLM. Cloud. Accounts. User-supplied components. New MCU families.

**Acceptance.** ≥ 90% of the 60 in-envelope benchmark cases reach DRC 0/0 and a
passing manufacturing profile with no human intervention; 100% of the 20
out-of-envelope cases are refused with a specific reason; identical briefs
produce identical `CircuitIR` hashes.

**Risks.** **Placement is the single biggest unbuilt technical risk in the
plan.** Nothing exists; the current DRC 0/0 result rests on 20 hand-tuned
coordinates. Routing success is downstream of placement quality, and a bad
placer will show up as routing failures that look like router bugs. Mitigate by
building the placer against the golden board first (it must reproduce a
routable layout for the known-good case) before generalising.

**Required before beta.** Yes. This is the milestone that turns a demo into a
product.

---

## M11 — Bring-your-own component

**Objective.** The unknown-part workflow becomes a real user flow.

**User value.** "I have this sensor" stops being a dead end.

**Deliverables.** Upload endpoint with size/type limits and isolated parsing;
extractor breadth — **pin tables first**, then packages, rails, absolute maxima,
I2C addresses, decoupling requirements; the ambiguity review screen;
project-scoped catalog overlay (removing the process-wide `lru_cache`);
package → vendored-footprint mapping with provenance; clear refusal for
unsupported packages.

**Dependencies.** M12 (isolation and storage), and the PyMuPDF licensing
decision.

**Non-goals.** OCR. Footprint geometry derived from datasheet drawings. Arbitrary
packages.

**Acceptance.** A hardware-literate tester onboards 10 unseen I2C sensors; ≥ 8
reach a verified design; every extracted claim is either relocated in the source
document or marked `UNKNOWN`; **zero fabricated citations**.

**Risks.** Footprints, not parsing, are the bottleneck. Uploaded documents
concentrate the legal and security exposure.

**Required before beta: NO — and this is a deliberate deviation from the
suggested ordering.** A curated ~30-part catalog can carry a closed beta, while
M11 is where legal and security risk concentrates. If schedule pressure
appears, **this is the milestone to cut**, and beta ships with "tell us what part
you need" as a support channel that also doubles as catalog research.

---

## M12 — Cloud project platform

**Objective.** Multiple users, multiple projects, durable history, safe
execution.

**User value.** Leave, come back, keep your work, compare versions.

**Deliverables.** FastAPI service; PostgreSQL schema (User / Project / Brief /
DesignRun / Artifact / Job / Event); Postgres-backed job queue; **isolated
worker container with pinned KiCad 10.0.5**, non-root, egress-restricted;
S3-compatible content-addressed artifact storage; invite-code + magic-link auth
via a managed provider; retention and deletion; structured logs, error tracking,
and the product-event pipeline. Full specification in
[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md).

**Dependencies.** **The PyMuPDF licensing decision is a hard blocker.** M10 for
something worth persisting.

**Non-goals.** Kubernetes, autoscaling, multi-region, teams, sharing, payments,
public signup.

**Acceptance.** 10 concurrent users; jobs survive a restart; artifacts
retrievable and hash-verifiable; the worker has no inbound network, no metadata
access, and no database credential; p95 runtime within budget; account deletion
removes artifacts from object storage.

**Risks.** Scope creep into infrastructure. The architecture is deliberately
boring; keep it that way.

**Required before beta.** Yes.

---

## M13 — Production model integration and product evaluation

**Objective.** Real natural language in, with the model strictly bounded — and a
*measured* product rather than a passing test suite.

**User value.** Describe a board in your own words.

**Deliverables.** `AnthropicProvider` implementing the existing `LlmProvider`
protocol with structured outputs; prompt registry with versioning; per-call,
per-project and per-user cost caps; model/prompt/token/cost recorded on
`LlmCallRecord`; the 120-case benchmark harness; the blind human intent rubric;
`tests/test_architecture.py` extended to forbid model imports in every
deterministic module added since M9.

**Dependencies.** M10 (something for the model to fill in), M12 (secrets and
isolation).

**Non-goals.** Model-emitted netlists. Model-authored evidence. Fine-tuning.
Agentic multi-turn design loops.

**Acceptance.** Every threshold in [EVALUATION_PLAN.md](EVALUATION_PLAN.md) §3,
including 100% out-of-envelope recall and a median intent-satisfaction score
≥ 4.0.

**Risks.** Interpretation quality is the whole milestone; if archetype selection
is unreliable, the fallback is the structured brief form from M10, which is why
M10 deliberately does not depend on a model.

**Required before beta.** Yes.

---

## M14 — Physical hardware validation *(starts in parallel with M12)*

**Objective.** Hardware decides.

**User value.** Every claim Ohmni makes becomes something that has been checked
against reality at least once.

**Deliverables.** A real provenance-bearing `ManufacturingProfile` from the
chosen fabricator; 3 designs × 5 boards, budgeted for 2 spins; assembly;
the recorded bring-up sequence; the **predicted-vs-measured table**; the defect
log; new rules and fixtures for every rule gap found.

**Dependencies.** M10 for designs worth building. **Not** M12 or M13 — the
boards can be ordered from M10 output while the platform is being built.

**Non-goals.** Automated bench instrumentation. Environmental or compliance
testing. Long-term reliability.

**Acceptance.** ≥ 1 design functional on first spin; ≥ 80% first-spin functional
yield; every `CALCULATED` prediction within its stated tolerance or a recorded
rule gap; every defect root-caused.

**Risks.** Lead times. A first spin that fails costs weeks — hence two spins in
the budget from the start.

**Required before beta.** **Yes — this is the gate on every reliability claim.**

---

## M15 — Closed beta

**Objective.** 25-50 invited users building real boards.

**Deliverables.** Invite flow and onboarding; in-product feedback capture; a
support loop; terms of service and privacy policy; status page; on-call runbook;
weekly metric review.

**Dependencies.** M9, M10, M12, M13, M14. (M11 explicitly optional.)

**Non-goals.** Public signup. Payments. Growth marketing.

**Acceptance.** Activation ≥ 60%; completion ≥ 40%; **zero safety-domain
escapes**; **zero fabricated-evidence reports**; ≥ 5 boards externally
fabricated and reported by users.

---

## 2. Prioritisation

Ruthless by design. Technical impressiveness is not a criterion.

### P0 — deployment blockers

Cannot host anything without resolving these.

1. **PyMuPDF AGPL-3.0 licensing decision.** Cheap now, expensive after M12.
2. **No persistence.** Jobs are a dict in one process; a restart loses work.
3. **No accounts or authorisation.**
4. **No worker isolation.** Subprocess execution and (later) untrusted PDF
   parsing happen in the web server's own context.
5. **No upload boundary.** No endpoint means no limits, no type checks, no
   sandbox.
6. **No safety refusal path.** `safety_domains` is never populated by any code
   path; the scope gate reduces to a Pydantic `le=12`.
7. **One hard-coded request string.** There is no product without this.
8. **No terms of service, privacy policy, or retention policy.**

### P1 — required for beta

9. Deterministic synthesis for three archetypes.
10. **The placement engine.** The largest unbuilt technical risk.
11. Catalog to ~30 parts and the full supported footprint set.
12. Production model provider, bounded to interpretation and proposals.
13. The 120-case benchmark and its thresholds, including the human rubric.
14. Notebook collapse, rationale records, and ~32 authored lessons.
15. Router time budget and truthful incomplete outcome.
16. A real manufacturing profile from the chosen fabricator.
17. Hardware first spin with the predicted-vs-measured table.
18. Product analytics.
19. Part availability and lifecycle curation (**not** live pricing).

### P2 — valuable shortly after beta

20. Bring-your-own-component workflow (M11).
21. One supplier adapter for real pricing and stock.
22. Version comparison UI.
23. SPICE DC operating point (spike S2).
24. A fourth archetype; RP2040 support.
25. Project sharing and export.

### P3 — future

26. 4-layer boards, buck converters, LiPo charging (needs a safety review),
    RF layout.
27. Bench instrument automation.
28. Firmware generation.
29. Community-contributed catalog entries.
30. Teams and collaboration.

## 3. What we should deliberately stop building

Each of these is genuinely good work. That is why they need to be named
explicitly — good work is the hardest kind to stop.

**Stop hardening the local demo server.** The last twenty commits include six
distinct M8 review-and-remediation cycles, and the current in-flight scope
`M8-REGRESSION-2` is the second post-milestone regression on a **single-user
local demo that M9 replaces**. The invariants it produced are real and belong in
`SECURITY.md`; the surface they protect is being retired. *Recommendation:
finish `M8-RG02`, take the one required focused review, and stop.*

**Stop adding verification rules.** Twenty-four rules already exceed the design
capability that feeds them — there is one board to check. New rules should come
from **M14 bench findings**, which is the only source that can teach the verifier
something the fixtures could not.

**Stop pursuing simulation (spike S2).** Decision 6 is sound reasoning, and the
DC-operating-point choice is right. But its stated purpose is to corroborate
arithmetic we already trust, and no user is blocked by its absence. Post-beta.

**Stop planning live supplier pricing.** Synthetic pricing is clearly labelled
and nobody's decision changes because a resistor is $0.05. Availability
curation, which is P1, delivers most of the value at a fraction of the cost.

**Stop expanding fabrication output formats.** Gerbers, drill, job file, and an
integrity manifest are enough to order a board.

**Stop further independent-review rounds on M8.** It completed at `3a6f9d3` with
a passing bounded independent review. Additional review of a retired surface has
negative expected value.

**Do not start** 4-layer support, high-speed or RF work, additional MCU
families, firmware generation, or bench automation.

## 4. Product SWOT

Grounded in [CAPABILITY_AUDIT.md](CAPABILITY_AUDIT.md).

### Strengths

- **The evidence type system.** Three separate types; claim status *derived*
  from evidence with no setter; a citation that fails relocation supports
  nothing. This is rare and hard to copy, because copying it means giving up the
  ability to assert.
- **Five rule outcomes with reported coverage and per-rule limitations.** "I had
  no data" is distinguishable from "I checked and it is fine."
- **Voltage derived from drivers**, with a test proving a rename changes nothing.
- **End-to-end fingerprinted lineage** that makes a release `STALE` automatically.
- **Real KiCad 10 ERC and DRC closure** at 0 violations / 0 unrouted on a routed
  board — independently corroborating, not replacing, Ohmni's own checks.
- **Architecture tests that parse imports** to enforce the trust boundary.
- 465 passing tests; a 14-fixture corpus at 100% coverage.
- **A UI that says `NOT_YET_VERIFIED`** when that is the truth.

### Weaknesses

- **No design synthesis.** The generation path is a four-payload replay.
- 9 parts; 8 footprints; 8 of 16 catalog package entries not PCB-compilable.
- One board; one lesson; one accepted request string.
- No persistence, accounts, cloud, or model.
- Synthetic pricing; synthetic manufacturing profile.
- No hardware has ever been built.
- Routing takes ~60 s of a ~75 s run, with no budget.
- The product surface is shaped like the pipeline.

### Opportunities

- **Software engineers entering hardware** are numerous, underserved, and
  already fluent in every concept Ohmni is built on.
- **"A type checker for circuits"** is a framing nobody else owns, and it is
  accurate rather than aspirational.
- The **predicted-vs-measured table** from M14 would be genuinely credible
  content that competitors cannot cheaply fake.
- Education and institutional channels (courses, clubs, workshops) map naturally
  onto the archetype model.
- The evidence layer is a moat **if** it is paired with a generator people
  actually use.

### Threats

- **Flux, CELUS, Circuit Mind, Quilter**, and fast-moving open EDA research.
- **A competitor can bolt a verifier onto a working generator faster than we can
  bolt a generator onto a verifier.** This is the strategic threat, and it is why
  M10 is urgent.
- Users over-trusting output, building a dead board, and blaming Ohmni.
- Hardware liability.
- The component universe is unbounded; every user arrives with a part we lack.
- AGPL and library licensing.
- Model cost per project if the interaction becomes chatty.

## 5. The six risks that matter most

| Risk | Why | Mitigation |
|---|---|---|
| **Technical: placement** | Nothing exists. Routing and DRC success are downstream of it, and today's clean DRC rests on 20 hand-tuned coordinates. | Build the placer against the golden board first; it must reproduce a routable layout for the known-good case before generalising. |
| **UX: the AGREE gate** | Too heavy and beginners bounce; skippable and every downstream honesty mechanism becomes decoration. | Default to a short, scannable brief; make assumptions the visually prominent element; measure `brief_confirmed` conversion as a first-class metric. |
| **Trust: a verified board that does not work** | Nothing in the current system could detect it. | The blind human intent rubric, and M14. Both exist for this single failure. |
| **Market: the output is worse than a Google search** | For an ESP32 + BME280 logger, Adafruit already sells one. | Win on *your variant* plus understanding, not on the canonical board. Never position Ohmni against boards that already exist. |
| **Deployment: AGPL plus untrusted-file execution** | Both gate hosting. Neither is solved by writing code. | Decide the PyMuPDF path now; isolate the worker in M12 regardless. |
| **Scope creep: the catalog** | Every user says "add my part". There is no natural stopping point. | The supported-package-set rule, and the archetype envelope, are the defences. Refuse clearly and count the refusals. |
