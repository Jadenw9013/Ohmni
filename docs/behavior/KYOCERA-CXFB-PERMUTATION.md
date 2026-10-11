# Kyocera CX3225FB / CX2016FB reference to OHM-143 / OHM-145 terminal binding

This binding changes terminal labels only. It does not verify the generic
crystal's physical dimensions or change the source specification.

Sources (archived in the run ledger, opened from the archived bytes):

- CX3225FB 8 pF specification, Drawing No. UKY1C-H1-25071-02[43], issued
  Jan.9,2026, https://ele.kyocera.com/assets/products/crystal-device/specification/CX3225FB_8pF.pdf
  (sha256 c515640ab68e4c7ed37406d46432ba2aacf6ffc00c596ba75ccf4701bcc0e31d).
- CX2016FB 8 pF specification, Drawing No. UKY1C-H1-25067-02[37], issued
  Jan.9,2026, https://ele.kyocera.com/assets/products/crystal-device/specification/CX2016FB_8pF.pdf
  (sha256 3cc7e6cd96df011e45a7445acbf99f24a0abb2438082c481f8b31db800253199).

Both sheets, page 4 section 2.1, show the lid-side outline with #4 top-left,
#3 top-right, #1 bottom-left, #2 bottom-right; the internal-connection sketch
joins the crystal blank to #1 and #3 (diagonal). The underside view mirrors X
(#3 top-left, #4 top-right, #2 bottom-left, #1 bottom-right). The pad table
assigns #1 = X'tal terminal (Input/output), #2 = GND terminal, #3 = X'tal
terminal (Input/output), #4 = GND terminal. Page 8 section 4.1 (marking)
repeats the lid-side corner labels (#4 upper-left, #3 upper-right, #1
lower-left, #2 lower-right) with the frequency print reading left to right and
"K" indicating the pin-1 direction.

The local `PCB_COMPONENT_3D_LIBRARY_SPEC.md` (unchanged source) specifies
library terminals, top view, counter-clockwise from top-left:
OHM-143 (line 20349) 1=(-1.1,+0.8), 2=(-1.1,-0.8), 3=(+1.1,-0.8), 4=(+1.1,+0.8);
OHM-145 (line 20578) 1=(-0.675,+0.525), 2=(-0.675,-0.525), 3=(+0.675,-0.525),
4=(+0.675,+0.525).
Keeping the same X/Y axes (long side along X, print reading left to right)
gives this derived correspondence:

| Manufacturer pad | Source lid-side corner | Library terminal | Electrical role |
| --- | --- | --- | --- |
| 1 | bottom-left | 2 | A |
| 2 | bottom-right | 3 | LID1 |
| 3 | top-right | 4 | B |
| 4 | top-left | 1 | LID2 |

The behavioral recipe therefore assigns library 1=LID2, 2=A, 3=LID1, 4=B and
retains the manufacturer's original map as evidence. The crystal terminals
stay diagonal (library 2 and 4), so the class rule "crystal on a diagonal
pair, lid on the other" still holds; only which diagonal changes. Removing or
changing the permutation refuses compilation. The generic library pin-1 dot
marks library terminal 1, which is a Kyocera GND pad, not the Kyocera pin-1
("K") direction. Pad sizes and positions of the generic library footprint
differ from the Kyocera drawing (CX3225FB pads about 0.9 x 0.8 mm at about
+/-1.05, +/-0.75; CX2016FB pads about 0.55 x 0.45 mm at about +/-0.625,
+/-0.475; derived from the page-4 dimensions) and must not be used as
manufacturing evidence. The runtime package selections are explicitly named
`3225 Kyocera CX3225FB reference` and `2016 Kyocera CX2016FB reference` to
prevent automatic substitution for a generic crystal.
