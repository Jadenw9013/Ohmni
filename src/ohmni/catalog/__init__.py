"""Local part catalog.

Every fact in this catalog is a *claim*, not truth (risk R4 in
PRE_IMPLEMENTATION_REVIEW.md). Seed entries were hand-entered from manufacturer
datasheets, so their evidence is recorded as ``EvidenceKind.CATALOG`` with the
page noted -- not as ``DATASHEET``, which would require a verbatim snippet that
has been mechanically confirmed against the actual PDF.

That distinction is the whole point. Writing a "verbatim" snippet from memory
and labelling it datasheet-supported is exactly the fabricated citation this
product exists to prevent. Once spike S3 ingests the real PDFs, these claims
upgrade to DATASHEET_SUPPORTED with machine-verified citations, and the change
in status is visible to the user.
"""

from .loader import JsonPartCatalog, default_catalog

__all__ = ["JsonPartCatalog", "default_catalog"]
