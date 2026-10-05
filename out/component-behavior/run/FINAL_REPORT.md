# Component behavior final report

> Script-generated from this run's structured checkpoint, source, bench and state records.

Run: `behavior-20261005T065040Z`. Branch: `codex/behavior-audit`.
Run state: **hard_stopped**. Hard stop: **ngspice_42_unavailable**.

## Stage-by-stage results

| Stage | Result in this run |
| --- | --- |
| audit | FAIL — see checkpoint checks |
| stage2 | NOT RUN / dependent work blocked |
| stage3 | NOT RUN / dependent work blocked |
| stage4 | NOT RUN / dependent work blocked |
| stage5 | NOT RUN / dependent work blocked |
| stage6 | NOT RUN / dependent work blocked |
| stage7 | NOT RUN / dependent work blocked |

Audit-software regression results and component-corpus audit results are separate. A passing unit test is not a bench run.

## Exact coverage totals

Records: 180. Before: {'complete': 18, 'partial': 144, 'research_required': 18}. After: {'complete': 18, 'partial': 144, 'research_required': 18}.
Current-run benchmark gate: **FAIL** — 0/205 canonical bench references passed; 21 additional authored netlists lack a canonical contract.
Source gate: **FAIL** — 41/63 cited URLs have successful hashed fetches.
Recorded fetch attempts: 65; distinct attempted URLs: 63.

## Simulator availability

Command: `ngspice -v`. Exit: `None`. Version gate: **FAIL**.

```text
[WinError 2] The system cannot find the file specified
```

## Checkpoints and canaries

| Checkpoint | Rule | Result | Detail |
| --- | --- | --- | --- |
| 001-audit | AUD-RULE-001 | PASS | rule hash 730f651999bc31c7e9db55deb1beac59d05da9aa2d9d9a89ec6f1f20eb53a1c7 matches state |
| 001-audit | AUD-CANARY-001 | PASS | 7/7 canaries rejected as expected |
| 001-audit | AUD-SOURCE-001 | FAIL | 41/63 cited URLs have successful hashed fetches |
| 001-audit | AUD-UPGRADE-001 | PASS | 0 status upgrades checked |
| 001-audit | AUD-VENDOR-001 | PASS | all vendor_model labels have attached compatible models |
| 001-audit | AUD-SPEC-001 | PASS | generated projection and approved LED permutation are current |
| 001-audit | AUD-BENCH-001 | FAIL | 0/205 canonical bench references passed; 21 additional authored netlists lack a canonical contract |
| 001-audit | AUD-PROTECT-001 | PASS | main, production checkout, remote refs and protected paths match baseline |
| 001-audit | AUD-COVERAGE-001 | PASS | 180 records and 180 coverage rows |
| 001-audit | AUD-VERIFY-001 | PASS | 0 completed research-stage verifier reports checked |
| 001-audit | AUD-RESUME-001 | PASS | run state is complete and parseable |
| 001-audit | AUD-REGRESSION-001 | PASS | 3 locked regression commands ran |
| 001-audit | AUD-HONESTY-001 | PASS | all recorded UI/code claims preserve non-run and violation status |
| 001-audit | canary: invented_parameter | PASS | Rejected by AUD-SOURCE-001 |
| 001-audit | canary: non_run_marked_pass | PASS | Rejected by AUD-HONESTY-001 |
| 001-audit | canary: swapped_led_permutation | PASS | Rejected by AUD-SPEC-001 |
| 001-audit | canary: unledgered_source | PASS | Rejected by AUD-SOURCE-001 |
| 001-audit | canary: upgrade_without_bench | PASS | Rejected by AUD-UPGRADE-001 |
| 001-audit | canary: vendor_model_without_file | PASS | Rejected by AUD-VENDOR-001 |
| 001-audit | canary: wrong_bench_expected | PASS | Rejected by AUD-BENCH-001 |
| 002-audit-final | AUD-RULE-001 | PASS | rule change is explicitly recorded as non-loosening |
| 002-audit-final | AUD-CANARY-001 | PASS | 7/7 canaries rejected as expected |
| 002-audit-final | AUD-SOURCE-001 | FAIL | 41/63 cited URLs have successful hashed fetches |
| 002-audit-final | AUD-UPGRADE-001 | PASS | 0 status upgrades checked |
| 002-audit-final | AUD-VENDOR-001 | PASS | all vendor_model labels have attached compatible models |
| 002-audit-final | AUD-SPEC-001 | PASS | generated projection and approved LED permutation are current |
| 002-audit-final | AUD-BENCH-001 | FAIL | 0/205 canonical bench references passed; 21 additional authored netlists lack a canonical contract |
| 002-audit-final | AUD-PROTECT-001 | PASS | main, production checkout, remote refs and protected paths match baseline |
| 002-audit-final | AUD-COVERAGE-001 | PASS | 180 records and 180 coverage rows |
| 002-audit-final | AUD-VERIFY-001 | PASS | 0 completed research-stage verifier reports checked |
| 002-audit-final | AUD-RESUME-001 | PASS | run state is complete and parseable |
| 002-audit-final | AUD-REGRESSION-001 | PASS | 4 locked regression commands ran |
| 002-audit-final | AUD-HONESTY-001 | PASS | all recorded UI/code claims preserve non-run and violation status |
| 002-audit-final | canary: invented_parameter | PASS | Rejected by AUD-SOURCE-001 |
| 002-audit-final | canary: non_run_marked_pass | PASS | Rejected by AUD-HONESTY-001 |
| 002-audit-final | canary: swapped_led_permutation | PASS | Rejected by AUD-SPEC-001 |
| 002-audit-final | canary: unledgered_source | PASS | Rejected by AUD-SOURCE-001 |
| 002-audit-final | canary: upgrade_without_bench | PASS | Rejected by AUD-UPGRADE-001 |
| 002-audit-final | canary: vendor_model_without_file | PASS | Rejected by AUD-VENDOR-001 |
| 002-audit-final | canary: wrong_bench_expected | PASS | Rejected by AUD-BENCH-001 |

## Blocked and parked items

- **AUD-BENCH-001:** 0/205 canonical bench references passed; 21 additional authored netlists lack a canonical contract
- **AUD-SOURCE-001:** 41/63 cited URLs have successful hashed fetches; named citations without resolved URLs also remain unresolved. See checkpoint 002 for every source issue.
- **stage2:** NOT RUN. The failed corpus checkpoint blocks dependent work; ngspice 42 is unavailable. Independent inventory, supplied-URL fetching, coverage and audit remediation were performed; full gap research and the later product implementations remain unfinished.
- **stage3:** NOT RUN. The failed corpus checkpoint blocks dependent work; ngspice 42 is unavailable. Independent inventory, supplied-URL fetching, coverage and audit remediation were performed; full gap research and the later product implementations remain unfinished.
- **stage4:** NOT RUN. The failed corpus checkpoint blocks dependent work; ngspice 42 is unavailable. Independent inventory, supplied-URL fetching, coverage and audit remediation were performed; full gap research and the later product implementations remain unfinished.
- **stage5:** NOT RUN. The failed corpus checkpoint blocks dependent work; ngspice 42 is unavailable. Independent inventory, supplied-URL fetching, coverage and audit remediation were performed; full gap research and the later product implementations remain unfinished.
- **stage6:** NOT RUN. The failed corpus checkpoint blocks dependent work; ngspice 42 is unavailable. Independent inventory, supplied-URL fetching, coverage and audit remediation were performed; full gap research and the later product implementations remain unfinished.
- **stage7:** NOT RUN. The failed corpus checkpoint blocks dependent work; ngspice 42 is unavailable. Independent inventory, supplied-URL fetching, coverage and audit remediation were performed; full gap research and the later product implementations remain unfinished.

## Unresolved check details

### AUD-SOURCE-001

41/63 cited URLs have successful hashed fetches

