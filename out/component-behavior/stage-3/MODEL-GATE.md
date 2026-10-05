# Stage 3 model gate

> Generated from recipes, scoped records and revalidated runtime receipts.

Registered bindings: 45. Bindings with current passing runtime comparisons: 40.
Runtime comparison results: {'failed': 5, 'passed': 58}.
Stage acceptance remains blocked by the separately recorded audit failures. Runtime comparisons only cover the measurement stated in each receipt; they do not establish complete model accuracy, ratings or safe operation.

| Entry | Source status before → after | Bound reference | Runtime comparisons / blockers |
| --- | --- | --- | --- |
| OHM-001 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-002 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-003 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-004 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-005 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-006 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-007 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-008 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-009 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-010 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-011 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-012 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-013 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-014 | partial → partial | Vishay WSL2512, 5 milliohm, two-terminal | Current runtime comparisons pass; limits below apply |
| OHM-015 | partial → partial | Unbound | Exact sense-pin variant and busbar thermal/current conditions are unbound; 36 W does not establish a safe free-air current. |
| OHM-016 | partial → partial | Bourns 4608X-101 eight-pin bussed network, 10 kohm | Current runtime comparisons pass; limits below apply |
| OHM-017 | partial → partial | Unbound | Confirm numbered pin-to-element map before simulating the physical array. |
| OHM-018 | partial → partial | Unbound | Maximum wiper current is unsourced; loaded-wiper simulation must be refused. End/contact resistance bounds do not establish nominal values. |
| OHM-019 | partial → partial | Unbound | Maximum wiper current is unsourced; loaded-wiper simulation must be refused. Style-specific voltage and mechanical direction still need explicit binding. |
| OHM-020 | research_required → research_required | Unbound | RV16AF power rating remains rating-critical and unsourced; refuse default simulation. |
| OHM-021 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-022 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-023 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-024 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-025 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-026 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-027 | partial → partial | Unbound | The exact default part voltage rating is not re-established by these general application documents. |
| OHM-028 | partial → partial | Unbound | Unbound generic disc voltage and safety class; no mains-use inference is permitted. |
| OHM-029 | partial → partial | Unbound | Rating-critical part voltage and ripple/lifetime limits need an exact series binding. |
| OHM-030 | partial → partial | Unbound | Rating-critical part voltage and ripple/lifetime limits need an exact series binding. |
| OHM-031 | partial → partial | Unbound | Rating-critical part voltage and ripple/lifetime limits need an exact series binding.; Three-pin auxiliary-terminal connectivity unresolved; only the separately mapped two-pin variant may proceed after rating binding. |
| OHM-032 | partial → partial | Unbound | Rating-critical part voltage and ripple/lifetime limits need an exact series binding. |
| OHM-033 | partial → partial | Unbound | Runtime must use the scoped MnO2 reverse/temperature limits instead of the generic fixed 3% envelope. |
| OHM-034 | partial → partial | Unbound | Runtime must use the scoped MnO2 reverse/temperature limits instead of the generic fixed 3% envelope. |
| OHM-035 | partial → partial | Unbound | Runtime must use the scoped MnO2 reverse/temperature limits instead of the generic fixed 3% envelope. |
| OHM-036 | partial → partial | Unbound | Runtime must use the scoped MnO2 reverse/temperature limits instead of the generic fixed 3% envelope. |
| OHM-037 | partial → partial | Unbound | The generic 10 mm default remains unbound to an exact rated part. |
| OHM-038 | partial → partial | Unbound | Unbound mains safety part; no claim of safe mains operation. |
| OHM-039 | partial → partial | Unbound | Do not use an unsourced Q/leakage model as a verified RF response. |
| OHM-040 | partial → partial | Unbound | Unresolved electrical/reference/geometry binding and condition-specific current limits; stored energy and short-circuit heating are safety relevant. |
| OHM-041 | partial → partial | Unbound | Do not use assumed 30% saturation drop / 40 K rise as sourced thermal or saturation limits. |
| OHM-042 | research_required → research_required | Unbound | Unspecified default variant and incomplete rating conditions remain blocked. |
| OHM-043 | partial → partial | Unbound | Saturation and temperature limits remain unestablished; no silent placeholder promotion. |
| OHM-044 | partial → partial | Coilcraft 0603CS-15NX_R_, suffix unselected; explicit alternative | Current runtime comparisons pass; limits below apply |
| OHM-045 | complete → complete | Bourns SRP7028A-1R8M | Current runtime comparisons pass; limits below apply |
| OHM-046 | partial → partial | Bourns SDR0604-100ML | Current runtime comparisons pass; limits below apply |
| OHM-047 | partial → partial | Unbound | Saturation limit is not established for the ferrite-core default. |
| OHM-048 | partial → partial | Bourns RLB0914-101KL | Current runtime comparisons pass; limits below apply |
| OHM-049 | partial → partial | Bourns 2107-V-RC | Current runtime comparisons pass; limits below apply |
| OHM-050 | partial → partial | Unbound | Default winding permutation cannot be used until explicit package binding is corrected and tested. |
| OHM-051 | partial → partial | Unbound | Mains-rated winding binding and missing saturation/thermal model need explicit handling; insulation test voltage is not a working voltage. |
| OHM-052 | partial → partial | Unbound | Do not claim safe galvanic isolation or a complete response from assumed 1 H / 5 mH / 100 pF. |
| OHM-053 | research_required → research_required | Unbound | No safety or thermal acceptance for this transformer until working-voltage and loss limits are bound. |
| OHM-054 | partial → partial | Unbound | Physical/reference and primary-conductor binding conflict; open-secondary operation is hazardous. |
| OHM-055 | partial → partial | Unbound | Working-voltage and complete physical pin binding remain unestablished; no isolation-safety acceptance. |
| OHM-056 | partial → partial | Scoped package record | OHM-056: stale or invalid runtime run_status; OHM-056: raw observation does not meet its locked or sourced contract |
| OHM-057 | partial → partial | Vishay 1N4007 | Current runtime comparisons pass; limits below apply |
| OHM-058 | partial → partial | Vishay 1N5408 | Current runtime comparisons pass; limits below apply |
| OHM-059 | partial → partial | Scoped package record | OHM-059: stale or invalid runtime run_status; OHM-059: raw observation does not meet its locked or sourced contract |
| OHM-060 | research_required → research_required | Unbound | The average-current derating curve must be implemented before claiming a complete thermal envelope. |
| OHM-061 | partial → partial | Scoped package record | OHM-061: stale or invalid runtime run_status; OHM-061: raw observation does not meet its locked or sourced contract |
| OHM-062 | research_required → research_required | Nexperia BAS316 | OHM-062: stale or invalid runtime run_status; OHM-062: raw observation does not meet its locked or sourced contract |
| OHM-063 | research_required → research_required | Nexperia BAS516 | OHM-063: stale or invalid runtime run_status; OHM-063: raw observation does not meet its locked or sourced contract |
| OHM-064 | partial → partial | Vishay S1M, original entry fit | Current runtime comparisons pass; limits below apply |
| OHM-065 | partial → partial | Vishay S2M PN; explicit alternative to Schottky default | Current runtime comparisons pass; limits below apply |
| OHM-066 | partial → partial | Unbound | Functional variant binding is deferred: the index projects PN, while the sourced default is SS34 Schottky. No MURS PN reference is verified; source function and model must not be silently interchanged. |
| OHM-067 | partial → partial | Vishay BAT42W; BAT54-derived proxy | Current runtime comparisons pass; limits below apply |
| OHM-068 | partial → partial | Diodes Incorporated BZT52C5V1; BZX55-derived proxy | Current runtime comparisons pass; limits below apply |
| OHM-069 | partial → partial | Vishay SMBJ15A | Current runtime comparisons pass; limits below apply |
| OHM-070 | partial → partial | Unbound | The available BAV99 power/thermal rating is explicitly for one diode loaded. Shared-package loading and configuration require a scoped runtime guard; no independent per-die power allocation is assumed. |
| OHM-071 | research_required → research_required | Vishay DF10M | Current runtime comparisons pass; limits below apply |
| OHM-072 | partial → partial | Unbound | Physical role binding remains unverified for the generic WOM/WOG combined entry. |
| OHM-073 | partial → partial | Vishay TLDR4400; authored LED_RED approximation | Current runtime comparisons pass; limits below apply |
| OHM-074 | partial → partial | Vishay TLHR5200 red | Current runtime comparisons pass; limits below apply |
| OHM-075 | research_required → research_required | Unbound | Junction-temperature/thermal acceptance cannot use the unsourced 350 K/W placeholder. |
| OHM-076 | research_required → research_required | Unbound | The copied thermal parameters are unsourced for this rectangular lamp. |
| OHM-077 | partial → partial | Kingbright APHHS1005SURCK red | Current runtime comparisons pass; limits below apply |
| OHM-078 | partial → partial | Unbound | Thermal acceptance lacks sourced junction/thermal parameters; generic color variants lack an exact reference. |
| OHM-079 | partial → partial | Kingbright AP2012EC red | Current runtime comparisons pass; limits below apply |
| OHM-080 | partial → partial | Kingbright APT3216SURCK red | Current runtime comparisons pass; limits below apply |
| OHM-081 | partial → partial | Vishay VLMW33S2V1-5K8L-08 white | Current runtime comparisons pass; limits below apply |
| OHM-082 | partial → partial | Avago ASMB-MTB0-0A3A2 | Current runtime comparisons pass; limits below apply |
| OHM-083 | research_required → research_required | Unbound | Do not simulate OHM-083 from a generic six-terminal RGB pin map or unsourced per-color ratings. |
| OHM-084 | partial → partial | Unbound | Rated supply-current model is blocked until an exact-version current specification is sourced. |
| OHM-085 | partial → partial | Unbound | Junction-to-solderpoint data does not establish a board/heatsink-to-ambient path; the85 C fit and revised source require explicit thermal-context handling before rated runtime use. |
| OHM-086 | partial → partial | Unbound | Module terminal map and module thermal limits are missing; keep the star model blocked. |
| OHM-087 | research_required → research_required | Unbound | Per-segment and common-lead aggregate power/current allocation is not established; do not use table PD/IF as a rated complete-display envelope. |
| OHM-088 | research_required → research_required | Unbound | Per-segment and common-lead aggregate power/current allocation is not established; do not use table PD/IF as a rated complete-display envelope. |
| OHM-089 | research_required → research_required | Unbound | Per-segment and common-lead aggregate power/current allocation is not established; do not use table PD/IF as a rated complete-display envelope. |
| OHM-090 | research_required → research_required | Unbound | Exact part-to-library terminal map remains unverified. |
| OHM-091 | partial → partial | Unbound | Do not simulate the assumed 100 mA/4.1 V backlight as a rated module load. |
| OHM-092 | partial → partial | Unbound | Unknown module terminal map and power/logic limits block module electrical simulation. |
| OHM-093 | partial → partial | Unbound | Default onsemi2N3904 source is unavailable. Opened PN2222A data does not validate that model or its generic TO-92 pin assignment. |
| OHM-094 | partial → partial | Unbound | Default MMBT3904/2N3904 fit is not established by the opened BC817 alternative; exact reference/model/pin binding is missing. |
| OHM-095 | partial → partial | Nexperia BCX56-16, Rev13 | Current runtime comparisons pass; limits below apply |
| OHM-096 | partial → partial | Unbound | Default AMS1117-3.3 regulator remains unbound; BCP56 transistor research cannot supply its electrical truth. Regulator binding is deferred to the IC stage. |
| OHM-097 | partial → partial | Fairchild BD139 ungraded, RevA February2000 | Current runtime comparisons pass; limits below apply |
| OHM-098 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-099 | research_required → research_required | Scoped package record | Current runtime comparisons pass; limits below apply |
| OHM-100 | research_required → research_required | Unbound | Default IRLR8721 compatible model card is unavailable; the IRLB8721 card is a different part and cannot be substituted. |
| OHM-101 | partial → partial | Unbound | The default regulator has no re-verified source/functional binding; keep that default blocked. |
| OHM-102 | partial → partial | Scoped package record | Current runtime comparisons pass; limits below apply |

