from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from scraper.chunker import SectionChunk, chunk_markdown_file

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chapters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_number TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    current_id  INTEGER,
    classification TEXT DEFAULT '',
    year        TEXT DEFAULT '',
    act_number  TEXT DEFAULT '',
    commencement_date TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id  INTEGER NOT NULL REFERENCES chapters(id),
    download_id INTEGER NOT NULL,
    version_label TEXT DEFAULT '',
    as_at_date  TEXT DEFAULT '',
    enacted_date TEXT DEFAULT '',
    UNIQUE(chapter_id, download_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id  INTEGER NOT NULL REFERENCES versions(id),
    chapter_number TEXT NOT NULL,
    section_ref TEXT NOT NULL,
    heading     TEXT DEFAULT '',
    chunk_text  TEXT NOT NULL,
    as_at_date  TEXT DEFAULT '',
    version_label TEXT DEFAULT '',
    chunk_index INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_text,
    heading,
    section_ref,
    chapter_number,
    content='chunks',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TABLE IF NOT EXISTS version_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    from_version_id INTEGER NOT NULL REFERENCES versions(id),
    to_version_id   INTEGER NOT NULL REFERENCES versions(id),
    relationship    TEXT NOT NULL DEFAULT 'supersedes',
    confidence      REAL DEFAULT 1.0
);
"""


class LawCiteDB:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._schema_inited = False

    def connect(self):
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.row_factory = sqlite3.Row
            self._init_tables()
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_tables(self):
        for stmt in SCHEMA_SQL.split(";"):
            s = stmt.strip()
            if s:
                self._conn.execute(s + ";")
        self._conn.commit()

    def init_schema(self):
        self.connect()
        self._init_tables()

    @staticmethod
    def _chapter_from_folder(folder: str) -> tuple[str, str]:
        parts = folder.split("_")
        if parts[0].isdigit() and len(parts) > 2 and parts[1].isdigit():
            return f"{parts[0]}:{parts[1]}", " ".join(parts[2:])
        return folder.replace("_", " "), ""

    def ingest_chapter(self, chapter_folder: str, markdown_dir: Path):
        conn = self.connect()
        folder_path = markdown_dir / chapter_folder
        if not folder_path.is_dir():
            return 0

        chapter_number, title = self._chapter_from_folder(chapter_folder)

        conn.execute(
            "INSERT OR IGNORE INTO chapters (chapter_number, title) VALUES (?, ?)",
            (chapter_number, title),
        )
        (chapter_id,) = conn.execute(
            "SELECT id FROM chapters WHERE chapter_number = ?", (chapter_number,)
        ).fetchone()

        count = 0
        for md_file in sorted(folder_path.iterdir()):
            if md_file.name.startswith(".") or md_file.suffix != ".md":
                continue
            download_id = int(md_file.stem)

            chunks = chunk_markdown_file(md_file)
            if not chunks:
                continue

            conn.execute(
                "INSERT OR IGNORE INTO versions (chapter_id, download_id) VALUES (?, ?)",
                (chapter_id, download_id),
            )
            (version_id,) = conn.execute(
                "SELECT id FROM versions WHERE chapter_id = ? AND download_id = ?",
                (chapter_id, download_id),
            ).fetchone()

            for c in chunks:
                c.version_id = str(version_id)
                conn.execute(
                    """INSERT INTO chunks
                    (version_id, chapter_number, section_ref, heading, chunk_text, as_at_date, version_label, chunk_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        version_id,
                        c.chapter_number,
                        c.section_ref,
                        c.heading,
                        c.chunk_text,
                        c.as_at_date,
                        c.version_label,
                        c.chunk_index,
                    ),
                )

            conn.commit()
            count += len(chunks)

        return count

    def ingest_all(self, markdown_dir: Path, limit: int = 0):
        folders = sorted(
            d.name for d in markdown_dir.iterdir() if d.is_dir() and "_" in d.name
        )
        if limit:
            folders = folders[:limit]

        total = 0
        for folder in folders:
            n = self.ingest_chapter(folder, markdown_dir)
            total += n
            print(f"  {folder}: {n} chunks")

        return total

    def rebuild_fts(self):
        conn = self.connect()
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        conn.commit()

    def lookup_section(
        self, chapter: str, section: str, as_at_date: str | None = None,
        min_chars: int = 0,
    ) -> list[dict]:
        conn = self.connect()
        query = """
            SELECT c.chunk_text, c.chapter_number, c.section_ref, c.heading,
                   c.as_at_date, c.version_label, v.download_id
            FROM chunks c
            JOIN versions v ON c.version_id = v.id
            WHERE c.chapter_number = ? AND c.section_ref = ?
        """
        params: list = [chapter, section]
        if as_at_date:
            query += " AND c.as_at_date = ?"
            params.append(as_at_date)

        query += " ORDER BY c.as_at_date DESC NULLS LAST"
        rows = conn.execute(query, params).fetchall()
        results = [dict(r) for r in rows]
        if min_chars:
            results = [r for r in results if len(r["chunk_text"]) >= min_chars]
        return results