- AUD-SOURCE-001: missing successful archived fetch: https://NXP.com/docs/en/application-note/AN12442.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://atom.ubbcluj.ro/alpar/datasheets/optoelectronic_components/LED/Untinted%20Non-Diffused%20LED%20(B)%20-%20Vishay.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://cdn1.components.ru/81/35081.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://engineering.purdue.edu/ece477/Archive/2008/Fall/F08-Grp02/datasheets/e60900232.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://onlinedocs.microchip.com/oxy/GUID-2ACDA668-0A87-46A1-B7FC-9DC74A5461AD-en-US-2/GUID-9D6E52D1-BC20-4009-8F14-35F680E0A5EC.html
- AUD-SOURCE-001: missing successful archived fetch: https://pdf.jiepei.com/as-103-13781511.html
- AUD-SOURCE-001: missing successful archived fetch: https://static.chipdip.ru/lib/143/DOC013143963.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://static.chipdip.ru/lib/150/DOC036150746.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://static.chipdip.ru/lib/442/DOC030442603.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://supplychain.molex.com/content/dam/molex/molex-dot-com/en_us/pdf/datasheets/987652-0671.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://uk.rs-online.com/web/p/pulse-transformers/1634318
- AUD-SOURCE-001: missing successful archived fetch: https://www.amphenolrf.com/en-us/assets/file/4065861601/
- AUD-SOURCE-001: missing successful archived fetch: https://www.coilcraft.com/en-us/files/datasheet/XAL40xx
- AUD-SOURCE-001: missing successful archived fetch: https://www.digikey.at/en/products/detail/abracon-llc/AFS869S3-T/675442
- AUD-SOURCE-001: missing successful archived fetch: https://www.digikey.ca/en/products/detail/TY-145P/237-1121-ND/242643
- AUD-SOURCE-001: missing successful archived fetch: https://www.digikey.it/en/products/detail/amgis-llc/AS-103/2260664
- AUD-SOURCE-001: missing successful archived fetch: https://www.e-sonic.com/productfiles/mf-pul/h315.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.molex.com/en-us/products/part-detail/732511150?display=pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/application_note/an2867-guidelines-for-oscillator-design-on-stm8afals-and-stm32-mcusmpus-stmicroelectronics.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.svmicrowave.com/images/uploaded/Solderless_PCB_Edge_Launch_Connectors_Application_Note.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.we-online.com/components/media/o868432v410
- AUD-SOURCE-001: missing successful archived fetch: https://www.zeuthen.desy.de/~sulanke/Projects/ICECUBE/mDOM/mainboard/datasheets/transformer_eth_H1102NL_+.pdf
- BEH-CAP-ALEL: named source requires URL-to-document resolution: S11
- BEH-CAP-ALEL: named source requires URL-to-document resolution: S12
- BEH-CAP-ALEL: named source requires URL-to-document resolution: S13
- BEH-CAP-ALEL: named source requires URL-to-document resolution: S14
- BEH-CAP-ALEL: named source requires URL-to-document resolution: S26
- BEH-CAP-ALPOLY: named source requires URL-to-document resolution: S11
- BEH-CAP-ALPOLY: named source requires URL-to-document resolution: S15
- BEH-CAP-ALPOLY: named source requires URL-to-document resolution: S17
- BEH-CAP-ALPOLY: named source requires URL-to-document resolution: S19
- BEH-CAP-ALPOLY: named source requires URL-to-document resolution: S26
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S1
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S2
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S3
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S4
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S5
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S6
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S7
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S8
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S9
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S10
- BEH-CAP-CERAMIC: named source requires URL-to-document resolution: S26
- BEH-CAP-EDLC: named source requires URL-to-document resolution: S23
- BEH-CAP-EDLC: named source requires URL-to-document resolution: S24
- BEH-CAP-EDLC: named source requires URL-to-document resolution: S25
- BEH-CAP-EDLC: named source requires URL-to-document resolution: S26
- BEH-CAP-FILM: named source requires URL-to-document resolution: S20
- BEH-CAP-FILM: named source requires URL-to-document resolution: S21
- BEH-CAP-FILM: named source requires URL-to-document resolution: S26
- BEH-CAP-MICA: named source requires URL-to-document resolution: S22
- BEH-CAP-MICA: named source requires URL-to-document resolution: S26
- BEH-CAP-TANT: named source requires URL-to-document resolution: S16
- BEH-CAP-TANT: named source requires URL-to-document resolution: S17
- BEH-CAP-TANT: named source requires URL-to-document resolution: S18
- BEH-CAP-TANT: named source requires URL-to-document resolution: S19
- BEH-CAP-TANT: named source requires URL-to-document resolution: S26
- BEH-CON-AUDIO: named source requires URL-to-document resolution: S20
- BEH-CON-AUDIO: named source requires URL-to-document resolution: S21
- BEH-CON-AUDIO: named source requires URL-to-document resolution: S22
- BEH-CON-DCJACK: named source requires URL-to-document resolution: 03/11/2025
- BEH-CON-DCJACK: named source requires URL-to-document resolution: S1
- BEH-CON-DCJACK: named source requires URL-to-document resolution: CUI Devices (Same Sky)
- BEH-CON-DCJACK: named source requires URL-to-document resolution: PJ-102A DC Power Jack datasheet rev 1.07
- BEH-CON-DCJACK: named source requires URL-to-document resolution: 24 Vdc, 2.5 A, 30 mohm, 5000 cycles, IR, temperature
- BEH-CON-DCJACK: named source requires URL-to-document resolution: n/a
- BEH-CON-DCJACK: named source requires URL-to-document resolution: S2
- BEH-CON-DCJACK: named source requires URL-to-document resolution: CUI (hosted by UConn course page)
- BEH-CON-DCJACK: named source requires URL-to-document resolution: PJ-102A DC Power Jack Datasheet (older copy)
- BEH-CON-DCJACK: named source requires URL-to-document resolution: 16 Vdc, 50/30 mohm, 500 Vac, 9.0 mm insertion depth, center pin 2.0, 3 terminals
- BEH-CON-FFC: named source requires URL-to-document resolution: 2010.9
- BEH-CON-FFC: named source requires URL-to-document resolution: S11
- BEH-CON-FFC: named source requires URL-to-document resolution: Hirose
- BEH-CON-FFC: named source requires URL-to-document resolution: FH12 Series FPC/FFC connector sheet (2010.9)
- BEH-CON-FFC: named source requires URL-to-document resolution: 0.5 A, 70% rule, 50 V AC, 50 mohm, 20 cycles, FPC thickness, temperature
- BEH-CON-HDMI: named source requires URL-to-document resolution: S12
- BEH-CON-HDMI: named source requires URL-to-document resolution: S13
- BEH-CON-HDMI: named source requires URL-to-document resolution: S14
- BEH-CON-HEADER: named source requires URL-to-document resolution: S1
- BEH-CON-HEADER: named source requires URL-to-document resolution: S2
- BEH-CON-HEADER: named source requires URL-to-document resolution: S3
- BEH-CON-HEADER: named source requires URL-to-document resolution: S4
- BEH-CON-MODJACK: named source requires URL-to-document resolution: S15
- BEH-CON-MODJACK: named source requires URL-to-document resolution: S16
- BEH-CON-MODJACK: named source requires URL-to-document resolution: S17
- BEH-CON-MODJACK: named source requires URL-to-document resolution: S18
- BEH-CON-MODJACK: named source requires URL-to-document resolution: S19
- BEH-CON-RF: named source requires URL-to-document resolution: 2009.2w
- BEH-CON-RF: named source requires URL-to-document resolution: S5
- BEH-CON-RF: named source requires URL-to-document resolution: Hirose
- BEH-CON-RF: named source requires URL-to-document resolution: Ultra Small Surface Mount Coaxial Connectors, U.FL Series (doc 2009.2w)
- BEH-CON-RF: named source requires URL-to-document resolution: 50 ohm, DC-6 GHz, VSWR, 30 cycles, contact resistance
- BEH-CON-RF: named source requires URL-to-document resolution: n/a
- BEH-CON-RF: named source requires URL-to-document resolution: S6
- BEH-CON-RF: named source requires URL-to-document resolution: Amphenol RF
- BEH-CON-RF: named source requires URL-to-document resolution: SMA Panel Mount Receptacles
- BEH-CON-RF: named source requires URL-to-document resolution: VSWR 1.15, DC-18 GHz, torque, 500 cycles, 2.0 mohm
- BEH-CON-RF: named source requires URL-to-document resolution: n/a
- BEH-CON-RF: named source requires URL-to-document resolution: S7
- BEH-CON-RF: named source requires URL-to-document resolution: Cytech Systems (distributor listing, Amphenol 132134)
- BEH-CON-RF: named source requires URL-to-document resolution: 132134 product page
- BEH-CON-RF: named source requires URL-to-document resolution: 50 ohm, 18 GHz max, 500 cycles, BeCu gold, PTFE
- BEH-CON-RF: named source requires URL-to-document resolution: n/a
- BEH-CON-RF: named source requires URL-to-document resolution: S8
- BEH-CON-RF: named source requires URL-to-document resolution: Molex
- BEH-CON-RF: named source requires URL-to-document resolution: 73251-1150 part detail page
- BEH-CON-RF: named source requires URL-to-document resolution: 50 ohm, 18 GHz, 500 Vrms
- BEH-CON-RF: named source requires URL-to-document resolution: Rev 2 (05/28)
- BEH-CON-RF: named source requires URL-to-document resolution: S9
- BEH-CON-RF: named source requires URL-to-document resolution: SV Microwave
- BEH-CON-RF: named source requires URL-to-document resolution: Solderless PCB Edge Launch Connectors Application Note Rev. 2 (05/28)
- BEH-CON-RF: named source requires URL-to-document resolution: VSWR 1.0-2.0 plots, torque
- BEH-CON-RF: named source requires URL-to-document resolution: n/a
- BEH-CON-RF: named source requires URL-to-document resolution: S10
- BEH-CON-RF: named source requires URL-to-document resolution: Copper Mountain Technologies
- BEH-CON-RF: named source requires URL-to-document resolution: Optimal fixture design with end launch SMA connectors
- BEH-CON-RF: named source requires URL-to-document resolution: small flat pin, fringing capacitance, CPWG guidance
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: n/a
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: S12
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: Hirose
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: DM3 Series microSD card connectors
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: microSD 8-pin names, 0.5 A, 125 V AC, 40 mohm, 10000 cycles, detect switch NO
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: n/a
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: S13
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: WERI (Wurth family listing 693 063 010 911)
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: SD Card Connector push-pull with card detection
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: 0.5 A, 100 VAC, 100 mohm, 10000 cycles, CD and WP switch states
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: n/a
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: S14
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: Molex
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: Memory card sockets 987652-0671
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: 0.5 A, 500 V AC, 100 mohm, 500-10000 cycles, CD on most models
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: n/a
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: S15
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: Cactus Technologies
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: An Introduction To SD Card Interface
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: SD mode pin table, 2.7-3.3 V
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: Rev 1.0
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: S16
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: Transcend
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: SDXC card series technical specification Rev. 1.0
- BEH-CON-SDSOCKET: named source requires URL-to-document resolution: SD/SPI pin table, 2.7-3.6 V, 15/100/200/500 mA, pull-ups 10-100 kohm, pin 1 10-90 kohm
- BEH-CON-TERMINAL: named source requires URL-to-document resolution: S1
- BEH-CON-TERMINAL: named source requires URL-to-document resolution: S2
- BEH-CON-TERMINAL: named source requires URL-to-document resolution: S3
- BEH-CON-USB: named source requires URL-to-document resolution: S1
- BEH-CON-USB: named source requires URL-to-document resolution: S2
- BEH-CON-USB: named source requires URL-to-document resolution: S3
- BEH-CON-USB: named source requires URL-to-document resolution: S4
- BEH-CON-USB: named source requires URL-to-document resolution: S5
- BEH-CON-USB: named source requires URL-to-document resolution: S6
- BEH-CON-USB: named source requires URL-to-document resolution: S7
- BEH-CON-USB: named source requires URL-to-document resolution: S8
- BEH-CON-USB: named source requires URL-to-document resolution: S9
- BEH-CON-USB: named source requires URL-to-document resolution: S10
- BEH-CON-USB: named source requires URL-to-document resolution: S11
- BEH-CON-WTB: named source requires URL-to-document resolution: S1
- BEH-CON-WTB: named source requires URL-to-document resolution: S2
- BEH-CON-WTB: named source requires URL-to-document resolution: S3
- BEH-CON-XT: named source requires URL-to-document resolution: v1.2
- BEH-CON-XT: named source requires URL-to-document resolution: S3
- BEH-CON-XT: named source requires URL-to-document resolution: Changzhou Amass Electronics
- BEH-CON-XT: named source requires URL-to-document resolution: XT60-F and XT60-M specification, version 1.2
- BEH-CON-XT: named source requires URL-to-document resolution: 30 A, 60 A peak, 0.55 mohm, 500 V DC, -20..120 C, 1000 cycles, 12 AWG
- BEH-CON-XT: named source requires URL-to-document resolution: V1.2
- BEH-CON-XT: named source requires URL-to-document resolution: S4
- BEH-CON-XT: named source requires URL-to-document resolution: Changzhou Amass Electronics
- BEH-CON-XT: named source requires URL-to-document resolution: XT30PW-M specification V1.2
- BEH-CON-XT: named source requires URL-to-document resolution: 15 A, 30 A peak, 0.80 mohm, 500 V, 1000 cycles
- BEH-DIO-BRIDGE: named source requires URL-to-document resolution: 10-Oct-06
- BEH-DIO-BRIDGE: named source requires URL-to-document resolution: S19
- BEH-DIO-BRIDGE: named source requires URL-to-document resolution: Vishay
- BEH-DIO-BRIDGE: named source requires URL-to-document resolution: DF005M thru DF10M Single-Phase Bridge Rectifier doc 88571
- BEH-DIO-BRIDGE: named source requires URL-to-document resolution: VRRM, IF(AV), IFSM, VF, IR, CJ, RthJA, polarity statement
- BEH-DIO-PN: named source requires URL-to-document resolution: 07-Nov-2024
- BEH-DIO-PN: named source requires URL-to-document resolution: S1
- BEH-DIO-PN: named source requires URL-to-document resolution: Vishay
- BEH-DIO-PN: named source requires URL-to-document resolution: 1N4148 small signal fast switching diode (doc 81857 rev 1.6)
- BEH-DIO-PN: named source requires URL-to-document resolution: ratings, VF max, IR, BV, Cd, trr
- BEH-DIO-SCHOTTKY: named source requires URL-to-document resolution: 23-Apr-2020
- BEH-DIO-SCHOTTKY: named source requires URL-to-document resolution: S10
- BEH-DIO-SCHOTTKY: named source requires URL-to-document resolution: Vishay
- BEH-DIO-SCHOTTKY: named source requires URL-to-document resolution: SS12 thru SS16 Surface Mount Schottky Barrier Rectifier doc 88746
- BEH-DIO-SCHOTTKY: named source requires URL-to-document resolution: ratings, leakage, thermal
- BEH-DIO-TVS: named source requires URL-to-document resolution: 09-Jan-2024
- BEH-DIO-TVS: named source requires URL-to-document resolution: S16
- BEH-DIO-TVS: named source requires URL-to-document resolution: Vishay
- BEH-DIO-TVS: named source requires URL-to-document resolution: SMBJ5.0A thru SMBJ188CA doc 88392
- BEH-DIO-TVS: named source requires URL-to-document resolution: PPPM, VWM, VBR, VC, IPP, ID, TC, IFSM, RthJA
- BEH-DIO-ZENER: named source requires URL-to-document resolution: 07-Nov-2024
- BEH-DIO-ZENER: named source requires URL-to-document resolution: S15
- BEH-DIO-ZENER: named source requires URL-to-document resolution: Vishay
- BEH-DIO-ZENER: named source requires URL-to-document resolution: BZX55 series Zener diodes doc 85604 Rev 2.0
- BEH-DIO-ZENER: named source requires URL-to-document resolution: VZ, rZ, TC, IR, Ptot, RthJA
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: not shown
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: S10
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: Hitachi
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: HD44780U
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: instruction set, init, timing
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: 2000-06-13
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: S11
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: Sitronix
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: ST7066 V1.2
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: timing, supply, instruction codes
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: not shown
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: S13
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: Winstar
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: WH1602B
- BEH-DISP-LCD1602: named source requires URL-to-document resolution: pins, supply, contrast
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: 2003-01-09
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: S14
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: Kingbright
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: SC56-11EWA, DSAA5198 V.2
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: segment ratings and VF
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: 2013-05-13
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: S15
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: Kingbright
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: TC23-11CGKWA V.4A
- BEH-DISP-LEDARRAY: named source requires URL-to-document resolution: matrix ratings
- BEH-DISP-OLED-I2C: named source requires URL-to-document resolution: Rev 1.1 April 2008
- BEH-DISP-OLED-I2C: named source requires URL-to-document resolution: S12
- BEH-DISP-OLED-I2C: named source requires URL-to-document resolution: Solomon Systech
- BEH-DISP-OLED-I2C: named source requires URL-to-document resolution: SSD1306 128x64 Dot Matrix OLED/PLED Segment/Common Driver
- BEH-DISP-OLED-I2C: named source requires URL-to-document resolution: supply, I2C address, control byte, commands, reset
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: 2020-04-01 (as printed; may be out of date)
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: S13
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: Murata
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: CSTLS8M00G53-B0 datasheet (CERALOCK with built-in load capacitors)
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: tolerance, stability, aging, 15 pF, R1 25 ohm
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: n/a
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: S14
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: Murata
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: CSTLS_G series page
- BEH-FREQ-CERRES: named source requires URL-to-document resolution: 3.40-10.00 MHz, +/-0.5 %, -20..+80 C, 47 pF type, discontinued flag
- BEH-FREQ-SAW: named source requires URL-to-document resolution: not shown
- BEH-FREQ-SAW: named source requires URL-to-document resolution: S15
- BEH-FREQ-SAW: named source requires URL-to-document resolution: Abracon
- BEH-FREQ-SAW: named source requires URL-to-document resolution: AFS869S3 SAW filter datasheet
- BEH-FREQ-SAW: named source requires URL-to-document resolution: 869 MHz, IL 4.5 dB, ripple 1.5, 35 dB, 50 ohm, pins 2/5, temperature, 10 dBm, ESD warning
- BEH-FREQ-SAW: named source requires URL-to-document resolution: n/a
- BEH-FREQ-SAW: named source requires URL-to-document resolution: S16
- BEH-FREQ-SAW: named source requires URL-to-document resolution: DigiKey / Lion Circuits (distributors)
- BEH-FREQ-SAW: named source requires URL-to-document resolution: AFS869S3-T product pages
- BEH-FREQ-SAW: named source requires URL-to-document resolution: bandwidth 8 MHz, 6 pins, 10 V DC (low trust)
- BEH-FREQ-XO: named source requires URL-to-document resolution: not shown
- BEH-FREQ-XO: named source requires URL-to-document resolution: S11
- BEH-FREQ-XO: named source requires URL-to-document resolution: SiTime
- BEH-FREQ-XO: named source requires URL-to-document resolution: SiT8008 low power programmable oscillator datasheet (mature)
- BEH-FREQ-XO: named source requires URL-to-document resolution: supply, current, startup, jitter, pinout, abs max, ESD
- BEH-FREQ-XO: named source requires URL-to-document resolution: 2021-02-16 (REVISED 2.16.2021)
- BEH-FREQ-XO: named source requires URL-to-document resolution: S12
- BEH-FREQ-XO: named source requires URL-to-document resolution: Abracon
- BEH-FREQ-XO: named source requires URL-to-document resolution: AST3TQ53 TCXO/VCTCXO
- BEH-FREQ-XO: named source requires URL-to-document resolution: stability ppb, aging, supply, output types, pins, package 5.0x3.2x1.6
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: not shown in extraction
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S1
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: STMicroelectronics
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: AN2867 Guidelines for oscillator design on STM8AF/AL/S and STM32 MCUs/MPUs
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: BVD circuit, Fs/Fa/Fp, CL formula, gm_crit, drive level, Sf, start-up, overdrive effects
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 2022-09-07
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S2
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Abracon
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ABLS Series HC49/US (AT49) SMD microprocessor crystal, drawing 450669 Rev AD
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ESR table, C0 7 pF, CL 18 pF, DL, tolerance, stability, aging, DLD
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: not shown
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S3
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Epson
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: FC-135R / FC-135 crystal unit
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 32.768 kHz: C1 3.4 fF, C0 1.0 pF, R1 70 kohm, parabolic -0.04 ppm/C2, DL 0.5 uW
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 2020 (c)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S4
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Epson
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: FA-238V / FA-238 / TSX-3225 crystal units
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ESR, DL 200 uW max/10 uW rec, aging, 4-pad pad assignment (2,4 = lid GND)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: not shown
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S5
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: NDK
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: NX3225GD crystal unit (automotive)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 8 MHz ESR 500 ohm max, DL 10 uW (max 200 uW), tolerance +/-50 ppm, stability +/-150 ppm
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: revised 04-25-22
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S6
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Abracon
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ABM3 ceramic SMD crystal (5.0 x 3.2 mm)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ESR 140 ohm at 8 MHz, C0 7 pF, CL 18 pF, DL 10-100 uW, aging
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 2024 (upload path)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S7
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Suntsu Electronics
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Crystal Equivalent Circuit
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: C1 0.005-0.030 pF fundamental, C0 1-7 pF, Thomson relation
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: n/a
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S8
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Microchip
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Recommended Crystal Characteristics (online documentation page, device family not shown)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: typical Cm 1.3-9 fF, C0 <= 3 pF, ESR <= 80-100 ohm
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 2021-07
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S9
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: Texas Instruments
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: SLLA549 TCAN455x clock optimization and design guidelines
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: start-up tau = 2*Lm/(R+Rneg), Rneg = -gm/(w^2*2*CL^2), safety 3-5x, Rd 50-100 ohm
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 2019-06
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S10
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: NXP
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: AN12442 Theoretical set up checks for MPC5510 XOSC use, Rev 0
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: 8 MHz example, gm_opt formula (cross-check only)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: n/a
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: S17
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ngspice project
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: ngspice manual (B sources, .tran uic, .meas)
- BEH-FREQ-XTAL: named source requires URL-to-document resolution: B-source tanh, .meas syntax
- BEH-IC-CHARGER-SOT235: named source requires URL-to-document resolution: S20, S25, S29
- BEH-IC-COMPARATOR: named source requires URL-to-document resolution: S3, S29
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S7
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S8
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S9
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S10
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S12
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S13
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S14
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S15
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S16
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S17
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S18
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S19
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S23
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S24
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S25
- BEH-IC-DIGITAL-IF: named source requires URL-to-document resolution: S26
- BEH-IC-DIGITAL-IO: named source requires URL-to-document resolution: S16, S17, S19, S23, S24
- BEH-IC-DRIVER-DIP16: named source requires URL-to-document resolution: S10, S12, S29
- BEH-IC-LDO-SOT235: named source requires URL-to-document resolution: S14, S31, S29
- BEH-IC-LOGIC-HC: named source requires URL-to-document resolution: S4, S5, S8, S29
- BEH-IC-LOGIC-SEQ: named source requires URL-to-document resolution: S4, S6, S7, S29
- BEH-IC-OPAMP: named source requires URL-to-document resolution: S2, S9, S11, S18, S29
- BEH-IC-OPTO-DIP6: named source requires URL-to-document resolution: S22, S29
- BEH-IC-PKGBIND: named source requires URL-to-document resolution: see Part C: S1-S15, S26, S27
- BEH-IC-RS232-DIP16: named source requires URL-to-document resolution: S13, S29
- BEH-IC-TIMER555: named source requires URL-to-document resolution: S1, S29
- BEH-LED-ADDRESSABLE: named source requires URL-to-document resolution: no revision printed in extract
- BEH-LED-ADDRESSABLE: named source requires URL-to-document resolution: S9
- BEH-LED-ADDRESSABLE: named source requires URL-to-document resolution: Worldsemi
- BEH-LED-ADDRESSABLE: named source requires URL-to-document resolution: WS2812B Intelligent control LED integrated light source
- BEH-LED-ADDRESSABLE: named source requires URL-to-document resolution: pins, timing, VDD, thresholds, GRB format, LED data
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: 14-Oct-14
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: S1
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: Vishay
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: TLDR4400 Rev 2.0
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: 3 mm deep red ratings, VF, Iv, red fit
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: 29-Apr-13
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: S2
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: Vishay
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: TLHB5800 Rev 2.0
- BEH-LED-INDICATOR: named source requires URL-to-document resolution: blue ratings, VF points
- BEH-LED-POWER: named source requires URL-to-document resolution: Rev 8D
- BEH-LED-POWER: named source requires URL-to-document resolution: S8
- BEH-LED-POWER: named source requires URL-to-document resolution: Cree
- BEH-LED-POWER: named source requires URL-to-document resolution: XLamp XP-E2 LEDs data sheet
- BEH-LED-POWER: named source requires URL-to-document resolution: VF, Rth_js, Tj max, VR, ESD, flux vs I and T
- BEH-LED-RGB: named source requires URL-to-document resolution: 2014-09-10
- BEH-LED-RGB: named source requires URL-to-document resolution: S7
- BEH-LED-RGB: named source requires URL-to-document resolution: Broadcom
- BEH-LED-RGB: named source requires URL-to-document resolution: ASMB-MTB0-0A3A2
- BEH-LED-RGB: named source requires URL-to-document resolution: pin map, VF, ratings
- BEH-MAG-CMC: named source requires URL-to-document resolution: 2025/08/05
- BEH-MAG-CMC: named source requires URL-to-document resolution: S8
- BEH-MAG-CMC: named source requires URL-to-document resolution: Wurth Elektronik
- BEH-MAG-CMC: named source requires URL-to-document resolution: ANP146a common mode choke theory
- BEH-MAG-CMC: named source requires URL-to-document resolution: DM/CM principle, k, leakage, equivalent circuit
- BEH-MAG-CMC: named source requires URL-to-document resolution: 2026-02-06
- BEH-MAG-CMC: named source requires URL-to-document resolution: S9
- BEH-MAG-CMC: named source requires URL-to-document resolution: Wurth Elektronik
- BEH-MAG-CMC: named source requires URL-to-document resolution: WE-SL5 744272222 datasheet
- BEH-MAG-CMC: named source requires URL-to-document resolution: L, LS, RDC, IR, VR, Z points
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: 9/09
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: S11
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: Pulse Electronics
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: H325.Q 10/100BASE-T single port surface mount magnetics
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: turns ratios, IL, RL, CMR, crosstalk, hipot 1500 Vrms
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: 5/09
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: S12
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: Pulse Engineering
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: H315.D 10/100BASE-T single port transformer modules
- BEH-MAG-ETHMAG: named source requires URL-to-document resolution: OCL 350 uH with 8 mA bias, 1500 Vrms
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: rev 07/22/17
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: S1
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: Coilcraft
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: Doc 469 inductor parameter definitions
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: Isat drop definitions, Irms, DCR, SRF
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: rev 02/25/26
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: S2
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: Coilcraft
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: XAL40xx shielded power inductors, Doc 806-1
- BEH-MAG-INDUCTOR: named source requires URL-to-document resolution: 30 % Isat, Irms 20/40 K, table rows
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: 07/18
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: S13
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: Talema Group
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: AS series current sense transformers datasheet (CERN-hosted copy)
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: family ranges, pins, burden, isolation, temperature
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: 06-06
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: S14
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: Talema Group
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: AS-103 / AS-211 datasheet copies (pdf.jiepei.com aggregator)
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: AS-103 row
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: not shown
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: S15
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: Talema/Amgis via DigiKey
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: AS-103 listing
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: conflicting 1:300 and 250 mH
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: not shown
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: S16
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: Elliott Sound Products
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: Current Transformers
- BEH-MAG-XFMR-CT: named source requires URL-to-document resolution: open-secondary warning (engineering article, secondary source)
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: 2023-10-19
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: S10
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: Wurth Elektronik
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: Design considerations for flyback transformer (Digital WE Days 2023)
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: gap energy storage, Isat requirement, leakage spike
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: not shown
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: S23
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: Wurth Elektronik
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: 750311691 pulse transformer listing (RS)
- BEH-MAG-XFMR-FLYBACK: named source requires URL-to-document resolution: order of magnitude of WE-FB parameters
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: not shown
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: S22
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: Triad Magnetics
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: TY-145P DigiKey listing
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: 600CT:600CT, 1:1, 200 Hz to 15 kHz
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: not shown
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: S3
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: ngspice
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: ngspice manual
- BEH-MAG-XFMR-SIGNAL: named source requires URL-to-document resolution: L, K syntax
- BEH-MEM-SPINOR: named source requires URL-to-document resolution: S21
- BEH-MEM-SPINOR: named source requires URL-to-document resolution: S22
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S1
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S2
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S3
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S4
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S5
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S6
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S11
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S13
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S16
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S25
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S26
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S27
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S28
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S29
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S30
- BEH-PKG-IC-BINDING: named source requires URL-to-document resolution: S31
- BEH-PWR-LOADSWITCH: named source requires URL-to-document resolution: S4
- BEH-PWR-LOADSWITCH: named source requires URL-to-document resolution: S5
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S1
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S2
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S4
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S5
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S6
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S7
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S10
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S11
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S12
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S13
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S14
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S15
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S16
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S19
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S24
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S25
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S26
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S27
- BEH-PWR-PKGTHERMAL: named source requires URL-to-document resolution: S28
- BEH-REG-BUCK-DCS: named source requires URL-to-document resolution: S1
- BEH-REG-BUCK-DCS: named source requires URL-to-document resolution: S2
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S17
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S18
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S19
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S20
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S21
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S22
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S23
- BEH-REG-LINEAR: named source requires URL-to-document resolution: S31
- BEH-RES-FIXED: named source requires URL-to-document resolution: see S1..S11, S22, S24 at the end of this file
- BEH-RES-NETWORK: named source requires URL-to-document resolution: S17, S18
- BEH-RES-POT: named source requires URL-to-document resolution: S19, S20, S21
- BEH-RES-SENSE: named source requires URL-to-document resolution: S13, S14, S15, S16, S22
- BEH-TRN-BJT: named source requires URL-to-document resolution: S1
- BEH-TRN-BJT: named source requires URL-to-document resolution: S2
- BEH-TRN-BJT: named source requires URL-to-document resolution: S3
- BEH-TRN-BJT: named source requires URL-to-document resolution: S4
- BEH-TRN-BJT: named source requires URL-to-document resolution: S5
- BEH-TRN-BJT: named source requires URL-to-document resolution: S6
- BEH-TRN-BJT: named source requires URL-to-document resolution: S7
- BEH-TRN-BJT: named source requires URL-to-document resolution: S30
- BEH-TRN-BJT: named source requires URL-to-document resolution: S31
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S8
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S9
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S10
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S11
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S12
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S13
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S14
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S15
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S16
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S28
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S29
- BEH-TRN-MOSFET: named source requires URL-to-document resolution: S31
- MCP1700T-3302E-TT/SOT-23: external citation has no fetched URL: DS20001826F
- MCP1700T-3302E-TT/SOT-89: external citation has no fetched URL: DS20001826F
- MCP1700T-3302E-TT/TO-92: external citation has no fetched URL: DS20001826F

