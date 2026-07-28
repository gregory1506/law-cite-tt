# law-cite-tt

## Purpose

A legal citation engine for the **Laws of Trinidad and Tobago**. Sources statute data from the official Digital Law Library at https://laws.gov.tt/ttdll-web/revision/list. Answers "what did provision X say on date Y?" by chunking 10,060 PDF markdown files into 407,008 section-aware chunks with FTS5 + vector search.

## Status

**Phase 1 complete** — chunker, DB (SQLite + FTS5), embeddings, vector search, goldset validation, demo app. All 61 tests pass.

## Project architecture

Two surfaces (both in this repo):

1. **Customer app** (Svelte, planned) — logged-in experience: Explore (search/lookup/browse), Cite, Chat tabs
2. **Marketing site** (separate project, not yet built) — landing pages, pricing, sign-up

## Current codebase

- `scraper/` — Python modules: chunker, SQLite DB layer, embeddings (sentence-transformers), FTS + vector + hybrid search
- `demo_app.py` + `templates/index.html` — FastAPI demo (run: `uvicorn demo_app:app --reload`)
- `tests/` — 61 tests across 8 test files
- `docs/superpowers/` — specs, plans, decision records

## Data

- **Markdown:** `/Volumes/Extreme SSD/law-cite-tt-data/markdown/` — 533 chapters, 10,060 files
- **SQLite DB:** `/Volumes/Extreme SSD/law-cite-tt-data/law_cite.db` — 407,008 chunks, all embedded (384-dim)
- **Source PDFs:** `https://laws.gov.tt/ttdll-web/revision/download/{id}?type=act`

## Next move

See `next_steps.md` for priorities. Key upcoming work:
- Migrate SQLite → PostgreSQL + pgvector (plan at `docs/superpowers/plans/2026-07-27-postgres-switch-plan.md`)
- Build Svelte customer app with Explore/Cite/Chat tabs
- Deploy marketing site on Cloudflare Pages

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
