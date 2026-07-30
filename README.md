# law-cite-tt

Citation validation service for the Laws of Trinidad and Tobago. See `CLAUDE.md` for project context and `docs/superpowers/specs/2026-07-26-law-cite-tt-architecture-design.md` for the full architecture.

## Current status

LawCite is live with a Svelte customer app on Cloudflare Workers and a FastAPI,
PostgreSQL 16, and pgvector backend on Hostinger:

- Frontend: https://law-cite-tt.gjo-ai.workers.dev
- API: https://srv1629323.hstgr.cloud
- Corpus: 533 chapters, 4,989 versions, and 407,008 embedded statutory chunks
- Research workflow: grouped provision search, exact lookup, chapter browsing,
  historical cutoffs, version selection, and official PDF links
- Citation workflow: structured resolution, explicit validation states,
  historical selection, exact source text, official PDFs, and copyable citations
- Next release gate: real authentication, API authorization, and rate limiting

The original reconnaissance pipeline remains available for rebuilding the source
corpus. The production application lives under `backend/` and `citation-tool/`.

## Running the Phase 0 reconnaissance crawl

This crawls all 533 chapters on https://laws.gov.tt and downloads **every historical version** of each (one chapter can have 10+ versions spanning back to the 1800s), extracting each to markdown. Expect **60–90+ minutes** — it deliberately rate-limits itself to ~1.5s between requests out of courtesy to a government website with no published crawl policy (see the spec's "Scraping etiquette" section). Do not remove or shorten that delay.

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) for the virtualenv (or plain `venv`/`pip` if `uv` isn't available — swap the commands below accordingly)
- The external drive must be attached and mounted at exactly `/Volumes/Extreme SSD` (see `scraper/config.py` — `OUTPUT_ROOT`). If it's mounted somewhere else or under a different name, edit `OUTPUT_ROOT` in that file before running.

### Setup (first time only)

```bash
cd /Users/gregoryollivierre/GREG_V2/law-cite-tt
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
pytest -v   # confirm all 16 tests pass before touching the live site
```

### Run the crawl

```bash
source .venv/bin/activate
python scripts/run_recon.py
```

It prints nothing until it finishes (roughly 60–90+ minutes later), then a final summary line like:

```
Processed <N> chapters: <N> ok, <N> likely scanned.
Report written to /Volumes/Extreme SSD/law-cite-tt-data/recon_report.csv
```

To run it in the background and check on it later instead of blocking a terminal:

```bash
source .venv/bin/activate
nohup python scripts/run_recon.py > /tmp/recon_run.log 2>&1 &
echo "PID: $!"
```

Check progress at any time with:

```bash
tail -20 /tmp/recon_run.log                                            # final summary once done
ls "/Volumes/Extreme SSD/law-cite-tt-data/pdfs" | wc -l                 # chapter folders created so far
```

### What "done" looks like

- `/Volumes/Extreme SSD/law-cite-tt-data/pdfs/<chapter>/<download_id>.pdf` — one folder per chapter, one PDF per historical version.
- `/Volumes/Extreme SSD/law-cite-tt-data/markdown/<chapter>/<download_id>.md` — matching extracted markdown per version.
- `/Volumes/Extreme SSD/law-cite-tt-data/recon_report.csv` — one row per (chapter, version) with `status`, `character_count`, `likely_scanned`.

A previous partial run (533 chapters, latest version only — before the "fetch every version" change) already confirmed: extraction quality is excellent, 0 chapters need OCR, and total size for that latest-only run was ~2.2 GB. The full-history run will be several times larger — don't worry if it takes up tens of GB; the external drive has 240+ GB free as of 2026-07-26.

### Known gotchas already handled by the code — do not "fix" these if you see them

- The site returns an **HTTP 500** (not an empty page) once you page past the last real listing entry. `scraper/catalog.py`'s `crawl_full_catalog` already treats this as the normal end-of-pagination signal — this is correct, verified behavior, not a bug.
- Running `python scripts/run_recon.py` directly (not via pytest) needs the project root on `sys.path` — already handled by a `sys.path.insert` at the top of `scripts/run_recon.py`.
- If the process is interrupted partway through, **re-running it restarts from scratch** — there is no resume/skip-already-done logic in Phase 0 (that idempotency belongs in the Phase 1 cloud pipeline, not this one-time reconnaissance script). Already-downloaded files just get overwritten with identical content, which is harmless but wastes time — better to let a started run finish if at all possible rather than interrupting and restarting.

### After the crawl finishes

Report back (or inspect yourself) the `recon_report.csv` summary — total rows, `status` breakdown, `likely_scanned` count, and `character_count` min/max/avg. That data is what the next planning phase (Phase 1: cloud pipeline — chunking, embeddings, Postgres/pgvector, API) needs before it can be written without guessing.
