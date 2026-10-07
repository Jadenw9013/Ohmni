# Checkpoint 025: stage4

- Time: `2026-10-05T22:15:49Z`
- Commit: `c8680baa6548e24f8870a562d7dcddc09674a46b`
- Rule hash: `f240b5f2beb9b8d56d2901fa5b663c5d877d0d6c68c84209b8e61301aafc21d3`
- Overall: **FAIL**
- Entries touched: OHM-104, OHM-105, OHM-106, OHM-110, OHM-111, OHM-112, OHM-114, OHM-115, OHM-119, OHM-120, OHM-124, OHM-125, OHM-126, OHM-138, OHM-143, OHM-144, OHM-145, OHM-147, OHM-176, OHM-180

| Rule | Result | Summary |
| --- | --- | --- |
| AUD-RULE-001 | PASS | rule change is explicitly recorded as non-loosening |
| AUD-CANARY-001 | PASS | 7/7 canaries rejected as expected |
| AUD-SOURCE-001 | FAIL | 267/339 cited URLs have successful hashed fetches |
| AUD-UPGRADE-001 | PASS | 0 status upgrades checked |
| AUD-VENDOR-001 | PASS | all vendor_model labels have attached compatible models |
| AUD-SPEC-001 | PASS | generated projection and approved LED permutation are current |
| AUD-BENCH-001 | FAIL | 74/205 canonical bench references passed; 21 additional authored netlists lack a canonical contract |
| AUD-PROTECT-001 | PASS | main, production checkout, remote refs and protected paths match baseline |
| AUD-COVERAGE-001 | PASS | 180 records and 180 coverage rows |
| AUD-VERIFY-001 | FAIL | 1 completed research-stage verifier reports checked |
| AUD-RESUME-001 | PASS | run state is complete and parseable |
| AUD-REGRESSION-001 | PASS | 4 locked regression commands ran |
| AUD-HONESTY-001 | PASS | all recorded UI/code claims preserve non-run and violation status |

## Details

