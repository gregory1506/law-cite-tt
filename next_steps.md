# Next Steps

Concrete, actionable items for continuing work here. Review this before starting any session.

## Priority

### Now
- Real auth for the customer app (citation-tool currently has a stub token gate in `src/lib/auth.js` — real login flow depends on the marketing site)
- Decide production Postgres hosting (self-managed VPS + Docker Compose vs. managed/Neon) per Phase H options in the plan doc

### Soon
- Build marketing site landing page (separate project, Cloudflare Pages)
- Citation formatter following T&T legal conventions (Cite tab is stubbed in citation-tool/src/routes/Cite.svelte)
- AI Chat tab for the customer app (stubbed in citation-tool/src/routes/Chat.svelte)

### Later
- Rate-limited background re-crawl for new revisions
- Subsidiary legislation and schedule support
- WebSocket streaming for long-running ingest operations

## Blocked
<!-- Items waiting on something external -->
- Marketing site design reference (user mentioned "maplejuris-like" look but that's a separate project)

## Completed

- Phase 0: Reconnaissance crawl — all 533 chapters, 10,060 PDFs extracted to markdown
- Phase 0: Golden test set — 30 entries, all validated
- Phase 1a: Section-aware chunker — 20 tests
- Phase 1b: Database schema + ingestion pipeline — 11 tests
- Phase 1c: Embedding + vector search — 13 tests
- Phase 1d: Golden set integration — all 30 entries retrievable
- Phase 1e: Full test suite — 61/61 passing
- Demo DB: 533 chapters, 4,989 versions, 407,008 chunks, all embedded
- FastAPI demo app with search/lookup/chapters/stats/landing page
- PDF source links on all results
- Documentation + Obsidian vault sync
- Private GitHub repo created
- Phase 2A: Directory reorg into backend/, citation-tool/, data/
- Phase 2B: Postgres + pgvector schema (data/init.sql), docker-compose db service
- Phase 2C: Async db_pg.py (asyncpg pool, FTS/vector/hybrid search)
- Phase 2D: FastAPI moved to backend/api/main.py, backed by db_pg
- Phase 2E: SQLite -> Postgres migration script, run against full 407,008-chunk dataset (exact count match)
- Phase 2F: Svelte customer app (citation-tool/) with working Explore tab (search/lookup/browse), stubbed Cite/Chat
- Phase 2G: Full docker-compose stack (db + api + citation-tool) verified end-to-end in browser
- Citation-tool dark legal-tech redesign: sidebar shell, stat tiles, responsive mobile navigation, polished Explore states, and styled Cite/Chat placeholders deployed to Cloudflare Workers
