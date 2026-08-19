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

## [2026-07-29] VPS backend and PostgreSQL deployment planning

**What was done:**
- Chose the production topology: Cloudflare-hosted frontend with FastAPI, PostgreSQL 16, and pgvector on the self-managed VPS
- Wrote an executable deployment plan with the target backend-only Compose file, environment, data transfer, health gates, backups, operations, and rollback
- Validated the proposed Compose YAML using `docker compose config --quiet`

**Files touched:**
- docs/superpowers/plans/2026-07-29-vps-backend-postgres-deployment.md
- next_steps.md
- work_log.md
- lessons_learned.md

**Status:** complete

## [2026-07-29] Hostinger Compose manually runbook

**What was done:**
- Adapted the VPS deployment to Hostinger Docker Manager's Compose manually workflow
- Split deployment into database-only restore and verified full-stack update stages
- Added exact image transfer, hPanel navigation, Compose YAML, validation gates, backups, updates, rollback, and troubleshooting steps
- Validated both copy-paste Compose stages with Docker Compose

**Files touched:**
- docs/superpowers/plans/2026-07-29-hostinger-compose-manually-runbook.md
- docs/superpowers/plans/2026-07-29-vps-backend-postgres-deployment.md
- next_steps.md
- work_log.md
- lessons_learned.md

**Status:** complete

## [2026-07-29 17:18] Lawyer and paralegal research workflow implementation

**What was done:**
- Added backward-compatible grouped provision search with legal metadata, historical cutoffs, deterministic pagination, and exact version lookup
- Rebuilt the Svelte research workflow around scannable provisions, safe excerpts, version selection, plain-language search modes, filters, lookup, and chapter browsing
- Added backend and frontend regression tests, then verified desktop and mobile workflows against the full PostgreSQL corpus
- Fixed migrated historical-date fallback and browse-to-filter stale results discovered during live browser QA

**Files touched:**
- backend/api/, backend/scraper/db_pg.py, tests/test_api.py, tests/test_db_pg.py
- citation-tool/src/, citation-tool/package.json, citation-tool/vite.config.js
- docs/superpowers/plans/2026-07-29-lawyer-paralegal-ux-implementation.md, next_steps.md, lessons_learned.md

**Status:** partial — implementation and QA complete; backend-first VPS and frontend deployment remain

## [2026-07-29 17:46] Lawyer and paralegal UX production rollout

**What was done:**
- Verified the new grouped-search image healthy on Hostinger while preserving `lawcite-api:ce84113` for rollback
- Built the frontend against `https://srv1629323.hstgr.cloud` and deployed Cloudflare Worker version `8b112881-4092-4202-bc49-41c54f2baa91`
- Verified production exact search and historical cutoff at desktop and mobile viewports
- Confirmed zero production console errors and no 390px mobile overflow

**Files touched:**
- citation-tool/dist/ build output
- docs/superpowers/plans/2026-07-29-lawyer-paralegal-ux-implementation.md
- next_steps.md, work_log.md

**Status:** complete

## [2026-07-29 17:52] Clear search and Chat placeholder follow-up

**What was done:**
- Added a persistent Clear action that resets query, chapter, date, and displayed results
- Restored Chat navigation with a responsive coming-soon view while keeping Cite hidden
- Added regression coverage and verified desktop/mobile layouts with zero console errors
- Deployed Cloudflare Worker version `98837494-e732-4872-ac61-76751aadc8da`

**Files touched:**
- citation-tool/src/App.svelte, citation-tool/src/routes/Explore.svelte, citation-tool/src/routes/Chat.svelte
- citation-tool/src/components/SearchBar.svelte, citation-tool/src/App.test.js, citation-tool/src/components/SearchBar.test.js
- next_steps.md, work_log.md

**Status:** complete

## [2026-07-30 19:10] Source-backed Cite validation production rollout

**What was done:**
- Added deterministic chapter/section/date resolution with explicit found, not-found, and ambiguous API states
- Built the responsive Cite workflow with exact source text, official PDFs, historical labels, and full/short copy controls
- Verified 87 production-relevant Python tests, 12 frontend tests, real-corpus desktop/mobile flows, CORS, and existing Research behavior
- Deployed Hostinger image `lawcite-api:a87fc7b` and Cloudflare Worker version `f74a010e-2548-4749-96c4-21f388a141c0`, retaining the prior API image for rollback

