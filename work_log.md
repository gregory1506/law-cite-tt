# Work Log

Chronological record of work done in this folder.

## Format

Each entry:
```
## [YYYY-MM-DD HH:MM] <short-title>

**What was done:**
- Bullet points of changes

**Files touched:**
- list of files

**Status:** complete | partial | blocked
```

## Entries

## [2026-07-26] Phase 0 — Reconnaissance crawl, PDF extraction, OCR

**What was done:**
- Built recon.py: crawls laws.gov.tt, downloads all PDFs, extracts to markdown via pdfplumber
- All 533 chapters crawled, 10,060 PDFs extracted to markdown
- Skip-if-complete logic: `.recon_done` markers per chapter directory
- Robust download handling: bad_download (non-PDF) + download_error (connection reset/timeout) with report rows
- 4 scanned PDFs OCR'd via pytesseract + pdf2image
- Golden test set: 30 entries (10 simple, 10 temporal, 5 nested, 5 edge), all validated (30/30 pass)

**Files touched:**
- scraper/recon.py, scraper/catalog.py, scraper/detail.py, scraper/pdf_to_markdown.py, scraper/http_client.py
- tests/test_recon.py, tests/test_catalog.py, tests/test_detail.py, tests/test_pdf_to_markdown.py, tests/test_http_client.py
- tests/fixtures/golden_set.json
- docs/superpowers/specs/2026-07-27-database-decision-record.md (7 DB alternatives compared)
- docs/superpowers/specs/2026-07-27-testing-framework.md (6 metric categories)
- docs/superpowers/specs/2026-07-27-phase-1-implementation-plan.md

**Status:** complete

## [2026-07-27] Phase 1a — Section-aware chunker

**What was done:**
- Built scraper/chunker.py: parses markdown files into section-aware chunks
- Handles 3 section formats: marginal-title-first, number-first, mixed
- Skips Arrangement of Sections, handles multi-line marginal titles
- Extracts metadata (chapter, version, as_at_date) from file headers
- Filters out arrangement entry artifacts
- 20 tests pass covering all section formats, temporal variants, metadata extraction

**Files touched:**
- scraper/chunker.py
- tests/test_chunker.py (20 tests)

**Status:** complete

## [2026-07-27] Phase 1b — Database schema + ingestion pipeline

**What was done:**
- Built scraper/db.py: SQLite schema with FTS5, chapters/versions/chunks/version_edges tables
- Temporal-aware lookup_section with date filtering
- DB auto-creates schema on first connect()
- 11 DB tests pass (schema, ingestion, lookup, golden set)

**Files touched:**
- scraper/db.py
- tests/test_db.py (11 tests)

**Status:** complete

## [2026-07-27] Phase 1c — Embedding + vector search

**What was done:**
- Built scraper/embed.py: embed_text, embed_batch, cosine_similarity, pack/unpack_embedding, embed_chunks_from_db
- Uses all-MiniLM-L6-v2 (384-dim normalized embeddings)
- Built scraper/search.py: SearchEngine with fts_search, vector_search, hybrid_search (weighted fusion)
- 13 search tests pass
- Demo DB on external drive: 533 chapters, 4,989 versions, 407,008 chunks ingested in 29s
- FTS5 index rebuilt
- All 407k chunks embedded in 12.6 min
- Full pipeline verified: FTS, vector, and hybrid search all working

**Files touched:**
- scraper/embed.py
- scraper/search.py
- tests/test_search.py (13 tests)
- /Volumes/Extreme SSD/law-cite-tt-data/law_cite.db

**Status:** complete

## [2026-07-27] Full test suite — all 61 tests pass

**What was done:**
- Final test run: 61/61 tests pass across all modules
- No regressions introduced during Phase 1

**Status:** complete

## [2026-07-27] FastAPI demo app + PDF source links

**What was done:**
- Built demo_app.py with 6 API endpoints (search, lookup, chapters, stats, landing page)
- Built templates/index.html: search (FTS/vector/hybrid), section lookup with version timeline, chapter browser
- Added pdf_url to all results linking to laws.gov.tt PDF download
- Pre-warmed embedding model at startup to avoid cold-start delay
- Default search mode changed to FTS (instant) instead of hybrid (loads ML model)
- Fixed SQLite thread safety (check_same_thread=False) for FastAPI + TestClient
- Re-ingested DB: fixed chapter number extraction (was `01:Prevention:of:Crimes` → now `10:01`)
- All 61 tests still pass

