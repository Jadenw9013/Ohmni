"""Pure, serializable document identity and location types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence import DocumentRef


class DocumentFingerprint(BaseModel):
    model_config = ConfigDict(frozen=True)
    algorithm: str = "sha256"
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DocumentRegion(BaseModel):
    model_config = ConfigDict(frozen=True)
    x0: float
    y0: float
    x1: float
    y1: float


class DocumentSpan(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    region: DocumentRegion | None = None

    @model_validator(mode="after")
    def _ordered(self) -> DocumentSpan:
        if self.end <= self.start:
            raise ValueError("span end must be greater than start")
        return self


class DocumentPage(BaseModel):
    number: int = Field(ge=1)
    text: str
    spans: list[DocumentSpan] = Field(default_factory=list)


class DatasheetIdentity(BaseModel):
    manufacturer: str | None = None
    detected_parts: list[str] = Field(default_factory=list)
    revision: str | None = None
    date: str | None = None
    ambiguous: bool = False


class DocumentMetadata(BaseModel):
    document_id: str
    fingerprint: DocumentFingerprint
    title: str | None = None
    page_count: int = Field(ge=1)
    identity: DatasheetIdentity = Field(default_factory=DatasheetIdentity)

    def as_ref(self) -> DocumentRef:
        part = self.identity.detected_parts[0] if len(self.identity.detected_parts) == 1 else None
        return DocumentRef(
            document_id=self.document_id,
            title=self.title,
            manufacturer=self.identity.manufacturer,
            part_number=part,
            revision=self.identity.revision,
            sha256=self.fingerprint.digest,
        )


class DatasheetDocument(BaseModel):
    metadata: DocumentMetadata
    pages: list[DocumentPage]

    def page(self, number: int) -> DocumentPage | None:
        return next((page for page in self.pages if page.number == number), None)
