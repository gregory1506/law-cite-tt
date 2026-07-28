from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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
    allow_origins=["http://localhost:5173"],
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
):
    db = get_db()
    results = await db.lookup_section(chapter, section, as_at_date=date or None)
    if not results:
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
