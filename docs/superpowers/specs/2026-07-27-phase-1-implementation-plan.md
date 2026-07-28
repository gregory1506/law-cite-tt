# Phase 1 Implementation Plan — Temporal Legal Citation Engine

**Target:** A local SQLite + sqlite-vec pipeline that chunks, embeds, and serves temporal citation queries against all 10,060 extracted markdown files.

---

## Phase 1a — Chunking Pipeline

**Goal:** Convert every version markdown file into structured chunks with section awareness.

**Files to create:**
- `scraper/chunker.py` — section-aware chunker, heading detector, garbage filter
- `tests/test_chunker.py` — unit tests on real markdown samples

**Output:**
- Chunk list per version: `(chunk_index, heading, section_ref, chunk_text, is_garbage)`

**Tests:**
- Section boundary recall ≥ 95% (what % of `Section \d+` markers produce their own chunk)
- Section boundary precision ≥ 95% (what % of chunks start at a real section boundary)
- Heading anchoring: every chunk begins with its chapter heading
- Garbage rejection: Tobago Deeds-style markdown yields 0 chunks, 1 flagged-as-garbage record

---

## Phase 1b — SQLite Schema + Ingestion

**Goal:** Create the SQLite database and ingest chapters, versions, and chunks.

**Files to create:**
- `scraper/db.py` — schema creation, insert helpers, connection management
- `tests/test_db.py` — schema integrity, round-trip insert/query

**Output:**
- `law_cite.db` with populated `chapters`, `versions`, `chunks` tables
- 533 chapter rows
- ~10,000 version rows
- ~100,000 chunk rows

**Tests:**
- Schema matches the decision record exactly
- Idempotent re-import: running the ingest twice produces the same row count
- Foreign key integrity: no orphaned chunks or versions

---

## Phase 1c — Embedding + Vector Search

**Goal:** Embed all chunks, build sqlite-vec index, validate recall.

**Files to create:**
- `scraper/embed.py` — embedding model wrapper (voyage-law-2 preferred, configurable)
- `scraper/search.py` — similarity search with temporal filter, citation lookup, FTS fallback
- `tests/test_search.py` — golden test set validation

**Output:**
- `chunks.embedding` column populated with float32 vectors
- sqlite-vec virtual table for ANN search

**Tests:**
- Recall@1 ≥ 90% on golden set (exact citation → exact text, unfiltered)
- Recall@5 ≥ 98% on golden set
- Temporal recall: for golden pairs where text changed between versions, version-stamped query returns correct version in top-1
- Cross-chapter isolation: 0 false positives from wrong chapters
- p50 latency < 100ms, p99 < 500ms

---

## Phase 1d — Golden Test Set

**Goal:** A hand-verified set of (citation → expected text) pairs drawn from real PDFs.

**Files to create:**
- `tests/fixtures/golden_set.json` — ~30 entries

**Format:**
```json
[
  {
    "chapter": "8:08",
    "section": "12",
    "subsection": "3",
    "as_at_date": "2016-12-31",
    "expected_text_prefix": "A person who absconds...",
    "source_version_id": 490,
    "notes": "Hand-verified against the 2016 revised edition PDF page 23"
  }
]
```

Coverage targets:
- 10 simple: "Chapter X Section Y" — exact text match, current version
- 10 temporal: same citation, two different dates → different expected text
- 5 multi-subsection: "Section 12(3)(b)" — nested reference
- 5 edge cases: preamble sections, schedules, repealed sections

---

## Phase 1e — Full Test Suite (Automated)

**Goal:** All tests from the decision record running in CI.

**Files to create/update:**
- `tests/test_temporal.py` — version resolution, amendment chain, gap detection
- `tests/test_latency.py` — p50/p99 benchmarks (pytest-benchmark)
- `tests/test_robustness.py` — concurrent readers, partial failure, re-index
- `tests/test_pipeline.py` — end-to-end: raw markdown → SQLite → query

**Output:**
- `pytest -v` returns ≥ 30 tests, all green
- Latency benchmarks recorded in a baseline file

---

## Phase 1f — API Layer

**Goal:** FastAPI endpoints for citation lookup + temporal query.

**Files to create:**
- `api/main.py` — FastAPI app
- `api/routes.py` — `/citations/lookup`, `/citations/search`, `/citations/versions`
- `api/schemas.py` — Pydantic request/response models
- `tests/test_api.py` — contract tests against seeded SQLite

**Endpoints:**
```
GET /citations/lookup?chapter=8:08&section=12&date=1950-06-01
  → { text, version, confidence, alternatives }

GET /citations/search?q=absconding+debtor&chapter=8:08
  → [{ chunk_text, version, score }]

GET /citations/versions?chapter=8:08&section=12
  → [{ version_label, as_at_date, text_preview }]
```

---

## Schedule (Estimates)

| Phase | Effort | Depends On |
|-------|--------|------------|
| 1a — Chunking | 2 sessions | — |
| 1b — Schema + Ingestion | 1 session | 1a |
| 1c — Embedding + Vector | 2 sessions | 1b |
| 1d — Golden Set | 1 session | 1a (need chunks to verify) |
| 1e — Full Test Suite | 2 sessions | 1c, 1d |
| 1f — API | 2 sessions | 1e |

**Total:** ~10 sessions. Can be parallelized: 1a + 1d can start together; 1b starts after 1a.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Section-aware regex fails on some chapters (non-standard formatting) | Fall back to fixed-size chunking per chapter; flag for manual review |
| voyage-law-2 embedding quality is insufficient for recall threshold | Benchmark against OpenAI `text-embedding-3-large` and `voyage-law-2`; pick whichever scores higher on golden set |
| sqlite-vec recall degrades at 100K vectors | Benchmark at 10K, 50K, and 100K; if linear degradation, switch to pgvector early |
| Golden set takes too long to hand-verify | Start with 15 entries, expand to 30 as a separate task |
