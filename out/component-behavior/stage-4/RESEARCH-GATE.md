# stage-4: research gate

> Script-generated from gapfill records and current-run ngspice receipts.

Entries: 20. Research outcomes: {'sources_reviewed': 20}.
Status upgrades: 0.
Class bench results do not establish package ratings or full physical-device validity.

| Entry | Before | After | Research | Sources / fields | Class benches |
| --- | --- | --- | --- | --- | --- |
| [OHM-103](../../../docs/behavior/gapfill/OHM-103.md) | partial | partial | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-104](../../../docs/behavior/gapfill/OHM-104.md) | complete | complete | sources_reviewed | 1 / 14 | 0/3 PASS |
| [OHM-105](../../../docs/behavior/gapfill/OHM-105.md) | complete | complete | sources_reviewed | 1 / 16 | 0/3 PASS |
| [OHM-106](../../../docs/behavior/gapfill/OHM-106.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-107](../../../docs/behavior/gapfill/OHM-107.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-108](../../../docs/behavior/gapfill/OHM-108.md) | research_required | research_required | sources_reviewed | 2 / 12 | 0/3 PASS |
| [OHM-109](../../../docs/behavior/gapfill/OHM-109.md) | partial | partial | sources_reviewed | 1 / 10 | 0/3 PASS |
| [OHM-110](../../../docs/behavior/gapfill/OHM-110.md) | complete | complete | sources_reviewed | 1 / 14 | 0/3 PASS |
| [OHM-111](../../../docs/behavior/gapfill/OHM-111.md) | complete | complete | sources_reviewed | 1 / 16 | 0/3 PASS |
| [OHM-112](../../../docs/behavior/gapfill/OHM-112.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-113](../../../docs/behavior/gapfill/OHM-113.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-114](../../../docs/behavior/gapfill/OHM-114.md) | complete | complete | sources_reviewed | 1 / 14 | 0/3 PASS |
| [OHM-115](../../../docs/behavior/gapfill/OHM-115.md) | complete | complete | sources_reviewed | 1 / 16 | 0/3 PASS |
| [OHM-116](../../../docs/behavior/gapfill/OHM-116.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-117](../../../docs/behavior/gapfill/OHM-117.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-118](../../../docs/behavior/gapfill/OHM-118.md) | complete | complete | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-119](../../../docs/behavior/gapfill/OHM-119.md) | complete | complete | sources_reviewed | 1 / 14 | 0/3 PASS |
| [OHM-120](../../../docs/behavior/gapfill/OHM-120.md) | partial | partial | sources_reviewed | 1 / 16 | 0/3 PASS |
| [OHM-121](../../../docs/behavior/gapfill/OHM-121.md) | partial | partial | sources_reviewed | 1 / 13 | 0/3 PASS |
| [OHM-122](../../../docs/behavior/gapfill/OHM-122.md) | partial | partial | sources_reviewed | 2 / 11 | 0/8 PASS |

## Remaining work and conflicts

### OHM-103: DIP-6 IC

- remaining: Package thetaJA and temperature derating are not established;70mW limits apply only at25C.
- remaining: CTR is a minimum at one operating point, not a calibrated transfer curve.
- remaining: Isolation test voltage5000VRMS is not a continuous working-voltage or mains-safety approval.
- conflicts: The primary Rev1.2 diagram confirms5=C,6=B; the spec Rev1.8 extract swap is rejected for this explicit revision.
- conflicts: Primary source prints70V VCEO absolute but guarantees30V BVCEO; preserve both and use30V conservative ceiling.
- conflicts: Spec package default Tj150C and2.5W cannot override4N35 Tj100C/70mW.

### OHM-104: DIP-8 IC

- remaining: Generic latch/threshold model remains a behavioural approximation; measured timing and supply-current behavior are separate.
- remaining: Board thermal path and package parasitics require application-specific evidence.
- conflicts: Only the NE555 reference and this package thermal column are bound; other listed ICs are not interchangeable.

### OHM-105: DIP-14 IC

- remaining: Thermal board conditions and actual switching/load behavior remain application-specific.
- remaining: Input leakage unit conflict prevents treating the spec1uA value as re-verified.
- conflicts: The commercial p5 table literally prints +/-1000 uA maximum input leakage; military p6 and sibling HC tables use nA. Do not silently correct the source unit.
- conflicts: Package default median thermal value is replaced only for this reference by its own sourced column.

### OHM-106: DIP-16 IC

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-107: DIP-20 IC

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-108: DIP-28 IC

