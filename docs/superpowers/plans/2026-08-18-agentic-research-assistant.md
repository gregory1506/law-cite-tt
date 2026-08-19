# LawCite TT Agentic Research Assistant Plan

**Date:** 2026-08-18

**Status:** Phase A LIVE (2026-08-18, image `lawcite-api:2cb6629`, Worker
`fbfa1426`). Phase B not started.

**Production frontend:** `https://law-cite-tt.gjo-ai.workers.dev`

**Production API origin:** `https://srv1629323.hstgr.cloud`

## Objective

Turn the Chat placeholder into a **grounded agentic research assistant** that
answers "what did provision X say on date Y?" and "what cases cite X?" by
reusing the existing retrieval and citation-graph infrastructure. No new data
sources, no new services — the two phases add an LLM tool-calling loop on top of
what is already live.

Phase A ships a general Chat agent whose tools are the existing statute
endpoints. Phase B adds a precedent-chain agent whose tools walk the 7,914-edge
case-law citation graph already crawled from webOPAC/CCJ.

The non-negotiable constraint: this is a **legal citation engine**. The agent
must never fabricate a statute, section, date, or case. Every factual claim in
the answer must trace to a tool result, and the sources section must be rendered
from actual tool output, not the model's recollection.

## Current State

- The Svelte frontend is deployed as static Worker assets; the Chat tab is a
  UI-only "coming soon" placeholder (`citation-tool/src/routes/Chat.svelte`).
- The FastAPI backend exposes production endpoints that already do the retrieval
  work: `/api/search`, `/api/search/grouped`, `/api/lookup`,
  `/api/citations/resolve`, `/api/chapters`, `/api/stats`.
- The backend has no LLM dependency today — embeddings are local via fastembed;
  there is no generation layer.
- Case-law artifacts exist off-graph: `graphify-out/case_edges.json` (7,914
  `CITES_STATUTE` edges, case → chapter/section) and the webOPAC crawl output
  (`webopac.jsonld`, with `case_name`, `title`, `record_id` per judgment) on the
  external SSD. `backend/graphrag/retrieve.py` already builds an in-memory
  adjacency structure over these, but only as a CLI tool — not served by the API.
- The public API is unauthenticated (auth/rate-limiting is a separate pending
  release gate).

## Decisions

### LLM provider — pluggable OpenAI-compatible client

Use the `openai` SDK pointed at an env-configured base URL, so the provider can
be swapped without code changes:

- `OPENAI_API_KEY` — required in production
- `OPENAI_BASE_URL` — optional; defaults to OpenAI, but can point at OpenRouter
  or any compatible gateway
- `LAWCITE_AGENT_MODEL` — model id (default a small capable model such as
  `gpt-4o-mini`; legal work may want a stronger model)

Rationale: no GPU on the VPS, one dependency, provider-agnostic, and the model
choice can be tuned after real-corpus eval rather than locked at build time.

### Tool architecture — in-process, not self-HTTP

Agent tools call `LawCitePGDB` methods directly (same process as the API) rather
than calling the HTTP endpoints. Faster, avoids CORS/auth/recursion concerns, and
lets tools return the already-enriched shapes the API uses.

### Endpoint shape — `POST /api/chat` (non-streaming first)

```
POST /api/chat
{ "messages": [ {role, content}, ... ], "mode": "research" | "precedent" }
```

Returns the assistant message plus a `sources` array of rendered tool results
(statute citations, case names, PDF links). Streaming via SSE is a follow-up,
not a Phase A requirement — keep the first cut simple.

### Grounding guardrail — structured reply + source pinning

- The loop instructs the model to reply as JSON:
  `{ "answer": "...", "source_ids": ["chunk:123", "case:...", ...] }`.
