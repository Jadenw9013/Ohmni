"""Provenance model.

Three concepts that the specification documents conflated (see
PRE_IMPLEMENTATION_REVIEW.md 3.1) are kept strictly separate here:

* :class:`EvidenceKind` -- where a fact physically came from.
* :class:`ClaimStatus`  -- how strongly a single claim is supported. **Derived**
  from the evidence attached to it; never settable on its own.
* :class:`SubsystemStatus` -- the roll-up label a subsystem carries in a report.

The derivation is the point. Nothing in this system -- including a language
model -- can assert that a value is "datasheet supported". It can only attach a
datasheet ``Evidence`` carrying a document id, a page number and a verbatim
snippet, and the status then follows mechanically.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .units import Quantity


class EvidenceKind(StrEnum):
    """Where a fact came from."""

    DATASHEET = "datasheet"
    CALCULATION = "calculation"
    SIMULATION = "simulation"
    ERC = "erc"
    DRC = "drc"
    BENCH = "bench"
    HUMAN = "human"
    CATALOG = "catalog"
    ASSUMPTION = "assumption"


class ClaimStatus(StrEnum):
    """How strongly a single claim is supported."""

    UNKNOWN = "UNKNOWN"
    ASSUMED = "ASSUMED"
    CATALOG_REPORTED = "CATALOG_REPORTED"
    CALCULATED = "CALCULATED"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    DATASHEET_SUPPORTED = "DATASHEET_SUPPORTED"
    SIMULATED = "SIMULATED"
    ERC_VERIFIED = "ERC_VERIFIED"
    DRC_VERIFIED = "DRC_VERIFIED"
    BENCH_VERIFIED = "BENCH_VERIFIED"


# Ordering used to pick the strongest evidence backing a claim, and to roll up
# a subsystem status. It is a display and selection ordering, not a claim that
# one kind of evidence is universally superior to another: a SPICE result and a
# datasheet limit answer different questions. A rule is free to consult
# whichever evidence it needs regardless of rank.
#
# The ordering runs from "nobody checked" to "we measured the physical board".
_STATUS_RANK: dict[ClaimStatus, int] = {
    ClaimStatus.UNKNOWN: 0,
    ClaimStatus.ASSUMED: 1,
    ClaimStatus.CATALOG_REPORTED: 2,
    ClaimStatus.CALCULATED: 3,
    ClaimStatus.HUMAN_CONFIRMED: 4,
    ClaimStatus.DATASHEET_SUPPORTED: 5,
    ClaimStatus.SIMULATED: 6,
    ClaimStatus.ERC_VERIFIED: 7,
    ClaimStatus.DRC_VERIFIED: 7,
    ClaimStatus.BENCH_VERIFIED: 8,
}

_KIND_TO_STATUS: dict[EvidenceKind, ClaimStatus] = {
    EvidenceKind.DATASHEET: ClaimStatus.DATASHEET_SUPPORTED,
    EvidenceKind.CALCULATION: ClaimStatus.CALCULATED,
    EvidenceKind.SIMULATION: ClaimStatus.SIMULATED,
    EvidenceKind.ERC: ClaimStatus.ERC_VERIFIED,
    EvidenceKind.DRC: ClaimStatus.DRC_VERIFIED,
    EvidenceKind.BENCH: ClaimStatus.BENCH_VERIFIED,
    EvidenceKind.HUMAN: ClaimStatus.HUMAN_CONFIRMED,
    EvidenceKind.CATALOG: ClaimStatus.CATALOG_REPORTED,
    EvidenceKind.ASSUMPTION: ClaimStatus.ASSUMED,
}


def status_rank(status: ClaimStatus) -> int:
    return _STATUS_RANK[status]


class SubsystemStatus(StrEnum):
    """Roll-up label for a subsystem, per VERIFICATION.md."""

    VERIFIED = "VERIFIED"
    SIMULATED = "SIMULATED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    ASSUMED = "ASSUMED"
    NOT_VERIFIED = "NOT_VERIFIED"
    UNSUPPORTED = "UNSUPPORTED"


class DocumentRef(BaseModel):
    """Identifies a source document. Datasheet revisions matter; keep them."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    revision: str | None = None
    url: str | None = None
    sha256: str | None = None


