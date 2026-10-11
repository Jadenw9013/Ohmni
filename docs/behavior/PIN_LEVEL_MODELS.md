# Pin-level reset-state models (D075)

Owner decision (2026-10-11, session chat): programmable devices are bound as pin-level electrical models frozen in their datasheet-documented reset state. Firmware is not modeled.

Generated template (`ohmni.behavior.netlist.pin_level_template` from the recipe's `pin_level` block):

- `X{ref}_<ROLE> {<ROLE>} {ref}_<ROLE>_din {ref}_<ROLE>_und {<GND>} {<GND>} <PU> {<SUPPLY>} {<GND>} <subckt> <parameters>` for every pad role. dout and oe are tied to the ground role, so the output stage is disabled and no logic state is invented. pu is tied to `{ref}_pu`, a 1 V internal node (`V{ref}_pu {ref}_pu {<GND>} DC 1`), only for a pad whose reset-state pull-up the source states; otherwise it is tied to the ground role. `<subckt>` is `dio_pin` (hashed `docs/behavior/bench/ic-digital-io/dio.lib`, BEH-IC-DIGITAL-IO) or `dio_pin_ft` (`docs/behavior/models/dio_ft.lib`: the same pad without the upper clamp diode, for pins whose source states no clamp to the supply). Supply, tied and unmodeled roles get no element: there is no core or peripheral current model.
- Pull-up value: the sourced typical when the source gives one, else the midpoint (min+max)/2 of the sourced range. The runtime probe checks the resulting current against the whole sourced range, not the midpoint.
- Drive fit (ATmega328P only; unreachable while oe = 0): roh = (VCC_test - VOH_min)/IOH_test and rol = VOL_max/IOL_test, the BEH-IC-DIGITAL-IO 7.4 limit-point fit applied to the sourced DS40002061B points (VOL 0.9 V at 20 mA and 5 V, not the spec's 0.4 V).
- Pin capacitance, where sourced: the typical CIO (STM32) or the maximum die capacitance (XC7A35T) as cpin; otherwise the asset's 4 pF.

Bound parts (each recipe's `pin_level` block lists its pads, rails, tied and unmodeled roles):

- OHM-122: ATmega328P-AU / ATmega328P-AU 32A TQFP-32; 23 pads (1 without the upper clamp), reset-state pull-ups on PC6_RESET; rails VCC; 3 unmodeled roles.
- OHM-123: ATmega32U4-AU / ATmega32U4 TQFP-44; 26 pads (1 without the upper clamp), reset-state pull-ups on PF4, PF5, PF7, RESET; rails VCC; 10 unmodeled roles.
- OHM-124: STM32F405RGT6 / STM32F405RGT6 LQFP64; 44 pads (41 without the upper clamp), reset-state pull-ups on NRST; rails VDD; 12 unmodeled roles.
- OHM-125: STM32F407VGT6 / STM32F407VGT6 LQFP100; 75 pads (72 without the upper clamp), reset-state pull-ups on NRST; rails VDD; 13 unmodeled roles.
- OHM-126: STM32F407ZGT6 / STM32F407ZGT6 LQFP144; 107 pads (104 without the upper clamp), reset-state pull-ups on NRST; rails VDD; 14 unmodeled roles.
- OHM-131: STM32F103CBU6 / STM32F103CBU6 UFQFPN48; 31 pads (19 without the upper clamp), reset-state pull-ups on NRST, PA13, PA15, PB4; rails VDD1; 9 unmodeled roles.
- OHM-138: XC7A35T / XC7A35T FTG256, unconfigured (JTAG mode, PUDC_B high); 170 pads (0 without the upper clamp), reset-state pull-ups on none; rails VCCINT, VCCBRAM, VCCAUX, VCCO_0, VCCO_14, VCCO_15, VCCO_34, VCCO_35; 17 unmodeled roles.
