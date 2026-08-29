"""Orchestration without collapsing extraction and verification."""

from __future__ import annotations

from pathlib import Path

from ..domain import ComponentSpec
from .extract import CandidateExtractor
from .merge import apply_verified_claims
from .models import DatasheetIngestionReport, FactType
from .pdf import PyMuPdfExtractor
from .verify import verify_candidate


class DatasheetPipeline:
    def __init__(self, parser: PyMuPdfExtractor, extractor: CandidateExtractor) -> None:
        self.parser = parser
        self.extractor = extractor

    def ingest(
        self, path: Path, component: ComponentSpec | None = None
    ) -> tuple[DatasheetIngestionReport, ComponentSpec | None]:
        document = self.parser.load(path)
        candidates = self.extractor.extract(document)
        results = [verify_candidate(document, candidate) for candidate in candidates]
        required = {
            FactType.MANUFACTURER, FactType.PART_NUMBER, FactType.REVISION,
            FactType.PACKAGE, FactType.PIN,
            FactType.SUPPLY_OPERATING_MIN, FactType.SUPPLY_OPERATING_MAX,
            FactType.SUPPLY_ABSOLUTE_MAX, FactType.INTERFACE,
            FactType.I2C_ADDRESS, FactType.DECOUPLING_CAPACITANCE,
        }
        verified_types = {r.candidate.fact_type for r in results if r.claim_supported}
        unknown = sorted((kind.value for kind in required - verified_types))
        report = DatasheetIngestionReport(
            document=document, candidates=candidates, results=results,
            unknown_required_fields=unknown,
        )
        updated = None
        if component is not None:
            updated, conflicts = apply_verified_claims(component, results)
            report.conflicts = conflicts
        return report, updated


def format_ingestion_report(report: DatasheetIngestionReport) -> str:
    identity = report.document.metadata.identity
    lines = [
        "Ohmni datasheet ingestion report",
        f"Document: {report.document.metadata.document_id}",
        f"Manufacturer: {identity.manufacturer or 'UNKNOWN'}",
        f"Detected device: {', '.join(identity.detected_parts) or 'UNKNOWN'}",
        f"Revision: {identity.revision or 'UNKNOWN'}",
        "",
        f"Claims extracted: {len(report.candidates)}",
        f"Verified: {len(report.verified)}",
        f"Rejected: {len(report.rejected)}",
        f"Ambiguous: {len(report.ambiguous)}",
        f"Unknown: {len(report.unknown_required_fields)}",
        "",
    ]
    for result in report.results:
        claim = result.candidate
        value = claim.quantity.engineering() if claim.quantity else (
            claim.text_value if claim.text_value is not None else str(claim.integer_value)
        )
        lines.append(f"{claim.fact_type.value} ({claim.rail or '-'})")
        lines.append(f"  {value}  {result.claim_status.value}  page {claim.page}")
        if result.reasons:
            lines.append(f"  reason: {'; '.join(result.reasons)}")
    if report.unknown_required_fields:
        lines.extend(["", "Unknown required fields:", *[f"  - {x}" for x in report.unknown_required_fields]])
    if report.conflicts:
        lines.extend(["", "Evidence conflicts:"])
        lines.extend(f"  - {c.subject}: {c.existing_value} vs {c.proposed_value}" for c in report.conflicts)
    return "\n".join(lines)
