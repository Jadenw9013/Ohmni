"""Local deterministic PDF normalization using PyMuPDF."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

import pymupdf

from ..domain import (
    DatasheetDocument,
    DatasheetIdentity,
    DocumentFingerprint,
    DocumentMetadata,
    DocumentPage,
    DocumentRegion,
    DocumentSpan,
)
from ..domain.component_synthesis import SourceRegion
from .observations import (
    MAX_OBSERVED_PAGES,
    MAX_RECTANGLES_PER_PAGE,
    MAX_RULES_PER_PAGE,
    MAX_TOKENS_PER_PAGE,
    DocumentObservationBundle,
    ObservationLimitError,
    PageObservation,
    PageRender,
    TextToken,
    VectorRectangle,
    VectorRule,
)


class PdfIngestStatus(StrEnum):
    INVALID_PDF = "invalid_pdf"
    ENCRYPTED = "encrypted"
    EMPTY = "empty"
    UNSUPPORTED_TEXT_EXTRACTION = "unsupported_text_extraction"
    TOO_LARGE = "too_large"
    PARSER_ERROR = "parser_error"


class PdfIngestError(ValueError):
    def __init__(self, status: PdfIngestStatus, detail: str) -> None:
        self.status = status
        super().__init__(detail)


class PyMuPdfExtractor:
    """Parses once per SHA-256 fingerprint; OCR is never invoked implicitly."""

    def __init__(self, *, max_bytes: int = 25 * 1024 * 1024, max_pages: int = 500) -> None:
        self.max_bytes = max_bytes
        self.max_pages = max_pages
        self._cache: dict[str, DatasheetDocument] = {}

    def load(self, path: Path) -> DatasheetDocument:
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise PdfIngestError(PdfIngestStatus.PARSER_ERROR, str(exc)) from exc
        if len(data) > self.max_bytes:
            raise PdfIngestError(PdfIngestStatus.TOO_LARGE, "PDF exceeds configured size limit")
        digest = hashlib.sha256(data).hexdigest()
        if digest in self._cache:
            return self._cache[digest]
        try:
            pdf = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise PdfIngestError(PdfIngestStatus.INVALID_PDF, str(exc)) from exc
        try:
            if pdf.needs_pass:
                raise PdfIngestError(PdfIngestStatus.ENCRYPTED, "encrypted PDF requires a password")
            if pdf.page_count == 0:
                raise PdfIngestError(PdfIngestStatus.EMPTY, "PDF has no pages")
            if pdf.page_count > self.max_pages:
                raise PdfIngestError(PdfIngestStatus.TOO_LARGE, "PDF exceeds configured page limit")
            pages = [self._page(pdf[i], i + 1) for i in range(pdf.page_count)]
            if not any(page.text.strip() for page in pages):
                raise PdfIngestError(
                    PdfIngestStatus.UNSUPPORTED_TEXT_EXTRACTION,
                    "PDF contains no extractable text; OCR was not attempted",
                )
            raw_meta = pdf.metadata or {}
            identity = _detect_identity(pages, raw_meta)
            metadata = DocumentMetadata(
                document_id=f"sha256:{digest}",
                fingerprint=DocumentFingerprint(digest=digest),
                title=raw_meta.get("title") or None,
                page_count=pdf.page_count,
                identity=identity,
            )
            result = DatasheetDocument(metadata=metadata, pages=pages)
            self._cache[digest] = result
            return result
        except PdfIngestError:
            raise
        except Exception as exc:
            raise PdfIngestError(PdfIngestStatus.PARSER_ERROR, str(exc)) from exc
        finally:
            pdf.close()

    @staticmethod
    def _page(page: pymupdf.Page, number: int) -> DocumentPage:
        lines: list[str] = []
        spans: list[DocumentSpan] = []
        cursor = 0
        blocks = sorted(page.get_text("blocks"), key=lambda b: (round(b[1], 1), b[0]))
        for block in blocks:
            text = " ".join(str(block[4]).split())
            if not text:
                continue
            if lines:
                cursor += 1
            start = cursor
            lines.append(text)
            cursor += len(text)
            spans.append(DocumentSpan(
                start=start, end=cursor, text=text,
                region=DocumentRegion(x0=block[0], y0=block[1], x1=block[2], y1=block[3]),
            ))
        return DocumentPage(number=number, text="\n".join(lines), spans=spans)


def _detect_identity(pages: list[DocumentPage], metadata: dict) -> DatasheetIdentity:
    head = "\n".join(page.text for page in pages[:3])
    upper = head.upper()
    manufacturer = "Bosch Sensortec" if "BOSCH SENSORTEC" in upper else None
    # Identity is taken from the cover, not every mentioned compatible part.
    # BME280 legitimately mentions BMP280 compatibility later in its preface.
    cover = pages[0].text.upper()
    known = [part for part in ("BME280", "BMP280") if part in cover]
    revision = None
    import re
    match = re.search(r"(?:revision|rev\.?|document revision)\s*[: ]\s*([A-Z0-9.\-]+)", head, re.IGNORECASE)
    if match:
        revision = match.group(1)
    date_match = re.search(r"document release date\s+([^\n]+)", head, re.IGNORECASE)
    date = date_match.group(1).strip() if date_match else (
        metadata.get("modDate") or metadata.get("creationDate") or None
    )
    return DatasheetIdentity(
        manufacturer=manufacturer,
        detected_parts=known,
        revision=revision,
        date=date,
        ambiguous=len(known) > 1,
    )


#: Version of the observation extraction rules below. It is recorded in every
#: bundle so a later change to token ordering or rectangle selection makes old
#: receipts visibly historical rather than silently current.
OBSERVATION_PARSER_VERSION = "1.0.0"
#: Locally rendered page images for vision. 200 DPI keeps a US Letter page under
#: two megapixels while leaving a 0.35 mm printed gap several pixels wide.
DEFAULT_RENDER_DPI = 200
#: Preflight budgets. These are checked BEFORE the expensive operation, not
#: after it: a bound enforced once a 38000 by 38000 pixel raster already exists
#: has not bounded anything. A2 is about 1700 points on its long side, so this
#: accepts every realistic datasheet page and refuses a page built to exhaust
#: memory.
MAX_PAGE_POINTS = 5000
#: Rendered pixels per page, and across one observation request.
MAX_RENDER_PIXELS = 40_000_000
MAX_TOTAL_RENDER_PIXELS = 120_000_000
#: Raw content-stream bytes per page, checked before the stream is interpreted.
MAX_PAGE_CONTENT_BYTES = 16 * 1024 * 1024
#: Longest single token. A word longer than this is rejected, not truncated:
#: silently shortening an observation makes "the text does not say that" and
#: "we stopped reading" indistinguishable, which is the same failure the page
#: bounds exist to prevent.
MAX_TOKEN_CHARS = 200
#: A drawn shape no thicker than this is a printed rule, not a filled area.
RULE_THICKNESS_PT = 1.5
#: How far a line segment may deviate from an axis and still be a rule.
RULE_ALIGNMENT_PT = 0.3


class BoundedObservationExtractor:
    """Records tokens, axis-aligned vector rectangles and page renders.

    Deliberately separate from :class:`PyMuPdfExtractor`, which produces the
    block-level document the existing text pipeline consumes. This one produces
    word-level geometry, because a table cell cannot be bound to a column from
    block text alone.

    Bounds fail closed: a page with more tokens or rectangles than the configured
    limit raises :class:`~ohmni.datasheet.observations.ObservationLimitError`
    rather than yielding a truncated page, so "not present in the source" can
    never mean "we stopped reading".
    """

    def __init__(
        self,
        *,
        max_bytes: int = 64 * 1024 * 1024,
        max_tokens_per_page: int = MAX_TOKENS_PER_PAGE,
        max_rectangles_per_page: int = MAX_RECTANGLES_PER_PAGE,
        render_dpi: int = DEFAULT_RENDER_DPI,
    ) -> None:
        self.max_bytes = max_bytes
        self.max_tokens_per_page = max_tokens_per_page
        self.max_rectangles_per_page = max_rectangles_per_page
        self.render_dpi = render_dpi

    def observe(
        self, path: Path, pages: Sequence[int], *, render: bool = False
    ) -> tuple[DocumentObservationBundle, dict[int, bytes]]:
        """Observe the named 1-based pages of one PDF.

        Returns the bundle and, when ``render`` is set, the PNG bytes per page.
        The images are handed back separately rather than embedded: the bundle
        is a receipt input and stays small, while the pixels go straight to the
        provider adapter and are addressed by the digest the bundle records.
        """
        requested = sorted(set(pages))
        if not requested:
            raise PdfIngestError(PdfIngestStatus.EMPTY, "no pages were requested")
        if len(requested) > MAX_OBSERVED_PAGES:
            raise ObservationLimitError(
                f"{len(requested)} pages requested; the bound is {MAX_OBSERVED_PAGES}"
            )
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise PdfIngestError(PdfIngestStatus.PARSER_ERROR, str(exc)) from exc
        if len(data) > self.max_bytes:
            raise PdfIngestError(PdfIngestStatus.TOO_LARGE, "PDF exceeds configured size limit")
        digest = hashlib.sha256(data).hexdigest()
        try:
            pdf = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise PdfIngestError(PdfIngestStatus.INVALID_PDF, str(exc)) from exc
        try:
            if pdf.needs_pass:
                raise PdfIngestError(PdfIngestStatus.ENCRYPTED, "encrypted PDF requires a password")
            if any(number < 1 or number > pdf.page_count for number in requested):
                raise PdfIngestError(
                    PdfIngestStatus.PARSER_ERROR,
                    f"requested page outside 1..{pdf.page_count}",
                )
            observed: list[PageObservation] = []
            images: dict[int, bytes] = {}
            total_pixels = 0
            for number in requested:
                page = pdf[number - 1]
                total_pixels += self._preflight(page, number, render=render)
                if total_pixels > MAX_TOTAL_RENDER_PIXELS:
                    raise ObservationLimitError(
                        f"the request would rasterise {total_pixels} pixels; the bound is "
                        f"{MAX_TOTAL_RENDER_PIXELS}"
                    )
                png = None
                if render:
                    pixmap = page.get_pixmap(dpi=self.render_dpi, alpha=False)
                    png = pixmap.tobytes("png")
                    images[number] = png
                observed.append(self._page(page, number, png))
            bundle = DocumentObservationBundle(
                document_digest=digest,
                parser="pymupdf",
                parser_version=getattr(pymupdf, "__version__", "unknown"),
                renderer="pymupdf-pixmap",
                renderer_version=getattr(pymupdf, "__version__", "unknown"),
                page_count=pdf.page_count,
                pages=tuple(observed),
            )
            return bundle, images
        except (PdfIngestError, ObservationLimitError):
            raise
        except Exception as exc:
            raise PdfIngestError(PdfIngestStatus.PARSER_ERROR, str(exc)) from exc
        finally:
            pdf.close()

    def _preflight(self, page: pymupdf.Page, number: int, *, render: bool) -> int:
        """Reject an oversize page before anything expensive is allocated.

        Returns the pixel count this page would rasterise, so the caller can
        keep a running total across the request.
        """
        width, height = page.rect.width, page.rect.height
        if width > MAX_PAGE_POINTS or height > MAX_PAGE_POINTS:
            raise ObservationLimitError(
                f"page {number} measures {width:.0f} by {height:.0f} points; the bound is "
                f"{MAX_PAGE_POINTS}"
            )
        try:
            content_bytes = len(page.read_contents())
        except Exception:  # noqa: BLE001 - an unreadable stream is a rejection, not a value
            raise ObservationLimitError(
                f"page {number} content stream could not be read within its bound"
            ) from None
        if content_bytes > MAX_PAGE_CONTENT_BYTES:
            raise ObservationLimitError(
                f"page {number} carries {content_bytes} content bytes; the bound is "
                f"{MAX_PAGE_CONTENT_BYTES}"
            )
        scale = self.render_dpi / 72
        pixels = int(width * scale) * int(height * scale)
        if render and pixels > MAX_RENDER_PIXELS:
            raise ObservationLimitError(
                f"page {number} would rasterise to {pixels} pixels at {self.render_dpi} dpi; "
                f"the bound is {MAX_RENDER_PIXELS}"
            )
        return pixels if render else 0

    def _page(self, page: pymupdf.Page, number: int, png: bytes | None) -> PageObservation:
        raw = page.get_text("words")
        if len(raw) > self.max_tokens_per_page:
            raise ObservationLimitError(
                f"page {number} has {len(raw)} tokens; the bound is {self.max_tokens_per_page}"
            )
        # Reading order is (top, left) with the same rounding used wherever a row
        # is reconstructed, so token IDs are stable across runs and machines.
        raw.sort(key=lambda w: (round(w[3], 2), round(w[0], 2), w[4]))
        for word in raw:
            if len(str(word[4])) > MAX_TOKEN_CHARS:
                raise ObservationLimitError(
                    f"page {number} carries a {len(str(word[4]))} character token; the bound "
                    f"is {MAX_TOKEN_CHARS}. It is rejected rather than truncated, so a "
                    "shortened observation can never look like an absent one."
                )
        tokens = tuple(
            TextToken(
                token_id=f"p{number}t{index}",
                text=str(word[4]),
                region=SourceRegion(x0=word[0], y0=word[1], x1=word[2], y1=word[3]),
            )
            for index, word in enumerate(
                [w for w in raw if str(w[4]).strip() and w[2] > w[0] and w[3] > w[1]]
            )
        )
        rectangles, rules = self._vectors(page, number)
        render = None
        if png is not None:
            render = PageRender(
                dpi=self.render_dpi,
                width_px=round(page.rect.width * self.render_dpi / 72),
                height_px=round(page.rect.height * self.render_dpi / 72),
                image_digest=hashlib.sha256(png).hexdigest(),
            )
        return PageObservation(
            number=number,
            width_pt=page.rect.width,
            height_pt=page.rect.height,
            rotation=page.rotation % 360,
            tokens=tokens,
            rectangles=rectangles,
            rules=rules,
            render=render,
        )

    def _vectors(
        self, page: pymupdf.Page, number: int
    ) -> tuple[tuple[VectorRectangle, ...], tuple[VectorRule, ...]]:
        """Split drawn vectors into shapes and axis-aligned rules.

        A table border reaches the page either as a thin filled rectangle or as
        a line segment, depending on the producer; both are the same fact, so
        both become a :class:`VectorRule`. Anything thin enough to be a rule is
        recorded only as one, so a stack of table borders can never be mistaken
        for a congruent group of lands.
        """
        shapes: list[tuple[float, float, float, float, bool, bool]] = []
        rules: list[tuple[str, float, float, float, float]] = []
        for drawing in page.get_drawings():
            stroked = drawing.get("type") in {"s", "fs"}
            filled = drawing.get("type") in {"f", "fs"}
            width = drawing.get("width") or 0.0
            for item in drawing["items"]:
                if item[0] == "re":
                    rect = item[1]
                    if rect.x1 <= rect.x0 or rect.y1 <= rect.y0:
                        continue
                    thin_h = rect.y1 - rect.y0 <= RULE_THICKNESS_PT
                    thin_v = rect.x1 - rect.x0 <= RULE_THICKNESS_PT
                    if thin_h and not thin_v:
                        rules.append(("horizontal", (rect.y0 + rect.y1) / 2, rect.x0, rect.x1,
                                      rect.y1 - rect.y0))
                    elif thin_v and not thin_h:
                        rules.append(("vertical", (rect.x0 + rect.x1) / 2, rect.y0, rect.y1,
                                      rect.x1 - rect.x0))
                    else:
                        shapes.append((rect.x0, rect.y0, rect.x1, rect.y1, stroked, filled))
                elif item[0] == "l":
                    start, end = item[1], item[2]
                    if abs(start.y - end.y) <= RULE_ALIGNMENT_PT and start.x != end.x:
                        rules.append(("horizontal", (start.y + end.y) / 2,
                                      min(start.x, end.x), max(start.x, end.x), width))
                    elif abs(start.x - end.x) <= RULE_ALIGNMENT_PT and start.y != end.y:
                        rules.append(("vertical", (start.x + end.x) / 2,
                                      min(start.y, end.y), max(start.y, end.y), width))
        unique_shapes = sorted(set(shapes), key=lambda r: (round(r[1], 2), round(r[0], 2)))
        if len(unique_shapes) > self.max_rectangles_per_page:
            raise ObservationLimitError(
                f"page {number} has {len(unique_shapes)} rectangles; "
                f"the bound is {self.max_rectangles_per_page}"
            )
        unique_rules = sorted(
            {(kind, round(pos, 3), round(low, 3), round(high, 3), round(thickness, 3))
             for kind, pos, low, high, thickness in rules},
            key=lambda r: (r[0], r[1], r[2]),
        )
        if len(unique_rules) > MAX_RULES_PER_PAGE:
            raise ObservationLimitError(
                f"page {number} has {len(unique_rules)} rules; the bound is {MAX_RULES_PER_PAGE}"
            )
        return (
            tuple(
                VectorRectangle(
                    feature_id=f"p{number}v{index}",
                    region=SourceRegion(x0=item[0], y0=item[1], x1=item[2], y1=item[3]),
                    stroked=item[4],
                    filled=item[5],
                )
                for index, item in enumerate(unique_shapes)
            ),
            tuple(
                VectorRule(
                    rule_id=f"p{number}r{index}", orientation=item[0], position=item[1],
                    start=item[2], end=item[3], thickness=item[4],
                )
                for index, item in enumerate(unique_rules)
            ),
        )
