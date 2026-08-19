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

## [2026-08-03] Averaging embeddings across all versions flattens idea discrimination

**Context:** Building a GraphRAG idea graph where each chapter|section gets one embedding by averaging all its historical-version chunk embeddings.

**What happened:** Averaged vectors are near-identical to the latest-version vector (cosine 0.93) — fine for stable sections — but sections that changed a lot across decades (or that are boilerplate "Interpretation" sections repeated verbatim across many chapters) collapse into a mushy middle. Retrieval seeds then tie-scored across unrelated chapters.

**Lesson:** Average only when the versions agree; otherwise prefer the latest dated version's embedding. At minimum, don't expect one canonical vector to serve both "what is this idea now" (latest) and "what did it say in 1950" (temporal) — keep per-version idea nodes for the temporal layer.

**Tags:** #graphrag #embeddings #retrieval

## [2026-08-03] Government legal sites hide full judgments behind summaries

**Context:** Prototyping a CCJ case-law crawl for the graph.

**What happened:** ccj.org judgment posts are short decision summaries (recent ~4 paragraphs; older posts bare citations with the real case note only in the og:description meta tag). No embedded PDFs on the post pages at all.

**Lesson:** Recon the page structure before writing the crawler — the extraction target is often a meta tag, not the <p> body. And "has a judgments page" does not mean "full-text judgments available"; you may need the court's judgment database / neutral-citation system, not the site's blog HTML.

**Tags:** #crawling #case-law #data-quality

## [2026-08-03] Anonymized crawling means honest identity, not hidden identity

**Context:** Asked to make the CCJ crawler "controlled and anonymized."

**What happened:** The correct interpretation is the opposite of proxy-rotating / IP-masking / cookie-evading — that's evasive and often violates ToS. Politeness = robots.txt-aware discovery (RSS feeds), one fixed identifiable research User-Agent, no personal identifiers, rate limits, idempotent storage, provenance params stripped, hashed node ids.

**Lesson:** For public research data, "anonymous" = "auditable but not personally identifiable", achieved via restraint (single honest UA, no evasion) not concealment. Always engage the site owner for large runs.

**Tags:** #crawling #etiquette #ethics

## [2026-08-03] Edge endpoints must be validated against node ids at build time

**Context:** Wiring case->chapter->idea traversal into the GraphRAG retriever and finding that traversal stopped at chapters.

**What happened:** PART_OF edges were emitted with `source: "10:01"` (the dict key / bare chapter number) while chapter nodes were stored with `id: "chapter:10:01"`. All 23,143 PART_OF edges silently referenced a nonexistent node, so a case could reach its cited chapters but never their ideas. Recall/statistics were unaffected (embeddings are node-based), so the bug hid from the eval harness.

**Lesson:** For any graph build, add a post-build invariant check — `len([e for e in edges if e.source not in node_ids or e.target not in node_ids]) == 0` — and fail loudly. Dangling edges are invisible to global metrics but break traversal.

**Tags:** #graphrag #graph-build #data-quality

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

## [2026-07-30] Cloudflare Access can protect a workers.dev route directly

**Context:** Planning invite-only authentication without purchasing a custom
domain for the private beta.

**What happened:** Cloudflare's current Workers configuration supports enabling
Access directly on the existing `workers.dev` route. A custom DNS zone is only
needed later for branded production routing, not for the beta access gate.

**Lesson:** Use the existing Worker hostname to validate the beta before paying
for a branded domain, while still enforcing origin-side JWT verification so the
public API cannot bypass Access.

**Tags:** #cloudflare-access #authentication #workers #private-beta

## [2026-08-03] WebOPAC judgment source sits behind a rotating session-token URL

**Context:** Crawling the TT Judiciary webOPAC (webopac.ttlawcourts.org) for full-text judgment PDFs.

