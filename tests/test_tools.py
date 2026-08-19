from datetime import date
from types import SimpleNamespace

import pytest

from api.tools import (
    HANDLERS,
    _citing_cases,
    _expand_case,
    _list_chapters,
    _lookup_section,
    _resolve_citation,
    _search_cases,
    _search_provisions,
    pdf_url,
)


class FakeConn:
    def __init__(self, rows):
        self.rows = rows

    async def fetch(self, sql, *params):
        return self.rows


class FakePool:
    def __init__(self, rows):
        self.rows = rows

    def acquire(self):
        return _Acquire(self.rows)


class _Acquire:
    def __init__(self, rows):
        self.rows = rows

    async def __aenter__(self):
        return FakeConn(self.rows)

    async def __aexit__(self, *exc):
        return False


def _chapters(rows):
    async def connect():
        return _fake_pool(rows)

    return SimpleNamespace(connect=connect)


def _fake_pool(rows):
    return FakePool(rows)


def _found_citation():
    return {
        "status": "found",
        "authority": {
            "title": "Absconding Debtors",
            "chapter_number": "8:08",
            "section_ref": "4",
            "heading": "Power to arrest",
            "chunk_text": "A debtor may be arrested in the prescribed case.",
            "chunk_index": 0,
            "chunk_id": 42,
            "version_id": 1,
            "download_id": 105522,
            "as_at_date": date(2009, 12, 31),
            "version_label": "2009 revision",
        },
        "alternatives": [],
    }


class FakeDB:
    def __init__(
        self,
        grouped=None,
        lookup=None,
        citation=None,
        chapters=None,
        citing=None,
        cases=None,
        case=None,
        citations_for=None,
        related=None,
    ):
        self.grouped = grouped
        self.lookup = lookup
        self.citation = citation
        self.chapters = chapters
        self.citing = citing
        self.cases = cases
        self.case = case
        self.citations_for = citations_for
        self.related = related

    async def search_grouped(self, query, **kwargs):
        return self.grouped

    async def lookup_section(self, chapter, section, as_at_date=None, **kwargs):
        return self.lookup

    async def resolve_citation(self, chapter, section, as_at_date=None):
        return self.citation

    async def connect(self):
        return FakePool(self.chapters)

    async def cases_citing_chapter(self, chapter, limit=20):
        return self.citing or []

    async def search_cases(self, query, limit=20):
        return self.cases or []

    async def get_case(self, case_id):
        return self.case

    async def case_citations_for(self, case_id):
        return self.citations_for or []

    async def cases_citing_chapters(self, chapter_numbers, exclude_case_id="", limit=20):
        return self.related or []


def _grouped_payload():
    return {
        "items": [
            {
                "key": "8:08::4",
                "title": "Absconding Debtors",
                "chapter_number": "8:08",
                "section_ref": "4",
                "heading": "Power to arrest",
                "matched_version": {
                    "version_id": 1,
                    "download_id": 105522,
                    "as_at_date": date(2009, 12, 31),
                    "version_label": "2009 revision",
                    "chunk_id": 7,
                    "chunk_text": "A debtor may be arrested in the prescribed case.",
                },
                "latest_available": None,
                "versions": [],
                "score": 1.0,
            }
        ],
        "has_more": False,
        "next_offset": None,
    }


@pytest.mark.asyncio
async def test_search_provisions_returns_text_and_sources():
    result = await _search_provisions(
        FakeDB(grouped=_grouped_payload()), query="absconding"
    )
    assert "Absconding Debtors" in result["text"]
    assert "Official PDF" in result["text"]
    assert result["sources"][0]["id"] == "chunk:7"
    assert result["sources"][0]["url"].startswith("https://laws.gov.tt")


@pytest.mark.asyncio
async def test_search_provisions_empty_results():
    result = await _search_provisions(FakeDB(grouped={"items": []}), query="zzz")
    assert result["sources"] == []
    assert "No provisions matched" in result["text"]


@pytest.mark.asyncio
async def test_lookup_section_returns_rows():
    rows = [
        {
            "chunk_text": "A debtor may be arrested in the prescribed case.",
            "chapter_number": "8:08",
            "section_ref": "4",
            "heading": "Power to arrest",
            "as_at_date": date(2009, 12, 31),
            "version_label": "2009 revision",
            "download_id": 105522,
        }
    ]
    result = await _lookup_section(FakeDB(lookup=rows), chapter="8:08", section="4")
    assert "s. 4" in result["text"]
    assert result["sources"][0]["id"].startswith("lookup:105522:")


