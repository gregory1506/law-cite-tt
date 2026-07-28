"""One-shot migration: copy chapters/versions/chunks (with embeddings)
from the sqlite law_cite.db into a PostgreSQL + pgvector database.

Usage:
    python migrate_sqlite_to_pg.py --sqlite <path> --pg <dsn> [--batch-size 1000] [--force]

--force truncates the destination chapters/versions/chunks tables first.
Without it, the script refuses to run against a non-empty destination.
"""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper.embed import unpack_embedding  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sqlite",
        default="/Volumes/Extreme SSD/law-cite-tt-data/law_cite.db",
        help="Path to the source sqlite database",
    )
    p.add_argument(
        "--pg",
        default="postgresql://lawcite:changeme@localhost:5432/lawcite",
        help="Destination Postgres DSN",
    )
    p.add_argument("--batch-size", type=int, default=1000)
    p.add_argument(
        "--force",
        action="store_true",
        help="Truncate destination chapters/versions/chunks before migrating",
    )
    return p.parse_args()


def _to_date(raw: str) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


async def migrate_chapters(sconn: sqlite3.Connection, pool: asyncpg.Pool) -> dict[int, int]:
    rows = sconn.execute("SELECT id, chapter_number, title FROM chapters ORDER BY id").fetchall()
    id_map: dict[int, int] = {}
    async with pool.acquire() as conn:
        for r in rows:
            new_id = await conn.fetchval(
                "INSERT INTO chapters (chapter_number, title) VALUES ($1, $2) RETURNING id",
                r["chapter_number"],
                r["title"],
            )
            id_map[r["id"]] = new_id
    print(f"  chapters: {len(id_map)} migrated")
    return id_map


async def migrate_versions(
    sconn: sqlite3.Connection, pool: asyncpg.Pool, chapter_id_map: dict[int, int]
) -> dict[int, int]:
    rows = sconn.execute(
        "SELECT id, chapter_id, download_id, version_label, as_at_date FROM versions ORDER BY id"
    ).fetchall()
    id_map: dict[int, int] = {}
    async with pool.acquire() as conn:
        for r in rows:
            new_id = await conn.fetchval(
                """
                INSERT INTO versions (chapter_id, download_id, version_label, as_at_date)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                chapter_id_map[r["chapter_id"]],
                r["download_id"],
                r["version_label"] or "",
                _to_date(r["as_at_date"]),
            )
            id_map[r["id"]] = new_id
    print(f"  versions: {len(id_map)} migrated")
    return id_map


async def migrate_chunks(
    sconn: sqlite3.Connection,
    pool: asyncpg.Pool,
    version_id_map: dict[int, int],
    batch_size: int,
) -> int:
    total = sconn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
    offset = 0
    migrated = 0
    start = time.monotonic()

    async with pool.acquire() as conn:
        stmt = await conn.prepare(
            """
            INSERT INTO chunks
            (version_id, chapter_number, section_ref, heading, chunk_text,
             as_at_date, version_label, chunk_index, embedding)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector)
            """
        )
        while True:
            rows = sconn.execute(
                """
                SELECT version_id, chapter_number, section_ref, heading, chunk_text,
                       as_at_date, version_label, chunk_index, embedding
                FROM chunks ORDER BY id LIMIT ? OFFSET ?
                """,
                (batch_size, offset),
            ).fetchall()
            if not rows:
                break

            records = []
            for r in rows:
                vec = unpack_embedding(r["embedding"]) if r["embedding"] else None
                vec_literal = "[" + ",".join(str(v) for v in vec) + "]" if vec else None
                records.append(
                    (
                        version_id_map[r["version_id"]],
                        r["chapter_number"],
                        r["section_ref"],
                        r["heading"] or "",
                        r["chunk_text"],
                        _to_date(r["as_at_date"]),
                        r["version_label"] or "",
                        r["chunk_index"] or 0,
                        vec_literal,
                    )
                )

            await stmt.executemany(records)
            migrated += len(rows)
            offset += batch_size
            elapsed = time.monotonic() - start
            rate = migrated / elapsed if elapsed else 0
            print(f"  chunks: {migrated}/{total} ({rate:.0f}/s)", end="\r")

    print(f"\n  chunks: {migrated} migrated")
    return migrated


async def run(args: argparse.Namespace) -> None:
    sconn = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
    sconn.row_factory = sqlite3.Row

    pool = await asyncpg.create_pool(args.pg, min_size=1, max_size=5)

    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM chapters")
    if existing and not args.force:
        print(
            f"Destination already has {existing} chapters. Pass --force to truncate and re-migrate."
        )
        await pool.close()
        sconn.close()
        return
    if existing and args.force:
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE chunks, versions, chapters RESTART IDENTITY CASCADE")
        print(f"Truncated existing {existing} chapters (and dependent rows).")

    print("Migrating chapters...")
    chapter_id_map = await migrate_chapters(sconn, pool)

    print("Migrating versions...")
    version_id_map = await migrate_versions(sconn, pool, chapter_id_map)

    print("Migrating chunks (this can take a while)...")
    await migrate_chunks(sconn, pool, version_id_map, args.batch_size)

    async with pool.acquire() as conn:
        ch = await conn.fetchval("SELECT COUNT(*) FROM chapters")
        ve = await conn.fetchval("SELECT COUNT(*) FROM versions")
        cn = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        em = await conn.fetchval("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")

    print(f"Done. chapters={ch} versions={ve} chunks={cn} embedded={em}")

    await pool.close()
    sconn.close()


def main() -> None:
    args = _parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