- remaining: Firmware/peripherals cannot be simulated in ngspice; any later model must be interface-only.
- remaining: Junction thermal parameters,pin capacitance and dynamic pad model remain unresolved.
- conflicts: The retained research combines explicitly named2009 electrical and2012 summary revisions; exact modern ordering-revision reconciliation remains open.
- conflicts: Spec package Tj150C/theta50C/W is not sourced for this MCU and cannot become a rating.
- conflicts: ATmega328P-PU uses0.300-inch/7.62mm narrow DIP, not library OHM-10815.24mm wide DIP. Electrical terminal numbers recorded; physical binding blocked.
- blockers: Physical package width mismatch prevents automatic binding.

### OHM-109: DIP-40 IC

- remaining: CPU instruction execution is not simulable with this ngspice layer.
- remaining: Absolute output-current,power and junction-temperature limits are not provided in the read rating table; do not guess.
- remaining: I/O capacitance/leakage applies only to named pins and conditions.
- blockers: Missing critical output-current/power/thermal ratings and no validated interface-only recipe.

### OHM-110: SOIC-8

- remaining: Generic latch/threshold model remains a behavioural approximation; measured timing and supply-current behavior are separate.
- remaining: Board thermal path and package parasitics require application-specific evidence.
- conflicts: Only the NE555 reference and this package thermal column are bound; other listed ICs are not interchangeable.

### OHM-111: SOIC-14

- remaining: Thermal board conditions and actual switching/load behavior remain application-specific.
- remaining: Input leakage unit conflict prevents treating the spec1uA value as re-verified.
- conflicts: The commercial p5 table literally prints +/-1000 uA maximum input leakage; military p6 and sibling HC tables use nA. Do not silently correct the source unit.
- conflicts: Package default median thermal value is replaced only for this reference by its own sourced column.

### OHM-112: SOIC-16

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-113: SOIC-20

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-114: TSSOP-8

- remaining: Generic latch/threshold model remains a behavioural approximation; measured timing and supply-current behavior are separate.
- remaining: Board thermal path and package parasitics require application-specific evidence.
- conflicts: Only the NE555 reference and this package thermal column are bound; other listed ICs are not interchangeable.

### OHM-115: TSSOP-14

- remaining: Thermal board conditions and actual switching/load behavior remain application-specific.
- remaining: Input leakage unit conflict prevents treating the spec1uA value as re-verified.
- conflicts: The commercial p5 table literally prints +/-1000 uA maximum input leakage; military p6 and sibling HC tables use nA. Do not silently correct the source unit.
- conflicts: Package default median thermal value is replaced only for this reference by its own sourced column.

### OHM-116: TSSOP-16

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-117: TSSOP-20

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-118: SSOP-16

- remaining: The complete sequential or bidirectional state model needs runtime binding and bench validation.
- remaining: Current limits are per output and total supply separately; do not multiply the per-pin rating by pin count.
- remaining: Package parasitics and actual board thermal path remain approximate.

### OHM-119: MSOP-8

- remaining: Output current depends on source/sink,voltage and temperature; no universal current cap is established here.
- remaining: Package series parasitics,noise and fault behavior are not validated.
- conflicts: VSSOP DGK lead span4.9mm is not a certification of the library MSOP contact centers4.35mm apart. Keep physical mismatch explicit.
- conflicts: Original LM358 supply32V absolute/30V recommended must not be replaced by LM358B40V/36V values.

### OHM-120: SOT-23-5 IC

- remaining: Current limit spans220..860mA atVOUT0.9nom; it is not a safe200mA overload allowance.
- remaining: Startup,loop stability and reverse current require dedicated validation.
- conflicts: The LDO binds TLV70033 only; alternate MCP6001/MCP73831/TLV9061 pin maps cannot be substituted.

### OHM-121: SOT-23-6 IC

- remaining: There is no authored canonical supervisor class; do not relabel a package-only placeholder as its executable function.
- remaining: Timed reset and CT behavior remain unimplemented.
- blockers: No validated TPS3808 supervisor model; pin/rating data alone does not implement the function.

### OHM-122: QFP-32

- remaining: Firmware/peripherals cannot be simulated in ngspice; any later model must be interface-only.
- remaining: Junction thermal parameters,pin capacitance and dynamic pad model remain unresolved.
- conflicts: The retained research combines explicitly named2009 electrical and2012 summary revisions; exact modern ordering-revision reconciliation remains open.
- conflicts: Spec package Tj150C/theta50C/W is not sourced for this MCU and cannot become a rating.
- blockers: No validated interface-only recipe; firmware/protocol behavior is not simulable.