**Files touched:**
- backend/api/citations.py, backend/api/main.py, backend/api/models.py, backend/scraper/db_pg.py
- citation-tool/src/App.svelte, citation-tool/src/lib/api.js, citation-tool/src/routes/Cite.svelte
- tests/test_citations.py, tests/test_api.py, tests/test_db_pg.py, citation-tool/src/routes/Cite.test.js
- README.md, CLAUDE.md, next_steps.md, lessons_learned.md

**Status:** complete

## [2026-07-30 19:40] Private beta authentication planning

**What was done:**
- Selected Cloudflare Access email one-time PINs with an explicit beta allowlist
- Designed a same-origin Worker API gateway with FastAPI JWT verification and rate limiting
- Documented deployment ordering, production acceptance checks, and rollback

**Files touched:**
- docs/superpowers/plans/2026-07-30-private-beta-authentication.md
- work_log.md, lessons_learned.md, next_steps.md

**Status:** complete

## [2026-07-30 20:25] YC-style MVP definition

**What was done:**
- Defined LawCite's narrow MVP promise around fast, verifiable T&T statutory research
- Scoped a 2–4 day beta-readiness build and a 14-day experiment with 5–10 legal professionals
- Added activation, usage, task-integrity, product-pull, and proceed/iterate/reconsider decision criteria
- Explicitly deferred Chat, agents, law graphs, matters, case law, drafting, and billing

**Files touched:**
- docs/superpowers/plans/2026-07-30-yc-mvp.md
- work_log.md, next_steps.md

**Status:** complete

## [2026-08-03 15:00] GraphRAG idea graph from the existing chunk cache

**What was done:**
- Built a GraphRAG over the Laws of TT entirely from the existing `law_cite.db` (no re-embedding): 23,175 idea nodes (chapter|section, embeddings averaged across versions), 533 chapter nodes, 136 cross-chapter concept nodes
- Extracted audited edges: PART_OF / CROSS_REF / MENTIONS (EXTRACTED) + SEMANTIC (INFERRED via top-k cosine, blocked matmul to avoid a 23k x 23k matrix)
- Ran greedy-modularity community detection -> 535 clusters; persisted idea embeddings as .npy for fast retrieval
- Built a BFS/DFS semantic retriever (query embedded with the same all-MiniLM-L6-v2 model) and a golden-set recall harness
- Idea-node recall@20 = 70% against the 30-entry golden set; "police supervision after conviction" returns Prevention of Crimes 10:01|5 at rank 1
- Exported graph.json, clusters.json, interactive graph.html, Neo4j graph.cypher, GRAPH_REPORT.md

**Files touched:**
- backend/graphrag/build.py, backend/graphrag/retrieve.py, backend/graphrag/eval_golden.py, backend/graphrag/export_viz.py
- graphify-out/ (graph.json, clusters.json, graph.html, graph.cypher, idea_embeddings.npy, idea_ids.json, GRAPH_REPORT.md)
- docs/superpowers/specs/graphrag-report.md

**Status:** complete

## [2026-08-03 16:00] CCJ case-law layer (crawler + CITES_STATUTE extractor)

**What was done:**
- Recon against ccj.org: robots.txt is permissive (sitemap published); judgment posts are decision summaries/metadata, not full PDFs — og:description carries the fuller case note on older pages
- Built a controlled + anonymized crawler (backend/scraper/case_crawl.py): consumes only the category RSS feeds the site advertises; fixed honest research UA, no IP rotation / proxies / cookie jars / fingerprint evasion; 3s rate limit, --limit cap, idempotent JSONL, PII-free, hashed node ids, utm params stripped
- Built the CITES_STATUTE edge extractor (backend/graphrag/case_edges.py): resolves Ch./Cap. NN:NN (REGEX) and act-title names (TITLE_MATCH) against the idea graph, tagged evidence/method/confidence
- Added tests/test_case_law.py (7 tests); full suite 38 passing
- Did NOT run a live crawl (bounded offline dry-run only) — real RAG runs are left to the user against the live site

**Files touched:**
- backend/scraper/case_crawl.py, backend/graphrag/case_edges.py, tests/test_case_law.py
- graphify-out/GRAPH_REPORT.md (appended case-law section)

