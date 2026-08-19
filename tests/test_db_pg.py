import os
from datetime import date
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
        await conn.execute(
            "TRUNCATE chunks, versions, chapters, case_citations, cases "
            "RESTART IDENTITY CASCADE"
        )
    yield store
    async with pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE chunks, versions, chapters, case_citations, cases "
            "RESTART IDENTITY CASCADE"
        )
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


async def _seed_grouped_search_data(db):
    pool = await db.connect()
    vector = "[" + ",".join(["1"] + ["0"] * 383) + "]"
    async with pool.acquire() as conn:
        chapter_id = await conn.fetchval(
            """
            INSERT INTO chapters (chapter_number, title)
            VALUES ('9:70', 'Bankruptcy Act')
            RETURNING id
            """
        )
        old_version_id = await conn.fetchval(
            """
            INSERT INTO versions
                (chapter_id, download_id, version_label, as_at_date)
            VALUES ($1, 1001, '2009 revision', $2)
            RETURNING id
            """,
            chapter_id,
            date(2009, 12, 31),
        )
        latest_version_id = await conn.fetchval(
            """
            INSERT INTO versions
                (chapter_id, download_id, version_label, as_at_date)
            VALUES ($1, 1002, '2012 revision', $2)
            RETURNING id
            """,
            chapter_id,
            date(2012, 12, 31),
        )
        undated_version_id = await conn.fetchval(
            """
            INSERT INTO versions
                (chapter_id, download_id, version_label, as_at_date)
            VALUES ($1, 1003, 'archive scan', NULL)
            RETURNING id
            """,
            chapter_id,
        )
        rows = [
            (
                old_version_id,
                "244",
                "Summary administration",
                "The debtor has absconded and may be adjudged bankrupt.",
                date(2009, 12, 31),
                "2009 revision",
                0,
            ),
            (
                latest_version_id,
                "244",
                "Summary administration",
                "Where the debtor has absconded the Court may act.",
                date(2012, 12, 31),
                "2012 revision",
                0,
            ),
            (
                undated_version_id,
                "244",
                "Summary administration",
                "An absconding debtor may be adjudged bankrupt.",
                None,
                "archive scan",
                0,
            ),
            (
                latest_version_id,
                "180",
                "Adjudication",
                "The absconding debtor may be adjudged bankrupt.",
                date(2012, 12, 31),
                "2012 revision",
                1,
            ),
            (
                old_version_id,
                "",
                "Schedule",
                "A schedule concerning an absconding debtor.",
                date(2009, 12, 31),
                "2009 revision",
                2,
            ),
            (
                latest_version_id,
                "",
                "Preliminary text",
                "Preliminary text concerning an absconding debtor.",
                date(2012, 12, 31),
                "2012 revision",
                3,
            ),
        ]
        await conn.executemany(
            """
            INSERT INTO chunks
                (version_id, chapter_number, section_ref, heading, chunk_text,
                 as_at_date, version_label, chunk_index, embedding)
            VALUES ($1, '9:70', $2, $3, $4, $5, $6, $7, $8::vector)
            """,
            [(*row, vector) for row in rows],
        )


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


@pytest.mark.asyncio
async def test_grouped_fts_returns_one_provision_with_ordered_versions(db):
    await _seed_grouped_search_data(db)

    result = await db.search_grouped("absconding debtor", mode="fts", limit=20)

    keys = [item["key"] for item in result["items"]]
    assert keys.count("9:70::244") == 1
    item = next(item for item in result["items"] if item["key"] == "9:70::244")
    assert item["title"] == "Bankruptcy Act"
    assert item["heading"] == "Summary administration"
    assert item["matched_version"]["download_id"] in {1001, 1002, 1003}
    assert item["latest_available"]["download_id"] == 1002
    assert [version["download_id"] for version in item["versions"]] == [
        1002,
        1001,
        1003,
    ]
    fallback_keys = [key for key in keys if "::chunk:" in key]
    assert len(fallback_keys) == 2


@pytest.mark.asyncio
async def test_grouped_search_historical_date_excludes_later_and_undated_versions(db):
    await _seed_grouped_search_data(db)

    result = await db.search_grouped(
        "absconding debtor",
        mode="fts",
        as_at_date="2010-01-01",
        limit=20,
    )

    item = next(item for item in result["items"] if item["key"] == "9:70::244")
    assert item["matched_version"]["download_id"] == 1001
    assert item["latest_available"]["download_id"] == 1001
    assert [version["download_id"] for version in item["versions"]] == [1001]


@pytest.mark.asyncio
async def test_grouped_search_historical_date_uses_migrated_chunk_date(db):
    await _seed_grouped_search_data(db)
    pool = await db.connect()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE versions SET as_at_date = NULL WHERE download_id = 1001"
        )

    result = await db.search_grouped(
        "absconding debtor",
        mode="fts",
        as_at_date="2010-01-01",
        limit=20,
    )

    item = next(item for item in result["items"] if item["key"] == "9:70::244")
    assert item["matched_version"]["download_id"] == 1001
    assert item["latest_available"]["download_id"] == 1001
    assert [version["download_id"] for version in item["versions"]] == [1001]


@pytest.mark.asyncio
async def test_grouped_search_paginates_unique_provisions(db):
    await _seed_grouped_search_data(db)

    first = await db.search_grouped("absconding debtor", mode="fts", limit=1)
    second = await db.search_grouped(
        "absconding debtor",
        mode="fts",
        limit=1,
        offset=first["next_offset"],
    )

    assert first["has_more"] is True
    assert first["next_offset"] == 1
    assert second["items"][0]["key"] != first["items"][0]["key"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["vector", "hybrid"])
