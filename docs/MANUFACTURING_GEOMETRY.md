# Manufacturing geometry corrections

The M10 benchmark uses PCB compiler 0.2.0 and the explicitly synthetic
`generic-prototype-2l-v2` profile. Neither is a fabricator qualification.

Earlier PCB emission estimated every component drill as 55% of the smaller
copper-land dimension. This was incorrect for the programming header and USB-C
connector. Current emission uses explicit round or oval drill dimensions from
inspected KiCad source footprints. The USB-C shield lands and its two nonplated
locating holes are also preserved. Both-layer routing obstacles include those
holes; a locating hole is not electrical copper or a connected terminal.

The USB-C mounting slots are 0.6 x 1.7 mm at the rear and 0.6 x 1.2 mm at the
front; its locating holes are 0.65 mm round. Header drills are 1 mm and button
drills are 1.1 mm. The local footprint definitions record their inspected source
hashes. Each compiled footprint also records the local geometry hash, because
an upstream source hash alone cannot identify which subset was emitted.

Manufacturing verification now measures the minimum distance between actual
component copper lands, component hole widths, and slot widths. Pads on the
same explicit net are exempt from mutual electrical clearance; unassigned and
mechanical copper remain included. Nonplated holes count as drilled geometry,
not copper. Missing, unsupported, changed or stale geometry yields UNKNOWN.

The existing minimum track width (0.15 mm), copper clearance (0.15 mm), round
drill width (0.30 mm), via diameter (0.60 mm) and edge clearance (0.30 mm) are
unchanged. Version 2 explicitly adds slot support with a 0.60 mm minimum width.
Profiles without slot support fail a slotted design; profiles that declare
support but omit the minimum slot width produce UNKNOWN. This added synthetic
capability is recorded before benchmark execution. It is not retroactively
applied to historical verification results and is not a claim about a supplier.

The TMP102 footprint has a 0.15 mm gap between adjacent lands. A stricter
0.20 mm factory-clearance profile therefore fails that geometry even when the
router's requested clearance is 0.20 mm. Routing settings cannot stand in for
measurements of fixed component lands.

Saved runs with an older compiler or local footprint library fingerprint must
be regenerated. Their files remain available on disk for historical inspection;
they are no longer published as a current build package. Independent KiCad DRC
and fabrication export still run on each newly generated design. Physical fit,
assembly, and electrical operation still require human review and bench work.
