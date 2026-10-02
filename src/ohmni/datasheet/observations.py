"""Immutable, pure observations of one source document.

An observation is what the *parser* saw, recorded before any model is asked
anything and never rewritten afterwards. Two properties make the later source
checks meaningful:

* **Stable identity.** Every token and vector feature has an ID derived from its
  page and its position in a deterministic ordering, so a receipt can name the
  exact glyphs a check read. :attr:`DocumentObservationBundle.observation_digest`
  covers all of it, which is what makes "this receipt checked different
  observations" a detectable condition rather than an assumption.
* **No interpretation.** Tokens carry text and geometry; rectangles carry
  geometry. Nothing here decides what a table is, which column a number sits in,
  or what a drawing means. That is :mod:`ohmni.datasheet.constraint_verifier`'s
  job, and it works only from this data.

Rendered pages are recorded by digest and transform, not by pixels: the image a
vision provider sees must be reconstructible and locatable in PDF coordinates,
but a bundle that carried megabytes of PNG would be unusable as a receipt input.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ..domain.component_synthesis import Sha256, SourceRegion

#: Bounds. A page with more tokens than this is not silently truncated; the
#: builder raises, because a quietly clipped page would make "the constraint is
#: not in the source" indistinguishable from "we stopped reading".
MAX_TOKENS_PER_PAGE = 4000
MAX_RECTANGLES_PER_PAGE = 2000
MAX_RULES_PER_PAGE = 4000
MAX_OBSERVED_PAGES = 64

TokenId = Annotated[str, StringConstraints(pattern=r"^p\d+t\d+$")]
FeatureId = Annotated[str, StringConstraints(pattern=r"^p\d+v\d+$")]
RuleId = Annotated[str, StringConstraints(pattern=r"^p\d+r\d+$")]


class TextToken(BaseModel):
    """One whitespace-delimited word with its PDF-user-space rectangle."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    token_id: TokenId
    text: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    region: SourceRegion

    @property
    def x_centre(self) -> float:
        return (self.region.x0 + self.region.x1) / 2

    @property
    def y_centre(self) -> float:
        return (self.region.y0 + self.region.y1) / 2


class VectorRectangle(BaseModel):
    """One axis-aligned rectangle drawn on the page.

    Used for drawing topology -- which pad is where relative to which -- never
    for dimensions. A mechanical drawing may be explicitly not to scale.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    feature_id: FeatureId
    region: SourceRegion
    stroked: bool
    filled: bool


class VectorRule(BaseModel):
    """One axis-aligned printed rule: a table border or a leader line.

    Table grammars are built on these rather than on whitespace. A printed
    column boundary is what the document actually says about which column a
    number is in; an inter-word gap is a guess, and a guess is how a value from
    the neighbouring column becomes evidence.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    rule_id: RuleId
    orientation: Literal["horizontal", "vertical"]
    position: float = Field(ge=-20000, le=20000)
    start: float = Field(ge=-20000, le=20000)
    end: float = Field(ge=-20000, le=20000)
    thickness: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _ordered(self) -> VectorRule:
        if self.end <= self.start:
            raise ValueError("a rule must have positive extent")
        return self

    def spans(self, low: float, high: float, *, tolerance: float = 0.0) -> bool:
        """True when this rule covers the whole interval along its own axis."""
        return self.start <= low + tolerance and self.end >= high - tolerance

    def covers_position(self, value: float, *, tolerance: float = 0.0) -> bool:
        return self.start - tolerance <= value <= self.end + tolerance


class PageRender(BaseModel):
    """A locally rendered raster of one page, recorded by digest and transform."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    dpi: int = Field(ge=36, le=600)
    width_px: int = Field(ge=1, le=20000)
    height_px: int = Field(ge=1, le=20000)
    image_digest: Sha256
    media_type: Annotated[str, StringConstraints(pattern=r"^image/png$")] = "image/png"

    @property
    def scale(self) -> float:
        """Pixels per PDF point, the transform a provider region must invert."""
        return self.dpi / 72.0


class PageObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    number: int = Field(ge=1, le=2000)
    width_pt: float = Field(gt=0, le=20000)
    height_pt: float = Field(gt=0, le=20000)
    rotation: int = Field(ge=0, le=270)
    tokens: tuple[TextToken, ...] = Field(default=(), max_length=MAX_TOKENS_PER_PAGE)
    rectangles: tuple[VectorRectangle, ...] = Field(default=(), max_length=MAX_RECTANGLES_PER_PAGE)
    rules: tuple[VectorRule, ...] = Field(default=(), max_length=MAX_RULES_PER_PAGE)
    render: PageRender | None = None

    @model_validator(mode="after")
    def _identifiers_belong_to_this_page(self) -> PageObservation:
        if self.rotation % 90:
            raise ValueError("page rotation must be a quarter turn")
        prefix = f"p{self.number}t"
        for index, token in enumerate(self.tokens):
            if token.token_id != f"{prefix}{index}":
                raise ValueError(f"token IDs must be page-ordered; got {token.token_id!r}")
        prefix = f"p{self.number}v"
        for index, rectangle in enumerate(self.rectangles):
            if rectangle.feature_id != f"{prefix}{index}":
                raise ValueError(f"feature IDs must be page-ordered; got {rectangle.feature_id!r}")
        prefix = f"p{self.number}r"
        for index, rule in enumerate(self.rules):
            if rule.rule_id != f"{prefix}{index}":
                raise ValueError(f"rule IDs must be page-ordered; got {rule.rule_id!r}")
        return self

    def token(self, token_id: str) -> TextToken | None:
        return next((item for item in self.tokens if item.token_id == token_id), None)

    def text(self) -> str:
        return " ".join(token.text for token in self.tokens)


class DocumentObservationBundle(BaseModel):
    """Everything observed about one exact document, with its own digest."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    document_digest: Sha256
    parser: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    parser_version: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    renderer: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    renderer_version: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    page_count: int = Field(ge=1, le=2000)
    pages: tuple[PageObservation, ...] = Field(min_length=1, max_length=MAX_OBSERVED_PAGES)

    @model_validator(mode="after")
    def _pages_are_ordered_and_in_range(self) -> DocumentObservationBundle:
        numbers = [page.number for page in self.pages]
        if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
            raise ValueError("observed pages must be unique and ascending")
        if numbers[-1] > self.page_count:
            raise ValueError("observed page number exceeds the document page count")
        return self

    def page(self, number: int) -> PageObservation | None:
        return next((item for item in self.pages if item.number == number), None)

    @property
    def observation_digest(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ObservationLimitError(ValueError):
    """A page exceeded a configured observation bound. No partial page is kept."""


__all__ = [
    "MAX_OBSERVED_PAGES",
    "MAX_RECTANGLES_PER_PAGE",
    "MAX_RULES_PER_PAGE",
    "MAX_TOKENS_PER_PAGE",
    "DocumentObservationBundle",
    "ObservationLimitError",
    "PageObservation",
    "PageRender",
    "TextToken",
    "VectorRectangle",
    "VectorRule",
]
