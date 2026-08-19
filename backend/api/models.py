from __future__ import annotations

from datetime import date as Date
from enum import Enum

from pydantic import BaseModel, Field


class VersionSummary(BaseModel):
    version_id: int
    download_id: int
    as_at_date: Date | None = None
    version_label: str = ""
    pdf_url: str = ""


class MatchedVersion(VersionSummary):
    chunk_id: int
    chunk_text: str


class GroupedSearchItem(BaseModel):
    key: str
    title: str
    chapter_number: str
    section_ref: str
    heading: str = ""
    matched_version: MatchedVersion
    latest_available: VersionSummary | None = None
    versions: list[VersionSummary]
    score: float


class GroupedSearchResponse(BaseModel):
    items: list[GroupedSearchItem]
    next_offset: int | None = None
    has_more: bool = False


class CitationStatus(str, Enum):
    found = "found"
    not_found = "not_found"
    ambiguous = "ambiguous"


class NormalizedCitationInput(BaseModel):
    chapter: str
    section: str
    date: Date | None = None


class CitationFormats(BaseModel):
    full: str
    short: str


class CitationAuthority(BaseModel):
    title: str
    chapter_number: str
    section_ref: str
    heading: str = ""
    as_at_date: Date | None = None
    version_label: str = ""
    download_id: int
    pdf_url: str


class CitationAlternative(BaseModel):
    title: str
    chapter_number: str
    section_ref: str = ""
    as_at_date: Date | None = None
    version_label: str = ""
    download_id: int | None = None


class CitationResolveResponse(BaseModel):
    status: CitationStatus
    normalized_input: NormalizedCitationInput
    citation: CitationFormats | None = None
    authority: CitationAuthority | None = None
    text: str = ""
    alternatives: list[CitationAlternative] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    mode: str = Field(default="research", pattern="^(research|precedent)$")


class ChatSource(BaseModel):
    id: str
    title: str = ""
    chapter: str = ""
    section: str = ""
    date: str = ""
    url: str = ""
    kind: str = "statute"


class ChatResponse(BaseModel):
    status: str = Field(pattern="^(ok|refused|error|unconfigured)$")
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)


class CaseSummary(BaseModel):
    id: str
    title: str = ""
    source: str = ""
    record_id: str = ""
    court: str = ""
    year: int | None = None
    url: str = ""



class CaseCitation(BaseModel):
    case_id: str
    chapter_number: str
    confidence: str = "medium"
    method: str = "REGEX"
    detail: str = ""


class CaseDetail(CaseSummary):
    citations: list[CaseCitation] = Field(default_factory=list)
    related_cases: list[CaseSummary] = Field(default_factory=list)
