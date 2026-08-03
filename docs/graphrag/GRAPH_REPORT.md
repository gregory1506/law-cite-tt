# GraphRAG for the Laws of Trinidad and Tobago

## What this is
A knowledge graph over the 10,060 PDF-derived statute texts, built entirely from the **existing** SQLite cache (`law_cite.db`) — no re-embedding of the corpus was needed. Each *idea* is a canonical `chapter|section` proposition, grouped into chapters, linked to recurring *concepts*, and connected by both explicit citations and embedding similarity.

## Source of truth
- **DB:** `/Volumes/Extreme SSD/law-cite-tt-data/law_cite.db`
- **Chunks:** 407,008 (each with a 384-dim `all-MiniLM-L6-v2` embedding)
- **Model:** per-chunk embeddings averaged across all historical versions to give each idea one stable vector.

## Graph stats

| Metric | Value |
|---|---|
| Idea nodes (chapter\|section) | 23,175 |
| Chapter nodes | 533 |
| Concept nodes | 136 |
| **Total nodes** | **23,844** |
| PART_OF edges (EXTRACTED) | 23,143 |
| CROSS_REF edges (EXTRACTED) | 6,074 |
| MENTIONS edges (EXTRACTED) | 31,222 |
| SEMANTIC edges (INFERRED) | 65,142 |
| **Total edges** | **125,581** |
| Evidence audit | 60,439 EXTRACTED / 65,142 INFERRED |
| Clusters (communities) | 535 |

## Node model
- `idea:CH|SEC` — a legal proposition (one canonical averaged embedding, `n_versions`, `as_at_dates`).
- `chapter:CH` — the statute itself (parent of its ideas).
- `concept:TERM` — a *defined term* that recurs across ≥2 chapters (e.g. Minister, Board, Court), bridging independent statutes.

## Edge model (honest audit)
| Type | Evidence | Meaning |
|---|---|---|
| PART_OF | EXTRACTED | stat = chapter governs section |
| CROSS_REF | EXTRACTED | "section N" or "Ch. NN:NN" cited in text |
| MENTIONS | EXTRACTED | section text uses a defined concept term |
| SEMANTIC | **INFERRED** | top-k embedding cosine similarity across chapters |

INFERRED edges are clearly tagged so you can distinguish *what was cited* from *what looks similar*.

## Building it
```sh
# build (needs the mounted SSD with law_cite.db)
python backend/graphrag/build.py            # ~2 min, writes graphify-out/
python backend/graphrag/build.py --no-semantic  # skip the 23k x 23k cosine pass
```

## Retrieval
```sh
python -m backend.graphrag.retrieve "penalty for murder in Trinidad and Tobago" --mode bfs
python -m backend.graphrag.retrieve "..." --mode dfs --depth 2
```
- **seeds**: query embedded with the same fastembed model, cosine-scored over idea embeddings.
- **BFS**: broad context (community surrounding the seed).
- **DFS**: trace a specific citation path.

## Evaluation
`backend/graphrag/eval_golden.py` runs the 30-entry `tests/fixtures/golden_set.json` through idea-node recall:
**idea-node recall@20 ≈ 70%**. The lower-confidence cases are temporal "original version" entries where averaging many historical versions dilutes the provenance-specific text — the exact-text citation engine (FTS5) is the correct surface for those.

## Outputs (in `graphify-out/`)
- `graph.json` — GraphRAG-ready JSON (nodes, edges, audit tags)
- `clusters.json` — 535 communities with members
- `idea_embeddings.npy` + `idea_ids.json` — persisted idea vectors for the retriever
- `graph.html` — interactive visualisation
- `graph.cypher` — Neo4j import script

## Honest limitations
- Averaging per-idea embeddings across versions collapses provenance; if you need the temporal layer, retain per-version idea nodes.
- CROSS_REF only resolves intra-act section numbers and "Ch. NN:NN" patterns; standalone act-title citations (e.g. "the Income Tax Act") are not yet resolved to chapter numbers.
- INFERRED semantic edges depend on the base embedding model's notion of "similar."

---

## Case-law layer (CCJ)

The statute graph is extended with a Caribbean Court of Justice case-law layer.

### Discovery / crawling
- `backend/scraper/case_crawl.py` — controlled, anonymized crawler.
  - Only consumes the category **RSS feeds** the site advertises (`/category/judgments/feed/`, `/category/oj-judgments/feed/`). robots.txt is permissive and publishes sitemaps.
  - Real requests carry one fixed, honest research User-Agent; **no** IP rotation, cookie jars, proxy masking, or fingerprint evasion — anonymity here means a single auditable identity with no personal identifiers and provenance params stripped.
  - Rate-limited (default 3s) via the existing `RateLimitedClient`, bounded `--limit`, idempotent JSONL output, PII-free.
- Run it yourself (it is a live crawl, not run from this sandbox):
  ```sh
  python backend/scraper/case_crawl.py --feed judgments --limit 50 --dry-run   # plan only
  python backend/scraper/case_crawl.py --feed judgments --limit 20
  ```

### Discovery finding
CCJ.org judgment posts are largely **decision summaries / metadata**, not full PDF judgments. Recent posts hold ~4 short paragraphs; older appellate posts are bare citations. The `og:description` meta tag carries the fuller case note on older pages and is merged into the body. For full-text judgments you need CCJ's judgment database / neutral-citation regeneration, not the blog HTML.

### Edges
- `backend/graphrag/case_edges.py` — extracts **CITES_STATUTE** edges from case prose, resolving citations against the idea graph:
  - `Ch./Cap. NN:NN` (REGEX, medium confidence) and bare chapter numbers
  - act-title names (`the Prevention of Crimes Act`, `the Income Tax Act`) via normalized title index (TITLE_MATCH, high when unambiguous)
  - every edge tagged `evidence: EXTRACTED`, `method`, `confidence`
- Output: `graphify-out/case_edges.json`

### Retrieval integration
`Retriever` auto-loads `case_edges.json`. `_expandable` treats chapters as
transit-only bridges: a `case` node expands into the ideas of its cited
chapters (`case -> chapter -> idea`), while an `idea` never fans out into its
whole chapter. Every edge must resolve both endpoints — a build-time check
asserts zero dangling edges.

### Tests
`tests/test_case_law.py` (7 tests) covers feed parsing, body extraction, edge resolution, confidence tagging, and JSONL loading.