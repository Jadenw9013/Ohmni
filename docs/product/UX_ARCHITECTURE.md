# Ohmni user journey and experience architecture

**Status:** PROPOSED. No milestone is approved by this document.
**Owns:** the user journey, information architecture, disclosure strategy,
interaction model, component-onboarding experience, and the learning product.
**Assumes:** the contract and envelope in [PRODUCT_V1.md](PRODUCT_V1.md).

---

## 1. The problem this document solves

The current experience is organised around the engineering pipeline. The
audit records the symptoms: a nav rail reading Overview / Repair / Evidence /
Notebook / Artifacts / BOM & cost / Release; a 17-row verification ladder whose
first eight rows are `Ohmni semantic verification - <subsystem>` with identical
detail text; a 513-event flat timeline; one lesson; and a read-only textarea
holding the only request the system accepts.

Everything in it is *true*. Almost none of it is *addressed to anyone*.

The fix is not to hide the engineering. The engineering is the product. The fix
is to make the engineering arrive **as an answer to a question the user is
actually asking at that moment**.

## 2. The journey

The suggested eight stages (IDEA / UNDERSTAND / PLAN / RESEARCH / DESIGN /
CHECK / BUILD / NEXT STEPS) mix user goals with Ohmni's internal phases. PLAN and
RESEARCH are things Ohmni does, not things the user is trying to accomplish, and
eight stages is more progress bar than anyone will read.

**Recommended: five stages, plus Learn as a layer rather than a stage.**

```
   DESCRIBE  ->  AGREE  ->  DESIGN  ->  REVIEW  ->  BUILD
       \___________\__________\__________\___________/
                        Learn (everywhere)
```

Learn is deliberately not a stage. A stage called "Learn" is a stage that gets
skipped. Learning has to happen where the decision happens.

---

### Stage 1 - DESCRIBE

**User goal:** "Say what I want without being made to feel stupid."

**Ohmni does:** accepts free text. Interprets it into a typed `Brief`. Runs the
deterministic envelope and safety gate *before* showing anything encouraging.

**User sees:** one text box and three example requests that are inside the
envelope. Nothing else. No pipeline, no jargon, no progress bar.

**User can change:** everything; nothing is committed yet.

**User learns:** by example - what kind of thing Ohmni builds, from the examples
rather than from a scope document.

**Checkpoint:** none.

**Failure modes and how they are communicated:**

| Failure | Response |
|---|---|
| Outside the envelope (mains, LiPo charging, motor drive, > 12 V, RF, medical) | **Refuse immediately, before any design work.** Name the specific reason, name what Ohmni *does* cover, and offer the nearest supported project. Never a generic error. |
| Too vague to interpret | Ask up to three specific questions. Never guess a safety-relevant field. |
| Names a part Ohmni does not have | Offer the closest catalog part with the difference stated, or (from M11) offer to ingest a datasheet. |
| Model interpretation fails schema validation twice | Fall back to the structured brief form. Never fall back to free text. |

---

### Stage 2 - AGREE **(the load-bearing stage)**

**User goal:** "Check that it understood me."

**Ohmni does:** presents the `Brief` as an editable structured document -
requirements with provenance chips, chosen archetype, filled slots, and a
separate, prominent list of **assumptions it made on your behalf**.

**User sees:**

```
  Your board                                        [edit]
  ──────────────────────────────────────────────────────────
  Reads   temperature, humidity, pressure   BME280   you said this
  Powered by  USB-C, 5 V                             you said this
  Runs at     3.3 V                                  Ohmni chose this  why?
  Shows       one status LED                         you said this
  Size        up to 100 x 70 mm, 2 layers            default          why?

  Ohmni assumed 2 things                             review
  ──────────────────────────────────────────────────────────
  · USB-C is used as a 5 V sink, without Power Delivery.
  · You will program the board over the 6-pin header, not over USB.
```

**User can change:** every field, by editing or by saying what to change.
Assumptions can be accepted individually or overridden.

**User learns:** the vocabulary of their own project, attached to their own
words. This is the highest-leverage teaching moment in the product, because the
user is motivated and the content is about *their* board.

**Checkpoint: MANDATORY.** Nothing is designed until the user confirms. This is
one of only two blocking gates in v1.

