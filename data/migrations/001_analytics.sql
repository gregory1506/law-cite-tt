-- Usage analytics (beta metrics): page views, dwell, searches, cite checks, chat turns.
-- Retention: purge rows older than ~400 days (retention policy set at first beta review).
CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    type        TEXT NOT NULL,
    path        TEXT NOT NULL DEFAULT '',
    meta        JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_hash     TEXT NOT NULL DEFAULT '',
    user_agent  TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);

CREATE TABLE IF NOT EXISTS chat_messages (
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

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at);
