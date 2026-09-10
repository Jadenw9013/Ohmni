These unmodified KiCad 10 library files were inspected on 2026-09-09 to
correct the project's through-hole land, drill, and locating-hole geometry.
Their raw SHA-256 hashes are pinned in `physical/footprints.py` and checked
against these files by `tests/test_footprint_drills.py`.

Upstream: KiCad footprint libraries, https://gitlab.com/kicad/libraries/kicad-footprints.
License: CC-BY-SA-4.0 with the KiCad libraries exception
(https://www.kicad.org/libraries/license/).

The push-button's local coordinates are translated by (-3.25, -2.25) mm to
center its placement envelope. Its source pad numbers, shapes, sizes, and
drills remain unchanged. The USB-C footprint's source includes both plated
shield slots and non-plated locating holes; both are retained.

These snapshots ground local footprint geometry. They do not establish
component authenticity, assembly suitability, or manufacturer acceptance.
