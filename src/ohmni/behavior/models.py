"""Data contracts for the component behavior research corpus.

These models describe evidence and authored behavior. They do not execute a
simulator or convert a research claim into a verified electrical fact.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BehaviorFidelity(StrEnum):
    """The only fidelity labels accepted by the behavior specification."""

    IDEAL_COMPONENTS = "ideal_components"
    BEHAVIOURAL_APPROXIMATION = "behavioural_approximation"
    VENDOR_MODEL = "vendor_model"


class BehaviorLayer(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class BehaviorStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    RESEARCH_REQUIRED = "research_required"


class SimulationDisposition(StrEnum):
    SIMULABLE = "simulable"
    NOT_SIMULABLE = "not_simulable"


class SourceAnchor(BaseModel):
    """A reproducible pointer to a local source input."""

    model_config = ConfigDict(frozen=True)

    document: str
    line: int = Field(ge=1)
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fragment_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class EvidenceCitation(BaseModel):
    """A cited external document; source status stays explicit."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    manufacturer: str | None = None
    revision: str | None = None
    page: int | None = Field(default=None, ge=1)
    url: str | None = None
    source_status: str
    note: str | None = None


class BenchReference(BaseModel):
    """An imported benchmark record, never evidence of a new local run."""

    model_config = ConfigDict(frozen=True)

    bench_id: str
    file: str
    expected: Any = None
    measured_in_ngspice: Any = None
    ngspice_version: str | None = None
    run_provenance: str = "imported_research_record"


class BehaviorClassRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    behavior_id: str = Field(pattern=r"^BEH-[A-Z0-9-]+$")
    applies_to: list[str]
    layer: BehaviorLayer
    category: str
    fidelity: BehaviorFidelity
    status: BehaviorStatus
    basis_values: list[str]
    source_refs: Any
    source: SourceAnchor
    benches: list[BenchReference]
    canonical_payload: dict[str, Any]


class PackagePinOrder(BaseModel):
    """A role-preserving permutation from catalog pins to package terminals."""

    model_config = ConfigDict(frozen=True)

    package_name: str
    catalog_pin_roles: dict[str, str]
    package_terminal_roles: dict[str, str]
    catalog_to_package_terminal: dict[str, str]
    catalog_to_footprint_pad: dict[str, str]
    citation: EvidenceCitation

    @model_validator(mode="after")
    def _require_complete_role_preserving_permutation(self) -> PackagePinOrder:
        catalog_pins = set(self.catalog_pin_roles)
        if set(self.catalog_to_package_terminal) != catalog_pins:
            raise ValueError("terminal permutation must map every catalog pin exactly once")
        terminals = list(self.catalog_to_package_terminal.values())
        if len(terminals) != len(set(terminals)):
            raise ValueError("terminal permutation targets must be unique")
        if set(terminals) != set(self.package_terminal_roles):
            raise ValueError("terminal permutation must cover every package terminal")
        for pin, terminal in self.catalog_to_package_terminal.items():
            if self.catalog_pin_roles[pin] != self.package_terminal_roles[terminal]:
                raise ValueError(
                    f"catalog pin {pin} role {self.catalog_pin_roles[pin]!r} does not match "
                    f"package terminal {terminal} role {self.package_terminal_roles[terminal]!r}"
                )
        if set(self.catalog_to_footprint_pad) != catalog_pins:
            raise ValueError("footprint permutation must map every catalog pin exactly once")
        pads = list(self.catalog_to_footprint_pad.values())
        if len(pads) != len(set(pads)):
            raise ValueError("footprint permutation targets must be unique")
        return self

    def terminal_order(self) -> list[str]:
        """Return package roles in numeric terminal order for focused tests and UI."""
        return [self.package_terminal_roles[key] for key in sorted(self.package_terminal_roles, key=int)]


class CatalogPartBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    part_id: str
    entry_ids: list[str] = Field(default_factory=list)
    package_pin_orders: list[PackagePinOrder]
    source: SourceAnchor
    rationale: str

    @model_validator(mode="after")
    def _unique_packages(self) -> CatalogPartBinding:
        names = [item.package_name for item in self.package_pin_orders]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate package pin orders for {self.part_id}")
        return self

    def package(self, name: str) -> PackagePinOrder:
        for package in self.package_pin_orders:
            if package.package_name == name:
                return package
        raise KeyError(f"{self.part_id} has no package pin order {name!r}")


class ResearchFact(BaseModel):
    """One re-derived field; a citation is provenance, not blanket verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: str
    value: Any
    basis: Literal["STANDARD", "MFR_DATASHEET", "CONSENSUS", "DERIVED", "ASSUMPTION", "RESEARCH_REQUIRED"]
    confidence: Literal["H", "M", "L"]
    sources: list[str] = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    source_locator: str | None = Field(default=None, min_length=1, exclude_if=lambda v: v is None)
    scope: str
    unit: str | None = None
    detail: str | None = None

    @model_validator(mode="after")
    def _require_source_location(self) -> ResearchFact:
        if self.page is None and not (self.source_locator or "").strip():
            raise ValueError("research requires a page or explicit non-paginated source locator")
        return self


class EntryResearch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    entry_id: str = Field(pattern=r"^OHM-\d{3}$")
    researched_at: str
    research_result: Literal["sources_reviewed", "unresolved"]
    field_updates: list[ResearchFact]
    documents: list[EvidenceCitation]
    remaining_open_items: list[str]
    conflicts: list[str] = Field(default_factory=list)
    simulation_blockers: list[str] = Field(default_factory=list)
    bench_results: list[str] = Field(default_factory=list)
    bench_result: str | None = None
    source: SourceAnchor


class BehaviorEntryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    entry_id: str = Field(pattern=r"^OHM-\d{3}$")
    component: str
    behavior_class_ids: list[str]
    layer: BehaviorLayer
    fidelity: BehaviorFidelity
    status: BehaviorStatus
    group: str
    simulation_disposition: SimulationDisposition
    simulation_reason: str
    class_record_paths: list[str]
    catalog_binding_ids: list[str] = Field(default_factory=list)
    resolution_ids: list[str] = Field(default_factory=list)
    source: SourceAnchor
    research: EntryResearch | None = None


class ResolutionKind(StrEnum):
    LABEL = "label"
    PERMUTATION = "permutation"
    BLOCKER = "blocker"
    POLICY = "policy"


class Stage1Resolution(BaseModel):
    """Auditable handling of a Stage 0 mismatch without rewriting source research."""

    model_config = ConfigDict(frozen=True)

    resolution_id: str
    kind: ResolutionKind
    entry_ids: list[str]
    subject: str
    action: str
    data: dict[str, Any] = Field(default_factory=dict)
    changes_electrical_truth: bool
    gate_required: bool
    source: SourceAnchor


class SourceConsistencyIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    entry_id: str | None = None
    behavior_id: str | None = None
    detail: str
    resolution: str


class BehaviorManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    generator: str
    source_spec: SourceAnchor
    entry_count: int
    class_count: int
    binding_count: int
    status_counts: dict[str, int]
    fidelity_counts: dict[str, int]
    bench_reference_count: int
    bench_execution: str
    source_consistency_issues: list[SourceConsistencyIssue]
    unbound_reference_classes: list[str]
    resolutions: list[Stage1Resolution]
