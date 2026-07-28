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