Why this stage is worth its cost: it is where trust is either earned or lost.
Every downstream honesty mechanism - provenance, coverage, `UNKNOWN` - is
worthless if the user never believed the input was right. It is also the cheapest
place to catch a misunderstanding: seconds here versus 75 seconds of pipeline and
a wrong board.

**Failure modes:** contradictory requirements (state both, ask which wins);
a requested change that would leave the envelope (refuse, with reason).

---

### Stage 3 - DESIGN

**User goal:** "Do the thing. Tell me if something goes wrong."

**Ohmni does:** synthesises `CircuitIR`, verifies, repairs, compiles the
schematic, runs ERC, places, routes, runs DRC, checks manufacturing, builds the
release.

**User sees:** eight named steps in the user's language, not the subsystem's:

| Internal stage | What the user reads |
|---|---|
| synthesis | Choosing parts and wiring them up |
| semantic verification | Checking the electrical design |
| repair | Fixing a problem it found |
| schematic + ERC | Drawing the schematic, then checking it with KiCad |
| placement | Arranging parts on the board |
| routing | Drawing the copper connections |
| DRC | Checking the board with KiCad |
| manufacturing + release | Checking it can be made, packaging the files |

Live, and **the repair is shown, not hidden.** When the verifier catches
something, the user sees: what was wrong, why it mattered, what Ohmni changed,
and that it re-checked. That moment is the single best demonstration of the
product's thesis, and the current demo is right to feature it.

**User can change:** nothing mid-run; they can cancel.

**User learns:** that checking is a separate act from designing, and that
somebody else's tool (KiCad) agreed.

**Checkpoint:** none. Runs to completion or to a named failure.

**Failure modes:** synthesis cannot satisfy the brief (say which requirement and
why); repair budget exhausted (show the remaining blocking findings in plain
language, offer specific brief changes); routing exceeds its time budget
(**report `ROUTING_INCOMPLETE`, never a silent pass or an unbounded wait**); DRC
violations (report as-is; do not paper over disagreement with Ohmni's own
result); KiCad unavailable (`UNSUPPORTED`, never an empty pass).

---

### Stage 4 - REVIEW

**User goal:** "Is this good? What don't I know? What should I change?"

**Ohmni does:** presents the result as an argument with a stated confidence,
not a wall of statuses.

**User sees**, in this order:

1. **The board.** A rendered schematic and PCB, large, first. It is the thing
   they asked for.
2. **What it does**, in three sentences derived from the brief.
3. **What Ohmni checked and what it found** - collapsed to one line per
   *subsystem the user can name* (power, connections, the I2C bus, the LED, the
   layout, manufacturability), each expandable to the rules underneath.
4. **What Ohmni could not check** - a first-class section, not a footnote:
   decoupling *placement*, thermal, EMC, signal integrity, simulation, and above
   all **bench behaviour**. Phrased as "here is what only hardware can settle."
5. **What it costs and how hard it is to build** - with price knowledge and the
   assembly difficulty of each package, including the reflow-recommended LGA.
6. **What to change** - concrete, offered edits that lead back to Stage 2.

**User can change:** the brief (returns to Stage 2, creating a new version), or
individual slots directly ("use a different sensor").

**User learns:** the difference between *verified*, *assumed*, and *unknown* -
by seeing all three about their own board on one screen.

**Checkpoint:** none, but the fabrication download is gated (Stage 5).

---

### Stage 5 - BUILD

**User goal:** "Get a real board."

**Ohmni does:** packages fabrication outputs with their integrity manifest and
explains what happens next.

**User sees:** the download; a plain-language ordering guide (what a fab house
needs, what the settings mean, roughly what it costs); a BOM with quantities
that account for MOQ; an assembly-order suggestion; and a **bring-up checklist
carrying Ohmni's own predictions** ("the 3.3 V rail should read about 3.3 V; the
LED should draw about 4.7 mA; the sensor should answer at address 0x76").

That last item is the product's best idea and it costs almost nothing: every one
of those numbers already exists as `CALCULATED` evidence. Turning them into a
checklist converts Ohmni from a generator into a thing the user *measures
against*, which is how "hardware decides" becomes real for one person at their
own desk.