### AUD-BENCH-001

0/205 canonical bench references passed; 21 additional authored netlists lack a canonical contract

- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-ALEL/B1: measurement not found unambiguously in archived output: |z| at 120 hz (ohm)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-ALEL/B2: measurement not found unambiguously in archived output: p (w)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-ALEL/B3: measurement not found unambiguously in archived output: flag at -1.5 v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-ALEL/B4: measurement not found unambiguously in archived output: esr at -25 c (ohm)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-ALPOLY/B1: measurement not found unambiguously in archived output: f0 (khz)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-ALPOLY/B2: measurement not found unambiguously in archived output: peak current rs=0.1 (a)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-CERAMIC/B1: measurement not found unambiguously in archived output: ceff at 0/1/2/4 v (uf)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-CERAMIC/B2: measurement not found unambiguously in archived output: srf (mhz)
- AUD-BENCH-001: BEH-CAP-CERAMIC/B2: measurement not found unambiguously in archived output: zmin (mohm)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-CERAMIC/B3: measurement not found unambiguously in archived output: v(t0+tau) (v)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-CERAMIC/B4: measurement not found unambiguously in archived output: flag edge (s)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-EDLC/B1: measurement not found unambiguously in archived output: v(tau) (v)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-EDLC/B2: measurement not found unambiguously in archived output: v1/v2 (v)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-EDLC/B3: measurement not found unambiguously in archived output: ipk (a)
- AUD-BENCH-001: BEH-CAP-EDLC/B3: measurement not found unambiguously in archived output: e (j)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-FILM/B1: measurement not found unambiguously in archived output: tan delta at 1 khz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-FILM/B2: measurement not found unambiguously in archived output: f0 (mhz)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-FILM/B3: measurement not found unambiguously in archived output: flag at 400 v amplitude
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-MICA/B1: measurement not found unambiguously in archived output: c at 125 c (pf)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-MICA/B2: measurement not found unambiguously in archived output: q at 1 mhz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-TANT/B1: measurement not found unambiguously in archived output: leakage current (ua)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-TANT/B2: measurement not found unambiguously in archived output: bit 1 edge (v)
- AUD-BENCH-001: BEH-CAP-TANT/B2: measurement not found unambiguously in archived output: bit 8 edge (v)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CAP-TANT/B3: measurement not found unambiguously in archived output: reverse flag edge (v)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-AUDIO/B1: measurement not found unambiguously in archived output: v_before
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-AUDIO/B2: measurement not found unambiguously in archived output: gain
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-DCJACK/B1: measurement not found unambiguously in archived output: v_drop
- AUD-BENCH-001: BEH-CON-DCJACK/B1: measurement not found unambiguously in archived output: dt
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-DCJACK/B2: measurement not found unambiguously in archived output: vload_unplugged
- AUD-BENCH-001: BEH-CON-DCJACK/B2: measurement not found unambiguously in archived output: vload_plugged
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-FFC/B1: measurement not found unambiguously in archived output: v_drop
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-FFC/B2: measurement not found unambiguously in archived output: i_contact1
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-HDMI/B1: measurement not found unambiguously in archived output: vdiff
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-HDMI/B2: measurement not found unambiguously in archived output: vload_first
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-HEADER/B1: measurement not found unambiguously in archived output: v_load
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-HEADER/B2: measurement not found unambiguously in archived output: v(b)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-HEADER/B3: measurement not found unambiguously in archived output: dt
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-HEADER/B4: measurement not found unambiguously in archived output: f3db
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-MODJACK/B1: measurement not found unambiguously in archived output: drop
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-MODJACK/B2: measurement not found unambiguously in archived output: vmin
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-MODJACK/B3: measurement not found unambiguously in archived output: gain
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-RF/B1: measurement not found unambiguously in archived output: vswr
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-RF/B2: measurement not found unambiguously in archived output: gamma_c
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-RF/B3: measurement not found unambiguously in archived output: gamma_step
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-SDSOCKET/B1: measurement not found unambiguously in archived output: v_cd_open
- AUD-BENCH-001: BEH-CON-SDSOCKET/B1: measurement not found unambiguously in archived output: v_cd_closed
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-SDSOCKET/B2: measurement not found unambiguously in archived output: vcc_loaded
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-TERMINAL/B1: measurement not found unambiguously in archived output: flag
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-TERMINAL/B2: measurement not found unambiguously in archived output: dt
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-USB/B1: measurement not found unambiguously in archived output: v_load_5a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-USB/B2: measurement not found unambiguously in archived output: vcc_56k
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-USB/B3: measurement not found unambiguously in archived output: f3db
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-USB/B4: measurement not found unambiguously in archived output: v_dp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-USB/B5: measurement not found unambiguously in archived output: vbus_on_load
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-WTB/B1: measurement not found unambiguously in archived output: i_straight
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-WTB/B2: measurement not found unambiguously in archived output: v_load
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-XT/B1: measurement not found unambiguously in archived output: p_xt60
- AUD-BENCH-001: BEH-CON-XT/B1: measurement not found unambiguously in archived output: dt
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-CON-XT/B2: measurement not found unambiguously in archived output: t63
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-BRIDGE/B1: measurement not found unambiguously in archived output: vpk
- AUD-BENCH-001: BEH-DIO-BRIDGE/B1: measurement not found unambiguously in archived output: vavg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-BRIDGE/B2: measurement not found unambiguously in archived output: ripple
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-BRIDGE/B3: measurement not found unambiguously in archived output: reverse dc current
- AUD-BENCH-001: BEH-DIO-BRIDGE/B3: measurement not found unambiguously in archived output: blocked current
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B1: measurement not found unambiguously in archived output: v at 10 ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B2: measurement not found unambiguously in archived output: trr
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B3: measurement not found unambiguously in archived output: vpk
- AUD-BENCH-001: BEH-DIO-PN/B3: measurement not found unambiguously in archived output: vavg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B4: measurement not found unambiguously in archived output: cj at 4 v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B5: measurement not found unambiguously in archived output: v at 100 ua reverse
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B6: measurement not found unambiguously in archived output: high clamp
- AUD-BENCH-001: BEH-DIO-PN/B6: measurement not found unambiguously in archived output: low clamp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-PN/B7: measurement not found unambiguously in archived output: vf at 100 c, 10 ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B1: measurement not found unambiguously in archived output: v at 1 a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B2: measurement not found unambiguously in archived output: ir 25c
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B2: measurement not found unambiguously in archived output: ir 100c
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B3: measurement not found unambiguously in archived output: tj at ta 60c
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B3: measurement not found unambiguously in archived output: runaway at ta 95c
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-TVS/B1: measurement not found unambiguously in archived output: v at 24.6 a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-TVS/B2: measurement not found unambiguously in archived output: ppeak
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-TVS/B3: measurement not found unambiguously in archived output: v at +/-24.6 a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-ZENER/B1: measurement not found unambiguously in archived output: vz
- AUD-BENCH-001: BEH-DIO-ZENER/B1: measurement not found unambiguously in archived output: rz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-ZENER/B2: measurement not found unambiguously in archived output: vout
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DIO-ZENER/B3: measurement not found unambiguously in archived output: dvout/dvin
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DISP-LCD1602/B1: measurement not found unambiguously in archived output: i_backlight
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DISP-LCD1602/B2: measurement not found unambiguously in archived output: vlcd
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DISP-LEDARRAY/B1: measurement not found unambiguously in archived output: i_led_avg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DISP-LEDARRAY/B2: measurement not found unambiguously in archived output: i_digit_avg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DISP-OLED-I2C/B1: measurement not found unambiguously in archived output: tr 30-70
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-DISP-OLED-I2C/B2: measurement not found unambiguously in archived output: vdd
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-CERRES/B1: measurement not found unambiguously in archived output: f_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-SAW/B1: measurement not found unambiguously in archived output: il_fc_db
- AUD-BENCH-001: BEH-FREQ-SAW/B1: measurement not found unambiguously in archived output: bw3_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-SAW/B2: measurement not found unambiguously in archived output: il_100ohm_db
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XO/B1: measurement not found unambiguously in archived output: f_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XO/B2: measurement not found unambiguously in archived output: vout_max_v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/B1: measurement not found unambiguously in archived output: zmin_ohm
- AUD-BENCH-001: BEH-FREQ-XTAL/B1: measurement not found unambiguously in archived output: fa_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/B2: measurement not found unambiguously in archived output: fl_18pf_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/B3: measurement not found unambiguously in archived output: fl_32k_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/P1: measurement not found unambiguously in archived output: dl_w
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/P2: measurement not found unambiguously in archived output: f_loop_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/P3: measurement not found unambiguously in archived output: f_tran_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/P5: measurement not found unambiguously in archived output: envelope_ratio_at_gm_crit
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-FREQ-XTAL/P6: measurement not found unambiguously in archived output: gm_crit_s
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-CHARGER-SOT235/B1: measurement not found unambiguously in archived output: ibat_a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-CHARGER-SOT235/B2: measurement not found unambiguously in archived output: i_4.19v_ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-CHARGER-SOT235/B3: measurement not found unambiguously in archived output: ibat_a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-COMPARATOR/B1: measurement not found unambiguously in archived output: trip voltage
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-COMPARATOR/B1b: measurement not found unambiguously in archived output: vol
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-COMPARATOR/B2: measurement not found unambiguously in archived output: t_5mv_us
- AUD-BENCH-001: BEH-IC-COMPARATOR/B2: measurement not found unambiguously in archived output: t_ttl_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D1: measurement not found unambiguously in archived output: vol, voh at 5 ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D2: measurement not found unambiguously in archived output: i_inj ma, vpin v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D3: measurement not found unambiguously in archived output: t_release_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D4: measurement not found unambiguously in archived output: idd ma at 1 and 18 mhz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DIGITAL-IO/B1: measurement not found unambiguously in archived output: vol_20ma
- AUD-BENCH-001: BEH-IC-DIGITAL-IO/B1: measurement not found unambiguously in archived output: voh_20ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DIGITAL-IO/B2: measurement not found unambiguously in archived output: pullup_pad_v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DRIVER-DIP16/B1: measurement not found unambiguously in archived output: vce_100ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DRIVER-DIP16/B1b: measurement not found unambiguously in archived output: vf
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-DRIVER-DIP16/B3: measurement not found unambiguously in archived output: vmotor
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LDO-SOT235/B1: measurement not found unambiguously in archived output: vout_vin3.0
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LDO-SOT235/B2: measurement not found unambiguously in archived output: delta_mv
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LDO-SOT235/B3: measurement not found unambiguously in archived output: tj_c
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B1: measurement not found unambiguously in archived output: voh_4ma
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B1: measurement not found unambiguously in archived output: vol_4ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B2: measurement not found unambiguously in archived output: tpd_ns
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B3: measurement not found unambiguously in archived output: icc_ua
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B4: measurement not found unambiguously in archived output: vt_plus
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B4: measurement not found unambiguously in archived output: vt_minus
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B5: measurement not found unambiguously in archived output: i_clamp_ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-SEQ/B1: measurement not found unambiguously in archived output: qa..qh
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-LOGIC-SEQ/B2: measurement not found unambiguously in archived output: low_output_index
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPAMP/B1: measurement not found unambiguously in archived output: f_-3db
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPAMP/B2: measurement not found unambiguously in archived output: sr v/us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPAMP/B3: measurement not found unambiguously in archived output: vout follower
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPAMP/B4: measurement not found unambiguously in archived output: f_-3db
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPAMP/B5: measurement not found unambiguously in archived output: icc ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPTO-DIP6/B1: measurement not found unambiguously in archived output: vc_2ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-OPTO-DIP6/B2: measurement not found unambiguously in archived output: ic_ma_at_if5ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-PKGBIND/B1: measurement not found unambiguously in archived output: f0
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-PKGBIND/B2: measurement not found unambiguously in archived output: tj dip/soic/tssop
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-PKGBIND/B3: measurement not found unambiguously in archived output: v bounce
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-RS232-DIP16/B1: measurement not found unambiguously in archived output: v_out
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-RS232-DIP16/B2: measurement not found unambiguously in archived output: vtp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-RS232-DIP16/B3: measurement not found unambiguously in archived output: sr_v_per_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-TIMER555/B1: measurement not found unambiguously in archived output: f_hz
- AUD-BENCH-001: BEH-IC-TIMER555/B1: measurement not found unambiguously in archived output: f_ti_formula
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-TIMER555/B1b: measurement not found unambiguously in archived output: f_hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-TIMER555/B2: measurement not found unambiguously in archived output: width_ms
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-TIMER555/B3: measurement not found unambiguously in archived output: width_ms
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-IC-TIMER555/B4: measurement not found unambiguously in archived output: voh_100ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-ADDRESSABLE/B1: measurement not found unambiguously in archived output: t0h
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-ADDRESSABLE/B2: measurement not found unambiguously in archived output: v_end
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-INDICATOR/B1: measurement not found unambiguously in archived output: vred@20ma
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-INDICATOR/B2: measurement not found unambiguously in archived output: i_red
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-INDICATOR/B3: measurement not found unambiguously in archived output: iavg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-INDICATOR/B4: measurement not found unambiguously in archived output: ir at bv
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-INDICATOR/B5: measurement not found unambiguously in archived output: iv(1ma)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-INDICATOR/B6: measurement not found unambiguously in archived output: dvf/dt red
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-POWER/B1: measurement not found unambiguously in archived output: tj
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-POWER/B2: measurement not found unambiguously in archived output: i_hot/i_cold
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-LED-RGB/B7: measurement not found unambiguously in archived output: i_each
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-CMC/B1: measurement not found unambiguously in archived output: lcm
- AUD-BENCH-001: BEH-MAG-CMC/B1: measurement not found unambiguously in archived output: ldm
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-CMC/B2: measurement not found unambiguously in archived output: z_2p5mhz
- AUD-BENCH-001: BEH-MAG-CMC/B2: measurement not found unambiguously in archived output: z_10mhz
- AUD-BENCH-001: BEH-MAG-CMC/B2: measurement not found unambiguously in archived output: z_100mhz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-CMC/B3: measurement not found unambiguously in archived output: lcm_at_1a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-ETHMAG/B1: measurement not found unambiguously in archived output: il_1mhz_db
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-ETHMAG/B2: measurement not found unambiguously in archived output: i_per_v_50hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-ETHMAG/B3: measurement not found unambiguously in archived output: v_line_plateau
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B1: measurement not found unambiguously in archived output: l_at_isat_xal4020
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B1: measurement not found unambiguously in archived output: l_at_isat_srp7028a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B2: measurement not found unambiguously in archived output: i_at_8us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B3: measurement not found unambiguously in archived output: f_peak
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B3: measurement not found unambiguously in archived output: q_100mhz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B4: measurement not found unambiguously in archived output: dt_5p5a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-CT/B1: measurement not found unambiguously in archived output: vburden_pk
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-CT/B2: measurement not found unambiguously in archived output: fc
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-CT/B3: measurement not found unambiguously in archived output: v_open_pk
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-FLYBACK/B1: measurement not found unambiguously in archived output: vout
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-FLYBACK/B2: measurement not found unambiguously in archived output: vdrain_pk
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-FLYBACK/B3: measurement not found unambiguously in archived output: p_clamp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-FLYBACK/B3b: measurement not found unambiguously in archived output: p_clamp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-SIGNAL/B1: measurement not found unambiguously in archived output: gain_1khz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-SIGNAL/B2: measurement not found unambiguously in archived output: fl
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MAG-XFMR-SIGNAL/B3: measurement not found unambiguously in archived output: i_pk
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MEM-SPINOR/F1: measurement not found unambiguously in archived output: tcslow_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-MEM-SPINOR/F2: measurement not found unambiguously in archived output: peak_droop_mv
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P1: measurement not found unambiguously in archived output: tj
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P2: measurement not found unambiguously in archived output: theta_4vias
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P3: measurement not found unambiguously in archived output: f0_mhz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P4: measurement not found unambiguously in archived output: peak_droop_mv
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PWR-LOADSWITCH/L1: measurement not found unambiguously in archived output: vdrop_v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PWR-LOADSWITCH/L2: measurement not found unambiguously in archived output: turn_on_v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PWR-LOADSWITCH/L3: measurement not found unambiguously in archived output: isc_a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PWR-PKGTHERMAL/B1: measurement not found unambiguously in archived output: tj_inf
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-PWR-PKGTHERMAL/B2: measurement not found unambiguously in archived output: pmax_12_rows
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B1: measurement not found unambiguously in archived output: fsw_mhz
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B1: measurement not found unambiguously in archived output: dil_a
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B2: measurement not found unambiguously in archived output: eta_1a
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B2: measurement not found unambiguously in archived output: fsw_10ma_khz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B3: measurement not found unambiguously in archived output: deviation_mv
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B4: measurement not found unambiguously in archived output: fsw_mhz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B5: measurement not found unambiguously in archived output: vout_v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-REG-LINEAR/B1: measurement not found unambiguously in archived output: vout_3p8v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-REG-LINEAR/B2: measurement not found unambiguously in archived output: line_reg
- AUD-BENCH-001: BEH-REG-LINEAR/B2: measurement not found unambiguously in archived output: load_reg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-REG-LINEAR/B4: measurement not found unambiguously in archived output: tj
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-FIXED/B1: measurement not found unambiguously in archived output: v(out)
- AUD-BENCH-001: BEH-RES-FIXED/B1: measurement not found unambiguously in archived output: r(125c)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-FIXED/B2: measurement not found unambiguously in archived output: r
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-FIXED/B3: measurement not found unambiguously in archived output: zmag
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-FIXED/B4: measurement not found unambiguously in archived output: p_allowed
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-FIXED/B5: measurement not found unambiguously in archived output: r85
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-NETWORK/B1: measurement not found unambiguously in archived output: v(p2)
- AUD-BENCH-001: BEH-RES-NETWORK/B1: measurement not found unambiguously in archived output: i(pin4)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-NETWORK/B2: measurement not found unambiguously in archived output: i_total
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-POT/B1: measurement not found unambiguously in archived output: v(w)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-POT/B2: measurement not found unambiguously in archived output: v(w)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-POT/B3: measurement not found unambiguously in archived output: v(w)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-POT/B4: measurement not found unambiguously in archived output: v(w)@0.25ms
- AUD-BENCH-001: BEH-RES-POT/B4: measurement not found unambiguously in archived output: v(w)@0.75ms
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-SENSE/B1: measurement not found unambiguously in archived output: v_kelvin
- AUD-BENCH-001: BEH-RES-SENSE/B1: measurement not found unambiguously in archived output: v_2wire
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-SENSE/B2: measurement not found unambiguously in archived output: v
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: BEH-RES-SENSE/B3: measurement not found unambiguously in archived output: zmag
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-BJT/B1: measurement not found unambiguously in archived output: ic
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-BJT/B2: measurement not found unambiguously in archived output: gain
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-BJT/B6: measurement not found unambiguously in archived output: dvbe_dt
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-BJT/B8: measurement not found unambiguously in archived output: loop_gain_criterion
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-MOSFET/B1: measurement not found unambiguously in archived output: vds
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-MOSFET/B2: measurement not found unambiguously in archived output: rds_4p5v_l3
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-MOSFET/B3: measurement not found unambiguously in archived output: qgd
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: actual ngspice 42 version output missing
- AUD-BENCH-001: bench bypassed product code
- AUD-BENCH-001: BEH-TRN-MOSFET/B8: measurement not found unambiguously in archived output: eav
- docs/behavior/bench/_smoke.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/beh-con-sd/B2b.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/cap-edlc/B2b.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/ic-driver/B2_uln_flyback_input.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/ic-ldo/B2b_current_limit.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/ic-ldo/B3b_thermal_limit.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/mag_inductor/X1_flux_form_disagrees.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/osc-pierce/B4.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/reg_linear/B3_load_step.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/reg_linear/B5_esr_stability.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_bjt/B3_hfe_2n3904.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_bjt/B3b_hfe_2n2222a.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_bjt/B3c_hfe_corners_2n3904.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_bjt/B4_vcesat.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_bjt/B5_early_ro.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_bjt/B7_switching_times.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_mosfet/B4_transconductance.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_mosfet/B5_body_diode_vsd.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_mosfet/B6_body_diode_qrr.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_mosfet/B7_rdson_vs_temp.cir: authored netlist has no canonical benchmark contract; not run
- docs/behavior/bench/trn_mosfet/B9_vth_spread_2n7000.cir: authored netlist has no canonical benchmark contract; not run