### AUD-SOURCE-001
- AUD-SOURCE-001: missing successful archived fetch: https://NXP.com/docs/en/application-note/AN12442.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://atom.ubbcluj.ro/alpar/datasheets/optoelectronic_components/LED/Untinted%20Non-Diffused%20LED%20(B)%20-%20Vishay.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://cdn.soselectronic.com/productdata/d3/71/bc19a080/attiny25gak-15mz.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://cdn1.components.ru/81/35081.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://community.infineon.com/t5/Knowledge-Base-Articles/Termination-Resistors-Required-for-the-USB-Type-C-Connector/ta-p/253544
- AUD-SOURCE-001: missing successful archived fetch: https://content.kemet.com/datasheets/F3054.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://cz.farnell.com/en-CZ/wurth-elektronik/65100516121/mini-usb-2-0-type-b-receptacle/dp/1642036
- AUD-SOURCE-001: missing successful archived fetch: https://datasheet.ciiva.com/14545/70045422-14545053.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://datasheet.ciiva.com/19454/234819-19454258.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://datasheets.ibselectronics.com/1050170002-Molex-datasheet-16324174.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://datasheets.ibselectronics.com/sj1-353xng.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://docs.ampnuts.ru/nexperia.com.datasheet/application-note/AN50006.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://engineering.purdue.edu/ece477/Archive/2008/Fall/F08-Grp02/datasheets/e60900232.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://hkcn.rs-online.com/web/p/pluggable-terminal-blocks/1896105
- AUD-SOURCE-001: missing successful archived fetch: https://jp.farnell.com/en-JP/harwin/m20-9990245/header-tht-2-54mm-1row-2way/dp/1022245
- AUD-SOURCE-001: missing successful archived fetch: https://onlinedocs.microchip.com/oxy/GUID-2ACDA668-0A87-46A1-B7FC-9DC74A5461AD-en-US-2/GUID-9D6E52D1-BC20-4009-8F14-35F680E0A5EC.html
- AUD-SOURCE-001: missing successful archived fetch: https://ph.rs-online.com/web/p/pcb-terminal-blocks/8020510
- AUD-SOURCE-001: missing successful archived fetch: https://static.chipdip.ru/lib/150/DOC036150746.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://static6.arrow.com/aropdfconversion/9b57075dcb9d6fd09f527e256d515abd213125c/c2012x5r1v106m085ac.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://supplychain.molex.com/content/dam/molex/molex-dot-com/en_us/pdf/datasheets/987652-0671.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://uk.rs-online.com/p/usb-connectors/8006867
- AUD-SOURCE-001: missing successful archived fetch: https://uk.rs-online.com/web/p/pulse-transformers/1634318
- AUD-SOURCE-001: missing successful archived fetch: https://www.advanced-monolithic.com/pdf/ds1117.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.alldatasheet.com/html-pdf/659067/FTDI/FT231XQ-R/3946/38/FT231XQ-R.html
- AUD-SOURCE-001: missing successful archived fetch: https://www.alldatasheet.net/html-pdf/303567/STMICROELECTRONICS/STM32F103CBU6XXX/160632/82/STM32F103CBU6XXX.html
- AUD-SOURCE-001: missing successful archived fetch: https://www.alldatasheet.net/html-pdf/346652/NXP/PCF8564ACX9SLASHBSLASH1/2502/33/PCF8564ACX9SLASHBSLASH1.html
- AUD-SOURCE-001: missing successful archived fetch: https://www.alldatasheet.net/html-pdf/556763/STMICROELECTRONICS/STM32F103CBU6/181902/93/STM32F103CBU6.html
- AUD-SOURCE-001: missing successful archived fetch: https://www.amphenolrf.com/en-us/assets/file/4065861601/
- AUD-SOURCE-001: missing successful archived fetch: https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.bpx.ie/dbdocument/104035/1757019.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.coilcraft.com/en-us/files/datasheet/XAL40xx
- AUD-SOURCE-001: missing successful archived fetch: https://www.digikey.at/en/products/detail/abracon-llc/AFS869S3-T/675442
- AUD-SOURCE-001: missing successful archived fetch: https://www.digikey.ca/en/products/detail/TY-145P/237-1121-ND/242643
- AUD-SOURCE-001: missing successful archived fetch: https://www.digikey.it/en/products/detail/amgis-llc/AS-103/2260664
- AUD-SOURCE-001: missing successful archived fetch: https://www.e-sonic.com/productfiles/mf-pul/h315.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-hb-supercapacitor-data-sheet.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.element14.cn/en-CN/phoenix-contact/1757242/header-right-angle-5-08mm-2way/dp/3705171
- AUD-SOURCE-001: missing successful archived fetch: https://www.kemet.com/content/dam/kemet/lightning/obsolete/technical-archive/2004-CARTS-Europe-Derating-Differences.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.molex.com/en-us/products/part-detail/22232021
- AUD-SOURCE-001: missing successful archived fetch: https://www.molex.com/en-us/products/part-detail/732511150?display=pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.mouser.com/datasheet/2/3/AFS869S3-46075.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.mouser.com/datasheet/2/427/VISHS73798_1-2566147.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.mouser.com/datasheet/2/949/w25q128jv_revf_03272018_plus-1489608.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.mouser.lt/datasheet/3/97/1/FC_135_en.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.mouser.lt/pdfDocs/LFPAKMOSFETthermaldesignguide-2.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.mouser.lt/pdfdocs/KEM_T2061_T543UPDATED-2.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.niccomp.com/wp-content/uploads/files/aluminum/RC-CorrectionFactors-122010r5.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.nxp.com/docs/en/application-note/AN10778.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.nxp.com/docs/en/data-sheet/LPC1769_68_67_66_65_64_63.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.nxp.com/docs/en/data-sheet/NX5P3290.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.nxp.com/docs/en/data-sheet/P89LPC933_934_935_936.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.nxp.com/docs/en/data-sheet/PCF8564A.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/download/data-sheet/pdf/2n7000-d.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/pdf/datasheet/2n3903-d.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/pdf/datasheet/bc546-d.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/pdf/datasheet/pn2222a-d.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/pub/Collateral/AN875-D.PDF
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/pub/Collateral/AND9008-D.PDF
- AUD-SOURCE-001: missing successful archived fetch: https://www.onsemi.com/pub/collateral/and90187-d.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com.cn/resource/zh/application_note/an5225-usb-typec-power-delivery-using-stm32-mcus-and-mpus-stmicroelectronics.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/application_note/an1703-guidelines-for-using-sts-mosfet-smd-packages-stmicroelectronics.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/application_note/an2867-guidelines-for-oscillator-design-on-stm8afals-and-stm32-mcusmpus-stmicroelectronics.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/datasheet/bd135.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/datasheet/l78.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/datasheet/l78l.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/datasheet/stm32f103c8.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/en/datasheet/stm32f407vg.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.st.com/resource/ja/application_note/an4879-introduction-to-usb-hardware-and-pcb-guidelines-using-stm32-mcus-stmicroelectronics.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.svmicrowave.com/images/uploaded/Solderless_PCB_Edge_Launch_Connectors_Application_Note.pdf
- AUD-SOURCE-001: missing successful archived fetch: https://www.tdk.com/en/tech-mag/electronics_primer/6
- AUD-SOURCE-001: missing successful archived fetch: https://www.usb.org/sites/default/files/USB
- AUD-SOURCE-001: missing successful archived fetch: https://www.wima.de/wp-content/uploads/media/WIMA_Main_Catalogue_2025.pdf
- BEH-CAP-ALEL/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-CAP-ALPOLY/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-CAP-CERAMIC/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-CAP-EDLC/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-CAP-FILM/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-CAP-MICA/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-CAP-TANT/S26: local or unresolved reference requires an explicit artifact binding: | S26 | OHMNI | benches in /home/claude/behavior/bench/cap-* (ngspice 42 runs) | local | 2026-10-02 | all measured values |
- BEH-IC-CHARGER-SOT235/S25: local or unresolved reference requires an explicit artifact binding: | S25 | OHMNI repository | `tests/corpus/annotations/MCP73831_SOT23-5.json` and `recordings/MCP73831_SOT23-5_accepted.json` | local | transcription 2026-09-14 | class 9: SOT-23-5 pin map |
- BEH-IC-CHARGER-SOT235/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-COMPARATOR/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-DIGITAL-IO/S24: local or unresolved reference requires an explicit artifact binding: | S24 | OHMNI repository | catalog record `src/ohmni/catalog/data/parts/25LC256-I_SN.json` | local | recorded 2026-09-09 | class 7: pin electrical types, abs max, firmware rule |
- BEH-IC-DRIVER-DIP16/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-LDO-SOT235/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-LDO-SOT235/S31: local or unresolved reference requires an explicit artifact binding: | S31 | Group R6 output | `/home/claude/behavior/parts/R6.md` (BEH-PWR-PKGTHERMAL, BEH-REG-LINEAR) | local | | cross-reference for thermal network and linear regulators |
- BEH-IC-LOGIC-HC/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-LOGIC-SEQ/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-OPAMP/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-OPTO-DIP6/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-RS232-DIP16/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- BEH-IC-TIMER555/S29: local or unresolved reference requires an explicit artifact binding: | S29 | OHMNI | `/home/claude/PCB_COMPONENT_3D_LIBRARY_SPEC.md`, entries OHM-103 to OHM-121 | local | as in the repo | pin 1, geometry, terminals |
- MCP1700T-3302E-TT/SOT-23: external citation has no fetched URL: DS20001826F
- MCP1700T-3302E-TT/SOT-89: external citation has no fetched URL: DS20001826F
- MCP1700T-3302E-TT/TO-92: external citation has no fetched URL: DS20001826F