## Implementation and remaining scope

CircuitIR instances compile through the existing NgspiceAdapter. Models are inlined, terminal permutations remain explicit, and the runtime enforces tnom/temp25 C. MOSFET cards require IS=0, regulator templates retain nodesets, and pin strays return to ground. Source stimuli currently support explicit DC voltage/current; arbitrary waveforms and AC circuit analysis are not implemented in this stage.

No source status was promoted. Unbound entries remain refused. Tantalum reverse/temperature policy and other condition-sensitive ratings require the later ratings stage; reference-function joins for package and mixed-function entries require the IC binding work. L3 protocol behavior remains outside ngspice.

A named alternate binding does not silently replace the default: Coilcraft RF, S2M PN and BAT42W proxy records name their scope and package selection explicitly. No generic purchased part is verified by selecting an OHM reference.


## Captured measurements

### OHM-001 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-001 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-002 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-002 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-003 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-003 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-004 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-004 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-005 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-005 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-006 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-006 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-007 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-007 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-008 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-008 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-009 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-009 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-010 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-010 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-011 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-011 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-012 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-012 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-013 / op

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 1, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-013 / tran

- Recorded comparison: passed.
- Contract: {'expected': 2.5, 'tolerance': 0.0025}.
- Captured observation: {'samples': 108, 'minimum': 2.5, 'maximum': 2.5}.
- Limits: Tests the authored ideal-divider equation and its compiled binding, not manufacturing suitability, ratings or destructive failure.