## Decisions (including all electrical-data decisions)

# Behavior audit decisions

## D-001 — Preserve unresolved source claims

Keep the imported statuses, parameters, basis and confidence unchanged. The
baseline contains 18 complete, 144 partial and 18 research_required entries.
The source ledger records both failed and successful fetches; a named citation
without a resolved fetched URL remains a failure. A fetched file alone does not
establish semantic support. The alternative of promoting a record based on a
download or code change was rejected. Electrical-data effect: no change.

## D-002 — Require the current-run simulator gate

`ngspice -v` is unavailable in the shell. Unit-test doubles and the supplied
ngspice-42 research logs are not current-run bench evidence. All 205 canonical
bench references are sent through the existing product adapter and recorded as
not_run; none is marked passing. The 21 additional authored netlists without a
canonical analytical contract remain flagged. The alternative of importing
historical measurements as new results was rejected. Electrical-data effect:
simulation eligibility is not promoted.

## D-003 — Keep the audit failure visible during independent remediation

The audit software and canaries can work while the component corpus fails the
full checkpoint. Failed source and simulator checks block dependent stages.
Independent source inventory, downloads, coverage generation, and audit repairs
continue. This follows the narrower reading of the failed-checkpoint gate and
the user's independent-work policy. No stage acceptance is inferred from a
passing canary suite.