### AUD-BENCH-001
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CAP-CERAMIC/B1: measurement not found unambiguously in archived output: Ceff at 0/1/2/4 V (uF)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CAP-EDLC/B2: measurement not found unambiguously in archived output: v1/v2 (V)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CAP-FILM/B2: measurement not found unambiguously in archived output: f0 (MHz)
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-AUDIO/B1: measurement not found unambiguously in archived output: v_before
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-AUDIO/B2: measurement not found unambiguously in archived output: gain
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-DCJACK/B1: measurement not found unambiguously in archived output: v_drop
- AUD-BENCH-001: BEH-CON-DCJACK/B1: measurement not found unambiguously in archived output: dT
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-DCJACK/B2: measurement not found unambiguously in archived output: vload_unplugged
- AUD-BENCH-001: BEH-CON-DCJACK/B2: measurement not found unambiguously in archived output: vload_plugged
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-FFC/B1: measurement not found unambiguously in archived output: v_drop
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-FFC/B2: measurement not found unambiguously in archived output: i_contact1
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-HDMI/B1: measurement not found unambiguously in archived output: vdiff
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-HDMI/B2: measurement not found unambiguously in archived output: vload_first
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-HEADER/B1: measurement not found unambiguously in archived output: V_load
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-HEADER/B3: measurement not found unambiguously in archived output: dT
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-MODJACK/B2: measurement not found unambiguously in archived output: vmin
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-MODJACK/B3: measurement not found unambiguously in archived output: gain
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-RF/B1: measurement not found unambiguously in archived output: vswr
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-RF/B2: measurement not found unambiguously in archived output: gamma_C
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-RF/B3: measurement not found unambiguously in archived output: gamma_step
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-SDSOCKET/B1: measurement not found unambiguously in archived output: v_cd_open
- AUD-BENCH-001: BEH-CON-SDSOCKET/B1: measurement not found unambiguously in archived output: v_cd_closed
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-SDSOCKET/B2: measurement not found unambiguously in archived output: vcc_loaded
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-TERMINAL/B1: measurement not found unambiguously in archived output: flag
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-TERMINAL/B2: measurement not found unambiguously in archived output: dT
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-USB/B1: measurement not found unambiguously in archived output: v_load_5A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-USB/B2: measurement not found unambiguously in archived output: vcc_56k
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-USB/B3: measurement not found unambiguously in archived output: f3dB
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-USB/B4: measurement not found unambiguously in archived output: v_dp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-USB/B5: measurement not found unambiguously in archived output: vbus_on_load
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-WTB/B1: measurement not found unambiguously in archived output: i_straight
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-WTB/B2: measurement not found unambiguously in archived output: V_load
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-CON-XT/B1: measurement not found unambiguously in archived output: P_xt60
- AUD-BENCH-001: BEH-CON-XT/B1: measurement not found unambiguously in archived output: dT
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-DIO-BRIDGE/B2: measurement not found unambiguously in archived output: ripple
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-DIO-BRIDGE/B3: measurement not found unambiguously in archived output: reverse DC current
- AUD-BENCH-001: BEH-DIO-BRIDGE/B3: measurement not found unambiguously in archived output: blocked current
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B3: measurement not found unambiguously in archived output: Tj at Ta 60C
- AUD-BENCH-001: BEH-DIO-SCHOTTKY/B3: measurement not found unambiguously in archived output: runaway at Ta 95C
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-DIO-TVS/B3: measurement not found unambiguously in archived output: V at +/-24.6 A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-CERRES/B1: measurement not found unambiguously in archived output: f_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-SAW/B1: measurement not found unambiguously in archived output: il_fc_dB
- AUD-BENCH-001: BEH-FREQ-SAW/B1: measurement not found unambiguously in archived output: bw3_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-SAW/B2: measurement not found unambiguously in archived output: il_100ohm_dB
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XO/B1: measurement not found unambiguously in archived output: f_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XO/B2: measurement not found unambiguously in archived output: vout_max_V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/B1: measurement not found unambiguously in archived output: zmin_ohm
- AUD-BENCH-001: BEH-FREQ-XTAL/B1: measurement not found unambiguously in archived output: fa_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/B2: measurement not found unambiguously in archived output: fL_18pF_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/B3: measurement not found unambiguously in archived output: fL_32k_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/P1: measurement not found unambiguously in archived output: DL_W
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/P2: measurement not found unambiguously in archived output: f_loop_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/P3: measurement not found unambiguously in archived output: f_tran_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/P5: measurement not found unambiguously in archived output: envelope_ratio_at_gm_crit
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-FREQ-XTAL/P6: measurement not found unambiguously in archived output: gm_crit_S
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-CHARGER-SOT235/B1: measurement not found unambiguously in archived output: Ibat_A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-CHARGER-SOT235/B2: measurement not found unambiguously in archived output: I_4.19V_mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-CHARGER-SOT235/B3: measurement not found unambiguously in archived output: Ibat_A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-COMPARATOR/B1: measurement not found unambiguously in archived output: trip voltage
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-COMPARATOR/B1b: measurement not found unambiguously in archived output: VOL
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-COMPARATOR/B2: measurement not found unambiguously in archived output: t_5mV_us
- AUD-BENCH-001: BEH-IC-COMPARATOR/B2: measurement not found unambiguously in archived output: t_TTL_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D1: measurement not found unambiguously in archived output: VOL, VOH at 5 mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D2: measurement not found unambiguously in archived output: I_inj mA, Vpin V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D3: measurement not found unambiguously in archived output: t_release_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DIGITAL-IF/D4: measurement not found unambiguously in archived output: Idd mA at 1 and 18 MHz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DIGITAL-IO/B1: measurement not found unambiguously in archived output: VOL_20mA
- AUD-BENCH-001: BEH-IC-DIGITAL-IO/B1: measurement not found unambiguously in archived output: VOH_20mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DIGITAL-IO/B2: measurement not found unambiguously in archived output: pullup_pad_V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DRIVER-DIP16/B1: measurement not found unambiguously in archived output: vce_100mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DRIVER-DIP16/B1b: measurement not found unambiguously in archived output: vf
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-DRIVER-DIP16/B3: measurement not found unambiguously in archived output: vmotor
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LDO-SOT235/B1: measurement not found unambiguously in archived output: vout_vin3.0
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LDO-SOT235/B2: measurement not found unambiguously in archived output: delta_mV
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LDO-SOT235/B3: measurement not found unambiguously in archived output: Tj_C
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B1: measurement not found unambiguously in archived output: VOH_4mA
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B1: measurement not found unambiguously in archived output: VOL_4mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B2: measurement not found unambiguously in archived output: tpd_ns
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B3: measurement not found unambiguously in archived output: icc_uA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B4: measurement not found unambiguously in archived output: VT_plus
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B4: measurement not found unambiguously in archived output: VT_minus
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-HC/B5: measurement not found unambiguously in archived output: I_clamp_mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-SEQ/B1: measurement not found unambiguously in archived output: QA..QH
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-LOGIC-SEQ/B2: measurement not found unambiguously in archived output: low_output_index
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPAMP/B1: measurement not found unambiguously in archived output: f_-3dB
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPAMP/B2: measurement not found unambiguously in archived output: SR V/us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPAMP/B3: measurement not found unambiguously in archived output: Vout follower
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPAMP/B4: measurement not found unambiguously in archived output: f_-3dB
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPAMP/B5: measurement not found unambiguously in archived output: Icc mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPTO-DIP6/B1: measurement not found unambiguously in archived output: Vc_2mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-OPTO-DIP6/B2: measurement not found unambiguously in archived output: Ic_mA_at_IF5mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-PKGBIND/B1: measurement not found unambiguously in archived output: f0
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-PKGBIND/B2: measurement not found unambiguously in archived output: Tj DIP/SOIC/TSSOP
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-PKGBIND/B3: measurement not found unambiguously in archived output: V bounce
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-RS232-DIP16/B1: measurement not found unambiguously in archived output: v_out
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-RS232-DIP16/B2: measurement not found unambiguously in archived output: vtp
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-RS232-DIP16/B3: measurement not found unambiguously in archived output: sr_V_per_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-TIMER555/B1: measurement not found unambiguously in archived output: f_Hz
- AUD-BENCH-001: BEH-IC-TIMER555/B1: measurement not found unambiguously in archived output: f_TI_formula
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-TIMER555/B1b: measurement not found unambiguously in archived output: f_Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-TIMER555/B2: measurement not found unambiguously in archived output: width_ms
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-TIMER555/B3: measurement not found unambiguously in archived output: width_ms
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-IC-TIMER555/B4: measurement not found unambiguously in archived output: VOH_100mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-LED-INDICATOR/B1: measurement not found unambiguously in archived output: Vred@20mA
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-LED-INDICATOR/B4: measurement not found unambiguously in archived output: IR at BV
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-LED-POWER/B2: measurement not found unambiguously in archived output: I_hot/I_cold
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-LED-RGB/B7: measurement not found unambiguously in archived output: I_each
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-CMC/B1: measurement not found unambiguously in archived output: Lcm
- AUD-BENCH-001: BEH-MAG-CMC/B1: measurement not found unambiguously in archived output: Ldm
- AUD-BENCH-001: measured=7499.836, expected=7500.0, tolerance=0.15
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=3707.45, expected=4000.0, tolerance=0.15
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=399.5682, expected=400.0, tolerance=0.15
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-CMC/B3: measurement not found unambiguously in archived output: Lcm_at_1A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-ETHMAG/B2: measurement not found unambiguously in archived output: I_per_V_50Hz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-ETHMAG/B3: measurement not found unambiguously in archived output: V_line_plateau
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B1: measurement not found unambiguously in archived output: L_at_Isat_XAL4020
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B1: measurement not found unambiguously in archived output: L_at_Isat_SRP7028A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B3: measurement not found unambiguously in archived output: f_peak
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B3: measurement not found unambiguously in archived output: Q_100MHz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MAG-INDUCTOR/B4: measurement not found unambiguously in archived output: dT_5p5A
- AUD-BENCH-001: measured=1640.907, expected=1639.3, tolerance=0.03
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=237.6563, expected=235.6, tolerance=0.05
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=21.27992, expected=21.466, tolerance=0.03
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=183.0105, expected=184.4, tolerance=0.05
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=0.1571843, expected=0.3528, tolerance=0.15
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=50.70204, expected=51.2, tolerance=0.03
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MEM-SPINOR/F1: measurement not found unambiguously in archived output: tCSlow_us
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-MEM-SPINOR/F2: measurement not found unambiguously in archived output: peak_droop_mV
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P1: measurement not found unambiguously in archived output: Tj
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P2: measurement not found unambiguously in archived output: theta_4vias
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P3: measurement not found unambiguously in archived output: f0_MHz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PKG-IC-BINDING/P4: measurement not found unambiguously in archived output: peak_droop_mV
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PWR-LOADSWITCH/L1: measurement not found unambiguously in archived output: vdrop_V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PWR-LOADSWITCH/L2: measurement not found unambiguously in archived output: turn_on_V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PWR-LOADSWITCH/L3: measurement not found unambiguously in archived output: isc_A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PWR-PKGTHERMAL/B1: measurement not found unambiguously in archived output: Tj_inf
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-PWR-PKGTHERMAL/B2: measurement not found unambiguously in archived output: pmax_12_rows
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B1: measurement not found unambiguously in archived output: fsw_MHz
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B1: measurement not found unambiguously in archived output: dIL_A
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B2: measurement not found unambiguously in archived output: eta_1A
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B2: measurement not found unambiguously in archived output: fsw_10mA_kHz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B3: measurement not found unambiguously in archived output: deviation_mV
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B4: measurement not found unambiguously in archived output: fsw_MHz
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-BUCK-DCS/B5: measurement not found unambiguously in archived output: vout_V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-LINEAR/B1: measurement not found unambiguously in archived output: Vout_3p8V
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-LINEAR/B2: measurement not found unambiguously in archived output: line_reg
- AUD-BENCH-001: BEH-REG-LINEAR/B2: measurement not found unambiguously in archived output: load_reg
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-REG-LINEAR/B4: measurement not found unambiguously in archived output: Tj
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: measured=-0.0005, expected=0.0005, tolerance=5e-07
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-TRN-BJT/B8: measurement not found unambiguously in archived output: loop_gain_criterion
- AUD-BENCH-001: missing/non-finite numeric comparison
- AUD-BENCH-001: bench did not run successfully
- AUD-BENCH-001: BEH-TRN-MOSFET/B8: measurement not found unambiguously in archived output: Eav
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
- OHM-056: stale or invalid runtime run_status
- OHM-056: raw observation does not meet its locked or sourced contract
- OHM-059: stale or invalid runtime run_status
- OHM-059: raw observation does not meet its locked or sourced contract
- OHM-061: stale or invalid runtime run_status
- OHM-061: raw observation does not meet its locked or sourced contract
- OHM-062: stale or invalid runtime run_status
- OHM-062: raw observation does not meet its locked or sourced contract
- OHM-063: stale or invalid runtime run_status
- OHM-063: raw observation does not meet its locked or sourced contract

