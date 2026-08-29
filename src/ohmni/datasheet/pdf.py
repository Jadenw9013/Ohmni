"""Local deterministic PDF normalization using PyMuPDF."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path

import pymupdf

from ..domain import (
    DatasheetDocument, DatasheetIdentity, DocumentFingerprint, DocumentMetadata,
    DocumentPage, DocumentRegion, DocumentSpan,
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
    match = re.search(r"(?:revision|rev\.?|document revision)\s*[: ]\s*([A-Z0-9.\-]+)", head, re.I)
    if match:
        revision = match.group(1)
    date_match = re.search(r"document release date\s+([^\n]+)", head, re.I)
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
