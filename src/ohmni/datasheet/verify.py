"""Independent deterministic source relocation and semantic claim checking."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from ..domain import (
    DatasheetDocument,
    DocumentSpan,
    Evidence,
    EvidenceKind,
    Quantity,
    parse_quantity,
)
from .models import CandidateClaim, ClaimVerificationStatus, FactType, VerifiedCandidate


def _normalized(text: str) -> str:
    return " ".join(text.casefold().replace("−", "-").replace("–", "-").split())


def _find_source(document: DatasheetDocument, candidate: CandidateClaim) -> DocumentSpan | None:
    page = document.page(candidate.page)
    if page is None:
        return None
    needle = _normalized(candidate.supporting_text)
    for span in page.spans:
        actual = _normalized(span.text)
        if needle == actual or needle in actual or (
            len(actual) >= 40 and len(actual) >= len(needle) * 0.8 and actual in needle
        ):
            return span
    best = max(page.spans, key=lambda s: SequenceMatcher(None, needle, _normalized(s.text)).ratio(), default=None)
    if best and SequenceMatcher(None, needle, _normalized(best.text)).ratio() >= 0.92:
        return best
    return None


def _quantities(text: str) -> list[Quantity]:
    results: list[Quantity] = []
    for raw in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?\s*(?:mV|V|mA|uA|µA|A|MOhm|kOhm|Ohm|ohm|pF|nF|uF|µF|F))\b", text):
        try:
            results.append(parse_quantity(raw))
        except ValueError:
            pass
    return results


def _supports(candidate: CandidateClaim, text: str) -> tuple[bool, str | None]:
    lower = _normalized(text)
    operating = {
        FactType.SUPPLY_OPERATING_MIN, FactType.SUPPLY_OPERATING_TYP,
        FactType.SUPPLY_OPERATING_MAX,
    }
    absolute = {FactType.SUPPLY_ABSOLUTE_MIN, FactType.SUPPLY_ABSOLUTE_MAX}
    if candidate.fact_type in operating:
        if "absolute maximum" in lower or "absolute ratings" in lower:
            return False, "absolute-maximum context cannot support an operating rating"
        if not any(word in lower for word in ("operating", "recommended", "operational")):
            return False, "source lacks recommended-operating context"
    if candidate.fact_type in absolute and "absolute" not in lower:
        return False, "source lacks absolute-maximum context"
    if candidate.quantity is not None:
        quantities = _quantities(text)
        matching = [q for q in quantities if q.unit is candidate.quantity.unit and q.is_close(candidate.quantity)]
        if not matching:
            return False, "proposed quantity and unit are not present in the source"
    elif candidate.integer_value is not None:
        hex_form = f"0x{candidate.integer_value:02x}"
        if hex_form not in lower and str(candidate.integer_value) not in lower:
            return False, "proposed integer is not present in the source"
    elif candidate.text_value is not None:
        value = candidate.text_value.casefold()
        aliases = {"i2c": ("i2c", "i²c"), "spi": ("spi",)}.get(value, (value,))
        if not any(alias in lower for alias in aliases):
            return False, "proposed text value is not present in the source"
    if candidate.fact_type is FactType.PIN:
        if not candidate.pin_number or not re.search(rf"\b{re.escape(candidate.pin_number)}\b", text):
            return False, "proposed pin number is not present in the source"
        if candidate.pin_function and _normalized(candidate.pin_function) not in lower:
            return False, "proposed pin function is not present in the source"
    if candidate.rail and candidate.rail.casefold() not in lower:
        return False, "named supply rail is not present in the source"
    return True, None


def _semantic_context(document: DatasheetDocument, page_number: int, span: DocumentSpan) -> str:
    page = document.page(page_number)
    if page is None:
        return span.text
    index = next((i for i, item in enumerate(page.spans) if item == span), 0)
    return " ".join(item.text for item in page.spans[max(0, index - 4): index + 1])


def verify_candidate(document: DatasheetDocument, candidate: CandidateClaim) -> VerifiedCandidate:
    span = _find_source(document, candidate)
    if span is None:
        return VerifiedCandidate(
            candidate=candidate, status=ClaimVerificationStatus.SOURCE_NOT_FOUND,
            source_found=False, claim_supported=False,
            reasons=["proposed supporting text was not found on the cited page"],
        )
    if candidate.ambiguity or document.metadata.identity.ambiguous:
        return VerifiedCandidate(
            candidate=candidate, status=ClaimVerificationStatus.AMBIGUOUS,
            source_found=True, claim_supported=False, matched_span=span,
            reasons=candidate.ambiguity or ["datasheet identity covers multiple detected variants"],
        )
    supported, reason = _supports(candidate, _semantic_context(document, candidate.page, span))
    if not supported:
        return VerifiedCandidate(
            candidate=candidate, status=ClaimVerificationStatus.CLAIM_NOT_SUPPORTED,
            source_found=True, claim_supported=False, matched_span=span,
            reasons=[reason or "source does not support the proposed claim"],
        )
    region = span.region
    evidence = Evidence(
        kind=EvidenceKind.DATASHEET,
        label=candidate.fact_type.value.replace("_", " "),
        document=document.metadata.as_ref(), source_id=document.metadata.document_id,
        page=candidate.page, snippet=span.text, snippet_verified=True,
        source_start=span.start, source_end=span.end,
        source_region=None if region is None else (region.x0, region.y0, region.x1, region.y1),
        quantity=candidate.quantity,
        text_value=candidate.text_value if candidate.text_value is not None else (
            str(candidate.integer_value) if candidate.integer_value is not None else None
        ),
    )
    return VerifiedCandidate(
        candidate=candidate, status=ClaimVerificationStatus.VERIFIED,
        source_found=True, claim_supported=True, matched_span=span, evidence=evidence,
    )
