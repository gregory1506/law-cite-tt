from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class VersionSummary(BaseModel):
    version_id: int
    download_id: int
    as_at_date: date | None = None
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
