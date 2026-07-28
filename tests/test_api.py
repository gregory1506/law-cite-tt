import os
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