**Checkpoint: MANDATORY.** Before the first fabrication download, an explicit
acknowledgement: this design has not been physically tested; Ohmni checked A, B,
C and did not check D, E, F; you are responsible for reviewing it. Shown once
per project, recorded, never a dark pattern, never dismissible by accident.

**Failure modes:** release is `STALE` because the brief changed
(**block the download**, explain, offer to re-run); manufacturing profile
findings (list them; the profile is synthetic in v1 and must say so).

---

### Learn (everywhere)

Covered in §7.

---

## 3. Information architecture

Ohmni's subsystems are not the user's nav. The mapping is deliberate.

**Top level (4 items):**

```
  Projects      the default landing surface once you have one
  New project   the DESCRIBE box, one field
  Learn         glossary + the lessons you have unlocked
  Account       settings, data, deletion
```

**Project workspace** - one vertical spine matching the journey, with two
drawers that are always reachable but never primary:

```
  ┌ Brief ──────────── what you asked for, and what Ohmni assumed
  ├ Design ─────────── the run: what happened, what it fixed
  ├ Checks ─────────── what was verified, what was not, what is unknown
  ├ Board ──────────── schematic + PCB, downloadable
  └ Build ─────────── order it, assemble it, bring it up

  drawers:  Parts        every component, its evidence, its alternatives
            History      brief versions, previous runs, compare, notebook
```

**What is deliberately *not* top-level nav, and why:**

- **ERC and DRC** are not destinations. They are *second opinions* that appear
  inside Checks, labelled as "KiCad checked this too, independently."
- **Engineering Notebook** is not a stage. It is the History drawer's deepest
  layer - the audit trail, not the narrative. The narrative lives in Design.
- **Schematic and PCB** are not separate pages. They are both "the board".
- **BOM and cost** live under Build, because that is when they matter.
- **Requirements** is not separate from Brief. One object, one place.
- **Evidence** is not a page. It is an expansion available on any claim.
  A page called Evidence guarantees nobody visits it.

**Collapsing the notebook.** 513 events cannot be a timeline. Group by the eight
Design steps, show one summary line per step with a count, and expand on demand.
The 204 `pad_binding_resolved` events become "38 components, 204 pads bound" -
one line, still fully inspectable. Keep the raw stream available and exportable;
it is real evidence and P3 users will want it.

## 4. Beginner versus advanced

**Recommendation: progressive disclosure. No modes.**

The tradeoff, honestly:

| | Explicit modes | Progressive disclosure |
|---|---|---|
| Beginner sees less | Yes, immediately | Yes, by default |
| Cost | Two products to design, build, test, screenshot, and support | One |
| Self-classification | The user must decide before they know anything; beginners pick "advanced" for pride and are lost, experts pick "beginner" to be safe and are annoyed | Never asked |
| Discovery of depth | A mode switch is a cliff | Each expansion teaches the next one |
| Failure mode | Detail that exists but is unreachable in the mode you are in | A page that grows long if everything is expanded |

Disclosure is **per object**, and there are exactly four affordances, used
consistently everywhere:

- **`why?`** - the rationale record (§7).
- **`evidence`** - the citation: document, page, verbatim snippet, and its
  machine-verification status.
- **`show the numbers`** - the arithmetic, with units and worst-case basis.
- **`rules`** - the specific rule IDs, outcomes, and limitations.

One persisted preference, not a mode: *"expand engineering detail by default."*
It changes initial state only; it never changes what exists. A returning P3 user
flips it once; a P1 user never finds it and never needs to.

**Non-negotiable:** the fabrication acknowledgement (Stage 5) and every
`UNKNOWN` / `NOT_VERIFIED` / `UNSUPPORTED` status are visible at every
disclosure level. Honesty is not a detail level.

## 5. Interaction model

**Recommendation: a structured document with scoped conversation. Not a chat
box.**

A chat box as the primary surface would be wrong here for a specific reason:
the project has *state* - a brief, a design, artifacts, a lineage - and chat
transcripts are a bad representation of state. The user needs to see what the
board *currently is*, not scroll back to find out.

The model:

