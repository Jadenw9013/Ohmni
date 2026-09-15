# Visual reference coverage — VIS-REF-001

The runtime reference inventory and artist-authored scene are implemented in [visual-inventory.js](../../apps/web/visual-inventory.js), with reusable geometry in [visual-assets.js](../../apps/web/visual-assets.js). The integrated explorer opens through **Explore sample board** or the local `#sample-board` route. This is an implementation coverage record; final browser screenshots, measured performance and the human visual comparison remain separate acceptance evidence.

The five supplied reference/annotation images were inspected. The privately supplied image remains outside served web assets. Source image SHA-256: `30cc966fcc367d91563782b3b411cd941daf181d174447e17dbbe0f18c37e207` (1500 × 853 pixels). Inventory-file SHA-256: `0f1b3518a71d8300d119b5c38b8c95f225f0a198857ed4794a67b8c4410bcf31`. The source package's image centers locate observations; they are never model dimensions, CAD coordinates, pin maps or circuit evidence. The imported source descriptions, family inferences and confidence remain distinct from authored model choices.

Every sample instance is **ILLUSTRATIVE_ONLY**, with null source component, null source footprint, no role evidence and circuit role **UNKNOWN**. Stable IDs are visual annotation IDs, not recovered reference designators. Chosen lead/contact counts, markings, bands and dimensions are explicitly illustrative. Generic family lessons cannot establish the depicted object's device identity, value, protocol, function or connectivity.

Persistent label: **Reference-inspired educational model · not an electrically verified design**.

## Count reconciliation

| Disposition | Entries | Runtime handling |
|---|---:|---|
| Independent illustrative bodies | 124 | 10 prominent IC forms, 20 candidate small black bodies, 6 header strips, 5 connector/metal forms, 15 silver cans, 4 navy cans, 1 coil, 1 orange radial, 8 posts and 54 independent P bodies. These are the 124 selectable owners. |
| Passive subdetails | 9 | P31, P32, P38, P48 and P59–P63 resolve to named parent bodies. No extra body or BOM entry. |
| Unresolved microdetail patches | 8 | X01–X08 are faint surface/attachment approximations without invented component counts. |
| Corner holes | 4 | Three clearly observed and one partly observed; sample openings have artist-selected positions and sizes. |
| Shared board/rendering features | 10 | B01–B10 map to slab, paths, rings/openings, solder, printed detail, package subparts and lighting. |
| Viewport-only aids | 3 | V01 deliberately omitted; V02/V03 represented by Ohmni-native view controls. |
| **Total inventory entries** | **158** | **Visual inventory, not an electrical BOM or a measured source-board component count.** |

The 54 independent P bodies comprise 26 banded resistor-like forms, 13 unbanded blue forms, 12 beige forms and 3 red coated forms. Seven beige bodies use a chip variant; P13/P16/P26/P43/P45 use rounded tan axial variants with bent leads. Two banded bodies use beige coating. Four navy and fifteen silver cans have varied dimensions. The exact population is a sample choice: retaining all 20 S candidates yields 124 bodies, including the partially occluded S05 with identity UNKNOWN.

P59–P63 have explicit row-body associations in the source. P31/P32/P38/P48 are assigned nearby visual owners only to represent ambiguous terminal/band patches without extra bodies; those four associations are approximate. Clicking any lead, contact or solder submesh resolves to its body owner. Searching a P subdetail ID reaches its parent through `subdetailIds`. X patches are not selectable component bodies.

## Authored normalized composition

The stage's **140 × 100 × 1.6 mm** dimensions are artist-selected drawing units, not recovered board dimensions. Coordinates are authored as `u` left→right and `v` rear→front, then displayed with `x=(u−0.5)×140`, `y=(0.5−v)×100`. This changes units within a chosen scene; it does not transform source pixels into PCB coordinates. Camera orientation is independent.

