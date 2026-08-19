from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api.agent import ChatAgent
from api.citations import format_citation, normalize_chapter, normalize_section
from api.models import (
    CaseDetail,
    CaseSummary,
    ChatRequest,
    ChatResponse,
    CitationResolveResponse,
    GroupedSearchResponse,
)
from scraper.db_pg import LawCitePGDB
from scraper.embed import _get_model

PG_DSN = os.environ.get(
    "PG_DSN", "postgresql://lawcite:changeme@localhost:5432/lawcite"
)
PDF_BASE = "https://laws.gov.tt/ttdll-web/revision/download"

# Local dev: backend/api/main.py -> repo root/templates (3 parents up).
# Container: /app/api/main.py -> /app/templates (2 parents up), templates
# copied alongside api/ and scraper/ by backend/Dockerfile.
_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "templates",
    Path(__file__).resolve().parent.parent / "templates",
]
TEMPLATES_DIR = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])

_db = LawCitePGDB(PG_DSN)
_model_loaded = False


def warm_model():
    global _model_loaded
    if not _model_loaded:
        _get_model()
        _model_loaded = True


def get_db() -> LawCitePGDB:
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    warm_model()
    await _db.connect()
    yield
    await _db.close()


def pdf_url(download_id: int | str) -> str:
    return f"{PDF_BASE}/{download_id}?type=act"


def enrich_row(r: dict) -> dict:
    r["pdf_url"] = pdf_url(r["download_id"]) if r.get("download_id") else ""
    return r


