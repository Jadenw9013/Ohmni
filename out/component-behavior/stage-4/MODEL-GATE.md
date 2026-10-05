# Stage 4 model gate

> Generated from recipes, scoped records and revalidated runtime receipts.

Registered bindings: 17. Bindings with current passing runtime comparisons: 17.
Runtime comparison results: {'passed': 27}.
Stage acceptance remains blocked by the separately recorded audit failures. Runtime comparisons only cover the measurement stated in each receipt; they do not establish complete model accuracy, ratings or safe operation.

| Entry | Source status before → after | Bound reference | Runtime comparisons / blockers |
| --- | --- | --- | --- |
| OHM-103 | partial → partial | 4N35; base open | Current runtime comparisons pass; limits below apply |
| OHM-104 | complete → complete | NE555 / NE555 P PDIP-8 | Current runtime comparisons pass; limits below apply |
| OHM-105 | complete → complete | SN74HC00 / SN74HC00 N PDIP-14 | Current runtime comparisons pass; limits below apply |
| OHM-106 | complete → complete | SN74HC595 / SN74HC595 N PDIP-16 | Current runtime comparisons pass; limits below apply |
| OHM-107 | complete → complete | SN74HC245 / SN74HC245 N PDIP-20 | Current runtime comparisons pass; limits below apply |
| OHM-108 | research_required → research_required | Unbound | Physical package width mismatch prevents automatic binding. |
| OHM-109 | partial → partial | Unbound | Missing critical output-current/power/thermal ratings and no validated interface-only recipe. |
| OHM-110 | complete → complete | NE555 / NE555 D SOIC-8 | Current runtime comparisons pass; limits below apply |
| OHM-111 | complete → complete | SN74HC00 / SN74HC00 D SOIC-14 | Current runtime comparisons pass; limits below apply |
| OHM-112 | complete → complete | SN74HC595 / SN74HC595 D SOIC-16 | Current runtime comparisons pass; limits below apply |
| OHM-113 | complete → complete | SN74HC245 / SN74HC245 DW SOIC-20 wide | Current runtime comparisons pass; limits below apply |
| OHM-114 | complete → complete | NE555 / NE555 PW TSSOP-8 | Current runtime comparisons pass; limits below apply |
| OHM-115 | complete → complete | SN74HC00 / SN74HC00 PW TSSOP-14 | Current runtime comparisons pass; limits below apply |
| OHM-116 | complete → complete | SN74HC595 / SN74HC595 PW TSSOP-16 | Current runtime comparisons pass; limits below apply |
| OHM-117 | complete → complete | SN74HC245 / SN74HC245 PW TSSOP-20 | Current runtime comparisons pass; limits below apply |
| OHM-118 | complete → complete | SN74HC595 / SN74HC595 DB SSOP-16 | Current runtime comparisons pass; limits below apply |
| OHM-119 | complete → complete | LM358DGKR / LM358DGKR DGK VSSOP-8; original LM358,not B/BA | Current runtime comparisons pass; limits below apply |
| OHM-120 | partial → partial | TLV70033 / TLV70033 DDC SOT-23-5 | Current runtime comparisons pass; limits below apply |
| OHM-121 | partial → partial | Unbound | No validated TPS3808 supervisor model; pin/rating data alone does not implement the function. |
| OHM-122 | partial → partial | Unbound | No validated interface-only recipe; firmware/protocol behavior is not simulable. |
| OHM-123 | partial → partial | Unbound | Physical body mismatch and unresolved rating-critical DC footnotes prevent automatic runtime binding. |
| OHM-124 | partial → partial | Unbound | No validated interface-only recipe; firmware execution is not simulable. |
| OHM-125 | partial → partial | Unbound | No validated interface-only recipe; firmware execution is not simulable. |
| OHM-126 | partial → partial | Unbound | No validated interface-only recipe; firmware execution is not simulable. |
| OHM-127 | complete → complete | Unbound | The authored averaged buck exports regulated OUT after an internal inductor; TPS62130 exposes SW, VOS and FB separately. Binding SW to OUT would change electrical truth. External L/C and loop validation remain unimplemented. |
| OHM-128 | partial → partial | Unbound | Missing rating-critical thermal/total-current data and no validated interface recipe. |
| OHM-129 | partial → partial | Unbound | Missing thermal evidence and no validated interface recipe. |
| OHM-130 | partial → partial | Unbound | No validated interface recipe and missing rating-critical thermal/per-pin limits. |
| OHM-131 | partial → partial | Unbound | Exposed-pad electrical role and interface-only model unresolved. |
| OHM-132 | partial → partial | Unbound | Unknown central-pad electrical connection prevents runtime binding. |
| OHM-133 | partial → partial | Unbound | TPS7A8001 adjustable FB, NR and EN functions do not match the authored fixed AMS1117 model. A source-bound adjustable control/thermal model remains unimplemented. |
| OHM-134 | complete → complete | Unbound | TPS62160 switch node SW is not the post-inductor OUT of the authored averaged buck. External L/C, feedback and loop validation remain unimplemented. |
| OHM-135 | partial → partial | Unbound | Missingthermal/supplystresslimits; no validated interface recipe. |
| OHM-136 | research_required → research_required | Unbound | No validated electrical-interface recipe and missing rating-critical current/thermal evidence. |
| OHM-137 | partial → partial | Unbound | No validated interface recipe or complete pin-specific rating evaluator. |
| OHM-138 | partial → partial | Unbound | No validated interface recipe or configuration-specific ratings. |
| OHM-139 | partial → partial | Unbound | Physical mismatch and no validated interface model. |
| OHM-140 | complete → complete | Unbound | No validated power-switch recipe including programmed limit and RCP behavior. |
| OHM-141 | partial → partial | Unbound | Missing reference-specific motional parameters and physical-envelope mismatch prevent a sourced runtime binding. |
| OHM-142 | partial → partial | Unbound | Missing reference-specific motional parameters and physical-envelope mismatch prevent a sourced runtime binding. |
| OHM-143 | partial → partial | Unbound | Missing reference-specific motional parameters and unvalidated physical terminal permutation. |
| OHM-144 | partial → partial | Unbound | Missing reference-specific motional parameters and unvalidated physical terminal permutation. |
| OHM-145 | partial → partial | Unbound | Missing reference-specific motional parameters and unvalidated physical terminal permutation. |
| OHM-146 | partial → partial | SiT8008 7050,3.3V,20MHz,industrial; OE tied toVDD | Current runtime comparisons pass; limits below apply |
| OHM-147 | partial → partial | Unbound | Unresolved rating-critical output/thermal data and physical mismatch. |
| OHM-148 | partial → partial | Unbound | Missing rating-critical drive limit and primary terminal map; no sourced runtime binding. |
| OHM-149 | partial → partial | Unbound | Input-power/DC rating interpretation and complete source-mask model validation unresolved. |
| OHM-150 | partial → partial | Unbound | Rating-critical working voltage and full mating/thermal context unresolved. |
| OHM-151 | partial → partial | Unbound | Rating-critical working voltage and full mating/thermal context unresolved. |
| OHM-152 | partial → partial | Unbound | Rating-critical working voltage and full mating/thermal context unresolved. |
| OHM-153 | partial → partial | Unbound | Rating-critical working voltage and full mating/thermal context unresolved. |
| OHM-154 | partial → partial | Unbound | Rating-critical working voltage and full mating/thermal context unresolved. |
| OHM-155 | partial → partial | Unbound | No executable package/reference binding. No source-backed absolute Rth or all-loaded derating curve;0.8blanketfactor remains assumption.; Mating-cycle endurance and crimp resistance are unestablished;do not use Molex values.; Cable pin1 can be any application net;keying does not standardize battery polarity.; Initial/conditioned resistance ceilings do not establish the spec6/12mohm typical proxies. |
| OHM-156 | partial → partial | Unbound | No executable package/reference binding. No source-backed absolute Rth or all-loaded derating curve;0.8blanketfactor remains assumption.; Mating-cycle endurance and crimp resistance are unestablished;do not use Molex values.; Cable pin1 can be any application net;keying does not standardize battery polarity.; Initial/conditioned resistance ceilings do not establish the spec6/12mohm typical proxies. |
| OHM-157 | partial → partial | Unbound | No executable package/reference binding. No source-backed absolute Rth or all-loaded derating curve;0.8blanketfactor remains assumption.; Mating-cycle endurance and crimp resistance are unestablished;do not use Molex values.; Cable pin1 can be any application net;keying does not standardize battery polarity.; Initial/conditioned resistance ceilings do not establish the spec6/12mohm typical proxies. |
| OHM-158 | partial → partial | Unbound | Rating-critical exact-reference voltage,temperature and current conditions unresolved. |
| OHM-159 | partial → partial | Unbound | Rating-critical operating-temperature/derating and validated resistance model unresolved. |
| OHM-160 | partial → partial | Unbound | Rating-critical operating-temperature/derating and validated resistance model unresolved. |
| OHM-161 | partial → partial | Unbound | Rating-critical mating derating/thermal context and validated contact-path model unresolved. |
| OHM-162 | partial → partial | Unbound | Exact source-backed pin-function and physical map plus validated contact model unavailable. |
| OHM-163 | partial → partial | Unbound | Missing validated pin-function/physical-terminal binding; USB protocol is not simulable. |
| OHM-164 | partial → partial | Unbound | Rating-critical scope and terminal binding unresolved; no USB protocol simulation. |
| OHM-165 | partial → partial | Unbound | Missing exact contact rating and physical map; USB/PD protocols not simulable. |
| OHM-166 | partial → partial | Unbound | Rating unit/scope and pin-function binding not closed; USB protocol not simulable. |
| OHM-167 | partial → partial | Unbound | Unvalidated reference footprint and signal map; HDMI protocol is not simulable. |
| OHM-168 | partial → partial | Unbound | Missing Type C map/contact resistance; HDMI protocol is not simulable. |
| OHM-169 | partial → partial | Unbound | Missing exact terminal map/contact ratings; no PHY/protocol simulation. |
| OHM-170 | partial → partial | Unbound | Physical/permutation mapping unresolved; do not assign telephony polarity from memory. |
| OHM-171 | partial → partial | Unbound | Missing maximum voltage and default physical binding. |
| OHM-172 | partial → partial | Unbound | Rating-critical limits and physical binding remain unresolved. |
| OHM-173 | partial → partial | Unbound | Safety-critical polarity and thermal derating unresolved. |
| OHM-174 | partial → partial | Unbound | Safety-critical variant, polarity and thermal scope unresolved. |
| OHM-175 | partial → partial | Unbound | Missing rating-critical current/voltage; RF transmission validity requires a sourced launch model. |
| OHM-176 | partial → partial | Unbound | Missing current/power rating and validated physical map. |
| OHM-177 | partial → partial | Unbound | Rating-critical fields and exact physical binding unresolved. |
| OHM-178 | partial → partial | Unbound | Unvalidated physical/cable pin mapping and load-temperature derating. |
| OHM-179 | partial → partial | Unbound | Exact physical mapping missing; SD protocol not simulable. |
| OHM-180 | partial → partial | Unbound | Default physical binding unresolved; SD protocol not simulable. |

