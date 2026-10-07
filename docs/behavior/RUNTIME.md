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
