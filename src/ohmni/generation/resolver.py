"""Deterministic catalog-only component resolution."""

from ..adapters import PartCatalog
from ..domain import ClaimStatus, status_rank
from .models import ComponentCandidate, ComponentRequest


def resolve_components(request: ComponentRequest, catalog: PartCatalog) -> list[ComponentCandidate]:
    words = set(request.capability.lower().replace("-", " ").split())
    candidates = []
    for part in catalog.all_parts():
        haystack = f"{part.category.value} {part.description} {part.display_name}".lower()
        if words and not any(word in haystack for word in words):
            continue
        if request.hand_solderable_preferred and not any(p.hand_solderable for p in part.packages):
            continue
        evidence = [e for pin in part.pins for e in pin.evidence]
        statuses = {"identity": max((e.status for e in part.evidence), default=ClaimStatus.UNKNOWN, key=status_rank).value}
        candidates.append(ComponentCandidate(part_id=part.part_id, display_name=part.display_name, fact_statuses=statuses, evidence=evidence))
    return candidates