| Region | Normalized envelope [u min, v min, u max, v max] | Composition |
|---|---|---|
| rear | 0.2, 0.03, 0.88, 0.36 | Navy cans, metal blocks, a coil-like form and orange coating. |
| left | 0.03, 0.1, 0.38, 0.77 | Several leaded packages, silver cans and a blue passive bank. |
| center | 0.34, 0.34, 0.74, 0.78 | A dominant square package and surrounding leaded components. |
| right | 0.69, 0.16, 0.97, 0.94 | Black strips, a metal shell and grouped blue and beige bodies. |
| front | 0.04, 0.7, 0.86, 0.97 | Long contact strips, silver cans and a row of banded bodies. |

Every body has an explicit transform below. Regional envelopes intentionally overlap; they are navigation/art-direction groups, not functional modules or placement constraints. Ninety-three fanout/corridor paths exist only under `illustrativeGuideGeometry`. Twenty-four small ring/opening features exist only under `illustrativeSurfaceFeatures`. Neither carries pins, net names, signal direction, connectivity or engineering status. Four corner openings and the small illustrative openings are real mesh holes, not painted discs.

## Per-entry implemented disposition

Family names identify generic rendering assets, not verified package types. The normalized positions and orientations below are artist-authored. Image descriptions in the last column are source observations; they are not model parameters.

