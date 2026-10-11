# Per-part simulation model cards

Each card below replaces a shared authored class card for one reference part. Fitted parameters
(IS, N, RS) are not written here: the runtime binds them from the part's own gapfill
`field_updates` (`spice_*_fit`), where each value carries its datasheet page, figure, read points,
residuals and confidence. Parameters not fitted are carried over unchanged from the authored
card in `docs/behavior/bench/beh-led-indicator/models.inc` and remain as stated there.

- OHM-074: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card.
- OHM-077: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card.
- OHM-079: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card.
- OHM-080: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card.
- OHM-081: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=60p VJ=1.0 M=0.33 TT=0 BV=5.5 IBV=10u EG=3.9 XTI=3)`; non-fitted terms from the authored LED_WHITE card.
- OHM-073: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card.
- OHM-082: three dies on a common anode; red uses `red_IS/red_N/red_RS`, green and blue share the datasheet's single GREEN/BLUE trace fit `gb_IS/gb_N/gb_RS` (the source does not separate them); non-fitted terms from the authored LED_RGB_R and LED_RGB_GB cards.
- OHM-075: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card (D070).
- OHM-076: `D{ref} {A} {K} LEDP_{ref}` with `.model LEDP_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; non-fitted terms from the authored LED_RED card (D070).
- OHM-084: the BEH-LED-ADDRESSABLE class template with the three channel duties fixed at full white, `B{ref}load {VDD} {VSS} I = {iq} + 3*{ich}*min(max((v({VDD},{VSS})-3.0)/0.5,0),1)` and `RIN{ref} {DIN} {VSS} 100Meg`; iq and ich are bound from the WS2812B-V7 sheet, the 3.0 V / 0.5 V knee stays the class's authored assumption (D070).
- OHM-087: one diode per segment, `D{ref}<SEG> {<SEG>} {COM} SEG_{ref}` for A, B, C, D, E, F, G and DP, sharing `.model SEG_{ref} D (IS={IS} N={N} RS={RS} CJO=30p VJ=1.0 M=0.33 TT=0 BV=15 IBV=10u EG=2.2 XTI=3)`; pins 3 and 8 are one internal common cathode (role COM); non-fitted terms from the authored LED_RED card; this expands the BEH-DISP-LEDARRAY `D{ref}_{seg} {SEG} {COM}` pattern (D070).
- OHM-088: the OHM-087 card expanded to sixteen segments, A1..DP1 on COM1 and A2..DP2 on COM2, sharing one `.model SEG_{ref}` with the same terms (D070).
- OHM-091: the BEH-DISP-LCD1602 class template with the assumed backlight diode `BL` replaced by `R{ref}bl {A} {K} {rbl}`, where rbl = vled_typ/iled_typ from the single sourced backlight point (5.0 V / 130 mA); `B{ref}idd {VDD} {VSS} I = {idd}` and `RV0{ref} {V0} {VSS} 100Meg` are unchanged (D070).
