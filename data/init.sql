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

CREATE TABLE cases (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT '',
    record_id       TEXT NOT NULL DEFAULT '',
    court           TEXT NOT NULL DEFAULT '',
    year            INT
);

CREATE INDEX idx_cases_title ON cases USING gin(to_tsvector('english', title));

CREATE TABLE case_citations (
    id              BIGSERIAL PRIMARY KEY,
    case_id         TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    chapter_number  TEXT NOT NULL,
    confidence      TEXT NOT NULL DEFAULT 'medium',
    method          TEXT NOT NULL DEFAULT 'REGEX',
    evidence        TEXT NOT NULL DEFAULT 'EXTRACTED',
    detail          TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_case_citations_chapter ON case_citations(chapter_number);
CREATE INDEX idx_case_citations_case ON case_citations(case_id);

-- Usage analytics (beta metrics): page views, dwell, searches, cite checks, chat turns.
-- Retention: purge rows older than ~400 days (retention policy set at first beta review).
CREATE TABLE events (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    type        TEXT NOT NULL,
    path        TEXT NOT NULL DEFAULT '',
    meta        JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_hash     TEXT NOT NULL DEFAULT '',
    user_agent  TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_created ON events(created_at);
CREATE INDEX idx_events_type ON events(type);

CREATE TABLE chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL DEFAULT '',
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT '',
    sources     JSONB NOT NULL DEFAULT '[]'::jsonb,
    mode        TEXT NOT NULL DEFAULT '',
    latency_ms  INT NOT NULL DEFAULT 0,
    ip_hash     TEXT NOT NULL DEFAULT '',
    user_agent  TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at);