@pytest.mark.asyncio
async def test_lookup_section_empty():
    result = await _lookup_section(FakeDB(lookup=[]), chapter="8:08", section="99")
    assert "No source text found" in result["text"]
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_resolve_citation_found_formats_citation():
    result = await _resolve_citation(
        FakeDB(citation=_found_citation()),
        chapter="Chap. 8:08",
        section="s. 4",
    )
    assert "FOUND" in result["text"]
    assert "Chap. 8:08, s. 4" in result["text"]
    assert result["sources"][0]["id"] == "chunk:42"


@pytest.mark.asyncio
async def test_resolve_citation_not_found_lists_alternatives():
    citation = {
        "status": "not_found",
        "authority": None,
        "alternatives": [
            {
                "title": "Absconding Debtors",
                "chapter_number": "8:08",
                "section_ref": "",
                "as_at_date": None,
                "version_label": "",
                "download_id": None,
            }
        ],
    }
    result = await _resolve_citation(
        FakeDB(citation=citation), chapter="8:08", section="999"
    )
    assert "not_found" in result["text"]
    assert "Absconding Debtors" in result["text"]
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_resolve_citation_invalid_input():
    result = await _resolve_citation(
        FakeDB(citation=_found_citation()), chapter="not-a-chapter", section="4"
    )
    assert "Invalid citation reference" in result["text"]


@pytest.mark.asyncio
async def test_list_chapters():
    rows = [
        {"chapter_number": "8:08", "title": "Absconding Debtors"},
        {"chapter_number": "1:01", "title": "Constitution"},
    ]
    db = _chapters(rows)
    result = await _list_chapters(db, query="absconding")
    assert "Absconding Debtors" in result["text"]
    assert {s["id"] for s in result["sources"]} == {"chapter:8:08", "chapter:1:01"}


def test_pdf_url_format():
    assert pdf_url(105522) == (
        "https://laws.gov.tt/ttdll-web/revision/download/105522?type=act"
    )


def test_all_handlers_are_async_and_registered():
    names = set(HANDLERS)
    assert names == {
        "search_provisions",
        "lookup_section",
        "resolve_citation",
        "list_chapters",
        "citing_cases",
        "search_cases",
        "expand_case",
    }


@pytest.mark.asyncio
async def test_citing_cases_lists_cases_with_source_ids():
    db = FakeDB(
        citing=[
            {
                "case_id": "case:8eec828c74db14ee",
                "chapter_number": "8:08",
                "confidence": "high",
                "method": "REGEX",
                "detail": "Ch. 8:08",
                "title": "Smith v Jones",
            }
        ]
    )
    result = await _citing_cases(db, chapter="Chap. 8:08")
    assert "Smith v Jones" in result["text"]
    assert "cites Chap. 8:08" in result["text"]
    assert result["sources"][0]["id"] == "case:8eec828c74db14ee"
    assert result["sources"][0]["kind"] == "case"


@pytest.mark.asyncio
async def test_citing_cases_invalid_chapter():
    result = await _citing_cases(FakeDB(), chapter="not-a-chapter")
    assert "Invalid chapter reference" in result["text"]
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_search_cases_matches_names():
    db = FakeDB(
        cases=[
            {
                "id": "case:0ee59724f387f344",
                "title": "Jones v Ministry of Finance",
                "source": "webopac",
                "record_id": "0ee59724f387f344",
                "court": "",
                "year": 2015,
            }
        ]
    )
    result = await _search_cases(db, query="jones")
    assert "Jones v Ministry of Finance" in result["text"]
    assert "2015" in result["text"]
    assert result["sources"][0]["id"] == "case:0ee59724f387f344"


@pytest.mark.asyncio
async def test_expand_case_builds_precedent_chain():
    db = FakeDB(
        case={
            "id": "case:8eec828c74db14ee",
            "title": "Smith v Jones",
            "source": "webopac",
            "record_id": "8eec828c74db14ee",
            "court": "",
            "year": None,
        },
        citations_for=[
            {
                "case_id": "case:8eec828c74db14ee",
                "chapter_number": "8:08",
                "confidence": "high",
                "method": "REGEX",
                "detail": "Ch. 8:08",
            }
        ],
        related=[
            {
                "case_id": "case:838382c6b1196fd6",
                "chapter_number": "8:08",
                "confidence": "medium",
                "method": "REGEX",
                "detail": "Ch. 8:08",
                "title": "Brown v State",
            }
        ],
    )
    result = await _expand_case(db, case_id="8eec828c74db14ee")
    assert "Smith v Jones" in result["text"]
    assert "Chap. 8:08" in result["text"]
    assert "Brown v State" in result["text"]
    ids = {s["id"] for s in result["sources"]}
    assert ids == {
        "case:8eec828c74db14ee",
        "case:838382c6b1196fd6",
    }


@pytest.mark.asyncio
async def test_expand_case_unknown_id():
    result = await _expand_case(FakeDB(), case_id="case:deadbeef")
    assert "No such case" in result["text"]
    assert result["sources"] == []