**Status:** complete

## [2026-08-03 17:00] Wire case edges into retriever + fix dangling PART_OF edges

**What was done:**
- Retriever auto-loads graphify-out/case_edges.json; `_expandable` makes chapters transit-only bridges (case -> chapter -> idea) so a case node expands into its cited chapters' ideas without ideas fanning out into whole chapters
- Fixed a dangling-edge bug: PART_OF edges used the bare chapter number ("10:01") as source while chapter nodes are id ("chapter:10:01") — all 23,143 PART_OF edges referenced nonexistent nodes. Traversal stopped at chapters; recall/stat metrics were unaffected so the eval harness hid it
- Added a post-build invariant in build.py that fails loudly on any dangling edge
- Rebuilt graph.json/httpserver (0 dangling), re-exported graph.html + graph.cypher; recall unchanged at 70% (Node-embedding-based)
- Logged lessons: edge-endpoint validation at build time; chapters-as-transit

**Files touched:**
- backend/graphrag/build.py, backend/graphrag/retrieve.py, backend/graphrag/eval_golden.py, exported graphify-out/graph.json, clusters.json, graph.html, graph.cypher
- work_log.md, lessons_learned.md

**Status:** complete

## [2026-08-03 17:30] WebOPAC judgments recon + crawler + one-year pilot

**What was done:**
- Recon: ttlawcourts.org homepage redirects to Outlook /owa/ (dead end); the real source is the Judiciary webOPAC — webopac.ttlawcourts.org (IIS + Minisys minisa.dll OPAC), a searchable catalog exposing full-text judgment PDFs under /LibraryJud/Judgments/<court>/<judge>/<year>/<file>.pdf
- Mapped the enumeration contract: load the direct-search form, parse its per-session action URL (session id rotates on every load), POST pub_yr_deldate=<year>; RECLIST result pages; each RECORD page carries the PDF link (as an href and as a bare URL in the "Full text" field)
- Built backend/scraper/webopac_crawl.py mirroring case_crawl.py etiquette (honest UA, no cookies/proxies/PII, RateLimitedClient delay, idempotent). It dedupes RECLIST pagination by the page-offset segment because session ids rotate on every response — full-URL dedup caused an infinite loop
- Storaged as PDF + text + parsed line: raw PDFs in case_law/webopac_pdfs/<year>/, one JSON-L record in case_law/webopac.jsonld (text via scraper.pdf_to_markdown)
- Ran a one-year pilot (2023): 606 record URLs enumerated; cap 5 PDFs downloaded and parsed end-to-end (20k-42k chars each, native so unprovided text -> not scanned), artifacts on the SSD

**Files touched:**
- backend/scraper/webopac_crawl.py (new)
- /Volumes/Extreme SSD/law-cite-tt-data/case_law/ (webopac_pdfs/2023/, webopac.jsonld)
- lessons_learned.md, next_steps.md

**Status:** complete (pilot); full-index sweep pending

## [2026-08-03 18:00] WebOPAC crawl scaled + CITES_STATUTE edges wired into graph

**What was done:**
- Fixed crawler idempotency: record_id was a per-run counter; now it is a sha256 hash of the source RECORD url (matches CCJ convention), so re-runs skip and edge sources are stable
- Reconciled case_edges.py to read both corpora: it now globs *.json*, normalizes CCJ (id/body) and webOPAC (record_id text combined by code) records
- Ran a scaled 2023 crawl (cap 40, delay 1.0s) -> 40 judgments downloaded+parsed (3k-226k chars, none scanned); ~11 realized CoA/HC PDFs incl. multi-year decisions
- Regenerated CITES_STATUTE edges across the merged corpus (40 webvalidity + 10 CCJ = 50 cases, 27 case nodes, 90 edges; 38 REGEX + 52 TITLE_MATCH; 47 high / 35 med / 8 low)
- Verified integration: retriever loads case_coledges (90), and a case seed traverses case -> chapter -> statutory ideas (e.g. case:8eec.. -> chapter:5:01 Arbitration -> its sections) — the design's "case as transit entry" works end-to-end

**Files touched:**
- backend/scraper/webopac_crawl.py (stable record_id)
- backend/graphrag/case_edges.py (dual-format load)
- graphify-out/case_edges.json (90 edges)
- /Volumes/Extreme SSD/law-cite-tt-data/case_law/webopac.jsonld (40), webocr p pdf repository