async def test_grouped_vector_and_hybrid_collapse_versions(db, mode):
    await _seed_grouped_search_data(db)

    result = await db.search_grouped("absconding debtor", mode=mode, limit=20)

    keys = [item["key"] for item in result["items"]]
    assert keys.count("9:70::244") == 1


@pytest.mark.asyncio
async def test_lookup_section_can_select_exact_download(db):
    await _seed_grouped_search_data(db)

    rows = await db.lookup_section("9:70", "244", download_id=1003)

    assert len(rows) == 1
    assert rows[0]["download_id"] == 1003
    assert "archive" in rows[0]["version_label"]


@pytest.mark.asyncio
async def test_resolve_citation_selects_latest_available_version(db):
    await _seed_grouped_search_data(db)

    result = await db.resolve_citation("9:70", "244")

    assert result["status"] == "found"
    assert result["authority"]["title"] == "Bankruptcy Act"
    assert result["authority"]["download_id"] == 1002
    assert result["authority"]["as_at_date"] == date(2012, 12, 31)


@pytest.mark.asyncio
async def test_resolve_citation_selects_historical_version(db):
    await _seed_grouped_search_data(db)

    result = await db.resolve_citation("9:70", "244", "2010-01-01")

    assert result["status"] == "found"
    assert result["authority"]["download_id"] == 1001
    assert result["authority"]["as_at_date"] == date(2009, 12, 31)


@pytest.mark.asyncio
async def test_resolve_citation_uses_migrated_chunk_date(db):
    await _seed_grouped_search_data(db)
    pool = await db.connect()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE versions SET as_at_date = NULL WHERE download_id = 1001"
        )

    result = await db.resolve_citation("9:70", "244", "2010-01-01")

    assert result["status"] == "found"
    assert result["authority"]["download_id"] == 1001


@pytest.mark.asyncio
async def test_resolve_citation_returns_not_found_and_section_alternatives(db):
    await _seed_grouped_search_data(db)

    result = await db.resolve_citation("9:70", "245")

    assert result["status"] == "not_found"
    assert result["authority"] is None
    assert any(item["section_ref"] == "244" for item in result["alternatives"])


@pytest.mark.asyncio
async def test_resolve_citation_reports_materially_ambiguous_rows(db):
    await _seed_grouped_search_data(db)
    pool = await db.connect()
    async with pool.acquire() as conn:
        version_id = await conn.fetchval(
            "SELECT id FROM versions WHERE download_id = 1002"
        )
        await conn.execute(
            """
            INSERT INTO chunks
                (version_id, chapter_number, section_ref, heading, chunk_text,
                 as_at_date, version_label, chunk_index)
            VALUES ($1, '9:70', '244', 'Alternate text', 'Conflicting text.',
                    $2, '2012 revision', 99)
            """,
            version_id,
            date(2012, 12, 31),
        )

    result = await db.resolve_citation("9:70", "244")

    assert result["status"] == "ambiguous"
    assert len(result["alternatives"]) == 2


async def _seed_cases(db):
    pool = await db.connect()
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO cases (id, title, source, record_id, court, year)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [
                ("case:aaaa", "Smith v Jones", "webopac", "aaaa", "High Court", 2015),
                ("case:bbbb", "Brown v State", "webopac", "bbbb", "", 2010),
                ("case:cccc", "Green v Green", "ccj", "cccc", "CCJ", None),
            ],
        )
        await conn.executemany(
            """
            INSERT INTO case_citations
                (case_id, chapter_number, confidence, method, evidence, detail)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [
                ("case:aaaa", "8:08", "high", "REGEX", "EXTRACTED", "Ch. 8:08"),
                ("case:bbbb", "8:08", "medium", "TITLE_MATCH", "EXTRACTED", "Absconding Debtors Act"),
                ("case:bbbb", "5:01", "medium", "REGEX", "EXTRACTED", "Ch. 5:01"),
                ("case:cccc", "8:08", "low", "REGEX", "EXTRACTED", "Ch. 8:08"),
            ],
        )


@pytest.mark.asyncio
async def test_cases_citing_chapter_returns_titled_cases(db):
    await _seed_cases(db)

    rows = await db.cases_citing_chapter("8:08")

    assert {r["case_id"] for r in rows} == {"case:aaaa", "case:bbbb", "case:cccc"}
    assert rows[0]["case_id"] == "case:aaaa"  # high confidence sorts first
    assert rows[0]["title"] == "Smith v Jones"


@pytest.mark.asyncio
async def test_case_citations_for_and_expansion(db):
    await _seed_cases(db)

    citations = await db.case_citations_for("case:bbbb")
    assert [c["chapter_number"] for c in citations] == ["5:01", "8:08"]

    related = await db.cases_citing_chapters(
        ["5:01", "8:08"],
        exclude_case_id="case:bbbb",
    )
    assert {r["case_id"] for r in related} == {"case:aaaa", "case:cccc"}
    assert "case:bbbb" not in {r["case_id"] for r in related}


@pytest.mark.asyncio
async def test_search_cases_matches_title(db):
    await _seed_cases(db)

    rows = await db.search_cases("smith")
    assert [r["id"] for r in rows] == ["case:aaaa"]


@pytest.mark.asyncio
async def test_get_case_returns_row(db):
    await _seed_cases(db)

    case = await db.get_case("case:aaaa")
    assert case is not None
    assert case["title"] == "Smith v Jones"
    assert await db.get_case("case:nope") is None