- After the loop, the server validates every `source_id` actually appeared in a
  tool result for that turn; any unknown id is dropped and the answer is
  re-issued once. If no tool result backs the answer, the server returns a
  refusal ("I could not verify this against the Laws of Trinidad and Tobago —
  try Research or Cite").
- The UI's Sources section is rendered from the server-side tool results, never
  from the model's text.

### Budget and safety caps

- Max 8 tool-call iterations per turn.
- Tool results truncated to ~2,000 chars each before being sent to the model;
  total context capped.
- The agent operates read-only against the DB — no write tools.

### Precedent data — migrate graph into Postgres

Move `case_edges.json` + webOPAC judgment metadata into the API's Postgres so
production is self-contained (no file dependency on the VPS):

- `cases` — judgment metadata (case id/hash, title, year, record_id)
- `case_citations` — `(case_id, chapter, section, confidence, method, evidence)`

A one-off migration script loads from `graphify-out/case_edges.json` and the
webOPAC JSONL on the developer machine, then `psql`/compose is used to load the
VPS. Edges are ~8k rows — tiny; the migration is fast and idempotent.

## Target Architecture

```text
Tester
  -> LawCite Worker (static Svelte)
       -> Chat tab
            -> POST /api/chat (FastAPI)
                 -> agent loop (openai SDK)
                      -> tools: LawCitePGDB (search/lookup/cite/chapters)
                               + case_citations (citing cases / expand)
                           -> PostgreSQL 16 + pgvector (+ case tables)
```

## Phase A — Chat agent over the existing API

New files:

- `backend/api/agent.py` — the loop: system prompt, message history, tool
  schema (JSON function definitions), up to 8 iterations, structured reply
  parsing, grounding validation, refusal path.
- `backend/api/tools.py` — tool registry. Each tool is an async function
  wrapping a `LawCitePGDB` method with an LLM-facing JSON schema:
  - `search_provisions(query, chapter?, date?, limit)` → `search_grouped`
  - `lookup_section(chapter, section, date?)` → `lookup_section`
  - `resolve_citation(chapter, section, date?)` → `resolve_citation`
  - `list_chapters(query?)` → `list_chapters`
- `backend/api/models.py` — `ChatRequest`, `ChatResponse`, `ChatSource`.
- `backend/api/main.py` — mount `POST /api/chat`.

Frontend:

- `citation-tool/src/routes/Chat.svelte` — real message UI (history list, input,
  loading state, render Sources with chapter/section + official PDF links,
  reuse existing CSS variables from Explore/Cite).
- `citation-tool/src/lib/api.js` — `chat()` helper.
- `citation-tool/src/routes/Chat.test.js` — component tests.

## Phase B — Precedent-chain agent over the citation graph

Data migration:

- `backend/scripts/load_case_edges.py` — reads `graphify-out/case_edges.json`
  and the webOPAC JSONL; upserts `cases` and `case_citations` into Postgres.
- `data/init.sql` — add the two tables.

New API surface:

- `GET /api/cases/citing?chapter=&section=` — cases citing a statute
- `GET /api/cases/{id}/citing` — cases citing a given case (chain expansion)
- `GET /api/cases?q=` — search cases by title/name

Agent tools (added to `backend/api/tools.py`, gated by `mode="precedent"`):

- `citing_cases(chapter, section?)` → statute → cases
- `expand_case(case_id)` → case → cases that cite it
- `search_cases(query)` → case lookup

The precedent prompt drives a genuine chain-of-precedent workflow: seed from a
provision, list cases citing it, then expand to cases citing those cases,
returning a dated precedent timeline. This is the differentiated capability.

## Files Touched

- `backend/api/agent.py`, `backend/api/tools.py`, `backend/api/main.py`,
  `backend/api/models.py`
- `backend/scripts/load_case_edges.py`
- `data/init.sql`
- `backend/requirements.txt` (+ `openai`)
- `citation-tool/src/routes/Chat.svelte`, `citation-tool/src/lib/api.js`,
  `citation-tool/src/routes/Chat.test.js`
- `next_steps.md`, `lessons_learned.md`, `work_log.md`

## Tests

- `tests/test_agent.py` — loop behavior with a mocked LLM client: tool
  selection, iteration cap, structured-reply parsing, grounding rejection on
  unverified claims, unknown `source_id` dropping.
- `tests/test_tools.py` — each tool's JSON schema and DB call against the real
  Postgres corpus (real-corpus assertions, mirroring existing test style).
- `tests/test_case_law.py` — extend for `cases`/`case_citations` tables and the
  three new endpoints.
- Frontend: `citation-tool/src/routes/Chat.test.js`.
- Live verification: same pattern as the Cite rollout — build against the
  production API, deploy Worker, and exercise real questions (a sample golden
  set of statute/date/case questions) at desktop and mobile widths.

## Deployment

1. Backend: build `lawcite-api:<commit>` image, push to the VPS, swap the
   running container (retain previous tag for rollback), add `OPENAI_API_KEY`
   (and `OPENAI_BASE_URL`/`LAWCITE_AGENT_MODEL` if needed) to the container env.
2. Load `cases`/`case_citations` on the VPS via the migration script, verify
   counts (7,914 edges expected).
3. Frontend: `VITE_API_BASE=https://srv1629323.hstgr.cloud npm run build`,
   `wrangler deploy`, verify `/api/chat` and the precedent endpoints from the
   live Worker origin.

## Verification

- `pytest -v` (existing suite + new tests) all green.
- `curl` the three precedent endpoints against production and confirm real case
  names for a known section (e.g. a section cited by webOPAC judgments).
- Send 5–10 golden questions through `/api/chat`; confirm every answer's sources
  render from tool output and no answer contains an unverifiable citation.
- Browser QA: desktop + mobile Chat and precedent flows, zero console errors.

## Risks and Mitigations

- **Hallucinated citations** — the grounding guardrail is mandatory; treat any
  bypass as a release blocker.
- **LLM cost / latency** — caps on iterations and context; non-streaming first;
  monitor per-request cost in the work log.
- **Case edges confidence is `medium` (regex-extracted)** — surface
  confidence/method in the Sources UI so a cautious reader knows edges are
  machine-extracted from webOPAC metadata, not manually verified.
- **Public API exposure** — the Chat/precedent endpoints inherit the same
  unauthenticated exposure as today; do not gate this plan on the separate auth
  release, but keep it on the release queue.