**Files touched:**
- demo_app.py, templates/index.html
- scraper/db.py, scraper/search.py
- /Volumes/Extreme SSD/law-cite-tt-data/law_cite.db (re-created)

**Status:** complete

## [2026-07-27] Documentation + Obsidian vault sync

**What was done:**
- Wrote comprehensive work_log.md (6 entries), lessons_learned.md (7 entries), next_steps.md
- Created PostgreSQL migration plan: `docs/superpowers/plans/2026-07-27-postgres-switch-plan.md`
- Synced all lessons + structure to Obsidian vault (Greg Work/Repo-Graph/law-cite-tt/)
- Updated CLAUDE.md with current project state for future LLM handoff
- Pushed to private GitHub repo: https://github.com/gregory1506/law-cite-tt

**Files touched:**
- CLAUDE.md, work_log.md, lessons_learned.md, next_steps.md
- docs/superpowers/plans/2026-07-27-postgres-switch-plan.md
- Obsidian vault (5 new lesson notes, updated Structure.md, Overview.md, _Index.md)

**Status:** complete

## [2026-07-28] Phase 2 — Full Postgres + pgvector migration, Svelte customer app, Docker Compose

**What was done:**
- Phase A: moved scraper/ and run_recon.py into backend/, requirements.txt into backend/, pytest pythonpath extended so imports are unchanged
- Phase B: wrote data/init.sql (chapters/versions/chunks with GIN + ivfflat indexes), stood up pgvector/pg16 via docker-compose
- Phase C: built backend/scraper/db_pg.py — async asyncpg-backed store merging the old LawCiteDB + SearchEngine (ingest, lookup_section, search_fts/vector/hybrid)
- Phase D: moved demo_app.py -> backend/api/main.py, swapped in db_pg, added lifespan pool management, CORS, /api/health, backend/Dockerfile
- Phase E: wrote backend/scripts/migrate_sqlite_to_pg.py; ran it against the full 407,008-chunk database — chapters=533 versions=4989 chunks=407008 embedded=407008, exact match to source
- Phase F: scaffolded citation-tool/ (Vite + Svelte 5) with Explore (search/lookup/browse, ported from templates/index.html), stubbed Cite/Chat tabs, stub auth gate
- Phase G: wired db+api+citation-tool into docker-compose.yml; verified full stack via `docker compose up` in a real browser
- Ran the whole thing in Chrome via chrome-devtools MCP against real data at every phase boundary, not just pytest

**Files touched:**
- backend/ (new: scraper/, api/, scripts/, Dockerfile, requirements.txt)
- data/init.sql, docker-compose.yml, .env.example
- citation-tool/ (new Svelte app + Dockerfile)
- tests/test_db_pg.py, tests/test_api.py, tests/test_migrate_sqlite_to_pg.py (12 new tests, 73 total)

**Status:** complete (on worktree branch `worktree-phase2-postgres`, not yet merged to master)

## [2026-07-29 11:48] Citation-tool dark frontend redesign

**What was done:**
- Completed the dark legal-tech redesign across the app shell, Explore components, and Cite/Chat placeholders
- Corrected button contrast, inactive tab legibility, mobile sidebar overflow/brand overlap, and result highlight colors
- Verified desktop and 390px layouts in Playwright, including search, lookup, browse, login, and navigation states
- Built against the production API and deployed Cloudflare Worker version `f9ac7d82-d394-46ef-9a20-bf9f14cc3788`

**Files touched:**
- citation-tool/src/App.svelte
- citation-tool/src/components/ChapterBrowser.svelte, LookupPanel.svelte, ResultCard.svelte, SearchBar.svelte, StatsBar.svelte
- citation-tool/src/routes/Chat.svelte, Cite.svelte, Explore.svelte
- work_log.md, lessons_learned.md, next_steps.md

**Status:** complete