## Implementation and remaining scope

CircuitIR instances compile through the existing NgspiceAdapter. Models are inlined, terminal permutations remain explicit, and the runtime enforces tnom/temp25 C. MOSFET cards require IS=0, regulator templates retain nodesets, and pin strays return to ground. Source stimuli support explicit DC voltage/current and typed PWL test waveforms. AC circuit analysis is not yet implemented.

No source status was promoted. Unbound entries remain refused. Tantalum reverse/temperature policy and other condition-sensitive ratings require the later ratings stage; reference-function joins for package and mixed-function entries require the IC binding work. L3 protocol behavior remains outside ngspice.

A named alternate binding does not silently replace the default: Coilcraft RF, S2M PN and BAT42W proxy records name their scope and package selection explicitly. No generic purchased part is verified by selecting an OHM reference.


## Captured measurements

### OHM-103 / op / default

- Recorded comparison: passed.
- Contract: [{'expected': 5.0, 'kind': 'absolute', 'scale': 1000, 'supply': 'supply', 'tolerance': 0.005}].
- Captured observation: {'samples': 1, 'minimum': 5.0, 'maximum': 5.0}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-104 / op / default

- Recorded comparison: passed.
- Contract: [{'kind': 'interval', 'maximum': 13.3, 'minimum': 12.75, 'node': 'OUT'}].
- Captured observation: {'samples': 1, 'minimum': 13.3, 'maximum': 13.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-105 / op / high

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'Y1', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y2', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y3', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y4', 'tolerance': 0.043}].
- Captured observation: {'samples': 4, 'minimum': 4.3, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-105 / op / low

- Recorded comparison: passed.
- Contract: [{'expected': 0.26, 'kind': 'absolute', 'node': 'Y1', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y2', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y3', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y4', 'tolerance': 0.0026}].
- Captured observation: {'samples': 4, 'minimum': 0.26, 'maximum': 0.26}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-106 / tran / default

- Recorded comparison: passed.
- Contract: [{'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QA', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QB', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QC', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QD', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QE', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QF', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QG', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QH', 'supply_voltage': 4.5, 'time': 2.4e-06}].
- Captured observation: {'samples': 8, 'minimum': 0.02887463009768764, 'maximum': 4.477722772056458}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-107 / op / a_to_b

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'B1', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B2', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B3', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B4', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B5', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B6', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B7', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B8', 'tolerance': 0.0026}].
- Captured observation: {'samples': 8, 'minimum': 0.26, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-107 / op / b_to_a

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'A1', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A2', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A3', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A4', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A5', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A6', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A7', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A8', 'tolerance': 0.0026}].
- Captured observation: {'samples': 8, 'minimum': 0.26, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-107 / op / disabled

- Recorded comparison: passed.
- Contract: [{'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B1', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B2', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B3', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B4', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B5', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B6', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B7', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B8', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 N PDIP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}].
- Captured observation: {'samples': 8, 'minimum': 2.249989, 'maximum': 2.249989}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-110 / op / default

- Recorded comparison: passed.
- Contract: [{'kind': 'interval', 'maximum': 13.3, 'minimum': 12.75, 'node': 'OUT'}].
- Captured observation: {'samples': 1, 'minimum': 13.3, 'maximum': 13.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-111 / op / high

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'Y1', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y2', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y3', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y4', 'tolerance': 0.043}].
- Captured observation: {'samples': 4, 'minimum': 4.3, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-111 / op / low

- Recorded comparison: passed.
- Contract: [{'expected': 0.26, 'kind': 'absolute', 'node': 'Y1', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y2', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y3', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y4', 'tolerance': 0.0026}].
- Captured observation: {'samples': 4, 'minimum': 0.26, 'maximum': 0.26}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-112 / tran / default

- Recorded comparison: passed.
- Contract: [{'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QA', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QB', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QC', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QD', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QE', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QF', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QG', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QH', 'supply_voltage': 4.5, 'time': 2.4e-06}].
- Captured observation: {'samples': 8, 'minimum': 0.02887463009768764, 'maximum': 4.477722772056458}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-113 / op / a_to_b

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'B1', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B2', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B3', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B4', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B5', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B6', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B7', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B8', 'tolerance': 0.0026}].
- Captured observation: {'samples': 8, 'minimum': 0.26, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-113 / op / b_to_a

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'A1', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A2', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A3', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A4', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A5', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A6', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A7', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A8', 'tolerance': 0.0026}].
- Captured observation: {'samples': 8, 'minimum': 0.26, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-113 / op / disabled

- Recorded comparison: passed.
- Contract: [{'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B1', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B2', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B3', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B4', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B5', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B6', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B7', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B8', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 DW SOIC-20 wide A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}].
- Captured observation: {'samples': 8, 'minimum': 2.249989, 'maximum': 2.249989}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-114 / op / default

- Recorded comparison: passed.
- Contract: [{'kind': 'interval', 'maximum': 13.3, 'minimum': 12.75, 'node': 'OUT'}].
- Captured observation: {'samples': 1, 'minimum': 13.3, 'maximum': 13.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-115 / op / high

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'Y1', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y2', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y3', 'tolerance': 0.043}, {'expected': 4.3, 'kind': 'absolute', 'node': 'Y4', 'tolerance': 0.043}].
- Captured observation: {'samples': 4, 'minimum': 4.3, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-115 / op / low

- Recorded comparison: passed.
- Contract: [{'expected': 0.26, 'kind': 'absolute', 'node': 'Y1', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y2', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y3', 'tolerance': 0.0026}, {'expected': 0.26, 'kind': 'absolute', 'node': 'Y4', 'tolerance': 0.0026}].
- Captured observation: {'samples': 4, 'minimum': 0.26, 'maximum': 0.26}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-116 / tran / default

- Recorded comparison: passed.
- Contract: [{'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QA', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QB', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QC', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QD', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QE', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QF', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QG', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QH', 'supply_voltage': 4.5, 'time': 2.4e-06}].
- Captured observation: {'samples': 8, 'minimum': 0.02887463009768764, 'maximum': 4.477722772056458}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-117 / op / a_to_b

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'B1', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B2', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B3', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B4', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B5', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B6', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'B7', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'B8', 'tolerance': 0.0026}].
- Captured observation: {'samples': 8, 'minimum': 0.26, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-117 / op / b_to_a

- Recorded comparison: passed.
- Contract: [{'expected': 4.3, 'kind': 'absolute', 'node': 'A1', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A2', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A3', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A4', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A5', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A6', 'tolerance': 0.0026}, {'expected': 4.3, 'kind': 'absolute', 'node': 'A7', 'tolerance': 0.043}, {'expected': 0.26, 'kind': 'absolute', 'node': 'A8', 'tolerance': 0.0026}].
- Captured observation: {'samples': 8, 'minimum': 0.26, 'maximum': 4.3}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-117 / op / disabled

- Recorded comparison: passed.
- Contract: [{'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B1', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B2', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B3', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B4', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B5', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B6', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B7', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}, {'derivation': 'Ideal10kohm/10kohm divider: VCC/2 +/- source off-state current maximum times5kohm Thevenin resistance.', 'kind': 'interval', 'maximum': 2.275, 'minimum': 2.225, 'node': 'B8', 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'off_state_output_leakage_max', 'page': 5, 'scope': 'SN74HC245 PW TSSOP-20 A/B pins; VO0orVCC,VCC6V,TA-40..85C', 'sources': ['https://www.ti.com/lit/ds/symlink/sn74hc245.pdf'], 'unit': 'uA', 'value': 5}}].
- Captured observation: {'samples': 8, 'minimum': 2.249989, 'maximum': 2.249989}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-118 / tran / default

- Recorded comparison: passed.
- Contract: [{'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QA', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QB', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QC', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QD', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QE', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QF', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 0, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QG', 'supply_voltage': 4.5, 'time': 2.4e-06}, {'derivation': 'Exact locked bit order; voltage classification uses the authored HC input thresholds, with the undefined band rejected.', 'expected': 1, 'high_fraction': 0.7, 'kind': 'logic', 'low_fraction': 0.3, 'node': 'QH', 'supply_voltage': 4.5, 'time': 2.4e-06}].
- Captured observation: {'samples': 8, 'minimum': 0.02887463009768764, 'maximum': 4.477722772056458}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-119 / op / default

- Recorded comparison: passed.
- Contract: [{'derivation': 'Two identical channels: sum of two unchanged B5 single-amplifier current contracts. Recipe retains its authored input offset rather than silently setting it to zero.', 'expected': 4.7, 'kind': 'absolute', 'scale': 1000, 'supply': 'supply', 'tolerance': 0.047}].
- Captured observation: {'samples': 1, 'minimum': 4.706, 'maximum': 4.706}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-120 / op / default

- Recorded comparison: passed.
- Contract: [{'expected': 2.9115, 'kind': 'absolute', 'node': 'OUT', 'tolerance': 0.014557500000000001}].
- Captured observation: {'samples': 1, 'minimum': 2.911468, 'maximum': 2.911468}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-146 / op / current

- Recorded comparison: passed.
- Contract: [{'kind': 'interval', 'maximum': 4.5, 'minimum': 0, 'scale': 1000, 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'quiescent_current_max', 'page': 1, 'scope': 'SiT8008 7050,3.3V,industrial,OE option; 20MHz,no load,3.3V option', 'sources': ['https://www.sitime.com/sites/default/files/mature-datasheets/SiT8008-datasheet.pdf'], 'unit': 'mA', 'value': 4.5}, 'supply': 'supply'}].
- Captured observation: {'samples': 1, 'minimum': 3.8, 'maximum': 3.8}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.

### OHM-146 / tran / frequency

- Recorded comparison: passed.
- Contract: [{'after': 0.005, 'derivation': 'Same f0*(1+ppm) contract at explicit20MHz variant; unchanged1Hz absolute tolerance. Source B1 measures200 periods from rise10 to210. Startup is5ms source maximum instead of5us bench demonstration.', 'expected': 20000500.0, 'kind': 'frequency', 'node': 'OUT', 'rise_end': 210, 'rise_start': 10, 'source_fact': {'basis': 'MFR_DATASHEET', 'confidence': 'H', 'detail': None, 'field': 'quiescent_current_test_frequency', 'page': 1, 'scope': 'SiT8008 3.3V current table condition20MHz,no load; explicitly selected runtime frequency,not a claim that all SiT8008 parts have this nominal frequency.', 'sources': ['https://www.sitime.com/sites/default/files/mature-datasheets/SiT8008-datasheet.pdf'], 'unit': 'MHz', 'value': 20}, 'threshold': 1.65, 'tolerance': 1.0}].
- Captured observation: {'samples': 1, 'minimum': 20000500.000001557, 'maximum': 20000500.000001557}.
- Limits: Package pin mapping and the explicitly named analytical observables only. This is not complete electrical, thermal, timing, rating or physical-package verification. Authored model assumptions remain visible.
