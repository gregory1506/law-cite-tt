CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chapters (
    id              SERIAL PRIMARY KEY,
    chapter_number  TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL
);

CREATE TABLE versions (
    id              SERIAL PRIMARY KEY,
    chapter_id      INT NOT NULL REFERENCES chapters(id),
    download_id     INT NOT NULL,
    version_label   TEXT DEFAULT '',
    as_at_date      DATE,
    UNIQUE(chapter_id, download_id)
);

CREATE TABLE chunks (
    id              SERIAL PRIMARY KEY,
    version_id      INT NOT NULL REFERENCES versions(id),
    chapter_number  TEXT NOT NULL,
    section_ref     TEXT NOT NULL,
    heading         TEXT DEFAULT '',
    chunk_text      TEXT NOT NULL,
    as_at_date      DATE,
    version_label   TEXT DEFAULT '',
    chunk_index     INT DEFAULT 0,
    embedding       vector(384)
);

CREATE INDEX idx_chunks_chapter_section ON chunks(chapter_number, section_ref);
CREATE INDEX idx_chunks_fts ON chunks USING gin(to_tsvector('english', chunk_text));
CREATE INDEX idx_chunks_vector ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