**Status:** complete; full-index sweep (all years, no cap) remains next

## [2026-08-03 18:45] GraphRAG proof-of-concept complete (with case-law edges)

**What was done:**
- Confirmed the GraphRAG PoC is complete end-to-end: graph build (23k idea nodes / 125k edges / 535 clusters), semantic retriever, and golden recall
- Idea-node recall@20 against the 30-entry golden set: 19/27 = 70% (3 skipped - no section ref)
- Wired the judicial case-law layer on top and re-verified both traversal directions:
  - statute query seeds surface the relevant ideas (e.g. "arbitration agreement enforcement" -> 5:01|20, 5:01|3, 54:70|82)
  - case seed walks case -> cited chapter -> its ideas (e.g. case:8eec.. -> chapter:5:01 -> sections)
- 90 CITES_STATUTE edges (38 REGEX + 52 TITLE_MATCH; 47 high/35 med/8 low) over 50 merged cases / 27 case nodes; retriever auto-loads case_enorte.json
- Updated graphify-out/GRAPH_REPORT.md: case-law section now documents BOTH CCJ and webOPAC sources, the 90-edge result, upstream years, and the modern 70% recall
- DIAGNOSED a false alarm: the "0 results/year" probes were parsing raw HTML where a tag splits "Search Results" from ":606"; the live OPAC index actually spans 1873-2024 (dense 1980-2024, 200-650/yr)

**Files touched:**
- graphify-out/GRAPH_REPORT.md (updated case-law + evaluation sections)
- work_log (this), next_steps.md

**Status:** PoC complete; full webOPAC sweep (1873-2024) is a background run

## [2026-08-03 20:30] webOPAC full-index sweep COMPLETE: 3,344 judgments, 7,914 case edges

**What was done:**
- Completed the webOPAC judgment sweep for 2018-2024 (all 7 dense years): 3,344 judgments downloaded + parsed to the SSD (2018: 529, 2019: 476, 2020: 505, 2021: 380, 2022: 386, 2023: 537, 2024: 525)
- Ran a resilience fix after the first crash: the crawl died mid-2020 on an unhandled SSLError from an external-host PDF (www.ttparliament.org); fetch_pdf and the per-record block now catch request/parse errors and skip instead of dying. Relaunched idempotently from 2020; completed to 2024
- Regenerated CITES_STATUTE edges over the full corpus: 3,354 cases -> 2,236 case nodes -> 7,914 edges (3,284 REGEX + 4,630 TITLE_MATCH; 4,230 high / 2,957 medium / 727 low)
- Top cited chapters: 7:08 (635), 4:01 (488), 56:03 (323), 15:01 (245), 7:09 (240), 81:01 (231)
- Verified retriever integration at full scale: 7,914 case edges load, graph = 26,080 nodes; statute seeds and case -> chapter -> idea traversal both still work

**Files touched:**
- backend/scraper/webopac_crawl.py (resilience fix, already pushed as 1b43fe0)
- graphify-out/case_edges.json (regenerated, gitignored)
- work_log.md, next_steps.md

**Status:** complete (2018-2024); historical 1873-2017 band remains optional

## [2026-08-03 21:00] Housekeeping: docs updated for sweep completion

**What was done:**
- lessons_learned.md: added two entries from this session's operational learnings
  - validate crawl resilience by running at scale (unhandled SSLError from an external-host PDF killed the first sweep; wrap per-record ops and relaunch idempotently; use python -u for unbuffered logs)
  - a "0 results" probe can be a parser bug, not a real zero (count regex hit a tag between "Search Results" and ":606")
- next_steps.md: removed stale done items, added a "Case-law layer (webOPAC) - current status" section with forward-looking NEXT items (historical band 1873-2017, case edges surfacing in product, GRAPH_REPORT.md refresh, metadata reconciliation, auth/rate-limit release gate)

**Files touched:**
- lessons_learned.md, next_steps.md

**Status:** complete

## [2026-08-18 21:50] Agentic Chat Phase A — grounded tool-calling agent over the statute API