### AUD-VERIFY-001
- stage2: OHM-083: primary source missing
- stage2: OHM-096: verifier mismatch
- stage2: OHM-097: verifier mismatch
- stage2: OHM-049 reviewed gapfill_sha256 is missing or stale
- stage2: OHM-049 reviewed generated_record_sha256 is missing or stale
- stage2: OHM-096 reviewed gapfill_sha256 is missing or stale
- stage2: OHM-096 reviewed generated_record_sha256 is missing or stale
- stage2: OHM-097 reviewed gapfill_sha256 is missing or stale
- stage2: OHM-097 reviewed generated_record_sha256 is missing or stale

### AUD-REGRESSION-001
- python scripts/generate_behavior_records.py --check: exit 0: behavior records current: 250 files
- python -m pytest tests/test_behavior_registry.py tests/test_ai_workflow.py tests/test_behavior_audit.py tests/test_simulation.py -q: exit 0: ........................................................................ [ 44%]
........................................................................ [ 88%]
...................                                                      [100%]
============================== warnings summary ===============================
..\..\.venv\Lib\site-packages\_pytest\cacheprovider.py:469
  C:\Dev\hackathon\.venv\Lib\site-packages\_pytest\cacheprovider.py:469: PytestCacheWarning: could not create cache path C:\Dev\hackathon\.worktrees\behavior-stage0\.pytest_cache\v\cache\nodeids: [WinError 5] Access is denied: 'C:\\Dev\\hackathon\\.worktrees\\behavior-stage0\\.pytest_cache\\v\\cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
