# Brief: unblocking component-behavior entries in OHMNI

You are one of six research agents. Your input file lists entries (OHM-xxx) that have a behavior class
but are not yet simulable, each with the blocker the audit recorded. Your job, per entry: decide whether
that blocker can be closed honestly from evidence, and if so draft exactly what would close it.
Honesty is the hard rule. A value or pin map you cannot support from a primary source stays unresolved.
Never invent, never use general knowledge as a source. Distributor pages or mirrors are secondary.

## Where things are (read-only; do NOT modify anything under /home/claude/repo)
- Entry record: /home/claude/repo/src/ohmni/behavior/data/entries/<id>.json (research.documents,
  research.field_updates = already-sourced facts, remaining_open_items, simulation_blockers).
- Gapfill page with the evidence fence: /home/claude/repo/docs/behavior/gapfill/<id>.md
- Behavior class: /home/claude/repo/src/ohmni/behavior/data/classes/<class>.json
  (`canonical_payload.parameters`, `.model.netlist_template` or other template keys, `.bench` = the
  class's locked test circuits with expected values and tolerances).
- Existing runtime recipes for 62 entries (copy their shape): /home/claude/repo/docs/behavior/runtime-recipes.json
  Good examples: OHM-044 (inductor, template_override + rdc probe), OHM-014 (sense resistor), OHM-016
  (resistor network, 8 pins), OHM-057 (diode), OHM-082 (multi-terminal LED), OHM-146 (oscillator IC),
  OHM-098 (MOSFET with inline model asset), OHM-105..120 (packages bound to reference ICs).
- How recipes compile: /home/claude/repo/src/ohmni/behavior/netlist.py (critical_facts pull a field from
  the entry's gapfill field_updates; the field must be sourced (basis not ASSUMPTION) with matching unit
  and a finite scalar; derived_parameters are expressions; template placeholders {Role} are terminal
  roles; template must be self-contained, no .include unless an inline_assets hashed file is bound).
- How runtime checks work: /home/claude/repo/tools/behavior_audit/runtime_benches.py (`dc_probe_definition`
  shows the existing per-class probes: each drives the bound model with a stimulus taken from a locked
  class bench or a sourced test condition, and compares one observable to a sourced limit or to the
  locked bench's analytic value). /home/claude/repo/tools/behavior_audit/ic_benches.py does IC/XO cases.
- Archived source bytes: the ledger /home/claude/repo/out/component-behavior/run/FETCH_LEDGER.jsonl maps
  url -> content_sha256; bytes are at /home/claude/repo/out/component-behavior/run/fetched-sources/<sha>.bin.
  Read PDFs with `pdftotext -layout`; render figure/pin-diagram pages with
  `pdftoppm -png -r 120 -f N -l N file.bin <your img dir>/name` and view them with the Read tool.
- STATE blockers: /home/claude/repo/out/component-behavior/run/STATE.json (`model_blockers`).
- Decision log for context: /home/claude/repo/out/component-behavior/run/DECISIONS.md

You may use WebFetch to locate a manufacturer primary document that is not archived yet. Such a
document can support a proposal only if marked `"archived": false` (it will need a browser download
before it counts). Prefer archived documents.

## What "closing a blocker" means
An entry becomes audited-simulable when: (1) it has a runtime recipe whose critical facts are all
sourced fields of the entry, with an evidenced terminal-role map (pin numbers to model roles from the
part's own pin diagram); (2) a runtime check exercises it and passes; (3) its record disposition is
simulable. Ratings the recorded blocker names (voltage rating, current limits, pin map, exact part
binding) must be sourced for the exact bound reference part. Some entries are safety/mains, protocol
or physically ambiguous: it is a correct outcome to keep them blocked with a precise reason.

## Output
Write JSON to /tmp/claude-0/b81/out_<group>.json, one object per input entry:
{
 "entry": "OHM-021", "class": "...", "verdict": "resolvable" | "resolvable_needs_download" | "blocked",
 "blocker_recorded": "...", "blocker_resolution": "how the evidence closes it, or why it cannot",
 "reference_part": "exact manufacturer part the binding is scoped to",
 "new_field_updates": [ {"field","value","unit","basis":"MFR_DATASHEET|DERIVED","confidence":"H|M|L",
     "sources":[url],"page":n,"scope":"part; condition","detail":"exact short quote or derivation",
     "archived": true} ],
 "recipe": { full proposed runtime-recipe object in the same shape as existing entries:
     behavior_id, package, reference_part, terminal_roles, critical_facts {alias:{field,unit[,output_unit]}},
     derived_parameters, class_parameters, quoted_parameters, template_key or template_override +
     template_provenance note, inline_assets, supported_analyses, limitations[] },
 "pin_map_evidence": "doc, page, figure; how each package terminal maps to each role",
 "runtime_check": {"stimulus":"...","observable":"...","comparison":"interval/absolute with numbers",
     "derived_from":"locked bench id or sourced field", "existing_probe_covers_it": true|false,
     "new_probe_needed_for_class": "describe if the class has no probe in runtime_benches.py"},
 "open_items_after": ["what remains unsourced even if bound"]
}
Then reply with a short summary: counts by verdict, which classes need a new runtime probe, and anything
surprising (wrong existing values, conflicts). Read each shared document once; be thorough but efficient.
