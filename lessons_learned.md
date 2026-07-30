# Lessons Learned

Non-obvious things discovered during work in this folder. Capture the "I wish I knew this before" moments.

## Format

Each entry:
```
## [YYYY-MM-DD] <title>

**Context:** What were you trying to do?

**What happened:** What surprised you?

**Lesson:** What would you do differently?

**Tags:** #tag1 #tag2
```

## Entries

## [2026-07-27] T&T law PDFs have inconsistent section formats across editions

**Context:** Building a section-aware chunker to split 10k+ markdown files by section.

**What happened:** Three distinct section formats appeared: the modern format puts the marginal title before the section number, the 1950s-era format puts the section number first with the title at the end, and older ordinances use Roman numerals. The chunker had to detect and handle all three without pre-classification.

**Lesson:** When parsing government documents across decades, design the parser to detect format variants heuristically rather than assume a single convention. The row-by-row approach (process each line independently, emit section on number match) proved more robust than trying to detect the overall format upfront.

**Tags:** #chunker #pdf-parsing #trinidad-tobago

## [2026-07-27] Arrangement of Sections masquerades as body text

**Context:** Writing `_find_body_start` to skip the Arrangement before section extraction.

**What happened:** "Arrangement of Sections" headers were inconsistently formatted — sometimes titled "ARRANGEMENT OF SECTIONS", sometimes "Arrangement of Sections", and sometimes not labelled at all. Subsidiary legislation in appendices also had their own mini-arrangements within the body area.

**Lesson:** The safest approach was a two-pass strategy: find the primary body start by looking for the first non-empty line after the Arrangement heading+entries, then scan forward from there. Secondary arrangements within subsidiary legislation were left intact since they're part of the body.

**Tags:** #chunker #edge-cases

## [2026-07-27] Golden set test failures revealed ordering and filtering problems

**Context:** Running 30 golden entries against the DB to validate lookup_section.

**What happened:** 13/28 entries initially failed. Root causes: wrong ordering by date (NULL dates sorted before real dates), arrangement entry filtering too aggressive (filtering out short body sections), schedule entries missing section_ref support, date-filtered lookups failing for undated versions.

**Lesson:** The golden set is invaluable for catching edge cases that unit tests miss. Fixing the test runner to check ALL results (not just the first) and report detailed verdicts per row made debugging tractable. The lesson: always iterate over results with tolerance rather than asserting on the first row.

**Tags:** #testing #golden-set #debugging

## [2026-07-27] Embedding 407k chunks: batch size matters more than expected

**Context:** Generating embeddings for all chunks to enable vector search.

**What happened:** Initial batch_size=32 estimated 280 min for 407k chunks. Increasing to batch_size=128 cut it to 47 min. Actual wall time was 12.6 min — the model warms up and throughput improves significantly after the first few batches.

**Lesson:** Always benchmark with representative batch sizes. Sentence transformers with `all-MiniLM-L6-v2` processes ~540 chunks/second on Apple Silicon once warmed up. The model download on first run is a one-time cost.

**Tags:** #embeddings #performance #sentence-transformers

## [2026-07-27] Chapter numbers from folder names must use first two underscore-parts only

**Context:** Building the `ingest_chapter` method in db.py. The markdown folder names encode the chapter number and title in the format `{n}_{m}_{Title_With_Underscores}`.

