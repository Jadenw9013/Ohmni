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
