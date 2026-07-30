import os
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault(
    "PG_DSN", "postgresql://lawcite:changeme@localhost:5432/lawcite_test"
)

from api.main import app  # noqa: E402

REAL_DATA = Path(
    "/Volumes/Extreme SSD/law-cite-tt-data/markdown/8_08_Absconding_Debtors/105522.md"
)


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            from api.main import get_db

            pool = await get_db().connect()
            async with pool.acquire() as conn:
                await conn.execute(
                    "TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE"
                )
            yield ac
            async with pool.acquire() as conn:
                await conn.execute(
                    "TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE"
                )


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_local_preview_origin_is_allowed(client):
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


@pytest.mark.asyncio
async def test_stats_on_empty_db(client):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    assert resp.json() == {"chapters": 0, "versions": 0, "chunks": 0, "embedded": 0}


@pytest.mark.asyncio
async def test_search_and_lookup_after_ingest(client):
    if not REAL_DATA.exists():
        pytest.skip(f"source file not found: {REAL_DATA}")

    from api.main import get_db

    db = get_db()
    tmp_dir = REAL_DATA.parent.parent  # markdown/ (real chapter dir has many historical versions)
    count = await db.ingest_chapter("8_08_Absconding_Debtors", tmp_dir)
    assert count >= 15

    resp = await client.get(
        "/api/lookup", params={"chapter": "8:08", "section": "1", "date": "2016-12-31"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "Absconding Debtors Act" in body[0]["chunk_text"]
    assert body[0]["pdf_url"].endswith("105522?type=act")

    resp = await client.get("/api/search", params={"q": "affidavit", "mode": "fts"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_grouped_search_contract_and_pdf_urls(client, monkeypatch):
    from api.main import get_db

    async def fake_search_grouped(*args, **kwargs):
        return {
            "items": [
                {
                    "key": "9:70::244",
                    "title": "Bankruptcy Act",
                    "chapter_number": "9:70",
                    "section_ref": "244",
                    "heading": "Summary administration",
                    "matched_version": {
                        "version_id": 2,
                        "download_id": 1002,
                        "as_at_date": date(2012, 12, 31),
                        "version_label": "2012 revision",
                        "chunk_id": 8,
                        "chunk_text": "Where the debtor has absconded.",
                    },
                    "latest_available": {
                        "version_id": 2,
                        "download_id": 1002,
                        "as_at_date": date(2012, 12, 31),
                        "version_label": "2012 revision",
                    },
                    "versions": [
                        {
                            "version_id": 2,
                            "download_id": 1002,
                            "as_at_date": date(2012, 12, 31),
                            "version_label": "2012 revision",
                        }
                    ],
                    "score": 0.75,
                }
            ],
            "next_offset": None,
            "has_more": False,
        }

    monkeypatch.setattr(get_db(), "search_grouped", fake_search_grouped)
    response = await client.get(
        "/api/search/grouped",
        params={"q": "absconding debtor", "mode": "fts"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["title"] == "Bankruptcy Act"
    assert body["items"][0]["matched_version"]["pdf_url"].endswith(
        "/1002?type=act"
    )
    assert body["items"][0]["latest_available"]["pdf_url"].endswith(
        "/1002?type=act"
    )


@pytest.mark.asyncio
async def test_grouped_search_rejects_unknown_mode(client):
    response = await client.get(
        "/api/search/grouped",
        params={"q": "debtor", "mode": "unknown"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_citation_resolve_contract_normalizes_and_formats(client, monkeypatch):
    from api.main import get_db

    async def fake_resolve(*args, **kwargs):
        return {
            "status": "found",
            "authority": {
                "title": "Absconding Debtors",
                "chapter_number": "8:08",
                "section_ref": "12(3)(a)",
                "heading": "Power to arrest",
                "as_at_date": date(2009, 12, 31),
                "version_label": "2009 revision",
                "download_id": 1001,
                "chunk_text": "A debtor may be arrested in the prescribed case.",
            },
            "alternatives": [],
        }

    monkeypatch.setattr(get_db(), "resolve_citation", fake_resolve)
    response = await client.get(
        "/api/citations/resolve",
        params={
            "chapter": "Chap. 8-8",
            "section": "section 12 (3) (A)",
            "date": "2010-01-01",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "found"
    assert body["normalized_input"] == {
        "chapter": "8:08",
        "section": "12(3)(a)",
        "date": "2010-01-01",
    }
    assert body["citation"]["full"] == (
        "Absconding Debtors Act, Chap. 8:08, s. 12(3)(a) "
        "(version available as at 1 January 2010)"
    )
    assert body["citation"]["short"] == "Chap. 8:08, s. 12(3)(a)"
    assert body["authority"]["pdf_url"].endswith("/1001?type=act")
    assert body["text"].startswith("A debtor")


@pytest.mark.asyncio
async def test_citation_resolve_returns_explicit_not_found(client, monkeypatch):
    from api.main import get_db

    async def fake_resolve(*args, **kwargs):
        return {
            "status": "not_found",
            "authority": None,
            "alternatives": [
                {
                    "title": "Absconding Debtors",
                    "chapter_number": "8:08",
                    "section_ref": "12",
                    "as_at_date": None,
                    "version_label": "",
                    "download_id": 1001,
                }
            ],
        }

    monkeypatch.setattr(get_db(), "resolve_citation", fake_resolve)
    response = await client.get(
        "/api/citations/resolve",
        params={"chapter": "8:08", "section": "13"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "not_found"
    assert response.json()["citation"] is None
    assert response.json()["alternatives"][0]["section_ref"] == "12"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"chapter": "chapter eight", "section": "12"},
        {"chapter": "8:08", "section": "section twelve"},
        {"chapter": "8:08", "section": "12", "date": "31-12-2012"},
    ],
)
async def test_citation_resolve_rejects_malformed_input(client, params):
    response = await client.get("/api/citations/resolve", params=params)

    assert response.status_code == 422
