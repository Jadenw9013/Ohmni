"""Carrier lands from bundled Adafruit Eagle CAD; no runtime network lookup.

Coordinates use the source PCB top view, centered outline, y inverted for KiCad.
The mic JP2 uses MR0: its x coordinates must be mirrored. Both modules stand
above the carrier on headers; module internals are not carrier copper.
"""
import hashlib
from pathlib import Path

from .models import FootprintDefinition, FootprintDrill, FootprintPad, FootprintSource


def recorder_footprints():
    root = Path(__file__).parents[1] / "catalog/data/recorder"
    values = []
    for name, filename, width, height, count, pitch_sign, y in (
        ("I2S-SPH0645-BREAKOUT", "Adafruit I2S Mic SPK0415HM4H.brd", 16.51, 12.7, 6, -1, 3.81),
        ("MICROSD-SDIO-BREAKOUT", "Adafruit SDIO microSD.brd", 25.4, 22.86, 9, 1, 8.89),
    ):
        values.append(FootprintDefinition(
            footprint_id="Ohmni:" + name, width_mm=width + 1, height_mm=height + 1,
            source=FootprintSource(library_id="Ohmni:" + name,
                upstream_file_sha256=hashlib.sha256((root / filename).read_bytes()).hexdigest(),
                license="Adafruit Creative Commons Attribution Share-Alike; bundled source license",
                derivation="Source header positions, translated to centered module outline and Y inverted; 1 mm courtyard allowance. Carrier lands 1.8 mm with 1 mm drills are authored header assembly policy."),
            pads=[FootprintPad(number=str(i + 1), x_mm=pitch_sign * (i - (count - 1) / 2) * 2.54,
                y_mm=y, width_mm=1.8, height_mm=1.8, kind="thru_hole",
                shape="rect" if i == 0 else "circle",
                drill=FootprintDrill(shape="circle", width_mm=1, height_mm=1)) for i in range(count)],
        ))
    return values