| ID | Disposition | Region / owner | Authored (u, v); rotation | Runtime model / feature binding | Source observation |
|---|---|---|---|---|---|
| IC01 | Implemented illustrative body | center | 0.5750, 0.5250; 0° | ohmni-procedural/qfp@reference-packages-v1 | Large central square black package with fine silver leads around its perimeter and circular orientation marks |
| IC02 | Implemented illustrative body | rear | 0.3500, 0.3300; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Horizontal rectangular multi-lead package below the short rear-left header |
| IC03 | Implemented illustrative body | rear | 0.5800, 0.3250; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Horizontal multi-lead package immediately in front of the tall blue capacitors |
| IC04 | Implemented illustrative body | right | 0.7800, 0.4050; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Rectangular multi-lead package inside the upper-right headers |
| IC05 | Implemented illustrative body | center | 0.4050, 0.5250; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Upright rectangular multi-lead package directly left of the large central package |
| IC06 | Implemented illustrative body | center | 0.5550, 0.7200; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Horizontal multi-lead package below the central package |
| IC07 | Implemented illustrative body | right | 0.7200, 0.7550; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Horizontal multi-lead package above the front-right long header |
| IC08 | Implemented illustrative body | left | 0.2050, 0.3250; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Upright multi-lead package in the upper-left interior |
| IC09 | Implemented illustrative body | left | 0.2500, 0.5050; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Upright multi-lead package halfway down the left interior |
| IC10 | Implemented illustrative body | front | 0.3050, 0.6900; 90° | ohmni-procedural/qfp@reference-packages-v1 | Upright multi-lead package in the lower-left interior |
| S01 | Implemented illustrative body | left | 0.1450, 0.1150; 0° | ohmni-procedural/few_terminal@reference-packages-v1 | Small black package behind the upper-left main IC, left of its neighboring small black package |
| S02 | Implemented illustrative body | left | 0.2000, 0.1150; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Small black package beside IC-small 01 near the white rear-left connector |
| S03 | Implemented illustrative body | left | 0.1050, 0.2670; 0° | ohmni-procedural/few_terminal@reference-packages-v1 | Small horizontal black package between left header and upper-left main IC |
| S04 | Implemented illustrative body | left | 0.1050, 0.5350; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Small black horizontal body below the left header, just above the left silver-can trio |
| S05 | Implemented illustrative body | left | 0.0700, 0.6650; 90° | ohmni-procedural/leadless_block@reference-packages-v1 | Partly obscured small black body behind/left of the silver-can cluster |
| S06 | Implemented illustrative body | left | 0.1550, 0.5850; 0° | ohmni-procedural/leadless_block@reference-packages-v1 | Small square black body between the left silver cans |
| S07 | Implemented illustrative body | front | 0.0850, 0.8550; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead package near the front-left mounting hole, farther from the hole |
| S08 | Implemented illustrative body | front | 0.0850, 0.9150; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead package near the front-left mounting hole, nearer the hole |
| S09 | Implemented illustrative body | front | 0.1900, 0.8700; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead package immediately right of the large white front-left connector |
| S10 | Implemented illustrative body | front | 0.2550, 0.8350; 90° | ohmni-procedural/leadless_block@reference-packages-v1 | Larger lead-poor black rectangle above the front-left silver can |
| S11 | Implemented illustrative body | front | 0.4250, 0.8720; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead package between the front silver-can pair and long front header |
| S12 | Implemented illustrative body | front | 0.6800, 0.8500; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead package above the right end of the long front header |
| S13 | Implemented illustrative body | rear | 0.7850, 0.2550; 0° | ohmni-procedural/few_terminal@reference-packages-v1 | Small low black body below the coil, inward from rear-right header |
| S14 | Implemented illustrative body | rear | 0.8500, 0.2500; 90° | ohmni-procedural/few_terminal@reference-packages-v1 | Small black body between coil-side passives and rear-right header |
| S15 | Implemented illustrative body | rear | 0.8300, 0.2950; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Adjacent small elongated black body along the rear-right header support cluster |
| S16 | Implemented illustrative body | right | 0.8300, 0.5250; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Horizontal black package below the long right header |
| S17 | Implemented illustrative body | right | 0.7350, 0.5650; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead black package inward from the metal connector, upper one |
| S18 | Implemented illustrative body | right | 0.7750, 0.6100; 90° | ohmni-procedural/small_outline@reference-packages-v1 | Small multi-lead black package inward from the metal connector, lower one |
| S19 | Implemented illustrative body | right | 0.9450, 0.8750; 90° | ohmni-procedural/leadless_block@reference-packages-v1 | Flat rectangular black package between front-right header and right corner |
| S20 | Implemented illustrative body | front | 0.3500, 0.8890; 0° | ohmni-procedural/small_outline@reference-packages-v1 | Long narrow marked black package directly behind the left end of the long front header |
| H01 | Implemented illustrative body | left | 0.0450, 0.3700; 90° | ohmni-procedural/header@reference-packages-v1 | Long black shrouded pin strip along the left edge |
| H02 | Implemented illustrative body | rear | 0.3350, 0.0650; 0° | ohmni-procedural/header@reference-packages-v1 | Short black shrouded pin strip on the rear-left edge |
| H03 | Implemented illustrative body | right | 0.9150, 0.2050; 90° | ohmni-procedural/header@reference-packages-v1 | Medium black pin strip on the rear-right edge, closer to rear corner |
| H04 | Implemented illustrative body | right | 0.9150, 0.5200; 90° | ohmni-procedural/header@reference-packages-v1 | Long black pin strip farther down the right edge |
| H05 | Implemented illustrative body | front | 0.4700, 0.9615; 0° | ohmni-procedural/header@reference-packages-v1 | Longest foreground pin strip across the lower edge |
| H06 | Implemented illustrative body | right | 0.8050, 0.9250; 0° | ohmni-procedural/header@reference-packages-v1 | Separate long pin strip across the lower-right edge |
| J01 | Implemented illustrative body | left | 0.0900, 0.0950; 0° | ohmni-procedural/white_connector@reference-packages-v1 | Small white connector body at the rear-left edge |
| J02 | Implemented illustrative body | front | 0.0750, 0.7550; 90° | ohmni-procedural/white_connector@reference-packages-v1 | Large white/light-gray rectangular connector at the lower-left edge |
| J03 | Implemented illustrative body | right | 0.8550, 0.7550; 0° | ohmni-procedural/shielded_connector@reference-packages-v1 | Large silver rectangular shell with two dark circular apertures on top and a dark front opening |
| J04 | Implemented illustrative body | rear | 0.4650, 0.0700; 0° | ohmni-procedural/rear_metal_block@reference-packages-v1 | Tall silver rectangular body at rear edge, left of matching tall silver body |
| J05 | Implemented illustrative body | rear | 0.5650, 0.0700; 0° | ohmni-procedural/rear_metal_block@reference-packages-v1 | Second tall silver rectangular body at rear edge |
| C01 | Implemented illustrative body | left | 0.1050, 0.1850; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Upper-left large silver can beside rear-left white connector |
| C02 | Implemented illustrative body | left | 0.2000, 0.2050; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Smaller silver can just right of the upper-left large can |
| C03 | Implemented illustrative body | rear | 0.2400, 0.1150; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Rear silver can of a close pair beside the short rear-left header |
| C04 | Implemented illustrative body | rear | 0.2850, 0.1800; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Front silver can of that close pair |
| C05 | Implemented illustrative body | left | 0.1750, 0.4250; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Silver can beside upper-left main IC and left header |
| C06 | Implemented illustrative body | left | 0.0750, 0.5900; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Leftmost can of the mid-left lower trio |
| C07 | Implemented illustrative body | left | 0.1500, 0.6500; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Lower/front can of the mid-left trio |
| C08 | Implemented illustrative body | left | 0.2250, 0.6250; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Right can of the mid-left trio |
| C09 | Implemented illustrative body | front | 0.3500, 0.8200; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Left/front can of the pair beside IC10 |
| C10 | Implemented illustrative body | front | 0.4300, 0.8050; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Right/rear can of the pair beside IC10 |
| C11 | Implemented illustrative body | front | 0.5200, 0.8180; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Left/front can under IC06 |
| C12 | Implemented illustrative body | front | 0.6100, 0.8180; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Right/rear can under IC06 |
| C13 | Implemented illustrative body | right | 0.9300, 0.7150; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Small silver can behind the metal connector |
| C14 | Implemented illustrative body | right | 0.9500, 0.7900; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Larger silver can to the right of the metal connector |
| C15 | Implemented illustrative body | front | 0.2500, 0.9550; 0° | ohmni-procedural/aluminum_can@reference-packages-v1 | Large silver can near the front-left mounting hole |
| E01 | Implemented illustrative body | rear | 0.4650, 0.2150; 0° | ohmni-procedural/electrolytic_can@reference-packages-v1 | Nearest/front tall navy can beside J04 |
| E02 | Implemented illustrative body | rear | 0.5700, 0.2100; 0° | ohmni-procedural/electrolytic_can@reference-packages-v1 | Second tall navy can beside J05 |
| E03 | Implemented illustrative body | rear | 0.6600, 0.0750; 0° | ohmni-procedural/electrolytic_can@reference-packages-v1 | Third tall navy can toward the rear edge |
| E04 | Implemented illustrative body | rear | 0.7450, 0.0750; 0° | ohmni-procedural/electrolytic_can@reference-packages-v1 | Fourth tall navy can, cropped by the top edge |
| L01 | Implemented illustrative body | rear | 0.8350, 0.0750; 0° | ohmni-procedural/wound_inductor@reference-packages-v1 | Single reddish-brown ribbed cylinder at the far/rear corner |
| O01 | Implemented illustrative body | rear | 0.7350, 0.2350; 0° | ohmni-procedural/coated_radial@reference-packages-v1 | Orange upright cylindrical/rounded body in front of rear blue capacitors |
| T01 | Implemented illustrative body | rear | 0.6500, 0.1850; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Slender gold post between rear capacitor group |
| T02 | Implemented illustrative body | rear | 0.6550, 0.2650; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Lower gold post in front of the same group |
| T03 | Implemented illustrative body | center | 0.7200, 0.3450; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Gold post above the upper-right main IC |
| T04 | Implemented illustrative body | left | 0.2450, 0.4150; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Gold post beside upper-left main IC |
| T05 | Implemented illustrative body | left | 0.3200, 0.5900; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Gold post beside mid-left main IC |
| T06 | Implemented illustrative body | front | 0.1850, 0.8300; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Gold post next to front-left white connector |
| T07 | Implemented illustrative body | front | 0.6500, 0.8100; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Gold post between front-center can cluster and small IC |
| T08 | Implemented illustrative body | right | 0.9200, 0.8430; 0° | ohmni-procedural/gold_post@reference-packages-v1 | Gold post next to right metal connector and silver can |
| P01 | Implemented illustrative body | rear | 0.2950, 0.2400; 90° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (432, 197) |
| P02 | Implemented illustrative body | rear | 0.3250, 0.2400; 90° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (456, 191) |
| P03 | Implemented illustrative body | rear | 0.3550, 0.2400; 90° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (480, 184) |
| P04 | Implemented illustrative body | rear | 0.3850, 0.2400; 90° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (503, 177) |
| P05 | Implemented illustrative body | rear | 0.4150, 0.2400; 90° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (526, 171) |
| P06 | Implemented illustrative body | left | 0.1450, 0.2450; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (307, 239) |
| P07 | Implemented illustrative body | left | 0.2350, 0.2200; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (348, 225) |
| P08 | Implemented illustrative body | left | 0.1050, 0.3250; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (263, 309) |
| P09 | Implemented illustrative body | left | 0.1120, 0.3700; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (280, 328) |
| P10 | Implemented illustrative body | left | 0.1170, 0.4150; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (293, 346) |
| P11 | Implemented illustrative body | left | 0.1220, 0.4600; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (300, 362) |
| P12 | Implemented illustrative body | left | 0.1600, 0.4900; 90° | ohmni-procedural/coated_red@reference-packages-v1 | red small passive body near (320, 352) |
| P13 | Implemented illustrative body | center | 0.3500, 0.4250; 90° | ohmni-procedural/ceramic_chip@reference-packages-v1 (axial variant) | tan small passive body near (572, 269) |
| P14 | Implemented illustrative body | center | 0.3900, 0.4150; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (593, 255) |
| P15 | Implemented illustrative body | center | 0.4300, 0.4050; 90° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (616, 241) |
| P16 | Implemented illustrative body | rear | 0.4480, 0.3950; 90° | ohmni-procedural/ceramic_chip@reference-packages-v1 (axial variant) | tan small passive body near (659, 226) |
| P17 | Implemented illustrative body | rear | 0.4850, 0.3970; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (703, 226) |
| P18 | Implemented illustrative body | rear | 0.5400, 0.3970; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (722, 215) |
| P19 | Implemented illustrative body | rear | 0.6050, 0.3970; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (766, 205) |
| P20 | Implemented illustrative body | rear | 0.8000, 0.1650; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (856, 68) |
| P21 | Implemented illustrative body | rear | 0.8350, 0.1900; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (877, 80) |
| P22 | Implemented illustrative body | rear | 0.7700, 0.3050; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (904, 144) |
| P23 | Implemented illustrative body | rear | 0.8480, 0.3450; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (923, 153) |
| P24 | Implemented illustrative body | center | 0.6850, 0.4250; 15° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (854, 229) |
| P25 | Implemented illustrative body | center | 0.7000, 0.4700; 15° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (878, 246) |
| P26 | Implemented illustrative body | center | 0.7200, 0.5100; 15° | ohmni-procedural/ceramic_chip@reference-packages-v1 (axial variant) | tan small passive body near (896, 264) |
| P27 | Implemented illustrative body | right | 0.8000, 0.5950; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (1026, 315) |
| P28 | Implemented illustrative body | right | 0.8270, 0.5950; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (1043, 308) |
| P29 | Implemented illustrative body | right | 0.8540, 0.5950; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (1058, 301) |
| P30 | Implemented illustrative body | right | 0.8810, 0.5950; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (1075, 295) |
| P31 | Implemented subdetail | right | — | P30: terminal / band / solder geometry; association approximate | tan small passive body near (1066, 330); body/end-pad separation is ambiguous in this patch |
| P32 | Implemented subdetail | right | — | P27: terminal / band / solder geometry; association approximate | tan small passive body near (1016, 329); body/end-pad separation is ambiguous in this patch |
| P33 | Implemented illustrative body | right | 0.7200, 0.6300; 0° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (918, 317) |
| P34 | Implemented illustrative body | right | 0.7200, 0.6650; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (931, 328) |
| P35 | Implemented illustrative body | right | 0.7600, 0.6650; 0° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (941, 338) |
| P36 | Implemented illustrative body | right | 0.7950, 0.6700; 0° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (949, 348) |
| P37 | Implemented illustrative body | right | 0.9650, 0.7000; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (1218, 326) |
| P38 | Implemented subdetail | right | — | P37: terminal / band / solder geometry; association approximate | banded blue small passive body near (1233, 318); body/end-pad separation is ambiguous in this patch |
| P39 | Implemented illustrative body | right | 0.9630, 0.6350; 0° | ohmni-procedural/coated_red@reference-packages-v1 | red small passive body near (1262, 305) |
| P40 | Implemented illustrative body | right | 0.9670, 0.8750; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (1293, 415) |
| P41 | Implemented illustrative body | center | 0.6800, 0.6450; 90° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (897, 361) |
| P42 | Implemented illustrative body | center | 0.6350, 0.6650; 0° | ohmni-procedural/ceramic_chip@reference-packages-v1 | tan small passive body near (856, 379) |
| P43 | Implemented illustrative body | center | 0.5950, 0.6500; 0° | ohmni-procedural/ceramic_chip@reference-packages-v1 (axial variant) | tan small passive body near (768, 374) |
| P44 | Implemented illustrative body | left | 0.3200, 0.5200; 90° | ohmni-procedural/coated_red@reference-packages-v1 | red small passive body near (529, 351) |
| P45 | Implemented illustrative body | center | 0.4250, 0.6500; 0° | ohmni-procedural/ceramic_chip@reference-packages-v1 (axial variant) | tan small passive body near (642, 398) |
| P46 | Implemented illustrative body | center | 0.4750, 0.6500; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (669, 382) |
| P47 | Implemented illustrative body | center | 0.5350, 0.6500; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (696, 378) |
| P48 | Implemented subdetail | center | — | P47: terminal / band / solder geometry; association approximate | Tan end/band area adjacent to P47; may belong to the same axial body |
| P49 | Implemented illustrative body | front | 0.1850, 0.7300; 0° | ohmni-procedural/coated_axial@reference-packages-v1 | blue small passive body near (417, 522) |
| P50 | Implemented illustrative body | front | 0.1850, 0.7700; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (438, 543) |
| P51 | Implemented illustrative body | front | 0.1850, 0.8070; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (449, 560) |
| P52 | Implemented illustrative body | front | 0.2450, 0.8800; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded tan small passive body near (503, 658) |
| P53 | Implemented illustrative body | front | 0.2350, 0.9040; 0° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded tan small passive body near (512, 682) |
| P54 | Implemented illustrative body | front | 0.4800, 0.8890; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (738, 581) |
| P55 | Implemented illustrative body | front | 0.5200, 0.8890; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (763, 570) |
| P56 | Implemented illustrative body | front | 0.5600, 0.8890; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (789, 559) |
| P57 | Implemented illustrative body | front | 0.6000, 0.8890; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (815, 548) |
| P58 | Implemented illustrative body | front | 0.6400, 0.8890; 90° | ohmni-procedural/axial_resistor@reference-packages-v1 | banded blue small passive body near (840, 537) |
| P59 | Implemented subdetail | front | — | P54: terminal / band / solder geometry; source-described association | Tan/light terminal or band detail at the front end of P54; not a separately established component |
| P60 | Implemented subdetail | front | — | P55: terminal / band / solder geometry; source-described association | Tan/light terminal or band detail at the front end of P55; not a separately established component |
| P61 | Implemented subdetail | front | — | P56: terminal / band / solder geometry; source-described association | Tan/light terminal or band detail at the front end of P56; not a separately established component |
| P62 | Implemented subdetail | front | — | P57: terminal / band / solder geometry; source-described association | Tan/light terminal or band detail at the front end of P57; not a separately established component |
| P63 | Implemented subdetail | front | — | P58: terminal / band / solder geometry; source-described association | Tan/light terminal or band detail at the front end of P58; not a separately established component |
| X01 | Implemented approximate patch; identity UNKNOWN | rear | 0.3500, 0.2720 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Sub-pixel/occluded parts and shiny terminations in the row beneath the short rear-left header |
| X02 | Implemented approximate patch; identity UNKNOWN | left | 0.1750, 0.2520 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Tiny pads, leads and possible chip passives between rear-left silver cans and small black packages |
| X03 | Implemented approximate patch; identity UNKNOWN | rear | 0.8250, 0.2200 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Tiny green/black/tan objects under coil and behind rear-right support ICs |
| X04 | Implemented approximate patch; identity UNKNOWN | center | 0.5400, 0.3670 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Overlapping small passives above central IC fanout |
| X05 | Implemented approximate patch; identity UNKNOWN | right | 0.8500, 0.6360 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Interleaved tiny tan parts and metallic pads in right-hand resistor bank |
| X06 | Implemented approximate patch; identity UNKNOWN | front | 0.5600, 0.9350 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Interleaved tiny bodies, solder fillets and printed marks beside foreground resistor bank |
| X07 | Implemented approximate patch; identity UNKNOWN | front | 0.2600, 0.9100 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Occluded small passive/lead regions behind the large front silver can |
| X08 | Implemented approximate patch; identity UNKNOWN | center | 0.5250, 0.6710 | ohmni-procedural/unresolved_patch@reference-packages-v1; not a counted body | Small plated holes and terminations between central lower passive trio and main IC |
| M01 | Implemented artistic board feature | corner | 0.045, 0.045 | createSlab geometric opening + gold-colored annulus | Rear-left gold-rimmed mounting hole |
| M02 | Implemented artistic board feature | corner | 0.045, 0.97 | createSlab geometric opening + gold-colored annulus | Front-left gold-rimmed mounting hole |
| M03 | Implemented artistic board feature | corner | 0.97, 0.96 | createSlab geometric opening + gold-colored annulus | Right-corner gold-rimmed mounting hole |
| M04 | Implemented artistic board feature | corner | 0.96, 0.045 | createSlab geometric opening + gold-colored annulus | Partly occluded/cropped rear-corner gold-rimmed hole |
| B01 | Implemented shared rendering feature | shared | — | VisualRenderer.createSlab: extruded mask/substrate with geometric openings | Green rectangular board slab with visible near-edge thickness |
| B02 | Implemented shared rendering feature | shared | — | createSlab: separate olive-brown sidewall material | Dark green/brown near-edge band |
| B03 | Implemented shared rendering feature | shared | — | illustrativeGuideGeometry.paths: 93 explicitly illustrative flat surface paths | Lighter green branching fine lines between component terminals |
| B04 | Implemented shared rendering feature | shared | — | illustrativeSurfaceFeatures.items: 24 authored ring/opening details; no connectivity | Numerous small round holes/dots along traces |
| B05 | Implemented shared rendering feature | shared | — | visual-assets.js: owning package solder feet / attachment details | Silver rectangular attachment lands under metal component feet |
| B06 | Implemented shared rendering feature | shared | — | visual-layers.js: authored Ohmni visual IDs and neutral sample title | White/light-gray component labels, outlines and orientation marks |
| B07 | Implemented shared rendering feature | shared | — | visual-assets.js: owning package mold marks and restrained authored printing | Dark circles/chamfers on IC tops |
| B08 | Implemented shared rendering feature | shared | — | visual-assets.js: individually shaped metallic lead shoulders, bends and feet | Numerous silver bent feet along black packages |
| B09 | Implemented shared rendering feature | shared | — | visual-assets.js: owning connector cavities, separate contacts and mounting detail | Recesses, gold contacts and white solder toes around headers |
| B10 | Implemented shared rendering feature | shared | — | VisualRenderer: procedural studio lighting, received and cast contact shadows | Dark halos and grounding shadows under parts |
| V01 | Viewport-only disposition | shared | — | Deliberately omitted: neutral Ohmni studio background instead of copied editor grid | Gray grid around board |
| V02 | Viewport-only disposition | shared | — | Native Ohmni Top / Underside / Edge view controls replace the source axis widget | Axis/corner widget at lower left |
| V03 | Viewport-only disposition | shared | — | Native Ohmni camera reset and view controls replace the source view cube | Orientation cube at top right |

