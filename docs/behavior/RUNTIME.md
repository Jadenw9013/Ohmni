# Component behavior runtime

`compile_circuit` translates CircuitIR connectivity and an explicit behavior
selection into a deterministic, self-contained ngspice deck. Authored joins live
in `runtime-recipes.json`; the normal record generator projects and hash-links
them into the runtime registry. The compiler does not fit models, fetch sources,
or issue a rating verdict.

Every recipe binds an OHM entry, an exact package, terminal roles, a behavior
class, and scoped primary-source fields. A catalog component needs an explicit
catalog-to-package permutation. A reference-only circuit may use its OHM ID as
the part ID; that selects the named reference model, without verifying a
purchased part. Repeated internally common terminals must share a circuit net.
Any unresolved component prevents the whole circuit from running.

Instance values, sourced ratings, authored class defaults, explicit assumptions,
and derived values retain separate provenance. Model confidence remains the
class's original model confidence; higher-confidence ratings cannot promote it.
Derived equations use bounded arithmetic without Python evaluation or imports.

Model libraries must be local, hash-matched assets. Their contents are inlined
once, with file and analysis commands rejected. MOSFET cards require `IS=0`.
Templates preserve authored regulator startup nodesets. Optional physical-pin
stray capacitances connect to ground only and require a positive value in farads.
The deck sets `.options tnom=25` and `.temp 25`.

CircuitIR external supplies become ideal DC voltage sources with explicit
limitations about omitted impedance and current limiting. Separate typed
`DCExcitation` values describe simulation test conditions in volts or amperes,
between existing circuit nets. These conditions do not become component ratings
or evidence. Duplicate ideal voltage sources across the same nets are refused.
Excitations are retained in the compilation and captured in the netlist hash.

`NgspiceAdapter.behavior_circuit` uses the existing simulator execution path and
requires actual ngspice 42 version output. Results distinguish `ran`, `failed`,
and `not_run`. A run carries a separate deterministic rating status; unknown conditions never become a pass. Successful numeric output is not an electrical safety pass.

Runtime probe receipts retain input hashes, the exact generated deck, raw
output, version text, and the comparison contract. The audit recompiles and
reparses these artifacts before accepting a receipt. Locked legacy expectations
are not changed to match a new result. For example, the signal-diode B1 deck uses
the simulator's 27 C default; its 0.73039 V expectation does not match the
required runtime temperature of 25 C. That acceptance conflict remains failed.

## Stage4 reference functions and waveforms

Functionless package records require an exact sourced reference-function selection plus the source pin-role map. Removing the selection, substituting another part, or treating an assumption as the source refuses compilation. The first ten IC bindings instantiate all four NAND gates, both op-amps, all sixteen shift-register terminals, and the LDO NC terminal metadata. Models remain behavioural approximations.

Typed PWL voltage/current excitations declare seconds and finite V/A samples from time zero in strictly increasing order. They never carry a source capability or component rating. Transient callers may explicitly choose up to the existing signal limit; the parser joins paginated column groups by sample identity before decimation and rejects conflicting duplicate observations. The LDO initial guess evaluates the authored equation before emitting a numeric nodeset.

`tools.behavior_audit.runtime_benches.run_runtime_recipes` reruns selected package bindings through NgspiceAdapter. `tools.behavior_audit.ic_benches` re-derives comparisons from locked analytical contracts and revalidates raw output, version, netlist and evidence hashes. No legacy expected value or tolerance was changed.

The final Stage4 batch adds 4N35 (isolated base), HC245 (both bus directions and disabled state), further HC595 packages and the explicit SiT8008 reference. Models enforce required ground roles, tied roles and isolated roles before simulation. SiT8008 manufacturer-to-library terminal permutation is hash-anchored and tested; its generic3D body/marker remains physically unverified. Transient native control output requests15 digits before parsing to retain the existing1Hz oscillator comparison tolerance. Raw samples, not downsampled display curves, establish frequency.

## Ratings and failure evaluation

The compiler accepts `measure_currents=True` to add deterministic zero-volt series probes for modeled terminal roles. It leaves NC terminals unmodeled and keeps regulator nodesets on physical circuit nets. The default preserves the existing calibration/benchmark deck identities. Missing currents are unknown, never inferred zero.

The adapter evaluates reference-scoped DC ratings after a successful run. `RatingContext` requires an explicit ambient/case temperature and confirmation of the source mounting/test conditions before thermal checks can evaluate. It does not derive ambient conditions from the25C simulator setting. Rating status is `not_run`, `unknown`, `within_model_limits`, or `violation`; a completed numerical solve is never a design pass. Transient peak/RMS/energy checks remain unknown.

Every original class rating and failure declaration remains in the result. Unrelated reference literals and nonquantitative triggers are not silently reinterpreted. The fixed-resistor overvoltage response can run the authored1G-ohm open approximation in a separate result, labeled `failure_approximation`. It does not erase the original violation or claim physical damage prediction. Other incomplete damage responses remain explicit.

`scripts/generate_behavior_examples.py` exports the existing authored probes as typed CircuitIR data. Loading validates recipe/research/generator identity, and compilation reproduces the original netlist before adding optional current probes. These are reference test circuits, not a user's saved design. The62 bindings and118 unbound-entry reasons remain distinct.

## Reference behavior UI

The Components dialog has a Behavior tab with source status, fidelity, confidence, limitations, and a Run reference circuit control. The62 authored reference circuits run through NgspiceAdapter in a separate output directory; the118 unbound entries show specific blockers. This is a learning reference, not a saved-project simulation or a manufacturing approval. Unknown ratings are explicit. Failed or canceled requests cannot reuse prior measurements.

