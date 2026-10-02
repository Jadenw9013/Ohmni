#!/usr/bin/env python3
"""Compose the CS-T04 visual evidence: generated CAD beside its source regions.

Three panels, each pairing what Ohmni emitted with the exact region of the
manufacturer document the deterministic checks relocated:

1. the generated footprint render beside the RECOMMENDED LAND PATTERN table;
2. the same render beside the land-pattern drawing whose printed pin labels
   anchored the numbering;
3. the generated symbol render beside the PIN FUNCTION table.

The crops are taken from the same locally rendered pages the observation bundle
recorded, at the coordinates the receipts name, so the picture and the receipts
describe the same pixels.

Usage::

    python scripts/component_cad_proof.py
    python scripts/component_cad_evidence_images.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ohmni.datasheet.pdf import BoundedObservationExtractor

DOCUMENT_ID = "MCP73831-DS20001984H"
CROP_DPI = 200
PANEL_MARGIN = 18
LABEL_HEIGHT = 34
LABEL_FONT_SIZE = 9

#: Regions in PDF points, taken from the receipts the source checks produced.
CROPS = {
    "land_pattern_table": (24, (130, 520, 520, 700)),
    "land_pattern_drawing": (24, (180, 150, 420, 500)),
    "pin_function_table": (11, (75, 105, 555, 295)),
}


def _crop(pdf: Path, page_number: int, box: tuple[float, float, float, float]) -> bytes:
    document = pymupdf.open(pdf)
    try:
        page = document[page_number - 1]
        clip = pymupdf.Rect(*box)
        return page.get_pixmap(dpi=CROP_DPI, clip=clip, alpha=False).tobytes("png")
    finally:
        document.close()


def _svg_png(svg: Path, scale: float) -> bytes:
    document = pymupdf.open(svg)
    try:
        page = document[0]
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")
    finally:
        document.close()


def _panel(
    title: str, left_label: str, left_png: bytes, right_label: str, right_png: bytes,
    destination: Path,
) -> None:
    left = pymupdf.open("png", left_png)[0].rect
    right = pymupdf.open("png", right_png)[0].rect
    label_font = pymupdf.Font("helv")
    left_label_width = label_font.text_length(left_label, LABEL_FONT_SIZE)
    # The panel is never narrower than its own captions: an overlapping label
    # would make the evidence harder to read than the thing it describes.
    offset = max(PANEL_MARGIN * 2 + left.width, PANEL_MARGIN * 2 + left_label_width)
    right_width = max(right.width, label_font.text_length(right_label, LABEL_FONT_SIZE))
    width = offset + right_width + PANEL_MARGIN
    height = max(left.height, right.height) + LABEL_HEIGHT * 2 + PANEL_MARGIN * 2
    document = pymupdf.open()
    page = document.new_page(width=width, height=height)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    page.insert_text((PANEL_MARGIN, 22), title, fontsize=13, fontname="hebo")
    top = LABEL_HEIGHT + PANEL_MARGIN
    page.insert_text((PANEL_MARGIN, top - 6), left_label, fontsize=LABEL_FONT_SIZE)
    page.insert_image(
        pymupdf.Rect(PANEL_MARGIN, top, PANEL_MARGIN + left.width, top + left.height),
        stream=left_png,
    )
    page.insert_text((offset, top - 6), right_label, fontsize=LABEL_FONT_SIZE)
    page.insert_image(
        pymupdf.Rect(offset, top, offset + right.width, top + right.height), stream=right_png
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(page.get_pixmap(dpi=150, alpha=False).tobytes("png"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="build/component_synthesis/evidence")
    args = parser.parse_args(argv)
    out_dir = (ROOT / args.out).resolve()
    manifest = json.loads((ROOT / "tests/corpus/manifest.json").read_text(encoding="utf-8"))
    pdf = ROOT / manifest["workspace"] / f"{DOCUMENT_ID}.pdf"
    if not pdf.is_file():
        print(f"ABSENT: {pdf.relative_to(ROOT)} -- run scripts/acquire_corpus.py first")
        return 2
    evidence_path = ROOT / "build/component_synthesis/CS-T04_evidence.json"
    if not evidence_path.is_file():
        print("ABSENT: CS-T04 evidence -- run scripts/component_cad_proof.py first")
        return 2
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    # Re-derive the observations so the crops and the receipts describe the same
    # rendered pages, rather than a separately rendered picture that merely looks
    # like them.
    bundle, _ = BoundedObservationExtractor().observe(
        pdf, sorted({page for page, _ in CROPS.values()})
    )
    assert bundle.document_digest == evidence["document"]["sha256"]

    footprint_svg = ROOT / "build/component_synthesis/renders/footprint" / (
        evidence["land_pattern"]["name"] + ".svg"
    )
    symbol_svg = next(
        (ROOT / "build/component_synthesis/renders/symbol").glob("*.svg"), None
    )
    if not footprint_svg.is_file() or symbol_svg is None:
        print("ABSENT: KiCad renders -- run scripts/component_cad_proof.py first")
        return 2

    footprint_png = _svg_png(footprint_svg, 14.0)
    symbol_png = _svg_png(symbol_svg, 5.0)
    digest = evidence["document"]["sha256"][:12]

    page_number, box = CROPS["land_pattern_table"]
    _panel(
        "CS-T04  generated footprint  vs  manufacturer recommended land table",
        f"Ohmni {evidence['land_pattern']['name']} "
        f"({evidence['artifacts']['footprint']['sha256'][:12]}), rendered by KiCad 10.0.5",
        footprint_png,
        f"{DOCUMENT_ID} page {page_number}, sha256 {digest}",
        _crop(pdf, page_number, box),
        out_dir / "01_footprint_vs_land_table.png",
    )
    page_number, box = CROPS["land_pattern_drawing"]
    _panel(
        "CS-T04  generated footprint  vs  land-pattern drawing that anchored the numbering",
        "Ohmni generated footprint, rendered by KiCad 10.0.5",
        footprint_png,
        f"{DOCUMENT_ID} page {page_number}, printed labels 1, 2 and 5",
        _crop(pdf, page_number, box),
        out_dir / "02_footprint_vs_drawing.png",
    )
    page_number, box = CROPS["pin_function_table"]
    _panel(
        "CS-T04  generated symbol  vs  manufacturer pin function table",
        f"Ohmni {evidence['symbol']['name']} "
        f"({evidence['artifacts']['symbol']['sha256'][:12]}), rendered by KiCad 10.0.5",
        symbol_png,
        f"{DOCUMENT_ID} page {page_number}, SOT-23-5 column only",
        _crop(pdf, page_number, box),
        out_dir / "03_symbol_vs_pin_table.png",
    )
    for path in sorted(out_dir.glob("*.png")):
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