## Family registry and education

All 18 sample families have catalog specimen data, a beginner explanation, a close-up inspection cue and a specific statement of what remains unknown. The asset library in the integrated explorer renders preview tiles from the same factories. Exact dimensions and selected lead/contact counts live in each instance's `modelAssumptions`; no source electrical metadata is fabricated.

| Family | Selectable body IDs | Registry binding |
|---|---|---|
| qfp | IC01, IC10 | ohmni-procedural/qfp@reference-packages-v1 |
| small_outline | IC02, IC03, IC04, IC05, IC06, IC07, IC08, IC09, S02, S04, S07, S08, S09, S11, S12, S15, S16, S17, S18, S20 | ohmni-procedural/small_outline@reference-packages-v1 |
| few_terminal | S01, S03, S13, S14 | ohmni-procedural/few_terminal@reference-packages-v1 |
| leadless_block | S05, S06, S10, S19 | ohmni-procedural/leadless_block@reference-packages-v1 |
| header | H01, H02, H03, H04, H05, H06 | ohmni-procedural/header@reference-packages-v1 |
| white_connector | J01, J02 | ohmni-procedural/white_connector@reference-packages-v1 |
| shielded_connector | J03 | ohmni-procedural/shielded_connector@reference-packages-v1 |
| rear_metal_block | J04, J05 | ohmni-procedural/rear_metal_block@reference-packages-v1 |
| aluminum_can | C01, C02, C03, C04, C05, C06, C07, C08, C09, C10, C11, C12, C13, C14, C15 | ohmni-procedural/aluminum_can@reference-packages-v1 |
| electrolytic_can | E01, E02, E03, E04 | ohmni-procedural/electrolytic_can@reference-packages-v1 |
| wound_inductor | L01 | ohmni-procedural/wound_inductor@reference-packages-v1 |
| coated_radial | O01 | ohmni-procedural/coated_radial@reference-packages-v1 |
| gold_post | T01, T02, T03, T04, T05, T06, T07, T08 | ohmni-procedural/gold_post@reference-packages-v1 |
| axial_resistor | P06, P07, P08, P09, P10, P11, P18, P21, P23, P25, P27, P28, P29, P30, P37, P40, P47, P50, P51, P52, P53, P54, P55, P56, P57, P58 | ohmni-procedural/axial_resistor@reference-packages-v1 |
| coated_axial | P01, P03, P05, P14, P17, P19, P20, P22, P24, P34, P41, P46, P49 | ohmni-procedural/coated_axial@reference-packages-v1 |
| ceramic_chip | P02, P04, P13, P15, P16, P26, P33, P35, P36, P42, P43, P45 | ohmni-procedural/ceramic_chip@reference-packages-v1 |
| coated_red | P12, P39, P44 | ohmni-procedural/coated_red@reference-packages-v1 |
| unresolved_patch | X01–X08 surface patches; no counted bodies | ohmni-procedural/unresolved_patch@reference-packages-v1 |

