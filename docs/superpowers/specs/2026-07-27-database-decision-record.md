# Database Decision Record

**Date:** 2026-07-27
**Context:** Phase 1 of law-cite-tt — selecting the storage and retrieval engine for a temporal legal citation engine covering the Laws of Trinidad and Tobago (533 chapters, ~10,000 versions, ~100,000 chunks).

## Decision

**SQLite + sqlite-vec in development; target Postgres + pgvector for production.**

Both use the same schema, same query patterns, same embedding store interface. The dev loop gets zero-infra iteration; the prod deployment path is clear.

## Requirements

- Store chapters, versions, chunks, and amendment/version edges
- Embedding similarity search (~100K vectors)
- Temporal queries: "what did section X say on date Y?" — date-range filtering on version
- Full-text search fallback (FTS5 or equivalent)
- Read-heavy API workload; writes only during batch import
- Single-developer iteration speed — no Docker, no cloud dependencies during dev

## Databases Considered

### Postgres + pgvector

| Pro | Con |
|-----|-----|
| Industry standard, battle-tested | Requires Docker or cloud instance for dev |
| Managed hosting (Neon, Supabase) with generous free tiers | Connection management overhead for a single-dev CLI tool |
| pgvector is mature, well-documented | Schema migrations need a tool (Alembic) |
| Concurrent writes scale well | Overkill for 100K vectors |

**Verdict:** Best for production. Painful for rapid local iteration where you might rebuild the schema 10 times in a session.

### SQLite + sqlite-vec

| Pro | Con |
|-----|-----|
| Zero infra — single file, no server, no Docker | sqlite-vec is newer (less battle-tested than pgvector) |
| Schema rebuilds are instant (drop and recreate) | Write concurrency is single-threaded (irrelevant here — writes are serial batch imports) |
| FTS5 is built-in, no extension management | No managed cloud offering (must migrate to Postgres for prod) |
| `sqlite-utils` provides a great CLI for inspection | — |
| 100K vectors is trivially fast | — |
| WAL mode handles concurrent reads | — |

**Verdict:** Best for development. Prod migration is a known, solved path (SQLite → Postgres is well-trodden).

### ChromaDB

| Pro | Con |
|-----|-----|
| Purpose-built for embeddings | Weak relational query support — temporal filters require client-side post-processing |
| Simple API | Persistence layer is opaque (hard to inspect or migrate) |
| Good for pure RAG prototypes | Schema-less design makes it hard to enforce referential integrity across chapters/versions/chunks |

**Verdict:** Wrong shape for this problem. Citation validation needs relational joins (chapter → version → chunk + temporal filter), not just vector search.

### Qdrant

| Pro | Con |
|-----|-----|
| Fast vector search, built-in payload filtering | Another service to run locally (Docker) |
| Payload filtering covers temporal queries | Overkill for 100K vectors |
| — | Two systems to keep in sync (Qdrant + SQLite for relational data) |

**Verdict:** Adds operational complexity without benefit at this scale.

### Neo4j

| Pro | Con |
|-----|-----|
| Natural fit for multi-hop amendment chains | Massive operational overhead for what amounts to date-range joins |
| MapleJuris uses it | The T&T corpus is 533 chapters, not 4.4M nodes — a graph DB is a cannon for a sparrow |
| — | SQL recursive CTEs handle shallow version chains just fine |

**Verdict:** Not justified. The version graph is shallow (one chapter → N versions → linear chain). SQLite recursive CTEs or simple `ORDER BY as_at_date DESC LIMIT 1` queries cover every temporal query we need.

### DuckDB

| Pro | Con |
|-----|-----|
| Fast analytical queries on parquet/CSV | Poor concurrent read performance (designed for analytics, not serving) |
| Good for ETL staging (as noted in the architecture spec) | No vector extension as mature as sqlite-vec |
| — | Not a serving database |

**Verdict:** Keep as ephemeral ETL staging only (already in the architecture spec). Not for the serving layer.

## Schema (SQLite, target Postgres)