## D-004 — Protect the actual primary checkout

Hash the primary checkout's tracked and non-ignored untracked files, its index,
HEAD and status, plus main and remote refs. Hashing status alone would miss a
second edit to an already modified file. Existing local work is preserved as the
baseline and is never cleaned or rewritten. No push or merge is performed.

## D-005 — Limit the bench parser to unambiguous sourced measurements

Compare named numeric scalars against the original expected value and tolerance.
Numeric strings and percentage tolerances are parsed without changing the
value. Qualitative expressions, missing measurements and repeated scalar names
remain failures; no guessed alias or enlarged tolerance is introduced.
Electrical-data effect: no change to expectations or tolerances.

## D-006 — Preserve violations and failed-run status in the existing UI

Suppress stale transient curves when a simulation reports unavailable, failed,
timed_out or not_run. A supplied rating violation is displayed as a violation.
The tests exercise the actual existing UI renderer. This is the bounded honesty
repair required by the audit; it does not claim Stage 6's full behavior UI is
implemented or that any electrical rating was evaluated.

## D-007 — Update the approval regression to the newly authorized scope

The workflow regression's exact approved-scope expectation is updated from
Stage 1 to the user's explicit completion scope, with assertions on the new
human approval record. Electrical baselines, benchmark expectations, tolerances
and canary fixture values are unchanged.