- **The Brief is the document.** Typed fields with provenance. Directly
  editable. It is the single source of intent, and the design is a consequence
  of it.
- **Conversation is scoped to an object.** You can talk to the brief, to a
  check, to a part, to the board. There is no global chat.
- **Every model turn returns a typed proposed change, rendered as a diff.**
  Never prose that silently mutates state.

```
  you: use an easier-to-solder sensor

  Ohmni proposes 1 change to your brief
  ──────────────────────────────────────────────────────
  Sensor   BME280 (LGA-8, needs reflow or hot air)
        →  SHT40  (DFN-4, still needs hot air)
        →  BME280 on a breakout board (through-hole, easy)   ← suggested

  This changes: the I2C address (0x76 → 0x44 for SHT40),
  the pressure reading (SHT40 does not measure pressure),
  and re-runs every check.

                                     [ accept ]  [ keep BME280 ]
```

How the named example utterances resolve:

| The user says | v1 behaviour |
|---|---|
| "make it smaller" | Typed change to the board-outline constraint. Re-places and re-routes. May legitimately fail routing - and says so. |
| "use an easier-to-solder sensor" | Slot swap, filtered by `AssemblyDifficulty`, with the functional differences stated up front. |
| "remove the LED" | Slot removal. Removes the LED, its resistor, and the `PB-LED-001` result. |
| "move USB-C to the left" | **Explicitly unsupported in v1.** There is no placement authoring surface, and pretending otherwise is worse than refusing. Response: "I can't place parts by hand yet. USB-C is always on a board edge; I can tell you which edge it's on." |
| "why did you pick that regulator?" | Not a change. Returns the rationale record. |
| "is this safe to plug into the wall?" | Refusal plus explanation. Mains is outside the envelope, permanently. |

**Re-verification on change.** This is where the existing engineering pays off.
A brief edit creates a new `Brief` version; the fingerprint chain already
determines exactly which downstream stages are invalid. The user sees:

```
  You changed: sensor
  Still valid:  nothing downstream
  Will re-run:  synthesis → checks → schematic → ERC → placement
                → routing → DRC → manufacturing → release
  Roughly 80 seconds.
```

For a change that only affects, say, the manufacturing profile, only the tail
re-runs. Showing the invalidation set is itself a lesson in how the system works.

**When Ohmni must stop and ask, rather than decide:**

1. Any `SafetyDomain` is detected. Always. No exceptions.
2. A requirement the user stated explicitly would have to be violated.
3. The request is ambiguous in a way that changes the parts chosen.
4. More than one archetype satisfies the request.
5. A named component is unknown.
6. The repair budget is exhausted with blocking findings remaining.
7. Anything irreversible or outward-facing: fabrication download, deletion,
   sharing.

**When Ohmni must decide and merely report:** every derived passive value, every
placement, every route, every rule outcome. Asking the user about a decoupling
capacitor value is not respect; it is abdication.

## 6. Component onboarding

The proposed flow is right, and roughly 60% of it exists as library code. What
is missing is mostly *product*, plus one genuinely hard engineering problem.

```
  user names an unknown part
    → Ohmni: "I don't know that one. Do you have its datasheet?"
    → upload (PDF, <= 25 MB, parsed in an isolated worker)
    → deterministic extraction of candidate facts
    → EVERY candidate independently relocated in the source document
    → facts that relocate → DATASHEET_SUPPORTED
      facts that do not   → UNKNOWN  (a failed citation supports nothing)
    → ambiguity review: the user confirms only what the machine could not settle
    → package check against the supported set
    → part becomes available TO THIS PROJECT
```

**What exists:** the entire verification half. `datasheet/pdf.py` parses,
`extract.py` produces candidates, `verify.py` relocates them in the source and
checks semantic support, `merge.py` applies verified claims with conflict
detection, and a citation that cannot be found downgrades the claim to
`UNKNOWN`. This is the hard, correct part, and it is done.

**What is missing, in order of difficulty:**