**What was done:**
- Added the openai SDK + httpx; agent config via OPENAI_API_KEY / OPENAI_BASE_URL / LAWCITE_AGENT_MODEL (Gemini-compatible endpoint works unchanged)
- Built backend/api/tools.py: four in-process tools wrapping LawCitePGDB (search_provisions, lookup_section, resolve_citation, list_chapters), each returning LLM-facing text + pinned source records (chunk/lookup/chapter ids, official PDF URLs)
- Built backend/api/agent.py: up to 8 tool iterations, OpenAI function-calling, structured JSON reply {answer, source_ids}, and a grounding guardrail that refuses answers whose source_ids are unknown or empty; conversational replies pass through only when no tools were used
- Added POST /api/chat (ChatRequest/ChatResponse models) — returns unconfigured until OPENAI_API_KEY is set
- Replaced the Chat placeholder with a real message UI: history, thinking state, refusal banner, server-rendered Sources with official PDF links, Enter-to-send composer
- Tests: 21 new backend (agent loop with scripted LLM, tool formatting with fake DB, endpoint wiring) + 3 new frontend (grounded render, refusal banner, request failure); updated App.test.js for the new Chat empty state
- Verified: backend unit suite green, full frontend suite 15/15, production build clean

**Files touched:**
- backend/api/agent.py, backend/api/tools.py, backend/api/main.py, backend/api/models.py (new)
- backend/requirements.txt, .env.example
- citation-tool/src/routes/Chat.svelte, citation-tool/src/lib/api.js, citation-tool/src/routes/Chat.test.js, citation-tool/src/App.test.js
- tests/test_agent.py, tests/test_tools.py (new)
- docs/superpowers/plans/2026-08-18-agentic-research-assistant.md

**Status:** partial — code + tests complete; production deploy (image rebuild + OPENAI_API_KEY env on VPS + wrangler deploy) and live model verification remain

## [2026-08-18 23:15] Agentic Chat Phase A production rollout (VPS + Cloudflare)

**What was done:**
- Deployed the agentic Chat end-to-end against production: image `lawcite-api:2cb6629` built on the VPS (/root/lawcite-build), compose /docker/lawcite/docker-compose.yml tagged and recreated; Gemini keys wired via hPanel env `${GEMINI_API_KEY}` → container OPENAI_API_KEY/OPENAI_BASE_URL/LAWCITE_AGENT_MODEL
- Fixed two live-failures discovered during rollout:
  - Gemini 3.x OpenAI-compat endpoint 400s unless the assistant's tool_calls echo back `extra_content.google.thought_signature`; the openai SDK surfaces it on `tc.model_extra`, so the loop now replays it on follow-up requests
  - the model couldn't cite sources because tool text never exposed the source ids — added `[Source id: ...]` to every tool's output, which made grounding pass
- Refined guardrail: conversational replies (plain or JSON) pass through when no tools ran; grounding is enforced only once tool results exist; system prompt nudges concise answers and plain-text chit-chat
- Deployed frontend to Cloudflare Worker version `fbfa1426-47df-4e08-ab4a-edb1d6fb512f`; verified live Chat UI
- Live verification: exact-section lookup returns grounded quote with 13 pinned sources; broad "fraud" question converges (7 sources); citation-validation returns honest not-found; chit-chat passes through
- Tests: 23 backend + 3 frontnetend green; push `e8db3e3`

**Files touched:**
- backend/api/agent.py, backend/api/tools.py, tests/test_agent.py
- work_log.md, lessons_learned.md, next_steps.md
- VPS: /docker/lawcite/docker-compose.yml, /root/lawcite-build, images lawcite-api:2cb6629
- Cloudflare Worker law-cite-tt (fbfa1426)

**Status:** complete (Phase A live); Phase B precedent-chain agent pending

## [2026-08-18 ~23:50] Agentic Chat Phase B — precedent-chain agent over the case-law graph (live)

