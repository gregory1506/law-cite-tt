import sqlite3
import sys
from pathlib import Path

import asyncpg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "scripts"))

from scraper.db import LawCiteDB
from scraper.embed import embed_chunks_from_db, unpack_embedding
from migrate_sqlite_to_pg import run as run_migration

MARKDOWN_DIR = Path("/Volumes/Extreme SSD/law-cite-tt-data/markdown")
PG_DSN = "postgresql://lawcite:changeme@localhost:5432/lawcite_test"


class _Args:
    def __init__(self, sqlite_path: str, force: bool = True, batch_size: int = 50):
        self.sqlite = sqlite_path
        self.pg = PG_DSN
        self.batch_size = batch_size
        self.force = force


@pytest.fixture
def source_sqlite(tmp_path):
    if not MARKDOWN_DIR.exists():
        pytest.skip(f"source markdown not found: {MARKDOWN_DIR}")
    db_path = tmp_path / "source.db"
    db = LawCiteDB(db_path)
    db.connect()
    count = db.ingest_chapter("8_08_Absconding_Debtors", MARKDOWN_DIR)
    assert count >= 15
    db.close()

    embedded = embed_chunks_from_db(db_path)
    assert embedded == count
    return db_path


@pytest.fixture
async def clean_pg():
    pool = await asyncpg.create_pool(PG_DSN, min_size=1, max_size=3)
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE")
    yield pool
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE")
    await pool.close()


@pytest.mark.asyncio
async def test_migration_preserves_counts_and_content(source_sqlite, clean_pg):
    sconn = sqlite3.connect(str(source_sqlite))
    sconn.row_factory = sqlite3.Row
    src_chapters = sconn.execute("SELECT COUNT(*) AS n FROM chapters").fetchone()["n"]
    src_versions = sconn.execute("SELECT COUNT(*) AS n FROM versions").fetchone()["n"]
    src_chunks = sconn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
    sconn.close()

    await run_migration(_Args(str(source_sqlite)))

    async with clean_pg.acquire() as conn:
        ch = await conn.fetchval("SELECT COUNT(*) FROM chapters")
        ve = await conn.fetchval("SELECT COUNT(*) FROM versions")
        cn = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        em = await conn.fetchval("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")

    assert ch == src_chapters
    assert ve == src_versions
    assert cn == src_chunks
    assert em == src_chunks

    async with clean_pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT chunk_text FROM chunks WHERE chapter_number = '8:08' AND section_ref = '1' "
            "AND as_at_date = '2016-12-31'"
        )
    assert row is not None
    assert "Absconding Debtors Act" in row["chunk_text"]


@pytest.mark.asyncio
async def test_migration_embedding_values_match_source(source_sqlite, clean_pg):
    sconn = sqlite3.connect(str(source_sqlite))
    sconn.row_factory = sqlite3.Row
    src_row = sconn.execute(
        "SELECT chunk_text, embedding FROM chunks WHERE chapter_number = '8:08' "
        "AND section_ref = '1' AND as_at_date = '2016-12-31'"
    ).fetchone()
    src_vec = unpack_embedding(src_row["embedding"])
    sconn.close()

    await run_migration(_Args(str(source_sqlite)))

    async with clean_pg.acquire() as conn:
        pg_vec_str = await conn.fetchval(
            "SELECT embedding::text FROM chunks WHERE chapter_number = '8:08' "
            "AND section_ref = '1' AND as_at_date = '2016-12-31'"
        )
    pg_vec = [float(x) for x in pg_vec_str.strip("[]").split(",")]

    assert len(pg_vec) == len(src_vec)
    assert all(abs(a - b) < 1e-4 for a, b in zip(pg_vec, src_vec))


@pytest.mark.asyncio
async def test_migration_refuses_non_empty_destination_without_force(source_sqlite, clean_pg):
    await run_migration(_Args(str(source_sqlite)))

    # second run without --force should be a no-op (refuses to touch existing data)
    async with clean_pg.acquire() as conn:
        before = await conn.fetchval("SELECT COUNT(*) FROM chapters")

    await run_migration(_Args(str(source_sqlite), force=False))

    async with clean_pg.acquire() as conn:
        after = await conn.fetchval("SELECT COUNT(*) FROM chapters")

    assert before == after
