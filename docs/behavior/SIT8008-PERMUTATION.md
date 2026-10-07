# SiT8008 reference to OHM-146 terminal binding

This binding changes terminal labels only. It does not verify the generic
oscillator's physical dimensions or change the source specification.

The manufacturer SiT8008 Rev1.11 datasheet, PDF page9, shows the marked top
view with manufacturer terminals4/3 on the upper edge and1/2 on the lower
edge. The underside drawing mirrors X. The opened primary source is
https://www.sitime.com/sites/default/files/mature-datasheets/SiT8008-datasheet.pdf.
Its archived fetch is recorded in the run ledger. Page2 assigns1=OE,
2=GND,3=OUT,4=VDD. Page9 gives a7.0 x5.0 x0.90mm MEMS body.

The local `PCB_COMPONENT_3D_LIBRARY_SPEC.md`, OHM-146 Terminals paragraph
(line20692 in the unchanged source), specifies library terminals
1=(-2.54,+1.905),2=(-2.54,-1.905),3=(+2.54,-1.905),4=(+2.54,+1.905).
`apps/web/component-library/data/completion-b.json` retains that convention.
Keeping the same X/Y axes gives this derived correspondence:

| Manufacturer pin | Source top-view corner | Library terminal | Electrical role |
| --- | --- | --- | --- |
| 1 | bottom-left | 2 | OE |
| 2 | bottom-right | 3 | GND |
| 3 | top-right | 4 | OUT |
| 4 | top-left | 1 | VDD |

The behavioral recipe therefore assigns library1=VDD,2=OE,3=GND,4=OUT
and retains the manufacturer's original map as evidence. Removing or
changing the permutation refuses compilation. The generic 3D pin1 dot is
the library terminal1 marker; it is not the manufacturer's OE-pin marker.
The generic1.8mm ceramic body is not an exact model of the0.90mm MEMS part.
Pad geometry and case rendering remain provisional and must not be used
as evidence for manufacturing. The runtime package selection is explicitly
named `7050 SiT8008 reference` to prevent automatic substitution for a
generic ceramic7050 oscillator.
