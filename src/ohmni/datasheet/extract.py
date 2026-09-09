"""Bounded candidate discovery. Document text remains data, never instructions."""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from ..domain import DatasheetDocument, Interface, Quantity, Unit, parse_quantity
from .models import CandidateClaim, FactType


@runtime_checkable
class CandidateExtractor(Protocol):
    def extract(self, document: DatasheetDocument) -> list[CandidateClaim]: ...


class BoundedTextExtractor:
    """Small deterministic extractor for the MVP fact vocabulary.

    It intentionally recognizes only explicit prose/table rows. An LLM-backed
    extractor may later implement the same protocol, but receives document text
    only in its provider's data field and its output still passes independent
    verification.
    """

    def extract(self, document: DatasheetDocument) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        identity = document.metadata.identity
        for kind, value in (
            (FactType.MANUFACTURER, identity.manufacturer),
            (FactType.PART_NUMBER, identity.detected_parts[0] if len(identity.detected_parts) == 1 else None),
            (FactType.REVISION, identity.revision),
        ):
            if value:
                located = next(
                    ((page.number, span.text) for page in document.pages[:3] for span in page.spans
                     if value.casefold() in span.text.casefold()),
                    None,
                )
                if located:
                    claims.append(self._text(located[0], located[1], kind, value))
        for page in document.pages:
            for span in page.spans:
                text = span.text
                lower = text.lower()
                for rail, lo, hi in re.findall(
                    r"\b(VDDIO|VDD)\b[^\n]{0,80}?(1(?:\.\d+)?)\s*(?:V|volt)[^\n]{0,30}?(\d(?:\.\d+)?)\s*(?:V|volt)",
                    text, re.IGNORECASE,
                ):
                    if "operat" in lower or "recommended" in lower:
                        claims.extend([
                            self._q(page.number, text, FactType.SUPPLY_OPERATING_MIN, rail.upper(), float(lo)),
                            self._q(page.number, text, FactType.SUPPLY_OPERATING_MAX, rail.upper(), float(hi)),
                        ])
                for rail, value in re.findall(
                    r"\b(VDDIO|VDD)\b[^\n]{0,60}?(\d(?:\.\d+)?)\s*(?:V|volt)", text, re.IGNORECASE
                ):
                    if "absolute maximum" in lower or "absolute ratings" in lower:
                        claims.append(self._q(
                            page.number, text, FactType.SUPPLY_ABSOLUTE_MAX, rail.upper(), float(value)
                        ))
                if "i2c" in lower or "i²c" in lower:
                    claims.append(self._text(page.number, text, FactType.INTERFACE, Interface.I2C.value))
                if "spi" in lower:
                    claims.append(self._text(page.number, text, FactType.INTERFACE, Interface.SPI.value))
                if "pull-up" in lower and ("required" in lower or "resistor" in lower):
                    claims.append(self._text(
                        page.number, text, FactType.PULL_UP_REQUIREMENT, "pull-up"
                    ))
                if "direct connection" in lower and "csb" in lower and "vddio" in lower:
                    claims.append(self._text(
                        page.number, text, FactType.CONTROL_CONDITION, "CSB"
                    ))
                package = re.search(r"\b(LGA(?:-?8)?)\b", text, re.IGNORECASE)
                if package and ("package" in lower or "metal lid" in lower):
                    claims.append(self._text(page.number, text, FactType.PACKAGE, package.group(1).upper()))
                pin = re.match(
                    r"^([1-9][0-9]*)\s+(GND|CSB|SDI|SCK|SDO|VDDIO|VDD)\s+(.+)$", text, re.IGNORECASE
                )
                if pin and not text.lower().startswith("pin "):
                    claims.append(CandidateClaim(
                        candidate_id=f"p{page.number}-pin-{pin.group(1)}",
                        fact_type=FactType.PIN, page=page.number, supporting_text=text,
                        pin_number=pin.group(1), text_value=pin.group(2).upper(),
                        pin_function=pin.group(3),
                    ))
                cap = re.search(r"\b(VDDIO|VDD)\b[^\n]{0,80}?\b(\d+(?:\.\d+)?\s*(?:pF|nF|uF|µF))\b", text, re.IGNORECASE)
                if cap and ("decoupl" in lower or "capacitor" in lower):
                    claims.append(CandidateClaim(
                        candidate_id=f"p{page.number}-decoupling-{len(claims)}",
                        fact_type=FactType.DECOUPLING_CAPACITANCE,
                        page=page.number, supporting_text=text, rail=cap.group(1).upper(),
                        quantity=parse_quantity(cap.group(2), unit=Unit.FARAD),
                    ))
                elif "recommended value" in lower and ("capacitor" in lower or "c1" in lower):
                    cap_value = re.search(r"(\d+(?:\.\d+)?\s*(?:pF|nF|uF|µF))\b", text, re.IGNORECASE)
                    if cap_value:
                        claims.append(CandidateClaim(
                            candidate_id=f"p{page.number}-decoupling-{len(claims)}",
                            fact_type=FactType.DECOUPLING_CAPACITANCE,
                            page=page.number, supporting_text=text,
                            quantity=parse_quantity(cap_value.group(1), unit=Unit.FARAD),
                        ))
                for address in re.findall(r"0x([0-9a-f]{2})", text, re.IGNORECASE):
                    if int(address, 16) <= 0x7F and ("i2c" in lower or "address" in lower):
                        claims.append(CandidateClaim(
                            candidate_id=f"p{page.number}-address-{address}-{len(claims)}",
                            fact_type=FactType.I2C_ADDRESS, page=page.number,
                            supporting_text=text, integer_value=int(address, 16),
                        ))
            if "absolute maximum" in page.text.lower():
                for span in page.spans:
                    match = re.search(
                        r"supply pin\s+VDD\s+and\s+VDDIO[^\n]*?(-?\d+(?:\.\d+)?)\s*V\b",
                        span.text, re.IGNORECASE,
                    )
                    if match:
                        value = float(match.group(1))
                        for rail in ("VDD", "VDDIO"):
                            claims.append(self._q(
                                page.number, span.text, FactType.SUPPLY_ABSOLUTE_MAX, rail, value
                            ))
        unique: dict[tuple, CandidateClaim] = {}
        for claim in claims:
            key = (
                claim.fact_type, claim.rail, claim.pin_number,
                claim.quantity, claim.text_value, claim.integer_value,
            )
            unique.setdefault(key, claim)
        return list(unique.values())

    @staticmethod
    def _q(page: int, text: str, kind: FactType, rail: str, value: float) -> CandidateClaim:
        return CandidateClaim(
            candidate_id=f"p{page}-{kind.value}-{rail}", fact_type=kind, page=page,
            supporting_text=text, rail=rail, quantity=Quantity.volts(value),
        )

    @staticmethod
    def _text(page: int, text: str, kind: FactType, value: str) -> CandidateClaim:
        return CandidateClaim(
            candidate_id=f"p{page}-{kind.value}-{value}", fact_type=kind, page=page,
            supporting_text=text, text_value=value,
        )