### OHM-014 / op

- Recorded comparison: passed.
- Contract: {'analytical_source': 'BEH-RES-SENSE/B1', 'derivation': "Same authored I*Rs equation and relative tolerance, evaluated at the bound 5 milliohm reference instead of the class bench's 1 milliohm example.", 'expected': 0.05, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': 'b25bde9e184f48fc4d20bd86358c2e094f446d0e029227a5348ef9d3fd8cdc73', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'nominal_resistance', 'page': 1, 'scope': 'Vishay WSL2512 5 milliohm two-terminal reference', 'sources': ['https://www.vishay.com/docs/30100/wsl.pdf'], 'unit': 'ohm', 'value': 0.005}, 'tolerance': 5.000000000000001e-05}.
- Captured observation: 0.05.
- Limits: Two-terminal isothermal DC Ohm's law only; no Kelvin, lead-drop, temperature or safe-current acceptance.

### OHM-016 / op

- Recorded comparison: passed.
- Contract: {'analytical_source': 'BEH-RES-NETWORK/B2', 'derivation': 'Same authored parallel sum N*V/R and relative tolerance, evaluated for the bound seven 10 kohm branches; the original four 1 kohm branch contract remains unchanged.', 'expected': 0.0035, 'kind': 'absolute', 'observable': 'supply_current', 'source_deck_sha256': '8fa6c319f64524d7d3f213d97460ee74158d0cd70dcf801b1f4a5031de4c32a3', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'nominal_resistance', 'page': 2, 'scope': 'Bourns 4608X-101 eight-pin bussed network, 10 kohm', 'sources': ['https://www.bourns.com/docs/Product-Datasheets/4600X.pdf'], 'unit': 'ohm', 'value': 10000}, 'tolerance': 3.5000000000000004e-06}.
- Captured observation: 0.0035.
- Limits: Total DC branch current for the sourced bussed topology only; per-element and whole-package thermal ratings remain separate.

