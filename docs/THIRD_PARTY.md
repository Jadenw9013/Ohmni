# Third-party geometry provenance

Ohmni's bounded PCB compiler includes pad-geometry subsets derived from the
official KiCad footprint libraries distributed with KiCad 10. Each
`FootprintSource` records the upstream library identifier and SHA-256 of the
inspected `.kicad_mod` source.

KiCad library assets are distributed under CC BY-SA 4.0 with the KiCad library
exception. Ohmni retains only the pad geometry needed by the golden fixture and
marks the generated board footprints with their source identifiers. Runtime
compilation does not read a user's global footprint libraries.

This does not imply that a footprint is manufacturer-verified. Package binding
status and upstream geometry provenance remain separate facts.