- node --test apps/web/tests/scope-view.test.mjs: exit 0: ample
  ---
  duration_ms: 2.4002
  type: 'test'
  ...
# Subtest: signal names are escaped, never injected
ok 11 - signal names are escaped, never injected
  ---
  duration_ms: 0.1895
  type: 'test'
  ...
# Subtest: the report section explains a missing curve instead of drawing one
ok 12 - the report section explains a missing curve instead of drawing one
  ---
  duration_ms: 0.1036
  type: 'test'
  ...
# Subtest: the limitation travels with the curve
ok 13 - the limitation travels with the curve
  ---
  duration_ms: 0.1395
  type: 'test'
  ...
# Subtest: a thinned result says how many steps it came from
ok 14 - a thinned result says how many steps it came from
  ---
  duration_ms: 0.1367
  type: 'test'
  ...
# Subtest: engineering notation keeps a millisecond axis readable
ok 15 - engineering notation keeps a millisecond axis readable
  ---
  duration_ms: 0.0455
  type: 'test'
  ...
1..15
# tests 15
# suites 0
# pass 15
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 63.2214
- python scripts/verify.py fast: exit 0: ..................................................... [ 62%]
........................................................................ [ 65%]
.......................................................................s [ 69%]
ssssssss................................................................ [ 72%]
........................................................................ [ 76%]
........................................................................ [ 80%]
........................................................................ [ 83%]
........................................................................ [ 87%]
........................................................................ [ 91%]
........................................................................ [ 94%]
........................................................................ [ 98%]
..............................                                           [100%]
1892 passed, 82 skipped, 49 deselected in 207.42s (0:03:27)

## Drift note

Audited 20 touched entries against the locked brief. The checkpoint does not yet satisfy every required assertion; all deviations are listed as failed checks below.