### OHM-044 / op

- Recorded comparison: passed.
- Contract: {'current': 0.7, 'kind': 'interval', 'maximum': 0.17, 'minimum': 0, 'observable': 'dc_resistance', 'source_facts': {'irms': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'reference_current', 'page': 2, 'scope': '0603CS-15NX_R_ reference; option suffix unselected; 15 C rise from 25 C, not absolute maximum', 'sources': ['https://www.coilcraft.com/getmedia/022eb894-7253-40d0-b07c-650d362fc80e/0603cs.pdf'], 'unit': 'A', 'value': 0.7}, 'rdc_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_dcr', 'page': 2, 'scope': '0603CS-15NX_R_ reference; option suffix unselected', 'sources': ['https://www.coilcraft.com/getmedia/022eb894-7253-40d0-b07c-650d362fc80e/0603cs.pdf'], 'unit': 'ohm', 'value': 0.17}}}.
- Captured observation: 0.17.
- Limits: Cold isothermal DC winding resistance against the sourced upper bound. Does not validate nonlinear inductance, resonant response, core loss, self-heating or safe sustained operation at the stimulus current.

### OHM-045 / op

- Recorded comparison: passed.
- Contract: {'current': 8.5, 'kind': 'interval', 'maximum': 0.017, 'minimum': 0, 'observable': 'dc_resistance', 'source_facts': {'irms': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'rated_rms_current', 'page': 1, 'scope': 'SRP7028A-1R8M; 40 C temperature rise', 'sources': ['https://www.farnell.com/datasheets/2907623.pdf'], 'unit': 'A', 'value': 8.5}, 'rdc_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'converted_unit': 'ohm', 'converted_value': 0.017, 'detail': None, 'field': 'maximum_dcr', 'page': 1, 'scope': 'SRP7028A-1R8M', 'sources': ['https://www.farnell.com/datasheets/2907623.pdf'], 'unit': 'mohm', 'value': 17}}}.
- Captured observation: 0.013999999999999999.
- Limits: Cold isothermal DC winding resistance against the sourced upper bound. Does not validate nonlinear inductance, resonant response, core loss, self-heating or safe sustained operation at the stimulus current.

### OHM-046 / op

- Recorded comparison: passed.
- Contract: {'current': 1.45, 'kind': 'interval', 'maximum': 0.1, 'minimum': 0, 'observable': 'dc_resistance', 'source_facts': {'irms': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'rated_rms_current', 'page': 1, 'scope': 'SDR0604-100ML; 40 C maximum rise', 'sources': ['https://www.bourns.com/pdfs/SDR0604.pdf'], 'unit': 'A', 'value': 1.45}, 'rdc_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'converted_unit': 'ohm', 'converted_value': 0.1, 'detail': None, 'field': 'maximum_dcr', 'page': 1, 'scope': 'SDR0604-100ML', 'sources': ['https://www.bourns.com/pdfs/SDR0604.pdf'], 'unit': 'ohm', 'value': 0.1}}}.
- Captured observation: 0.09999999999999999.
- Limits: Cold isothermal DC winding resistance against the sourced upper bound. Does not validate nonlinear inductance, resonant response, core loss, self-heating or safe sustained operation at the stimulus current.

### OHM-048 / op

- Recorded comparison: passed.
- Contract: {'current': 1.1, 'kind': 'interval', 'maximum': 0.28, 'minimum': 0, 'observable': 'dc_resistance', 'source_facts': {'irms': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'rated_rms_current', 'page': 6, 'scope': 'RLB0914-101KL; 40 C typical rise; current itself is a typical value, not guaranteed minimum or maximum', 'sources': ['https://www.bourns.com/docs/product-datasheets/RLB.pdf'], 'unit': 'A', 'value': 1.1}, 'rdc_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'converted_unit': 'ohm', 'converted_value': 0.28, 'detail': None, 'field': 'maximum_dcr', 'page': 6, 'scope': 'RLB0914-101KL', 'sources': ['https://www.bourns.com/docs/product-datasheets/RLB.pdf'], 'unit': 'ohm', 'value': 0.28}}}.
- Captured observation: 0.27999999999999997.
- Limits: Cold isothermal DC winding resistance against the sourced upper bound. Does not validate nonlinear inductance, resonant response, core loss, self-heating or safe sustained operation at the stimulus current.

### OHM-049 / op

- Recorded comparison: passed.
- Contract: {'current': 5.0, 'kind': 'interval', 'maximum': 0.029, 'minimum': 0, 'observable': 'dc_resistance', 'source_facts': {'irms': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'rated_current', 'page': 1, 'scope': '2107-V-RC; 2107 row with V mounting suffix per ordering note; 30 C maximum temperature rise', 'sources': ['https://www.bourns.com/docs/product-datasheets/2100_series.pdf'], 'unit': 'A', 'value': 5}, 'rdc_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'converted_unit': 'ohm', 'converted_value': 0.029, 'detail': None, 'field': 'maximum_dcr', 'page': 1, 'scope': '2107-V-RC; 2107 row with V mounting suffix per ordering note', 'sources': ['https://www.bourns.com/docs/product-datasheets/2100_series.pdf'], 'unit': 'ohm', 'value': 0.029}}}.
- Captured observation: 0.028999999999999998.
- Limits: Cold isothermal DC winding resistance against the sourced upper bound. Does not validate nonlinear inductance, resonant response, core loss, self-heating or safe sustained operation at the stimulus current.

### OHM-056 / op

- Recorded comparison: failed.
- Contract: {'analytical_source': 'BEH-DIO-PN/B1', 'expected': 0.73039, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': '8dffd8f6985236af4d99116aa263af199cdcdb5fc7c245e50fe3f888153ca5ec', 'tolerance': 0.001}.
- Captured observation: 0.7255607.
- Limits: Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value.

### OHM-057 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 1.1, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage', 'page': 2, 'scope': 'Vishay 1N4007; 25 C unless stated; IF=1 A', 'sources': ['https://www.vishay.com/docs/88503/1n4001.pdf'], 'unit': 'V', 'value': 1.1}}.
- Captured observation: 0.9240392.
- Limits: Isothermal25 C forward voltage against the scoped primary-source maximum at its test current; a source-bound check does not validate typical fit, temperature, reverse recovery or ratings.

### OHM-058 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 1.2, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage', 'page': 2, 'scope': 'Vishay 1N5408; 25 C unless stated; IF=3 A', 'sources': ['https://www.vishay.com/docs/88516/1n5400.pdf'], 'unit': 'V', 'value': 1.2}}.
- Captured observation: 1.192271.
- Limits: Isothermal25 C forward voltage against the scoped primary-source maximum at its test current; a source-bound check does not validate typical fit, temperature, reverse recovery or ratings.

### OHM-059 / op

- Recorded comparison: failed.
- Contract: {'analytical_source': 'BEH-DIO-PN/B1', 'expected': 0.73039, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': '8dffd8f6985236af4d99116aa263af199cdcdb5fc7c245e50fe3f888153ca5ec', 'tolerance': 0.001}.
- Captured observation: 0.7255607.
- Limits: Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value.

### OHM-061 / op

- Recorded comparison: failed.
- Contract: {'analytical_source': 'BEH-DIO-PN/B1', 'expected': 0.73039, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': '8dffd8f6985236af4d99116aa263af199cdcdb5fc7c245e50fe3f888153ca5ec', 'tolerance': 0.001}.
- Captured observation: 0.7255607.
- Limits: Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value.

### OHM-062 / op

- Recorded comparison: failed.
- Contract: {'analytical_source': 'BEH-DIO-PN/B1', 'expected': 0.73039, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': '8dffd8f6985236af4d99116aa263af199cdcdb5fc7c245e50fe3f888153ca5ec', 'tolerance': 0.001}.
- Captured observation: 0.7255607.
- Limits: Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value.

### OHM-063 / op

- Recorded comparison: failed.
- Contract: {'analytical_source': 'BEH-DIO-PN/B1', 'expected': 0.73039, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': '8dffd8f6985236af4d99116aa263af199cdcdb5fc7c245e50fe3f888153ca5ec', 'tolerance': 0.001}.
- Captured observation: 0.7255607.
- Limits: Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value.

### OHM-064 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 1.1, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage', 'page': 2, 'scope': 'S1M SMA; IF=1 A; TA25 C source table default', 'sources': ['https://www.vishay.com/doc?88711'], 'unit': 'V', 'value': 1.1}}.
- Captured observation: 1.093054.
- Limits: Isothermal25 C forward voltage against the scoped primary-source maximum at its test current; a source-bound check does not validate typical fit, temperature, reverse recovery or ratings.

### OHM-065 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 1.15, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage', 'page': 2, 'scope': 'S2M SMB; IF=1.5 A', 'sources': ['https://www.vishay.com/doc?88712'], 'unit': 'V', 'value': 1.15}}.
- Captured observation: 1.126806.
- Limits: Isothermal25 C forward voltage against the scoped primary-source maximum at its test current; a source-bound check does not validate typical fit, temperature, reverse recovery or ratings.

### OHM-067 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 0.4, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage', 'page': 2, 'scope': 'BAT42W SOD123; package-matched alternative to BAT54 SOT23; IF10 mA', 'sources': ['https://www.diodes.com/datasheet/download/BAT42W.pdf'], 'unit': 'V', 'value': 0.4}}.
- Captured observation: 0.3035291.
- Limits: Isothermal25 C forward voltage against the scoped primary-source maximum at its test current; a source-bound check does not validate typical fit, temperature, reverse recovery or ratings.

### OHM-068 / op / legacy

- Recorded comparison: passed.
- Contract: {'analytical_source': 'BEH-DIO-ZENER/B1', 'expected': 5.1, 'kind': 'absolute', 'node': 'cathode', 'observable': 'node_voltage', 'source_deck_sha256': 'bf8f3b0ae809d16e0779fc1ed9b16de5242820fb6740c4e08707f78442e51768', 'test_current': 0.005, 'test_current_evidence': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'converted_unit': 'A', 'converted_value': 0.005, 'detail': None, 'field': 'zener_test_current', 'page': 2, 'scope': 'BZT52C5V1; TA25 C; short-duration pulse test per note10', 'sources': ['https://www.diodes.com/_files/datasheets/ds18004.pdf'], 'unit': 'mA', 'value': 5}, 'tolerance': 0.01}.
- Captured observation: 5.09983.
- Limits: Isothermal 25 C voltage at the source short-pulse test current. Does not validate equilibrium self-heating, the impedance/knee envelope, surge, forward-current limit or destructive behavior.

### OHM-068 / op / source_bound

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 5.4, 'minimum': 4.8, 'node': 'cathode', 'observable': 'node_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'zener_voltage_range', 'page': 2, 'scope': 'BZT52C5V1 SOD123; IZT5mA,25C; nominal5.1V; source note10 short-duration pulse to minimize self-heating; not equilibrium DC', 'selected_value': 5.4, 'selected_value_path': [1], 'sources': ['https://www.diodes.com/_files/datasheets/ds18004.pdf'], 'unit': 'V', 'value': [4.8, 5.4]}, 'test_current': 0.005, 'test_current_evidence': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'converted_unit': 'A', 'converted_value': 0.005, 'detail': None, 'field': 'zener_test_current', 'page': 2, 'scope': 'BZT52C5V1; TA25 C; short-duration pulse test per note10', 'sources': ['https://www.diodes.com/_files/datasheets/ds18004.pdf'], 'unit': 'mA', 'value': 5}}.
- Captured observation: 5.09983.
- Limits: Isothermal 25 C voltage at the source short-pulse test current. Does not validate equilibrium self-heating, the impedance/knee envelope, surge, forward-current limit or destructive behavior.

### OHM-069 / op / legacy

- Recorded comparison: passed.
- Contract: {'analytical_source': 'BEH-DIO-TVS/B1', 'expected': 24.4, 'kind': 'absolute', 'node': 'cathode', 'observable': 'node_voltage', 'source_deck_sha256': 'a1f44f588f3fefe33edb85ccd93c846f83e3b03ed62a332c25f0a8c9afc903da', 'test_current': 24.6, 'test_current_evidence': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'peak_pulse_current', 'page': 2, 'scope': 'SMBJ15A; TA25 C; 10/1000 us waveform, source figure2 derating and figure3 waveform', 'sources': ['https://www.vishay.com/docs/88392/smbj.pdf'], 'unit': 'A', 'value': 24.6}, 'tolerance': 0.122}.
- Captured observation: 24.4.
- Limits: Static isothermal clamp-curve probe at 25 C only. The source rating describes a pulse; an operating-point result does not establish allowable continuous current, pulse waveform, heating or protected-load survival. Legacy numerical tolerance and the source voltage maximum are checked separately.

### OHM-069 / op / source_bound

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 24.4, 'minimum': 0, 'node': 'cathode', 'observable': 'node_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_clamping_voltage', 'page': 2, 'scope': 'SMBJ15A unidirectional / SMBJ15CA bidirectional; Ippm24.6A,10/1000us pulse;25C', 'sources': ['https://www.vishay.com/docs/88392/smbj.pdf'], 'unit': 'V', 'value': 24.4}, 'test_current': 24.6, 'test_current_evidence': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'peak_pulse_current', 'page': 2, 'scope': 'SMBJ15A; TA25 C; 10/1000 us waveform, source figure2 derating and figure3 waveform', 'sources': ['https://www.vishay.com/docs/88392/smbj.pdf'], 'unit': 'A', 'value': 24.6}}.
- Captured observation: 24.4.
- Limits: Static isothermal clamp-curve probe at 25 C only. The source rating describes a pulse; an operating-point result does not establish allowable continuous current, pulse waveform, heating or protected-load survival. Legacy numerical tolerance and the source voltage maximum are checked separately.

### OHM-071 / op / negative

- Recorded comparison: passed.
- Contract: {'derivation': "Two conducting junctions; sum of two source per-diode forward-voltage maxima. Both AC polarities use the original bench's 10 V input amplitude.", 'kind': 'interval', 'maximum': 2.2, 'minimum': 0, 'observable': 'bridge_drop', 'source_deck_sha256': '07a175ac644ca384e8b8a4cf187e0554f74b2510450bcbad6e2841d718dd1274', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage_per_diode', 'page': 2, 'scope': 'DF10M DFM; 1A; TA25 C source table default', 'sources': ['https://www.vishay.com/doc?88571'], 'unit': 'V', 'value': 1.1}, 'stimulus_source': 'BEH-DIO-BRIDGE/B1', 'supply_magnitude': 10, 'test_current': 1.0}.
- Captured observation: 2.186119999999999.
- Limits: Isothermal DC rectification and two-junction voltage bound under both AC polarities; does not validate ripple, shared thermal behavior, surge or safe sustained output current.

### OHM-071 / op / positive

- Recorded comparison: passed.
- Contract: {'derivation': "Two conducting junctions; sum of two source per-diode forward-voltage maxima. Both AC polarities use the original bench's 10 V input amplitude.", 'kind': 'interval', 'maximum': 2.2, 'minimum': 0, 'observable': 'bridge_drop', 'source_deck_sha256': '07a175ac644ca384e8b8a4cf187e0554f74b2510450bcbad6e2841d718dd1274', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'maximum_forward_voltage_per_diode', 'page': 2, 'scope': 'DF10M DFM; 1A; TA25 C source table default', 'sources': ['https://www.vishay.com/doc?88571'], 'unit': 'V', 'value': 1.1}, 'stimulus_source': 'BEH-DIO-BRIDGE/B1', 'supply_magnitude': 10, 'test_current': 1.0}.
- Captured observation: 2.1861239999999995.
- Limits: Isothermal DC rectification and two-junction voltage bound under both AC polarities; does not validate ripple, shared thermal behavior, surge or safe sustained output current.

### OHM-073 / op

- Recorded comparison: passed.
- Contract: {'analytical_source': 'BEH-LED-INDICATOR/B1', 'expected': 2.0, 'kind': 'absolute', 'observable': 'anode_voltage', 'source_deck_sha256': '29fe19065247098a3dacc078c2a5cdd90962fdcb06ac581925b4b9e212b0c159', 'tolerance': 0.05}.
- Captured observation: 1.988581.
- Limits: Authored proxy forward curve only. The runtime enforces 25 C; a legacy bench temperature mismatch is reported without changing its locked expected value.

### OHM-074 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 3.0, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'red_forward_voltage_typical_max', 'page': 2, 'scope': 'TLHR5200 red; 20 mA', 'selected_value': 3, 'selected_value_path': [1], 'sources': ['https://www.farnell.com/datasheets/6603.pdf'], 'unit': 'V', 'value': [2, 3]}, 'test_current': 0.02}.
- Captured observation: 1.988581.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-077 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 2.5, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 2, 'scope': 'APHHS1005SURCK; IF20mA', 'selected_value': 2.5, 'selected_value_path': [1], 'sources': ['https://www.kingbrightusa.com/images/catalog/SPEC/APHHS1005SURCK.pdf'], 'unit': 'V', 'value': [1.95, 2.5]}, 'test_current': 0.02}.
- Captured observation: 1.988581.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-079 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 2.5, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 2, 'scope': 'AP2012EC; IF20mA', 'selected_value': 2.5, 'selected_value_path': [1], 'sources': ['https://www.kingbrightusa.com/images/catalog/SPEC/AP2012EC.pdf'], 'unit': 'V', 'value': [2, 2.5]}, 'test_current': 0.02}.
- Captured observation: 1.988581.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-080 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 2.5, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 2, 'scope': 'APT3216SURCK; IF20mA', 'selected_value': 2.5, 'selected_value_path': [1], 'sources': ['https://www.kingbrightusa.com/images/catalog/SPEC/APT3216SURCK.pdf'], 'unit': 'V', 'value': [1.95, 2.5]}, 'test_current': 0.02}.
- Captured observation: 1.988581.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-081 / op

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 4.2, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 2, 'scope': 'VLMW33 white; not a rating for every PLCC-2 LED; 20 mA,25 C', 'selected_value': 4.2, 'selected_value_path': [1], 'sources': ['https://www.vishay.com/doc?81273'], 'unit': 'V', 'value': [3.7, 4.2]}, 'test_current': 0.02}.
- Captured observation: 3.179538.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-082 / op / blue

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 3.6, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 3, 'scope': 'ASMB-MTB0-0A3A2; IF20 mA,TJ25 C', 'selected_value': 3.6, 'selected_value_path': ['blue', 1], 'sources': ['https://docs.rs-online.com/f6e8/0900766b814caf0e.pdf'], 'unit': 'V', 'value': {'blue': [3.1, 3.6], 'green': [3.1, 3.6], 'red': [2.1, 2.6]}}, 'test_current': 0.02}.
- Captured observation: 3.080177.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-082 / op / green

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 3.6, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 3, 'scope': 'ASMB-MTB0-0A3A2; IF20 mA,TJ25 C', 'selected_value': 3.6, 'selected_value_path': ['green', 1], 'sources': ['https://docs.rs-online.com/f6e8/0900766b814caf0e.pdf'], 'unit': 'V', 'value': {'blue': [3.1, 3.6], 'green': [3.1, 3.6], 'red': [2.1, 2.6]}}, 'test_current': 0.02}.
- Captured observation: 3.080177.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-082 / op / red

