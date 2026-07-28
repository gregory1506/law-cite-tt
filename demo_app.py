from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from scraper.db import LawCiteDB
from scraper.search import SearchEngine
from scraper.embed import embed_text, _get_model

DB_PATH = Path("/Volumes/Extreme SSD/law-cite-tt-data/law_cite.db")
PDF_BASE = "https://laws.gov.tt/ttdll-web/revision/download"

_db: LawCiteDB | None = None
_search: SearchEngine | None = None
_model_loaded: bool = False


def warm_model():
    global _model_loaded
    if not _model_loaded:
        _get_model()
        _model_loaded = True


def get_db() -> LawCiteDB:
    global _db
    if _db is None:
        _db = LawCiteDB(DB_PATH)
        _db.connect()
    return _db


def get_search() -> SearchEngine:
    global _search
    if _search is None:
        _search = SearchEngine(DB_PATH)
    return _search


def pdf_url(download_id: int | str) -> str:
    return f"{PDF_BASE}/{download_id}?type=act"


def enrich_row(r: dict) -> dict:
    r["pdf_url"] = pdf_url(r["download_id"]) if r.get("download_id") else ""
    return r


app = FastAPI(title="LawCite TT — Laws of Trinidad and Tobago")
warm_model()


@app.get("/api/chapters")
def list_chapters(q: str = "", limit: int = 200):
    db = get_db()
    conn = db.connect()
    sql = "SELECT chapter_number, title FROM chapters"
    params: list[str] = []
    if q:
        sql += " WHERE chapter_number LIKE ? OR title LIKE ?"
        params.extend([f"%{q}%", f"%{q}%"])
    sql += " ORDER BY chapter_number LIMIT ?"
    params.append(str(limit))
    rows = conn.execute(sql, params).fetchall()
    return [{"chapter": r["chapter_number"], "title": r["title"]} for r in rows]


@app.get("/api/lookup")
def lookup_section(
    chapter: str = Query(..., description="Chapter number e.g. 8:08"),
    section: str = Query(..., description="Section reference e.g. 1, 3A"),
    date: str = Query("", description="As-at date e.g. 2016-12-31"),
):
    db = get_db()
    results = db.lookup_section(chapter, section, as_at_date=date or None)
    if not results:
        results = db.lookup_section(chapter, section)
    return [enrich_row(r) for r in results]


@app.get("/api/search")
def search(
    q: str = Query(..., description="Search query"),
    chapter: str = Query("", description="Filter by chapter number"),
    mode: str = Query("fts", description="Search mode: fts, vector, hybrid"),
    limit: int = Query(20, ge=1, le=100),
):
    engine = get_search()
    if mode == "fts":
        results = engine.fts_search(q, chapter=chapter, limit=limit)
    elif mode == "vector":
        results = engine.vector_search(q, chapter=chapter, limit=limit)
    else:
        results = engine.hybrid_search(q, chapter=chapter, limit=limit)
    return [enrich_row(r) for r in results]


@app.get("/api/stats")
def stats():
    db = get_db()
    conn = db.connect()
    ch = conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    ve = conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
    cn = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    em = conn.execute(
        "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL"
    ).fetchone()[0]
    return {
        "chapters": ch,
        "versions": ve,
        "chunks": cn,
        "embedded": em,
    }


@app.get("/", response_class=HTMLResponse)
def landing_page():
    return HTMLResponse(
        (Path(__file__).parent / "templates" / "index.html").read_text()
    )