```sql
-- Core entities
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY,
    chapter_number TEXT NOT NULL,       -- "8:08"
    title TEXT NOT NULL,
    classification TEXT,
    year TEXT,
    act_number TEXT,
    commencement_date TEXT,
    current_id INTEGER UNIQUE NOT NULL  -- laws.gov.tt internal ID
);

CREATE TABLE versions (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    download_id INTEGER NOT NULL,       -- laws.gov.tt download ID
    label TEXT,                          -- "Original Act", "Revised Edition 2006", etc.
    as_at_date TEXT,                     -- "as at December 31st 2016"
    enacted_date TEXT,                   -- parsed from metadata
    superseded_by INTEGER REFERENCES versions(id),
    UNIQUE(chapter_id, download_id)
);

-- Cross-reference/amendment edges
-- Captures "Version A amended by Act X (Version B)" relationships
CREATE TABLE version_edges (
    id INTEGER PRIMARY KEY,
    from_version_id INTEGER NOT NULL REFERENCES versions(id),
    to_version_id INTEGER NOT NULL REFERENCES versions(id),
    relationship_type TEXT NOT NULL,     -- 'supersedes', 'amends', 'repeals', 'references'
    confidence REAL DEFAULT 1.0
);

-- Chunks with embeddings
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES versions(id),
    chunk_index INTEGER NOT NULL,       -- position within version
    heading TEXT,                        -- "Part II — Administration", or NULL if none
    section_ref TEXT,                    -- "Section 12", NULL if preamble
    chunk_text TEXT NOT NULL,
    embedding BLOB,                      -- float32 vector, stored flat
    extraction_method TEXT DEFAULT 'native',  -- 'native' | 'ocr'
    is_garbage INTEGER DEFAULT 0,        -- 1 if below quality threshold
    UNIQUE(version_id, chunk_index)
);

-- Full-text search
CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_text, heading, section_ref, content=chunks);
```

### Key query patterns

**Primary: "What did section X of chapter Y say on date Z?"**
```sql
SELECT c.chunk_text, v.as_at_date, v.label
FROM chunks c
JOIN versions v ON c.version_id = v.id
JOIN chapters ch ON v.chapter_id = ch.id
WHERE ch.chapter_number = '8:08'
  AND c.section_ref = 'Section 12'
  AND v.as_at_date <= '1950-06-01'
ORDER BY v.as_at_date DESC
LIMIT 1;
```

**Amendment chain: "Show me every version of section X"**
```sql
SELECT c.chunk_text, v.as_at_date, v.label
FROM chunks c
JOIN versions v ON c.version_id = v.id
JOIN chapters ch ON v.chapter_id = ch.id
WHERE ch.chapter_number = '8:08'
  AND c.section_ref = 'Section 12'
ORDER BY v.as_at_date ASC;
```

**Vector search: "Find chunks similar to this query text, filtered by date"**
```sql
SELECT c.chunk_text, v.as_at_date,
       vec_distance_cosine(c.embedding, ?) AS distance
FROM chunks c
JOIN versions v ON c.version_id = v.id
JOIN chapters ch ON v.chapter_id = ch.id
WHERE ch.chapter_number = '8:08'
  AND v.as_at_date <= ?
ORDER BY distance
LIMIT 5;
```

## Prod Migration Path

When ready to deploy:

1. Dump SQLite: `.dump` or write a migration script
2. Re-embed into Postgres + pgvector (same schema, trivial mapping)
3. Swap connection string in the API config

No code changes in the API layer if we abstract the connection behind a repository interface.

## Tests Required

See the comprehensive test suite in the architecture discussion:
- Retrieval accuracy (recall@K with temporal filter)
- Temporal correctness (version resolution, amendment chain ordering, gap detection)
- Chunking quality (section boundary recall/precision, heading anchoring, garbage rejection)
- Latency (p50/p99 for citation and temporal queries)
- Robustness (idempotent re-import, partial failure recovery, concurrent readers, full re-index)
