# Next Steps

Concrete, actionable items for continuing work here. Review this before starting any session.

## Priority

### Now
- **Phase 2: PostgreSQL migration.** Plan at `docs/superpowers/plans/2026-07-27-postgres-switch-plan.md`.
  - Phase A: Directory reorg (backend/, citation-tool/, data/)
  - Phase B: PG schema + pgvector
  - Phase C: Refactor db.py → async with asyncpg
  - Phase D: Move FastAPI into backend/api/
  - Phase E: Migration script (SQLite → PG)
  - Phase F: Svelte customer app (Explore/Cite/Chat)
  - Phase G: Docker Compose
  - Phase H: Deploy

### Soon
- Build marketing site landing page (separate project, Cloudflare Pages)
- Citation formatter following T&T legal conventions
- AI Chat tab for the customer app
- Auth/login gate for customer app

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