app = FastAPI(title="LawCite TT — Laws of Trinidad and Tobago", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"http://(?:localhost|127\.0\.0\.1)(:\d+)?|"
        r"https://law-cite-tt\.gjo-ai\.workers\.dev"
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    pool = await get_db().connect()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok"}


@app.get("/api/chapters")
async def list_chapters(q: str = "", limit: int = 200):
    pool = await get_db().connect()
    sql = "SELECT chapter_number, title FROM chapters"
    params: list = []
    if q:
        params.extend([f"%{q}%", f"%{q}%"])
        sql += " WHERE chapter_number ILIKE $1 OR title ILIKE $2"
    params.append(limit)
    sql += f" ORDER BY chapter_number LIMIT ${len(params)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [{"chapter": r["chapter_number"], "title": r["title"]} for r in rows]


@app.get("/api/lookup")
async def lookup_section(
    chapter: str = Query(..., description="Chapter number e.g. 8:08"),
    section: str = Query(..., description="Section reference e.g. 1, 3A"),
    date: str = Query("", description="As-at date e.g. 2016-12-31"),
    download_id: int | None = Query(None, description="Exact source download ID"),
):
    db = get_db()
    results = await db.lookup_section(
        chapter,
        section,
        as_at_date=date or None,
        download_id=download_id,
    )
    if not results and date and download_id is None:
        results = await db.lookup_section(chapter, section)
    return [enrich_row(r) for r in results]


@app.get("/api/search")
async def search(
    q: str = Query(..., description="Search query"),
    chapter: str = Query("", description="Filter by chapter number"),
    mode: str = Query("fts", description="Search mode: fts, vector, hybrid"),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_db()
    if mode == "fts":
        results = await db.search_fts(q, chapter=chapter, limit=limit)
    elif mode == "vector":
        results = await db.search_vector(q, chapter=chapter, limit=limit)
    else:
        results = await db.search_hybrid(q, chapter=chapter, limit=limit)
    return [enrich_row(r) for r in results]


@app.get("/api/search/grouped", response_model=GroupedSearchResponse)
async def search_grouped(
    q: str = Query(..., description="Search query"),
    chapter: str = Query("", description="Filter by chapter number"),
    mode: str = Query("fts", pattern="^(fts|hybrid|vector)$"),
    date: str = Query("", description="Only versions available by this date"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    payload = await get_db().search_grouped(
        q,
        mode=mode,
        chapter=chapter,
        as_at_date=date,
        limit=limit,
        offset=offset,
    )
    for item in payload["items"]:
        matched = item["matched_version"]
        matched["pdf_url"] = pdf_url(matched["download_id"])
        for version in item["versions"]:
            version["pdf_url"] = pdf_url(version["download_id"])
        if item["latest_available"]:
            item["latest_available"]["pdf_url"] = pdf_url(
                item["latest_available"]["download_id"]
            )
    return payload


@app.get("/api/citations/resolve", response_model=CitationResolveResponse)
async def resolve_citation(
    chapter: str = Query(..., min_length=1),
    section: str = Query(..., min_length=1),
    as_at_date: date | None = Query(None, alias="date"),
):
    try:
        normalized_chapter = normalize_chapter(chapter)
        normalized_section = normalize_section(section)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    result = await get_db().resolve_citation(
        normalized_chapter,
        normalized_section,
        as_at_date.isoformat() if as_at_date else None,
    )
    normalized_input = {
        "chapter": normalized_chapter,
        "section": normalized_section,
        "date": as_at_date,
    }
    if result["status"] != "found":
        return {
            "status": result["status"],
            "normalized_input": normalized_input,
            "alternatives": result["alternatives"],
        }

    authority = result["authority"]
    full, short = format_citation(
        authority["title"],
        normalized_chapter,
        normalized_section,
        as_at_date,
    )
    return {
        "status": "found",
        "normalized_input": normalized_input,
        "citation": {"full": full, "short": short},
        "authority": {
            "title": authority["title"],
            "chapter_number": authority["chapter_number"],
            "section_ref": authority["section_ref"],
            "heading": authority["heading"] or "",
            "as_at_date": authority["as_at_date"],
            "version_label": authority["version_label"] or "",
            "download_id": authority["download_id"],
            "pdf_url": pdf_url(authority["download_id"]),
        },
        "text": authority["chunk_text"],
        "alternatives": [],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    agent = ChatAgent(get_db())
    result = await agent.run(messages, mode=payload.mode)
    return ChatResponse(**result)


def _case_summary(row: dict) -> dict:
    return {
        "id": row["case_id"],
        "title": row.get("title") or "",
        "source": row.get("source") or "",
        "record_id": row.get("record_id") or "",
        "court": row.get("court") or "",
        "year": row.get("year"),
    }


@app.get("/api/cases", response_model=list[CaseSummary])
async def search_cases(
    q: str = Query(..., min_length=1, description="Search cases by title"),
    limit: int = Query(20, ge=1, le=100),
):
    rows = await get_db().search_cases(q, limit=limit)
    return [_case_summary(r) for r in rows]


@app.get("/api/cases/citing", response_model=list[CaseSummary])
async def cases_citing(
    chapter: str = Query(..., min_length=1, description="Chapter number e.g. 8:08"),
    limit: int = Query(20, ge=1, le=100),
):
    rows = await get_db().cases_citing_chapter(chapter, limit=limit)
    return [_case_summary(r) for r in rows]


@app.get("/api/cases/{case_id}", response_model=CaseDetail)
async def case_detail(case_id: str):
    db = get_db()
    case = await db.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Unknown case: {case_id}")

    citations = await db.case_citations_for(case_id)
    chapters = sorted({c["chapter_number"] for c in citations})
    related_rows = await db.cases_citing_chapters(
        chapters,
        exclude_case_id=case_id,
        limit=50,
    )
    return {
        **case,
        "id": case["id"],
        "title": case.get("title") or "",
        "source": case.get("source") or "",
        "record_id": case.get("record_id") or "",
        "court": case.get("court") or "",
        "year": case.get("year"),
        "citations": citations,
        "related_cases": [_case_summary(r) for r in related_rows],
    }


@app.get("/api/stats")
async def stats():
    pool = await get_db().connect()
    async with pool.acquire() as conn:
        ch = await conn.fetchval("SELECT COUNT(*) FROM chapters")
        ve = await conn.fetchval("SELECT COUNT(*) FROM versions")
        cn = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        em = await conn.fetchval(
            "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL"
        )
    return {
        "chapters": ch,
        "versions": ve,
        "chunks": cn,
        "embedded": em,
    }


@app.get("/", response_class=HTMLResponse)
def landing_page():
    return HTMLResponse((TEMPLATES_DIR / "index.html").read_text())