**What happened:** Using `split("_", 1)[1].replace("_", ":")` produced chapter numbers like `01:Prevention:of:Crimes` instead of `10:01`. The `chunks` table had correct numbers (from the chunker's header parser) but the `chapters` table was wrong, breaking the `/api/chapters` endpoint.

**Lesson:** Never derive structured data from folder names by splitting on the same separator that appears in the title. Two-part prefix identification (`parts[0].isdigit() and parts[1].isdigit()`) fixed it cleanly. Also: always verify the `chapters` table after ingestion by querying the first 5 rows.

**Tags:** #data-ingestion #chapter-numbers #bugs

## [2026-07-27] SQLite `check_same_thread=False` is needed for FastAPI + TestClient

**Context:** Running the FastAPI demo app. `get_db()` and `get_search()` create connections on module load, but TestClient routes requests through a thread pool.

**What happened:** `SQLite objects created in a thread can only be used in that same thread` — the connection was created in the main thread but used from a worker thread.

**Lesson:** Either pass `check_same_thread=False` on `sqlite3.connect()` (quick fix for dev/demo) or switch to PostgreSQL with proper connection pooling (production fix). The `check_same_thread` flag is safe for read-heavy workloads with WAL mode but doesn't protect against concurrent writes.

**Tags:** #sqlite #fastapi #concurrency

## [2026-07-27] pip packages installed outside virtualenv can cause confusing import errors

**Context:** Setting up sentence-transformers for the embedding module.

**What happened:** `pip install sentence-transformers` succeeded but the package was installed to the system Python 3.12 site-packages, not the venv's Python 3.13. Python reported "ModuleNotFoundError" even though `pip list` showed it installed.

**Lesson:** Always use `uv pip install` inside the virtual environment to ensure packages go to the right location. The system `pip` may default to a different Python version's site-packages.

**Tags:** #python #venv #dependency-management

## [2026-07-28] CORS failures in the browser look identical to a dead server

**Context:** Wiring the Svelte frontend to the FastAPI backend during the Postgres migration (Phase F/G).

**What happened:** `curl` to the API worked perfectly, but the browser's fetch calls all failed with `net::ERR_FAILED` and no CORS error message in the console — it looked exactly like the server was unreachable. The actual cause was `allow_origins=["http://localhost:5173"]` in FastAPI's CORSMiddleware, but Vite had picked port 5174 because something else already held 5173. A second, subtler version of the same bug: `allow_origin_regex=r"http://localhost:\d+"` still rejected `http://localhost` (port 80) because browsers omit the port from the Origin header when it's the default for the scheme (80 for http, 443 for https) — the regex required a port number that wasn't there.

**Lesson:** When a frontend fetch to a known-good API fails with `ERR_FAILED` and zero server-side logs of the request, suspect CORS before anything else — Chrome doesn't surface CORS as a distinguishable error to `fetch()`'s catch handler. Also: don't hardcode a dev port in CORS config, and if using a regex for allowed origins, always make the port group optional (`(:\d+)?`) to cover default-port origins.

**Tags:** #cors #fastapi #debugging #docker

## [2026-07-28] `git worktree` doesn't inherit gitignored directories like `.venv`

**Context:** Setting up an isolated worktree for the Postgres migration phase.

**What happened:** The new worktree had no `.venv/` (correctly gitignored), so `python`/`pip` weren't found via the usual relative path. Rather than creating a duplicate venv per worktree, pointing directly at the main checkout's `.venv/bin/python` worked fine since the interpreter and installed packages don't depend on cwd.

**Lesson:** For lightweight worktree-based phases, it's fine to share one venv across the main checkout and its worktrees by absolute path — no need to reinstall dependencies per worktree unless the worktree needs genuinely different package versions.

**Tags:** #git #worktrees #venv

## [2026-07-29] Token swaps still require checking inherited native control colors

**Context:** Finishing the citation-tool dark theme after the shared CSS tokens and sidebar shell were already in place.

**What happened:** Inactive Explore tabs inherited the browser's black button text and became nearly invisible, while the mobile menu button overlapped the sidebar brand even though the desktop shell and production build both looked correct.

**Lesson:** A dark-theme pass needs visual checks of every interactive state at desktop and mobile widths; successful compilation and shared color tokens do not cover browser defaults or fixed-position overlap.

**Tags:** #frontend #css #responsive #visual-qa

## [2026-07-29] Traefik labels do not create network reachability

**Context:** Turning the existing Docker Compose deployment sketch into a production VPS plan.

**What happened:** The API had correct-looking Traefik router and service labels but was only on its Compose default network. An independently deployed Traefik container cannot route to that service unless both containers share an external Docker network.

**Lesson:** Every Traefik-backed Compose service should explicitly join the proxy's external network and set `traefik.docker.network` when it also joins a private application network.

**Tags:** #docker #traefik #networking #deployment

## [2026-07-29] Manual Compose needs a distributable image and self-contained initialization

**Context:** Adapting the LawCite deployment to Hostinger Docker Manager's Compose manually editor.

**What happened:** The repository-oriented Compose used `build:` and mounted `data/init.sql`, but a manually pasted Hostinger project has neither the private repository build context nor that host file.

**Lesson:** For manual Compose platforms, load or publish a versioned application image and make database initialization self-contained. For this deployment, restore the full PostgreSQL dump before adding the API.

**Tags:** #docker #hostinger #deployment #images

## [2026-07-29] Historical dates must use the migrated canonical fallback

**Context:** Verifying grouped search with an as-at date against the full PostgreSQL corpus.

**What happened:** Synthetic fixtures stored dates on both `versions` and `chunks`, but migrated production-shaped rows can have `versions.as_at_date` null while `chunks.as_at_date` is populated. Filtering only the version column returned no valid historical provisions.

**Lesson:** Search filters and response metadata must use the same canonical expression, `COALESCE(versions.as_at_date, chunks.as_at_date)`. Include a migrated-shape regression fixture, not only idealized new-schema rows.

**Tags:** #postgresql #migration #temporal-search #testing

## [2026-07-29] Catalog metadata needs independent corpus validation

**Context:** Reviewing legal-first search results in a real browser after adding legislation titles.

**What happened:** Some bankruptcy provisions are associated with the catalog title `30:50 Burial Grounds`, even though the matched text and official PDF are bankruptcy material. The frontend accurately exposed an existing chapter/version association problem.

**Lesson:** Once authority metadata becomes prominent, validate catalog joins against document text and source IDs. UI polish cannot compensate for a wrong title-to-version relationship, so this requires a separate corpus reconciliation pass.

**Tags:** #data-quality #legal-research #metadata #validation

## [2026-07-30] Local preview CORS must cover loopback host variants

**Context:** Running the Cite workflow in a real browser against the production API before deployment.

**What happened:** The API allowed `http://localhost:<port>` but rejected the equivalent `http://127.0.0.1:<port>` origin, so the page loaded while chapter requests failed. A second unrelated app was already using the IPv6 `localhost` listener, making a host swap unsafe.

**Lesson:** Development CORS should explicitly permit both `localhost` and `127.0.0.1` with optional ports. Browser QA should inspect the console immediately and reuse a fixed host/port pair so origin-specific failures are not mistaken for API outages.

**Tags:** #cors #browser-qa #localhost #deployment