1. **Footprint acquisition - the real bottleneck.** A part can have a perfectly
   verified datasheet and still be unusable, because the PCB compiler needs pad
   geometry and there are 8 footprints. Today 8 of 16 catalog package entries
   cannot be PCB-compiled at all. **Datasheet parsing is not the hard part of
   bring-your-own-component; footprints are.**
   *Recommendation:* do not attempt to derive pad geometry from datasheet
   drawings. Restrict user-supplied parts to the supported package set and map
   each package to a vendored, SHA-256-pinned subset of the KiCad footprint
   libraries, extending the provenance model already described in
   `docs/THIRD_PARTY.md`. A part in an unsupported package is refused clearly:
   "I can read this datasheet, but I don't have a verified footprint for a
   QFN-24. Supported packages are: ..."
2. **Extraction breadth.** The current extractor recognises a small regex
   vocabulary and produces no `PIN` facts at all - so no user-supplied part can
   currently be wired. Pin tables are the priority; then packages, rails,
   absolute maxima, I2C addresses, decoupling requirements.
3. **Upload as a product surface:** endpoint, size and type limits, isolated
   parse, storage, retention, deletion. Security requirements in
   [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md).
4. **The ambiguity review screen.** Show only what the machine could not settle.
   If it settled everything, do not make the user confirm anything - that is the
   whole point of machine verification.
5. **Project-scoped catalog overlay.** The catalog is a process-wide
   `lru_cache` today. A user's part must not leak into another user's project.
6. **Scanned PDFs** report unsupported. Keep it that way; do not add OCR.

## 7. The learning product

One hard-coded lesson is not a learning product. But the raw material is
already generated on every run - findings, rule limitations, evidence,
calculated values, decisions - and none of it is authored into anything a person
would read.

### The rationale record

Every decision and every finding carries the same five fields, generated from
typed inputs. Never model chain-of-thought; never free-form narration.

```
  What is this?      Decoupling capacitor
  Why does it matter? A chip's current demand changes faster than the power
                      supply can respond. A small capacitor next to the pin
                      supplies that instant demand locally.
  What did Ohmni do?  Placed a 100 nF capacitor between each of the ESP32's
                      3.3 V pins and ground - C3 and C4.
  Evidence            ESP32-WROOM-32E datasheet, p.12: "100 nF"
                      CATALOG_REPORTED - hand-entered, page recorded,
                      snippet not machine-verified
  What should I take
  away?               Ohmni proved these capacitors EXIST. It cannot prove
                      they are within 2 mm of the pin - and distance is what
                      makes decoupling work. That is checked at layout, and
                      it passed: 1.4 mm.
```

That last field is the one that makes Ohmni a mentor rather than a generator,
and it comes straight from `RuleResult.limitations`, which already exists.

### Content plan

**One authored lesson per verification rule (24) plus one per pipeline stage
(8) = 32 lessons.** This is a bounded, tractable writing project - perhaps a
week - and it converts "teaching" from a claim into an asset. Each lesson is
keyed to a rule ID or stage, so it appears exactly when that rule fires or that
stage runs on *the user's own board*.

**Lessons unlock from events, not from a curriculum.** You learn about I2C
pull-ups the first time your board has an I2C bus. `Learn` then shows what you
have unlocked, so progress is a by-product of building rather than homework.

### Mechanisms

- **`why?` on every status badge.** No exceptions. A badge with no explanation
  is a badge nobody trusts.
- **Evidence expansion** shows document, page, verbatim snippet, and machine-
  verification status - including, prominently, when the status is
  `CATALOG_REPORTED` and the snippet was never captured. The status *changing*
  when a datasheet is ingested is itself the best demonstration of the product's
  thesis, and should be shown as a change, not a state.
- **Interactive artifacts.** Clicking a component in the schematic or PCB shows
  its part, its evidence, why it is there, and which rules touched it. This is
  the difference between "here is a picture of a schematic" and "here is your
  circuit, explained."
- **Glossary on first use, per project.** A term is annotated the first time it
  appears in *your* project and plain thereafter. Never a modal, never a tour.
- **The bring-up checklist** (Stage 5) is the highest-value lesson in the
  product, because it is the only one the user checks against reality.

### Not this

- No model chain-of-thought, ever. Structured engineering rationale only.
- No gamification, badges, streaks, or points.
- No mandatory tutorial before the first project.
- No lesson that explains a concept without connecting it to something on the
  user's own board.
