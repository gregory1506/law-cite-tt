# Plan: SQLite → PostgreSQL + pgvector + Docker Compose

## Product architecture — two surfaces

### 1. Marketing site (separate project)
Public-facing landing pages, pricing, blog, sign-up. Not built yet. Should follow a polished legal-tech look and feel (similar in vibe to maplejuris.com but completely independent). **Not covered by this plan.**

### 2. Customer app (this plan)
A logged-in Svelte app behind the marketing site's login wall. Three pillars:
- **Chat** — AI conversation about T&T laws (future)
- **Cite** — Generate properly formatted legal citations
- **Explore** — Search/browse the statute corpus (what's built so far)

```

marketing site (separate) ─── landing, pricing, sign-up
     │
     └── /app/ ───→ Svelte customer app
                       ├── Chat (future)
                       ├── Cite (future)
                       └── Explore ←─ built now
                             │
                             └── FastAPI ──→ PostgreSQL + pgvector
```

## Why move to PG

- Thread-safe concurrent reads without `check_same_thread` hack
- pgvector index for fast ANN (vs brute-force scan of 407k embeddings)
- Proper connection pooling
- Docker Compose gives one-command deploy

## Proposed stack

```
citation-tool (Svelte/Vite, nginx)  ──→  api (FastAPI, uvicorn)  ──→  db (PostgreSQL 16 + pgvector)
      :5173 / :80                            :8000                          :5432
```

## Phases

### Phase A — Directory reorg (30 min)
```
law-cite-tt/
├── backend/
│   ├── scraper/        # chunker, embed, db_pg (refactored)
│   ├── api/            # FastAPI app, routes
│   ├── requirements.txt
│   └── Dockerfile
├── citation-tool/      # demo/testing frontend (NOT the marketing site)
│   ├── src/            # Svelte components
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── init.sql        # schema + pgvector extension
├── docker-compose.yml
├── .env.example
└── tests/              # tests stay at root, run against test PG
```

### Phase B — PostgreSQL schema + pgvector (2 hr)

The SQLite `chunks` table had `embedding BLOB`. In PG:

```sql
CREATE EXTENSION vector;

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
```

**Key differences from SQLite:**
- `tsvector` GIN index replaces FTS5 (equivalent performance)
- `ivfflat` index on `vector(384)` replaces brute-force scan
- No need for separate FTS table — the GIN index is column-level

### Phase C — Refactor db.py → async (3 hr)

Current `db.py` is synchronous. Need an async layer:

- `backend/scraper/db_pg.py` — async with `asyncpg` + connection pool
  - `connect()` → `create_pool()`
  - `ingest_chapter()` → stream chunks in batch INSERT
  - `lookup_section()` → parameterized query with `to_tsvector`
  - `search_fts()` → `plainto_tsquery('english', $1)`
  - `search_vector()` → `ORDER BY embedding <=> $1 LIMIT $2`
  - `search_hybrid()` → weighted union or `ts_rank + (1 - cosine)`

The `SearchEngine` class merges into `db_pg.py` — single connection pool, no separate search module needed.

`embed.py` stays synchronous (model inference is CPU-bound, doesn't benefit from async). Call it via `run_in_executor` or just keep the FastAPI endpoint sync (thread pool handles it).

### Phase D — FastAPI refactor (1 hr)

- Move `demo_app.py` → `backend/api/main.py`
- Routes stay the same, just swap `get_db()` to return the async pool
- Middleware: CORS (for Svelte dev server on :5173)
- Health check endpoint

### Phase E — Migration script (1 hr)

A one-shot script that:
1. Reads all data from the existing SQLite DB
2. Connects to PostgreSQL
3. Bulk-inserts chapters, versions, chunks (including embeddings as `vector`)

```python
# backend/scripts/migrate_sqlite_to_pg.py
#
# Usage: python migrate_sqlite_to_pg.py --sqlite <path> --pg <dsn>
#
# Batches of 1000, with progress bar.
# Embeddings are already computed — just copy the float arrays.
```

### Phase F — Svelte customer app (3+ hr)

The customer app (logged-in experience behind the marketing site). Three tabs:
- **Explore** — search, lookup, chapter browser (port of current HTML/JS demo)
- **Cite** — citation formatter (future, stubbed tab)
- **Chat** — AI conversation about T&T laws (future, stubbed tab)

```
citation-tool/
├── src/
│   ├── App.svelte           # top nav: Explore | Cite | Chat, auth gate
│   ├── lib/
│   │   ├── api.js           # fetch() wrappers for /api/*
│   │   └── auth.js          # session/token handling (stub for now)
│   ├── routes/
│   │   ├── Explore.svelte   # search bar, results, tabs (port of current HTML)
│   │   ├── Cite.svelte      # citation form (stub)
│   │   └── Chat.svelte      # AI chat (stub)
│   └── components/
│       ├── SearchBar.svelte
│       ├── ResultCard.svelte
│       ├── LookupPanel.svelte
│       ├── ChapterBrowser.svelte
│       └── StatsBar.svelte
├── vite.config.js
├── Dockerfile
└── package.json
```

**Phase F.1** — Port the existing search/lookup/browse HTML/JS into Svelte (2 hr)
**Phase F.2** — Stub the Cite and Chat tabs with placeholder UIs (30 min)
**Phase F.3** — Add login gate + session handling (30 min, can be a simple token check against the API)

Build produces static files → served by nginx in production.

### Phase G — Docker Compose (30 min)

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./data/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_DB: lawcite
      POSTGRES_USER: lawcite
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lawcite"]
  
  api:
    build: ./backend
    depends_on:
      db: { condition: service_healthy }
    environment:
      PG_DSN: postgresql://lawcite:${PG_PASSWORD}@db:5432/lawcite
    ports:
      - "8000:8000"
  
  citation-tool:
    build: ./citation-tool
    ports:
      - "80:80"
    depends_on:
      - api

volumes:
  pgdata:
```

### Phase H — Git hosting + deploy (30 min)

**Git hosting (private):**
- **GitHub**: `gh repo create law-cite-tt --private` — simple, free for private repos
- **Forgejo**: Self-hosted on your own server. Runs as a Docker container, lightweight, mirrors the Gitea UI. Good if you want to keep everything on your infra. Either way works — the plan is repo-agnostic.

**Deploy options for the landing page (Cloudflare):**
- **Marketing site** → Cloudflare Pages (static HTML, free tier, custom domain)
- **Customer app + API** → needs a server for the FastAPI backend + PostgreSQL. Options:
  - Docker Compose on a VPS with Cloudflare Tunnel for HTTPS
  - Backend on a cheap VPS, frontend on Cloudflare Pages talking to the API
  - Neon (serverless Postgres with pgvector) + FastAPI on a small VM

The PostgreSQL + pgvector requirement rules out purely serverless for the data layer, so some VPS or managed PG is needed.

## Effort summary

| Phase | What | Time |
|-------|------|------|
| A | Directory reorg | 30 min |
| B | PG schema + pgvector | 2 hr |
| C | Refactor db.py → async | 3 hr |
| D | FastAPI refactor | 1 hr |
| E | Migration script | 1 hr |
| F | Svelte frontend | 3 hr |
| G | Docker Compose | 30 min |
| H | Deploy | 30 min |
| **Total** | | **~11.5 hr** |

## Risk & notes

- **pgvector index build** on 407k 384-d vectors takes ~30s. Query with `lists=100` is <10ms.
- **FTS equivalent**: PostgreSQL `to_tsvector('english', chunk_text)` with GIN index is not identical to FTS5 but close enough. We lose the `porter` stemmer — `english` config uses Snowball which is similar.
- **Embedding model stays the same**: `all-MiniLM-L6-v2` → `vector(384)`. No re-embedding needed.
- **Svelte frontend is optional**: The existing HTML/JS can be served by FastAPI directly for a quicker path. Svelte adds build step + dependency but gives cleaner component structure.