class Evidence(BaseModel):
    """One piece of support for one fact.

    Field requirements are enforced per kind, because an "evidence" record that
    does not say where it came from is decoration rather than provenance.
    """

    model_config = ConfigDict(frozen=True)

    kind: EvidenceKind
    label: str = Field(description="What fact this supports, in plain language.")

    # Where it came from. Which of these are required depends on `kind`.
    source_id: str | None = Field(
        default=None,
        description="Document id, simulation run id, ERC run id, or catalog record id.",
    )
    document: DocumentRef | None = None
    page: int | None = Field(default=None, ge=1)
    snippet: str | None = Field(
        default=None, description="Verbatim text from the source, for re-verification."
    )
    snippet_verified: bool | None = Field(
        default=None,
        description=(
            "True if the snippet was mechanically confirmed to occur on the cited page. "
            "None means nobody has checked yet (e.g. a hand-authored catalog entry). "
            "False means the check ran and failed, which downgrades the claim to UNKNOWN."
        ),
    )

    # What it says.
    quantity: Quantity | None = None
    text_value: str | None = None
    detail: str | None = Field(
        default=None,
        description="For calculations, the formula and inputs. For runs, the parameters.",
    )

    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _require_provenance_for_kind(self) -> Evidence:
        if self.kind is EvidenceKind.DATASHEET:
            missing = [
                name
                for name, present in (
                    ("source_id or document", bool(self.source_id or self.document)),
                    ("page", self.page is not None),
                    ("snippet", bool(self.snippet)),
                )
                if not present
            ]
            if missing:
                raise ValueError(
                    "datasheet evidence requires " + ", ".join(missing) + "; "
                    "an uncited datasheet claim is not datasheet-supported"
                )
        elif self.kind is EvidenceKind.CALCULATION:
            if not self.detail:
                raise ValueError(
                    "calculation evidence requires `detail` showing the formula and inputs"
                )
        elif self.kind in (EvidenceKind.SIMULATION, EvidenceKind.ERC, EvidenceKind.DRC):
            if not self.source_id:
                raise ValueError(f"{self.kind.value} evidence requires a run id in `source_id`")
        elif self.kind is EvidenceKind.BENCH:
            if not self.source_id or self.quantity is None:
                raise ValueError(
                    "bench evidence requires a measurement id and a measured quantity"
                )
        return self

    @property
    def status(self) -> ClaimStatus:
        """The claim status this evidence confers. Derived, never stored."""
        if self.kind is EvidenceKind.DATASHEET and self.snippet_verified is False:
            # The citation was checked against the document and did not hold up.
            # A failed citation supports nothing.
            return ClaimStatus.UNKNOWN
        return _KIND_TO_STATUS[self.kind]

    @property
    def provenance_machine_verified(self) -> bool:
        """True only when the citation itself was mechanically confirmed."""
        return self.kind is EvidenceKind.DATASHEET and self.snippet_verified is True

    def describe(self) -> str:
        parts = [self.label]
        if self.quantity is not None:
            parts.append(f"= {self.quantity.engineering()}")
        elif self.text_value:
            parts.append(f"= {self.text_value}")
        where = self.document.part_number if self.document else self.source_id
        if where and self.page is not None:
            parts.append(f"[{where} p.{self.page}]")
        elif where:
            parts.append(f"[{where}]")
        if self.detail:
            parts.append(f"({self.detail})")
        return " ".join(parts)


def datasheet_evidence(
    label: str,
    *,
    document: DocumentRef,
    page: int,
    snippet: str,
    quantity: Quantity | None = None,
    text_value: str | None = None,
) -> Evidence:
    """Convenience constructor that makes the required citation fields obvious."""
    return Evidence(
        kind=EvidenceKind.DATASHEET,
        label=label,
        document=document,
        source_id=document.document_id,
        page=page,
        snippet=snippet,
        quantity=quantity,
        text_value=text_value,
    )


def calculated_evidence(
    label: str, *, detail: str, quantity: Quantity | None = None, text_value: str | None = None
) -> Evidence:
    """Convenience constructor. `detail` must show the working."""
    return Evidence(
        kind=EvidenceKind.CALCULATION,
        label=label,
        detail=detail,
        quantity=quantity,
        text_value=text_value,
    )


def catalog_evidence(
    label: str,
    *,
    document: DocumentRef,
    page: int | None = None,
    quantity: Quantity | None = None,
    text_value: str | None = None,
    detail: str | None = None,
) -> Evidence:
    """A fact entered into our catalog by a human from a manufacturer document.

    Deliberately *not* ``datasheet_evidence``. That constructor demands a
    verbatim snippet, and a snippet written from memory rather than copied from
    the document is a fabricated citation -- the precise failure mode this
    product exists to prevent. A catalog record names the document and the page
    so a human can check it, and ranks below a machine-verified citation until
    the PDF is actually ingested.
    """
    return Evidence(
        kind=EvidenceKind.CATALOG,
        label=label,
        document=document,
        source_id=document.document_id,
        page=page,
        quantity=quantity,
        text_value=text_value,
        detail=detail
        or (
            "Hand-entered from the manufacturer datasheet; page recorded for review. "
            "The verbatim snippet has not been captured and the citation has not been "
            "machine-verified."
        ),
    )


def assumed_evidence(label: str, *, detail: str, quantity: Quantity | None = None) -> Evidence:
    """An explicit assumption. Honest, and ranked accordingly."""
    return Evidence(
        kind=EvidenceKind.ASSUMPTION, label=label, detail=detail, quantity=quantity
    )


class Claim(BaseModel):
    """A value together with everything that supports it."""

    subject: str = Field(description='What this claim is about, e.g. "U3 VDD operating range".')
    quantity: Quantity | None = None
    text: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)

    @property
    def status(self) -> ClaimStatus:
        """The strongest status among the attached evidence.

        With no evidence the answer is UNKNOWN. That is a valid, successful
        result -- not a failure to be papered over with a confidence score.
        """
        if not self.evidence:
            return ClaimStatus.UNKNOWN
        return max((e.status for e in self.evidence), key=status_rank)

    @property
    def is_supported(self) -> bool:
        return status_rank(self.status) >= status_rank(ClaimStatus.CALCULATED)

    def strongest_evidence(self) -> Evidence | None:
        if not self.evidence:
            return None
        return max(self.evidence, key=lambda e: status_rank(e.status))