## Design-level runs

`ComponentBehaviorService.run_design` (API: `POST /api/behavior/design/run` with the session identity and a `design` object) compiles a caller's own multi-part `CircuitIR` with the same `compile_circuit`, adapter and rating step the reference circuits use, with current probes on every part. It does not read or change a saved project.

- Every part must resolve to an audited simulable entry: either the single recipe whose catalog part and package match, or an explicit `selections` entry. Ambiguous, unbound, reference-only and documented entries stop the whole run before the simulator starts, and each refused part is named with its reason. A catalog LED whose declared colour differs from the bound reference part is not substituted.
- Ratings are evaluated per part, together, on the same operating point or transient window. The design is `within_model_limits` only when every part is; `design_summary` lists the unknown and violating parts. Declared sources stay ideal; board copper, layout parasitics and source capability are not simulated.
- Two parts that define the same `.model` or `.subckt` name get per-part names (ngspice 42 keeps the first of two same-named cards without a warning). Hash-locked inline assets are never rewritten; two assets may share a name only with an identical definition. Single-part reference decks are unchanged.
- Limits: at most 40 parts and 120 nets per run; a transient run with more rating signals than the adapter prints leaves every part's ratings unknown with that reason.

## AC analysis

`analysis="ac"` (design runs: `ac_points_hz`, one to eight frequencies, and an optional display `ac_sweep`) solves the operating point and then one single-frequency AC solve per requested point, each block echoed with its own marker and printing the solved frequency, which must match the requested one (a failed solve cannot pass off the previous plot's vectors); a point with a missing, duplicated or mismatched value is dropped, and a run without every requested point and vector fails. AC excitations (`ACExcitation`: optional DC bias plus `ac_rms`) are explicit, used only by AC runs and required by them; the AC magnitude is the sine's RMS value, so every result is an RMS phasor. A binding validated for the operating point runs in AC, because the AC solve linearizes the same model around that point.

- Operating-point ratings are evaluated on the solved DC point as before. Each requested frequency adds sinusoidal steady-state checks from DC plus RMS phasors: peak = |DC| + sqrt(2)*|AC| and RMS = sqrt(DC^2 + |AC|^2) for capacitors (rated and peak voltage, tantalum reverse swing, EDLC peak current), inductors (RMS heating, saturation), chokes, connector contacts, resistors (average power, peak voltage) and potentiometers.
- Tantalum ripple: the KEMET T491 ripple rating (`maximum_ripple_current`) and ESR heating (I^2 * `maximum_esr` against `maximum_power_dissipation`) are stated at 100 kHz and 25 C (RMS). For a card that is only Cb || Rlk, the checks are exact at 100 kHz at or below 25 C (D057); below 100 kHz they can only prove a violation, and above 100 kHz or warmer they are unknown. The bound T491 cards now carry the maximum ESR in series (D058). Real ESR, capacitance tolerance and the omitted ESL move the part's current in directions that card cannot bound, so for any tantalum card with a series element beyond Cb and Rlk, these rows are unknown in both directions, in AC and transient runs alike (D063). A dual solve (ESR = 0 and ESR = maximum, both required to pass) would restore a sound ripple check; that choice is queued for the owner.
- The KEMET T491 tantalum cards (OHM-033..036) carry the sourced 100 kHz maximum ESR in series (D058). Each also has an AC impedance receipt at 100 kHz, `OHM-03x-ac.json`, which requires the bound card to reproduce ESR + (Rleak || 1/(jwC)) from its own sourced facts. With the maximum ESR in the card, neither the tantalum's own current nor parallel parts' currents are bounded in either direction in general; their current checks do not gain a guarantee from it. Transient terminal voltages include the ESR drop.
- OHM-037 is bound to WIMA MKS4G031003F (D059). BEH-CAP-FILM has a transient charge probe under the locked B1 tolerance, and a rating branch: the DC rating derated 1.25 %/K above 85 C; the 125 C limit; peak voltage; and, in AC runs, the 50 Hz rule 1.4 x Urms + UDC <= Ur. At other frequencies that rule can only prove a violation.
- Only the classes listed above have AC rating translations. Every other part, and a listed part whose limits are not bound, gets an explicit unknown "AC swing" row at each frequency, so an AC run never passes on operating-point rows alone. A part whose operating point lacks a terminal value gets an unknown "AC checks" row; a missing value is never read as zero. The ripple rating's frequency, temperature and RMS basis are read from the record's own source scope (T491: "100 kHz, 25 C; RMS current"), not assumed for the class; the exact ripple and ESR heating rows also need the thermal scope confirmed. Temperature ratings follow their sources: T491 rated voltage up to 85 C, KYOCERA AVX SCC 2.7 V at 65 C and 2.3 V at 85 C. With no declared ambient these can only prove a violation (D060).
- Linearity is read from the compiled netlist (continuation lines included; POLY controlled sources and any unscanned include count as nonlinear): any semiconductor, switch, behavioural or digital element, or any value that reads a circuit voltage or current (the saturating inductor card), makes the circuit nonlinear, and then every AC-derived row is unknown with its computed result in the reason. Bound cards omit unsourced parasitics (ESL, self-resonance, and ESR where it is not sourced), so AC voltages and current sharing between parts can be non-conservative; the result carries this in `ac.limitations`. The ESR heating check uses the sourced maximum ESR, not the model.
