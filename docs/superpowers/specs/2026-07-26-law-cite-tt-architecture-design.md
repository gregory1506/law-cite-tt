# law-cite-tt: Architecture Design

**Status:** Approved for planning
**Date:** 2026-07-26

## Purpose

An API-first citation validation and lookup service for the Laws of Trinidad and Tobago, modeled on MapleJuris (Canadian legal citation validation API backed by a knowledge graph). Given a chapter/act/section reference, the API confirms whether it resolves to an actual, in-force provision — validated against the real statutory text, not just catalog metadata — and returns it formatted as a proper T&T-official-style citation.

Source of truth: https://laws.gov.tt/ttdll-web/revision/list (Government of the Republic of Trinidad and Tobago Digital Law Library).

## Corpus size (verified, not estimated)

The site exposes no total-count or page-count UI element. Verified by binary-searching the `offset` query parameter against the live "Revised Acts" list (10 records per page) until entries stopped appearing:

- **533 entries** in the Revised Acts list as of 2026-07-26.
- Repealed acts, unproclaimed acts, omitted acts, and legal notices are separate lists on the site and are **out of scope for v1** (may be added later as their own ingestion targets).

## Why metadata alone is not enough

An earlier draft of this design scoped v1 to chapter/act-level metadata only (title, act number, dates, in-force status), with PDF text fetched lazily on first request. On review, this was rejected: MapleJuris's actual value proposition is validating a citation against the *exact statutory text*, not just confirming a chapter exists. Metadata-only validation cannot answer "does Section 12(3) say what this citation claims" — only "does this chapter exist and is it in force." Since matching that capability is the point of the project, full text must be ingested for every chapter, not fetched reactively.

The resolution keeps the **graph** simple (chapter/act-level nodes only — no per-section graph nodes) while still supporting section-level validation, by pushing that capability into the **retrieval layer** instead: full text is chunked with section-awareness and embedded, so a query about a specific section is answered by searching indexed chunks, not by walking a deeper graph.

## Components

- **Scraper/ETL (Python)** — crawls the Revised Acts list (paginated, rate-limited), scrapes metadata, downloads each version's PDF, extracts text, chunks, and embeds it. Uses an in-process DuckDB instance purely as ephemeral staging/dedup/transform space during each run — DuckDB never persists as a store between runs.
- **Serving database: managed Postgres + pgvector** (e.g. Neon). Tables: `chapters`, `versions`, `amendments` (edges), `chunks` (chunk_text + embedding + section_ref + extraction_method, keyed to `version_id`). At 533 rows, this is trivially fast — no need for Neo4j (graph is too shallow to justify a dedicated graph DB) or TimescaleDB (versioning is a date-range query, not a time-series/metrics workload).
- **Blob storage** (e.g. Vercel Blob or S3-compatible) — holds raw extracted text per version, keyed by version ID. Keeps Postgres rows small; Postgres holds pointers, not blobs.
- **API: FastAPI (Python)** — same language as the scraper, sharing a core library for "fetch + parse a PDF" so both the batch scraper and any future on-demand path use identical logic.

## Data flow

1. **Eager full crawl (v1 launch, one-time batch):** for all 533 chapters — scrape metadata, fetch each chapter's current PDF, extract text, chunk, embed, and populate Postgres + Blob storage. This must complete before the API is considered launch-ready, since validation is meaningless without text coverage.
2. **Ongoing scraper runs (scheduled, via GitHub Actions cron):** re-crawl metadata; for any chapter whose extracted-text content hash has changed (new revision published), re-run extract → chunk → embed for that chapter only. Unchanged chapters are skipped — no wasted re-embedding cost.
3. **API requests** are served entirely from Postgres/pgvector/Blob storage — the API itself never scrapes laws.gov.tt directly.

## PDF consumption pipeline

1. **Fetch** the specific PDF from `/ttdll-web/revision/download/[ID]?type=act` — one file at a time, never bulk-mirrored.
2. **Detect text layer vs. scanned.** The corpus spans 1898–2016; older ordinances are likely scanned images with no text layer, newer revisions likely native text. Try native extraction (PyMuPDF/pdfplumber) first; if extracted character count is near-zero or the text is mostly garbage, fall back to OCR (Tesseract).
3. **Clean/normalize** — strip headers/footers/page numbers, fix OCR hyphenation artifacts, normalize whitespace.
4. **Chunk, structure-aware first.** Try splitting on section markers (regex) so a chunk maps to "Section 12" wherever possible. Fall back to fixed-size sliding-window chunking (with overlap) where section structure can't be reliably detected — common in OCR'd older ordinances.
5. **Embed** using a legal-domain-tuned embedding model (e.g. Voyage `voyage-law-2`) rather than a generic one, since retrieval quality on legal text is the whole point of this layer. Exact provider is finalized during implementation, not locked in this spec.
6. **Store** — raw text → Blob storage; chunks + embeddings → the `chunks` pgvector table, tagged with `extraction_method` (native/OCR) for provenance.
7. **Idempotency** — hash the raw extracted text; skip re-chunk/re-embed for a version whose hash hasn't changed since the last run.

## Scraping etiquette (hard constraints — this is a government website)

- **No 500s / no server strain.** Sequential requests only (no concurrency against laws.gov.tt), with a deliberate delay between requests (start at ~1–2s, adjustable if the site clearly tolerates more). Exponential backoff and a request cap on retries for transient errors — never hammer a failing endpoint.
- **Anonymous scraping preferred.** Use a plain, standard browser-like User-Agent (not a self-identifying bot/contact UA). No authentication, no cookies beyond what's needed to load a page, no attempt to bypass any access control.
- **`robots.txt` was checked and returns 404** (no crawl policy published) — self-imposed limits above stand in for one.
- **Cache aggressively.** Once a page or PDF is fetched, never re-fetch it unless a scheduled diff run detects it changed. The eager full crawl is a one-time cost, not a recurring one.

## Error handling

- Scraper failures are **row-level**: skip and log, never abort the whole run. A failed chapter is retried on the next scheduled run, not immediately re-hammered.
- API distinguishes **"chapter/section doesn't exist"** from **"exists but text temporarily unavailable"** (e.g. extraction failed) rather than opaque 500s.
- A scraper outage or partial failure never blocks the API from serving already-ingested data.

## Testing

- Scraper tests run against **saved HTML fixtures** (real samples already captured during design/verification), not the live site — CI never hits laws.gov.tt.
- API gets contract tests against a seeded test Postgres instance.
- A periodic **manual** (non-CI) smoke test against the live site catches upstream structure changes early.

## Explicitly out of scope for v1

- Section-level graph nodes (handled via retrieval/chunking instead, see above).
- Repealed acts, unproclaimed acts, omitted acts, legal notices (separate site lists, not part of the initial 533-entry corpus).
- A public search/browse UI (API-first; a UI can be a thin client added later).
- Confidence-scored fuzzy citation matching (MapleJuris-style "did you mean" alternatives) — worth revisiting post-v1 once exact-match validation is proven.