**What happened:** The homepage-level campaign redirect goes to Outlook /owa/ — the actual OPAC lives on the same host, and g. Every search action URL embeds a per-load session id and every RECLIST response carries the "next page" links with fresh session ids. Doing URL-based dedup for pagination produced an infinite loop (each response's page links were always "new").

**Lesson:** (1) Probe the published OPAC, not the marketing homepage, for real content. (2) When paginated listing URLs embed a session token, dedup by the stable semantic key (the record/page offset), not the full URL. (3) Rediscover the form action per search rather than hardcoding a session-bearing URL.

**Tags:** #webopac #scraping #session-token #crawler

## [2026-08-03] The OPAC exposes the same PDF as both an href and a bare URL

**Context:** Extracting full-text judgment links from RECORD pages.

**What happened:** The judgment PDF URL appears twice on a record page: once as an <a href> and again as a bare URL inside the "Full text/Additional Information" MARC field. Preferring the /Judgments/ path avoids pulling ancillary items (e.g. CJ law-term speeches under /LawTermOpen/) into the judgment corpus.

**Lesson:** Crawl by the full-text field but filter/rank by path prefix so the corpus stays judgment-only.

**Tags:** #webopac #pdf-links #marc

## [2026-08-03] Validate crawl resilience by running it, not just a dry-run

**Context:** Full-index webOPAC judgment sweep.

**What happened:** A ~40-record pilot validated every happy path but the full
sweep died mid-2020 on an **unhandled SSLError**: one record's full-text PDF
pointed at an external host (`www.ttparliament.org`) with a cert that failed
verification. `RateLimitedClient` only retried `ConnectionError`/`Timeout`, so
the `SSLError` propagated and killed the whole process losing minutes of work.

**Lesson:** In a long autonomous crawl, treat *every* per-record operation as
fallible — external/third-party content, transient TLS, and parse edge cases
all leak in at scale. Wrap each unit in its own try/except and `continue`
(rather than abort). Also: relaunch idempotently (by stable record hash) so a
crash never wastes already-done work. Prefer `python -u` for unbuffered logs so
progress is observable in a detached run.

**Tags:** #crawlers #sslerror #resilience #background #idempotent

## [2026-08-03] A "0 results" probe can be a parser bug, not a real zero

**Context:** Bracket-checking the OPAC year range.

**What happened:** Multiple year probes reported 0 results when the index was
clearly populated. Root cause: the count regex ran against the raw HTML where a
tag sits between `Search Results` and `:606`. The same page in the visible/text
form shows `Search Results :606`.

**Lesson:** When "nothing found" is surprising, verify by stripping tags and
re-reading the count before concluding the source is empty. A probing
false-negative cost us a re-scoping question and a delay.

**Tags:** #scraping #regex #false-negative #probe

## [2026-08-18] Gemini works as a drop-in via the OpenAI-compatible endpoint

**Context:** Wiring the agentic Chat loop without a dedicated LLM API.

**What happened:** The plan abstracted the LLM behind `OPENAI_BASE_URL` +
`openai` SDK. The user's Gemini key works with zero code changes by pointing
`OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/` and
`LAWCITE_AGENT_MODEL=gemini-2.5-flash`. Function-calling and JSON replies work
through that shim the same as OpenAI.

**Lesson:** When the user already holds a key for a different provider, check for
its OpenAI-compatible endpoint before assuming SDK/provider lock-in. Keep the
LLM client behind env-configured base URL + model so switching is a config change.

**Tags:** #agents #gemini #openai-compatible #llm #config

## [2026-08-18] Grounding guardrails: plain-text passthrough vs refusal

**Context:** Building the agent loop for a legal citation engine where fabrication
is unacceptable.

**What happened:** The model's final message can arrive as structured JSON (when
it respects the instruction) or plain prose. Naively refusing all plain text
breaks conversational replies ("hi"), but passing it through after tools were
used lets the model sneak in unverified claims. Resolved by keying the decision
off whether any tools ran: no tools used → conversational passthrough; tools
used → require a grounded structured reply or refuse. Also: a plain-text
fallthrough was safer than a hard `response_format` dependency across providers.

**Lesson:** A grounding guardrail needs to distinguish "no tools were needed"
from "tools were used but not cited". Judge ungroundedness by the presence of
tool activity, not by the shape of the reply alone.

**Tags:** #agents #grounding #llm #legal-tech #guardrails

## [2026-08-18] Gemini 3.x requires echoing thought_signature on tool calls

**Context:** Wiring a tool-calling loop against Gemini through its OpenAI-compatible
endpoint.

**What happened:** The first model call returned a tool call, but the follow-up
request (with the tool result) failed with `400 Function call is missing a
thought_signature in functionCall parts`. Gemini 3.x models return
`tool_calls[].extra_content.google.thought_signature` and strictly require it to
be replayed on the echoed assistant tool call. The openai SDK keeps it in
`tc.model_extra["extra_content"]`; frameworks that copy only the OpenAI-schema
fields drop it and break. Also surfaced: if the model can't see the exact source
ids in tool output, it invents/omits them and grounding refuses the answer —
always print the ids the guardrail expects.

**Lesson:** When a tool-calling loop talks to a non-OpenAI backend through the
OpenAI-compat surface, preserve provider-specific fields on every tool call
round-trip, and expose the grounding ids in the tool text the model reads. Test
live against the actual model provider, not just a mock.

**Tags:** #agents #gemini #thought-signature #openai-compatible #grounding #deployment