**What was done:**
- `cases` + `case_citations` tables in data/init.sql (and applied directly on the production PG)
- backend/scripts/load_case_edges.py: loads graphify-out/case_edges.json (7,914 CITES_STATUTE edges, 2,236 unique case nodes) into Postgres; `--records` backfills title/court/year from crawled webOPAC/CCJ JSONL (edge id `case:<sha256-prefix>` joins to crawler `record_id` directly)
- LawCitePGDB: cases_citing_chapter, case_citations_for, cases_citing_chapters (two-hop statute-mediated expansion), get_case, search_cases
- API: GET /api/cases?q=, GET /api/cases/citing?chapter=, GET /api/cases/{id} (detail + related_cases)
- Agent tools: citing_cases, search_cases, expand_case — registered for every mode (no frontend change); system prompt extended for precedent questions
- Dockerfile now ships backend/scripts + case_edges.json; loader runs in-container via `docker compose exec api python -m scripts.load_case_edges --edges /app/case_edges.json --pg "$PG_DSN" --force`
- Deployed image `lawcite-api:18bee46`; live verification: citing, expand (2-hop chain of 50 related cases), search, and agent precedent questions all `status: ok` with case sources
- Fixed live 500: /api/cases search used `row["case_id"]` but search rows carry `id`; `_case_summary` now reads either; regression test added (push `d5f5012`)
- Caveat: case titles are blank until the external SSD (webopac.jsonld) is mounted and the loader re-run with `--records` — answers currently cite `case:<hash>` handles only

**Files touched:**
- backend/api/{agent,main,models,tools}.py, backend/scraper/db_pg.py, backend/scripts/load_case_edges.py, backend/Dockerfile, data/init.sql
- tests/{test_tools,test_agent,test_db_pg,test_load_case_edges}.py
- VPS: /root/lawcite-build, image lawcite-api:18bee46, tables created + data loaded
- pushes `18bee46` (feat) + `d5f5012` (fix)

**Status:** complete (Phase B live); titles backfill pending SSD mount

## [2026-08-19 ~12:30] Phase B title backfill — case names + years extracted from webOPAC corpus

**What was done:**
- SSD attached; shipped webopac.jsonld (3,344 records, 138MB) + judgments.jsonl to the VPS and re-ran the loader with `--records` (via `docker cp` into the api container; note: container recreate wipes `docker cp`'d files — copy AFTER `compose up`)
- webOPAC records have no title field — the case name is parsed from the judgment header: `BETWEEN ... AND ...` party pattern, numbered parties `(1) ...`, Court of Appeal `OF ... AND ...` pattern, fallback to first name-like header line; header markers restricted to the first 12 lines so a `BETWEEN` deep in the body isn't misread
- Years from delivery-date filenames (`cv_18_01783DD10apr2019.pdf`), "Date of Delivery" lines, or plain url year
- Result: **2,235 / 2,236 case nodes titled (99.96%), 2,049 with year**; live-verified on `/api/cases`, `/api/cases/citing`, and agent precedent answers now name real cases
- Regression tests for the header heuristics (13 loader tests)

**Files touched:**
- backend/scripts/load_case_edges.py (title/year extraction), tests/test_load_case_edges.py
- VPS: image lawcite-api:18bee46 rebuilt, records copied into container, loader re-run against production PG
- push `299e2b3`

**Status:** complete

## [2026-08-19 ~13:20] Historical-band crawl sweep drivers

**What was done:**
- Created `backend/scripts/scan_webopac_years.py` to scan record counts per delivery year from 1873 to 2017 without downloading PDFs.
- Created `backend/scripts/sweep_webopac.py` to drive the historical-band crawl (1873-2017) year-by-year with a configurable cap, polite rate-limiting, and resumable file-appending logic.
- Pushed scripts in commit `c2cbcef`.

**Files touched:**
- backend/scripts/scan_webopac_years.py, backend/scripts/sweep_webopac.py
- push `c2cbcef`

**Status:** complete

## [2026-08-19 ~14:35] Historical-band sizing scan & pilot

**What was done:**
- Ran a pilot crawl of the year 2017 using `sweep_webopac.py` (cap=3) on the local machine with SSD attached. Successfully downloaded, parsed, and appended 3 records to the SSD JSONL (`webopac.jsonld`).
- Ran a complete historical-band scan (1873-2017) using `scan_webopac_years.py` locally. The process ran in the background for 1 hour and 19 minutes, hitting every year's OPAC search and pagination endpoint.
- Identified **16,852 total records** across the 1873-2017 band (saved to untracked `backend/webopac_scan.jsonl`).

**Files touched:**
- /Volumes/Extreme SSD/law-cite-tt-data/case_law/ (webopac.jsonld, webopac_pdfs/2017/)
- backend/webopac_scan.jsonl (new, untracked)

**Status:** complete (scan complete, full download pending)

