from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import asyncpg

from scraper.chunker import chunk_markdown_file
from scraper.embed import embed_text


class LawCitePGDB:
    """Async Postgres + pgvector backed store. Merges the old sqlite
    LawCiteDB (ingestion) and SearchEngine (FTS/vector/hybrid search)
    into a single connection-pooled class."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
        return self._pool

    async def close(self):
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @staticmethod
    def _parse_date(raw: str) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def _chapter_from_folder(folder: str) -> tuple[str, str]:
        parts = folder.split("_")
        if parts[0].isdigit() and len(parts) > 2 and parts[1].isdigit():
            return f"{parts[0]}:{parts[1]}", " ".join(parts[2:])
        return folder.replace("_", " "), ""

    async def ingest_chapter(self, chapter_folder: str, markdown_dir: Path) -> int:
        pool = await self.connect()
        folder_path = markdown_dir / chapter_folder
        if not folder_path.is_dir():
            return 0

        chapter_number, title = self._chapter_from_folder(chapter_folder)

        async with pool.acquire() as conn:
            chapter_id = await conn.fetchval(
                """
                INSERT INTO chapters (chapter_number, title) VALUES ($1, $2)
                ON CONFLICT (chapter_number) DO UPDATE SET title = EXCLUDED.title
                RETURNING id
                """,
                chapter_number,
                title,
            )

            count = 0
            for md_file in sorted(folder_path.iterdir()):
                if md_file.name.startswith(".") or md_file.suffix != ".md":
                    continue
                download_id = int(md_file.stem)

                chunks = chunk_markdown_file(md_file)
                if not chunks:
                    continue

                version_id = await conn.fetchval(
                    """
                    INSERT INTO versions (chapter_id, download_id) VALUES ($1, $2)
                    ON CONFLICT (chapter_id, download_id) DO UPDATE SET chapter_id = EXCLUDED.chapter_id
                    RETURNING id
                    """,
                    chapter_id,
                    download_id,
                )

                await conn.executemany(
                    """
                    INSERT INTO chunks
                    (version_id, chapter_number, section_ref, heading, chunk_text,
                     as_at_date, version_label, chunk_index)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    [
                        (
                            version_id,
                            c.chapter_number,
                            c.section_ref,
                            c.heading,
                            c.chunk_text,
                            self._parse_date(c.as_at_date),
                            c.version_label,
                            c.chunk_index,
                        )
                        for c in chunks
                    ],
                )
                count += len(chunks)

        return count

    async def lookup_section(
        self,
        chapter: str,
        section: str,
        as_at_date: str | None = None,
        min_chars: int = 0,
    ) -> list[dict[str, Any]]:
        pool = await self.connect()
        query = """
            SELECT c.chunk_text, c.chapter_number, c.section_ref, c.heading,
                   c.as_at_date, c.version_label, v.download_id
            FROM chunks c
            JOIN versions v ON c.version_id = v.id
            WHERE c.chapter_number = $1 AND c.section_ref = $2
        """
        params: list[Any] = [chapter, section]
        if as_at_date:
            query += " AND c.as_at_date = $3"
            params.append(self._parse_date(as_at_date))

        query += " ORDER BY c.as_at_date DESC NULLS LAST"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        results = [dict(r) for r in rows]
        if min_chars:
            results = [r for r in results if len(r["chunk_text"]) >= min_chars]
        return results

    async def search_fts(
        self,
        query: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        pool = await self.connect()
        sql = """
            SELECT c.id, c.chunk_text, c.section_ref, c.chapter_number,
                   c.version_id, c.as_at_date, v.download_id,
                   ts_rank(to_tsvector('english', c.chunk_text), plainto_tsquery('english', $1)) AS score
            FROM chunks c
            JOIN versions v ON c.version_id = v.id
            WHERE to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', $1)
        """
        params: list[Any] = [query]

        if chapter:
            params.append(chapter)
            sql += f" AND c.chapter_number = ${len(params)}"
        if as_at_date:
            params.append(self._parse_date(as_at_date))
            sql += f" AND (c.as_at_date IS NULL OR c.as_at_date <= ${len(params)})"

        params.append(limit)
        sql += f" ORDER BY score DESC LIMIT ${len(params)}"

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]

    async def search_vector(
        self,
        query: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        pool = await self.connect()
        qvec = embed_text(query)
        qvec_literal = "[" + ",".join(str(v) for v in qvec) + "]"

        sql = """
            SELECT c.id, c.chunk_text, c.section_ref, c.chapter_number,
                   c.version_id, c.as_at_date, v.download_id,
                   1 - (c.embedding <=> $1::vector) AS score
            FROM chunks c
            JOIN versions v ON c.version_id = v.id
            WHERE c.embedding IS NOT NULL
        """
        params: list[Any] = [qvec_literal]

        if chapter:
            params.append(chapter)
            sql += f" AND c.chapter_number = ${len(params)}"
        if as_at_date:
            params.append(self._parse_date(as_at_date))
            sql += f" AND (c.as_at_date IS NULL OR c.as_at_date <= ${len(params)})"

        params.append(limit)
        sql += f" ORDER BY c.embedding <=> $1::vector LIMIT ${len(params)}"

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(r) for r in rows]

    async def search_hybrid(
        self,
        query: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
        fts_weight: float = 0.5,
    ) -> list[dict[str, Any]]:
        fts_results = await self.search_fts(
            query, chapter=chapter, as_at_date=as_at_date, limit=limit * 2
        )
        vec_results = await self.search_vector(
            query, chapter=chapter, as_at_date=as_at_date, limit=limit * 2
        )

        fts_by_id = {r["id"]: r["score"] for r in fts_results}
        vec_by_id = {r["id"]: r["score"] for r in vec_results}
        all_ids = set(fts_by_id) | set(vec_by_id)

        fts_max = max(fts_by_id.values()) if fts_by_id else 1.0
        vec_max = max(vec_by_id.values()) if vec_by_id else 1.0

        rows_by_id = {r["id"]: r for r in fts_results}
        for r in vec_results:
            rows_by_id.setdefault(r["id"], r)

        combined = []
        for rid in all_ids:
            fts_s = fts_by_id.get(rid, 0.0)
            vec_s = vec_by_id.get(rid, 0.0)
            score = fts_weight * (fts_s / fts_max) + (1 - fts_weight) * (vec_s / vec_max)
            d = dict(rows_by_id[rid])
            d["score"] = round(score, 6)
            combined.append(d)

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:limit]
