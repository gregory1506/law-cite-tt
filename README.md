# law-cite-tt

A legal citation engine for the **Laws of Trinidad and Tobago**. Sources statute data from the official Digital Law Library at <https://laws.gov.tt/ttdll-web/revision/list> and answers "what did provision X say on date Y?" by searching 407,000+ section-aware statutory chunks with full-text + vector search.

## Live product

Production research release is live:

- **Frontend:** https://law-cite-tt.gjo-ai.workers.dev
- **API:** https://srv1629323.hstgr.cloud (`/api/health`)
- **Corpus:** 533 chapters, 4,989 versions, 407,008 embedded statutory chunks

### Features

- **Research** — grouped provision search, exact chapter/section lookup, chapter browsing, historical cutoffs, version selection, and official PDF links
- **Cite** — structured citation resolution with explicit found / not-found / ambiguous states, exact source text, historical selection, official PDFs, and copyable citations
- **Chat** — coming soon (placeholder)

Next release gate: production authentication, API authorization, and rate limiting.

## Architecture

Two surfaces live in this repo:

1. **Customer app** (`citation-tool/`) — Svelte 5 (runes) + Vite, deployed as static assets to Cloudflare Workers (`wrangler deploy`)
2. **API** (`backend/`) — FastAPI backed by PostgreSQL 16 + pgvector on a Hostinger VPS behind Traefik

The ingestion pipeline (`backend/scraper/`) crawls laws.gov.tt, extracts PDFs to markdown, chunks section-aware, embeds (384-dim), and indexes into PostgreSQL with FTS5-style full-text + vector search. A case-law layer crawls webOPAC judgments and derives statute citation edges (7,914 edges / 2,236 case nodes).

### Repo layout

- `backend/api/` — production FastAPI application
- `backend/scraper/` — ingestion, database, embeddings, and search modules
- `backend/graphrag/` — case-law citation graph tooling
- `citation-tool/` — production Svelte customer app
- `tests/` — scraper, database, migration, and API coverage
- `docs/superpowers/` — specs, plans, decision records
- `data/` — database init SQL and fixtures

## Development

### Backend

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r backend/requirements.txt
pytest -v
```

### Frontend

```bash
cd citation-tool
npm install
VITE_API_BASE=https://srv1629323.hstgr.cloud npm run dev
```

Build for production with `VITE_API_BASE=... npm run build`, then `wrangler deploy`.

## Background: corpus acquisition

The corpus was built from a deliberate rate-limited crawl of all 533 chapters on <https://laws.gov.tt>, downloading **every historical version** of each (one chapter can have 10+ versions spanning back to the 1800s) and extracting each to markdown. The crawl rate-limits itself to ~1.5s between requests out of courtesy to a government website with no published crawl policy. Do not remove or shorten that delay.

- Data lives on an external drive mounted at `/Volumes/Extreme SSD/law-cite-tt-data/` (see `backend/scraper/config.py` — `OUTPUT_ROOT`)
- Run the reconnaissance crawl with `python backend/scripts/run_recon.py`
- The SQLite working DB (`law_cite.db`) and markdown corpus live alongside the PDFs on that drive; production uses the PostgreSQL/pgvector migration

### Known crawl gotchas — do not "fix"

- The site returns an **HTTP 500** (not an empty page) once you page past the last real listing entry. `backend/scraper/catalog.py`'s `crawl_full_catalog` already treats this as the normal end-of-pagination signal — this is correct, verified behavior, not a bug.
- If the recon run is interrupted partway through, **re-running restarts from scratch** — there is no resume/skip-already-done logic in Phase 0. Already-downloaded files just get overwritten with identical content; harmless but wasteful.
