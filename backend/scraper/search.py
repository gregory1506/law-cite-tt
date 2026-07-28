from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from scraper.embed import (
    cosine_similarity,
    embed_batch,
    embed_text,
    unpack_embedding,
)


class SearchEngine:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def has_embeddings(self) -> bool:
        has_col = self.conn.execute("PRAGMA table_info(chunks)").fetchall()
        return any(r["name"] == "embedding" for r in has_col)

    def fts_search(
        self,
        query: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT c.id, c.chunk_text, c.section_ref, c.chapter_number,
                   c.version_id, c.as_at_date, v.download_id,
                   rank AS score
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.rowid
            JOIN versions v ON c.version_id = v.id
            WHERE chunks_fts MATCH ?
        """
        params: list[str] = [query]

        if chapter:
            sql += " AND c.chapter_number = ?"
            params.append(chapter)
        if as_at_date:
            sql += " AND (c.as_at_date IS NULL OR c.as_at_date <= ?)"
            params.append(as_at_date)

        sql += " ORDER BY rank LIMIT ?"
        params.append(str(limit))

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def vector_search(
        self,
        query: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        qvec = embed_text(query)
        rows = self.conn.execute(
            "SELECT c.id, c.chunk_text, c.section_ref, c.chapter_number, "
            "c.version_id, c.as_at_date, c.embedding, v.download_id "
            "FROM chunks c "
            "JOIN versions v ON c.version_id = v.id "
            "WHERE c.embedding IS NOT NULL"
        ).fetchall()

        if chapter:
            rows = [r for r in rows if r["chapter_number"] == chapter]
        if as_at_date:
            rows = [
                r
                for r in rows
                if r["as_at_date"] is None or r["as_at_date"] <= as_at_date
            ]

        scored = []
        for r in rows:
            vec = unpack_embedding(r["embedding"])
            score = cosine_similarity(qvec, vec)
            d = dict(r)
            d.pop("embedding", None)
            d["score"] = round(score, 6)
            scored.append(d)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def hybrid_search(
        self,
        query: str,
        chapter: str = "",
        as_at_date: str = "",
        limit: int = 20,
        fts_weight: float = 0.5,
    ) -> list[dict[str, Any]]:
        fts_results = self.fts_search(
            query, chapter=chapter, as_at_date=as_at_date, limit=limit * 2
        )
        vec_results = self.vector_search(
            query, chapter=chapter, as_at_date=as_at_date, limit=limit * 2
        )

        seen: set[int] = set()
        combined = []
        fts_by_id = {r["id"]: r["score"] for r in fts_results}
        vec_by_id = {r["id"]: r["score"] for r in vec_results}

        all_ids_set = set(fts_by_id) | set(vec_by_id)

        if fts_by_id:
            fts_max = max(fts_by_id.values())
        else:
            fts_max = 1.0
        if vec_by_id:
            vec_max = max(vec_by_id.values())
        else:
            vec_max = 1.0

        for rid in all_ids_set:
            fts_s = fts_by_id.get(rid, 0.0)
            vec_s = vec_by_id.get(rid, 0.0)
            combined_score = (
                fts_weight * (fts_s / fts_max)
                + (1 - fts_weight) * (vec_s / vec_max)
            )

            row = None
            for r in fts_results:
                if r["id"] == rid:
                    row = r
                    break
            if row is None:
                for r in vec_results:
                    if r["id"] == rid:
                        row = r
                        break
            if row is None:
                continue

            d = dict(row)
            d.pop("embedding", None)
            d["score"] = round(combined_score, 6)
            combined.append(d)

        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:limit]