## Every rule change

- {'id': 'RULE_CHANGE-001', 'old_sha256': '730f651999bc31c7e9db55deb1beac59d05da9aa2d9d9a89ec6f1f20eb53a1c7', 'new_sha256': 'f240b5f2beb9b8d56d2901fa5b663c5d877d0d6c68c84209b8e61301aafc21d3', 'classification': 'tighten', 'reason': 'Add the complete Stage 1 fast repository gate to every checkpoint, in addition to the existing focused and UI regressions. The first checkpoint ran focused regressions only; this corrects that omission without removing a check or changing any expected value, tolerance, canary or baseline.', 'reviewer': 'implementation-agent; listed for final human review'}

## Independent verifier results

NOT RUN: no research stage completed. No independent research acceptance is claimed.

## Needs human review

- OHM-012 — Cement power resistor: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-013 — Wirewound power resistor: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-038 — X2 safety capacitor: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-040 — Supercapacitor: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-044 — SMD wirewound inductor: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-052 — Small signal transformer: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-053 — Flyback transformer: rating-critical/safety-relevant research and current-run bench required; source status stays research_required.
- OHM-054 — Current transformer: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-055 — Ethernet magnetics transformer: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-069 — TVS diode: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-173 — XT30 PCB connector: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- OHM-174 — XT60 PCB connector: rating-critical/safety-relevant research and current-run bench required; source status stays partial.
- Source conflict: Master table assigns BEH-REG-LINEAR to OHM-133, but the canonical class applies_to list omits the entry.
- OHM-071, OHM-072: Keep automatic electrical binding blocked until a manufacturer drawing establishes PLUS and MINUS; AC1 and AC2 may interchange only afterward.
- 599 per-entry open-item references are preserved in GAP_INVENTORY.json and the full coverage table below. No rating-critical field is promoted by this run.

