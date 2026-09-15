# Proposed richer electrical demonstrator — W8 planning only

**Not approved for implementation.** VIS-REF-001 authorizes this proposal, not
changes to the authenticated 29-component board. Its golden artifacts remain
the baseline. The 124-body educational scene is not a candidate electrical BOM.

A useful next demonstrator would extend the existing ESP32 sensor/controller
with independently verifiable functions. Select parts from requirements and
relocatable datasheet evidence; do not reverse-engineer the reference image into
a supposed circuit.

| Proposed module | Preliminary population, not a purchase BOM | Work required before admission |
| --- | --- | --- |
| Protected low-voltage input | One protection device, one resettable fuse or current limiter, supporting passives | Select exact devices and limits; add source-grounded catalog records, footprint/pin mapping, power and fault checks. USB-C power negotiation remains outside this proposal. |
| Two low-voltage switched outputs | Two driver transistors, two gate resistors, two gate pull-downs, two load connectors; suppression only where the specified load requires it | Add supported driver/load semantics, current and dissipation limits, pin voltage checks, flyback obligations for inductive loads, and layout rules. No mains switching. |
| Display and auxiliary sensor expansion | One keyed I2C connector, one optional display connector and required decoupling; actual peripheral devices chosen later | Resolve bus addresses, rail levels, capacitance/rise-time budget, connector orientation and current demand. New footprints and missing deterministic checks require explicit coverage. |
| Service and bring-up | Clearly labeled power/ground/debug test points and user controls justified by the firmware specification | Validate real pin ownership and access, preserve boot/strapping constraints, generate a source-backed bring-up checklist. |

Indicative work is **10–20 engineering days**, excluding fabrication lead time:
2–4 days for requirements/evidence admission; 3–6 for deterministic rules,
footprints and synthesis; 3–6 for placement/routing/release and firmware;
2–4 for bench verification and corrections. These are planning estimates, not
measured delivery commitments or prices. Routing may dominate: M10-T05's
unresolved work remains parked and is not made complete by this visualization.

An implementation approval should first settle input source and current, load
type and maximum current, peripheral interfaces, board dimensions, assembly
constraints and firmware behavior. Each module then needs semantic evidence,
ERC, physical/routing checks, DRC and release validation. Firmware tests and
bench measurements remain separate evidence; neither a good render nor ERC/DRC
establishes working hardware. No supplier prices, stock facts, new catalog
records, electrical artifacts or firmware were created by W8.