Procedural models, materials, letter shapes and studio lighting are original project source; no license was found in the repository, so their registry license is **UNSPECIFIED**, not an assumed MIT grant. Three.js is separately vendored under its own MIT license. No source screenshot, external font, texture or third-party model is shipped by this inventory. File hashes and local asset serving are maintained by the runtime asset manifest; the illustration uses the separate namespace `ohmni:illustrative-reference:v1`.

## Verification and remaining acceptance

`node --test apps/web/tests/visual-inventory.test.mjs` passed **10 tests**. Checks cover all 158 unique IDs and exact dispositions; 124 bodies / 54 passive bodies / 9 parent details; source-null and UNKNOWN-role separation; normalized scene transforms; no circuit, verification, BOM or release fields; eight unresolved non-body patches; 24 B04 surface details; eighteen model-registry family bindings; independent fresh manifests; and documentation coverage.

The model-bound layout check builds all 124 assemblies, including their actual rendered leads/feet, verifies they fit the chosen stage and verifies no pair has overlapping x/y bounding boxes above 0.001 mm numerical tolerance. This is a visual-layout regression check using artistic dimensions, **not PCB clearance, component-dimension or assembly verification**.

The five-object GPU proof was captured in the browser before the full library. The parent integration reports that the full sample renders through the application. Final screenshots, family macros, source-artifact hash invariance, measured load/geometry/frame costs and the human visual comparison are owned by the integration acceptance record. Do not interpret the passing inventory/model tests as human visual acceptance or validation of this sample's electronics.

Final integration: all18 family previews and macros captured; X01–X08 can be inspected through a separate non-component detail list or their library family tile. Final browser evidence, source hashes, independent review and remaining human acceptance are recorded in [IMPLEMENTATION_HANDOFF.md](IMPLEMENTATION_HANDOFF.md).
