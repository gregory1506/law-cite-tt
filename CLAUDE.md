# law-cite-tt

## Purpose

A legal citation engine for the **Laws of Trinidad and Tobago**. Sources statute data from the official Digital Law Library at https://laws.gov.tt/ttdll-web/revision/list. Answers "what did provision X say on date Y?" by chunking 10,060 PDF markdown files into 407,008 section-aware chunks with FTS5 + vector search.

## Status

**Production research release live** — the Cloudflare-hosted Svelte app uses a
FastAPI, PostgreSQL 16, and pgvector backend on Hostinger. The production corpus
contains 533 chapters, 4,989 versions, and 407,008 embedded chunks. Research
and Cite are live; the next release gate is production authentication and
authorization.

## Project architecture

Two surfaces (both in this repo):

1. **Customer app** (Svelte, live) — Explore and Cite are live; Chat is a placeholder
2. **Marketing site** (separate project, not yet built) — landing pages, pricing, sign-up

## Current codebase

- `backend/scraper/` — ingestion, SQLite compatibility, PostgreSQL, embeddings, and search modules
- `backend/api/` — production FastAPI application
- `citation-tool/` — production Svelte customer app
- `tests/` — scraper, database, migration, and API coverage
- `docs/superpowers/` — specs, plans, decision records

## Data

- **Markdown:** `/Volumes/Extreme SSD/law-cite-tt-data/markdown/` — 533 chapters, 10,060 files
- **SQLite DB:** `/Volumes/Extreme SSD/law-cite-tt-data/law_cite.db` — 407,008 chunks, all embedded (384-dim)
- **Source PDFs:** `https://laws.gov.tt/ttdll-web/revision/download/{id}?type=act`

## Next move

See `next_steps.md` for priorities. Key upcoming work:
- Add production authentication, authorization, and rate limiting
- Reconcile known chapter/version metadata mismatches

## Key files for context

- `work_log.md` — chronological work record
- `lessons_learned.md` — gotchas and non-obvious discoveries
- `next_steps.md` — priority queue

## Git

- **Remote:** `https://github.com/gregory1506/law-cite-tt` (private)
- **Branch:** `master`

## Virtual env

```sh
source .venv/bin/activate
uv pip install <pkg>  # use uv pip, not pip
```
