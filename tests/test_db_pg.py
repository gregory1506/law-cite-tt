import os
from pathlib import Path

import pytest

from scraper.db_pg import LawCitePGDB

TEST_DSN = os.environ.get(
    "TEST_PG_DSN", "postgresql://lawcite:changeme@localhost:5432/lawcite_test"
)

REAL_DATA = Path(
    "/Volumes/Extreme SSD/law-cite-tt-data/markdown/8_08_Absconding_Debtors/105522.md"
)


@pytest.fixture
async def db():
    store = LawCitePGDB(TEST_DSN)
    pool = await store.connect()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE")
    yield store
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE")
    await store.close()


async def _seed_chapter(tmp_path, name="8_08_Absconding_Debtors"):
    if not REAL_DATA.exists():
        pytest.skip(f"source file not found: {REAL_DATA}")
    folder = tmp_path / name
    folder.mkdir()
    (folder / "105522.md").write_text(
        REAL_DATA.read_text(encoding="utf-8", errors="replace")
    )
    return folder.parent


@pytest.mark.asyncio
async def test_ingest_chapter_creates_chapter_version_and_chunks(db, tmp_path):
    markdown_dir = await _seed_chapter(tmp_path)
    count = await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)
    assert count >= 15

    pool = await db.connect()
    async with pool.acquire() as conn:
        chapters = await conn.fetch("SELECT * FROM chapters")
        versions = await conn.fetch("SELECT * FROM versions")
        chunks = await conn.fetch("SELECT * FROM chunks")

    assert len(chapters) == 1
    assert chapters[0]["chapter_number"] == "8:08"
    assert len(versions) == 1
    assert versions[0]["download_id"] == 105522
    assert len(chunks) == count


@pytest.mark.asyncio
async def test_ingest_chapter_is_idempotent(db, tmp_path):
    markdown_dir = await _seed_chapter(tmp_path)
    await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)
    await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)

    pool = await db.connect()
    async with pool.acquire() as conn:
        chapters = await conn.fetch("SELECT * FROM chapters")
        versions = await conn.fetch("SELECT * FROM versions")

    assert len(chapters) == 1
    assert len(versions) == 1


@pytest.mark.asyncio
async def test_lookup_section_returns_matching_chunk(db, tmp_path):
    markdown_dir = await _seed_chapter(tmp_path)
    await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)

    results = await db.lookup_section("8:08", "1")
    assert len(results) == 1
    assert "Absconding Debtors Act" in results[0]["chunk_text"]


@pytest.mark.asyncio
async def test_lookup_section_with_as_at_date_filter(db, tmp_path):
    markdown_dir = await _seed_chapter(tmp_path)
    await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)

    results = await db.lookup_section("8:08", "1", as_at_date="2016-12-31")
    assert len(results) == 1

    results = await db.lookup_section("8:08", "1", as_at_date="1900-01-01")
    assert results == []


@pytest.mark.asyncio
async def test_search_fts_finds_seeded_text(db, tmp_path):
    markdown_dir = await _seed_chapter(tmp_path)
    await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)

    results = await db.search_fts("affidavit")
    assert len(results) >= 1
    assert any("affidavit" in r["chunk_text"] for r in results)


@pytest.mark.asyncio
async def test_search_vector_and_hybrid_run_without_embeddings(db, tmp_path):
    markdown_dir = await _seed_chapter(tmp_path)
    await db.ingest_chapter("8_08_Absconding_Debtors", markdown_dir)

    # No embeddings populated yet -> vector search returns nothing, but must not error
    vec_results = await db.search_vector("affidavit")
    assert vec_results == []

    hybrid_results = await db.search_hybrid("affidavit")
    assert len(hybrid_results) >= 1
