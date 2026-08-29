# Edge Cases

## Datasheet ingestion

- scanned PDFs
- multi-column layouts
- nested tables
- revision mismatch
- part family datasheets
- one datasheet covering multiple packages
- package-specific pinout changes
- values expressed only in graphs
- min/typ/max tables
- absolute max confused with recommended operating range
- mixed units
- footnotes that change constraints
- errata documents
- application notes conflicting with older datasheets

## Component resolution

- counterfeit-like MPN names
- obsolete parts
- NRND parts
- no-stock parts
- alternate manufacturer naming
- package suffix affecting electrical characteristics
- same base MPN with incompatible footprints
- distributor page differing from manufacturer page

## Electrical

- missing ground
- floating enable pin
- required boot straps
- missing pull-ups
- duplicate bus addresses
- wrong logic-level compatibility
- current overload
- regulator dropout violation
- thermal overload
- reverse current
- insufficient capacitor derating
- polarity mistakes
- LED current resistor omitted
- analog reference noise
- reset timing constraints

## Cost

- low part price but huge MOQ
- multiple distributors creating high shipping
- package requiring reflow
- four-layer board caused by component choice
- hard-to-source connector
- programmer/debugger required
- custom cable required

## User behavior

- vague requirements
- contradictory requirements
- user requests unsupported safety-critical design
- user uploads wrong datasheet
- user names a breakout board but supplies bare IC datasheet
- user assumes dev-board pinout equals chip pinout

## Simulation

- missing SPICE model
- vendor model incompatible with ngspice
- convergence failure
- idealized model hides real issue
- simulation passes but digital firmware behavior remains untested

## AI-specific

- prompt injection inside PDF
- invented component facts
- invented citations
- confident explanation after failed verifier
- repair loop oscillates between two designs
- explanation describes outdated design state
- tool output silently truncated
