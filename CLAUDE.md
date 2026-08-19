# law-cite-tt

## Purpose

A legal citation engine for the **Laws of Trinidad and Tobago**. Sources statute data from the official Digital Law Library. Answers "what did provision X say on date Y?" by chunking 10,060 PDF markdown files into 407,008 section-aware chunks with FTS5 + vector search.


## Status

**Production research release live** — the Cloudflare-hosted Svelte app uses a
FastAPI, PostgreSQL 16, and pgvector backend on Hostinger. The production corpus
contains 533 chapters, 4,989 versions, 407,008 embedded chunks, and 7,914 case citation edges.
Research, Cite, and Agentic Chat are all live.

## Project architecture

Two main surfaces (both in this repo):

1. **Customer app** (`citation-tool/`) — Svelte 5 + Vite, deployed to Cloudflare Workers (Research, Cite, Chat live)
2. **API Backend** (`backend/`) — FastAPI backed by PostgreSQL 16 + pgvector on Hostinger VPS

## Current codebase

- `backend/scraper/` — ingestion, SQLite compatibility, PostgreSQL, embeddings, and search modules
- `backend/api/` — production FastAPI application & agentic tool handlers
- `backend/graphrag/` — case-law citation graph builder and edge extractors
- `citation-tool/` — production Svelte 5 customer app
- `tests/` — scraper, database, migration, and API coverage
- `docs/superpowers/` — specs, plans, decision records

## Data

- **Corpus Data:** 533 chapters, 10,060 files, 407,008 statutory chunks (384-dim embedded)
- **Case Law Graph:** 2,236 Judgments, 7,914 statute-case citation edges
- **PDF Proxy:** `/api/pdf/{download_id}` (proxied server-side via backend)

## Next move

See `next_steps.md` for priorities. Key upcoming work:
- Add production authentication, authorization, and rate limiting
- Reconcile known chapter/version metadata mismatches

## Key files for context

- `work_log.md` — chronological work record
- `lessons_learned.md` — gotchas and non-obvious discoveries
- `next_steps.md` — priority queue

## Git

- **Remote:** `https://github.com/gregory1506/law-cite-tt`
- **Branch:** `master`


## Virtual env

```sh
source .venv/bin/activate
uv pip install <pkg>  # use uv pip, not pip
```
