# Next Steps

Concrete, actionable items for continuing work here. Review this before starting any session.

## Priority

### Now
- Launch the YC-style MVP in `docs/superpowers/plans/2026-07-30-yc-mvp.md`, beginning with `docs/superpowers/plans/2026-07-30-private-beta-authentication.md`, then run the defined 14-day beta experiment with 5–10 legal professionals
- Backfill case titles: mount the external SSD and re-run the loader with `--records /Volumes/Extreme SSD/law-cite-tt-data/case_law` so precedent answers name cases instead of `case:<hash>` handles
- Decide how case edges surface in the product UI: 'cited by N judgments' on statute/chapter views, precedent chain in the Chat tab

### Soon
- Audit and repair chapter/version associations in the migrated corpus; for example, bankruptcy text and sections are currently attached to the `30:50 Burial Grounds` catalog title in some historical rows
- Add GitHub Actions CI/CD: run tests, build and publish versioned `linux/amd64` API images to GHCR, deploy the selected image to the VPS over a restricted SSH key, verify `/api/health`, and retain the previous tag for rollback
- Add a separate citation-tool workflow that builds and deploys the frontend to Cloudflare Workers, then verifies the production URL
- Introduce Alembic migrations and run backward-compatible database migrations before switching the API container during backend deployments
- Make PostgreSQL ingestion idempotent before automating it: replace a version's chunks transactionally and enforce a unique constraint such as `(version_id, chunk_index)`
- Package reconciliation and ingestion as a dedicated Compose job, schedule it on the VPS, preserve original PDFs in R2/S3-compatible storage, and record source IDs/checksums so only new or changed documents are processed
- Add nightly off-host PostgreSQL backups with retention, checksum verification, monitoring, and periodic restore tests
- Build marketing site landing page (separate project, Cloudflare Pages)
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
- Lawyer/paralegal UX implementation phases 1-5: grouped provision search, legal metadata and version controls, safe contextual excerpts, legal-first search/lookup/browse workflows, frontend tests, and desktop/mobile browser QA
- Lawyer/paralegal UX production rollout: backend image `lawcite-api:ux-grouped-20260729` deployed on Hostinger and frontend Worker version `8b112881-4092-4202-bc49-41c54f2baa91` deployed and verified
- Frontend follow-up: persistent Clear search action and visible Chat coming-soon route deployed as Worker version `98837494-e732-4872-ac61-76751aadc8da`
- Cite validation MVP: source-backed chapter/section/date resolution, explicit found/not-found/ambiguous states, exact statutory text, official PDFs, full/short citation copy, and responsive desktop/mobile workflows deployed with API image `lawcite-api:a87fc7b` and Worker version `f74a010e-2548-4749-96c4-21f388a141c0`
- Agentic research assistant Phase A LIVE: grounded tool-calling Chat agent (`POST /api/chat`) over the statute API, Gemini via OPENAI_BASE_URL, grounding guardrail refuses unverifiable answers, server-rendered Sources. API image `lawcite-api:2cb6629`, Worker `fbfa1426-47df-4e08-ab4a-edb1d6fb512f`
- Agentic research assistant Phase B LIVE (precedent-chain agent): `cases`/`case_citations` in Postgres, loader `backend/scripts/load_case_edges.py`, `/api/cases`, `/api/cases/citing`, `/api/cases/{id}`, agent tools `citing_cases`/`search_cases`/`expand_case`. API image `lawcite-api:18bee46`. Titles pending SSD backfill

### Case-law layer (webOPAC) - current status

- [done] webOPAC crawler + CCJ crawler both live; sweep 2018-2024 COMPLETE: 3,344 judgments on SSD
- [done] CITES_STATUTE edges regenerated over full corpus: 7,914 edges / 2,236 case nodes / 3,354 cases
- [done] GraphRAG PoC complete (recall@20 = 70%); retriever integrates case edges both directions
- NEXT: optional historical band (1873-2017) for fuller citation coverage
- NEXT: decide how case edges surface in product - statute page 'cited by N judgments', reverse edges in Explore/API
- NEXT: refresh GRAPH_REPORT.md case-law numbers (now 7,914 edges, not 90)
- NEXT: reconcile chapter/version metadata mismatches (pre-existing queue item)
- NEXT: production authentication, authorization, rate limiting (release gate)
