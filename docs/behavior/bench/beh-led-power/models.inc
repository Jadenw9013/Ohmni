* XP-E2-class white power LED, parameters fitted at Tj=85 C to Cree XP-E2 Rev 8D Vf points (3.05 V @700 mA, 3.15 V @1000 mA), N=3 assumed.
* TNOM=85 so the card reproduces the datasheet points at Tj=85 C. Tempco set by EG (about -3 mV/K, ASSUMPTION).
.model LED_XPE2 D (IS=1.87e-14 N=3.0 RS=0.2233 CJO=300p VJ=1.0 M=0.33 BV=5 IBV=10u EG=3.9 XTI=3 TNOM=85)