- Recorded comparison: passed.
- Contract: {'kind': 'interval', 'maximum': 2.6, 'minimum': 0, 'observable': 'anode_voltage', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'forward_voltage_typical_max', 'page': 3, 'scope': 'ASMB-MTB0-0A3A2; IF20 mA,TJ25 C', 'selected_value': 2.6, 'selected_value_path': ['red', 1], 'sources': ['https://docs.rs-online.com/f6e8/0900766b814caf0e.pdf'], 'unit': 'V', 'value': {'blue': [3.1, 3.6], 'green': [3.1, 3.6], 'red': [2.1, 2.6]}}, 'test_current': 0.02}.
- Captured observation: 2.087601.
- Limits: Explicit color-family proxy at the source test current, checked against its maximum forward voltage. This does not validate the typical curve, thermal/optical model, reverse operation or physical package equivalence.

### OHM-095 / op

- Recorded comparison: passed.
- Contract: {'base_current': 0.0009486832980505137, 'kind': 'interval', 'maximum': 250.0, 'minimum': 100.0, 'observable': 'current_gain', 'source_facts': {'gain_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_maximum_16_bin', 'page': 6, 'scope': 'BCX56-16 only; VCE2 V, IC150 mA, Tamb25 C; no pulse footnote on this row', 'sources': ['https://assets.nexperia.com/documents/data-sheet/BCX56_SER.pdf'], 'unit': '1', 'value': 250}, 'gain_min': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_minimum_16_bin', 'page': 6, 'scope': 'BCX56-16 only; VCE2 V, IC150 mA, Tamb25 C; no pulse footnote on this row', 'sources': ['https://assets.nexperia.com/documents/data-sheet/BCX56_SER.pdf'], 'unit': '1', 'value': 100}, 'gain_test_ic': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_test_collector_current', 'page': 6, 'scope': 'BCX56-16 only; hFE test condition at Tamb25 C; no pulse footnote on this row', 'sources': ['https://assets.nexperia.com/documents/data-sheet/BCX56_SER.pdf'], 'unit': 'A', 'value': 0.15}, 'gain_test_vce': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_test_collector_voltage', 'page': 6, 'scope': 'BCX56-16 only; hFE test condition at Tamb25 C; no pulse footnote on this row', 'sources': ['https://assets.nexperia.com/documents/data-sheet/BCX56_SER.pdf'], 'unit': 'V', 'value': 2}}}.
- Captured observation: 158.11388300841898.
- Limits: One-point DC gain-bin check using a geometric-mean BF and assumed IS. Does not validate gain roll-off, transient response, temperature behavior, ratings or SOA.

### OHM-097 / op

- Recorded comparison: passed.
- Contract: {'base_current': 0.001875, 'kind': 'interval', 'maximum': 160.0, 'minimum': 40.0, 'observable': 'current_gain', 'source_facts': {'gain_max': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_maximum_ungraded', 'page': 1, 'scope': 'Fairchild BD139 ungraded; VCE2 V, IC150 mA, TC25 C; electrical characteristics table, not the separate grade-16 classification', 'sources': ['https://www.farnell.com/datasheets/79944.pdf'], 'unit': '1', 'value': 160}, 'gain_min': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_minimum_ungraded', 'page': 1, 'scope': 'Fairchild BD139 ungraded; VCE2 V, IC150 mA, TC25 C; electrical characteristics table, not the separate grade-16 classification', 'sources': ['https://www.farnell.com/datasheets/79944.pdf'], 'unit': '1', 'value': 40}, 'gain_test_ic': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_test_collector_current', 'page': 1, 'scope': 'Fairchild BD139 ungraded; VCE2 V, IC150 mA, TC25 C; electrical characteristics table, not the separate grade-16 classification', 'sources': ['https://www.farnell.com/datasheets/79944.pdf'], 'unit': 'A', 'value': 0.15}, 'gain_test_vce': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'dc_gain_test_collector_voltage', 'page': 1, 'scope': 'Fairchild BD139 ungraded; VCE2 V, IC150 mA, TC25 C; electrical characteristics table, not the separate grade-16 classification', 'sources': ['https://www.farnell.com/datasheets/79944.pdf'], 'unit': 'V', 'value': 2}}}.
- Captured observation: 80.0.
- Limits: One-point DC gain-bin check using a geometric-mean BF and assumed IS. Does not validate gain roll-off, transient response, temperature behavior, ratings or SOA.

### OHM-098 / op

- Recorded comparison: passed.
- Contract: {'expected': 0.0175, 'tolerance': 0.0005250000000000001}.
- Captured observation: 0.017500070000280005.
- Limits: Isothermal authored fit at 25 C; no SOA, avalanche, board thermal or destructive-failure acceptance. Uses the unchanged B1 relative fit tolerance with the scoped datasheet on-resistance target.

### OHM-099 / op

- Recorded comparison: passed.
- Contract: {'expected': 0.04, 'tolerance': 0.0012000000000000001}.
- Captured observation: 0.04000042857602046.
- Limits: Isothermal authored fit at 25 C; no SOA, avalanche, board thermal or destructive-failure acceptance. Uses the unchanged B1 relative fit tolerance with the scoped datasheet on-resistance target.

### OHM-102 / op

- Recorded comparison: passed.
- Contract: {'expected': 0.085, 'tolerance': 0.00255}.
- Captured observation: 0.08499975714355103.
- Limits: Isothermal authored fit at 25 C; no SOA, avalanche, board thermal or destructive-failure acceptance. Uses the unchanged B1 relative fit tolerance with the scoped datasheet on-resistance target.
