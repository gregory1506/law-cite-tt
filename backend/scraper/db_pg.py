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
        download_id: int | None = None,
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
            params.append(self._parse_date(as_at_date))
            query += f" AND c.as_at_date = ${len(params)}"
        if download_id is not None:
            params.append(download_id)
            query += f" AND v.download_id = ${len(params)}"

        query += " ORDER BY c.as_at_date DESC NULLS LAST, c.chunk_index, c.id"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        results = [dict(r) for r in rows]
        if min_chars:
            results = [r for r in results if len(r["chunk_text"]) >= min_chars]
        return results

    @staticmethod
    def _group_key(row: dict[str, Any]) -> str:
        section_ref = (row.get("section_ref") or "").strip()
        if section_ref:
            return f"{row['chapter_number']}::{section_ref}"
        return f"{row['chapter_number']}::chunk:{row['id']}"

    async def _search_group_candidates(
        self,
        query: str,
        *,
        mode: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        pool = await self.connect()
        params: list[Any] = []

        if mode == "fts":
            params.append(query)
            score_sql = (
                "ts_rank(to_tsvector('english', c.chunk_text), "
                "plainto_tsquery('english', $1))"
            )
            match_sql = (
                "to_tsvector('english', c.chunk_text) "
                "@@ plainto_tsquery('english', $1)"
            )
        elif mode == "vector":
            qvec = embed_text(query)
            qvec_literal = "[" + ",".join(str(v) for v in qvec) + "]"
            params.append(qvec_literal)
            score_sql = "1 - (c.embedding <=> $1::vector)"
            match_sql = "c.embedding IS NOT NULL"
        else:
            raise ValueError(f"Unsupported grouped search mode: {mode}")

        filters = [match_sql]
        if chapter:
            params.append(chapter)
            filters.append(f"c.chapter_number = ${len(params)}")
        if as_at_date:
            parsed_date = self._parse_date(as_at_date)
            if parsed_date is None:
                return []
            params.append(parsed_date)
            # Undated versions cannot be proven to apply on a historical date.
            filters.append(
                f"COALESCE(v.as_at_date, c.as_at_date) <= ${len(params)}"
            )

        params.extend([offset, limit])
        offset_param = len(params) - 1
        limit_param = len(params)
        sql = f"""
            WITH scored AS (
                SELECT
                    c.id,
                    c.chunk_text,
                    c.section_ref,
                    c.chapter_number,
                    c.heading,
                    c.version_id,
                    COALESCE(v.as_at_date, c.as_at_date) AS as_at_date,
                    COALESCE(NULLIF(v.version_label, ''), c.version_label, '') AS version_label,
                    v.download_id,
                    ch.title,
                    {score_sql} AS score,
                    CASE
                        WHEN btrim(c.section_ref) <> ''
                            THEN c.chapter_number || '::' || btrim(c.section_ref)
                        ELSE c.chapter_number || '::chunk:' || c.id::text
                    END AS provision_key
                FROM chunks c
                JOIN versions v ON c.version_id = v.id
                JOIN chapters ch ON v.chapter_id = ch.id
                WHERE {' AND '.join(filters)}
            ),
            ranked AS (
                SELECT scored.*,
                       row_number() OVER (
                           PARTITION BY provision_key
                           ORDER BY score DESC, as_at_date DESC NULLS LAST, id DESC
                       ) AS provision_rank
                FROM scored
            )
            SELECT *
            FROM ranked
            WHERE provision_rank = 1
            ORDER BY score DESC, provision_key
            OFFSET ${offset_param}
            LIMIT ${limit_param}
        """

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]

    async def _version_summaries(
        self,
        candidates: list[dict[str, Any]],
        *,
        as_at_date: str = "",
    ) -> dict[str, list[dict[str, Any]]]:
        section_keys = {
            (row["chapter_number"], (row.get("section_ref") or "").strip())
            for row in candidates
            if (row.get("section_ref") or "").strip()
        }
        summaries: dict[str, list[dict[str, Any]]] = {}

        if section_keys:
            params: list[Any] = []
            predicates: list[str] = []
            for chapter_number, section_ref in sorted(section_keys):
                params.extend([chapter_number, section_ref])
                predicates.append(
                    f"(c.chapter_number = ${len(params) - 1} "
                    f"AND c.section_ref = ${len(params)})"
                )

            date_filter = ""
            if as_at_date:
                parsed_date = self._parse_date(as_at_date)
                if parsed_date is None:
                    return {}
                params.append(parsed_date)
                date_filter = (
                    "AND COALESCE(v.as_at_date, c.as_at_date) "
                    f"<= ${len(params)}"
                )

            sql = f"""
                SELECT DISTINCT
                    c.chapter_number,
                    c.section_ref,
                    v.id AS version_id,
                    v.download_id,
                    COALESCE(v.as_at_date, c.as_at_date) AS as_at_date,
                    COALESCE(NULLIF(v.version_label, ''), c.version_label, '') AS version_label
                FROM chunks c
                JOIN versions v ON c.version_id = v.id
                WHERE ({' OR '.join(predicates)})
                {date_filter}
                ORDER BY
                    c.chapter_number,
                    c.section_ref,
                    as_at_date DESC NULLS LAST,
                    v.download_id DESC
            """
            pool = await self.connect()
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
            for raw in rows:
                row = dict(raw)
                key = f"{row['chapter_number']}::{row['section_ref'].strip()}"
                summaries.setdefault(key, []).append(
                    {
                        "version_id": row["version_id"],
                        "download_id": row["download_id"],
                        "as_at_date": row["as_at_date"],
                        "version_label": row["version_label"] or "",
                    }
                )

        for candidate in candidates:
            key = candidate["provision_key"]
            if key not in summaries:
                summaries[key] = [
                    {
                        "version_id": candidate["version_id"],
                        "download_id": candidate["download_id"],
                        "as_at_date": candidate["as_at_date"],
                        "version_label": candidate["version_label"] or "",
                    }
                ]

        return summaries

    async def search_grouped(
        self,
        query: str,
        *,
        mode: str = "fts",
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        requested = limit + 1
        if mode in {"fts", "vector"}:
            candidates = await self._search_group_candidates(
                query,
                mode=mode,
                chapter=chapter,
                as_at_date=as_at_date,
                limit=requested,
                offset=offset,
            )
        elif mode == "hybrid":
            candidate_limit = max((offset + requested) * 4, 80)
            fts_results = await self._search_group_candidates(
                query,
                mode="fts",
                chapter=chapter,
                as_at_date=as_at_date,
                limit=candidate_limit,
            )
            vector_results = await self._search_group_candidates(
                query,
                mode="vector",
                chapter=chapter,
                as_at_date=as_at_date,
                limit=candidate_limit,
            )
            fts_by_key = {row["provision_key"]: row for row in fts_results}
            vector_by_key = {row["provision_key"]: row for row in vector_results}
            all_keys = set(fts_by_key) | set(vector_by_key)
            fts_max = max((row["score"] for row in fts_results), default=1.0) or 1.0
            vector_max = (
                max((row["score"] for row in vector_results), default=1.0) or 1.0
            )

            combined = []
            for key in all_keys:
                fts_row = fts_by_key.get(key)
                vector_row = vector_by_key.get(key)
                fts_score = fts_row["score"] if fts_row else 0.0
                vector_score = vector_row["score"] if vector_row else 0.0
                row = dict(fts_row or vector_row)
                row["score"] = 0.5 * (fts_score / fts_max) + 0.5 * (
                    vector_score / vector_max
                )
                combined.append(row)
            combined.sort(
                key=lambda row: (-row["score"], row["provision_key"], -row["id"])
            )
            candidates = combined[offset : offset + requested]
        else:
            raise ValueError(f"Unsupported grouped search mode: {mode}")

        has_more = len(candidates) > limit
        page = candidates[:limit]
        versions_by_key = await self._version_summaries(
            page,
            as_at_date=as_at_date,
        )
        items = []
        for row in page:
            versions = versions_by_key[row["provision_key"]]
            latest_available = next(
                (version for version in versions if version["as_at_date"] is not None),
                None,
            )
            items.append(
                {
                    "key": row["provision_key"],
                    "title": row["title"],
                    "chapter_number": row["chapter_number"],
                    "section_ref": row["section_ref"],
                    "heading": row["heading"] or "",
                    "matched_version": {
                        "version_id": row["version_id"],
                        "download_id": row["download_id"],
                        "as_at_date": row["as_at_date"],
                        "version_label": row["version_label"] or "",
                        "chunk_id": row["id"],
                        "chunk_text": row["chunk_text"],
                    },
                    "latest_available": latest_available,
                    "versions": versions,
                    "score": float(row["score"]),
                }
            )

        return {
            "items": items,
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
        }

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