## Full coverage table

# Component behavior coverage

> Generated by `python -m tools.behavior_audit coverage`; do not edit rows by hand.

Entries: **180**. Audited simulable: **0**. complete: **18**. partial: **144**. research_required: **18**.

| Entry | Behavior class | Layer | Fidelity | Status before | Status after | Simulable | Why | Current-run bench | Open items |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OHM-001 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-002 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-003 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-004 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-005 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-006 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-007 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-008 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-009 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-010 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-011 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-012 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-013 | BEH-RES-FIXED | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-RES-FIXED /parameters/cp: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/ls: basis=ASSUMPTION, confidence=L; BEH-RES-FIXED /parameters/rth: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-014 | BEH-RES-SENSE | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-RES-SENSE /parameters/rc: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-015 | BEH-RES-SENSE | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-RES-SENSE /parameters/rc: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-016 | BEH-RES-NETWORK | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-017 | BEH-RES-NETWORK | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-018 | BEH-RES-POT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-RES-POT /parameters/pos: basis=ASSUMPTION, confidence=M; BEH-RES-POT /parameters/rw: basis=ASSUMPTION, confidence=L; BEH-RES-POT /parameters/taper: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-019 | BEH-RES-POT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-RES-POT /parameters/pos: basis=ASSUMPTION, confidence=M; BEH-RES-POT /parameters/rw: basis=ASSUMPTION, confidence=L; BEH-RES-POT /parameters/taper: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-020 | BEH-RES-POT | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/4 PASS | BEH-RES-POT /parameters/pos: basis=ASSUMPTION, confidence=M; BEH-RES-POT /parameters/rw: basis=ASSUMPTION, confidence=L; BEH-RES-POT /parameters/taper: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-021 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-022 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-023 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-024 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-025 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-026 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-027 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-028 | BEH-CAP-CERAMIC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-CERAMIC /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-CERAMIC /parameters/v0_bias_knee: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-029 | BEH-CAP-ALEL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-ALEL /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/r_leak: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-030 | BEH-CAP-ALEL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-ALEL /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/r_leak: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-031 | BEH-CAP-ALEL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CAP-ALEL /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/r_leak: basis=ASSUMPTION, confidence=L; BEH-CAP-ALEL /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-032 | BEH-CAP-ALPOLY | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CAP-ALPOLY /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-ALPOLY /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-ALPOLY /parameters/rated_voltage: basis=MFR_DATASHEET, confidence=L; BEH-CAP-ALPOLY /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-033 | BEH-CAP-TANT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CAP-TANT /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-034 | BEH-CAP-TANT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CAP-TANT /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-035 | BEH-CAP-TANT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CAP-TANT /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-036 | BEH-CAP-TANT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CAP-TANT /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/esr: basis=ASSUMPTION, confidence=L; BEH-CAP-TANT /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-037 | BEH-CAP-FILM | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CAP-FILM /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-FILM /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-038 | BEH-CAP-FILM | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CAP-FILM /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-FILM /parameters/value: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-039 | BEH-CAP-MICA | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CAP-MICA /parameters/esl: basis=ASSUMPTION, confidence=L; BEH-CAP-MICA /parameters/q_at_1mhz: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-040 | BEH-CAP-EDLC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-041 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-042 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-043 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-044 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-045 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | complete | complete | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L |
| OHM-046 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-047 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-048 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-049 | BEH-MAG-INDUCTOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-MAG-INDUCTOR /parameters/lr: basis=ASSUMPTION, confidence=L; BEH-MAG-INDUCTOR /parameters/rp: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-050 | BEH-MAG-CMC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-MAG-CMC /parameters/c0: basis=DERIVED, confidence=L; BEH-MAG-CMC /parameters/isat_cm: basis=ASSUMPTION, confidence=L; BEH-MAG-CMC /parameters/rpar: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-051 | BEH-MAG-CMC | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-MAG-CMC /parameters/c0: basis=DERIVED, confidence=L; BEH-MAG-CMC /parameters/isat_cm: basis=ASSUMPTION, confidence=L; BEH-MAG-CMC /parameters/rpar: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-052 | BEH-MAG-XFMR-SIGNAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-MAG-XFMR-SIGNAL /parameters/ciw: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-SIGNAL /parameters/isat_m: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-SIGNAL /parameters/llk: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-SIGNAL /parameters/lp: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-SIGNAL /parameters/rwinding: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-053 | BEH-MAG-XFMR-FLYBACK | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/4 PASS | BEH-MAG-XFMR-FLYBACK /parameters/ciw: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-FLYBACK /parameters/isat_pri: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-FLYBACK /parameters/llk: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-FLYBACK /parameters/lp: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-FLYBACK /parameters/rpri: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-FLYBACK /parameters/rsec: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-054 | BEH-MAG-XFMR-CT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-MAG-XFMR-CT /parameters/isat_m_pri: basis=ASSUMPTION, confidence=L; BEH-MAG-XFMR-CT /parameters/lsec: basis=MFR_DATASHEET, confidence=L; BEH-MAG-XFMR-CT /parameters/rsec: basis=MFR_DATASHEET, confidence=L; BEH-MAG-XFMR-CT /parameters/turns_ratio: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-055 | BEH-MAG-ETHMAG | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-MAG-ETHMAG /parameters/ciw: basis=ASSUMPTION, confidence=L; BEH-MAG-ETHMAG /parameters/leakage: basis=DERIVED, confidence=L; BEH-MAG-ETHMAG /parameters/ocl: basis=MFR_DATASHEET, confidence=L; BEH-MAG-ETHMAG /parameters/rwinding: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-056 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-057 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-058 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-059 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-060 | BEH-DIO-PN | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-061 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-062 | BEH-DIO-PN | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-063 | BEH-DIO-PN | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-064 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-065 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-066 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-067 | BEH-DIO-SCHOTTKY | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-DIO-SCHOTTKY /parameters/BV: basis=ASSUMPTION, confidence=L; BEH-DIO-SCHOTTKY /parameters/CJO: basis=ASSUMPTION, confidence=L; BEH-DIO-SCHOTTKY /parameters/IS: basis=DERIVED, confidence=L; BEH-DIO-SCHOTTKY /parameters/N: basis=ASSUMPTION, confidence=L; BEH-DIO-SCHOTTKY /parameters/RS: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-068 | BEH-DIO-ZENER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-069 | BEH-DIO-TVS | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-DIO-TVS /parameters/VBR_nom: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-070 | BEH-DIO-PN | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/7 PASS | BEH-DIO-PN /parameters/M: basis=ASSUMPTION, confidence=L; BEH-DIO-PN /parameters/VJ: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-071 | BEH-DIO-BRIDGE | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/3 PASS | BEH-DIO-BRIDGE /parameters/CJO: basis=DERIVED, confidence=L; BEH-DIO-BRIDGE /parameters/IS: basis=DERIVED, confidence=L; BEH-DIO-BRIDGE /parameters/N: basis=ASSUMPTION, confidence=L; BEH-DIO-BRIDGE /parameters/RS: basis=ASSUMPTION, confidence=L; BEH-DIO-BRIDGE /parameters/TT: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Bridge terminal functions unresolved; automatic electrical binding blocked |
| OHM-072 | BEH-DIO-BRIDGE | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-DIO-BRIDGE /parameters/CJO: basis=DERIVED, confidence=L; BEH-DIO-BRIDGE /parameters/IS: basis=DERIVED, confidence=L; BEH-DIO-BRIDGE /parameters/N: basis=ASSUMPTION, confidence=L; BEH-DIO-BRIDGE /parameters/RS: basis=ASSUMPTION, confidence=L; BEH-DIO-BRIDGE /parameters/TT: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Bridge terminal functions unresolved; automatic electrical binding blocked |
| OHM-073 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-074 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-075 | BEH-LED-INDICATOR | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-076 | BEH-LED-INDICATOR | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-077 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-078 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-079 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-080 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-081 | BEH-LED-INDICATOR | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/6 PASS | BEH-LED-INDICATOR /bench/5/expected/0: basis=ASSUMPTION, confidence=not specified; BEH-LED-INDICATOR /parameters/IS: basis=DERIVED, confidence=L; BEH-LED-INDICATOR /parameters/N: basis=ASSUMPTION, confidence=L; BEH-LED-INDICATOR /parameters/RS: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-082 | BEH-LED-RGB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/1 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-083 | BEH-LED-RGB | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/1 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-084 | BEH-LED-ADDRESSABLE | L3 | behavioural_approximation | partial | partial | no | L3 protocol or firmware behavior requires a higher-layer model. | 0/2 PASS | BEH-LED-ADDRESSABLE /parameters/ich: basis=ASSUMPTION, confidence=L; BEH-LED-ADDRESSABLE /parameters/iq: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Protocol/firmware outside ngspice; electrical-interface simulation is a separate bounded claim |
| OHM-085 | BEH-LED-POWER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-LED-POWER /parameters/eta: basis=ASSUMPTION, confidence=L; BEH-LED-POWER /parameters/rth_sa: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-086 | BEH-LED-POWER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-LED-POWER /parameters/eta: basis=ASSUMPTION, confidence=L; BEH-LED-POWER /parameters/rth_sa: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-087 | BEH-DISP-LEDARRAY | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-088 | BEH-DISP-LEDARRAY | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-089 | BEH-DISP-LEDARRAY | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-090 | BEH-DISP-LEDARRAY | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-091 | BEH-DISP-LCD1602 | L3 | behavioural_approximation | partial | partial | no | L3 protocol or firmware behavior requires a higher-layer model. | 0/2 PASS | BEH-DISP-LCD1602 /parameters/backlight_if: basis=ASSUMPTION, confidence=L; BEH-DISP-LCD1602 /parameters/backlight_vf: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Protocol/firmware outside ngspice; electrical-interface simulation is a separate bounded claim |
| OHM-092 | BEH-DISP-OLED-I2C | L3 | behavioural_approximation | partial | partial | no | L3 protocol or firmware behavior requires a higher-layer model. | 0/2 PASS | BEH-DISP-OLED-I2C /parameters/iidle: basis=ASSUMPTION, confidence=L; BEH-DISP-OLED-I2C /parameters/ion: basis=ASSUMPTION, confidence=L; BEH-DISP-OLED-I2C /parameters/rpu: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Protocol/firmware outside ngspice; electrical-interface simulation is a separate bounded claim |
| OHM-093 | BEH-TRN-BJT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-BJT /parameters/VAF: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-094 | BEH-TRN-BJT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-BJT /parameters/VAF: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-095 | BEH-TRN-BJT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-BJT /parameters/VAF: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-096 | BEH-TRN-BJT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-BJT /parameters/VAF: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-097 | BEH-TRN-BJT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-BJT /parameters/VAF: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-098 | BEH-TRN-MOSFET | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-MOSFET /parameters/cgs_ciss: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-099 | BEH-TRN-MOSFET | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/4 PASS | BEH-TRN-MOSFET /parameters/cgs_ciss: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-100 | BEH-TRN-MOSFET | L1 | behavioural_approximation | research_required | research_required | no | Required electrical or terminal evidence remains unresolved. | 0/4 PASS | BEH-TRN-MOSFET /parameters/cgs_ciss: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-101 | BEH-TRN-MOSFET | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-MOSFET /parameters/cgs_ciss: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-102 | BEH-TRN-MOSFET | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-TRN-MOSFET /parameters/cgs_ciss: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-103 | BEH-IC-PKGBIND | L1 | behavioural_approximation | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-104 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-105 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-106 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-107 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-108 | BEH-IC-PKGBIND | L1 | behavioural_approximation | research_required | research_required | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-109 | BEH-IC-PKGBIND | L1 | behavioural_approximation | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-110 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-111 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-112 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-113 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-114 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-115 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-116 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-117 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-118 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-119 | BEH-IC-PKGBIND | L1 | behavioural_approximation | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-120 | BEH-IC-PKGBIND | L1 | behavioural_approximation | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-121 | BEH-IC-PKGBIND | L1 | behavioural_approximation | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/3 PASS | BEH-IC-PKGBIND /parameters/lead_C: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_L: basis=MFR_DATASHEET, confidence=L; BEH-IC-PKGBIND /parameters/lead_R: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-122 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-123 | BEH-PKG-IC-BINDING | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-124 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-125 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-126 | BEH-PKG-IC-BINDING | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-127 | BEH-PKG-IC-BINDING, BEH-REG-BUCK-DCS | L1 | ideal_components | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/9 PASS | BEH-REG-BUCK-DCS /parameters/RINJ: basis=ASSUMPTION, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-128 | BEH-PKG-IC-BINDING | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-129 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-130 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-131 | BEH-PKG-IC-BINDING | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-132 | BEH-PKG-IC-BINDING, BEH-PWR-LOADSWITCH | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/7 PASS | BEH-PWR-LOADSWITCH /parameters/ILIM: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-133 | BEH-PKG-IC-BINDING, BEH-REG-LINEAR | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/7 PASS | BEH-REG-LINEAR /parameters/ilim: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation; Master table includes BEH-REG-LINEAR but canonical applies_to omits OHM-133 |
| OHM-134 | BEH-PKG-IC-BINDING, BEH-REG-BUCK-DCS | L1 | ideal_components | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/9 PASS | BEH-REG-BUCK-DCS /parameters/RINJ: basis=ASSUMPTION, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-135 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-136 | BEH-PKG-IC-BINDING | L1 | ideal_components | research_required | research_required | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-137 | BEH-PKG-IC-BINDING, BEH-IC-DIGITAL-IF | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/8 PASS | BEH-IC-DIGITAL-IF /parameters/C_pin: basis=MFR_DATASHEET, confidence=L; BEH-IC-DIGITAL-IF /parameters/Ceff: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_high: basis=DERIVED, confidence=L; BEH-IC-DIGITAL-IF /parameters/RON_low: basis=DERIVED, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-138 | BEH-PKG-IC-BINDING | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-139 | BEH-PKG-IC-BINDING | L1 | ideal_components | partial | partial | no | A package has no electrical function until a sourced reference part is bound. | 0/4 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-140 | BEH-PKG-IC-BINDING, BEH-PWR-LOADSWITCH | L1 | ideal_components | complete | complete | no | A package has no electrical function until a sourced reference part is bound. | 0/7 PASS | BEH-PWR-LOADSWITCH /parameters/ILIM: basis=ASSUMPTION, confidence=L; Package needs a primary-source reference-part binding before electrical simulation |
| OHM-141 | BEH-FREQ-XTAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/8 PASS | BEH-FREQ-XTAL /parameters/C1: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-142 | BEH-FREQ-XTAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/8 PASS | BEH-FREQ-XTAL /parameters/C1: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-143 | BEH-FREQ-XTAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/8 PASS | BEH-FREQ-XTAL /parameters/C1: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-144 | BEH-FREQ-XTAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/8 PASS | BEH-FREQ-XTAL /parameters/C1: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-145 | BEH-FREQ-XTAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/8 PASS | BEH-FREQ-XTAL /parameters/C1: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-146 | BEH-FREQ-XO | L2 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-FREQ-XO /parameters/rout: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-147 | BEH-FREQ-XO | L2 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-FREQ-XO /parameters/rout: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-148 | BEH-FREQ-CERRES | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/1 PASS | BEH-FREQ-CERRES /parameters/C0: basis=ASSUMPTION, confidence=L; BEH-FREQ-CERRES /parameters/C1: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-149 | BEH-FREQ-SAW | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-150 | BEH-CON-HEADER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CON-HEADER /parameters/Lpin: basis=DERIVED, confidence=L; BEH-CON-HEADER /parameters/Rc: basis=ASSUMPTION, confidence=L; BEH-CON-HEADER /parameters/Rth_derived: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-151 | BEH-CON-HEADER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CON-HEADER /parameters/Lpin: basis=DERIVED, confidence=L; BEH-CON-HEADER /parameters/Rc: basis=ASSUMPTION, confidence=L; BEH-CON-HEADER /parameters/Rth_derived: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-152 | BEH-CON-HEADER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CON-HEADER /parameters/Lpin: basis=DERIVED, confidence=L; BEH-CON-HEADER /parameters/Rc: basis=ASSUMPTION, confidence=L; BEH-CON-HEADER /parameters/Rth_derived: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-153 | BEH-CON-HEADER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CON-HEADER /parameters/Lpin: basis=DERIVED, confidence=L; BEH-CON-HEADER /parameters/Rc: basis=ASSUMPTION, confidence=L; BEH-CON-HEADER /parameters/Rth_derived: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-154 | BEH-CON-HEADER | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/4 PASS | BEH-CON-HEADER /parameters/Lpin: basis=DERIVED, confidence=L; BEH-CON-HEADER /parameters/Rc: basis=ASSUMPTION, confidence=L; BEH-CON-HEADER /parameters/Rth_derived: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-155 | BEH-CON-WTB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-WTB /parameters/Rmate: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-156 | BEH-CON-WTB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-WTB /parameters/Rmate: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-157 | BEH-CON-WTB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-WTB /parameters/Rmate: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-158 | BEH-CON-WTB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-WTB /parameters/Rmate: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-159 | BEH-CON-TERMINAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-TERMINAL /parameters/Rclamp: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-160 | BEH-CON-TERMINAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-TERMINAL /parameters/Rclamp: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-161 | BEH-CON-TERMINAL | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-TERMINAL /parameters/Rclamp: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-162 | BEH-CON-USB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-CON-USB /parameters/Rc_other: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-163 | BEH-CON-USB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-CON-USB /parameters/Rc_other: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-164 | BEH-CON-USB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-CON-USB /parameters/Rc_other: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-165 | BEH-CON-USB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-CON-USB /parameters/Rc_other: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-166 | BEH-CON-USB | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/5 PASS | BEH-CON-USB /parameters/Rc_other: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-167 | BEH-CON-HDMI | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-168 | BEH-CON-HDMI | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-169 | BEH-CON-MODJACK | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-170 | BEH-CON-MODJACK | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-171 | BEH-CON-AUDIO | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-AUDIO /parameters/Rsw: basis=MFR_DATASHEET, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-172 | BEH-CON-DCJACK | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-DCJACK /parameters/r_switch_on: basis=ASSUMPTION, confidence=L; BEH-CON-DCJACK /parameters/switch_partner: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-173 | BEH-CON-XT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-XT /parameters/alpha: basis=ASSUMPTION, confidence=L; BEH-CON-XT /parameters/c_th: basis=ASSUMPTION, confidence=L; BEH-CON-XT /parameters/i_peak: basis=MFR_DATASHEET, confidence=L; BEH-CON-XT /parameters/r_th: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-174 | BEH-CON-XT | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-XT /parameters/alpha: basis=ASSUMPTION, confidence=L; BEH-CON-XT /parameters/c_th: basis=ASSUMPTION, confidence=L; BEH-CON-XT /parameters/i_peak: basis=MFR_DATASHEET, confidence=L; BEH-CON-XT /parameters/r_th: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-175 | BEH-CON-RF | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CON-RF /parameters/c_pad: basis=ASSUMPTION, confidence=L; BEH-CON-RF /parameters/l_pin: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-176 | BEH-CON-RF | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CON-RF /parameters/c_pad: basis=ASSUMPTION, confidence=L; BEH-CON-RF /parameters/l_pin: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-177 | BEH-CON-RF | L1 | behavioural_approximation | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/3 PASS | BEH-CON-RF /parameters/c_pad: basis=ASSUMPTION, confidence=L; BEH-CON-RF /parameters/l_pin: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-178 | BEH-CON-FFC | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-179 | BEH-CON-SDSOCKET | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-SDSOCKET /parameters/r_switch_on: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |
| OHM-180 | BEH-CON-SDSOCKET | L1 | ideal_components | partial | partial | no | Product behavior model and current-run bench not yet audited. | 0/2 PASS | BEH-CON-SDSOCKET /parameters/r_switch_on: basis=ASSUMPTION, confidence=L; Retain source status until parameters, ratings, failure behavior and current-run bench are supported |

